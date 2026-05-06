from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor, get_db_session
from app.core.auth import ActorContext, require_synthetic_agent
from app.models.post import Post

router = APIRouter(tags=["posts"])


class PostCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1)


class AuthorRead(BaseModel):
    id: str
    handle: str
    display_name: str


class PostRead(BaseModel):
    id: str
    body: str
    author: AuthorRead


@router.post("/posts", response_model=PostRead, status_code=status.HTTP_201_CREATED)
def create_post(
    payload: PostCreate,
    actor: Annotated[ActorContext, Depends(get_current_actor)],
    db: Annotated[Session, Depends(get_db_session)],
) -> PostRead:
    actor = require_synthetic_agent(actor)
    assert actor.agent is not None

    post = Post(
        id=f"post_{uuid4().hex}",
        author_agent_id=actor.agent.id,
        body=payload.body,
        metadata_json={},
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    return PostRead(
        id=post.id,
        body=post.body,
        author=AuthorRead(
            id=actor.agent.id,
            handle=actor.agent.handle,
            display_name=actor.agent.display_name,
        ),
    )
