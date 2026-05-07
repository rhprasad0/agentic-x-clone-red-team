from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.finding import Finding
from app.models.validation_event import ValidationEvent
from app.models.validation_run import ValidationRun
from app.services.public_evidence_allowlists import (
    PUBLIC_EVIDENCE_GENERATED_AT,
    PUBLIC_EVIDENCE_REDACTION_MODE,
    PUBLIC_EVIDENCE_SCOPE,
    PUBLIC_EVIDENCE_TOP_LEVEL_FIELDS,
    PUBLIC_FINDING_FIELDS,
    PUBLIC_VALIDATION_EVENT_FIELDS,
    PUBLIC_VALIDATION_RUN_FIELDS,
    ordered_public_payload,
)
from app.services.read_models import timestamp


def public_validation_run_payload(
    run: ValidationRun,
    events: list[ValidationEvent],
    findings: list[Finding],
) -> dict[str, Any]:
    """Allowlisted public payload for one V2 validation run."""

    payload = {
        "id": run.id,
        "scenario_id": run.scenario_id,
        "status": run.status,
        "objective": run.objective,
        "created_at": timestamp(run.created_at),
        "events": [public_validation_event_payload(event) for event in events],
        "findings": [public_finding_payload(finding) for finding in findings],
    }
    return ordered_public_payload(payload, PUBLIC_VALIDATION_RUN_FIELDS)


def public_validation_event_payload(event: ValidationEvent) -> dict[str, Any]:
    """Allowlisted public payload for one V2 validation event."""

    payload = {
        "id": event.id,
        "validation_run_id": event.validation_run_id,
        "event_type": event.event_type,
        "redacted_summary": event.redacted_summary,
        "created_at": timestamp(event.created_at),
    }
    return ordered_public_payload(payload, PUBLIC_VALIDATION_EVENT_FIELDS)


def public_finding_payload(finding: Finding) -> dict[str, Any]:
    """Allowlisted public payload for one V2 validation finding."""

    payload = {
        "id": finding.id,
        "validation_run_id": finding.validation_run_id,
        "scenario_run_id": finding.scenario_run_id,
        "severity": finding.severity,
        "status": finding.status,
        "title": finding.title,
        "affected_route_class": finding.affected_route_class,
        "affected_object_class": finding.affected_object_class,
        "redacted_evidence_summary": finding.redacted_evidence_summary,
        "fix_ref": finding.fix_ref,
        "regression_ref": finding.regression_ref,
        "residual_risk": finding.residual_risk,
        "created_at": timestamp(finding.created_at),
    }
    return ordered_public_payload(payload, PUBLIC_FINDING_FIELDS)


def build_public_evidence_payload(
    validation_runs: list[dict[str, Any]],
    *,
    redaction_mode: str = PUBLIC_EVIDENCE_REDACTION_MODE,
) -> dict[str, Any]:
    """Build the deterministic top-level public evidence manifest."""

    payload = {
        "export_type": "public_evidence",
        "scope": PUBLIC_EVIDENCE_SCOPE,
        "redaction_mode": redaction_mode,
        "generated_at": PUBLIC_EVIDENCE_GENERATED_AT,
        "safety_notes": [
            "Synthetic used-car fixture world only.",
            "V2 validation-run, event, and finding class fields only; raw traces "
            "and bearer credentials are intentionally excluded.",
        ],
        "validation_runs": validation_runs,
    }
    return ordered_public_payload(payload, PUBLIC_EVIDENCE_TOP_LEVEL_FIELDS)


def build_public_evidence_export(
    db: Session,
    *,
    validation_run_ids: list[str] | None = None,
    redaction_mode: str = PUBLIC_EVIDENCE_REDACTION_MODE,
) -> dict[str, Any]:
    """Build a deterministic public-safe V2 validation evidence export."""

    statement = select(ValidationRun).order_by(
        ValidationRun.created_at.asc(), ValidationRun.id.asc()
    )
    if validation_run_ids is not None:
        statement = statement.where(ValidationRun.id.in_(validation_run_ids))
    runs = db.scalars(statement).all()

    exported_runs: list[dict[str, Any]] = []
    for run in runs:
        events = db.scalars(
            select(ValidationEvent)
            .where(ValidationEvent.validation_run_id == run.id)
            .order_by(ValidationEvent.created_at.asc(), ValidationEvent.id.asc())
        ).all()
        findings = db.scalars(
            select(Finding)
            .where(Finding.validation_run_id == run.id)
            .order_by(Finding.created_at.asc(), Finding.id.asc())
        ).all()
        exported_runs.append(public_validation_run_payload(run, events, findings))

    return build_public_evidence_payload(exported_runs, redaction_mode=redaction_mode)
