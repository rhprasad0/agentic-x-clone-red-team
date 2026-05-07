from pathlib import Path

from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient

BACKEND_APP = Path(__file__).resolve().parents[1] / "app"


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


def test_routes_use_authority_specific_dependencies_instead_of_inline_auth_checks() -> None:
    route_sources = {
        path.relative_to(BACKEND_APP): path.read_text(encoding="utf-8")
        for path in (BACKEND_APP / "api" / "routes").glob("*.py")
    }

    protected_sources = "\n".join(route_sources.values())
    assert "require_synthetic_agent_authority" in protected_sources
    assert "require_harness_authority" in protected_sources
    assert "get_current_actor" not in protected_sources
    assert "require_synthetic_agent(" not in protected_sources
    assert "require_harness(" not in protected_sources


def test_synthetic_agent_and_harness_authority_classes_are_not_interchangeable(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    harness_post = client.post(
        "/posts",
        headers=auth_headers("harness_fixture"),
        json={"text": "Synthetic harness should not author a social post."},
    )
    agent_reset = client.post("/fixtures/reset", headers=auth_headers("agent_alex_fixture"))
    agent_export = client.post(
        "/exports/public-evidence", headers=auth_headers("agent_alex_fixture")
    )
    missing_finding = client.get("/findings")
    agent_finding = client.get("/findings", headers=auth_headers("agent_alex_fixture"))
    harness_finding = client.get("/findings", headers=auth_headers("harness_fixture"))

    assert_v2_error(harness_post, 403, "forbidden")
    assert_v2_error(agent_reset, 403, "forbidden")
    assert_v2_error(agent_export, 403, "forbidden")
    assert_v2_error(missing_finding, 401, "unauthorized")
    assert_v2_error(agent_finding, 403, "forbidden")
    assert harness_finding.status_code == 200


def test_home_timeline_resolves_viewer_only_from_synthetic_agent_token(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    missing = client.get("/timelines/home")
    harness = client.get("/timelines/home", headers=auth_headers("harness_fixture"))
    agent = client.get("/timelines/home", headers=auth_headers("agent_alex_fixture"))

    assert_v2_error(missing, 401, "unauthorized")
    assert_v2_error(harness, 403, "forbidden")
    assert agent.status_code == 200
    assert set(agent.json()) == {"items", "next_cursor", "has_more", "limit"}
