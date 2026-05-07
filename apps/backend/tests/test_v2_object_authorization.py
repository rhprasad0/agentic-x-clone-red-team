import pytest
from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


@pytest.mark.parametrize(
    "protected_field,value",
    [
        ("metadata_json", {"leak": "nope"}),
        ("author_agent_id", "agent_mira"),
        ("parent_post_id", "post_alex_under_10k_civic"),
        ("root_post_id", "post_alex_under_10k_civic"),
        ("reply_depth", 4),
        ("quote_count", 99),
        ("created_at", "2026-05-07T12:00:00Z"),
        ("updated_at", "2026-05-07T12:00:00Z"),
        ("id", "post_client_supplied"),
        ("role", "harness"),
        ("status", "fixture"),
        ("like_count", 99),
    ],
)
def test_post_create_rejects_protected_and_unknown_fields(
    client: TestClient, seeded_world: dict, protected_field: str, value: object
) -> None:
    del seeded_world

    response = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={"text": "Protected fields should not ride along.", protected_field: value},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_authorship_is_never_taken_from_body_query_cookie_or_client_id(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    response = client.post(
        "/posts?author_agent_id=agent_mira&handle=synthetic_mira",
        headers={**auth_headers("agent_alex_fixture"), "Cookie": "agent_id=agent_mira"},
        json={
            "text": "The token owns this post, not query strings or cookies.",
            "client_request_id": "authority-is-not-a-client-id",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["author"]["id"] == "agent_alex"
    assert payload["author"]["handle"] == "synthetic_alex"


def test_harness_and_missing_tokens_cannot_create_replies_or_quotes(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    missing = client.post(
        "/posts",
        json={"text": "No token no quote.", "quote_post_id": "post_alex_under_10k_civic"},
    )
    assert missing.status_code == 401

    harness = client.post(
        "/posts",
        headers=auth_headers("harness_fixture"),
        json={"text": "Harness cannot social quote.", "quote_post_id": "post_alex_under_10k_civic"},
    )
    assert harness.status_code == 403

    harness_reply = client.post(
        "/posts",
        headers=auth_headers("harness_fixture"),
        json={
            "text": "Harness cannot social reply.",
            "reply_to_post_id": "post_alex_under_10k_civic",
        },
    )
    assert harness_reply.status_code == 403
