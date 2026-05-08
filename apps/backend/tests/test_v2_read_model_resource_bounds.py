from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from app.services import read_models


def test_public_timeline_materializes_only_bounded_page_sources(
    client: TestClient, v2_read_graph: dict[str, dict[str, str]], monkeypatch
) -> None:
    del v2_read_graph
    materialized_posts = 0
    materialized_reposts = 0
    original_post_item = read_models.timeline_item_from_post
    original_repost_item = read_models.timeline_item_from_repost

    def count_post_item(post, db):
        nonlocal materialized_posts
        materialized_posts += 1
        return original_post_item(post, db)

    def count_repost_item(repost, db):
        nonlocal materialized_reposts
        materialized_reposts += 1
        return original_repost_item(repost, db)

    monkeypatch.setattr(read_models, "timeline_item_from_post", count_post_item)
    monkeypatch.setattr(read_models, "timeline_item_from_repost", count_repost_item)

    response = client.get("/timelines/public?limit=1&include_replies=true")

    assert response.status_code == 200
    assert response.json()["has_more"] is True
    assert materialized_posts <= 2
    assert materialized_reposts <= 2


def test_profile_replies_materializes_limit_plus_one_before_dto_expansion(
    client: TestClient, v2_read_graph: dict[str, dict[str, str]], monkeypatch
) -> None:
    del v2_read_graph
    materialized_reply_posts = 0
    original_post_item = read_models.timeline_item_from_post

    def count_post_item(post, db):
        nonlocal materialized_reply_posts
        materialized_reply_posts += 1
        return original_post_item(post, db)

    monkeypatch.setattr(read_models, "timeline_item_from_post", count_post_item)

    response = client.get("/agents/synthetic_alex/replies?limit=1")

    assert response.status_code == 200
    assert response.json()["has_more"] is True
    assert materialized_reply_posts <= 2


def test_thread_replies_materialize_limit_plus_one_before_reply_dto_expansion(
    client: TestClient, v2_read_graph: dict[str, dict[str, str]], monkeypatch
) -> None:
    root_post_id = v2_read_graph["posts"]["root"]
    reply_dto_ids: list[str] = []
    original_post_dto: Callable[..., dict[str, Any]] = read_models.post_dto

    def count_post_dto(post, db):
        if post.id != root_post_id:
            reply_dto_ids.append(post.id)
        return original_post_dto(post, db)

    monkeypatch.setattr(read_models, "post_dto", count_post_dto)

    response = client.get(f"/posts/{root_post_id}/thread?limit=1")

    assert response.status_code == 200
    assert response.json()["has_more"] is True
    assert len(reply_dto_ids) <= 2
