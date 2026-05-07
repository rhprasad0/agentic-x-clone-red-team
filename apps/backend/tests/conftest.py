import sys
from collections.abc import Iterator

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.core.config import REPO_ROOT, get_settings
from app.main import create_app
from app.services.fixtures import DELETE_ORDER

ALEMBIC_CONFIG = REPO_ROOT / "apps" / "backend" / "alembic.ini"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FIXTURE_CREDENTIAL_VALUES = {
    "agent_alex_fixture": "agent_alex_fixture_token_placeholder",
    "agent_mira_fixture": "agent_mira_fixture_token_placeholder",
    "harness_fixture": "harness_fixture_token_placeholder",
}


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
