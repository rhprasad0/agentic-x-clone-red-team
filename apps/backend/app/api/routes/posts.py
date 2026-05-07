from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_synthetic_agent_authority
from app.api.dto import post_dto
from app.core.auth import ActorContext
from app.models.post import Post
from app.services.authorization import (
    resolve_parent_for_social_mutation,
    resolve_public_post,
    resolve_quote_for_social_mutation,
)

router = APIRouter(tags=["posts"])


class PostCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=280)
    reply_to_post_id: str | None = Field(default=None, min_length=1, max_length=80)
    quote_post_id: str | None = Field(default=None, min_length=1, max_length=80)
    client_request_id: str | None = Field(default=None, min_length=1, max_length=120)


def create_post_row(
    *,
    payload: PostCreate,
    actor: ActorContext,
    db: Session,
    route_parent_post_id: str | None = None,
) -> Post:
    assert actor.agent is not None
    parent_id = route_parent_post_id or payload.reply_to_post_id
    parent = resolve_parent_for_social_mutation(db, parent_id)
    quoted = resolve_quote_for_social_mutation(db, payload.quote_post_id)
    post_id = f"post_{uuid4().hex}"
    root_post_id = post_id
    reply_depth = 0
    if parent is not None:
        root_post_id = parent.root_post_id or parent.id
        reply_depth = min(parent.reply_depth + 1, 4)
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
    db.commit()
    db.refresh(post)
    return resolve_public_post(db, post.id)


@router.post("/posts", status_code=status.HTTP_201_CREATED)
def create_post(
    payload: PostCreate,
    actor: Annotated[ActorContext, Depends(require_synthetic_agent_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    return post_dto(create_post_row(payload=payload, actor=actor, db=db), db)


@router.post("/posts/{post_id}/replies", status_code=status.HTTP_201_CREATED)
def create_reply(
    post_id: str,
    payload: PostCreate,
    actor: Annotated[ActorContext, Depends(require_synthetic_agent_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    post = create_post_row(
        payload=payload,
        actor=actor,
        db=db,
        route_parent_post_id=post_id,
    )
    return post_dto(post, db)
