#!/usr/bin/env python3
"""Generate a scanner-safe public evidence example from committed synthetic fixtures."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "fixtures" / "used_car_world"
DEFAULT_OUTPUT = REPO_ROOT / "exports" / "public-evidence" / "used-car-world-public-evidence.json"


def _load_fixture(name: str) -> list[dict[str, Any]]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def build_public_evidence_payload() -> dict[str, Any]:
    runs = _load_fixture("scenario_runs.json")
    events = _load_fixture("events.json")
    findings = _load_fixture("findings.json")

    exported_runs: list[dict[str, Any]] = []
    for run in runs:
        run_id = run["id"]
        exported_runs.append(
            {
                "id": run_id,
                "scenario_id": run["scenario_id"],
                "status": run["status"],
                "objective": run.get("objective"),
                "metadata_json": run.get("metadata_json", {}),
                "created_at": run["created_at"],
                "events": [
                    {
                        "id": event["id"],
                        "scenario_run_id": run_id,
                        "event_type": event["event_type"],
                        "redacted_summary": event["redacted_summary"],
                        "metadata_json": event.get("metadata_json", {}),
                        "created_at": event["created_at"],
                    }
                    for event in events
                    if event["scenario_run_id"] == run_id
                ],
                "findings": [
                    {
                        "id": finding["id"],
                        "scenario_run_id": run_id,
                        "severity": finding["severity"],
                        "status": finding["status"],
                        "title": finding.get("title"),
                        "redacted_evidence_summary": finding["redacted_evidence_summary"],
                        "metadata_json": finding.get("metadata_json", {}),
                        "created_at": finding["created_at"],
                    }
                    for finding in findings
                    if finding["scenario_run_id"] == run_id
                ],
            }
        )

    return {
        "export_type": "public_evidence",
        "redaction": "synthetic_redacted",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "safety_notes": [
            "Synthetic used-car fixture world only.",
            "Redacted event and finding summaries only; no raw traces or bearer values.",
        ],
        "runs": exported_runs,
    }


def build_public_evidence_file(output_path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    payload = build_public_evidence_payload()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    output_path = DEFAULT_OUTPUT
    payload = build_public_evidence_file(output_path=output_path)
    relative_output = output_path.relative_to(REPO_ROOT)
    print(f"Wrote {relative_output} with {len(payload['runs'])} synthetic run(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
