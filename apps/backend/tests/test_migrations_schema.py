from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects.postgresql import JSONB

from alembic import command
from app.core.config import get_settings

REPO_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG = REPO_ROOT / "apps" / "backend" / "alembic.ini"
EXPECTED_TABLES = {
    "agents",
    "posts",
    "scenario_runs",
    "events",
    "findings",
    "auth_fixtures",
}


def _upgrade_to_head() -> None:
    alembic_cfg = Config(str(ALEMBIC_CONFIG))
    command.upgrade(alembic_cfg, "head")


def test_alembic_upgrade_head_creates_expected_v1_tables() -> None:
    _upgrade_to_head()
    engine = create_engine(get_settings().database_url)

    try:
        inspector = inspect(engine)
        assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))
        assert inspector.get_pk_constraint("agents")["constrained_columns"] == ["id"]
        assert inspector.get_pk_constraint("posts")["constrained_columns"] == ["id"]
        assert inspector.get_pk_constraint("scenario_runs")["constrained_columns"] == ["id"]
    finally:
        engine.dispose()


def test_v1_schema_uses_jsonb_metadata_and_timezone_timestamps() -> None:
    _upgrade_to_head()
    engine = create_engine(get_settings().database_url)

    try:
        inspector = inspect(engine)
        for table_name in EXPECTED_TABLES:
            columns = {column["name"]: column for column in inspector.get_columns(table_name)}
            assert columns["created_at"]["type"].timezone is True

        for table_name in ("agents", "posts", "scenario_runs", "events", "findings"):
            columns = {column["name"]: column for column in inspector.get_columns(table_name)}
            assert "metadata_json" in columns
            assert isinstance(columns["metadata_json"]["type"], JSONB)
            assert "metadata" not in columns
    finally:
        engine.dispose()


def test_v1_schema_enforces_public_ids_and_auth_hash_boundaries() -> None:
    _upgrade_to_head()
    engine = create_engine(get_settings().database_url)

    try:
        inspector = inspect(engine)
        auth_columns = {column["name"]: column for column in inspector.get_columns("auth_fixtures")}
        assert {"credential_label", "token_hash", "authority_type", "agent_id", "enabled"}.issubset(
            auth_columns
        )
        assert "token" not in auth_columns
        assert "token_plaintext" not in auth_columns

        for table_name in EXPECTED_TABLES:
            id_column = next(
                column for column in inspector.get_columns(table_name) if column["name"] == "id"
            )
            assert id_column["type"].python_type is str

        with engine.connect() as connection:
            agent_id = connection.execute(
                text("select column_default from information_schema.columns "
                     "where table_name = 'agents' and column_name = 'id'")
            ).scalar_one()
            assert agent_id is None
    finally:
        engine.dispose()
