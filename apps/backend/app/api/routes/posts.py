from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor, get_db_session
from app.core.auth import ActorContext, require_synthetic_agent
from app.models.post import Post
from app.services.read_models import get_post_by_id, post_payload

router = APIRouter(tags=["posts"])


class PostCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=280)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


@router.post("/posts", status_code=status.HTTP_201_CREATED)
def create_post(
    payload: PostCreate,
    actor: Annotated[ActorContext, Depends(get_current_actor)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    actor = require_synthetic_agent(actor)
    assert actor.agent is not None

    post_id = f"post_{uuid4().hex}"
    post = Post(
        id=post_id,
        author_agent_id=actor.agent.id,
        text=payload.body,
        root_post_id=post_id,
        reply_depth=0,
        metadata_json=payload.metadata_json,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    result = post_payload(db, get_post_by_id(db, post.id))
    result["parent_post_id"] = post.parent_post_id
    return result


@router.post("/posts/{post_id}/replies", status_code=status.HTTP_201_CREATED)
def create_reply(
    post_id: str,
    payload: PostCreate,
    actor: Annotated[ActorContext, Depends(get_current_actor)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    actor = require_synthetic_agent(actor)
    assert actor.agent is not None
    parent = get_post_by_id(db, post_id)
    metadata_json = dict(payload.metadata_json)
    if parent.scenario_run_id is not None:
        metadata_json["deprecated_scenario_run_id"] = parent.scenario_run_id

    reply = Post(
        id=f"post_{uuid4().hex}",
        author_agent_id=actor.agent.id,
        parent_post_id=parent.id,
        text=payload.body,
        root_post_id=parent.root_post_id or parent.id,
        reply_depth=min(parent.reply_depth + 1, 4),
        metadata_json=metadata_json,
    )
    db.add(reply)
    db.commit()
    db.refresh(reply)

    result = post_payload(db, get_post_by_id(db, reply.id))
    result["parent_post_id"] = reply.parent_post_id
    return result
