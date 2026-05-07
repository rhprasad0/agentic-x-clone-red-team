from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db_session, require_synthetic_agent_authority
from app.api.dto import list_envelope, post_dto, timeline_item_from_post, timeline_item_from_repost
from app.core.auth import ActorContext
from app.models.follow import Follow
from app.models.post import Post
from app.models.repost import Repost
from app.services.authorization import public_read_resolution, resolve_public_post
from app.services.read_models import ordered_posts, post_payload

router = APIRouter(tags=["timeline"])


def reject_unknown_query_options(request: Request, allowed: set[str]) -> None:
    unknown = set(request.query_params) - allowed
    if unknown:
        raise HTTPException(status_code=422, detail="Request validation failed")


def timeline_items(
    db: Session,
    posts: list[Post],
    reposts: list[Repost],
    limit: int,
) -> dict[str, Any]:
    items = [timeline_item_from_post(post, db) for post in posts]
    items.extend(timeline_item_from_repost(repost, db) for repost in reposts)
    items.sort(key=lambda item: (item["sort_timestamp"], item["id"]), reverse=True)
    return list_envelope(items[:limit], limit, has_more=len(items) > limit)


@router.get("/timeline")
def get_timeline(db: Annotated[Session, Depends(get_db_session)]) -> dict[str, list[dict]]:
    posts = ordered_posts(
        select(Post).order_by(Post.created_at.desc(), Post.id.desc()),
        db,
    )
    return {"items": [post_payload(db, post) for post in posts]}


@router.get("/timelines/public")
def get_public_timeline(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    include_replies: bool = False,
) -> dict[str, Any]:
    public_read_resolution()
    reject_unknown_query_options(request, {"limit", "cursor", "include_replies"})
    post_statement = select(Post).order_by(Post.created_at.desc(), Post.id.desc()).limit(limit + 1)
    if not include_replies:
        post_statement = post_statement.where(Post.parent_post_id.is_(None))
    posts = ordered_posts(post_statement, db)
    reposts = list(
        db.scalars(
            select(Repost)
            .options(joinedload(Repost.agent), joinedload(Repost.post).joinedload(Post.author))
            .order_by(Repost.created_at.desc(), Repost.id.desc())
            .limit(limit + 1)
        ).unique()
    )
    return timeline_items(db, posts, reposts, limit)


@router.get("/timelines/home")
def get_home_timeline(
    request: Request,
    actor: Annotated[ActorContext, Depends(require_synthetic_agent_authority)],
    db: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    include_replies: bool = False,
) -> dict[str, Any]:
    reject_unknown_query_options(request, {"limit", "cursor", "include_replies"})
    assert actor.agent is not None
    followed_agent_ids = list(
        db.scalars(
            select(Follow.followee_agent_id).where(Follow.follower_agent_id == actor.agent.id)
        )
    )
    visible_agent_ids = [actor.agent.id, *followed_agent_ids]
    post_statement = (
        select(Post)
        .where(Post.author_agent_id.in_(visible_agent_ids))
        .order_by(Post.created_at.desc(), Post.id.desc())
        .limit(limit + 1)
    )
    if not include_replies:
        post_statement = post_statement.where(Post.parent_post_id.is_(None))
    posts = ordered_posts(post_statement, db)
    reposts = list(
        db.scalars(
            select(Repost)
            .where(Repost.agent_id.in_(visible_agent_ids))
            .options(joinedload(Repost.agent), joinedload(Repost.post).joinedload(Post.author))
            .order_by(Repost.created_at.desc(), Repost.id.desc())
            .limit(limit + 1)
        ).unique()
    )
    return timeline_items(db, posts, reposts, limit)


@router.get("/posts/{post_id}/thread")
def get_post_thread(
    post_id: str, db: Annotated[Session, Depends(get_db_session)]
) -> dict[str, Any]:
    public_read_resolution()
    selected = resolve_public_post(db, post_id)
    root = resolve_public_post(db, selected.root_post_id or selected.id)
    ancestors = []
    current = selected
    while current.parent_post_id is not None:
        parent = resolve_public_post(db, current.parent_post_id)
        ancestors.append(parent)
        current = parent
    ancestors.reverse()
    replies = ordered_posts(
        select(Post)
        .where(Post.parent_post_id == selected.id)
        .order_by(Post.created_at.asc(), Post.id.asc()),
        db,
    )
    return {
        "root": post_dto(root, db),
        "selected": post_dto(selected, db),
        "ancestors": [post_dto(ancestor, db) for ancestor in ancestors],
        "replies": [post_dto(reply, db) for reply in replies],
        "next_cursor": None,
    }
