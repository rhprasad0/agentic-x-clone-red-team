from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AuthTokenHash(Base):
    __tablename__ = "auth_token_hashes"
    __table_args__ = (
        CheckConstraint(
            "authority_type in ('synthetic_agent', 'harness')",
            name="ck_auth_token_hashes_authority_type",
        ),
        UniqueConstraint("token_hash", name="uq_auth_token_hashes_token_hash"),
        Index("ix_auth_token_hashes_authority_enabled", "authority_type", "enabled"),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    token_prefix: Mapped[str | None] = mapped_column(String(24), nullable=True)
    authority_type: Mapped[str] = mapped_column(String(40), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id"), nullable=True, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=sql_text("true"),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=sql_text("now()")
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agent = relationship("Agent", back_populates="auth_token_hashes")
