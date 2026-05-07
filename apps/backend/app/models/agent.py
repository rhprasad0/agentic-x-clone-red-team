from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("handle_normalized", name="uq_agents_handle_normalized"),
        Index("ix_agents_handle_normalized_id", "handle_normalized", "id"),
        Index("ix_agents_created_at_id", "created_at", "id"),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    handle: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    handle_normalized: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_seed: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_fixture: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sql_text("false"),
    )
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    posts = relationship("Post", back_populates="author")
    auth_fixtures = relationship("AuthFixture", back_populates="agent")
    auth_token_hashes = relationship("AuthTokenHash", back_populates="agent")
    likes = relationship("Like", back_populates="agent")
    reposts = relationship("Repost", back_populates="agent")
    following_edges = relationship(
        "Follow",
        foreign_keys="Follow.follower_agent_id",
        back_populates="follower",
    )
    follower_edges = relationship(
        "Follow",
        foreign_keys="Follow.followee_agent_id",
        back_populates="followee",
    )
