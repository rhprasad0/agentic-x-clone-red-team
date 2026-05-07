from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ValidationEvent(Base):
    __tablename__ = "validation_events"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    validation_run_id: Mapped[str] = mapped_column(
        ForeignKey("validation_runs.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    redacted_summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "ix_validation_events_validation_run_created_at_id",
            "validation_run_id",
            "created_at",
            "id",
        ),
        Index("ix_validation_events_event_type", "event_type"),
    )

    validation_run = relationship("ValidationRun", back_populates="events")
