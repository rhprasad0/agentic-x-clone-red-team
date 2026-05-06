from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AuthFixture(Base):
    __tablename__ = "auth_fixtures"
    __table_args__ = (
        CheckConstraint(
            "authority_type in ('synthetic_agent', 'harness')",
            name="ck_auth_fixtures_authority_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    credential_label: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    authority_type: Mapped[str] = mapped_column(String(40), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    agent = relationship("Agent", back_populates="auth_fixtures")
