#!/usr/bin/env python3
"""Generate a scanner-safe V2 public evidence example from committed fixtures.

The committed fixture directory still carries V1 file names (`scenario_runs.json` and
`events.json`) for historical compatibility. This script uses an explicit local
compatibility adapter that re-keys those rows into V2 validation-run and
validation-event fields before applying the same public allowlists used by the
HTTP export service. The adapter copies only class-level synthetic IDs, statuses,
redacted summaries, public-safe refs, and timestamps; it never exports raw
metadata, hidden validation content, token material, request/response bodies, or
private environment/path values.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "apps" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.public_evidence_allowlists import (  # noqa: E402
    PUBLIC_EVIDENCE_GENERATED_AT,
    PUBLIC_EVIDENCE_REDACTION_MODE,
    PUBLIC_EVIDENCE_SCOPE,
    PUBLIC_EVIDENCE_TOP_LEVEL_FIELDS,
    PUBLIC_FINDING_FIELDS,
    PUBLIC_VALIDATION_EVENT_FIELDS,
    PUBLIC_VALIDATION_RUN_FIELDS,
    ordered_public_payload,
)

FIXTURE_ROOT = REPO_ROOT / "fixtures" / "used_car_world"
DEFAULT_OUTPUT = REPO_ROOT / "exports" / "public-evidence" / "used-car-world-public-evidence.json"


def _load_fixture(name: str) -> list[dict[str, Any]]:
    path = FIXTURE_ROOT / name
    if path.suffix != ".json":
        path = path.with_suffix(".json")
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _validation_run_id(scenario_run_id: str) -> str:
    return f"validation_{scenario_run_id}"


def _row_object(row: dict[str, Any]) -> SimpleNamespace:
    normalized = dict(row)
    for key in ("created_at", "updated_at"):
        if key in normalized and isinstance(normalized[key], str):
            normalized[key] = _parse_datetime(normalized[key])
    return SimpleNamespace(**normalized)


def _adapt_validation_run(row: dict[str, Any]) -> SimpleNamespace:
    return _row_object(
        {
            "id": _validation_run_id(row["id"]),
            "scenario_run_id": row["id"],
            "scenario_id": row["scenario_id"],
            "status": row["status"],
            "objective": row.get("objective"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    )


def _adapt_validation_event(row: dict[str, Any]) -> SimpleNamespace:
    return _row_object(
        {
            "id": row["id"],
            "validation_run_id": _validation_run_id(row["scenario_run_id"]),
            "event_type": row["event_type"],
            "redacted_summary": row["redacted_summary"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    )


def _adapt_finding(row: dict[str, Any]) -> SimpleNamespace:
    scenario_run_id = row["scenario_run_id"]
    return _row_object(
        {
            "id": row["id"],
            "validation_run_id": _validation_run_id(scenario_run_id),
            "scenario_run_id": scenario_run_id,
            "severity": row["severity"],
            "status": row["status"],
            "title": row.get("title"),
            "affected_route_class": row.get("affected_route_class"),
            "affected_object_class": row.get("affected_object_class"),
            "redacted_evidence_summary": row["redacted_evidence_summary"],
            "fix_ref": row.get("fix_ref"),
            "regression_ref": row.get("regression_ref"),
            "residual_risk": row.get("residual_risk"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    )


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _public_validation_event_payload(event: SimpleNamespace) -> dict[str, Any]:
    payload = {
        "id": event.id,
        "validation_run_id": event.validation_run_id,
        "event_type": event.event_type,
        "redacted_summary": event.redacted_summary,
        "created_at": _timestamp(event.created_at),
    }
    return ordered_public_payload(payload, PUBLIC_VALIDATION_EVENT_FIELDS)


def _public_finding_payload(finding: SimpleNamespace) -> dict[str, Any]:
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
        "created_at": _timestamp(finding.created_at),
    }
    return ordered_public_payload(payload, PUBLIC_FINDING_FIELDS)


def _public_validation_run_payload(
    run: SimpleNamespace,
    events: list[SimpleNamespace],
    findings: list[SimpleNamespace],
) -> dict[str, Any]:
    payload = {
        "id": run.id,
        "scenario_id": run.scenario_id,
        "status": run.status,
        "objective": run.objective,
        "created_at": _timestamp(run.created_at),
        "events": [_public_validation_event_payload(event) for event in events],
        "findings": [_public_finding_payload(finding) for finding in findings],
    }
    return ordered_public_payload(payload, PUBLIC_VALIDATION_RUN_FIELDS)


def _public_evidence_manifest(validation_runs: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "export_type": "public_evidence",
        "scope": PUBLIC_EVIDENCE_SCOPE,
        "redaction_mode": PUBLIC_EVIDENCE_REDACTION_MODE,
        "generated_at": PUBLIC_EVIDENCE_GENERATED_AT,
        "safety_notes": [
            "Synthetic used-car fixture world only.",
            "V2 validation-run, event, and finding class fields only; raw traces "
            "and bearer credentials are intentionally excluded.",
        ],
        "validation_runs": validation_runs,
    }
    return ordered_public_payload(payload, PUBLIC_EVIDENCE_TOP_LEVEL_FIELDS)


def build_public_evidence_payload_from_fixtures() -> dict[str, Any]:
    runs = [_adapt_validation_run(row) for row in _load_fixture("scenario_runs")]
    events = [_adapt_validation_event(row) for row in _load_fixture("events")]
    findings = [_adapt_finding(row) for row in _load_fixture("findings")]

    events_by_run: dict[str, list[SimpleNamespace]] = {}
    for event in sorted(events, key=lambda item: (item.created_at, item.id)):
        events_by_run.setdefault(event.validation_run_id, []).append(event)

    findings_by_run: dict[str, list[SimpleNamespace]] = {}
    for finding in sorted(findings, key=lambda item: (item.created_at, item.id)):
        findings_by_run.setdefault(finding.validation_run_id, []).append(finding)

    validation_runs = [
        _public_validation_run_payload(
            run,
            events_by_run.get(run.id, []),
            findings_by_run.get(run.id, []),
        )
        for run in sorted(runs, key=lambda item: (item.created_at, item.id))
    ]
    return _public_evidence_manifest(validation_runs)


# Backwards-compatible function name for tests/scripts that imported V1 helper.
def build_public_evidence_payload() -> dict[str, Any]:
    return build_public_evidence_payload_from_fixtures()


def build_public_evidence_file(output_path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    payload = build_public_evidence_payload_from_fixtures()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    output_path = DEFAULT_OUTPUT
    payload = build_public_evidence_file(output_path=output_path)
    relative_output = output_path.relative_to(REPO_ROOT)
    print(f"Wrote {relative_output} with {len(payload['validation_runs'])} synthetic validation run(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
