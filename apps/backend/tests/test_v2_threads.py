from fastapi.testclient import TestClient


def assert_v2_error(response, expected_status: int, expected_code: str) -> None:
    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code


def test_thread_returns_selected_post_ancestors_siblings_and_descendants_with_cursor(
    client: TestClient, v2_read_graph: dict[str, dict[str, str]]
) -> None:
    first = client.get(f"/posts/{v2_read_graph['posts']['reply_quote']}/thread?limit=1")

    assert first.status_code == 200
    payload = first.json()
    assert set(payload) == {
        "root",
        "selected",
        "ancestors",
        "replies",
        "next_cursor",
        "has_more",
        "limit",
    }
    assert payload["root"]["id"] == v2_read_graph["posts"]["root"]
    assert payload["selected"]["id"] == v2_read_graph["posts"]["reply_quote"]
    assert payload["selected"]["parent_summary"]["id"] == v2_read_graph["posts"]["reply_parent"]
    assert payload["selected"]["quoted_post"]["id"] == v2_read_graph["posts"]["root_mira"]
    assert [post["id"] for post in payload["ancestors"]] == [
        v2_read_graph["posts"]["root"],
        v2_read_graph["posts"]["reply_parent"],
    ]
    assert [post["id"] for post in payload["replies"]] == [
        v2_read_graph["posts"]["sibling_reply"]
    ]
    assert payload["has_more"] is True
    assert isinstance(payload["next_cursor"], str)

    second = client.get(
        f"/posts/{v2_read_graph['posts']['reply_quote']}/thread"
        f"?limit=1&cursor={payload['next_cursor']}"
    )
    assert second.status_code == 200
    assert [post["id"] for post in second.json()["replies"]] == [
        v2_read_graph["posts"]["reply_child"]
    ]
    assert second.json()["has_more"] is False


def test_thread_embeds_available_quotes_and_unavailable_placeholders(
    client: TestClient, v2_read_graph: dict[str, dict[str, str]]
) -> None:
    available = client.get(f"/posts/{v2_read_graph['posts']['quote']}/thread")
    unavailable = client.get(f"/posts/{v2_read_graph['posts']['quote_hidden']}/thread")

    assert available.status_code == 200
    assert available.json()["selected"]["quoted_post"]["id"] == v2_read_graph["posts"][
        "root_mira"
    ]

    assert unavailable.status_code == 200
    placeholder = unavailable.json()["selected"]["quoted_post"]
    assert placeholder == {
        "id": v2_read_graph["posts"]["hidden"],
        "availability": "unavailable",
        "reason": "not_found",
    }
    assert "Synthetic hidden note" not in unavailable.text
    assert "do_not_echo_unavailable_fixture" not in unavailable.text


def test_thread_missing_target_404_and_cursor_is_bound_to_selected_post(
    client: TestClient, v2_read_graph: dict[str, dict[str, str]]
) -> None:
    missing = client.get("/posts/post_missing_fixture/thread")
    assert_v2_error(missing, 404, "not_found")

    first = client.get(f"/posts/{v2_read_graph['posts']['root']}/thread?limit=1")
    assert first.status_code == 200
    cursor = first.json()["next_cursor"]
    assert isinstance(cursor, str)

    wrong_post = client.get(
        f"/posts/{v2_read_graph['posts']['root_mira']}/thread?limit=1&cursor={cursor}"
    )
    assert_v2_error(wrong_post, 400, "bad_request")
