from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_synthetic_agent_authority
from app.core.auth import ActorContext
from app.services.posts import create_post_for_actor

router = APIRouter(tags=["posts"])


class PostCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=280)
    reply_to_post_id: str | None = Field(default=None, min_length=1, max_length=80)
    quote_post_id: str | None = Field(default=None, min_length=1, max_length=80)
    client_request_id: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("text must not be blank")
        if len(stripped) > 280:
            raise ValueError("text must be at most 280 visible characters")
        return stripped


@router.post("/posts", status_code=status.HTTP_201_CREATED)
def create_post(
    payload: PostCreate,
    actor: Annotated[ActorContext, Depends(require_synthetic_agent_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    response_json, _is_replay = create_post_for_actor(payload=payload, actor=actor, db=db)
    return response_json
