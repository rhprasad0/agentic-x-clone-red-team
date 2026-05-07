from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dto import post_dto
from app.core.auth import ActorContext
from app.models.post import Post
from app.services.authorization import (
    resolve_parent_for_social_mutation,
    resolve_public_post,
    resolve_quote_for_social_mutation,
)
from app.services.idempotency import (
    IdempotencyScope,
    begin_idempotent_request,
    record_idempotency_success,
    safe_request_fingerprint,
)

POST_CREATE_OPERATION = "POST /posts"
POST_CREATE_ALLOWED_FIELDS = {
    "text",
    "reply_to_post_id",
    "quote_post_id",
    "client_request_id",
}
MAX_REPLY_DEPTH = 4


def create_post_for_actor(
    *,
    db: Session,
    actor: ActorContext,
    payload: Any,
) -> tuple[dict[str, Any], bool]:
    assert actor.agent is not None
    request_body = payload.model_dump(exclude_none=True)
    client_request_id = payload.client_request_id
    record_id: str | None = None
    if client_request_id is not None:
        scope = IdempotencyScope(
            actor_key=actor.agent.id,
            route_key=POST_CREATE_OPERATION,
            target_key="self",
            operation_class=POST_CREATE_OPERATION,
        )
        fingerprint = safe_request_fingerprint(
            operation_class=POST_CREATE_OPERATION,
            body=request_body,
            allowed_fields=POST_CREATE_ALLOWED_FIELDS,
        )
        decision = begin_idempotent_request(db, scope, client_request_id, fingerprint)
        if decision.outcome == "replay":
            assert decision.response_json is not None
            return decision.response_json, True
        if decision.outcome == "conflict":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict")
        if decision.outcome == "in_flight":
            replay = _wait_for_completed_idempotency_replay(
                db, scope, client_request_id, fingerprint
            )
            if replay is not None:
                return replay, True
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict")
        record_id = decision.record_id

    post = _insert_post(db=db, actor=actor, payload=payload)
    response_json = post_dto(post, db)
    if record_id is not None:
        record_idempotency_success(
            db,
            record_id,
            status_code=status.HTTP_201_CREATED,
            response_json=response_json,
            result_reference=post.id,
        )
    return response_json, False


def _insert_post(*, db: Session, actor: ActorContext, payload: Any) -> Post:
    assert actor.agent is not None
    parent = resolve_parent_for_social_mutation(db, payload.reply_to_post_id)
    quoted = resolve_quote_for_social_mutation(db, payload.quote_post_id)

    post_id = f"post_{uuid4().hex}"
    root_post_id = post_id
    reply_depth = 0
    if parent is not None:
        reply_depth = parent.reply_depth + 1
        if reply_depth > MAX_REPLY_DEPTH:
            raise HTTPException(
                status_code=422,
                detail="Request validation failed",
            )
        root_post_id = parent.root_post_id or parent.id

    post = Post(
        id=post_id,
        author_agent_id=actor.agent.id,
        text=payload.text,
        parent_post_id=parent.id if parent is not None else None,
        root_post_id=root_post_id,
        reply_depth=reply_depth,
        quote_post_id=quoted.id if quoted is not None else None,
        client_request_id=payload.client_request_id,
        metadata_json={},
    )
    db.add(post)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if payload.client_request_id is not None:
            existing = db.scalars(
                select(Post).where(
                    Post.author_agent_id == actor.agent.id,
                    Post.client_request_id == payload.client_request_id,
                )
            ).one_or_none()
            if existing is not None:
                return resolve_public_post(db, existing.id)
        raise
    db.refresh(post)
    return resolve_public_post(db, post.id)


def _wait_for_completed_idempotency_replay(
    db: Session,
    scope: IdempotencyScope,
    client_request_id: str,
    fingerprint: str,
) -> dict[str, Any] | None:
    # Bounded local retry window for duplicate retry races in tests/local runs.
    for _ in range(20):
        time.sleep(0.025)
        db.rollback()
        decision = begin_idempotent_request(db, scope, client_request_id, fingerprint)
        if decision.outcome == "replay":
            return decision.response_json
        if decision.outcome == "conflict":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict")
    return None
