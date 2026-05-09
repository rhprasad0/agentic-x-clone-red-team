from __future__ import annotations

import json
import logging
import re
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from app.core.auth import ActorContext

APP_LOGGER_NAME = "app.operational"
OPERATIONAL_LOGGER_NAME = APP_LOGGER_NAME
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.:/?&=-]{1,240}$")
PRIVATE_PATH_RE = re.compile(r"/(home|Users|var/private|tmp)/[^\s\"']+", re.IGNORECASE)
PRIVATE_URL_RE = re.compile(
    r"https?://(?:127\.0\.0\.1|localhost|10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)"
    r"[^\s\"']*",
    re.IGNORECASE,
)
SENSITIVE_FIELD_RE = re.compile(
    r"(authorization|bearer|token|secret|password|hash|raw|trace|body|header|env|private|"
    r"sql|prompt|response)",
    re.IGNORECASE,
)
SAFE_TEXT_RE = re.compile(r"^[A-Za-z0-9_.:/?&=, -]{0,240}$")

ALLOWED_LOG_KEYS = frozenset(
    {
        "action",
        "actor_authority_class",
        "agent_count",
        "api_retry_count",
        "artifact_path",
        "artifact_path_class",
        "cache_control_class",
        "candidate_count",
        "candidate_ref_class",
        "client_request_id",
        "component",
        "correlation_id",
        "created_count",
        "cursor_class",
        "duration_ms",
        "error_class",
        "event_class",
        "exception_class",
        "fallback_to_root_post_count",
        "has_more",
        "intent",
        "issue_class",
        "item_count",
        "limit",
        "method",
        "outcome_class",
        "phase",
        "post_candidate_count",
        "profile_tab",
        "proposal_repair_count",
        "redaction_status",
        "relationship_action",
        "request_id",
        "reused_count",
        "route_class",
        "safe_synthetic_actor_id",
        "status_code",
        "target_object_class",
        "target_ref_class",
        "unique_action_classes",
    }
)

_CONFIGURED = False


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        event = getattr(record, "operational_event", None)
        if isinstance(event, Mapping):
            payload["event"] = safe_log_payload(event)
        return json.dumps(payload, sort_keys=True)


def configure_logging(settings: object | None = None) -> None:
    del settings
    global _CONFIGURED
    logger = logging.getLogger(APP_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.disabled = False
    logger.propagate = True
    if not any(getattr(handler, "_xclone_operational", False) for handler in logger.handlers):
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JsonLogFormatter())
        handler._xclone_operational = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    _CONFIGURED = True


def safe_log_payload(payload: Mapping[str, object]) -> dict[str, object]:
    safe: dict[str, object] = {"redaction_status": "redacted"}
    for key, value in payload.items():
        safe_key = str(key)
        if safe_key not in ALLOWED_LOG_KEYS:
            continue
        safe[safe_key] = _safe_value(safe_key, value)
    if "redaction_status" not in safe:
        safe["redaction_status"] = "redacted"
    return safe


def emit_operational_event(
    request: Request | None = None,
    *,
    event_class: str,
    outcome_class: str,
    actor: ActorContext | None = None,
    route_class: str | None = None,
    target_object_class: str | None = None,
    **fields: object,
) -> None:
    payload: dict[str, object] = {
        "event_class": event_class,
        "outcome_class": outcome_class,
        "redaction_status": "redacted",
    }
    if request is not None:
        payload.update(
            {
                "correlation_id": getattr(request.state, "correlation_id", None),
                "method": request.method,
                "route_class": route_class
                or _safe_attr(request.scope.get("endpoint"), "v2_route_class", "unknown"),
                "target_object_class": target_object_class
                or _safe_attr(request.scope.get("endpoint"), "v2_target_object_class", "unknown"),
            }
        )
    elif route_class:
        payload["route_class"] = route_class
    if target_object_class and "target_object_class" not in payload:
        payload["target_object_class"] = target_object_class
    if actor is not None:
        payload["actor_authority_class"] = actor.authority_type
        if actor.agent is not None:
            payload["safe_synthetic_actor_id"] = actor.agent.id
    payload.update(fields)
    logging.getLogger(APP_LOGGER_NAME).info(
        "operational_event",
        extra={"operational_event": safe_log_payload(payload)},
    )


def _safe_attr(endpoint: Any, attr_name: str, default: str) -> str:
    value = getattr(endpoint, attr_name, default)
    return value if isinstance(value, str) else default


def _safe_value(key: str, value: object) -> object:
    if value is None:
        return None
    if isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        if SENSITIVE_FIELD_RE.search(key):
            return _safe_class_label(value)
        if PRIVATE_PATH_RE.search(value) or PRIVATE_URL_RE.search(value):
            return "redacted"
        if not SAFE_TEXT_RE.fullmatch(value):
            return "redacted"
        return value[:240]
    return "redacted"


def _safe_class_label(value: str) -> str:
    if (
        value
        and SAFE_ID_RE.fullmatch(value)
        and not PRIVATE_PATH_RE.search(value)
        and not PRIVATE_URL_RE.search(value)
    ):
        return value[:240]
    return "redacted"
