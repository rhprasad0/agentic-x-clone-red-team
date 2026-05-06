from dataclasses import dataclass
from hashlib import sha256

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.agent import Agent
from app.models.auth_fixture import AuthFixture

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


def hash_bearer_token(token: str) -> str:
    """Hash a fixture bearer token for database lookup without storing cleartext."""

    return sha256(token.encode("utf-8")).hexdigest()


def parse_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise_unauthorized()

    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise_unauthorized()
    return token.strip()


def resolve_actor_from_token(db: Session, token: str) -> ActorContext:
    token_hash = hash_bearer_token(token)
    fixture = db.scalars(
        select(AuthFixture)
        .options(joinedload(AuthFixture.agent))
        .where(AuthFixture.token_hash == token_hash)
    ).one_or_none()

    if fixture is None or not fixture.enabled:
        raise_unauthorized()

    if fixture.authority_type == AUTHORITY_SYNTHETIC_AGENT:
        if fixture.agent is None:
            raise_unauthorized()
        return ActorContext(
            credential_label=fixture.credential_label,
            authority_type=AUTHORITY_SYNTHETIC_AGENT,
            agent=fixture.agent,
        )

    if fixture.authority_type == AUTHORITY_HARNESS:
        return ActorContext(
            credential_label=fixture.credential_label,
            authority_type=AUTHORITY_HARNESS,
            agent=None,
        )

    raise_unauthorized()


def raise_unauthorized() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_synthetic_agent(actor: ActorContext) -> ActorContext:
    if not actor.is_synthetic_agent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Synthetic agent authority required",
        )
    return actor


def require_harness(actor: ActorContext) -> ActorContext:
    if not actor.is_harness:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Harness authority required",
        )
    return actor
