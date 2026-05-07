from pathlib import Path

from fastapi.testclient import TestClient

FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "used_car_world"


def test_fixture_files_exist_without_plaintext_tokens() -> None:
    expected_files = {
        "agents.json",
        "posts.json",
        "auth_fixtures.json",
        "scenario_runs.json",
        "events.json",
        "findings.json",
    }

    assert expected_files == {path.name for path in FIXTURE_ROOT.glob("*.json")}
    auth_text = (FIXTURE_ROOT / "auth_fixtures.json").read_text()
    assert "agent_alex_fixture_token_placeholder" not in auth_text
    assert "agent_mira_fixture_token_placeholder" not in auth_text
    assert "harness_fixture_token_placeholder" not in auth_text
    assert "token_hash" in auth_text


def test_reset_is_harness_only_and_loads_deterministic_world(
    client: TestClient, harness_headers: dict[str, str]
) -> None:
    assert client.post("/fixtures/reset").status_code == 401

    first = client.post("/fixtures/reset", headers=harness_headers)
    second = client.post("/fixtures/reset", headers=harness_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert (
        first.json()
        == second.json()
        == {
            "status": "ok",
            "agents": 2,
            "posts": 4,
            "scenario_runs": 1,
            "events": 2,
            "findings": 1,
            "auth_fixtures": 3,
            "auth_token_hashes": 3,
            "validation_runs": 1,
            "validation_events": 2,
        }
    )

    timeline = client.get("/timeline")
    assert timeline.status_code == 200
    assert [item["id"] for item in timeline.json()["items"]] == [
        "post_alex_reply_budget",
        "post_mira_mechanic_checklist",
        "post_mira_reply_inspection",
        "post_alex_under_10k_civic",
    ]


def test_seed_is_idempotent_without_clearing_agent_posts(
    client: TestClient, harness_headers: dict[str, str]
) -> None:
    reset = client.post("/fixtures/reset", headers=harness_headers)
    assert reset.status_code == 200

    created = client.post(
        "/posts",
        headers={"Authorization": "Bearer agent_alex_fixture_token_placeholder"},
        json={"text": "Synthetic agent-added listing note."},
    )
    assert created.status_code == 201

    seed = client.post("/fixtures/seed", headers=harness_headers)

    assert seed.status_code == 200
    assert seed.json()["posts"] == 4
    timeline_ids = [item["id"] for item in client.get("/timeline").json()["items"]]
    assert created.json()["id"] in timeline_ids
