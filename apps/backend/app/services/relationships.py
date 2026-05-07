from __future__ import annotations

import hashlib
import time
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dto import relationship_dto
from app.core.auth import ActorContext
from app.models.agent import Agent
from app.models.follow import Follow
from app.models.like import Like
from app.models.post import Post
from app.models.repost import Repost
from app.services.authorization import resolve_public_agent, resolve_public_post
from app.services.idempotency import (
    IdempotencyScope,
    begin_idempotent_request,
    record_idempotency_success,
    safe_request_fingerprint,
)

RelationshipType = Literal["like", "repost", "follow"]

RELATIONSHIP_ALLOWED_FIELDS = {"client_request_id"}
LIKE_CREATE_OPERATION = "POST /posts/{post_id}/like"
REPOST_CREATE_OPERATION = "POST /posts/{post_id}/repost"
FOLLOW_CREATE_OPERATION = "POST /agents/{handle}/follow"


def create_like_for_actor(
    *,
    db: Session,
    actor: ActorContext,
    post_id: str,
    payload: Any,
) -> tuple[dict[str, Any], int]:
    agent = _require_agent(actor)
    post = resolve_public_post(db, post_id)
    record_id, replay = _begin_relationship_idempotency(
        db=db,
        actor=agent,
        payload=payload,
        operation_class=LIKE_CREATE_OPERATION,
        route_key=LIKE_CREATE_OPERATION,
        target_key=f"post:{post.id}",
    )
    if replay is not None:
        return replay, status.HTTP_200_OK

    response_json, created = _insert_or_get_like(db, agent, post)
    _record_relationship_success(
        db=db,
        record_id=record_id,
        status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        response_json=response_json,
        relationship_type="like",
    )
    return response_json, status.HTTP_201_CREATED if created else status.HTTP_200_OK


def delete_like_for_actor(*, db: Session, actor: ActorContext, post_id: str) -> None:
    agent = _require_agent(actor)
    post = resolve_public_post(db, post_id)
    db.execute(delete(Like).where(Like.agent_id == agent.id, Like.post_id == post.id))
    db.commit()


def create_repost_for_actor(
    *,
    db: Session,
    actor: ActorContext,
    post_id: str,
    payload: Any,
) -> tuple[dict[str, Any], int]:
    agent = _require_agent(actor)
    post = resolve_public_post(db, post_id)
    record_id, replay = _begin_relationship_idempotency(
        db=db,
        actor=agent,
        payload=payload,
        operation_class=REPOST_CREATE_OPERATION,
        route_key=REPOST_CREATE_OPERATION,
        target_key=f"post:{post.id}",
    )
    if replay is not None:
        return replay, status.HTTP_200_OK

    response_json, created = _insert_or_get_repost(db, agent, post)
    _record_relationship_success(
        db=db,
        record_id=record_id,
        status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        response_json=response_json,
        relationship_type="repost",
    )
    return response_json, status.HTTP_201_CREATED if created else status.HTTP_200_OK


def delete_repost_for_actor(*, db: Session, actor: ActorContext, post_id: str) -> None:
    agent = _require_agent(actor)
    post = resolve_public_post(db, post_id)
    db.execute(delete(Repost).where(Repost.agent_id == agent.id, Repost.post_id == post.id))
    db.commit()


def create_follow_for_actor(
    *,
    db: Session,
    actor: ActorContext,
    handle: str,
    payload: Any,
) -> tuple[dict[str, Any], int]:
    agent = _require_agent(actor)
    target = resolve_public_agent(db, handle)
    if agent.id == target.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict")

    record_id, replay = _begin_relationship_idempotency(
        db=db,
        actor=agent,
        payload=payload,
        operation_class=FOLLOW_CREATE_OPERATION,
        route_key=FOLLOW_CREATE_OPERATION,
        target_key=f"agent:{target.id}",
    )
    if replay is not None:
        return replay, status.HTTP_200_OK

    response_json, created = _insert_or_get_follow(db, agent, target)
    _record_relationship_success(
        db=db,
        record_id=record_id,
        status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        response_json=response_json,
        relationship_type="follow",
    )
    return response_json, status.HTTP_201_CREATED if created else status.HTTP_200_OK


def delete_follow_for_actor(*, db: Session, actor: ActorContext, handle: str) -> None:
    agent = _require_agent(actor)
    target = resolve_public_agent(db, handle)
    db.execute(
        delete(Follow).where(
            Follow.follower_agent_id == agent.id,
            Follow.followee_agent_id == target.id,
        )
    )
    db.commit()


def _insert_or_get_like(db: Session, agent: Agent, post: Post) -> tuple[dict[str, Any], bool]:
    existing = _get_like(db, agent.id, post.id)
    if existing is not None:
        return _relationship_response(existing, "like"), False

    like = Like(id=_relationship_id("like", agent.id, post.id), agent_id=agent.id, post_id=post.id)
    db.add(like)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _get_like(db, agent.id, post.id)
        if existing is not None:
            return _relationship_response(existing, "like"), False
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict") from None
    db.refresh(like)
    return _relationship_response(like, "like"), True


def _insert_or_get_repost(db: Session, agent: Agent, post: Post) -> tuple[dict[str, Any], bool]:
    existing = _get_repost(db, agent.id, post.id)
    if existing is not None:
        return _relationship_response(existing, "repost"), False

    repost = Repost(
        id=_relationship_id("repost", agent.id, post.id),
        agent_id=agent.id,
        post_id=post.id,
    )
    db.add(repost)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _get_repost(db, agent.id, post.id)
        if existing is not None:
            return _relationship_response(existing, "repost"), False
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict") from None
    db.refresh(repost)
    return _relationship_response(repost, "repost"), True


def _insert_or_get_follow(db: Session, agent: Agent, target: Agent) -> tuple[dict[str, Any], bool]:
    existing = _get_follow(db, agent.id, target.id)
    if existing is not None:
        return _relationship_response(existing, "follow"), False

    follow = Follow(
        id=_relationship_id("follow", agent.id, target.id),
        follower_agent_id=agent.id,
        followee_agent_id=target.id,
    )
    db.add(follow)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _get_follow(db, agent.id, target.id)
        if existing is not None:
            return _relationship_response(existing, "follow"), False
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict") from None
    db.refresh(follow)
    return _relationship_response(follow, "follow"), True


def _begin_relationship_idempotency(
    *,
    db: Session,
    actor: Agent,
    payload: Any,
    operation_class: str,
    route_key: str,
    target_key: str,
) -> tuple[str | None, dict[str, Any] | None]:
    request_body = _request_body(payload)
    client_request_id = request_body.get("client_request_id")
    if client_request_id is None:
        return None, None

    scope = IdempotencyScope(
        actor_key=actor.id,
        route_key=route_key,
        target_key=target_key,
        operation_class=operation_class,
    )
    fingerprint = safe_request_fingerprint(
        operation_class=operation_class,
        body=request_body,
        allowed_fields=RELATIONSHIP_ALLOWED_FIELDS,
    )
    decision = begin_idempotent_request(db, scope, client_request_id, fingerprint)
    if decision.outcome == "replay":
        assert decision.response_json is not None
        return None, decision.response_json
    if decision.outcome == "conflict":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict")
    if decision.outcome == "in_flight":
        replay = _wait_for_completed_relationship_replay(
            db,
            scope,
            client_request_id,
            fingerprint,
        )
        if replay is not None:
            return None, replay
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict")
    return decision.record_id, None


def _wait_for_completed_relationship_replay(
    db: Session,
    scope: IdempotencyScope,
    client_request_id: str,
    fingerprint: str,
) -> dict[str, Any] | None:
    for _ in range(20):
        time.sleep(0.025)
        db.rollback()
        decision = begin_idempotent_request(db, scope, client_request_id, fingerprint)
        if decision.outcome == "replay":
            assert decision.response_json is not None
            return decision.response_json
        if decision.outcome == "conflict":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict")
    return None


def _record_relationship_success(
    *,
    db: Session,
    record_id: str | None,
    status_code: int,
    response_json: dict[str, Any],
    relationship_type: RelationshipType,
) -> None:
    if record_id is None:
        return
    record_idempotency_success(
        db,
        record_id,
        status_code=status_code,
        response_json=response_json,
        result_reference=f"{relationship_type}:{response_json['id']}",
    )


def _relationship_response(
    relationship: Like | Repost | Follow,
    relationship_type: RelationshipType,
) -> dict[str, Any]:
    return relationship_dto(relationship, relationship_type)


def _request_body(payload: Any) -> dict[str, Any]:
    if payload is None:
        return {}
    return payload.model_dump(exclude_none=True)


def _get_like(db: Session, agent_id: str, post_id: str) -> Like | None:
    return db.scalars(
        select(Like).where(
            Like.agent_id == agent_id,
            Like.post_id == post_id,
        )
    ).one_or_none()


def _get_repost(db: Session, agent_id: str, post_id: str) -> Repost | None:
    return db.scalars(
        select(Repost).where(
            Repost.agent_id == agent_id,
            Repost.post_id == post_id,
        )
    ).one_or_none()


def _get_follow(db: Session, follower_agent_id: str, followee_agent_id: str) -> Follow | None:
    return db.scalars(
        select(Follow).where(
            Follow.follower_agent_id == follower_agent_id,
            Follow.followee_agent_id == followee_agent_id,
        )
    ).one_or_none()


def _relationship_id(prefix: RelationshipType, actor_id: str, target_id: str) -> str:
    digest = hashlib.sha256(f"{prefix}:{actor_id}:{target_id}".encode()).hexdigest()
    return f"{prefix}_{digest[:32]}"


def _require_agent(actor: ActorContext) -> Agent:
    assert actor.agent is not None
    return actor.agent
