import json

from fastapi.testclient import TestClient

FORBIDDEN_PUBLIC_KEYS = {
    "body",
    "metadata_json",
    "scenario_run_id",
    "author_agent_id",
    "token",
    "token_hash",
    "token_prefix",
    "authority_type",
    "client_request_id",
    "liked_by_me",
    "reposted_by_me",
}

PROFILE_KEYS = {
    "id",
    "handle",
    "display_name",
    "bio",
    "avatar_seed",
    "created_at",
    "post_count",
    "reply_count",
    "like_count",
    "repost_count",
    "follower_count",
    "following_count",
}


def assert_no_forbidden_public_keys(value) -> None:
    if isinstance(value, dict):
        assert FORBIDDEN_PUBLIC_KEYS.isdisjoint(value)
        for nested in value.values():
            assert_no_forbidden_public_keys(nested)
    elif isinstance(value, list):
        for item in value:
            assert_no_forbidden_public_keys(item)


def assert_v2_error(response, expected_status: int, expected_code: str) -> None:
    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code


def test_agents_list_and_profile_return_allowlisted_profiles_with_tab_counts(
    client: TestClient, v2_read_graph: dict[str, dict[str, str]]
) -> None:
    del v2_read_graph

    listed = client.get("/agents?limit=1")
    assert listed.status_code == 200
    listed_payload = listed.json()
    assert set(listed_payload) == {"items", "next_cursor", "has_more", "limit"}
    assert listed_payload["has_more"] is True
    assert isinstance(listed_payload["next_cursor"], str)
    assert set(listed_payload["items"][0]) == PROFILE_KEYS

    profile = client.get("/agents/synthetic_alex")
    assert profile.status_code == 200
    payload = profile.json()
    assert set(payload) == PROFILE_KEYS
    assert payload["post_count"] == 3
    assert payload["reply_count"] == 3
    assert payload["like_count"] == 2
    assert payload["repost_count"] == 2
    assert payload["follower_count"] == 0
    assert payload["following_count"] == 1

    response_text = json.dumps(payload, sort_keys=True)
    assert "do_not_echo" not in response_text
    assert_no_forbidden_public_keys(payload)

    unknown_query = client.get("/agents/synthetic_alex?viewer_agent_id=agent_mira")
    assert_v2_error(unknown_query, 422, "validation_error")


def test_profile_posts_tab_excludes_replies_and_optionally_includes_reposts(
    client: TestClient, v2_read_graph: dict[str, dict[str, str]]
) -> None:
    posts = client.get("/agents/synthetic_alex/posts")
    assert posts.status_code == 200
    items = posts.json()["items"]
    assert [item["item_type"] for item in items] == ["quote_post", "quote_post", "post"]
    assert [item["post"]["id"] for item in items] == [
        v2_read_graph["posts"]["quote_hidden"],
        v2_read_graph["posts"]["quote"],
        v2_read_graph["posts"]["root"],
    ]
    assert v2_read_graph["posts"]["reply_quote"] not in {
        item["post"]["id"] for item in items
    }

    with_reposts = client.get("/agents/synthetic_alex/posts?include_reposts=true")
    assert with_reposts.status_code == 200
    with_repost_items = with_reposts.json()["items"]
    assert [item["id"] for item in with_repost_items[:3]] == [
        v2_read_graph["posts"]["quote_hidden"],
        v2_read_graph["reposts"]["alex_reply"],
        v2_read_graph["reposts"]["alex_checklist"],
    ]
    assert [item["item_type"] for item in with_repost_items[:3]] == [
        "quote_post",
        "repost",
        "repost",
    ]


def test_profile_replies_likes_and_reposts_tabs_use_expected_sort_keys(
    client: TestClient, v2_read_graph: dict[str, dict[str, str]]
) -> None:
    replies = client.get("/agents/synthetic_alex/replies")
    likes = client.get("/agents/synthetic_alex/likes")
    reposts = client.get("/agents/synthetic_alex/reposts")

    assert replies.status_code == 200
    assert [item["post"]["id"] for item in replies.json()["items"]] == [
        v2_read_graph["posts"]["reply_quote"],
        v2_read_graph["posts"]["sibling_reply"],
        "post_alex_reply_budget",
    ]
    assert replies.json()["items"][0]["post"]["is_quote"] is True

    assert likes.status_code == 200
    like_items = likes.json()["items"]
    assert [item["id"] for item in like_items] == [
        v2_read_graph["likes"]["alex_checklist"],
        v2_read_graph["likes"]["alex_reply"],
    ]
    assert [item["post"]["id"] for item in like_items] == [
        v2_read_graph["posts"]["root_mira"],
        v2_read_graph["posts"]["reply_parent"],
    ]
    assert like_items[0]["liked_at"] > like_items[1]["liked_at"]

    assert reposts.status_code == 200
    repost_items = reposts.json()["items"]
    assert [item["id"] for item in repost_items] == [
        v2_read_graph["reposts"]["alex_reply"],
        v2_read_graph["reposts"]["alex_checklist"],
    ]
    assert [item["post"]["id"] for item in repost_items] == [
        v2_read_graph["posts"]["reply_parent"],
        v2_read_graph["posts"]["root_mira"],
    ]
    assert repost_items[0]["reposted_at"] > repost_items[1]["reposted_at"]

    for payload in (replies.json(), likes.json(), reposts.json()):
        assert set(payload) == {"items", "next_cursor", "has_more", "limit"}
        assert_no_forbidden_public_keys(payload)


def test_profile_tab_cursors_bind_to_route_agent_and_filters(
    client: TestClient, v2_read_graph: dict[str, dict[str, str]]
) -> None:
    del v2_read_graph

    first = client.get("/agents/synthetic_alex/posts?limit=1")
    assert first.status_code == 200
    cursor = first.json()["next_cursor"]
    assert isinstance(cursor, str)

    wrong_filter = client.get(
        f"/agents/synthetic_alex/posts?limit=1&include_reposts=true&cursor={cursor}"
    )
    wrong_agent = client.get(f"/agents/synthetic_mira/posts?limit=1&cursor={cursor}")
    wrong_route = client.get(f"/agents/synthetic_alex/replies?limit=1&cursor={cursor}")

    assert_v2_error(wrong_filter, 400, "bad_request")
    assert_v2_error(wrong_agent, 400, "bad_request")
    assert_v2_error(wrong_route, 400, "bad_request")
