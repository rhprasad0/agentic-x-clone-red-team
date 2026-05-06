from fastapi.testclient import TestClient


def test_timeline_returns_seeded_top_level_posts_in_stable_reverse_chronological_order(
    client: TestClient, seeded_world: dict
) -> None:
    response = client.get("/timeline")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "post_mira_mechanic_checklist",
                "body": (
                    "Synthetic checklist: ask for service records, cold start video, and a "
                    "pre-purchase inspection before chasing any used-car deal."
                ),
                "created_at": "2026-05-06T12:10:00Z",
                "metadata_json": {"topic": "inspection"},
                "reply_count": 1,
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
                "metadata_json": {"topic": "under_10k"},
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
