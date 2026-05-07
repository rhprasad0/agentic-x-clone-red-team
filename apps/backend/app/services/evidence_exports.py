from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.finding import Finding
from app.models.scenario_run import ScenarioRun
from app.models.validation_run import ValidationRun
from app.services.read_models import timestamp


def _run_export(run: ScenarioRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "scenario_id": run.scenario_id,
        "status": run.status,
        "objective": run.objective,
        "created_at": timestamp(run.created_at),
    }


def _event_export(event: Event) -> dict[str, Any]:
    return {
        "id": event.id,
        "scenario_run_id": event.scenario_run_id,
        "event_type": event.event_type,
        "redacted_summary": event.redacted_summary,
        "created_at": timestamp(event.created_at),
    }


def _finding_export(finding: Finding) -> dict[str, Any]:
    return {
        "id": finding.id,
        "scenario_run_id": finding.scenario_run_id,
        "severity": finding.severity,
        "status": finding.status,
        "title": finding.title,
        "redacted_evidence_summary": finding.redacted_evidence_summary,
        "created_at": timestamp(finding.created_at),
    }


def build_public_evidence_export(db: Session) -> dict[str, Any]:
    """Build a public-safe synthetic evidence summary without raw traces or credentials."""

    runs = db.scalars(
        select(ScenarioRun).order_by(ScenarioRun.created_at.asc(), ScenarioRun.id.asc())
    ).all()
    exported_runs: list[dict[str, Any]] = []
    for run in runs:
        events = db.scalars(
            select(Event)
            .where(Event.scenario_run_id == run.id)
            .order_by(Event.created_at.asc(), Event.id.asc())
        ).all()
        findings = db.scalars(
            select(Finding)
            .join(ValidationRun)
            .where(ValidationRun.scenario_run_id == run.id)
            .order_by(Finding.created_at.asc(), Finding.id.asc())
        ).all()
        exported_runs.append(
            {
                **_run_export(run),
                "events": [_event_export(event) for event in events],
                "findings": [_finding_export(finding) for finding in findings],
            }
        )

    return {
        "export_type": "public_evidence",
        "redaction": "synthetic_redacted",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "safety_notes": [
            "Synthetic fixtures only.",
            "Redacted summaries only; raw traces and bearer credentials are "
            "intentionally excluded.",
        ],
        "runs": exported_runs,
    }
