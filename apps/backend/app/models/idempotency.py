from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        CheckConstraint(
            "state in ('in_flight', 'completed')",
            name="ck_idempotency_records_state",
        ),
        UniqueConstraint(
            "actor_key",
            "operation_class",
            "route_key",
            "target_key",
            "client_request_id",
            name="uq_idempotency_records_scope_key",
        ),
        Index("ix_idempotency_records_scope_hash", "scope_hash", "client_request_id"),
        Index("ix_idempotency_records_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    actor_key: Mapped[str] = mapped_column(String(160), nullable=False)
    operation_class: Mapped[str] = mapped_column(String(80), nullable=False)
    route_key: Mapped[str] = mapped_column(String(160), nullable=False)
    target_key: Mapped[str] = mapped_column(String(160), nullable=False)
    client_request_id: Mapped[str] = mapped_column(String(120), nullable=False)
    scope_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_fingerprint_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="in_flight")
    result_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    response_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
