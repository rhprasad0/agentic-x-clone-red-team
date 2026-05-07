from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ValidationRun(Base):
    __tablename__ = "validation_runs"
    __table_args__ = (
        UniqueConstraint("scenario_run_id", name="uq_validation_runs_scenario_run_id"),
        Index("ix_validation_runs_scenario_id", "scenario_id"),
        Index("ix_validation_runs_created_at_id", "created_at", "id"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    scenario_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("scenario_runs.id"), nullable=True
    )
    scenario_id: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    scenario_run = relationship("ScenarioRun", back_populates="validation_run")
    events = relationship("ValidationEvent", back_populates="validation_run")
    findings = relationship("Finding", back_populates="validation_run")
