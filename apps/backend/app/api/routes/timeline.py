from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_synthetic_agent_authority
from app.core.auth import ActorContext
from app.models.follow import Follow
from app.services.authorization import public_read_resolution, resolve_public_post
from app.services.read_models import (
    HOME_TIMELINE_ROUTE,
    PUBLIC_TIMELINE_ROUTE,
    thread_read_model,
    timeline_feed,
)

router = APIRouter(tags=["timeline"])


def reject_unknown_query_options(request: Request, allowed: set[str]) -> None:
    unknown = set(request.query_params) - allowed
    if unknown:
        raise HTTPException(status_code=422, detail="Request validation failed")


def reject_get_body(request: Request) -> None:
    content_length = request.headers.get("content-length")
    if content_length and content_length != "0":
        raise HTTPException(status_code=422, detail="Request validation failed")


@router.get("/timeline")
def get_timeline(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = None,
    include_replies: bool = False,
) -> dict[str, Any]:
    return get_public_timeline(
        request=request,
        db=db,
        limit=limit,
        cursor=cursor,
        include_replies=include_replies,
    )


@router.get("/timelines/public")
def get_public_timeline(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = None,
    include_replies: bool = False,
) -> dict[str, Any]:
    public_read_resolution()
    reject_unknown_query_options(request, {"limit", "cursor", "include_replies"})
    return timeline_feed(
        db,
        route_key=PUBLIC_TIMELINE_ROUTE,
        actor_key="public",
        include_replies=include_replies,
        limit=limit,
        cursor=cursor,
    )


@router.get("/timelines/home")
def get_home_timeline(
    request: Request,
    actor: Annotated[ActorContext, Depends(require_synthetic_agent_authority)],
    db: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = None,
    include_replies: bool = False,
) -> dict[str, Any]:
    reject_unknown_query_options(request, {"limit", "cursor", "include_replies"})
    reject_get_body(request)
    assert actor.agent is not None
    followed_agent_ids = list(
        db.scalars(
            select(Follow.followee_agent_id).where(Follow.follower_agent_id == actor.agent.id)
        )
    )
    visible_agent_ids = [actor.agent.id, *followed_agent_ids]
    return timeline_feed(
        db,
        route_key=HOME_TIMELINE_ROUTE,
        actor_key=actor.agent.id,
        include_replies=include_replies,
        limit=limit,
        cursor=cursor,
        visible_agent_ids=visible_agent_ids,
    )


@router.get("/posts/{post_id}/thread")
def get_post_thread(
    request: Request,
    post_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = None,
) -> dict[str, Any]:
    public_read_resolution()
    reject_unknown_query_options(request, {"limit", "cursor"})
    selected = resolve_public_post(db, post_id)
    return thread_read_model(db, selected=selected, limit=limit, cursor=cursor)
