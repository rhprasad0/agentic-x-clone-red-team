from dataclasses import dataclass
from datetime import UTC, datetime
from typing import NoReturn

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.agent import Agent
from app.models.auth_token_hash import AuthTokenHash
from app.services.tokens import hash_bearer_token, is_well_formed_bearer_token

AUTHORITY_SYNTHETIC_AGENT = "synthetic_agent"
AUTHORITY_HARNESS = "harness"


@dataclass(frozen=True)
class ActorContext:
    credential_label: str
    authority_type: str
    agent: Agent | None = None

    @property
    def is_synthetic_agent(self) -> bool:
        return self.authority_type == AUTHORITY_SYNTHETIC_AGENT and self.agent is not None

    @property
    def is_harness(self) -> bool:
        return self.authority_type == AUTHORITY_HARNESS


class AuthHTTPException(HTTPException):
    def __init__(self, event_class: str) -> None:
        self.event_class = event_class
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )


def parse_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise_unauthorized("auth_missing")

    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise_unauthorized("auth_invalid")
    return token.strip()


def resolve_actor_from_token(db: Session, token: str) -> ActorContext:
    if not is_well_formed_bearer_token(token):
        raise_unauthorized("auth_invalid")

    token_hash = hash_bearer_token(token)
    stored_token = db.scalars(
        select(AuthTokenHash)
        .options(joinedload(AuthTokenHash.agent))
        .where(AuthTokenHash.token_hash == token_hash)
    ).one_or_none()

    if stored_token is None:
        raise_unauthorized("auth_invalid")
    if not stored_token.enabled or stored_token.revoked_at is not None:
        raise_unauthorized("auth_disabled")

    stored_token.last_used_at = datetime.now(UTC)

    if stored_token.authority_type == AUTHORITY_SYNTHETIC_AGENT:
        if stored_token.agent is None:
            raise_unauthorized("auth_invalid")
        return ActorContext(
            credential_label=stored_token.label,
            authority_type=AUTHORITY_SYNTHETIC_AGENT,
            agent=stored_token.agent,
        )

    if stored_token.authority_type == AUTHORITY_HARNESS:
        return ActorContext(
            credential_label=stored_token.label,
            authority_type=AUTHORITY_HARNESS,
            agent=None,
        )

    raise_unauthorized("auth_invalid")


def raise_unauthorized(event_class: str = "auth_invalid") -> NoReturn:
    raise AuthHTTPException(event_class)


def require_synthetic_agent(actor: ActorContext) -> ActorContext:
    if not actor.is_synthetic_agent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return actor


def require_harness(actor: ActorContext) -> ActorContext:
    if not actor.is_harness:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return actor
