"""add v2 idempotency records

Revision ID: 20260507_0003
Revises: 20260507_0002
Create Date: 2026-05-07 15:40:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260507_0003"
down_revision: str | None = "20260507_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_column(name: str) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("actor_key", sa.String(length=160), nullable=False),
        sa.Column("operation_class", sa.String(length=80), nullable=False),
        sa.Column("route_key", sa.String(length=160), nullable=False),
        sa.Column("target_key", sa.String(length=160), nullable=False),
        sa.Column("client_request_id", sa.String(length=120), nullable=False),
        sa.Column("scope_hash", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint_hash", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=20), server_default="in_flight", nullable=False),
        sa.Column("result_status_code", sa.Integer(), nullable=True),
        sa.Column("result_reference", sa.String(length=160), nullable=True),
        sa.Column("response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint(
            "state in ('in_flight', 'completed')",
            name="ck_idempotency_records_state",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "actor_key",
            "operation_class",
            "route_key",
            "target_key",
            "client_request_id",
            name="uq_idempotency_records_scope_key",
        ),
    )
    op.create_index(
        "ix_idempotency_records_scope_hash",
        "idempotency_records",
        ["scope_hash", "client_request_id"],
        unique=False,
    )
    op.create_index(
        "ix_idempotency_records_expires_at",
        "idempotency_records",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_idempotency_records_expires_at", table_name="idempotency_records")
    op.drop_index("ix_idempotency_records_scope_hash", table_name="idempotency_records")
    op.drop_table("idempotency_records")
