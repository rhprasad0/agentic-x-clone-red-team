from fastapi.testclient import TestClient


def test_agent_and_scenario_read_routes_smoke(client: TestClient, seeded_world: dict) -> None:
    harness_headers = {"Authorization": "Bearer harness_fixture_token_placeholder"}
    agents = client.get("/agents")
    agent = client.get("/agents/synthetic_mira")
    runs = client.get("/validation-runs", headers=harness_headers)
    run = client.get("/validation-runs/validation_run_used_car_baseline", headers=harness_headers)
    alias_run = client.get("/scenario-runs/run_used_car_baseline", headers=harness_headers)
    events = client.get(
        "/validation-runs/validation_run_used_car_baseline/events", headers=harness_headers
    )
    findings = client.get(
        "/validation-runs/validation_run_used_car_baseline/findings", headers=harness_headers
    )
    finding = client.get("/findings/finding_fixture_scope_note", headers=harness_headers)

    assert agents.status_code == 200
    assert [item["handle"] for item in agents.json()["items"]] == [
        "synthetic_mira",
        "synthetic_alex",
    ]
    assert agent.status_code == 200
    assert agent.json()["id"] == "agent_mira"
    assert runs.status_code == 200
    assert [item["id"] for item in runs.json()["items"]] == ["validation_run_used_car_baseline"]
    assert run.status_code == 200
    assert alias_run.status_code == 200
    assert alias_run.json() == run.json()
    assert run.json()["scenario_id"] == "RT-001"
    assert events.status_code == 200
    assert [item["id"] for item in events.json()["items"]] == [
        "event_fixture_reset",
        "event_timeline_probe",
    ]
    assert findings.status_code == 200
    assert [item["id"] for item in findings.json()["items"]] == ["finding_fixture_scope_note"]
    assert finding.status_code == 200
    assert finding.json()["redacted_evidence_summary"].startswith("Synthetic finding")


def test_openapi_docs_posture_is_documented_and_local_docs_are_reachable(
    client: TestClient,
) -> None:
    docs = client.get("/docs")
    openapi = client.get("/openapi.json")
    inventory = client.get("/openapi.json").json()["paths"]

    assert docs.status_code == 200
    assert openapi.status_code == 200
    for route in (
        "/agents",
        "/agents/{handle}",
        "/agents/{handle}/posts",
        "/timeline",
        "/timelines/public",
        "/timelines/home",
        "/posts/{post_id}/thread",
        "/validation-runs",
        "/validation-runs/{run_id}",
        "/validation-runs/{run_id}/events",
        "/validation-runs/{run_id}/findings",
        "/findings",
        "/findings/{finding_id}",
        "/fixtures/seed",
        "/fixtures/reset",
    ):
        assert route in inventory
