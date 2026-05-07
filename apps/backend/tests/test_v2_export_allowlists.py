import json
from pathlib import Path

from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient

EXPORT_ROUTE = "/exports/public-evidence"
PUBLIC_EXPORT_TOP_LEVEL_KEYS = {
    "export_type",
    "scope",
    "redaction_mode",
    "generated_at",
    "safety_notes",
    "validation_runs",
}
PUBLIC_VALIDATION_RUN_KEYS = {
    "id",
    "scenario_id",
    "status",
    "objective",
    "created_at",
    "events",
    "findings",
}
PUBLIC_VALIDATION_EVENT_KEYS = {
    "id",
    "validation_run_id",
    "event_type",
    "redacted_summary",
    "created_at",
}
PUBLIC_FINDING_KEYS = {
    "id",
    "validation_run_id",
    "scenario_run_id",
    "severity",
    "status",
    "title",
    "affected_route_class",
    "affected_object_class",
    "redacted_evidence_summary",
    "fix_ref",
    "regression_ref",
    "residual_risk",
    "created_at",
}
PROHIBITED_PUBLIC_MARKERS = {
    "metadata_json",
    "raw_trace",
    "request_headers",
    "request_body",
    "response_body",
    "token_value",
    "token_hash",
    "authorization",
    "private_path",
    "environment_value",
    "sql_fragment",
    "stack_trace",
    "agent_alex_fixture_token_placeholder",
    "harness_fixture_token_placeholder",
}


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def assert_public_allowlists(payload: dict) -> None:
    assert set(payload) == PUBLIC_EXPORT_TOP_LEVEL_KEYS
    assert payload["export_type"] == "public_evidence"
    assert payload["scope"] == "validation_runs"
    assert payload["redaction_mode"] == "synthetic_redacted"
    assert payload["generated_at"] == "2026-05-07T00:00:00Z"
    assert payload["validation_runs"]

    for validation_run in payload["validation_runs"]:
        assert set(validation_run) == PUBLIC_VALIDATION_RUN_KEYS
        assert validation_run["created_at"].endswith("Z")
        for event in validation_run["events"]:
            assert set(event) == PUBLIC_VALIDATION_EVENT_KEYS
            assert event["validation_run_id"] == validation_run["id"]
            assert event["created_at"].endswith("Z")
        for finding in validation_run["findings"]:
            assert set(finding) == PUBLIC_FINDING_KEYS
            assert finding["validation_run_id"] == validation_run["id"]
            assert finding["created_at"].endswith("Z")

    exported_text = json.dumps(payload, sort_keys=True).lower()
    for marker in PROHIBITED_PUBLIC_MARKERS:
        assert marker not in exported_text
    assert "/" + "home" + "/" + "example" not in exported_text


def test_public_evidence_route_accepts_only_harness_and_allowlisted_request_fields(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world
    harness_headers = auth_headers("harness_fixture")
    agent_headers = auth_headers("agent_alex_fixture")

    assert client.post(EXPORT_ROUTE, json={"scope": "validation_runs"}).status_code == 401
    assert (
        client.post(
            EXPORT_ROUTE,
            headers=agent_headers,
            json={"scope": "validation_runs"},
        ).status_code
        == 403
    )

    assert (
        client.post(
            EXPORT_ROUTE,
            headers=harness_headers,
            json={"scope": "validation_runs", "actor_id": "harness_fixture"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            EXPORT_ROUTE,
            headers=harness_headers,
            json={"scope": "scenario_runs"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            EXPORT_ROUTE,
            headers=harness_headers,
            json={"scope": "validation_runs", "redaction_mode": "raw"},
        ).status_code
        == 422
    )

    response = client.post(
        EXPORT_ROUTE,
        headers=harness_headers,
        json={"scope": "validation_runs", "redaction_mode": "synthetic_redacted"},
    )
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert_public_allowlists(response.json())


def test_public_evidence_export_filters_validation_run_ids_and_is_deterministic(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world
    harness_headers = auth_headers("harness_fixture")

    created = client.post(
        "/validation-runs",
        headers=harness_headers,
        json={
            "scenario_id": "RT-V2-EXPORT-FILTER",
            "objective": "Synthetic extra validation run for export filter coverage.",
        },
    )
    assert created.status_code == 201
    validation_run_id = created.json()["id"]

    request_body = {"scope": "validation_runs", "validation_run_ids": [validation_run_id]}
    first = client.post(EXPORT_ROUTE, headers=harness_headers, json=request_body)
    second = client.post(EXPORT_ROUTE, headers=harness_headers, json=request_body)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert [run["id"] for run in first.json()["validation_runs"]] == [validation_run_id]
    assert_public_allowlists(first.json())


def test_public_evidence_script_uses_same_v2_allowlists_as_route(tmp_path: Path) -> None:
    from scripts.export_public_evidence import build_public_evidence_file

    output_path = tmp_path / "public-evidence.json"
    payload = build_public_evidence_file(output_path=output_path)
    written = json.loads(output_path.read_text(encoding="utf-8"))

    assert written == payload
    assert_public_allowlists(payload)
