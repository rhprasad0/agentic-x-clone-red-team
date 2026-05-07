from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    validation_run_id: Mapped[str] = mapped_column(
        ForeignKey("validation_runs.id"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open")
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    affected_route_class: Mapped[str | None] = mapped_column(String(120), nullable=True)
    affected_object_class: Mapped[str | None] = mapped_column(String(120), nullable=True)
    redacted_evidence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    fix_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    regression_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    residual_risk: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    validation_run = relationship("ValidationRun", back_populates="findings")

    @property
    def scenario_run_id(self) -> str | None:
        if self.validation_run is not None:
            return self.validation_run.scenario_run_id
        return None
