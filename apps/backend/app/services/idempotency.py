import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.idempotency import IdempotencyRecord

IdempotencyOutcome = Literal["started", "replay", "conflict", "in_flight"]

PROTECTED_FIELD_NAMES = {
    "authorization",
    "headers",
    "headers_json",
    "raw_body",
    "metadata_json",
    "token",
    "token_hash",
    "access_token",
    "refresh_token",
}


@dataclass(frozen=True)
class IdempotencyScope:
    actor_key: str
    route_key: str
    target_key: str
    operation_class: str


@dataclass(frozen=True)
class IdempotencyDecision:
    outcome: IdempotencyOutcome
    record_id: str | None = None
    status_code: int | None = None
    response_json: dict[str, Any] | None = None
    result_reference: str | None = None


def normalize_client_request_id(
    client_request_id: str,
    *,
    settings: Settings | None = None,
) -> str:
    resolved_settings = settings or get_settings()
    normalized = client_request_id.strip()
    if not normalized or len(normalized) > resolved_settings.v2_client_request_id_max_length:
        raise HTTPException(status_code=400, detail="Invalid client_request_id")
    return normalized


def safe_request_fingerprint(
    *,
    operation_class: str,
    body: dict[str, Any],
    allowed_fields: set[str],
) -> str:
    safe_fields = {
        key: body[key]
        for key in sorted(allowed_fields)
        if key in body and key.lower() not in PROTECTED_FIELD_NAMES
    }
    canonical = _canonical_json(
        {
            "operation_class": operation_class,
            "body": safe_fields,
        }
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def begin_idempotent_request(
    db: Session,
    scope: IdempotencyScope,
    client_request_id: str,
    request_fingerprint_hash: str,
    *,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> IdempotencyDecision:
    resolved_settings = settings or get_settings()
    current_time = _as_utc(now or datetime.now(UTC))
    normalized_client_request_id = normalize_client_request_id(
        client_request_id,
        settings=resolved_settings,
    )
    _prune_expired_records(db, current_time)

    existing = _get_record(db, scope, normalized_client_request_id)
    if existing is not None:
        if _as_utc(existing.expires_at) <= current_time:
            db.delete(existing)
            db.commit()
        else:
            return _decision_for_existing(existing, request_fingerprint_hash)

    record = IdempotencyRecord(
        id=_record_id(scope, normalized_client_request_id),
        actor_key=scope.actor_key,
        operation_class=scope.operation_class,
        route_key=scope.route_key,
        target_key=scope.target_key,
        client_request_id=normalized_client_request_id,
        scope_hash=_scope_hash(scope),
        request_fingerprint_hash=request_fingerprint_hash,
        state="in_flight",
        expires_at=current_time + timedelta(seconds=resolved_settings.v2_idempotency_ttl_seconds),
    )
    db.add(record)
    try:
        db.commit()
        return IdempotencyDecision(outcome="started", record_id=record.id)
    except IntegrityError:
        db.rollback()

    existing = _get_record(db, scope, normalized_client_request_id)
    if existing is None:
        return begin_idempotent_request(
            db,
            scope,
            normalized_client_request_id,
            request_fingerprint_hash,
            settings=resolved_settings,
            now=current_time,
        )
    if _as_utc(existing.expires_at) <= current_time:
        db.delete(existing)
        db.commit()
        return begin_idempotent_request(
            db,
            scope,
            normalized_client_request_id,
            request_fingerprint_hash,
            settings=resolved_settings,
            now=current_time,
        )
    return _decision_for_existing(existing, request_fingerprint_hash)


def record_idempotency_success(
    db: Session,
    record_id: str,
    *,
    status_code: int,
    response_json: dict[str, Any],
    result_reference: str,
) -> IdempotencyRecord:
    record = db.get(IdempotencyRecord, record_id)
    if record is None:
        raise ValueError("Idempotency record not found")

    record.state = "completed"
    record.result_status_code = status_code
    record.response_json = _sanitize_response_json(response_json)
    record.result_reference = result_reference
    record.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(record)
    return record


def idempotency_conflict_envelope(reason: str) -> dict[str, Any]:
    return {
        "error": {
            "code": "conflict",
            "message": "Conflict",
            "details": {"reason": reason},
        }
    }


def _decision_for_existing(
    record: IdempotencyRecord,
    request_fingerprint_hash: str,
) -> IdempotencyDecision:
    if record.request_fingerprint_hash != request_fingerprint_hash:
        return IdempotencyDecision(
            outcome="conflict",
            record_id=record.id,
            status_code=409,
            response_json=idempotency_conflict_envelope("fingerprint_mismatch"),
            result_reference=record.result_reference,
        )
    if record.state == "completed":
        return IdempotencyDecision(
            outcome="replay",
            record_id=record.id,
            status_code=record.result_status_code,
            response_json=record.response_json,
            result_reference=record.result_reference,
        )
    return IdempotencyDecision(
        outcome="in_flight",
        record_id=record.id,
        status_code=409,
        response_json=idempotency_conflict_envelope("in_flight"),
        result_reference=record.result_reference,
    )


def _get_record(
    db: Session,
    scope: IdempotencyScope,
    client_request_id: str,
) -> IdempotencyRecord | None:
    return db.scalars(
        select(IdempotencyRecord).where(
            IdempotencyRecord.actor_key == scope.actor_key,
            IdempotencyRecord.operation_class == scope.operation_class,
            IdempotencyRecord.route_key == scope.route_key,
            IdempotencyRecord.target_key == scope.target_key,
            IdempotencyRecord.client_request_id == client_request_id,
        )
    ).one_or_none()


def _prune_expired_records(db: Session, now: datetime) -> None:
    db.execute(delete(IdempotencyRecord).where(IdempotencyRecord.expires_at <= now))
    db.commit()


def _record_id(scope: IdempotencyScope, client_request_id: str) -> str:
    digest = hashlib.sha256(
        _canonical_json(
            {
                "scope": _scope_hash(scope),
                "client_request_id": client_request_id,
            }
        ).encode("utf-8")
    ).hexdigest()
    return f"idem_{digest[:32]}"


def _scope_hash(scope: IdempotencyScope) -> str:
    return hashlib.sha256(
        _canonical_json(
            {
                "actor_key": scope.actor_key,
                "operation_class": scope.operation_class,
                "route_key": scope.route_key,
                "target_key": scope.target_key,
            }
        ).encode("utf-8")
    ).hexdigest()


def _sanitize_response_json(value: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, item in value.items():
        if key.lower() in PROTECTED_FIELD_NAMES:
            continue
        if isinstance(item, dict):
            sanitized[key] = _sanitize_response_json(item)
        elif isinstance(item, list):
            sanitized[key] = [
                _sanitize_response_json(element) if isinstance(element, dict) else element
                for element in item
            ]
        else:
            sanitized[key] = item
    return sanitized


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
