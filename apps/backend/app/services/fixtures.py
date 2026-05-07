import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import REPO_ROOT
from app.models.agent import Agent
from app.models.auth_fixture import AuthFixture
from app.models.event import Event
from app.models.finding import Finding
from app.models.post import Post
from app.models.scenario_run import ScenarioRun

FIXTURE_ROOT = REPO_ROOT / "fixtures" / "used_car_world"

FIXTURE_MODELS = {
    "agents": Agent,
    "scenario_runs": ScenarioRun,
    "auth_fixtures": AuthFixture,
    "posts": Post,
    "events": Event,
    "findings": Finding,
}

LOAD_ORDER = ("agents", "scenario_runs", "auth_fixtures", "posts", "events", "findings")
DELETE_ORDER = (Finding, Event, Post, AuthFixture, ScenarioRun, Agent)


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


def _seed_fixture_rows(db: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for fixture_name in LOAD_ORDER:
        model = FIXTURE_MODELS[fixture_name]
        rows = _load_fixture(fixture_name)
        for row in rows:
            db.merge(model(**_normalize_row(row)))
        counts[fixture_name] = len(rows)
    db.commit()
    return counts


def seed_used_car_world(db: Session) -> dict[str, int | str]:
    counts = _seed_fixture_rows(db)
    return {"status": "ok", **counts}


def reset_used_car_world(db: Session) -> dict[str, int | str]:
    for model in DELETE_ORDER:
        db.execute(delete(model))
    db.commit()
    counts = _seed_fixture_rows(db)
    return {"status": "ok", **counts}
