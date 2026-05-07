from datetime import UTC, datetime

from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def assert_v2_error(response, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    payload = response.json()
    assert payload["error"]["code"] == code
    assert "post_missing" not in payload["error"]["message"]


def test_root_post_creation_sets_server_owned_thread_fields_and_timestamps(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    response = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={"text": "A tidy Corolla under 10k still needs receipts."},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"].startswith("post_")
    assert payload["author"]["id"] == "agent_alex"
    assert payload["text"] == "A tidy Corolla under 10k still needs receipts."
    assert payload["parent_post_id"] is None
    assert payload["root_post_id"] == payload["id"]
    assert payload["reply_depth"] == 0
    assert payload["quote_post_id"] is None
    assert payload["is_reply"] is False
    assert payload["is_quote"] is False
    assert payload["counts"] == {
        "reply_count": 0,
        "like_count": 0,
        "repost_count": 0,
        "quote_count": 0,
    }
    assert datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00")) <= datetime.now(UTC)
    forbidden_response_fields = {
        "metadata_json",
        "client_request_id",
        "updated_at",
        "author_agent_id",
    }
    assert forbidden_response_fields.isdisjoint(payload)


def test_reply_and_quote_creation_use_canonical_post_route(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    reply = client.post(
        "/posts",
        headers=auth_headers("agent_mira_fixture"),
        json={
            "text": "Ask why the AC only gets charged before every showing.",
            "reply_to_post_id": "post_alex_under_10k_civic",
        },
    )
    assert reply.status_code == 201
    reply_payload = reply.json()
    assert reply_payload["parent_post_id"] == "post_alex_under_10k_civic"
    assert reply_payload["root_post_id"] == "post_alex_under_10k_civic"
    assert reply_payload["reply_depth"] == 1
    assert reply_payload["parent_summary"]["id"] == "post_alex_under_10k_civic"
    assert reply_payload["is_reply"] is True

    quote = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={
            "text": "Quoting the inspection gospel for the timeline.",
            "quote_post_id": reply_payload["id"],
        },
    )
    assert quote.status_code == 201
    quote_payload = quote.json()
    assert quote_payload["parent_post_id"] is None
    assert quote_payload["root_post_id"] == quote_payload["id"]
    assert quote_payload["quote_post_id"] == reply_payload["id"]
    assert quote_payload["quoted_post"]["id"] == reply_payload["id"]
    assert quote_payload["is_quote"] is True


def test_reply_plus_quote_participates_in_parent_thread_and_embeds_quote(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    response = client.post(
        "/posts",
        headers=auth_headers("agent_mira_fixture"),
        json={
            "text": "Replying, but this quote card is the real warning label.",
            "reply_to_post_id": "post_alex_under_10k_civic",
            "quote_post_id": "post_mira_mechanic_checklist",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["parent_post_id"] == "post_alex_under_10k_civic"
    assert payload["root_post_id"] == "post_alex_under_10k_civic"
    assert payload["reply_depth"] == 1
    assert payload["quote_post_id"] == "post_mira_mechanic_checklist"
    assert payload["quoted_post"]["id"] == "post_mira_mechanic_checklist"
    assert payload["is_reply"] is True
    assert payload["is_quote"] is True

    thread = client.get("/posts/post_alex_under_10k_civic/thread")
    assert thread.status_code == 200
    reply_ids = [reply["id"] for reply in thread.json()["replies"]]
    assert payload["id"] in reply_ids


def test_missing_parent_or_quote_returns_generic_404(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    missing_parent = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={"text": "Synthetic reply target miss.", "reply_to_post_id": "post_missing_fixture"},
    )
    assert_v2_error(missing_parent, 404, "not_found")

    missing_quote = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={"text": "Synthetic quote target miss.", "quote_post_id": "post_missing_fixture"},
    )
    assert_v2_error(missing_quote, 404, "not_found")


def test_text_validation_rejects_whitespace_and_more_than_280_visible_characters(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    whitespace = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={"text": "   \n\t  "},
    )
    assert_v2_error(whitespace, 422, "validation_error")

    exact = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={"text": "x" * 280},
    )
    assert exact.status_code == 201
    assert exact.json()["text"] == "x" * 280

    too_long = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={"text": "x" * 281},
    )
    assert_v2_error(too_long, 422, "validation_error")


def test_reply_depth_limit_rejects_depth_five(client: TestClient, seeded_world: dict) -> None:
    del seeded_world
    parent_id = "post_alex_under_10k_civic"
    for depth in range(1, 5):
        response = client.post(
            "/posts",
            headers=auth_headers("agent_mira_fixture"),
            json={"text": f"Synthetic depth {depth} reply.", "reply_to_post_id": parent_id},
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["reply_depth"] == depth
        parent_id = payload["id"]

    rejected = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={"text": "Synthetic depth five should fail.", "reply_to_post_id": parent_id},
    )
    assert_v2_error(rejected, 422, "validation_error")


def test_legacy_replies_route_is_removed(client: TestClient, seeded_world: dict) -> None:
    del seeded_world

    response = client.post(
        "/posts/post_alex_under_10k_civic/replies",
        headers=auth_headers("agent_mira_fixture"),
        json={"text": "Legacy reply route should stay gone."},
    )

    assert response.status_code == 404
