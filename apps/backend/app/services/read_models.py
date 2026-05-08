from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.api.dto import (
    agent_profile,
    like_tab_item,
    list_envelope,
    post_dto,
    timeline_item_from_post,
    timeline_item_from_repost,
)
from app.models.agent import Agent
from app.models.event import Event
from app.models.finding import Finding
from app.models.like import Like
from app.models.post import Post
from app.models.repost import Repost
from app.models.scenario_run import ScenarioRun
from app.models.validation_run import ValidationRun
from app.services.cursors import (
    CursorPosition,
    CursorScope,
    apply_keyset_pagination,
    decode_cursor,
    encode_cursor,
)

PUBLIC_ACTOR_KEY = "public"
PUBLIC_TIMELINE_ROUTE = "GET /timelines/public"
HOME_TIMELINE_ROUTE = "GET /timelines/home"
AGENTS_ROUTE = "GET /agents"
PROFILE_POSTS_ROUTE = "GET /agents/{handle}/posts"
PROFILE_REPLIES_ROUTE = "GET /agents/{handle}/replies"
PROFILE_LIKES_ROUTE = "GET /agents/{handle}/likes"
PROFILE_REPOSTS_ROUTE = "GET /agents/{handle}/reposts"
THREAD_ROUTE = "GET /posts/{post_id}/thread"

TimelineSource = Literal["post", "repost"]


def timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _not_found(message: str) -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)


def agent_payload(agent: Agent, db: Session | None = None) -> dict[str, Any]:
    if db is not None:
        return agent_profile(agent, db)
    return {
        "id": agent.id,
        "handle": agent.handle,
        "display_name": agent.display_name,
        "bio": agent.bio,
        "avatar_seed": agent.avatar_seed,
        "created_at": timestamp(agent.created_at),
    }


def post_payload(db: Session, post: Post) -> dict[str, Any]:
    reply_count = (
        db.scalar(select(func.count(Post.id)).where(Post.parent_post_id == post.id)) or 0
    )
    return {
        "id": post.id,
        "body": post.text,
        "created_at": timestamp(post.created_at),
        "parent_post_id": post.parent_post_id,
        "reply_count": reply_count,
        "scenario_run_id": post.scenario_run_id,
        "author": {
            "id": post.author.id,
            "handle": post.author.handle,
            "display_name": post.author.display_name,
        },
    }


def scenario_run_payload(run: ScenarioRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "scenario_id": run.scenario_id,
        "status": run.status,
        "objective": run.objective,
        "created_at": timestamp(run.created_at),
    }


def event_payload(event: Event) -> dict[str, Any]:
    return {
        "id": event.id,
        "scenario_run_id": event.scenario_run_id,
        "event_type": event.event_type,
        "redacted_summary": event.redacted_summary,
        "created_at": timestamp(event.created_at),
    }


def finding_payload(finding: Finding) -> dict[str, Any]:
    return {
        "id": finding.id,
        "scenario_run_id": finding.scenario_run_id,
        "severity": finding.severity,
        "status": finding.status,
        "title": finding.title,
        "redacted_evidence_summary": finding.redacted_evidence_summary,
        "created_at": timestamp(finding.created_at),
    }


def get_agent_by_handle(db: Session, handle: str) -> Agent:
    agent = db.scalars(
        select(Agent).where(Agent.handle_normalized == handle.lower())
    ).one_or_none()
    if agent is None:
        _not_found("Agent not found")
    return agent


def get_post_by_id(db: Session, post_id: str) -> Post:
    post = db.scalars(
        select(Post).options(joinedload(Post.author)).where(Post.id == post_id)
    ).one_or_none()
    if post is None:
        _not_found("Post not found")
    return post


def get_scenario_run_by_id(db: Session, run_id: str) -> ScenarioRun:
    run = db.scalars(select(ScenarioRun).where(ScenarioRun.id == run_id)).one_or_none()
    if run is None:
        _not_found("Scenario run not found")
    return run


def get_validation_run_for_scenario(db: Session, run_id: str) -> ValidationRun:
    validation_run = db.scalars(
        select(ValidationRun).where(ValidationRun.scenario_run_id == run_id)
    ).one_or_none()
    if validation_run is None:
        _not_found("Validation run not found")
    return validation_run


def ordered_posts(statement: Select[tuple[Post]], db: Session) -> list[Post]:
    return list(db.scalars(statement.options(joinedload(Post.author))).unique())


def _public_post_statement() -> Select[tuple[Post]]:
    return (
        select(Post)
        .options(joinedload(Post.author))
        .join(Post.author)
        .where(Agent.disabled_at.is_(None))
    )


def _public_repost_statement() -> Select[tuple[Repost]]:
    return (
        select(Repost)
        .join(Repost.agent)
        .where(Agent.disabled_at.is_(None))
        .options(joinedload(Repost.agent), joinedload(Repost.post).joinedload(Post.author))
    )


def _public_like_statement() -> Select[tuple[Like]]:
    return (
        select(Like)
        .join(Like.agent)
        .where(Agent.disabled_at.is_(None))
        .options(joinedload(Like.post).joinedload(Post.author))
    )


def _position_from_item(item: dict[str, Any]) -> CursorPosition:
    return CursorPosition(
        created_at=datetime.fromisoformat(item["sort_timestamp"].replace("Z", "+00:00")),
        item_id=item["id"],
    )


def _page_items(
    items: list[dict[str, Any]],
    *,
    limit: int,
    cursor: str | None,
    scope: CursorScope,
) -> dict[str, Any]:
    items.sort(
        key=lambda item: (item["sort_timestamp"], item["id"]),
        reverse=scope.direction == "desc",
    )
    if cursor is not None:
        position = decode_cursor(cursor, scope)
        if scope.direction == "desc":
            items = [
                item
                for item in items
                if (
                    datetime.fromisoformat(item["sort_timestamp"].replace("Z", "+00:00")),
                    item["id"],
                )
                < (position.created_at, position.item_id)
            ]
        else:
            items = [
                item
                for item in items
                if (
                    datetime.fromisoformat(item["sort_timestamp"].replace("Z", "+00:00")),
                    item["id"],
                )
                > (position.created_at, position.item_id)
            ]
    page = items[:limit]
    has_more = len(items) > limit
    next_cursor = encode_cursor(_position_from_item(page[-1]), scope) if has_more and page else None
    return list_envelope(page, limit, has_more=has_more, next_cursor=next_cursor)


def _cursor_position(cursor: str | None, scope: CursorScope) -> CursorPosition | None:
    return decode_cursor(cursor, scope) if cursor else None


def _bounded_statement(
    statement: Select[tuple[Any]],
    model: Any,
    *,
    limit: int,
    cursor: str | None,
    scope: CursorScope,
) -> Select[tuple[Any]]:
    return apply_keyset_pagination(
        statement,
        model,
        position=_cursor_position(cursor, scope),
        direction=scope.direction,
        limit=limit,
    )


def _page_already_bounded_items(
    items: list[dict[str, Any]], *, limit: int, scope: CursorScope
) -> dict[str, Any]:
    items.sort(
        key=lambda item: (item["sort_timestamp"], item["id"]),
        reverse=scope.direction == "desc",
    )
    page = items[:limit]
    has_more = len(items) > limit
    next_cursor = encode_cursor(_position_from_item(page[-1]), scope) if has_more and page else None
    return list_envelope(page, limit, has_more=has_more, next_cursor=next_cursor)


def list_public_agents(db: Session, *, limit: int, cursor: str | None) -> dict[str, Any]:
    scope = CursorScope(AGENTS_ROUTE, PUBLIC_ACTOR_KEY, {}, "desc")
    position = decode_cursor(cursor, scope) if cursor else None
    statement = select(Agent).where(Agent.disabled_at.is_(None))
    if position is not None:
        statement = statement.where(
            (Agent.created_at < position.created_at)
            | ((Agent.created_at == position.created_at) & (Agent.id < position.item_id))
        )
    agents = list(
        db.scalars(statement.order_by(Agent.created_at.desc(), Agent.id.desc()).limit(limit + 1))
    )
    page = agents[:limit]
    next_cursor = (
        encode_cursor(CursorPosition(_as_utc(page[-1].created_at), page[-1].id), scope)
        if len(agents) > limit and page
        else None
    )
    return list_envelope(
        [agent_profile(agent, db) for agent in page],
        limit,
        has_more=len(agents) > limit,
        next_cursor=next_cursor,
    )


def timeline_feed(
    db: Session,
    *,
    route_key: str,
    actor_key: str,
    include_replies: bool,
    limit: int,
    cursor: str | None,
    visible_agent_ids: list[str] | None = None,
) -> dict[str, Any]:
    scope = CursorScope(
        route_key,
        actor_key,
        {"include_replies": include_replies},
        "desc",
    )
    post_statement = _public_post_statement()
    if visible_agent_ids is not None:
        post_statement = post_statement.where(Post.author_agent_id.in_(visible_agent_ids))
    if not include_replies:
        post_statement = post_statement.where(Post.parent_post_id.is_(None))
    posts = list(
        db.scalars(
            _bounded_statement(post_statement, Post, limit=limit, cursor=cursor, scope=scope)
        ).unique()
    )

    repost_statement = _public_repost_statement()
    if visible_agent_ids is not None:
        repost_statement = repost_statement.where(Repost.agent_id.in_(visible_agent_ids))
    reposts = list(
        db.scalars(
            _bounded_statement(
                repost_statement, Repost, limit=limit, cursor=cursor, scope=scope
            )
        ).unique()
    )

    items = [timeline_item_from_post(post, db) for post in posts]
    items.extend(timeline_item_from_repost(repost, db) for repost in reposts)
    return _page_already_bounded_items(items, limit=limit, scope=scope)


def profile_posts_feed(
    db: Session,
    *,
    agent: Agent,
    include_reposts: bool,
    limit: int,
    cursor: str | None,
) -> dict[str, Any]:
    scope = CursorScope(
        PROFILE_POSTS_ROUTE,
        agent.id,
        {"include_reposts": include_reposts},
        "desc",
    )
    post_statement = _public_post_statement().where(
        Post.author_agent_id == agent.id,
        Post.parent_post_id.is_(None),
    )
    posts = list(
        db.scalars(
            _bounded_statement(post_statement, Post, limit=limit, cursor=cursor, scope=scope)
        ).unique()
    )
    items = [timeline_item_from_post(post, db) for post in posts]
    if include_reposts:
        repost_statement = _public_repost_statement().where(Repost.agent_id == agent.id)
        reposts = list(
            db.scalars(
                _bounded_statement(
                    repost_statement, Repost, limit=limit, cursor=cursor, scope=scope
                )
            ).unique()
        )
        items.extend(timeline_item_from_repost(repost, db) for repost in reposts)
    return _page_already_bounded_items(items, limit=limit, scope=scope)


def profile_replies_feed(
    db: Session, *, agent: Agent, limit: int, cursor: str | None
) -> dict[str, Any]:
    scope = CursorScope(PROFILE_REPLIES_ROUTE, agent.id, {}, "desc")
    post_statement = _public_post_statement().where(
        Post.author_agent_id == agent.id,
        Post.parent_post_id.is_not(None),
    )
    posts = list(
        db.scalars(
            _bounded_statement(post_statement, Post, limit=limit, cursor=cursor, scope=scope)
        ).unique()
    )
    items = [timeline_item_from_post(post, db) for post in posts]
    return _page_already_bounded_items(items, limit=limit, scope=scope)


def profile_likes_feed(
    db: Session, *, agent: Agent, limit: int, cursor: str | None
) -> dict[str, Any]:
    scope = CursorScope(PROFILE_LIKES_ROUTE, agent.id, {}, "desc")
    like_statement = _public_like_statement().where(Like.agent_id == agent.id)
    likes = list(
        db.scalars(
            _bounded_statement(like_statement, Like, limit=limit, cursor=cursor, scope=scope)
        ).unique()
    )
    items = [like_tab_item(like, db) for like in likes]
    return _page_already_bounded_items(items, limit=limit, scope=scope)


def profile_reposts_feed(
    db: Session, *, agent: Agent, limit: int, cursor: str | None
) -> dict[str, Any]:
    scope = CursorScope(PROFILE_REPOSTS_ROUTE, agent.id, {}, "desc")
    repost_statement = _public_repost_statement().where(Repost.agent_id == agent.id)
    reposts = list(
        db.scalars(
            _bounded_statement(
                repost_statement, Repost, limit=limit, cursor=cursor, scope=scope
            )
        ).unique()
    )
    items = [timeline_item_from_repost(repost, db) for repost in reposts]
    return _page_already_bounded_items(items, limit=limit, scope=scope)


def thread_read_model(
    db: Session,
    *,
    selected: Post,
    limit: int,
    cursor: str | None,
) -> dict[str, Any]:
    root_id = selected.root_post_id or selected.id
    root = db.scalars(_public_post_statement().where(Post.id == root_id)).one_or_none()
    if root is None:
        _not_found("Thread root not found")

    ancestors: list[Post] = []
    current = selected
    while current.parent_post_id is not None:
        parent = db.scalars(
            _public_post_statement().where(Post.id == current.parent_post_id)
        ).one_or_none()
        if parent is None:
            break
        ancestors.append(parent)
        current = parent
    ancestors.reverse()

    scope = CursorScope(THREAD_ROUTE, selected.id, {}, "asc")
    excluded_ids = {root.id, selected.id, *(post.id for post in ancestors)}
    reply_statement = _public_post_statement().where(
        Post.root_post_id == root.id, Post.id.not_in(excluded_ids)
    )
    replies = list(
        db.scalars(
            _bounded_statement(reply_statement, Post, limit=limit, cursor=cursor, scope=scope)
        ).unique()
    )
    items = [
        dict(post_dto(reply, db), sort_timestamp=timestamp(reply.created_at))
        for reply in replies
    ]
    page = _page_already_bounded_items(items, limit=limit, scope=scope)
    return {
        "root": post_dto(root, db),
        "selected": post_dto(selected, db),
        "ancestors": [post_dto(ancestor, db) for ancestor in ancestors],
        "replies": [
            {key: value for key, value in item.items() if key != "sort_timestamp"}
            for item in page["items"]
        ],
        "next_cursor": page["next_cursor"],
        "has_more": page["has_more"],
        "limit": page["limit"],
    }
