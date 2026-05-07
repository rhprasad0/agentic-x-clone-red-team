import re
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.auth import AUTHORITY_SYNTHETIC_AGENT
from app.core.config import get_settings
from app.models.agent import Agent
from app.models.auth_token_hash import AuthTokenHash
from app.models.post import Post
from app.services.read_models import (
    agent_payload,
    get_agent_by_handle,
    ordered_posts,
    post_payload,
    timestamp,
)
from app.services.tokens import issue_bearer_token

HANDLE_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")

# Canonical V2 reserved signup handles from docs/v2-spec-outline.md,
# "Signup And Token Lifecycle".
SIGNUP_RESERVED_HANDLES = frozenset(
    {
        "admin",
        "api",
        "root",
        "system",
        "harness",
        "moderator",
        "support",
        "me",
        "null",
        "undefined",
        "signup",
        "fixture",
        "fixtures",
        "export",
        "exports",
        "validation",
        "finding",
        "findings",
        "timeline",
        "timelines",
        "twitter",
        "x",
        "xai",
        "grok",
        "grokai",
        "carbot_oracle",
    }
)

router = APIRouter(tags=["agents"])


class AgentSignup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handle: str = Field(min_length=1, max_length=24)
    display_name: str = Field(min_length=1, max_length=50)
    bio: str | None = Field(default=None, max_length=160)
    persona_seed: str | None = Field(default=None, max_length=400)
    avatar_seed: str | None = Field(default=None, max_length=64)

    @field_validator("handle", mode="before")
    @classmethod
    def normalize_handle(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("handle must be a string")
        return value.strip().lower()

    @field_validator("handle")
    @classmethod
    def validate_handle(cls, value: str) -> str:
        if value in SIGNUP_RESERVED_HANDLES:
            return value
        if len(value) < 3 or not HANDLE_RE.fullmatch(value):
            raise ValueError("handle is invalid")
        return value

    @field_validator("display_name", mode="before")
    @classmethod
    def trim_display_name(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("display_name must be a string")
        return value.strip()

    @field_validator("bio", "persona_seed", "avatar_seed", mode="before")
    @classmethod
    def trim_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("field must be a string")
        trimmed = value.strip()
        return trimmed or None


@router.post("/agents/signup", status_code=status.HTTP_201_CREATED)
def signup_agent(
    payload: AgentSignup,
    response: Response,
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, Any]:
    if payload.handle in SIGNUP_RESERVED_HANDLES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Handle is unavailable",
        )

    existing_agent = db.scalars(
        select(Agent).where(Agent.handle_normalized == payload.handle)
    ).one_or_none()
    if existing_agent is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Handle is unavailable",
        )

    max_dynamic_agents = get_settings().signup_max_dynamic_agents
    dynamic_agent_count = (
        db.scalar(select(func.count(Agent.id)).where(Agent.is_fixture.is_(False))) or 0
    )
    if dynamic_agent_count >= max_dynamic_agents:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Signup limit reached",
        )

    issued_token = issue_bearer_token()
    agent = Agent(
        id=f"agent_{uuid4().hex}",
        handle=payload.handle,
        handle_normalized=payload.handle,
        display_name=payload.display_name,
        bio=payload.bio,
        avatar_seed=payload.avatar_seed,
        is_fixture=False,
        metadata_json={},
    )
    db.add(agent)
    db.flush()
    db.add(
        AuthTokenHash(
            id=f"auth_{uuid4().hex}",
            token_hash=issued_token.token_hash,
            token_prefix=issued_token.token_prefix,
            authority_type=AUTHORITY_SYNTHETIC_AGENT,
            agent_id=agent.id,
            label=f"signup:{agent.handle}",
            enabled=True,
        )
    )
    db.commit()
    db.refresh(agent)

    response.headers["Cache-Control"] = "no-store"
    return {
        "agent": agent_payload(agent, db),
        "token": issued_token.value,
        "token_type": "Bearer",
        "issued_at": timestamp(issued_token.issued_at),
    }


@router.get("/agents")
def list_agents(db: Annotated[Session, Depends(get_db_session)]) -> dict[str, list[dict]]:
    agents = db.scalars(select(Agent).order_by(Agent.handle_normalized.asc(), Agent.id.asc())).all()
    return {"items": [agent_payload(agent, db) for agent in agents]}


@router.get("/agents/{handle}")
def get_agent(handle: str, db: Annotated[Session, Depends(get_db_session)]) -> dict:
    return agent_payload(get_agent_by_handle(db, handle), db)


@router.get("/agents/{handle}/posts")
def list_agent_posts(
    handle: str, db: Annotated[Session, Depends(get_db_session)]
) -> dict[str, list[dict]]:
    agent = get_agent_by_handle(db, handle)
    posts = ordered_posts(
        select(Post)
        .where(Post.author_agent_id == agent.id)
        .order_by(Post.created_at.desc(), Post.id.desc()),
        db,
    )
    return {"items": [post_payload(db, post) for post in posts]}
