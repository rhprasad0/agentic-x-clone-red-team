from concurrent.futures import ThreadPoolExecutor
from typing import Any

from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.main import create_app
from app.models.follow import Follow
from app.models.like import Like
from app.models.repost import Repost


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def request_from_fresh_client(
    method: str,
    path: str,
    *,
    token_label: str,
    json_body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any] | None, str]:
    with TestClient(create_app()) as race_client:
        response = race_client.request(
            method,
            path,
            headers=auth_headers(token_label),
            json=json_body,
        )
        if response.content:
            return response.status_code, response.json(), response.text
        return response.status_code, None, response.text


def relationship_count(db_session: Session, model, *criteria) -> int:
    db_session.rollback()
    return db_session.scalar(select(func.count(model.id)).where(*criteria)) or 0


def get_post_counts(post_id: str) -> dict[str, int]:
    with TestClient(create_app()) as check_client:
        response = check_client.get(f"/posts/{post_id}/thread")
        assert response.status_code == 200
        return response.json()["selected"]["counts"]


def get_agent_profile(handle: str) -> dict[str, Any]:
    with TestClient(create_app()) as check_client:
        response = check_client.get(f"/agents/{handle}")
        assert response.status_code == 200
        return response.json()


def assert_no_raw_storage_error(results: list[tuple[int, dict[str, Any] | None, str]]) -> None:
    for _status, payload, text in results:
        assert payload is None or payload.get("error", {}).get("code") != "error"
        assert "IntegrityError" not in text
        assert "sqlalchemy" not in text.lower()
        assert "duplicate key" not in text.lower()


def test_concurrent_duplicate_relationship_posts_create_one_row_and_stable_counts(
    db_session: Session, seeded_world: dict
) -> None:
    del seeded_world

    race_specs = [
        (
            "POST",
            "/posts/post_mira_mechanic_checklist/like",
            "agent_alex_fixture",
            Like,
            (Like.agent_id == "agent_alex", Like.post_id == "post_mira_mechanic_checklist"),
        ),
        (
            "POST",
            "/posts/post_mira_mechanic_checklist/repost",
            "agent_alex_fixture",
            Repost,
            (Repost.agent_id == "agent_alex", Repost.post_id == "post_mira_mechanic_checklist"),
        ),
        (
            "POST",
            "/agents/synthetic_mira/follow",
            "agent_alex_fixture",
            Follow,
            (
                Follow.follower_agent_id == "agent_alex",
                Follow.followee_agent_id == "agent_mira",
            ),
        ),
    ]

    for method, path, token_label, model, criteria in race_specs:
        def send_request(
            _index: int,
            method: str = method,
            path: str = path,
            token_label: str = token_label,
        ) -> tuple[int, dict[str, Any] | None, str]:
            return request_from_fresh_client(
                method,
                path,
                token_label=token_label,
                json_body={},
            )

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(send_request, range(4)))

        statuses = [status for status, _payload, _text in results]
        assert set(statuses).issubset({200, 201})
        assert statuses.count(201) == 1
        assert relationship_count(db_session, model, *criteria) == 1
        assert_no_raw_storage_error(results)

    counts = get_post_counts("post_mira_mechanic_checklist")
    assert counts["like_count"] == 1
    assert counts["repost_count"] == 1
    profile = get_agent_profile("synthetic_mira")
    assert profile["follower_count"] == 1


def test_concurrent_idempotent_relationship_retries_replay_canonical_response(
    db_session: Session, seeded_world: dict
) -> None:
    del seeded_world

    race_specs = [
        (
            "/posts/post_alex_under_10k_civic/like",
            "same-key-like-race",
            Like,
            (Like.agent_id == "agent_mira", Like.post_id == "post_alex_under_10k_civic"),
        ),
        (
            "/posts/post_alex_under_10k_civic/repost",
            "same-key-repost-race",
            Repost,
            (Repost.agent_id == "agent_mira", Repost.post_id == "post_alex_under_10k_civic"),
        ),
        (
            "/agents/synthetic_alex/follow",
            "same-key-follow-race",
            Follow,
            (
                Follow.follower_agent_id == "agent_mira",
                Follow.followee_agent_id == "agent_alex",
            ),
        ),
    ]

    for path, client_request_id, model, criteria in race_specs:
        def send_request(
            _index: int,
            path: str = path,
            client_request_id: str = client_request_id,
        ) -> tuple[int, dict[str, Any] | None, str]:
            return request_from_fresh_client(
                "POST",
                path,
                token_label="agent_mira_fixture",
                json_body={"client_request_id": client_request_id},
            )

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(send_request, range(4)))

        statuses = [status for status, _payload, _text in results]
        payloads = [payload for _status, payload, _text in results]
        assert set(statuses).issubset({200, 201})
        assert statuses.count(201) == 1
        assert all(payload == payloads[0] for payload in payloads)
        assert relationship_count(db_session, model, *criteria) == 1
        assert_no_raw_storage_error(results)


def test_concurrent_duplicate_relationship_deletes_leave_zero_rows_and_stable_counts(
    db_session: Session, seeded_world: dict
) -> None:
    del seeded_world

    setup_requests = [
        (
            "POST",
            "/posts/post_alex_under_10k_civic/like",
            "agent_mira_fixture",
            Like,
            (Like.agent_id == "agent_mira", Like.post_id == "post_alex_under_10k_civic"),
        ),
        (
            "POST",
            "/posts/post_alex_under_10k_civic/repost",
            "agent_mira_fixture",
            Repost,
            (Repost.agent_id == "agent_mira", Repost.post_id == "post_alex_under_10k_civic"),
        ),
        (
            "POST",
            "/agents/synthetic_alex/follow",
            "agent_mira_fixture",
            Follow,
            (
                Follow.follower_agent_id == "agent_mira",
                Follow.followee_agent_id == "agent_alex",
            ),
        ),
    ]

    for method, path, token_label, model, criteria in setup_requests:
        status, _payload, _text = request_from_fresh_client(
            method,
            path,
            token_label=token_label,
            json_body={},
        )
        assert status == 201
        assert relationship_count(db_session, model, *criteria) == 1

    delete_specs = [
        (
            "/posts/post_alex_under_10k_civic/like",
            Like,
            (Like.agent_id == "agent_mira", Like.post_id == "post_alex_under_10k_civic"),
        ),
        (
            "/posts/post_alex_under_10k_civic/repost",
            Repost,
            (Repost.agent_id == "agent_mira", Repost.post_id == "post_alex_under_10k_civic"),
        ),
        (
            "/agents/synthetic_alex/follow",
            Follow,
            (
                Follow.follower_agent_id == "agent_mira",
                Follow.followee_agent_id == "agent_alex",
            ),
        ),
    ]

    for path, model, criteria in delete_specs:
        def send_request(
            _index: int,
            path: str = path,
        ) -> tuple[int, dict[str, Any] | None, str]:
            return request_from_fresh_client(
                "DELETE",
                path,
                token_label="agent_mira_fixture",
            )

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(send_request, range(4)))

        assert [status for status, _payload, _text in results] == [204, 204, 204, 204]
        assert relationship_count(db_session, model, *criteria) == 0
        assert_no_raw_storage_error(results)

    counts = get_post_counts("post_alex_under_10k_civic")
    assert counts["like_count"] == 0
    assert counts["repost_count"] == 0
    assert get_agent_profile("synthetic_alex")["follower_count"] == 0
