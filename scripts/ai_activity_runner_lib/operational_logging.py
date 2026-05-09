# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TextIO

from .redaction import safe_summary

ALLOWED_EVENT_KEYS = frozenset(
    {
        "action",
        "agent_count",
        "api_retry_count",
        "artifact_path_class",
        "candidate_count",
        "component",
        "created_count",
        "duration_ms",
        "event_class",
        "fallback_to_root_post_count",
        "intent",
        "issue_class",
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
        "run_id",
        "safe_message",
        "safe_synthetic_actor_id",
        "status_code",
        "step",
        "target_class",
        "target_fingerprint",
        "target_ref_class",
        "unique_action_classes",
    }
)

SAFE_CLASS_VALUES = {
    "blocked",
    "client_error",
    "completed",
    "failure",
    "global",
    "https",
    "info",
    "loopback",
    "network_error",
    "none",
    "policy_rejected",
    "redacted",
    "replayed",
    "runner",
    "server_error",
    "signup",
    "silence",
    "skipped",
    "success",
    "timeout",
    "unknown",
    "unsafe",
    "validation_error",
}


def safe_event_payload(payload: Mapping[str, object]) -> dict[str, object]:
    safe: dict[str, object] = {"redaction_status": "redacted"}
    for key, value in payload.items():
        safe_key = str(key)
        if safe_key not in ALLOWED_EVENT_KEYS:
            continue
        safe[safe_key] = _safe_value(safe_key, value)
    return safe


def _safe_value(key: str, value: object) -> object:
    if value is None:
        return None
    if isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        if key == "safe_message":
            return safe_summary(value, max_chars=160)
        if key.endswith("_class") or key in {"outcome_class", "phase", "component", "method", "intent", "action", "event_class", "route_class", "run_id", "target_fingerprint", "safe_synthetic_actor_id", "request_id", "profile_tab", "relationship_action"}:
            cleaned = safe_summary(value, max_chars=120)
            if cleaned == "[REDACTED]":
                return "redacted"
            return cleaned
        return safe_summary(value, max_chars=120)
    return "redacted"


class RunnerOperationalLogger:
    def __init__(self, *, run_id: str, stream: TextIO | None = None, enabled: bool = True) -> None:
        self.run_id = run_id
        self.stream = stream or sys.stderr
        self.enabled = enabled

    def emit(self, event_class: str, **fields: object) -> None:
        if not self.enabled:
            return
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "event_class": event_class,
            "component": "ai_activity_runner",
            "run_id": self.run_id,
        }
        payload.update(fields)
        safe_payload = safe_event_payload(payload)
        print(json.dumps(safe_payload, sort_keys=True), file=self.stream, flush=True)
