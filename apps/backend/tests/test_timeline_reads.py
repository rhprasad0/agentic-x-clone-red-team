from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.models.post import Post


def test_timeline_alias_returns_v2_public_timeline_envelope(
    client: TestClient, seeded_world: dict
) -> None:
    alias = client.get("/timeline")
    canonical = client.get("/timelines/public")

    assert alias.status_code == 200
    assert canonical.status_code == 200
    assert alias.json() == canonical.json()
    assert set(alias.json()) == {"items", "next_cursor", "has_more", "limit"}
    assert [item["post"]["id"] for item in alias.json()["items"]] == [
        "post_mira_mechanic_checklist",
        "post_alex_under_10k_civic",
    ]


def test_timeline_and_profile_tie_break_with_id_desc(
    client: TestClient, db_session, seeded_world: dict
) -> None:
    del seeded_world
    shared_created_at = datetime(2026, 5, 6, 12, 20, tzinfo=UTC)
    db_session.add_all(
        [
            Post(
                id="post_tie_alpha",
                author_agent_id="agent_alex",
                body="Synthetic tie-order alpha note.",
                created_at=shared_created_at,
                updated_at=shared_created_at,
            ),
            Post(
                id="post_tie_zulu",
                author_agent_id="agent_alex",
                body="Synthetic tie-order zulu note.",
                created_at=shared_created_at,
                updated_at=shared_created_at,
            ),
        ]
    )
    db_session.commit()

    timeline_ids = [
        item["post"]["id"] for item in client.get("/timeline").json()["items"]
    ]
    profile_ids = [
        item["post"]["id"]
        for item in client.get("/agents/synthetic_alex/posts").json()["items"]
    ]

    assert timeline_ids[:2] == ["post_tie_zulu", "post_tie_alpha"]
    assert profile_ids[:2] == ["post_tie_zulu", "post_tie_alpha"]


def test_agent_posts_filters_by_handle_and_thread_returns_replies(
    client: TestClient, seeded_world: dict
) -> None:
    agent_posts = client.get("/agents/synthetic_alex/posts")
    thread = client.get("/posts/post_alex_under_10k_civic/thread")

    assert agent_posts.status_code == 200
    assert [item["post"]["id"] for item in agent_posts.json()["items"]] == [
        "post_alex_under_10k_civic",
    ]
    assert thread.status_code == 200
    assert thread.json()["root"]["id"] == "post_alex_under_10k_civic"
    assert [reply["id"] for reply in thread.json()["replies"]] == ["post_mira_reply_inspection"]


def test_unknown_read_resources_return_404(client: TestClient, seeded_world: dict) -> None:
    assert client.get("/agents/synthetic_unknown").status_code == 404
    assert client.get("/agents/synthetic_unknown/posts").status_code == 404
    assert client.get("/posts/post_unknown/thread").status_code == 404
