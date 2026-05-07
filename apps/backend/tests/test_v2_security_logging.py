import json
import logging

from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import AUTHORITY_SYNTHETIC_AGENT, hash_bearer_token
from app.core.security_logging import SECURITY_EVENT_CLASSES
from app.models.auth_token_hash import AuthTokenHash
from app.services.tokens import diagnostic_token_prefix

EXPECTED_SECURITY_EVENT_CLASSES = {
    "auth_missing",
    "auth_invalid",
    "auth_disabled",
    "wrong_authority",
    "object_authorization_denied",
    "protected_field_rejection",
    "schema_validation_failure",
    "cursor_tamper_or_expiry",
    "idempotency_conflict",
    "guardrail_limit",
    "fixture_invocation",
    "validation_artifact_write",
    "export_invocation",
}

SAFE_LOG_KEYS = {
    "timestamp",
    "correlation_id",
    "event_class",
    "route_class",
    "method",
    "actor_authority_class",
    "safe_synthetic_actor_id",
    "target_object_class",
    "outcome_class",
    "status_code",
    "redaction_status",
}


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def security_events(caplog) -> list[dict[str, object]]:
    return [
        record.security_event
        for record in caplog.records
        if hasattr(record, "security_event")
    ]


def assert_safe_security_events(events: list[dict[str, object]]) -> None:
    assert events
    for event in events:
        assert set(event) == SAFE_LOG_KEYS
        assert event["event_class"] in SECURITY_EVENT_CLASSES
        assert event["redaction_status"] == "redacted"
        assert isinstance(event["timestamp"], str)
        assert isinstance(event["correlation_id"], str)
        assert event["correlation_id"]
        assert event["method"] in {"DELETE", "GET", "POST"}
        assert isinstance(event["status_code"], int)


def assert_forbidden_markers_absent(
    *,
    caplog,
    responses,
    extra_markers: set[str],
) -> None:
    private_path_marker = "/" + "home" + "/" + "synthetic" + "/" + "repo"
    forbidden_markers = {
        "Authorization",
        "Bearer ",
        "token_hash_marker_placeholder",
        "raw_body_marker_placeholder",
        "stack_trace_marker_placeholder",
        "SELECT * FROM auth_token_hashes",
        "dependency.internal.example.com",
        "ENV_VALUE_MARKER_PLACEHOLDER",
        private_path_marker,
        *extra_markers,
    }
    log_text = caplog.text + json.dumps(security_events(caplog), sort_keys=True)
    response_text = "\n".join(response.text for response in responses)

    for marker in forbidden_markers:
        assert marker not in log_text
        assert marker not in response_text


def test_security_logging_event_class_registry_is_complete() -> None:
    assert EXPECTED_SECURITY_EVENT_CLASSES <= SECURITY_EVENT_CLASSES


def test_auth_validation_cursor_and_idempotency_failures_log_redacted_metadata_only(
    client: TestClient,
    db_session: Session,
    seeded_world: dict,
    caplog,
) -> None:
    del seeded_world
    caplog.set_level(logging.INFO, logger="app.security")
    disabled_token = "disabled_security_log_token_placeholder"
    invalid_bearer_marker = "bearer_value_must_not_appear_placeholder"

    db_session.add(
        AuthTokenHash(
            id="auth_disabled_security_logging",
            label="disabled_security_logging",
            token_hash=hash_bearer_token(disabled_token),
            token_prefix=diagnostic_token_prefix(disabled_token),
            authority_type=AUTHORITY_SYNTHETIC_AGENT,
            agent_id="agent_alex",
            enabled=False,
        )
    )
    db_session.commit()

    missing = client.post("/posts", json={"text": "Synthetic missing auth log note."})
    invalid = client.post(
        "/posts",
        headers={"Authorization": f"Bearer {invalid_bearer_marker}"},
        json={"text": "Synthetic invalid auth log note."},
    )
    disabled = client.post(
        "/posts",
        headers={"Authorization": f"Bearer {disabled_token}"},
        json={"text": "Synthetic disabled auth log note."},
    )
    wrong_authority = client.post(
        "/fixtures/reset", headers=auth_headers("agent_alex_fixture")
    )
    protected_field = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={
            "text": "Synthetic protected-field log note.",
            "token_hash": "token_hash_marker_placeholder",
            "raw_body": "raw_body_marker_placeholder",
            "stack_trace": "stack_trace_marker_placeholder",
            "sql_fragment": "SELECT * FROM auth_token_hashes",
            "dependency_url": "https://dependency.internal.example.com/api",
            "environment_value": "ENV_VALUE_MARKER_PLACEHOLDER",
            "private_path": "/" + "home" + "/" + "synthetic" + "/" + "repo",
        },
    )
    cursor = client.get(
        "/timelines/public?cursor=tampered_cursor_marker_placeholder"
    )
    first_post = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={
            "text": "Synthetic idempotent log note one.",
            "client_request_id": "security-log-idempotency",
        },
    )
    idempotency_conflict = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={
            "text": "Synthetic idempotent log note two.",
            "client_request_id": "security-log-idempotency",
        },
    )

    responses = [
        missing,
        invalid,
        disabled,
        wrong_authority,
        protected_field,
        cursor,
        first_post,
        idempotency_conflict,
    ]
    assert [response.status_code for response in responses] == [
        401,
        401,
        401,
        403,
        422,
        400,
        201,
        409,
    ]

    events = security_events(caplog)
    assert_safe_security_events(events)
    event_classes = {event["event_class"] for event in events}
    assert {
        "auth_missing",
        "auth_invalid",
        "auth_disabled",
        "wrong_authority",
        "protected_field_rejection",
        "schema_validation_failure",
        "cursor_tamper_or_expiry",
        "idempotency_conflict",
    } <= event_classes
    assert_forbidden_markers_absent(
        caplog=caplog,
        responses=responses,
        extra_markers={invalid_bearer_marker, disabled_token},
    )


def test_harness_fixture_validation_and_export_successes_log_redacted_metadata_only(
    client: TestClient,
    seeded_world: dict,
    harness_headers: dict[str, str],
    caplog,
) -> None:
    del seeded_world
    caplog.set_level(logging.INFO, logger="app.security")

    fixture = client.post("/fixtures/reset", headers=harness_headers)
    run = client.post(
        "/validation-runs",
        headers=harness_headers,
        json={
            "scenario_id": "RT-V2-LOGGING",
            "objective": "Synthetic validation logging check.",
        },
    )
    event = client.post(
        f"/validation-runs/{run.json()['id']}/events",
        headers=harness_headers,
        json={
            "event_type": "logging_check",
            "redacted_summary": "Synthetic validation logging event.",
        },
    )
    finding = client.post(
        f"/validation-runs/{run.json()['id']}/findings",
        headers=harness_headers,
        json={
            "severity": "low",
            "redacted_evidence_summary": "Synthetic validation logging finding.",
        },
    )
    export = client.post("/exports/public-evidence", headers=harness_headers)

    responses = [fixture, run, event, finding, export]
    assert [response.status_code for response in responses] == [200, 201, 201, 201, 200]

    events = security_events(caplog)
    assert_safe_security_events(events)
    event_classes = {event["event_class"] for event in events}
    assert {
        "fixture_invocation",
        "validation_artifact_write",
        "export_invocation",
    } <= event_classes
    assert_forbidden_markers_absent(caplog=caplog, responses=responses, extra_markers=set())
