from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
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


@router.get("/scenario-runs")
def list_scenario_runs(db: Annotated[Session, Depends(get_db_session)]) -> dict[str, list[dict]]:
    runs = db.scalars(
        select(ScenarioRun).order_by(ScenarioRun.created_at.asc(), ScenarioRun.id.asc())
    ).all()
    return {"items": [scenario_run_payload(run) for run in runs]}


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
