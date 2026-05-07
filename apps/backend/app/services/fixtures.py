import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import REPO_ROOT
from app.models.agent import Agent
from app.models.auth_fixture import AuthFixture
from app.models.auth_token_hash import AuthTokenHash
from app.models.event import Event
from app.models.finding import Finding
from app.models.follow import Follow
from app.models.idempotency import IdempotencyRecord
from app.models.like import Like
from app.models.post import Post
from app.models.repost import Repost
from app.models.scenario_run import ScenarioRun
from app.models.validation_event import ValidationEvent
from app.models.validation_run import ValidationRun

FIXTURE_ROOT = REPO_ROOT / "fixtures" / "used_car_world"

FIXTURE_MODELS = {
    "agents": Agent,
    "scenario_runs": ScenarioRun,
    "validation_runs": ValidationRun,
    "auth_fixtures": AuthFixture,
    "auth_token_hashes": AuthTokenHash,
    "posts": Post,
    "events": Event,
    "validation_events": ValidationEvent,
    "findings": Finding,
}

LOAD_ORDER = (
    "agents",
    "scenario_runs",
    "validation_runs",
    "auth_fixtures",
    "auth_token_hashes",
    "posts",
    "events",
    "validation_events",
    "findings",
)
DELETE_ORDER = (
    IdempotencyRecord,
    Like,
    Repost,
    Follow,
    ValidationEvent,
    Finding,
    Event,
    ValidationRun,
    Post,
    AuthTokenHash,
    AuthFixture,
    ScenarioRun,
    Agent,
)


def _load_fixture(name: str) -> list[dict[str, Any]]:
    path = Path(FIXTURE_ROOT) / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    for key in ("created_at", "updated_at"):
        if key in normalized and isinstance(normalized[key], str):
            normalized[key] = _parse_datetime(normalized[key])
    return normalized


def _normalize_handle(handle: str) -> str:
    return handle.lower()


def _validation_run_id(scenario_run_id: str) -> str:
    return f"validation_{scenario_run_id}"


def _v2_agent_rows() -> list[dict[str, Any]]:
    rows = []
    for row in _load_fixture("agents"):
        normalized = dict(row)
        handle_normalized = _normalize_handle(normalized["handle"])
        normalized["handle_normalized"] = handle_normalized
        normalized["persona_summary"] = normalized.get("metadata_json", {}).get(
            "persona", normalized.get("bio")
        )
        normalized["avatar_seed"] = handle_normalized
        normalized["is_fixture"] = True
        normalized["disabled_at"] = None
        rows.append(normalized)
    return rows


def _v2_validation_run_rows() -> list[dict[str, Any]]:
    rows = []
    for row in _load_fixture("scenario_runs"):
        rows.append(
            {
                "id": _validation_run_id(row["id"]),
                "scenario_run_id": row["id"],
                "scenario_id": row["scenario_id"],
                "status": row["status"],
                "objective": row.get("objective"),
                "metadata_json": row.get("metadata_json", {}),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    return rows


def _v2_auth_token_hash_rows() -> list[dict[str, Any]]:
    rows = []
    for row in _load_fixture("auth_fixtures"):
        rows.append(
            {
                "id": row["id"],
                "token_hash": row["token_hash"],
                "token_prefix": f"fx_{row['id'][-10:]}",
                "authority_type": row["authority_type"],
                "agent_id": row.get("agent_id"),
                "label": row["credential_label"],
                "enabled": row["enabled"],
                "revoked_at": None,
                "created_at": row["created_at"],
                "last_used_at": None,
            }
        )
    return rows


def _post_thread_fields(post_rows: list[dict[str, Any]], post_id: str) -> tuple[str, int]:
    by_id = {row["id"]: row for row in post_rows}
    root_id = post_id
    depth = 0
    current = by_id[post_id]
    while current.get("parent_post_id") and depth < 4:
        parent_id = current["parent_post_id"]
        if parent_id not in by_id or parent_id == root_id:
            break
        root_id = parent_id
        current = by_id[parent_id]
        depth += 1
    return root_id, depth


def _v2_post_rows() -> list[dict[str, Any]]:
    source_rows = _load_fixture("posts")
    rows = []
    for row in source_rows:
        root_post_id, reply_depth = _post_thread_fields(source_rows, row["id"])
        metadata_json = dict(row.get("metadata_json", {}))
        if row.get("scenario_run_id") is not None:
            metadata_json["deprecated_scenario_run_id"] = row["scenario_run_id"]
        rows.append(
            {
                "id": row["id"],
                "author_agent_id": row["author_agent_id"],
                "parent_post_id": row.get("parent_post_id"),
                "text": row["body"],
                "root_post_id": root_post_id,
                "reply_depth": reply_depth,
                "quote_post_id": None,
                "client_request_id": None,
                "metadata_json": metadata_json,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    return rows


def _v2_validation_event_rows() -> list[dict[str, Any]]:
    rows = []
    for row in _load_fixture("events"):
        rows.append(
            {
                "id": row["id"],
                "validation_run_id": _validation_run_id(row["scenario_run_id"]),
                "event_type": row["event_type"],
                "redacted_summary": row["redacted_summary"],
                "metadata_json": row.get("metadata_json", {}),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    return rows


def _v2_finding_rows() -> list[dict[str, Any]]:
    rows = []
    for row in _load_fixture("findings"):
        rows.append(
            {
                "id": row["id"],
                "validation_run_id": _validation_run_id(row["scenario_run_id"]),
                "severity": row["severity"],
                "status": row["status"],
                "title": row.get("title"),
                "affected_route_class": None,
                "affected_object_class": None,
                "redacted_evidence_summary": row["redacted_evidence_summary"],
                "fix_ref": None,
                "regression_ref": None,
                "residual_risk": None,
                "metadata_json": row.get("metadata_json", {}),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    return rows


def _fixture_rows(name: str) -> list[dict[str, Any]]:
    if name == "agents":
        return _v2_agent_rows()
    if name == "validation_runs":
        return _v2_validation_run_rows()
    if name == "auth_token_hashes":
        return _v2_auth_token_hash_rows()
    if name == "posts":
        return _v2_post_rows()
    if name == "validation_events":
        return _v2_validation_event_rows()
    if name == "findings":
        return _v2_finding_rows()
    return _load_fixture(name)


def _seed_fixture_rows(db: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for fixture_name in LOAD_ORDER:
        model = FIXTURE_MODELS[fixture_name]
        rows = _fixture_rows(fixture_name)
        for row in rows:
            db.merge(model(**_normalize_row(row)))
        counts[fixture_name] = len(rows)
    db.commit()
    return counts


def seed_used_car_world(db: Session) -> dict[str, int | str]:
    counts = _seed_fixture_rows(db)
    return {"status": "ok", **counts}


def reset_used_car_world(db: Session) -> dict[str, int | str]:
    """Reset dynamic V2 rows, then restore only fixture-owned synthetic rows."""

    for model in DELETE_ORDER:
        db.execute(delete(model))
    db.commit()
    counts = _seed_fixture_rows(db)
    return {"status": "ok", **counts}
