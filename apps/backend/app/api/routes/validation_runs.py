from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_harness_authority
from app.api.dto import finding_dto, validation_event_dto, validation_run_dto
from app.core.auth import ActorContext
from app.core.security_logging import emit_security_event, v2_route_metadata
from app.models.finding import Finding
from app.models.validation_event import ValidationEvent
from app.models.validation_run import ValidationRun
from app.services.authorization import finding_read, validation_write

router = APIRouter(tags=["validation-runs"])
finding_router = APIRouter(tags=["findings"])
scenario_alias_router = APIRouter(tags=["scenario-runs"])


class ValidationRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1)
    objective: str | None = None


class ValidationEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=1)
    redacted_summary: str = Field(min_length=1)


class FindingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: str = Field(min_length=1)
    title: str | None = None
    redacted_evidence_summary: str = Field(min_length=1)
    affected_route_class: str | None = None
    affected_object_class: str | None = None
    fix_ref: str | None = None
    regression_ref: str | None = None
    residual_risk: str | None = None


def _not_found(message: str) -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)


def _get_validation_run(db: Session, run_id: str) -> ValidationRun:
    run = db.scalars(
        select(ValidationRun).where(
            (ValidationRun.id == run_id) | (ValidationRun.scenario_run_id == run_id)
        )
    ).one_or_none()
    if run is None:
        _not_found("Validation run not found")
    return run


def _list_validation_runs(actor: ActorContext, db: Session) -> dict[str, list[dict]]:
    finding_read(actor)
    runs = db.scalars(
        select(ValidationRun).order_by(ValidationRun.created_at.asc(), ValidationRun.id.asc())
    ).all()
    return {"items": [validation_run_dto(run) for run in runs]}


def _create_validation_run(
    request: Request, payload: ValidationRunCreate, actor: ActorContext, db: Session
) -> dict[str, Any]:
    validation_write(actor)
    run = ValidationRun(
        id=f"validation_run_{uuid4().hex}",
        scenario_run_id=None,
        scenario_id=payload.scenario_id,
        status="running",
        objective=payload.objective,
        metadata_json={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    emit_security_event(
        request,
        event_class="validation_artifact_write",
        status_code=status.HTTP_201_CREATED,
        outcome_class="success",
        actor=actor,
    )
    return validation_run_dto(run)


def _get_validation_run_payload(run_id: str, actor: ActorContext, db: Session) -> dict:
    finding_read(actor)
    return validation_run_dto(_get_validation_run(db, run_id))


def _list_validation_events(
    run_id: str, actor: ActorContext, db: Session
) -> dict[str, list[dict]]:
    finding_read(actor)
    validation_run = _get_validation_run(db, run_id)
    events = db.scalars(
        select(ValidationEvent)
        .where(ValidationEvent.validation_run_id == validation_run.id)
        .order_by(ValidationEvent.created_at.asc(), ValidationEvent.id.asc())
    ).all()
    return {"items": [validation_event_dto(event) for event in events]}


def _create_validation_event(
    request: Request,
    run_id: str,
    payload: ValidationEventCreate,
    actor: ActorContext,
    db: Session,
) -> dict[str, Any]:
    validation_write(actor)
    validation_run = _get_validation_run(db, run_id)
    event = ValidationEvent(
        id=f"validation_event_{uuid4().hex}",
        validation_run_id=validation_run.id,
        event_type=payload.event_type,
        redacted_summary=payload.redacted_summary,
        metadata_json={},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    emit_security_event(
        request,
        event_class="validation_artifact_write",
        status_code=status.HTTP_201_CREATED,
        outcome_class="success",
        actor=actor,
    )
    return validation_event_dto(event)


def _list_validation_findings(
    run_id: str, actor: ActorContext, db: Session
) -> dict[str, list[dict]]:
    finding_read(actor)
    validation_run = _get_validation_run(db, run_id)
    findings = db.scalars(
        select(Finding)
        .where(Finding.validation_run_id == validation_run.id)
        .order_by(Finding.created_at.asc(), Finding.id.asc())
    ).all()
    return {"items": [finding_dto(finding) for finding in findings]}


def _create_validation_finding(
    request: Request,
    run_id: str,
    payload: FindingCreate,
    actor: ActorContext,
    db: Session,
) -> dict[str, Any]:
    validation_write(actor)
    validation_run = _get_validation_run(db, run_id)
    finding = Finding(
        id=f"finding_{uuid4().hex}",
        validation_run_id=validation_run.id,
        severity=payload.severity,
        status="open",
        title=payload.title,
        affected_route_class=payload.affected_route_class,
        affected_object_class=payload.affected_object_class,
        redacted_evidence_summary=payload.redacted_evidence_summary,
        fix_ref=payload.fix_ref,
        regression_ref=payload.regression_ref,
        residual_risk=payload.residual_risk,
        metadata_json={},
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    emit_security_event(
        request,
        event_class="validation_artifact_write",
        status_code=status.HTTP_201_CREATED,
        outcome_class="success",
        actor=actor,
    )
    return finding_dto(finding)


def _list_findings(actor: ActorContext, db: Session) -> dict[str, list[dict]]:
    finding_read(actor)
    findings = db.scalars(
        select(Finding).order_by(Finding.created_at.asc(), Finding.id.asc())
    ).all()
    return {"items": [finding_dto(finding) for finding in findings]}


def _get_finding(finding_id: str, actor: ActorContext, db: Session) -> dict:
    finding_read(actor)
    finding = db.scalars(select(Finding).where(Finding.id == finding_id)).one_or_none()
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    return finding_dto(finding)


@router.get("/validation-runs")
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="validation_run",
)
def list_validation_runs(
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, list[dict]]:
    return _list_validation_runs(actor, db)


@router.post("/validation-runs", status_code=status.HTTP_201_CREATED)
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="validation_run",
)
def create_validation_run(
    request: Request,
    payload: ValidationRunCreate,
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    return _create_validation_run(request, payload, actor, db)


@router.get("/validation-runs/{run_id}")
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="validation_run",
)
def get_validation_run(
    run_id: str,
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict:
    return _get_validation_run_payload(run_id, actor, db)


@router.get("/validation-runs/{run_id}/events")
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="validation_event",
)
def list_validation_run_events(
    run_id: str,
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, list[dict]]:
    return _list_validation_events(run_id, actor, db)


@router.post("/validation-runs/{run_id}/events", status_code=status.HTTP_201_CREATED)
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="validation_event",
)
def create_validation_run_event(
    request: Request,
    run_id: str,
    payload: ValidationEventCreate,
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    return _create_validation_event(request, run_id, payload, actor, db)


@router.get("/validation-runs/{run_id}/findings")
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="finding",
)
def list_validation_run_findings(
    run_id: str,
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, list[dict]]:
    return _list_validation_findings(run_id, actor, db)


@router.post("/validation-runs/{run_id}/findings", status_code=status.HTTP_201_CREATED)
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="finding",
)
def create_validation_run_finding(
    request: Request,
    run_id: str,
    payload: FindingCreate,
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    return _create_validation_finding(request, run_id, payload, actor, db)


@finding_router.get("/findings")
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="finding",
)
def list_findings(
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, list[dict]]:
    return _list_findings(actor, db)


@finding_router.get("/findings/{finding_id}")
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="finding",
)
def get_finding(
    finding_id: str,
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict:
    return _get_finding(finding_id, actor, db)


@scenario_alias_router.get("/scenario-runs", include_in_schema=False)
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="validation_run",
    alias_for="/validation-runs",
)
def list_scenario_runs_alias(
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, list[dict]]:
    return _list_validation_runs(actor, db)


@scenario_alias_router.post(
    "/scenario-runs", status_code=status.HTTP_201_CREATED, include_in_schema=False
)
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="validation_run",
    alias_for="/validation-runs",
)
def create_scenario_run_alias(
    request: Request,
    payload: ValidationRunCreate,
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    return _create_validation_run(request, payload, actor, db)


@scenario_alias_router.get("/scenario-runs/{run_id}", include_in_schema=False)
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="validation_run",
    alias_for="/validation-runs/{run_id}",
)
def get_scenario_run_alias(
    run_id: str,
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict:
    return _get_validation_run_payload(run_id, actor, db)


@scenario_alias_router.get("/scenario-runs/{run_id}/events", include_in_schema=False)
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="validation_event",
    alias_for="/validation-runs/{run_id}/events",
)
def list_scenario_run_events_alias(
    run_id: str,
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, list[dict]]:
    return _list_validation_events(run_id, actor, db)


@scenario_alias_router.post(
    "/scenario-runs/{run_id}/events", status_code=status.HTTP_201_CREATED, include_in_schema=False
)
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="validation_event",
    alias_for="/validation-runs/{run_id}/events",
)
def create_scenario_run_event_alias(
    request: Request,
    run_id: str,
    payload: ValidationEventCreate,
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    return _create_validation_event(request, run_id, payload, actor, db)


@scenario_alias_router.get("/scenario-runs/{run_id}/findings", include_in_schema=False)
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="finding",
    alias_for="/validation-runs/{run_id}/findings",
)
def list_scenario_run_findings_alias(
    run_id: str,
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, list[dict]]:
    return _list_validation_findings(run_id, actor, db)


@scenario_alias_router.post(
    "/scenario-runs/{run_id}/findings",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@v2_route_metadata(
    auth_class="harness",
    route_class="validation_artifact",
    target_object_class="finding",
    alias_for="/validation-runs/{run_id}/findings",
)
def create_scenario_run_finding_alias(
    request: Request,
    run_id: str,
    payload: FindingCreate,
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    return _create_validation_finding(request, run_id, payload, actor, db)
