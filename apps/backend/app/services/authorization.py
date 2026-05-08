from typing import NoReturn

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.auth import ActorContext
from app.models.agent import Agent
from app.models.post import Post


def _forbidden() -> NoReturn:
    raise HTTPException(status_code=403, detail="Forbidden")


def _not_found() -> NoReturn:
    raise HTTPException(status_code=404, detail="Resource not found")


def public_read_resolution() -> None:
    return None


def synthetic_agent_social_mutation(actor: ActorContext) -> ActorContext:
    if not actor.is_synthetic_agent:
        _forbidden()
    return actor


def harness_only_route(actor: ActorContext) -> ActorContext:
    if not actor.is_harness:
        _forbidden()
    return actor


def fixture_reset_route(actor: ActorContext) -> ActorContext:
    return harness_only_route(actor)


def validation_write(actor: ActorContext) -> ActorContext:
    return harness_only_route(actor)


def finding_read(actor: ActorContext) -> ActorContext:
    return harness_only_route(actor)


def export_invocation(actor: ActorContext) -> ActorContext:
    return harness_only_route(actor)


def resolve_public_agent(db: Session, handle: str) -> Agent:
    agent = db.scalars(
        select(Agent).where(
            Agent.handle_normalized == handle.lower(),
            Agent.disabled_at.is_(None),
        )
    ).one_or_none()
    if agent is None:
        _not_found()
    return agent


def resolve_public_post(db: Session, post_id: str) -> Post:
    post = db.scalars(
        select(Post)
        .options(joinedload(Post.author))
        .where(Post.id == post_id)
        .join(Post.author)
        .where(Agent.disabled_at.is_(None))
    ).one_or_none()
    if post is None:
        _not_found()
    return post


def resolve_parent_for_social_mutation(db: Session, post_id: str | None) -> Post | None:
    if post_id is None:
        return None
    return resolve_public_post(db, post_id)


def resolve_quote_for_social_mutation(db: Session, post_id: str | None) -> Post | None:
    if post_id is None:
        return None
    return resolve_public_post(db, post_id)
