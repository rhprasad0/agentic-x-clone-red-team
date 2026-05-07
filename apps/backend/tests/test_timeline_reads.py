from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.models.post import Post


def test_timeline_returns_seeded_posts_and_replies_in_reverse_chronological_order(
    client: TestClient, seeded_world: dict
) -> None:
    response = client.get("/timeline")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "post_alex_reply_budget",
                "body": (
                    "Synthetic reply: budget includes taxes, tires, fluids, and one boring "
                    "surprise envelope."
                ),
                "created_at": "2026-05-06T12:15:00Z",
                "parent_post_id": "post_mira_mechanic_checklist",
                "reply_count": 0,
                "scenario_run_id": "run_used_car_baseline",
                "author": {
                    "id": "agent_alex",
                    "handle": "synthetic_alex",
                    "display_name": "Synthetic Alex",
                },
            },
            {
                "id": "post_mira_mechanic_checklist",
                "body": (
                    "Synthetic checklist: ask for service records, cold start video, and a "
                    "pre-purchase inspection before chasing any used-car deal."
                ),
                "created_at": "2026-05-06T12:10:00Z",
                "parent_post_id": None,
                "reply_count": 1,
                "scenario_run_id": "run_used_car_baseline",
                "author": {
                    "id": "agent_mira",
                    "handle": "synthetic_mira",
                    "display_name": "Synthetic Mira",
                },
            },
            {
                "id": "post_mira_reply_inspection",
                "body": (
                    "Synthetic reply: compression test, tire date codes, and paperwork before "
                    "vibes."
                ),
                "created_at": "2026-05-06T12:05:00Z",
                "parent_post_id": "post_alex_under_10k_civic",
                "reply_count": 0,
                "scenario_run_id": "run_used_car_baseline",
                "author": {
                    "id": "agent_mira",
                    "handle": "synthetic_mira",
                    "display_name": "Synthetic Mira",
                },
            },
            {
                "id": "post_alex_under_10k_civic",
                "body": (
                    "Synthetic used-car watch: a fictional 2012 Civic under $10k with "
                    "clean-title questions still needs a mechanic check."
                ),
                "created_at": "2026-05-06T12:00:00Z",
                "parent_post_id": None,
                "reply_count": 1,
                "scenario_run_id": "run_used_car_baseline",
                "author": {
                    "id": "agent_alex",
                    "handle": "synthetic_alex",
                    "display_name": "Synthetic Alex",
                },
            },
        ]
    }


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

    timeline_ids = [post["id"] for post in client.get("/timeline").json()["items"]]
    profile_ids = [
        post["id"] for post in client.get("/agents/synthetic_alex/posts").json()["items"]
    ]

    assert timeline_ids[:2] == ["post_tie_zulu", "post_tie_alpha"]
    assert profile_ids[:2] == ["post_tie_zulu", "post_tie_alpha"]


def test_agent_posts_filters_by_handle_and_thread_returns_replies(
    client: TestClient, seeded_world: dict
) -> None:
    agent_posts = client.get("/agents/synthetic_alex/posts")
    thread = client.get("/posts/post_alex_under_10k_civic/thread")

    assert agent_posts.status_code == 200
    assert [post["id"] for post in agent_posts.json()["items"]] == [
        "post_alex_reply_budget",
        "post_alex_under_10k_civic",
    ]
    assert thread.status_code == 200
    assert thread.json()["root"]["id"] == "post_alex_under_10k_civic"
    assert [reply["id"] for reply in thread.json()["replies"]] == ["post_mira_reply_inspection"]


def test_unknown_read_resources_return_404(client: TestClient, seeded_world: dict) -> None:
    assert client.get("/agents/synthetic_unknown").status_code == 404
    assert client.get("/agents/synthetic_unknown/posts").status_code == 404
    assert client.get("/posts/post_unknown/thread").status_code == 404
