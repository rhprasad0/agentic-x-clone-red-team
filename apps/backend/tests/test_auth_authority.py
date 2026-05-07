from collections.abc import Iterator

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.core.auth import hash_bearer_token
from app.core.config import REPO_ROOT, get_settings
from app.main import create_app
from app.models.agent import Agent
from app.models.auth_token_hash import AuthTokenHash
from app.services.fixtures import DELETE_ORDER

ALEMBIC_CONFIG = REPO_ROOT / "apps" / "backend" / "alembic.ini"
AGENT_ALEX_TOKEN = "agent_alex_fixture_token_placeholder"
AGENT_MIRA_TOKEN = "agent_mira_fixture_token_placeholder"
HARNESS_TOKEN = "harness_fixture_token_placeholder"
DISABLED_TOKEN = "disabled_fixture_token_placeholder"


@pytest.fixture()
def db_session() -> Iterator[Session]:
    alembic_cfg = Config(str(ALEMBIC_CONFIG))
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(get_settings().database_url)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        for model in DELETE_ORDER:
            session.execute(delete(model))
        session.add_all(
            [
                Agent(
                    id="agent_alex",
                    handle="synthetic_alex",
                    handle_normalized="synthetic_alex",
                    display_name="Synthetic Alex",
                ),
                Agent(
                    id="agent_mira",
                    handle="synthetic_mira",
                    handle_normalized="synthetic_mira",
                    display_name="Synthetic Mira",
                ),
                AuthTokenHash(
                    id="auth_agent_alex_fixture",
                    label="agent_alex_fixture",
                    token_hash=hash_bearer_token(AGENT_ALEX_TOKEN),
                    authority_type="synthetic_agent",
                    agent_id="agent_alex",
                    enabled=True,
                ),
                AuthTokenHash(
                    id="auth_agent_mira_fixture",
                    label="agent_mira_fixture",
                    token_hash=hash_bearer_token(AGENT_MIRA_TOKEN),
                    authority_type="synthetic_agent",
                    agent_id="agent_mira",
                    enabled=True,
                ),
                AuthTokenHash(
                    id="auth_harness_fixture",
                    label="harness_fixture",
                    token_hash=hash_bearer_token(HARNESS_TOKEN),
                    authority_type="harness",
                    enabled=True,
                ),
                AuthTokenHash(
                    id="auth_disabled_fixture",
                    label="disabled_fixture",
                    token_hash=hash_bearer_token(DISABLED_TOKEN),
                    authority_type="synthetic_agent",
                    agent_id="agent_alex",
                    enabled=False,
                ),
            ]
        )
        session.commit()
        yield session
    finally:
        session.rollback()
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    def override_db_session() -> Iterator[Session]:
        yield db_session

    from app.api.deps import get_db_session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_hash_bearer_token_is_stable_sha256_without_cleartext() -> None:
    hashed = hash_bearer_token(AGENT_ALEX_TOKEN)

    assert hashed == hash_bearer_token(AGENT_ALEX_TOKEN)
    assert len(hashed) == 64
    assert AGENT_ALEX_TOKEN not in hashed


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic agent_alex_fixture_token_placeholder"},
        bearer("invalid_fixture_token_placeholder"),
        bearer(DISABLED_TOKEN),
    ],
)
def test_missing_invalid_or_disabled_tokens_fail_closed(
    client: TestClient, headers: dict[str, str]
) -> None:
    response = client.post("/posts", headers=headers, json={"body": "Synthetic Civic note."})

    assert response.status_code == 401


def test_agent_post_authorship_comes_from_resolved_token(client: TestClient) -> None:
    response = client.post(
        "/posts",
        headers=bearer(AGENT_ALEX_TOKEN),
        json={"body": "Synthetic Civic inspection note."},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["author"]["id"] == "agent_alex"
    assert payload["author"]["handle"] == "synthetic_alex"
    assert payload["body"] == "Synthetic Civic inspection note."


def test_post_body_identity_fields_are_rejected_not_authoritative(client: TestClient) -> None:
    response = client.post(
        "/posts",
        headers=bearer(AGENT_ALEX_TOKEN),
        json={
            "body": "Synthetic spoof attempt.",
            "author_agent_id": "agent_mira",
            "handle": "synthetic_mira",
            "role": "harness",
            "status": "trusted",
            "metadata_json": {"server_owned": True},
        },
    )

    assert response.status_code == 422


def test_wrong_authority_tokens_fail_with_forbidden(client: TestClient) -> None:
    harness_post = client.post(
        "/posts",
        headers=bearer(HARNESS_TOKEN),
        json={"body": "Harness should not author feed posts."},
    )
    agent_seed = client.post("/fixtures/seed", headers=bearer(AGENT_ALEX_TOKEN))

    assert harness_post.status_code == 403
    assert agent_seed.status_code == 403


def test_harness_authority_can_reach_harness_only_fixture_route(client: TestClient) -> None:
    response = client.post("/fixtures/seed", headers=bearer(HARNESS_TOKEN))

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "agents": 2,
        "posts": 4,
        "scenario_runs": 1,
        "events": 2,
        "findings": 1,
        "auth_fixtures": 3,
        "auth_token_hashes": 3,
        "validation_runs": 1,
        "validation_events": 2,
    }
