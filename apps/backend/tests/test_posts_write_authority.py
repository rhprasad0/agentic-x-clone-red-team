from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def test_post_authorship_comes_from_agent_token_and_rejects_identity_spoofing(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    spoof = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={
            "text": "Synthetic note about a boring Corolla inspection.",
            "author_agent_id": "agent_mira",
            "handle": "synthetic_mira",
            "role": "harness",
        },
    )
    assert spoof.status_code == 422

    created = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={
            "text": "Synthetic note about a boring Corolla inspection.",
        },
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["author"]["id"] == "agent_alex"
    assert payload["author"]["handle"] == "synthetic_alex"
    assert "metadata_json" not in payload
    assert payload["parent_post_id"] is None
    assert payload["text"] == "Synthetic note about a boring Corolla inspection."
    assert payload["counts"]["reply_count"] == 0


def test_reply_authorship_comes_from_agent_token_and_parent_must_exist(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    missing_parent = client.post(
        "/posts/post_missing_fixture/replies",
        headers=auth_headers("agent_mira_fixture"),
        json={"text": "Synthetic reply to a missing parent."},
    )
    assert missing_parent.status_code == 404

    spoof = client.post(
        "/posts/post_alex_under_10k_civic/replies",
        headers=auth_headers("agent_mira_fixture"),
        json={
            "text": "Synthetic reply with attempted spoof fields.",
            "author_agent_id": "agent_alex",
            "created_at": "2026-05-06T12:00:00Z",
        },
    )
    assert spoof.status_code == 422

    created = client.post(
        "/posts/post_alex_under_10k_civic/replies",
        headers=auth_headers("agent_mira_fixture"),
        json={"text": "Synthetic reply: inspect the title before the test drive."},
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["author"]["id"] == "agent_mira"
    assert payload["parent_post_id"] == "post_alex_under_10k_civic"

    thread = client.get("/posts/post_alex_under_10k_civic/thread")
    assert thread.status_code == 200
    reply_ids = [reply["id"] for reply in thread.json()["replies"]]
    assert payload["id"] in reply_ids


def test_harness_and_missing_tokens_cannot_write_agent_posts(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    assert client.post("/posts", json={"text": "Synthetic denied post."}).status_code == 401
    assert (
        client.post(
            "/posts",
            headers=auth_headers("harness_fixture"),
            json={"text": "Synthetic denied harness post."},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/posts/post_alex_under_10k_civic/replies",
            headers=auth_headers("harness_fixture"),
            json={"text": "Synthetic denied harness reply."},
        ).status_code
        == 403
    )
