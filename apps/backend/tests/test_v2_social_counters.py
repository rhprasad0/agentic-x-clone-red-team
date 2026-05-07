from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def post_counts(client: TestClient, post_id: str) -> dict[str, int]:
    response = client.get(f"/posts/{post_id}/thread")
    assert response.status_code == 200
    return response.json()["selected"]["counts"]


def agent_counts(client: TestClient, handle: str) -> dict[str, int]:
    response = client.get(f"/agents/{handle}")
    assert response.status_code == 200
    payload = response.json()
    return {
        "post_count": payload["post_count"],
        "reply_count": payload["reply_count"],
        "like_count": payload["like_count"],
        "repost_count": payload["repost_count"],
        "follower_count": payload["follower_count"],
        "following_count": payload["following_count"],
    }


def test_like_repost_follow_and_quote_counters_are_derived_consistently(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    assert post_counts(client, "post_alex_under_10k_civic") == {
        "reply_count": 1,
        "like_count": 0,
        "repost_count": 0,
        "quote_count": 0,
    }
    assert agent_counts(client, "synthetic_mira") == {
        "post_count": 1,
        "reply_count": 1,
        "like_count": 0,
        "repost_count": 0,
        "follower_count": 0,
        "following_count": 0,
    }

    assert (
        client.post(
            "/posts/post_alex_under_10k_civic/like",
            headers=auth_headers("agent_mira_fixture"),
            json={},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/posts/post_alex_under_10k_civic/repost",
            headers=auth_headers("agent_mira_fixture"),
            json={},
        ).status_code
        == 201
    )
    quote = client.post(
        "/posts",
        headers=auth_headers("agent_mira_fixture"),
        json={
            "text": "Synthetic quote: the under-10k Civic still needs a lift inspection.",
            "quote_post_id": "post_alex_under_10k_civic",
        },
    )
    assert quote.status_code == 201
    follow = client.post(
        "/agents/synthetic_alex/follow",
        headers=auth_headers("agent_mira_fixture"),
        json={},
    )
    assert follow.status_code == 201

    assert post_counts(client, "post_alex_under_10k_civic") == {
        "reply_count": 1,
        "like_count": 1,
        "repost_count": 1,
        "quote_count": 1,
    }
    assert agent_counts(client, "synthetic_mira") == {
        "post_count": 2,
        "reply_count": 1,
        "like_count": 1,
        "repost_count": 1,
        "follower_count": 0,
        "following_count": 1,
    }
    assert agent_counts(client, "synthetic_alex")["follower_count"] == 1

    assert (
        client.delete(
            "/posts/post_alex_under_10k_civic/like",
            headers=auth_headers("agent_mira_fixture"),
        ).status_code
        == 204
    )
    assert (
        client.delete(
            "/posts/post_alex_under_10k_civic/repost",
            headers=auth_headers("agent_mira_fixture"),
        ).status_code
        == 204
    )
    assert (
        client.delete(
            "/agents/synthetic_alex/follow",
            headers=auth_headers("agent_mira_fixture"),
        ).status_code
        == 204
    )

    assert post_counts(client, "post_alex_under_10k_civic") == {
        "reply_count": 1,
        "like_count": 0,
        "repost_count": 0,
        "quote_count": 1,
    }
    assert agent_counts(client, "synthetic_mira") == {
        "post_count": 2,
        "reply_count": 1,
        "like_count": 0,
        "repost_count": 0,
        "follower_count": 0,
        "following_count": 0,
    }
    assert agent_counts(client, "synthetic_alex")["follower_count"] == 0


def test_likes_do_not_become_timeline_events_and_reposts_are_not_quotes(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    before = client.get("/timelines/public?include_replies=true")
    assert before.status_code == 200
    before_items = before.json()["items"]
    assert {item["item_type"] for item in before_items}.isdisjoint({"like", "repost"})

    like = client.post(
        "/posts/post_alex_under_10k_civic/like",
        headers=auth_headers("agent_mira_fixture"),
        json={},
    )
    assert like.status_code == 201
    after_like = client.get("/timelines/public?include_replies=true")
    assert after_like.status_code == 200
    after_like_items = after_like.json()["items"]
    assert not any(item.get("item_type") == "like" for item in after_like_items)
    assert len(after_like_items) == len(before_items)

    repost = client.post(
        "/posts/post_alex_under_10k_civic/repost",
        headers=auth_headers("agent_mira_fixture"),
        json={},
    )
    assert repost.status_code == 201
    after_repost = client.get("/timelines/public?include_replies=true")
    assert after_repost.status_code == 200
    after_repost_items = after_repost.json()["items"]
    repost_items = [item for item in after_repost_items if item["item_type"] == "repost"]
    assert len(repost_items) == 1
    assert repost_items[0]["post"]["id"] == "post_alex_under_10k_civic"
    assert repost_items[0]["post"]["counts"]["repost_count"] == 1
    assert repost_items[0]["post"]["counts"]["quote_count"] == 0


def test_fixture_reset_clears_relationship_rows_idempotency_and_derived_counts(
    client: TestClient,
    seeded_world: dict,
    harness_headers: dict[str, str],
) -> None:
    del seeded_world

    assert (
        client.post(
            "/posts/post_alex_under_10k_civic/like",
            headers=auth_headers("agent_mira_fixture"),
            json={"client_request_id": "reset-clears-like"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/posts/post_alex_under_10k_civic/repost",
            headers=auth_headers("agent_mira_fixture"),
            json={"client_request_id": "reset-clears-repost"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/agents/synthetic_alex/follow",
            headers=auth_headers("agent_mira_fixture"),
            json={"client_request_id": "reset-clears-follow"},
        ).status_code
        == 201
    )
    assert post_counts(client, "post_alex_under_10k_civic")["like_count"] == 1
    assert post_counts(client, "post_alex_under_10k_civic")["repost_count"] == 1
    assert agent_counts(client, "synthetic_mira")["following_count"] == 1

    reset = client.post("/fixtures/reset", headers=harness_headers)

    assert reset.status_code == 200
    assert post_counts(client, "post_alex_under_10k_civic")["like_count"] == 0
    assert post_counts(client, "post_alex_under_10k_civic")["repost_count"] == 0
    assert agent_counts(client, "synthetic_mira")["like_count"] == 0
    assert agent_counts(client, "synthetic_mira")["repost_count"] == 0
    assert agent_counts(client, "synthetic_mira")["following_count"] == 0
    assert agent_counts(client, "synthetic_alex")["follower_count"] == 0

    replay_after_reset = client.post(
        "/posts/post_alex_under_10k_civic/like",
        headers=auth_headers("agent_mira_fixture"),
        json={"client_request_id": "reset-clears-like"},
    )
    assert replay_after_reset.status_code == 201
