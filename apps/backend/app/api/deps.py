from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.auth import ActorContext, parse_bearer_token, resolve_actor_from_token
from app.db.session import get_db_session
from app.services.authorization import harness_only_route, synthetic_agent_social_mutation


def resolve_bearer_actor(
    db: Annotated[Session, Depends(get_db_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> ActorContext:
    token = parse_bearer_token(authorization)
    return resolve_actor_from_token(db, token)


def get_current_actor(
    actor: Annotated[ActorContext, Depends(resolve_bearer_actor)],
) -> ActorContext:
    return actor


def require_synthetic_agent_authority(
    actor: Annotated[ActorContext, Depends(resolve_bearer_actor)],
) -> ActorContext:
    return synthetic_agent_social_mutation(actor)


def require_harness_authority(
    actor: Annotated[ActorContext, Depends(resolve_bearer_actor)],
) -> ActorContext:
    return harness_only_route(actor)
