"""add v2 social and validation schema

Revision ID: 20260507_0002
Revises: 20260506_0001
Create Date: 2026-05-07 14:50:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260507_0002"
down_revision: str | None = "20260506_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB_EMPTY = sa.text("'{}'::jsonb")


def timestamp_column(name: str) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


def upgrade() -> None:
    op.add_column("agents", sa.Column("handle_normalized", sa.String(length=80), nullable=True))
    op.add_column("agents", sa.Column("persona_summary", sa.Text(), nullable=True))
    op.add_column("agents", sa.Column("avatar_seed", sa.String(length=80), nullable=True))
    op.add_column(
        "agents",
        sa.Column("is_fixture", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("agents", sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        update agents
        set
            handle_normalized = lower(handle),
            persona_summary = coalesce(metadata_json ->> 'persona', bio),
            avatar_seed = lower(handle),
            is_fixture = true
        where handle_normalized is null
        """
    )
    op.alter_column(
        "agents",
        "handle_normalized",
        existing_type=sa.String(length=80),
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_agents_handle_normalized",
        "agents",
        ["handle_normalized"],
    )
    op.create_index(
        "ix_agents_handle_normalized_id",
        "agents",
        ["handle_normalized", "id"],
        unique=False,
    )
    op.create_index("ix_agents_created_at_id", "agents", ["created_at", "id"], unique=False)

    op.create_table(
        "validation_runs",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("scenario_run_id", sa.String(length=80), nullable=True),
        sa.Column("scenario_id", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), server_default="pending", nullable=False),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=JSONB_EMPTY,
            nullable=False,
        ),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.ForeignKeyConstraint(["scenario_run_id"], ["scenario_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scenario_run_id", name="uq_validation_runs_scenario_run_id"),
    )
    op.create_index(
        "ix_validation_runs_scenario_id",
        "validation_runs",
        ["scenario_id"],
        unique=False,
    )
    op.create_index(
        "ix_validation_runs_created_at_id",
        "validation_runs",
        ["created_at", "id"],
        unique=False,
    )
    op.execute(
        """
        insert into validation_runs (
            id,
            scenario_run_id,
            scenario_id,
            status,
            objective,
            metadata_json,
            created_at,
            updated_at
        )
        select
            'validation_' || id,
            id,
            scenario_id,
            status,
            objective,
            metadata_json,
            created_at,
            updated_at
        from scenario_runs
        on conflict (scenario_run_id) do nothing
        """
    )

    op.create_table(
        "validation_events",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("validation_run_id", sa.String(length=120), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("redacted_summary", sa.Text(), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=JSONB_EMPTY,
            nullable=False,
        ),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.ForeignKeyConstraint(["validation_run_id"], ["validation_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_validation_events_validation_run_created_at_id",
        "validation_events",
        ["validation_run_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_validation_events_event_type",
        "validation_events",
        ["event_type"],
        unique=False,
    )
    op.execute(
        """
        insert into validation_events (
            id,
            validation_run_id,
            event_type,
            redacted_summary,
            metadata_json,
            created_at,
            updated_at
        )
        select
            events.id,
            validation_runs.id,
            events.event_type,
            events.redacted_summary,
            events.metadata_json,
            events.created_at,
            events.updated_at
        from events
        join validation_runs on validation_runs.scenario_run_id = events.scenario_run_id
        """
    )

    op.create_table(
        "auth_token_hashes",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("token_prefix", sa.String(length=24), nullable=True),
        sa.Column("authority_type", sa.String(length=40), nullable=False),
        sa.Column("agent_id", sa.String(length=80), nullable=True),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        timestamp_column("created_at"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "authority_type in ('synthetic_agent', 'harness')",
            name="ck_auth_token_hashes_authority_type",
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_auth_token_hashes_token_hash"),
    )
    op.create_index(
        "ix_auth_token_hashes_agent_id",
        "auth_token_hashes",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_auth_token_hashes_authority_enabled",
        "auth_token_hashes",
        ["authority_type", "enabled"],
        unique=False,
    )
    op.execute(
        """
        insert into auth_token_hashes (
            id,
            token_hash,
            token_prefix,
            authority_type,
            agent_id,
            label,
            enabled,
            revoked_at,
            created_at,
            last_used_at
        )
        select
            id,
            token_hash,
            null,
            authority_type,
            agent_id,
            credential_label,
            enabled,
            null,
            created_at,
            null
        from auth_fixtures
        on conflict (token_hash) do nothing
        """
    )

    op.add_column("posts", sa.Column("text", sa.Text(), nullable=True))
    op.add_column("posts", sa.Column("root_post_id", sa.String(length=80), nullable=True))
    op.add_column(
        "posts",
        sa.Column("reply_depth", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column("posts", sa.Column("quote_post_id", sa.String(length=80), nullable=True))
    op.add_column("posts", sa.Column("client_request_id", sa.String(length=120), nullable=True))
    op.execute("update posts set text = body")
    op.execute(
        """
        update posts
        set metadata_json = metadata_json || jsonb_build_object(
            'deprecated_scenario_run_id',
            scenario_run_id
        )
        where scenario_run_id is not null
        """
    )
    op.execute(
        """
        with recursive ancestry as (
            select
                id,
                parent_post_id as current_parent_id,
                id as root_id,
                0 as depth
            from posts
            union all
            select
                ancestry.id,
                parent.parent_post_id,
                parent.id,
                ancestry.depth + 1
            from ancestry
            join posts parent on parent.id = ancestry.current_parent_id
            where ancestry.current_parent_id is not null
              and ancestry.depth < 4
        ),
        resolved as (
            select distinct on (id)
                id,
                root_id,
                least(depth, 4) as reply_depth
            from ancestry
            order by id, depth desc
        )
        update posts
        set
            root_post_id = resolved.root_id,
            reply_depth = resolved.reply_depth
        from resolved
        where posts.id = resolved.id
        """
    )
    op.execute("update posts set root_post_id = id, reply_depth = 0 where root_post_id is null")
    op.alter_column("posts", "text", existing_type=sa.Text(), nullable=False)
    op.create_foreign_key("posts_root_post_id_fkey", "posts", "posts", ["root_post_id"], ["id"])
    op.create_foreign_key("posts_quote_post_id_fkey", "posts", "posts", ["quote_post_id"], ["id"])
    op.create_check_constraint("ck_posts_text_length", "posts", "length(text) between 1 and 280")
    op.create_check_constraint("ck_posts_reply_depth", "posts", "reply_depth between 0 and 4")
    op.create_index(
        "ix_posts_created_at_id",
        "posts",
        [sa.text("created_at DESC"), sa.text("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_posts_author_created_at_id",
        "posts",
        ["author_agent_id", sa.text("created_at DESC"), sa.text("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_posts_root_created_at_id",
        "posts",
        ["root_post_id", sa.text("created_at ASC"), sa.text("id ASC")],
        unique=False,
    )
    op.create_index(
        "ix_posts_quote_created_at_id",
        "posts",
        ["quote_post_id", sa.text("created_at DESC"), sa.text("id DESC")],
        unique=False,
    )
    op.create_index(
        "uq_posts_author_client_request_id",
        "posts",
        ["author_agent_id", "client_request_id"],
        unique=True,
        postgresql_where=sa.text("client_request_id is not null"),
    )
    op.drop_index(op.f("ix_posts_scenario_run_id"), table_name="posts")
    op.drop_constraint("posts_scenario_run_id_fkey", "posts", type_="foreignkey")
    op.drop_constraint("ck_posts_body_not_empty", "posts", type_="check")
    op.drop_column("posts", "scenario_run_id")
    op.drop_column("posts", "body")

    op.add_column("findings", sa.Column("validation_run_id", sa.String(length=120), nullable=True))
    op.add_column(
        "findings",
        sa.Column("affected_route_class", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "findings",
        sa.Column("affected_object_class", sa.String(length=120), nullable=True),
    )
    op.add_column("findings", sa.Column("fix_ref", sa.String(length=120), nullable=True))
    op.add_column("findings", sa.Column("regression_ref", sa.String(length=120), nullable=True))
    op.add_column("findings", sa.Column("residual_risk", sa.Text(), nullable=True))
    op.execute(
        """
        update findings
        set validation_run_id = validation_runs.id
        from validation_runs
        where validation_runs.scenario_run_id = findings.scenario_run_id
        """
    )
    op.alter_column(
        "findings",
        "validation_run_id",
        existing_type=sa.String(length=120),
        nullable=False,
    )
    op.create_foreign_key(
        "findings_validation_run_id_fkey",
        "findings",
        "validation_runs",
        ["validation_run_id"],
        ["id"],
    )
    op.create_index(
        "ix_findings_validation_run_id",
        "findings",
        ["validation_run_id"],
        unique=False,
    )
    op.drop_index(op.f("ix_findings_scenario_run_id"), table_name="findings")
    op.drop_constraint("findings_scenario_run_id_fkey", "findings", type_="foreignkey")
    op.drop_column("findings", "scenario_run_id")

    op.create_table(
        "likes",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("agent_id", sa.String(length=80), nullable=False),
        sa.Column("post_id", sa.String(length=80), nullable=False),
        sa.Column("client_request_id", sa.String(length=120), nullable=True),
        timestamp_column("created_at"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "post_id", name="uq_likes_agent_post"),
    )
    op.create_index(
        "ix_likes_post_created_at_id",
        "likes",
        ["post_id", sa.text("created_at DESC"), sa.text("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_likes_agent_created_at_id",
        "likes",
        ["agent_id", sa.text("created_at DESC"), sa.text("id DESC")],
        unique=False,
    )
    op.create_index(
        "uq_likes_agent_client_request_id",
        "likes",
        ["agent_id", "client_request_id"],
        unique=True,
        postgresql_where=sa.text("client_request_id is not null"),
    )

    op.create_table(
        "reposts",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("agent_id", sa.String(length=80), nullable=False),
        sa.Column("post_id", sa.String(length=80), nullable=False),
        sa.Column("client_request_id", sa.String(length=120), nullable=True),
        timestamp_column("created_at"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "post_id", name="uq_reposts_agent_post"),
    )
    op.create_index(
        "ix_reposts_post_created_at_id",
        "reposts",
        ["post_id", sa.text("created_at DESC"), sa.text("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_reposts_agent_created_at_id",
        "reposts",
        ["agent_id", sa.text("created_at DESC"), sa.text("id DESC")],
        unique=False,
    )
    op.create_index(
        "uq_reposts_agent_client_request_id",
        "reposts",
        ["agent_id", "client_request_id"],
        unique=True,
        postgresql_where=sa.text("client_request_id is not null"),
    )

    op.create_table(
        "follows",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("follower_agent_id", sa.String(length=80), nullable=False),
        sa.Column("followee_agent_id", sa.String(length=80), nullable=False),
        sa.Column("client_request_id", sa.String(length=120), nullable=True),
        timestamp_column("created_at"),
        sa.CheckConstraint(
            "follower_agent_id <> followee_agent_id",
            name="ck_follows_not_self",
        ),
        sa.ForeignKeyConstraint(["followee_agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["follower_agent_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "follower_agent_id",
            "followee_agent_id",
            name="uq_follows_follower_followee",
        ),
    )
    op.create_index(
        "ix_follows_followee_created_at_id",
        "follows",
        ["followee_agent_id", sa.text("created_at DESC"), sa.text("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_follows_follower_created_at_id",
        "follows",
        ["follower_agent_id", sa.text("created_at DESC"), sa.text("id DESC")],
        unique=False,
    )
    op.create_index(
        "uq_follows_follower_client_request_id",
        "follows",
        ["follower_agent_id", "client_request_id"],
        unique=True,
        postgresql_where=sa.text("client_request_id is not null"),
    )


def downgrade() -> None:
    op.drop_table("follows", if_exists=True)
    op.drop_table("reposts", if_exists=True)
    op.drop_table("likes", if_exists=True)

    op.add_column("findings", sa.Column("scenario_run_id", sa.String(length=80), nullable=True))
    op.execute(
        """
        update findings
        set scenario_run_id = validation_runs.scenario_run_id
        from validation_runs
        where validation_runs.id = findings.validation_run_id
        """
    )
    op.create_foreign_key(
        "findings_scenario_run_id_fkey",
        "findings",
        "scenario_runs",
        ["scenario_run_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_findings_scenario_run_id"),
        "findings",
        ["scenario_run_id"],
        unique=False,
    )
    op.drop_index("ix_findings_validation_run_id", table_name="findings")
    op.drop_constraint("findings_validation_run_id_fkey", "findings", type_="foreignkey")
    op.drop_column("findings", "residual_risk")
    op.drop_column("findings", "regression_ref")
    op.drop_column("findings", "fix_ref")
    op.drop_column("findings", "affected_object_class")
    op.drop_column("findings", "affected_route_class")
    op.drop_column("findings", "validation_run_id")

    op.add_column("posts", sa.Column("body", sa.Text(), nullable=True))
    op.add_column("posts", sa.Column("scenario_run_id", sa.String(length=80), nullable=True))
    op.execute("update posts set body = text")
    op.execute(
        """
        update posts
        set scenario_run_id = metadata_json ->> 'deprecated_scenario_run_id'
        where metadata_json ? 'deprecated_scenario_run_id'
        """
    )
    op.alter_column("posts", "body", existing_type=sa.Text(), nullable=False)
    op.create_foreign_key(
        "posts_scenario_run_id_fkey",
        "posts",
        "scenario_runs",
        ["scenario_run_id"],
        ["id"],
    )
    op.create_check_constraint("ck_posts_body_not_empty", "posts", "length(body) > 0")
    op.create_index(op.f("ix_posts_scenario_run_id"), "posts", ["scenario_run_id"], unique=False)
    op.drop_index("uq_posts_author_client_request_id", table_name="posts")
    op.drop_index("ix_posts_quote_created_at_id", table_name="posts")
    op.drop_index("ix_posts_root_created_at_id", table_name="posts")
    op.drop_index("ix_posts_author_created_at_id", table_name="posts")
    op.drop_index("ix_posts_created_at_id", table_name="posts")
    op.drop_constraint("ck_posts_reply_depth", "posts", type_="check")
    op.drop_constraint("ck_posts_text_length", "posts", type_="check")
    op.drop_constraint("posts_quote_post_id_fkey", "posts", type_="foreignkey")
    op.drop_constraint("posts_root_post_id_fkey", "posts", type_="foreignkey")
    op.drop_column("posts", "client_request_id")
    op.drop_column("posts", "quote_post_id")
    op.drop_column("posts", "reply_depth")
    op.drop_column("posts", "root_post_id")
    op.drop_column("posts", "text")

    op.drop_table("auth_token_hashes")
    op.drop_table("validation_events")
    op.drop_table("validation_runs")

    op.drop_index("ix_agents_created_at_id", table_name="agents")
    op.drop_index("ix_agents_handle_normalized_id", table_name="agents")
    op.drop_constraint("uq_agents_handle_normalized", "agents", type_="unique")
    op.drop_column("agents", "disabled_at")
    op.drop_column("agents", "is_fixture")
    op.drop_column("agents", "avatar_seed")
    op.drop_column("agents", "persona_summary")
    op.drop_column("agents", "handle_normalized")
