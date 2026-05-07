import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.idempotency import IdempotencyRecord
from app.services.idempotency import (
    IdempotencyScope,
    begin_idempotent_request,
    idempotency_conflict_envelope,
    normalize_client_request_id,
    record_idempotency_success,
    safe_request_fingerprint,
)

NOW = datetime(2026, 5, 7, 12, 0, tzinfo=UTC)


def idem_settings(**overrides: object) -> Settings:
    defaults = {
        "v2_client_request_id_max_length": 32,
        "v2_idempotency_ttl_seconds": 60,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def scope(
    *,
    actor_key: str = "synthetic_agent:agent_alex",
    route_key: str = "POST /posts",
    target_key: str = "post:create",
    operation_class: str = "create_post",
) -> IdempotencyScope:
    return IdempotencyScope(
        actor_key=actor_key,
        route_key=route_key,
        target_key=target_key,
        operation_class=operation_class,
    )


def test_client_request_id_length_is_config_driven() -> None:
    settings = idem_settings(v2_client_request_id_max_length=12)

    assert normalize_client_request_id("request_123", settings=settings) == "request_123"

    with pytest.raises(HTTPException) as exc_info:
        normalize_client_request_id("request_12345", settings=settings)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid client_request_id"


def test_retry_replays_canonical_response_and_conflicting_reuse_is_conflict(
    db_session: Session,
) -> None:
    settings = idem_settings()
    request_scope = scope()
    fingerprint = safe_request_fingerprint(
        operation_class="create_post",
        body={
            "text": "Synthetic retryable post.",
            "metadata_json": {"internal_marker": "metadata_private_marker_placeholder"},
            "Authorization": "Bearer authorization_header_placeholder",
            "token_hash": "token_hash_placeholder",
        },
        allowed_fields={"text"},
    )

    first = begin_idempotent_request(
        db_session,
        request_scope,
        "post-create-001",
        fingerprint,
        settings=settings,
        now=NOW,
    )
    assert first.outcome == "started"

    canonical_payload = {
        "id": "post_synthetic_result",
        "text": "Synthetic retryable post.",
    }
    record_idempotency_success(
        db_session,
        first.record_id,
        status_code=201,
        response_json=canonical_payload,
        result_reference="post:post_synthetic_result",
    )

    retry = begin_idempotent_request(
        db_session,
        request_scope,
        "post-create-001",
        fingerprint,
        settings=settings,
        now=NOW,
    )
    assert retry.outcome == "replay"
    assert retry.status_code == 201
    assert retry.response_json == canonical_payload
    assert retry.result_reference == "post:post_synthetic_result"

    conflict = begin_idempotent_request(
        db_session,
        request_scope,
        "post-create-001",
        safe_request_fingerprint(
            operation_class="create_post",
            body={"text": "Synthetic conflicting post."},
            allowed_fields={"text"},
        ),
        settings=settings,
        now=NOW,
    )
    assert conflict.outcome == "conflict"
    assert conflict.status_code == 409
    assert conflict.response_json == idempotency_conflict_envelope("fingerprint_mismatch")


def test_idempotency_storage_keeps_only_safe_normalized_request_and_result_fields(
    db_session: Session,
) -> None:
    settings = idem_settings()
    fingerprint = safe_request_fingerprint(
        operation_class="create_post",
        body={
            "text": "Synthetic safe field.",
            "reply_to_post_id": "post_synthetic_parent",
            "raw_body": "raw_body_marker_placeholder",
            "metadata_json": {"private_note": "metadata_marker_placeholder"},
            "Authorization": "Bearer authorization_marker_placeholder",
            "token_hash": "token_hash_marker_placeholder",
        },
        allowed_fields={"text", "reply_to_post_id"},
    )

    decision = begin_idempotent_request(
        db_session,
        scope(target_key="post:post_synthetic_parent"),
        "post-reply-001",
        fingerprint,
        settings=settings,
        now=NOW,
    )
    record_idempotency_success(
        db_session,
        decision.record_id,
        status_code=201,
        response_json={"id": "post_synthetic_reply", "text": "Synthetic safe field."},
        result_reference="post:post_synthetic_reply",
    )

    column_names = set(IdempotencyRecord.__table__.columns.keys())
    assert "metadata_json" not in column_names
    assert "raw_body" not in column_names
    assert "headers_json" not in column_names
    assert "authorization" not in column_names
    assert "token_hash" not in column_names

    persisted = db_session.get(IdempotencyRecord, decision.record_id)
    assert persisted is not None
    persisted_blob = json.dumps(
        {
            "fingerprint": persisted.request_fingerprint_hash,
            "response": persisted.response_json,
            "result_reference": persisted.result_reference,
        },
        sort_keys=True,
    )
    for forbidden in (
        "raw_body_marker_placeholder",
        "metadata_marker_placeholder",
        "authorization_marker_placeholder",
        "token_hash_marker_placeholder",
    ):
        assert forbidden not in persisted_blob


def test_same_client_request_id_is_scoped_by_actor_route_and_target(db_session: Session) -> None:
    settings = idem_settings()
    fingerprint = safe_request_fingerprint(
        operation_class="create_post",
        body={"text": "Synthetic scoped idempotency request."},
        allowed_fields={"text"},
    )
    scopes = [
        scope(actor_key="synthetic_agent:agent_alex"),
        scope(actor_key="synthetic_agent:agent_mira"),
        scope(route_key="POST /posts/post_synthetic_parent/replies"),
        scope(target_key="post:post_synthetic_parent"),
    ]

    decisions = [
        begin_idempotent_request(
            db_session,
            request_scope,
            "same-client-request-id",
            fingerprint,
            settings=settings,
            now=NOW,
        )
        for request_scope in scopes
    ]

    assert [decision.outcome for decision in decisions] == ["started"] * 4
    assert db_session.scalar(select(func.count(IdempotencyRecord.id))) == 4


def test_expired_records_are_pruned_and_key_can_be_reused(db_session: Session) -> None:
    settings = idem_settings(v2_idempotency_ttl_seconds=1)
    request_scope = scope()
    first_fingerprint = safe_request_fingerprint(
        operation_class="create_post",
        body={"text": "Synthetic first request."},
        allowed_fields={"text"},
    )
    second_fingerprint = safe_request_fingerprint(
        operation_class="create_post",
        body={"text": "Synthetic second request after expiry."},
        allowed_fields={"text"},
    )

    first = begin_idempotent_request(
        db_session,
        request_scope,
        "expires-001",
        first_fingerprint,
        settings=settings,
        now=NOW,
    )
    assert first.outcome == "started"

    second = begin_idempotent_request(
        db_session,
        request_scope,
        "expires-001",
        second_fingerprint,
        settings=settings,
        now=NOW + timedelta(seconds=2),
    )

    assert second.outcome == "started"
    assert db_session.scalar(select(func.count(IdempotencyRecord.id))) == 1


def test_fixture_reset_clears_idempotency_records(
    client: TestClient,
    db_session: Session,
    harness_headers: dict[str, str],
) -> None:
    settings = idem_settings()
    decision = begin_idempotent_request(
        db_session,
        scope(),
        "reset-clears-001",
        safe_request_fingerprint(
            operation_class="create_post",
            body={"text": "Synthetic request cleared by fixture reset."},
            allowed_fields={"text"},
        ),
        settings=settings,
        now=NOW,
    )
    assert decision.outcome == "started"
    assert db_session.scalar(select(func.count(IdempotencyRecord.id))) == 1

    response = client.post("/fixtures/reset", headers=harness_headers)

    assert response.status_code == 200
    assert db_session.scalar(select(func.count(IdempotencyRecord.id))) == 0
