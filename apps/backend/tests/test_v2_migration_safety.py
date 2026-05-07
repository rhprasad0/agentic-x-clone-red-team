
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.core.config import REPO_ROOT, get_settings

ALEMBIC_CONFIG = REPO_ROOT / "apps" / "backend" / "alembic.ini"
VERSIONS_DIR = REPO_ROOT / "apps" / "backend" / "alembic" / "versions"
V1_REVISION = "20260506_0001"


def alembic_config() -> Config:
    return Config(str(ALEMBIC_CONFIG))


def reset_to_base() -> None:
    command.downgrade(alembic_config(), "base")


def upgrade_to(revision: str) -> None:
    command.upgrade(alembic_config(), revision)


def test_migration_files_do_not_embed_private_or_token_material() -> None:
    forbidden_fragments = {
        "postgresql://",
        "postgresql+psycopg://",
        "/" + "home" + "/",
        "token_placeholder",
        "bearer ",
        "private_key",
        "secret",
    }

    for path in VERSIONS_DIR.glob("*.py"):
        text_body = path.read_text(encoding="utf-8").lower()
        assert not any(fragment in text_body for fragment in forbidden_fragments), path.name


def test_v2_upgrade_backfills_v1_fixture_data_without_dropping_deprecated_tables() -> None:
    reset_to_base()
    upgrade_to(V1_REVISION)
    engine = create_engine(get_settings().database_url)

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    insert into agents (
                        id, handle, display_name, bio, metadata_json, created_at, updated_at
                    )
                    values (
                        'agent_v1_alex',
                        'Synthetic_Alex',
                        'Synthetic Alex',
                        'Fictional used-car budget scout.',
                        '{}',
                        '2026-05-06T12:00:00Z',
                        '2026-05-06T12:00:00Z'
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    insert into scenario_runs (
                        id, scenario_id, status, objective, metadata_json, created_at, updated_at
                    )
                    values (
                        'run_v1_used_car',
                        'RT-V2',
                        'completed',
                        'Synthetic V1 data preservation check.',
                        '{}',
                        '2026-05-06T12:01:00Z',
                        '2026-05-06T12:02:00Z'
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    insert into auth_fixtures (
                        id,
                        credential_label,
                        token_hash,
                        authority_type,
                        agent_id,
                        enabled,
                        created_at,
                        updated_at
                    )
                    values (
                        'auth_v1_alex',
                        'agent_v1_alex_fixture',
                        'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                        'synthetic_agent',
                        'agent_v1_alex',
                        true,
                        '2026-05-06T12:01:00Z',
                        '2026-05-06T12:01:00Z'
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    insert into posts (
                        id,
                        author_agent_id,
                        parent_post_id,
                        scenario_run_id,
                        body,
                        metadata_json,
                        created_at,
                        updated_at
                    )
                    values (
                        'post_v1_root',
                        'agent_v1_alex',
                        null,
                        'run_v1_used_car',
                        'Synthetic V1 root post about a fictional under-$10k sedan.',
                        '{}',
                        '2026-05-06T12:03:00Z',
                        '2026-05-06T12:03:00Z'
                    ),
                    (
                        'post_v1_reply',
                        'agent_v1_alex',
                        'post_v1_root',
                        'run_v1_used_car',
                        'Synthetic V1 reply preserves thread depth.',
                        '{}',
                        '2026-05-06T12:04:00Z',
                        '2026-05-06T12:04:00Z'
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    insert into events (
                        id,
                        scenario_run_id,
                        event_type,
                        redacted_summary,
                        metadata_json,
                        created_at,
                        updated_at
                    )
                    values (
                        'event_v1_probe',
                        'run_v1_used_car',
                        'route_probe',
                        'Synthetic V1 event stays public-safe.',
                        '{}',
                        '2026-05-06T12:05:00Z',
                        '2026-05-06T12:05:00Z'
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    insert into findings (
                        id,
                        scenario_run_id,
                        severity,
                        status,
                        title,
                        redacted_evidence_summary,
                        metadata_json,
                        created_at,
                        updated_at
                    )
                    values (
                        'finding_v1_scope',
                        'run_v1_used_car',
                        'low',
                        'open',
                        'Synthetic V1 finding',
                        'Synthetic V1 evidence summary remains redacted.',
                        '{}',
                        '2026-05-06T12:06:00Z',
                        '2026-05-06T12:06:00Z'
                    )
                    """
                )
            )
    finally:
        engine.dispose()

    upgrade_to("head")
    engine = create_engine(get_settings().database_url)

    try:
        inspector = inspect(engine)
        assert {"scenario_runs", "events", "auth_fixtures"}.issubset(inspector.get_table_names())

        post_columns = {column["name"] for column in inspector.get_columns("posts")}
        finding_columns = {column["name"] for column in inspector.get_columns("findings")}
        assert "body" not in post_columns
        assert "scenario_run_id" not in post_columns
        assert "scenario_run_id" not in finding_columns

        with engine.connect() as connection:
            agent = connection.execute(
                text(
                    """
                    select handle_normalized, is_fixture
                    from agents
                    where id = 'agent_v1_alex'
                    """
                )
            ).one()
            assert agent.handle_normalized == "synthetic_alex"
            assert agent.is_fixture is True

            copied_auth = connection.execute(
                text(
                    """
                    select label, token_hash, token_prefix, enabled
                    from auth_token_hashes
                    where id = 'auth_v1_alex'
                    """
                )
            ).one()
            assert copied_auth.label == "agent_v1_alex_fixture"
            assert copied_auth.token_hash == (
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            )
            assert copied_auth.token_prefix is None
            assert copied_auth.enabled is True

            posts = {
                row.id: row
                for row in connection.execute(
                    text(
                        """
                        select id, text, root_post_id, reply_depth
                        from posts
                        order by id
                        """
                    )
                )
            }
            assert posts["post_v1_root"].text.startswith("Synthetic V1 root post")
            assert posts["post_v1_root"].root_post_id == "post_v1_root"
            assert posts["post_v1_root"].reply_depth == 0
            assert posts["post_v1_reply"].root_post_id == "post_v1_root"
            assert posts["post_v1_reply"].reply_depth == 1

            validation_run = connection.execute(
                text(
                    """
                    select id, scenario_run_id, scenario_id, status
                    from validation_runs
                    where scenario_run_id = 'run_v1_used_car'
                    """
                )
            ).one()
            assert validation_run.id == "validation_run_v1_used_car"
            assert validation_run.scenario_id == "RT-V2"
            assert validation_run.status == "completed"

            validation_event = connection.execute(
                text(
                    """
                    select validation_run_id, event_type, redacted_summary
                    from validation_events
                    where id = 'event_v1_probe'
                    """
                )
            ).one()
            assert validation_event.validation_run_id == validation_run.id
            assert validation_event.event_type == "route_probe"

            finding = connection.execute(
                text(
                    """
                    select validation_run_id, severity, redacted_evidence_summary
                    from findings
                    where id = 'finding_v1_scope'
                    """
                )
            ).one()
            assert finding.validation_run_id == validation_run.id
            assert finding.severity == "low"
    finally:
        engine.dispose()


def test_v2_revision_supports_best_effort_downgrade_and_reupgrade() -> None:
    reset_to_base()
    upgrade_to("head")
    command.downgrade(alembic_config(), V1_REVISION)
    upgrade_to("head")

    engine = create_engine(get_settings().database_url)
    try:
        assert "auth_token_hashes" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
