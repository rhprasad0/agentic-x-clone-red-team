from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        CheckConstraint("length(body) > 0", name="ck_posts_body_not_empty"),
        CheckConstraint(
            "parent_post_id is null or parent_post_id <> id",
            name="ck_posts_not_own_parent",
        ),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    author_agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id"), nullable=False, index=True
    )
    parent_post_id: Mapped[str | None] = mapped_column(
        ForeignKey("posts.id"), nullable=True, index=True
    )
    scenario_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("scenario_runs.id"), nullable=True, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    author = relationship("Agent", back_populates="posts")
    parent = relationship("Post", remote_side=[id], back_populates="replies")
    replies = relationship("Post", back_populates="parent")
    scenario_run = relationship("ScenarioRun", back_populates="posts")
