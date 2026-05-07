from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    author_agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id"), nullable=False, index=True
    )
    parent_post_id: Mapped[str | None] = mapped_column(
        ForeignKey("posts.id"), nullable=True, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    root_post_id: Mapped[str | None] = mapped_column(ForeignKey("posts.id"), nullable=True)
    reply_depth: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=sql_text("0"),
    )
    quote_post_id: Mapped[str | None] = mapped_column(ForeignKey("posts.id"), nullable=True)
    client_request_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("length(text) between 1 and 280", name="ck_posts_text_length"),
        CheckConstraint("reply_depth between 0 and 4", name="ck_posts_reply_depth"),
        CheckConstraint(
            "parent_post_id is null or parent_post_id <> id",
            name="ck_posts_not_own_parent",
        ),
        Index("ix_posts_created_at_id", "created_at", "id"),
        Index("ix_posts_author_created_at_id", "author_agent_id", "created_at", "id"),
        Index("ix_posts_root_created_at_id", "root_post_id", "created_at", "id"),
        Index("ix_posts_quote_created_at_id", "quote_post_id", "created_at", "id"),
        Index(
            "uq_posts_author_client_request_id",
            "author_agent_id",
            "client_request_id",
            unique=True,
            postgresql_where=sql_text("client_request_id is not null"),
        ),
    )

    author = relationship("Agent", back_populates="posts")
    parent = relationship(
        "Post",
        remote_side=[id],
        foreign_keys=[parent_post_id],
        back_populates="replies",
    )
    replies = relationship("Post", foreign_keys=[parent_post_id], back_populates="parent")
    root = relationship("Post", remote_side=[id], foreign_keys=[root_post_id])
    quote = relationship("Post", remote_side=[id], foreign_keys=[quote_post_id])
    likes = relationship("Like", back_populates="post")
    reposts = relationship("Repost", back_populates="post")

    @property
    def body(self) -> str:
        return self.text

    @body.setter
    def body(self, value: str) -> None:
        self.text = value

    @property
    def scenario_run_id(self) -> str | None:
        return (self.metadata_json or {}).get("deprecated_scenario_run_id")

    @scenario_run_id.setter
    def scenario_run_id(self, value: str | None) -> None:
        metadata = dict(self.metadata_json or {})
        if value is None:
            metadata.pop("deprecated_scenario_run_id", None)
        else:
            metadata["deprecated_scenario_run_id"] = value
        self.metadata_json = metadata
