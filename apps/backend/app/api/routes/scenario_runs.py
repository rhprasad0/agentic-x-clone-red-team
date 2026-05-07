from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor, get_db_session
from app.core.auth import ActorContext, require_harness
from app.models.event import Event
from app.models.finding import Finding
from app.models.scenario_run import ScenarioRun
from app.services.read_models import (
    event_payload,
    finding_payload,
    get_scenario_run_by_id,
    scenario_run_payload,
)

router = APIRouter(tags=["scenario-runs"])
finding_router = APIRouter(tags=["findings"])


class ScenarioRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1)
    objective: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=1)
    redacted_summary: str = Field(min_length=1)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FindingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: str = Field(min_length=1)
    title: str | None = None
    redacted_evidence_summary: str = Field(min_length=1)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


@router.get("/scenario-runs")
def list_scenario_runs(db: Annotated[Session, Depends(get_db_session)]) -> dict[str, list[dict]]:
    runs = db.scalars(
        select(ScenarioRun).order_by(ScenarioRun.created_at.asc(), ScenarioRun.id.asc())
    ).all()
    return {"items": [scenario_run_payload(run) for run in runs]}


@router.post("/scenario-runs", status_code=status.HTTP_201_CREATED)
def create_scenario_run(
    payload: ScenarioRunCreate,
    actor: Annotated[ActorContext, Depends(get_current_actor)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    require_harness(actor)
    run = ScenarioRun(
        id=f"run_{uuid4().hex}",
        scenario_id=payload.scenario_id,
        status="running",
        objective=payload.objective,
        metadata_json=payload.metadata_json,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return scenario_run_payload(run)


@router.get("/scenario-runs/{run_id}")
def get_scenario_run(run_id: str, db: Annotated[Session, Depends(get_db_session)]) -> dict:
    return scenario_run_payload(get_scenario_run_by_id(db, run_id))


@router.get("/scenario-runs/{run_id}/events")
def list_scenario_run_events(
    run_id: str, db: Annotated[Session, Depends(get_db_session)]
) -> dict[str, list[dict]]:
    get_scenario_run_by_id(db, run_id)
    events = db.scalars(
        select(Event)
        .where(Event.scenario_run_id == run_id)
        .order_by(Event.created_at.asc(), Event.id.asc())
    ).all()
    return {"items": [event_payload(event) for event in events]}


@router.post("/scenario-runs/{run_id}/events", status_code=status.HTTP_201_CREATED)
def create_scenario_run_event(
    run_id: str,
    payload: EventCreate,
    actor: Annotated[ActorContext, Depends(get_current_actor)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    require_harness(actor)
    get_scenario_run_by_id(db, run_id)
    event = Event(
        id=f"event_{uuid4().hex}",
        scenario_run_id=run_id,
        event_type=payload.event_type,
        redacted_summary=payload.redacted_summary,
        metadata_json=payload.metadata_json,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event_payload(event)


@router.get("/scenario-runs/{run_id}/findings")
def list_scenario_run_findings(
    run_id: str, db: Annotated[Session, Depends(get_db_session)]
) -> dict[str, list[dict]]:
    get_scenario_run_by_id(db, run_id)
    findings = db.scalars(
        select(Finding)
        .where(Finding.scenario_run_id == run_id)
        .order_by(Finding.created_at.asc(), Finding.id.asc())
    ).all()
    return {"items": [finding_payload(finding) for finding in findings]}


@router.post("/scenario-runs/{run_id}/findings", status_code=status.HTTP_201_CREATED)
def create_scenario_run_finding(
    run_id: str,
    payload: FindingCreate,
    actor: Annotated[ActorContext, Depends(get_current_actor)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    require_harness(actor)
    get_scenario_run_by_id(db, run_id)
    finding = Finding(
        id=f"finding_{uuid4().hex}",
        scenario_run_id=run_id,
        severity=payload.severity,
        status="open",
        title=payload.title,
        redacted_evidence_summary=payload.redacted_evidence_summary,
        metadata_json=payload.metadata_json,
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding_payload(finding)


@finding_router.get("/findings")
def list_findings(db: Annotated[Session, Depends(get_db_session)]) -> dict[str, list[dict]]:
    findings = db.scalars(
        select(Finding).order_by(Finding.created_at.asc(), Finding.id.asc())
    ).all()
    return {"items": [finding_payload(finding) for finding in findings]}


@finding_router.get("/findings/{finding_id}")
def get_finding(finding_id: str, db: Annotated[Session, Depends(get_db_session)]) -> dict:
    finding = db.scalars(select(Finding).where(Finding.id == finding_id)).one_or_none()
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    return finding_payload(finding)
