import json
import re
from datetime import UTC, datetime

from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import hash_bearer_token
from app.core.config import REPO_ROOT
from app.models.agent import Agent
from app.models.auth_token_hash import AuthTokenHash

BEARER_VALUE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def signup_payload(handle: str = "civic_skeptic") -> dict[str, str]:
    return {
        "handle": handle,
        "display_name": "Civic Skeptic",
        "bio": "Synthetic under-10k inspection notes.",
        "persona_seed": "Fictional used-car reliability chatter.",
        "avatar_seed": "civic_skeptic_avatar",
    }


def signup(client: TestClient, handle: str = "civic_skeptic") -> dict:
    response = client.post("/agents/signup", json=signup_payload(handle))
    assert response.status_code == 201
    return response.json()


def env_example_value(name: str) -> str:
    for line in (REPO_ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1]
    raise AssertionError(f"missing {name} in .env.example")


def assert_generic_error(response, expected_status: int, expected_code: str) -> None:
    assert response.status_code == expected_status
    body = response.json()
    assert body == {
        "error": {
            "code": expected_code,
            "message": body["error"]["message"],
            "details": None,
        }
    }
    text = response.text.lower()
    assert "token_hash" not in text
    assert "authorization" not in text
    assert "revoked" not in text
    assert "disabled" not in text


def test_signup_returns_display_once_token_and_persists_only_hash(
    client: TestClient, db_session: Session
) -> None:
    response = client.post(
        "/agents/signup",
        json=signup_payload(" Civic_Skeptic "),
    )

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    token = body["token"]
    agent_payload = body["agent"]

    assert body["token_type"] == "Bearer"
    assert isinstance(token, str)
    assert len(token) >= 32
    assert BEARER_VALUE_PATTERN.fullmatch(token)
    assert body["issued_at"].endswith("Z")
    assert agent_payload["handle"] == "civic_skeptic"
    assert agent_payload["display_name"] == "Civic Skeptic"
    assert agent_payload["bio"] == "Synthetic under-10k inspection notes."
    assert agent_payload["post_count"] == 0
    assert agent_payload["follower_count"] == 0

    stored_agent = db_session.scalar(
        select(Agent).where(Agent.handle_normalized == "civic_skeptic")
    )
    assert stored_agent is not None
    assert stored_agent.id == agent_payload["id"]
    assert stored_agent.is_fixture is False
    assert stored_agent.disabled_at is None
    assert stored_agent.metadata_json == {}

    stored_token = db_session.scalar(
        select(AuthTokenHash).where(AuthTokenHash.agent_id == stored_agent.id)
    )
    assert stored_token is not None
    assert stored_token.authority_type == "synthetic_agent"
    assert stored_token.enabled is True
    assert stored_token.revoked_at is None
    assert stored_token.token_hash == hash_bearer_token(token)
    assert stored_token.token_hash != token
    assert token not in stored_token.token_hash
    assert stored_token.token_prefix is not None
    assert stored_token.token_prefix != token
    assert len(stored_token.token_prefix) <= 16

    profile = client.get("/agents/civic_skeptic")
    agent_list = client.get("/agents")

    assert profile.status_code == 200
    assert agent_list.status_code == 200
    public_text = profile.text + agent_list.text
    assert token not in public_text
    assert stored_token.token_hash not in public_text
    assert "token_hash" not in public_text


def test_signup_token_authorizes_agent_posts_by_hash_lookup(
    client: TestClient,
) -> None:
    body = signup(client, "corolla_counter")
    token = body["token"]

    created = client.post(
        "/posts",
        headers={"Authorization": f"Bearer {token}"},
        json={"text": "Synthetic Corolla note after signup."},
    )

    assert created.status_code == 201
    assert created.json()["author"]["id"] == body["agent"]["id"]
    assert created.json()["author"]["handle"] == "corolla_counter"


def test_env_example_fixture_placeholder_tokens_resolve_through_auth_token_hashes(
    client: TestClient, harness_headers: dict[str, str]
) -> None:
    assert client.post("/fixtures/reset", headers=harness_headers).status_code == 200
    alex_token = env_example_value("XCLONE_AGENT_ALEX_TOKEN")
    harness_token = env_example_value("XCLONE_HARNESS_TOKEN")

    agent_post = client.post(
        "/posts",
        headers={"Authorization": f"Bearer {alex_token}"},
        json={"text": "Synthetic fixture env placeholder token continuity."},
    )
    fixture_reset = client.post(
        "/fixtures/reset",
        headers={"Authorization": f"Bearer {harness_token}"},
    )

    assert alex_token == FIXTURE_CREDENTIAL_VALUES["agent_alex_fixture"]
    assert harness_token == FIXTURE_CREDENTIAL_VALUES["harness_fixture"]
    assert agent_post.status_code == 201
    assert fixture_reset.status_code == 200


def test_signup_rejects_duplicate_reserved_and_invalid_handles(
    client: TestClient, db_session: Session
) -> None:
    from app.api.routes import agents as agents_routes

    expected_reserved_samples = {
        "api",
        "admin",
        "twitter",
        "me",
        "carbot_oracle",
    }
    assert expected_reserved_samples <= agents_routes.SIGNUP_RESERVED_HANDLES

    for handle in expected_reserved_samples:
        response = client.post("/agents/signup", json=signup_payload(handle))
        assert response.status_code == 409
        assert (
            db_session.scalar(
                select(func.count(Agent.id)).where(Agent.handle_normalized == handle)
            )
            == 0
        )

    first = client.post("/agents/signup", json=signup_payload("altima_auditor"))
    duplicate = client.post("/agents/signup", json=signup_payload("ALTIMA_AUDITOR"))
    assert first.status_code == 201
    assert duplicate.status_code == 409

    invalid_payloads = [
        signup_payload("ab"),
        signup_payload("_civic"),
        signup_payload("civic_"),
        signup_payload("civic__skeptic"),
        signup_payload("civic-skeptic"),
        {**signup_payload("blank_display"), "display_name": "   "},
        {**signup_payload("long_display"), "display_name": "D" * 51},
        {**signup_payload("long_bio"), "bio": "B" * 161},
        {**signup_payload("long_persona"), "persona_seed": "P" * 401},
        {**signup_payload("long_avatar"), "avatar_seed": "A" * 65},
    ]
    for payload in invalid_payloads:
        response = client.post("/agents/signup", json=payload)
        assert_generic_error(response, 422, "validation_error")


def test_signup_rejects_protected_fields_without_echoing_values(
    client: TestClient,
) -> None:
    protected_values = {
        "id": "agent_client_supplied",
        "agent_id": "agent_fixture_claim",
        "authority_type": "harness",
        "is_fixture": True,
        "disabled_at": "2026-05-07T12:00:00Z",
        "created_at": "2026-05-07T12:00:00Z",
        "token": "client_token_claim_placeholder",
        "token_hash": "client_hash_claim_placeholder",
        "token_prefix": "client_prefix_claim",
        "post_count": 42,
        "follower_count": 42,
        "following_count": 42,
        "metadata_json": {"role": "system"},
    }

    for field, value in protected_values.items():
        response = client.post(
            "/agents/signup",
            json={**signup_payload(f"field_{field[:10]}"), field: value},
        )

        assert_generic_error(response, 422, "validation_error")
        assert str(value) not in response.text


def test_signup_guardrail_limits_dynamic_non_fixture_agents(
    client: TestClient, monkeypatch
) -> None:
    from app.api.routes import agents as agents_routes

    class TinySignupSettings:
        signup_max_dynamic_agents = 1

    monkeypatch.setattr(agents_routes, "get_settings", lambda: TinySignupSettings())

    first = client.post("/agents/signup", json=signup_payload("budget_civic"))
    second = client.post("/agents/signup", json=signup_payload("budget_corolla"))

    assert first.status_code == 201
    assert_generic_error(second, 429, "resource_limit")


def test_auth_lookup_rejects_missing_malformed_unknown_disabled_revoked_and_wrong_authority(
    client: TestClient, db_session: Session, harness_headers: dict[str, str]
) -> None:
    reset = client.post("/fixtures/reset", headers=harness_headers)
    assert reset.status_code == 200
    body = signup(client, "token_checker")
    token = body["token"]

    missing = client.post("/posts", json={"text": "Synthetic denied missing token."})
    malformed = client.post(
        "/posts",
        headers={"Authorization": f"Basic {token}"},
        json={"text": "Synthetic denied malformed token."},
    )
    unknown = client.post(
        "/posts",
        headers={"Authorization": "Bearer unknown_fixture_token_placeholder"},
        json={"text": "Synthetic denied unknown token."},
    )

    stored_token = db_session.scalar(
        select(AuthTokenHash).where(AuthTokenHash.token_hash == hash_bearer_token(token))
    )
    assert stored_token is not None
    stored_token.enabled = False
    db_session.commit()
    disabled = client.post(
        "/posts",
        headers={"Authorization": f"Bearer {token}"},
        json={"text": "Synthetic denied disabled token."},
    )

    stored_token.enabled = True
    stored_token.revoked_at = datetime(2026, 5, 7, 12, 0, tzinfo=UTC)
    db_session.commit()
    revoked = client.post(
        "/posts",
        headers={"Authorization": f"Bearer {token}"},
        json={"text": "Synthetic denied revoked token."},
    )

    wrong_authority = client.post(
        "/posts",
        headers=auth_headers("harness_fixture"),
        json={"text": "Synthetic denied harness token."},
    )

    for response in [missing, malformed, unknown, disabled, revoked]:
        assert_generic_error(response, 401, "unauthorized")
        assert token not in response.text
    assert_generic_error(wrong_authority, 403, "forbidden")


def test_fixture_reset_removes_dynamic_signup_agents_and_generated_token_hashes(
    client: TestClient, db_session: Session, harness_headers: dict[str, str]
) -> None:
    assert client.post("/fixtures/reset", headers=harness_headers).status_code == 200
    body = signup(client, "reset_cleaner")
    token = body["token"]
    token_hash = hash_bearer_token(token)

    created = client.post(
        "/posts",
        headers={"Authorization": f"Bearer {token}"},
        json={"text": "Synthetic dynamic post removed by reset."},
    )
    assert created.status_code == 201
    assert db_session.get(Agent, body["agent"]["id"]) is not None
    assert (
        db_session.scalar(
            select(func.count(AuthTokenHash.id)).where(AuthTokenHash.token_hash == token_hash)
        )
        == 1
    )

    reset = client.post("/fixtures/reset", headers=harness_headers)

    assert reset.status_code == 200
    reset_text = json.dumps(reset.json(), sort_keys=True)
    assert token not in reset_text
    assert token_hash not in reset_text
    assert db_session.get(Agent, body["agent"]["id"]) is None
    assert (
        db_session.scalar(
            select(func.count(AuthTokenHash.id)).where(AuthTokenHash.token_hash == token_hash)
        )
        == 0
    )
    assert (
        db_session.scalar(select(func.count(Agent.id)).where(Agent.is_fixture.is_(True))) == 2
    )
    assert db_session.scalar(select(func.count(AuthTokenHash.id))) == 3

    fixture_post = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={"text": "Synthetic fixture token still works after reset."},
    )
    assert fixture_post.status_code == 201
