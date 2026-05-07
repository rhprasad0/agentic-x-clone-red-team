import json

from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient

PROTECTED_MARKERS = {
    "metadata_json",
    "raw_trace",
    "request_headers",
    "token_value",
    "token_hash",
    "private_path",
    "environment_value",
    "sql_fragment",
    "stack_trace",
    "actor_id",
    "owner_id",
}


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def assert_v2_error(response, expected_status: int, expected_code: str) -> None:
    assert response.status_code == expected_status
    assert response.json() == {
        "error": {
            "code": expected_code,
            "message": response.json()["error"]["message"],
            "details": None,
        }
    }


def assert_no_protected_markers(payload: dict) -> None:
    payload_text = json.dumps(payload, sort_keys=True)
    for marker in PROTECTED_MARKERS:
        assert marker not in payload_text


def test_validation_routes_are_harness_only_for_canonical_and_alias_reads(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world
    agent_headers = auth_headers("agent_alex_fixture")
    harness_headers = auth_headers("harness_fixture")

    protected_gets = [
        "/validation-runs",
        "/validation-runs/validation_run_used_car_baseline",
        "/validation-runs/validation_run_used_car_baseline/events",
        "/validation-runs/validation_run_used_car_baseline/findings",
        "/scenario-runs",
        "/scenario-runs/run_used_car_baseline",
        "/scenario-runs/run_used_car_baseline/events",
        "/scenario-runs/run_used_car_baseline/findings",
        "/findings",
        "/findings/finding_fixture_scope_note",
    ]

    for route in protected_gets:
        assert_v2_error(client.get(route), 401, "unauthorized")
        assert_v2_error(client.get(route, headers=agent_headers), 403, "forbidden")
        harness_response = client.get(route, headers=harness_headers)
        assert harness_response.status_code == 200
        assert_no_protected_markers(harness_response.json())


def test_harness_can_create_validation_run_event_and_finding_on_canonical_v2_routes(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world
    harness_headers = auth_headers("harness_fixture")

    run = client.post(
        "/validation-runs",
        headers=harness_headers,
        json={
            "scenario_id": "RT-V2-VALIDATION",
            "objective": "Synthetic V2 validation route smoke.",
        },
    )
    assert run.status_code == 201
    run_payload = run.json()
    assert run_payload["id"].startswith("validation_run_")
    assert run_payload["scenario_run_id"] is None
    assert run_payload["scenario_id"] == "RT-V2-VALIDATION"
    assert run_payload["status"] == "running"
    assert_no_protected_markers(run_payload)

    event = client.post(
        f"/validation-runs/{run_payload['id']}/events",
        headers=harness_headers,
        json={
            "event_type": "route_probe",
            "redacted_summary": "Synthetic validation event with no raw trace.",
        },
    )
    assert event.status_code == 201
    event_payload = event.json()
    assert event_payload["validation_run_id"] == run_payload["id"]
    assert event_payload["event_type"] == "route_probe"
    assert_no_protected_markers(event_payload)

    finding = client.post(
        f"/validation-runs/{run_payload['id']}/findings",
        headers=harness_headers,
        json={
            "severity": "medium",
            "title": "Synthetic validation finding",
            "affected_route_class": "validation_write",
            "affected_object_class": "validation_run",
            "redacted_evidence_summary": "Synthetic finding summary with no raw trace.",
            "fix_ref": "fix-validation-route",
            "regression_ref": "test_v2_validation_routes",
            "residual_risk": "Synthetic residual risk stays redacted.",
        },
    )
    assert finding.status_code == 201
    finding_payload = finding.json()
    assert finding_payload["validation_run_id"] == run_payload["id"]
    assert finding_payload["scenario_run_id"] is None
    assert finding_payload["status"] == "open"
    assert finding_payload["affected_route_class"] == "validation_write"
    assert finding_payload["affected_object_class"] == "validation_run"
    assert finding_payload["fix_ref"] == "fix-validation-route"
    assert finding_payload["regression_ref"] == "test_v2_validation_routes"
    assert finding_payload["residual_risk"] == "Synthetic residual risk stays redacted."
    assert_no_protected_markers(finding_payload)

    list_payload = client.get("/findings", headers=harness_headers).json()
    get_payload = client.get(f"/findings/{finding_payload['id']}", headers=harness_headers).json()
    assert finding_payload["id"] in {item["id"] for item in list_payload["items"]}
    assert get_payload == finding_payload


def test_validation_write_routes_reject_agents_and_protected_body_fields(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world
    agent_headers = auth_headers("agent_alex_fixture")
    harness_headers = auth_headers("harness_fixture")

    assert_v2_error(
        client.post("/validation-runs", headers=agent_headers, json={"scenario_id": "RT-DENY"}),
        403,
        "forbidden",
    )
    assert_v2_error(
        client.post(
            "/validation-runs/validation_run_used_car_baseline/events",
            headers=agent_headers,
            json={"event_type": "note", "redacted_summary": "Synthetic denied event."},
        ),
        403,
        "forbidden",
    )
    assert_v2_error(
        client.post(
            "/validation-runs/validation_run_used_car_baseline/findings",
            headers=agent_headers,
            json={"severity": "low", "redacted_evidence_summary": "Synthetic denied finding."},
        ),
        403,
        "forbidden",
    )

    protected_run = client.post(
        "/validation-runs",
        headers=harness_headers,
        json={
            "id": "validation_run_client_supplied",
            "scenario_id": "RT-PROTECTED",
            "status": "completed",
            "started_at": "2026-05-07T00:00:00Z",
            "metadata_json": {"operator_note": "do_not_accept"},
            "actor_id": "agent_alex",
        },
    )
    assert protected_run.status_code == 422

    redirected_event = client.post(
        "/validation-runs/validation_run_used_car_baseline/events",
        headers=harness_headers,
        json={
            "validation_run_id": "validation_run_other_fixture",
            "event_type": "note",
            "redacted_summary": "Synthetic body attempted to redirect the event.",
            "raw_trace": "do_not_accept",
        },
    )
    assert redirected_event.status_code == 422

    redirected_finding = client.post(
        "/validation-runs/validation_run_used_car_baseline/findings",
        headers=harness_headers,
        json={
            "validation_run_id": "validation_run_other_fixture",
            "severity": "low",
            "status": "closed",
            "redacted_evidence_summary": "Synthetic body attempted to redirect the finding.",
            "token_value": "do_not_accept",
        },
    )
    assert redirected_finding.status_code == 422


def test_validation_event_and_finding_parent_run_must_exist(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world
    harness_headers = auth_headers("harness_fixture")

    event = client.post(
        "/validation-runs/validation_run_missing_fixture/events",
        headers=harness_headers,
        json={"event_type": "note", "redacted_summary": "Synthetic missing run event."},
    )
    assert event.status_code == 404

    finding = client.post(
        "/validation-runs/validation_run_missing_fixture/findings",
        headers=harness_headers,
        json={"severity": "low", "redacted_evidence_summary": "Synthetic missing run finding."},
    )
    assert finding.status_code == 404
