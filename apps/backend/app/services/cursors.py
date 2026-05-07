import base64
import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import HTTPException
from sqlalchemy import Select, and_, or_

from app.core.config import Settings, get_settings

CursorDirection = Literal["asc", "desc"]


@dataclass(frozen=True)
class CursorPosition:
    created_at: datetime
    item_id: str


@dataclass(frozen=True)
class CursorScope:
    route_key: str
    actor_key: str
    filters: Mapping[str, Any]
    direction: CursorDirection = "desc"


def normalize_limit(limit: int | None, *, settings: Settings | None = None) -> int:
    resolved_settings = settings or get_settings()
    if limit is None:
        return resolved_settings.v2_cursor_default_limit
    if limit < 1 or limit > resolved_settings.v2_cursor_max_limit:
        raise HTTPException(status_code=400, detail="Invalid limit")
    return limit


def encode_cursor(
    position: CursorPosition,
    scope: CursorScope,
    *,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> str:
    resolved_settings = settings or get_settings()
    issued_at = _as_utc(now or datetime.now(UTC))
    expires_at = issued_at + timedelta(seconds=resolved_settings.v2_cursor_ttl_seconds)
    payload = {
        "v": 1,
        "created_at": _timestamp(position.created_at),
        "id": position.item_id,
        "scope": _scope_hash(scope),
        "direction": scope.direction,
        "exp": int(expires_at.timestamp()),
    }
    payload_bytes = _canonical_json(payload).encode("utf-8")
    envelope = {
        "payload": payload,
        "signature": hmac.new(
            resolved_settings.v2_cursor_signing_key.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest(),
    }
    return base64.urlsafe_b64encode(_canonical_json(envelope).encode("utf-8")).decode(
        "ascii"
    ).rstrip("=")


def decode_cursor(
    cursor: str,
    scope: CursorScope,
    *,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> CursorPosition:
    resolved_settings = settings or get_settings()
    try:
        envelope = json.loads(_urlsafe_b64decode(cursor))
        payload = envelope["payload"]
        signature = envelope["signature"]
        payload_bytes = _canonical_json(payload).encode("utf-8")
        expected = hmac.new(
            resolved_settings.v2_cursor_signing_key.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            _raise_bad_cursor()
        if payload.get("v") != 1:
            _raise_bad_cursor()
        if payload.get("scope") != _scope_hash(scope):
            _raise_bad_cursor()
        if payload.get("direction") != scope.direction:
            _raise_bad_cursor()
        current_time = _as_utc(now or datetime.now(UTC))
        expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=UTC)
        if current_time >= expires_at:
            _raise_bad_cursor()
        return CursorPosition(
            created_at=_parse_timestamp(payload["created_at"]),
            item_id=str(payload["id"]),
        )
    except HTTPException:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        _raise_bad_cursor()


def apply_keyset_pagination(
    statement: Select[tuple[Any]],
    model: Any,
    *,
    position: CursorPosition | None,
    direction: CursorDirection = "desc",
    limit: int,
) -> Select[tuple[Any]]:
    created_at = model.created_at
    item_id = model.id

    if direction == "desc":
        statement = statement.order_by(None).order_by(created_at.desc(), item_id.desc())
        if position is not None:
            statement = statement.where(
                or_(
                    created_at < position.created_at,
                    and_(created_at == position.created_at, item_id < position.item_id),
                )
            )
    elif direction == "asc":
        statement = statement.order_by(None).order_by(created_at.asc(), item_id.asc())
        if position is not None:
            statement = statement.where(
                or_(
                    created_at > position.created_at,
                    and_(created_at == position.created_at, item_id > position.item_id),
                )
            )
    else:
        raise HTTPException(status_code=400, detail="Invalid cursor")

    return statement.limit(limit + 1)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _scope_hash(scope: CursorScope) -> str:
    scope_payload = {
        "route_key": scope.route_key,
        "actor_key": scope.actor_key,
        "filters": dict(scope.filters),
        "direction": scope.direction,
    }
    return hashlib.sha256(_canonical_json(scope_payload).encode("utf-8")).hexdigest()


def _timestamp(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    return _as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _urlsafe_b64decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii")).decode("utf-8")


def _raise_bad_cursor() -> None:
    raise HTTPException(status_code=400, detail="Invalid cursor")
