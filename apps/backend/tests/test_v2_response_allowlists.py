import json

from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.post import Post


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


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
}


def assert_no_forbidden_public_keys(value) -> None:
    if isinstance(value, dict):
        assert FORBIDDEN_PUBLIC_KEYS.isdisjoint(value)
        for nested in value.values():
            assert_no_forbidden_public_keys(nested)
    elif isinstance(value, list):
        for item in value:
            assert_no_forbidden_public_keys(item)


def test_public_v2_read_responses_are_serialized_through_allowlist_dtos(
    client: TestClient, db_session: Session, seeded_world: dict
) -> None:
    del seeded_world
    unsafe_marker = "dto_allowlist_marker_do_not_echo"

    post = db_session.get(Post, "post_alex_under_10k_civic")
    assert post is not None
    post.metadata_json = {
        "operator_note": unsafe_marker,
        "token_hash": "hash_marker_do_not_echo",
    }
    db_session.commit()

    responses = [
        client.get("/agents/synthetic_alex"),
        client.get("/agents/synthetic_alex/posts"),
        client.get("/timelines/public"),
        client.get("/posts/post_alex_under_10k_civic/thread"),
    ]

    for response in responses:
        assert response.status_code == 200
        payload = response.json()
        payload_text = json.dumps(payload, sort_keys=True)
        assert_no_forbidden_public_keys(payload)
        assert unsafe_marker not in payload_text
        assert "hash_marker_do_not_echo" not in payload_text


def test_created_post_response_omits_protected_storage_and_auth_fields(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    response = client.post(
        "/posts",
        headers=auth_headers("agent_mira_fixture"),
        json={"text": "Synthetic response allowlist check for an old Corolla."},
    )

    assert response.status_code == 201
    payload = response.json()
    assert set(payload) == {
        "id",
        "author",
        "text",
        "created_at",
        "parent_post_id",
        "root_post_id",
        "reply_depth",
        "quote_post_id",
        "parent_summary",
        "quoted_post",
        "counts",
        "is_reply",
        "is_quote",
    }
    assert set(payload["author"]) == {"id", "handle", "display_name", "avatar_seed"}
    assert set(payload["counts"]) == {"reply_count", "like_count", "repost_count", "quote_count"}
    assert_no_forbidden_public_keys(payload)
