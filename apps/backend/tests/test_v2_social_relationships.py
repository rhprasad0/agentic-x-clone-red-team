from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient

from app.main import create_app


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def assert_v2_error(response, expected_status: int, expected_code: str) -> None:
    assert response.status_code == expected_status
    payload = response.json()
    assert payload["error"]["code"] == expected_code
    response_text = response.text
    assert "IntegrityError" not in response_text
    assert "SQL" not in response_text
    assert "token_hash" not in response_text


def assert_relationship_payload(
    payload: dict,
    *,
    relationship_type: str,
    actor_id: str,
    target_id: str,
) -> None:
    assert set(payload) == {"id", "relationship_type", "actor", "target_id", "created_at"}
    assert payload["id"].startswith(f"{relationship_type}_")
    assert payload["relationship_type"] == relationship_type
    assert payload["actor"]["id"] == actor_id
    assert payload["target_id"] == target_id
    assert set(payload["actor"]) == {"id", "handle", "display_name", "avatar_seed"}


def test_relationship_routes_are_registered_and_require_bearer_auth() -> None:
    with TestClient(create_app()) as unauthenticated_client:
        for method, path in (
            ("POST", "/posts/post_alex_under_10k_civic/like"),
            ("DELETE", "/posts/post_alex_under_10k_civic/like"),
            ("POST", "/posts/post_alex_under_10k_civic/repost"),
            ("DELETE", "/posts/post_alex_under_10k_civic/repost"),
            ("POST", "/agents/synthetic_mira/follow"),
            ("DELETE", "/agents/synthetic_mira/follow"),
        ):
            response = unauthenticated_client.request(method, path, json={})
            assert_v2_error(response, 401, "unauthorized")


def test_like_and_repost_routes_are_idempotent_and_delete_to_204(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    first_like = client.post(
        "/posts/post_alex_under_10k_civic/like",
        headers=auth_headers("agent_mira_fixture"),
        json={},
    )
    duplicate_like = client.post(
        "/posts/post_alex_under_10k_civic/like",
        headers=auth_headers("agent_mira_fixture"),
        json={},
    )

    assert first_like.status_code == 201
    assert duplicate_like.status_code == 200
    assert duplicate_like.json() == first_like.json()
    assert_relationship_payload(
        first_like.json(),
        relationship_type="like",
        actor_id="agent_mira",
        target_id="post_alex_under_10k_civic",
    )

    first_repost = client.post(
        "/posts/post_alex_under_10k_civic/repost",
        headers=auth_headers("agent_mira_fixture"),
        json={},
    )
    duplicate_repost = client.post(
        "/posts/post_alex_under_10k_civic/repost",
        headers=auth_headers("agent_mira_fixture"),
        json={},
    )

    assert first_repost.status_code == 201
    assert duplicate_repost.status_code == 200
    assert duplicate_repost.json() == first_repost.json()
    assert_relationship_payload(
        first_repost.json(),
        relationship_type="repost",
        actor_id="agent_mira",
        target_id="post_alex_under_10k_civic",
    )

    assert (
        client.delete(
            "/posts/post_alex_under_10k_civic/like",
            headers=auth_headers("agent_mira_fixture"),
        ).status_code
        == 204
    )
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
            "/posts/post_alex_under_10k_civic/repost",
            headers=auth_headers("agent_mira_fixture"),
        ).status_code
        == 204
    )


def test_follow_route_uses_token_actor_and_path_target_only(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    first_follow = client.post(
        "/agents/synthetic_mira/follow",
        headers=auth_headers("agent_alex_fixture"),
        json={},
    )
    duplicate_follow = client.post(
        "/agents/synthetic_mira/follow",
        headers=auth_headers("agent_alex_fixture"),
        json={},
    )

    assert first_follow.status_code == 201
    assert duplicate_follow.status_code == 200
    assert duplicate_follow.json() == first_follow.json()
    assert_relationship_payload(
        first_follow.json(),
        relationship_type="follow",
        actor_id="agent_alex",
        target_id="agent_mira",
    )

    assert (
        client.delete(
            "/agents/synthetic_mira/follow",
            headers=auth_headers("agent_alex_fixture"),
        ).status_code
        == 204
    )
    assert (
        client.delete(
            "/agents/synthetic_mira/follow",
            headers=auth_headers("agent_alex_fixture"),
        ).status_code
        == 204
    )


def test_unknown_targets_return_404_but_absent_relationship_deletes_still_204(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    assert_v2_error(
        client.post(
            "/posts/post_missing_fixture/like",
            headers=auth_headers("agent_alex_fixture"),
            json={},
        ),
        404,
        "not_found",
    )
    assert_v2_error(
        client.request(
            "DELETE",
            "/posts/post_missing_fixture/repost",
            headers=auth_headers("agent_alex_fixture"),
        ),
        404,
        "not_found",
    )
    assert_v2_error(
        client.post(
            "/agents/synthetic_missing/follow",
            headers=auth_headers("agent_alex_fixture"),
            json={},
        ),
        404,
        "not_found",
    )

    absent_like_delete = client.delete(
        "/posts/post_mira_mechanic_checklist/like",
        headers=auth_headers("agent_alex_fixture"),
    )
    absent_repost_delete = client.delete(
        "/posts/post_mira_mechanic_checklist/repost",
        headers=auth_headers("agent_alex_fixture"),
    )
    absent_follow_delete = client.delete(
        "/agents/synthetic_mira/follow",
        headers=auth_headers("agent_alex_fixture"),
    )

    assert absent_like_delete.status_code == 204
    assert absent_repost_delete.status_code == 204
    assert absent_follow_delete.status_code == 204


def test_self_like_and_repost_are_allowed_but_self_follow_is_rejected(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    self_like = client.post(
        "/posts/post_alex_under_10k_civic/like",
        headers=auth_headers("agent_alex_fixture"),
        json={},
    )
    self_repost = client.post(
        "/posts/post_alex_under_10k_civic/repost",
        headers=auth_headers("agent_alex_fixture"),
        json={},
    )
    self_follow = client.post(
        "/agents/synthetic_alex/follow",
        headers=auth_headers("agent_alex_fixture"),
        json={},
    )

    assert self_like.status_code == 201
    assert self_repost.status_code == 201
    assert_v2_error(self_follow, 409, "conflict")


def test_relationship_routes_reject_wrong_authority(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    for method, path in (
        ("POST", "/posts/post_alex_under_10k_civic/like"),
        ("DELETE", "/posts/post_alex_under_10k_civic/like"),
        ("POST", "/posts/post_alex_under_10k_civic/repost"),
        ("DELETE", "/posts/post_alex_under_10k_civic/repost"),
        ("POST", "/agents/synthetic_mira/follow"),
        ("DELETE", "/agents/synthetic_mira/follow"),
    ):
        response = client.request(
            method,
            path,
            headers=auth_headers("harness_fixture"),
            json={} if method == "POST" else None,
        )
        assert_v2_error(response, 403, "forbidden")


def test_post_relationship_bodies_allow_only_optional_client_request_id(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world
    protected_body = {
        "client_request_id": "relationship-body-allowlist",
        "text": "Client text is not accepted on relationship routes.",
        "agent_id": "agent_mira",
        "actor_id": "agent_mira",
        "author_agent_id": "agent_mira",
        "post_id": "post_mira_mechanic_checklist",
        "target_id": "post_mira_mechanic_checklist",
        "created_at": "2026-05-07T12:00:00Z",
        "updated_at": "2026-05-07T12:00:00Z",
        "counts": {"like_count": 99},
        "metadata_json": {"operator_note": "relationship_marker_do_not_echo"},
        "role": "harness",
        "status": "enabled",
        "authority_type": "harness",
    }

    for path in (
        "/posts/post_alex_under_10k_civic/like",
        "/posts/post_alex_under_10k_civic/repost",
        "/agents/synthetic_mira/follow",
    ):
        rejected = client.post(
            path,
            headers=auth_headers("agent_alex_fixture"),
            json=protected_body,
        )
        assert_v2_error(rejected, 422, "validation_error")
        assert "relationship_marker_do_not_echo" not in rejected.text
        assert "Client text" not in rejected.text

    accepted = client.post(
        "/posts/post_alex_under_10k_civic/like",
        headers=auth_headers("agent_alex_fixture"),
        json={"client_request_id": "relationship-body-accepted"},
    )
    assert accepted.status_code == 201


def test_delete_relationship_bodies_accept_no_fields(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    for path in (
        "/posts/post_alex_under_10k_civic/like",
        "/posts/post_alex_under_10k_civic/repost",
        "/agents/synthetic_mira/follow",
    ):
        rejected = client.request(
            "DELETE",
            path,
            headers=auth_headers("agent_alex_fixture"),
            json={"client_request_id": "delete-body-rejected"},
        )
        assert_v2_error(rejected, 422, "validation_error")


def test_relationship_client_request_id_replays_and_is_scoped_by_operation_and_target(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    request = {"client_request_id": "shared-relationship-key"}
    first_like = client.post(
        "/posts/post_alex_under_10k_civic/like",
        headers=auth_headers("agent_mira_fixture"),
        json=request,
    )
    retry_like = client.post(
        "/posts/post_alex_under_10k_civic/like",
        headers=auth_headers("agent_mira_fixture"),
        json=request,
    )
    same_key_other_operation = client.post(
        "/posts/post_alex_under_10k_civic/repost",
        headers=auth_headers("agent_mira_fixture"),
        json=request,
    )
    same_key_other_target = client.post(
        "/posts/post_mira_mechanic_checklist/like",
        headers=auth_headers("agent_mira_fixture"),
        json=request,
    )
    same_key_other_actor = client.post(
        "/posts/post_alex_under_10k_civic/like",
        headers=auth_headers("agent_alex_fixture"),
        json=request,
    )

    assert first_like.status_code == 201
    assert retry_like.status_code == 200
    assert retry_like.json() == first_like.json()
    assert same_key_other_operation.status_code == 201
    assert same_key_other_target.status_code == 201
    assert same_key_other_actor.status_code == 201


def test_relationship_client_request_id_conflicts_are_bounded(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    first = client.post(
        "/posts/post_alex_under_10k_civic/like",
        headers=auth_headers("agent_mira_fixture"),
        json={"client_request_id": "relationship-conflict-key"},
    )
    conflict = client.post(
        "/posts/post_alex_under_10k_civic/like",
        headers=auth_headers("agent_mira_fixture"),
        json={"client_request_id": " relationship-conflict-key "},
    )

    assert first.status_code == 201
    assert_v2_error(conflict, 409, "conflict")
