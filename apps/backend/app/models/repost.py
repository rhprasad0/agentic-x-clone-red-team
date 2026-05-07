from datetime import datetime

from sqlalchemy import (
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


class Repost(Base):
    __tablename__ = "reposts"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False)
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id"), nullable=False)
    client_request_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("agent_id", "post_id", name="uq_reposts_agent_post"),
        Index("ix_reposts_post_created_at_id", "post_id", "created_at", "id"),
        Index("ix_reposts_agent_created_at_id", "agent_id", "created_at", "id"),
        Index(
            "uq_reposts_agent_client_request_id",
            "agent_id",
            "client_request_id",
            unique=True,
            postgresql_where=sql_text("client_request_id is not null"),
        ),
    )

    agent = relationship("Agent", back_populates="reposts")
    post = relationship("Post", back_populates="reposts")
