"""create v1 schema

Revision ID: 20260506_0001
Revises:
Create Date: 2026-05-06 18:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260506_0001"
down_revision: str | None = None
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
    op.create_table(
        "agents",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("handle", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=JSONB_EMPTY,
            nullable=False,
        ),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("handle"),
    )
    op.create_index(op.f("ix_agents_handle"), "agents", ["handle"], unique=False)

    op.create_table(
        "scenario_runs",
        sa.Column("id", sa.String(length=80), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scenario_runs_scenario_id"), "scenario_runs", ["scenario_id"], unique=False
    )

    op.create_table(
        "auth_fixtures",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("credential_label", sa.String(length=120), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("authority_type", sa.String(length=40), nullable=False),
        sa.Column("agent_id", sa.String(length=80), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint(
            "authority_type in ('synthetic_agent', 'harness')",
            name="ck_auth_fixtures_authority_type",
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("credential_label"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_auth_fixtures_agent_id"), "auth_fixtures", ["agent_id"], unique=False
    )

    op.create_table(
        "posts",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("author_agent_id", sa.String(length=80), nullable=False),
        sa.Column("parent_post_id", sa.String(length=80), nullable=True),
        sa.Column("scenario_run_id", sa.String(length=80), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=JSONB_EMPTY,
            nullable=False,
        ),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint("length(body) > 0", name="ck_posts_body_not_empty"),
        sa.CheckConstraint(
            "parent_post_id is null or parent_post_id <> id", name="ck_posts_not_own_parent"
        ),
        sa.ForeignKeyConstraint(["author_agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["parent_post_id"], ["posts.id"]),
        sa.ForeignKeyConstraint(["scenario_run_id"], ["scenario_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_posts_author_agent_id"), "posts", ["author_agent_id"], unique=False
    )
    op.create_index(
        op.f("ix_posts_parent_post_id"), "posts", ["parent_post_id"], unique=False
    )
    op.create_index(
        op.f("ix_posts_scenario_run_id"), "posts", ["scenario_run_id"], unique=False
    )

    op.create_table(
        "events",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("scenario_run_id", sa.String(length=80), nullable=False),
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
        sa.ForeignKeyConstraint(["scenario_run_id"], ["scenario_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_events_event_type"), "events", ["event_type"], unique=False)
    op.create_index(
        op.f("ix_events_scenario_run_id"), "events", ["scenario_run_id"], unique=False
    )

    op.create_table(
        "findings",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("scenario_run_id", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), server_default="open", nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("redacted_evidence_summary", sa.Text(), nullable=False),
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
    )
    op.create_index(
        op.f("ix_findings_scenario_run_id"), "findings", ["scenario_run_id"], unique=False
    )
    op.create_index(op.f("ix_findings_severity"), "findings", ["severity"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_findings_severity"), table_name="findings")
    op.drop_index(op.f("ix_findings_scenario_run_id"), table_name="findings")
    op.drop_table("findings")
    op.drop_index(op.f("ix_events_scenario_run_id"), table_name="events")
    op.drop_index(op.f("ix_events_event_type"), table_name="events")
    op.drop_table("events")
    op.drop_index(op.f("ix_posts_scenario_run_id"), table_name="posts")
    op.drop_index(op.f("ix_posts_parent_post_id"), table_name="posts")
    op.drop_index(op.f("ix_posts_author_agent_id"), table_name="posts")
    op.drop_table("posts")
    op.drop_index(op.f("ix_auth_fixtures_agent_id"), table_name="auth_fixtures")
    op.drop_table("auth_fixtures")
    op.drop_index(op.f("ix_scenario_runs_scenario_id"), table_name="scenario_runs")
    op.drop_table("scenario_runs")
    op.drop_index(op.f("ix_agents_handle"), table_name="agents")
    op.drop_table("agents")
