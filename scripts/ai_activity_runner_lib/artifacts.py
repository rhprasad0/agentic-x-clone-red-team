# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .redaction import redact_mapping, safe_summary

ISSUE_SCHEMA = "v2-ai-activity-runner.issue.v1"
ACTIVITY_SCHEMA = "v2-ai-activity-runner.activity.v1"
SUMMARY_SCHEMA = "v2-ai-activity-runner.summary.v1"
REGISTRY_SCHEMA = "v2-ai-activity-runner.agent-registry.v1"
_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass
class IssueEvent:
    run_id: str
    severity: str
    issue_class: str
    component: str
    safe_message: str
    agent_handle: str | None = None
    route_class: str | None = None
    redacted: bool = False
    sensitive_fields_removed: list[str] = field(default_factory=list)
    schema_version: str = ISSUE_SCHEMA
    ts: str = field(default_factory=utc_now)


@dataclass
class ActivityEvent:
    run_id: str
    agent_handle: str
    action: str
    route_class: str | None
    target: dict[str, Any]
    outcome: str
    status_code: int | None = None
    redaction: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    schema_version: str = ACTIVITY_SCHEMA
    ts: str = field(default_factory=utc_now)


class ArtifactWriter:
    def __init__(self, output_root: Path | str, run_id: str) -> None:
        if run_id in {".", ".."} or not _SAFE_RUN_ID.fullmatch(run_id) or ".." in run_id:
            raise ValueError("run_id must be a safe slug")
        self.run_id = run_id
        root = Path(output_root)
        candidate = root if root.name == run_id else root / run_id
        resolved_root = root.resolve(strict=False)
        resolved_candidate = candidate.resolve(strict=False)
        try:
            resolved_candidate.relative_to(resolved_root)
        except ValueError as exc:
            raise ValueError("artifact run directory must stay within output root") from exc
        self.run_dir = candidate
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.activity_path = self.run_dir / "activity.jsonl"
        self.issues_path = self.run_dir / "issues.jsonl"
        self.registry_path = self.run_dir / "agents.redacted.jsonl"
        self.summary_path = self.run_dir / "summary.json"
        self.issue_counts: dict[str, int] = {}
        self.action_counts: dict[str, int] = {}

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        safe = redact_mapping(payload)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(safe, sort_keys=True) + "\n")

    def record_issue(self, event: IssueEvent) -> None:
        self.issue_counts[event.issue_class] = self.issue_counts.get(event.issue_class, 0) + 1
        event.safe_message = safe_summary(event.safe_message, 240)
        self._append_jsonl(self.issues_path, asdict(event))

    def safe_record_issue(self, **kwargs: Any) -> None:
        try:
            self.record_issue(IssueEvent(run_id=self.run_id, **kwargs))
        except OSError:
            # Last-resort fail closed: never raise a traceback containing paths from artifact logging.
            pass

    def record_activity(self, event: ActivityEvent) -> None:
        self.action_counts[event.action] = self.action_counts.get(event.action, 0) + 1
        self._append_jsonl(self.activity_path, asdict(event))

    def write_agent_registry(self, agents: list[Any]) -> None:
        for agent in agents:
            payload = agent.redacted_summary() if hasattr(agent, "redacted_summary") else redact_mapping(dict(agent))
            payload["schema_version"] = REGISTRY_SCHEMA
            self._append_jsonl(self.registry_path, payload)

    def write_summary(self, *, config_summary: dict[str, Any], started_at: str, finished_at: str | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        summary = {
            "schema_version": SUMMARY_SCHEMA,
            "run_id": self.run_id,
            "runner_mode": config_summary.get("runner_mode"),
            "agent_count": config_summary.get("agent_count"),
            "signup_mode": config_summary.get("signup_mode"),
            "state_rotation": config_summary.get("state_rotation"),
            "llm_provider_mode": config_summary.get("llm_provider_mode"),
            "api_target_class": config_summary.get("api_target_class"),
            "style_pack": config_summary.get("style_pack"),
            "style_pack_pool": config_summary.get("style_pack_pool"),
            "silliness_level": config_summary.get("silliness_level"),
            "chaos_level": config_summary.get("chaos_level"),
            "started_at": started_at,
            "finished_at": finished_at or utc_now(),
            "actions": self.action_counts,
            "issues": self.issue_counts,
            "redaction": {"artifacts_redacted": True},
        }
        if extra:
            summary.update(extra)
        self.summary_path.write_text(json.dumps(redact_mapping(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return summary
