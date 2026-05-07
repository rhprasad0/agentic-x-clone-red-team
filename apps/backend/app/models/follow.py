from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Follow(Base):
    __tablename__ = "follows"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    follower_agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False)
    followee_agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False)
    client_request_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "follower_agent_id <> followee_agent_id",
            name="ck_follows_not_self",
        ),
        UniqueConstraint(
            "follower_agent_id",
            "followee_agent_id",
            name="uq_follows_follower_followee",
        ),
        Index("ix_follows_followee_created_at_id", "followee_agent_id", "created_at", "id"),
        Index("ix_follows_follower_created_at_id", "follower_agent_id", "created_at", "id"),
        Index(
            "uq_follows_follower_client_request_id",
            "follower_agent_id",
            "client_request_id",
            unique=True,
            postgresql_where=sql_text("client_request_id is not null"),
        ),
    )

    follower = relationship(
        "Agent",
        foreign_keys=[follower_agent_id],
        back_populates="following_edges",
    )
    followee = relationship(
        "Agent",
        foreign_keys=[followee_agent_id],
        back_populates="follower_edges",
    )
