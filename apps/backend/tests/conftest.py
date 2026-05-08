import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.core.auth import AUTHORITY_HARNESS, hash_bearer_token
from app.core.config import REPO_ROOT, get_settings
from app.main import create_app
from app.models.agent import Agent
from app.models.auth_token_hash import AuthTokenHash
from app.models.follow import Follow
from app.models.like import Like
from app.models.post import Post
from app.models.repost import Repost
from app.services.fixtures import DELETE_ORDER
from app.services.tokens import diagnostic_token_prefix

ALEMBIC_CONFIG = REPO_ROOT / "apps" / "backend" / "alembic.ini"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FIXTURE_CREDENTIAL_VALUES = {
    "agent_alex_fixture": "agent_alex_fixture_token_placeholder",
    "agent_mira_fixture": "agent_mira_fixture_token_placeholder",
    "harness_fixture": "harness_fixture_token_placeholder",
}


def seed_harness_fixture_token(session: Session) -> None:
    token = FIXTURE_CREDENTIAL_VALUES["harness_fixture"]
    session.add(
        AuthTokenHash(
            id="auth_harness_fixture",
            label="harness_fixture",
            token_hash=hash_bearer_token(token),
            token_prefix=diagnostic_token_prefix(token),
            authority_type=AUTHORITY_HARNESS,
            enabled=True,
        )
    )
    session.commit()


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
        session.commit()
        session.expunge_all()
        seed_harness_fixture_token(session)
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


@pytest.fixture()
def harness_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES['harness_fixture']}"}


@pytest.fixture()
def seeded_world(client: TestClient, harness_headers: dict[str, str]) -> dict:
    response = client.post("/fixtures/reset", headers=harness_headers)
    assert response.status_code == 200
    return response.json()


@pytest.fixture()
def v2_read_graph(db_session: Session, seeded_world: dict) -> dict[str, dict[str, str]]:
    """Synthetic V2 read graph with quotes, replies, likes, reposts, and follows."""

    del seeded_world
    base = datetime(2026, 5, 7, 12, 0, tzinfo=UTC)

    hidden_agent = Agent(
        id="agent_hidden_fixture",
        handle="synthetic_hidden",
        handle_normalized="synthetic_hidden",
        display_name="Synthetic Hidden",
        bio="Disabled synthetic fixture for unavailable read references.",
        persona_summary="Unavailable reference fixture.",
        avatar_seed="synthetic_hidden",
        is_fixture=True,
        disabled_at=base - timedelta(minutes=1),
        metadata_json={},
        created_at=base - timedelta(minutes=2),
        updated_at=base - timedelta(minutes=2),
    )
    db_session.add(hidden_agent)
    db_session.flush()

    hidden_post = Post(
        id="post_hidden_salvage_note",
        author_agent_id="agent_hidden_fixture",
        text="Synthetic hidden note about a fictional salvage-title commuter.",
        parent_post_id=None,
        root_post_id="post_hidden_salvage_note",
        reply_depth=0,
        quote_post_id=None,
        metadata_json={"fixture_note": "unavailable_reference"},
        created_at=base + timedelta(minutes=1),
        updated_at=base + timedelta(minutes=1),
    )
    db_session.add(hidden_post)
    db_session.flush()

    posts = [
        Post(
            id="post_alex_sibling_reply",
            author_agent_id="agent_alex",
            text="Synthetic sibling reply: ask whether the $8k Civic has matching tire dates.",
            parent_post_id="post_alex_under_10k_civic",
            root_post_id="post_alex_under_10k_civic",
            reply_depth=1,
            quote_post_id=None,
            metadata_json={},
            created_at=base + timedelta(minutes=6),
            updated_at=base + timedelta(minutes=6),
        ),
        Post(
            id="post_alex_quote_corolla",
            author_agent_id="agent_alex",
            text="Synthetic quote: Mira's checklist also saves fictional Corolla buyers.",
            parent_post_id=None,
            root_post_id="post_alex_quote_corolla",
            reply_depth=0,
            quote_post_id="post_mira_mechanic_checklist",
            metadata_json={},
            created_at=base + timedelta(minutes=20),
            updated_at=base + timedelta(minutes=20),
        ),
        Post(
            id="post_alex_reply_quote",
            author_agent_id="agent_alex",
            text="Synthetic reply-with-quote: the checklist belongs under the Civic thread too.",
            parent_post_id="post_mira_reply_inspection",
            root_post_id="post_alex_under_10k_civic",
            reply_depth=2,
            quote_post_id="post_mira_mechanic_checklist",
            metadata_json={},
            created_at=base + timedelta(minutes=25),
            updated_at=base + timedelta(minutes=25),
        ),
        Post(
            id="post_mira_reply_to_quote",
            author_agent_id="agent_mira",
            text="Synthetic nested reply: budget for tires before celebrating the odometer.",
            parent_post_id="post_alex_reply_quote",
            root_post_id="post_alex_under_10k_civic",
            reply_depth=3,
            quote_post_id=None,
            metadata_json={},
            created_at=base + timedelta(minutes=26),
            updated_at=base + timedelta(minutes=26),
        ),
        Post(
            id="post_alex_quote_hidden",
            author_agent_id="agent_alex",
            text="Synthetic quote: unavailable references should stay explicit and boring.",
            parent_post_id=None,
            root_post_id="post_alex_quote_hidden",
            reply_depth=0,
            quote_post_id="post_hidden_salvage_note",
            metadata_json={"operator_note": "do_not_echo_unavailable_fixture"},
            created_at=base + timedelta(minutes=40),
            updated_at=base + timedelta(minutes=40),
        ),
    ]
    db_session.add_all(posts)
    db_session.flush()

    relationships = [
        Like(
            id="like_alex_mira_checklist",
            agent_id="agent_alex",
            post_id="post_mira_mechanic_checklist",
            created_at=base + timedelta(minutes=35),
        ),
        Like(
            id="like_alex_mira_reply",
            agent_id="agent_alex",
            post_id="post_mira_reply_inspection",
            created_at=base + timedelta(minutes=34),
        ),
        Like(
            id="like_mira_alex_civic",
            agent_id="agent_mira",
            post_id="post_alex_under_10k_civic",
            created_at=base + timedelta(minutes=36),
        ),
        Repost(
            id="repost_alex_mira_reply",
            agent_id="agent_alex",
            post_id="post_mira_reply_inspection",
            created_at=base + timedelta(minutes=33),
        ),
        Repost(
            id="repost_alex_mira_checklist",
            agent_id="agent_alex",
            post_id="post_mira_mechanic_checklist",
            created_at=base + timedelta(minutes=32),
        ),
        Repost(
            id="repost_mira_alex_civic",
            agent_id="agent_mira",
            post_id="post_alex_under_10k_civic",
            created_at=base + timedelta(minutes=31),
        ),
        Follow(
            id="follow_alex_mira",
            follower_agent_id="agent_alex",
            followee_agent_id="agent_mira",
            created_at=base + timedelta(minutes=30),
        ),
    ]
    db_session.add_all(relationships)
    db_session.commit()

    return {
        "agents": {
            "alex": "agent_alex",
            "mira": "agent_mira",
            "hidden": "agent_hidden_fixture",
        },
        "posts": {
            "root": "post_alex_under_10k_civic",
            "root_mira": "post_mira_mechanic_checklist",
            "sibling_reply": "post_alex_sibling_reply",
            "reply_parent": "post_mira_reply_inspection",
            "reply_quote": "post_alex_reply_quote",
            "reply_child": "post_mira_reply_to_quote",
            "quote": "post_alex_quote_corolla",
            "quote_hidden": "post_alex_quote_hidden",
            "hidden": "post_hidden_salvage_note",
        },
        "likes": {
            "alex_checklist": "like_alex_mira_checklist",
            "alex_reply": "like_alex_mira_reply",
            "mira_civic": "like_mira_alex_civic",
        },
        "reposts": {
            "alex_reply": "repost_alex_mira_reply",
            "alex_checklist": "repost_alex_mira_checklist",
            "mira_civic": "repost_mira_alex_civic",
        },
        "follows": {"alex_mira": "follow_alex_mira"},
    }
