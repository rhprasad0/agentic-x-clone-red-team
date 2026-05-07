from __future__ import annotations

import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import Request

from app.core.auth import ActorContext

SECURITY_LOGGER_NAME = "app.security"

SECURITY_EVENT_CLASSES = frozenset(
    {
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
)

SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")


def v2_route_metadata(
    *,
    auth_class: str,
    route_class: str,
    target_object_class: str,
    alias_for: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(endpoint: Callable[..., Any]) -> Callable[..., Any]:
        endpoint.v2_auth_class = auth_class  # type: ignore[attr-defined]
        endpoint.v2_route_class = route_class  # type: ignore[attr-defined]
        endpoint.v2_target_object_class = target_object_class  # type: ignore[attr-defined]
        endpoint.v2_alias_for = alias_for  # type: ignore[attr-defined]
        return endpoint

    return decorator


def ensure_correlation_id(request: Request) -> str:
    correlation_id = getattr(request.state, "correlation_id", None)
    if not isinstance(correlation_id, str) or not correlation_id:
        correlation_id = uuid4().hex
        request.state.correlation_id = correlation_id
    return correlation_id


def emit_security_event(
    request: Request,
    *,
    event_class: str,
    status_code: int,
    outcome_class: str,
    actor: ActorContext | None = None,
    actor_authority_class: str | None = None,
    route_class: str | None = None,
    target_object_class: str | None = None,
) -> None:
    if event_class not in SECURITY_EVENT_CLASSES:
        event_class = "schema_validation_failure"

    endpoint = request.scope.get("endpoint")
    resolved_route_class = route_class or _safe_attr(endpoint, "v2_route_class", "unknown")
    resolved_target_class = target_object_class or _safe_attr(
        endpoint, "v2_target_object_class", "unknown"
    )
    resolved_authority_class = actor_authority_class or _actor_authority_class(actor)
    payload = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "correlation_id": ensure_correlation_id(request),
        "event_class": event_class,
        "route_class": _safe_label(resolved_route_class),
        "method": request.method,
        "actor_authority_class": _safe_label(resolved_authority_class),
        "safe_synthetic_actor_id": _safe_actor_id(actor),
        "target_object_class": _safe_label(resolved_target_class),
        "outcome_class": _safe_label(outcome_class),
        "status_code": status_code,
        "redaction_status": "redacted",
    }
    logger = logging.getLogger(SECURITY_LOGGER_NAME)
    logger.disabled = False
    logger.propagate = True
    logger.info(
        "security_event",
        extra={"security_event": payload},
    )


def _safe_attr(endpoint: Any, attr_name: str, default: str) -> str:
    value = getattr(endpoint, attr_name, default)
    return value if isinstance(value, str) else default


def _safe_label(value: str) -> str:
    return value if SAFE_ID_RE.fullmatch(value) else "redacted"


def _actor_authority_class(actor: ActorContext | None) -> str:
    if actor is None:
        return "unknown"
    return actor.authority_type


def _safe_actor_id(actor: ActorContext | None) -> str | None:
    if actor is None or actor.agent is None:
        return None
    actor_id = actor.agent.id
    return actor_id if SAFE_ID_RE.fullmatch(actor_id) else "redacted"
