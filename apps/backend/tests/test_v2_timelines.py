from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def assert_v2_error(response, expected_status: int, expected_code: str) -> None:
    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code


def sort_keys(items: list[dict]) -> list[tuple[str, str]]:
    return [(item["sort_timestamp"], item["id"]) for item in items]


def test_public_timeline_filters_replies_includes_quotes_and_reposts_not_likes(
    client: TestClient, v2_read_graph: dict[str, dict[str, str]]
) -> None:
    response = client.get("/timelines/public")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"items", "next_cursor", "has_more", "limit"}
    assert payload["limit"] == 25
    items = payload["items"]
    assert sort_keys(items) == sorted(sort_keys(items), reverse=True)
    assert not any(item["item_type"] == "like" for item in items)

    post_item_ids = {
        item["post"]["id"] for item in items if item["item_type"] != "repost"
    }
    assert v2_read_graph["posts"]["quote"] in post_item_ids
    assert v2_read_graph["posts"]["quote_hidden"] in post_item_ids
    assert v2_read_graph["posts"]["reply_quote"] not in post_item_ids
    assert v2_read_graph["posts"]["reply_parent"] not in post_item_ids

    repost_items = [item for item in items if item["item_type"] == "repost"]
    assert {item["id"] for item in repost_items} >= {
        v2_read_graph["reposts"]["alex_reply"],
        v2_read_graph["reposts"]["mira_civic"],
    }
    alex_reply_repost = next(
        item for item in repost_items if item["id"] == v2_read_graph["reposts"]["alex_reply"]
    )
    assert alex_reply_repost["post"]["id"] == v2_read_graph["posts"]["reply_parent"]
    assert alex_reply_repost["sort_timestamp"] == alex_reply_repost["reposted_at"]

    with_replies = client.get("/timelines/public?include_replies=true")
    assert with_replies.status_code == 200
    reply_item_ids = {
        item["post"]["id"]
        for item in with_replies.json()["items"]
        if item["item_type"] == "reply"
    }
    assert v2_read_graph["posts"]["reply_quote"] in reply_item_ids


def test_public_timeline_cursor_is_keyset_and_bound_to_filter_scope(
    client: TestClient, v2_read_graph: dict[str, dict[str, str]]
) -> None:
    del v2_read_graph

    first = client.get("/timelines/public?limit=2")
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["has_more"] is True
    assert isinstance(first_payload["next_cursor"], str)

    second = client.get(f"/timelines/public?limit=2&cursor={first_payload['next_cursor']}")
    assert second.status_code == 200
    assert {
        item["id"] for item in first_payload["items"]
    }.isdisjoint({item["id"] for item in second.json()["items"]})

    wrong_filter = client.get(
        f"/timelines/public?limit=2&include_replies=true&cursor={first_payload['next_cursor']}"
    )
    assert_v2_error(wrong_filter, 400, "bad_request")


def test_home_timeline_uses_token_actor_and_rejects_viewer_claims(
    client: TestClient, v2_read_graph: dict[str, dict[str, str]]
) -> None:
    missing = client.get("/timelines/home")
    invalid = client.get(
        "/timelines/home", headers={"Authorization": "Bearer unknown_token_placeholder"}
    )
    harness = client.get("/timelines/home", headers=auth_headers("harness_fixture"))
    viewer_query = client.get(
        "/timelines/home?viewer_agent_id=agent_mira",
        headers=auth_headers("agent_alex_fixture"),
    )
    viewer_body = client.request(
        "GET",
        "/timelines/home",
        headers=auth_headers("agent_alex_fixture"),
        json={"viewer_agent_id": "agent_mira"},
    )

    assert_v2_error(missing, 401, "unauthorized")
    assert_v2_error(invalid, 401, "unauthorized")
    assert_v2_error(harness, 403, "forbidden")
    assert_v2_error(viewer_query, 422, "validation_error")
    assert_v2_error(viewer_body, 422, "validation_error")

    response = client.get("/timelines/home", headers=auth_headers("agent_alex_fixture"))
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    assert not any(item["item_type"] == "like" for item in items)
    assert not any(item["item_type"] == "reply" for item in items)
    assert {
        item["post"]["author"]["id"] for item in items if item["item_type"] != "repost"
    } <= {v2_read_graph["agents"]["alex"], v2_read_graph["agents"]["mira"]}

    empty_signup = client.post(
        "/agents/signup",
        json={
            "handle": "budget_lurker",
            "display_name": "Budget Lurker",
            "bio": "Synthetic observer of fictional under-$10k car posts.",
        },
    )
    assert empty_signup.status_code == 201
    empty_home = client.get(
        "/timelines/home",
        headers={"Authorization": f"Bearer {empty_signup.json()['token']}"},
    )
    assert empty_home.status_code == 200
    assert empty_home.json()["items"] == []


def test_home_timeline_cursor_is_bound_to_resolved_actor(
    client: TestClient, v2_read_graph: dict[str, dict[str, str]]
) -> None:
    del v2_read_graph

    first = client.get(
        "/timelines/home?limit=1", headers=auth_headers("agent_alex_fixture")
    )
    assert first.status_code == 200
    cursor = first.json()["next_cursor"]
    assert isinstance(cursor, str)

    wrong_actor = client.get(
        f"/timelines/home?limit=1&cursor={cursor}",
        headers=auth_headers("agent_mira_fixture"),
    )
    assert_v2_error(wrong_actor, 400, "bad_request")
