from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def test_harness_can_create_scenario_run_event_and_finding(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    run = client.post(
        "/scenario-runs",
        headers=auth_headers("harness_fixture"),
        json={
            "scenario_id": "RT-005",
            "objective": "Synthetic burst-posting harness smoke.",
            "metadata_json": {"fixture": "used_car_world"},
        },
    )
    assert run.status_code == 201
    run_payload = run.json()
    assert run_payload["scenario_id"] == "RT-005"
    assert run_payload["status"] == "running"
    assert "metadata_json" not in run_payload

    event = client.post(
        f"/scenario-runs/{run_payload['id']}/events",
        headers=auth_headers("harness_fixture"),
        json={
            "event_type": "route_probe",
            "redacted_summary": "Synthetic harness wrote a redacted route probe.",
            "metadata_json": {"route": "/timeline"},
        },
    )
    assert event.status_code == 201
    assert event.json()["scenario_run_id"] == run_payload["id"]

    finding = client.post(
        f"/scenario-runs/{run_payload['id']}/findings",
        headers=auth_headers("harness_fixture"),
        json={
            "severity": "medium",
            "title": "Synthetic route probe finding",
            "redacted_evidence_summary": "Synthetic evidence summary with no raw trace.",
            "metadata_json": {"redaction": "public_safe"},
        },
    )
    assert finding.status_code == 201
    finding_payload = finding.json()
    assert finding_payload["scenario_run_id"] == run_payload["id"]
    assert finding_payload["status"] == "open"


def test_harness_routes_reject_agents_and_protected_body_fields(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    agent_headers = auth_headers("agent_alex_fixture")
    harness_headers = auth_headers("harness_fixture")

    agent_run = client.post("/scenario-runs", headers=agent_headers, json={"scenario_id": "RT-001"})
    assert agent_run.status_code == 403
    assert (
        client.post(
            "/scenario-runs/run_used_car_baseline/events",
            headers=agent_headers,
            json={"event_type": "note", "redacted_summary": "Synthetic denied event."},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/scenario-runs/run_used_car_baseline/findings",
            headers=agent_headers,
            json={"severity": "low", "redacted_evidence_summary": "Synthetic denied finding."},
        ).status_code
        == 403
    )

    protected_run = client.post(
        "/scenario-runs",
        headers=harness_headers,
        json={"scenario_id": "RT-006", "status": "completed", "id": "run_client_supplied"},
    )
    assert protected_run.status_code == 422

    redirected_event = client.post(
        "/scenario-runs/run_used_car_baseline/events",
        headers=harness_headers,
        json={
            "scenario_run_id": "run_other_fixture",
            "event_type": "note",
            "redacted_summary": "Synthetic body attempted to redirect the event.",
        },
    )
    assert redirected_event.status_code == 422

    redirected_finding = client.post(
        "/scenario-runs/run_used_car_baseline/findings",
        headers=harness_headers,
        json={
            "scenario_run_id": "run_other_fixture",
            "severity": "low",
            "status": "closed",
            "redacted_evidence_summary": "Synthetic body attempted to redirect the finding.",
        },
    )
    assert redirected_finding.status_code == 422


def test_harness_event_and_finding_parent_run_must_exist(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world
    harness_headers = auth_headers("harness_fixture")

    event = client.post(
        "/scenario-runs/run_missing_fixture/events",
        headers=harness_headers,
        json={"event_type": "note", "redacted_summary": "Synthetic missing run event."},
    )
    assert event.status_code == 404

    finding = client.post(
        "/scenario-runs/run_missing_fixture/findings",
        headers=harness_headers,
        json={"severity": "low", "redacted_evidence_summary": "Synthetic missing run finding."},
    )
    assert finding.status_code == 404
