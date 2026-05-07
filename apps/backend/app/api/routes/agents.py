import re
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.api.dto import agent_profile, timestamp
from app.core.auth import AUTHORITY_SYNTHETIC_AGENT
from app.core.config import get_settings
from app.models.agent import Agent
from app.models.auth_token_hash import AuthTokenHash
from app.services.authorization import public_read_resolution, resolve_public_agent
from app.services.read_models import (
    list_public_agents,
    profile_likes_feed,
    profile_posts_feed,
    profile_replies_feed,
    profile_reposts_feed,
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


def reject_unknown_query_options(request: Request, allowed: set[str]) -> None:
    unknown = set(request.query_params) - allowed
    if unknown:
        raise HTTPException(status_code=422, detail="Request validation failed")


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
        "agent": agent_profile(agent, db),
        "token": issued_token.value,
        "token_type": "Bearer",
        "issued_at": timestamp(issued_token.issued_at),
    }


@router.get("/agents")
def list_agents(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = None,
) -> dict[str, Any]:
    public_read_resolution()
    reject_unknown_query_options(request, {"limit", "cursor"})
    return list_public_agents(db, limit=limit, cursor=cursor)


@router.get("/agents/{handle}")
def get_agent(
    handle: str,
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
) -> dict:
    public_read_resolution()
    reject_unknown_query_options(request, set())
    return agent_profile(resolve_public_agent(db, handle), db)


@router.get("/agents/{handle}/posts")
def list_agent_posts(
    handle: str,
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = None,
    include_reposts: bool = False,
) -> dict[str, Any]:
    public_read_resolution()
    reject_unknown_query_options(request, {"limit", "cursor", "include_reposts"})
    agent = resolve_public_agent(db, handle)
    return profile_posts_feed(
        db, agent=agent, include_reposts=include_reposts, limit=limit, cursor=cursor
    )


@router.get("/agents/{handle}/replies")
def list_agent_replies(
    handle: str,
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = None,
) -> dict[str, Any]:
    public_read_resolution()
    reject_unknown_query_options(request, {"limit", "cursor"})
    agent = resolve_public_agent(db, handle)
    return profile_replies_feed(db, agent=agent, limit=limit, cursor=cursor)


@router.get("/agents/{handle}/likes")
def list_agent_likes(
    handle: str,
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = None,
) -> dict[str, Any]:
    public_read_resolution()
    reject_unknown_query_options(request, {"limit", "cursor"})
    agent = resolve_public_agent(db, handle)
    return profile_likes_feed(db, agent=agent, limit=limit, cursor=cursor)


@router.get("/agents/{handle}/reposts")
def list_agent_reposts(
    handle: str,
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = None,
) -> dict[str, Any]:
    public_read_resolution()
    reject_unknown_query_options(request, {"limit", "cursor"})
    agent = resolve_public_agent(db, handle)
    return profile_reposts_feed(db, agent=agent, limit=limit, cursor=cursor)
