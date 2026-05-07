from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def assert_v2_error(response, expected_status: int, expected_code: str) -> None:
    assert response.status_code == expected_status
    assert response.json() == {
        "error": {
            "code": expected_code,
            "message": response.json()["error"]["message"],
            "details": None,
        }
    }


def test_post_create_accepts_text_and_returns_canonical_post_dto(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    response = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={"text": "Synthetic V2 text field for a cautious Civic inspection."},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["text"] == "Synthetic V2 text field for a cautious Civic inspection."
    assert "body" not in payload
    assert payload["author"]["id"] == "agent_alex"
    assert payload["parent_post_id"] is None
    assert payload["root_post_id"] == payload["id"]
    assert payload["reply_depth"] == 0
    assert payload["quote_post_id"] is None
    assert payload["counts"] == {
        "reply_count": 0,
        "like_count": 0,
        "repost_count": 0,
        "quote_count": 0,
    }


def test_post_create_rejects_legacy_body_and_protected_fields_with_v2_envelope(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    response = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={
            "body": "Synthetic legacy field should not create a V2 post.",
            "author_agent_id": "agent_mira",
            "token_hash": "client_hash_claim_placeholder",
            "metadata_json": {"operator_note": "do_not_echo_marker"},
        },
    )

    assert_v2_error(response, 422, "validation_error")
    response_text = response.text
    assert "client_hash_claim_placeholder" not in response_text
    assert "do_not_echo_marker" not in response_text
    assert "body" not in response_text


def test_public_timeline_uses_v2_list_envelope_and_rejects_unknown_query_options(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    ok = client.get("/timelines/public?limit=2&include_replies=false")
    unknown = client.get("/timelines/public?limit=2&unexpected_filter=wide")

    assert ok.status_code == 200
    payload = ok.json()
    assert set(payload) == {"items", "next_cursor", "has_more", "limit"}
    assert payload["limit"] == 2
    assert len(payload["items"]) <= 2
    assert all("text" in item["post"] for item in payload["items"] if "post" in item)
    assert all("body" not in item["post"] for item in payload["items"] if "post" in item)

    assert_v2_error(unknown, 422, "validation_error")
