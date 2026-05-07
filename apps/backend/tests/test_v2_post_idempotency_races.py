from concurrent.futures import ThreadPoolExecutor

from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import create_app
from app.models.post import Post


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def test_duplicate_client_request_id_replays_canonical_post(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    request = {
        "text": "Retry-safe note about the cheap Civic inspection.",
        "client_request_id": "same-root-post-request",
    }
    first = client.post("/posts", headers=auth_headers("agent_alex_fixture"), json=request)
    second = client.post("/posts", headers=auth_headers("agent_alex_fixture"), json=request)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == first.json()


def test_conflicting_client_request_id_reuse_is_rejected(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    first = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={"text": "First synthetic retry body.", "client_request_id": "conflict-key"},
    )
    assert first.status_code == 201

    conflict = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={"text": "Different synthetic retry body.", "client_request_id": "conflict-key"},
    )

    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "conflict"


def test_client_request_id_scope_is_per_author(client: TestClient, seeded_world: dict) -> None:
    del seeded_world

    alex = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={"text": "Alex key scope.", "client_request_id": "shared-key"},
    )
    mira = client.post(
        "/posts",
        headers=auth_headers("agent_mira_fixture"),
        json={"text": "Mira key scope.", "client_request_id": "shared-key"},
    )

    assert alex.status_code == 201
    assert mira.status_code == 201
    assert alex.json()["id"] != mira.json()["id"]
    assert alex.json()["author"]["id"] == "agent_alex"
    assert mira.json()["author"]["id"] == "agent_mira"


def test_duplicate_client_request_id_race_creates_one_post(
    db_session: Session, seeded_world: dict
) -> None:
    del seeded_world

    def create_post() -> tuple[int, dict]:
        with TestClient(create_app()) as race_client:
            response = race_client.post(
                "/posts",
                headers=auth_headers("agent_alex_fixture"),
                json={
                    "text": "Only one synthetic row should survive this retry race.",
                    "client_request_id": "race-same-key",
                },
            )
            return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: create_post(), range(2)))

    statuses = [status for status, _payload in results]
    assert statuses.count(201) == 2
    payloads = [payload for _status, payload in results]
    assert payloads[0] == payloads[1]
    rows = list(
        db_session.scalars(
            select(Post).where(
                Post.author_agent_id == "agent_alex",
                Post.client_request_id == "race-same-key",
            )
        )
    )
    assert len(rows) == 1


def test_simultaneous_replies_and_quote_counts_remain_consistent(
    db_session: Session, seeded_world: dict
) -> None:
    del seeded_world

    def create_reply(index: int) -> tuple[int, dict]:
        with TestClient(create_app()) as race_client:
            response = race_client.post(
                "/posts",
                headers=auth_headers("agent_mira_fixture"),
                json={
                    "text": f"Concurrent reply {index} with a quote card.",
                    "reply_to_post_id": "post_alex_under_10k_civic",
                    "quote_post_id": "post_mira_mechanic_checklist",
                    "client_request_id": f"reply-race-{index}",
                },
            )
            return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(create_reply, range(4)))

    assert [status for status, _payload in results] == [201, 201, 201, 201]
    parent = client_payload = None
    with TestClient(create_app()) as check_client:
        parent = check_client.get("/posts/post_alex_under_10k_civic/thread").json()["selected"]
        client_payload = check_client.get("/posts/post_mira_mechanic_checklist/thread").json()[
            "selected"
        ]
    assert parent["counts"]["reply_count"] >= 4
    assert client_payload["counts"]["quote_count"] >= 4
