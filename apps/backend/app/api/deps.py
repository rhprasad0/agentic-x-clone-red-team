from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.auth import (
    ActorContext,
    AuthHTTPException,
    parse_bearer_token,
    resolve_actor_from_token,
)
from app.core.security_logging import emit_security_event
from app.db.session import get_db_session
from app.services.authorization import harness_only_route, synthetic_agent_social_mutation


def resolve_bearer_actor(
    request: Request,
    db: Annotated[Session, Depends(get_db_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> ActorContext:
    try:
        token = parse_bearer_token(authorization)
        return resolve_actor_from_token(db, token)
    except AuthHTTPException as exc:
        emit_security_event(
            request,
            event_class=exc.event_class,
            status_code=exc.status_code,
            outcome_class="denied",
            actor_authority_class="unknown",
        )
        raise


def get_current_actor(
    actor: Annotated[ActorContext, Depends(resolve_bearer_actor)],
) -> ActorContext:
    return actor


def require_synthetic_agent_authority(
    request: Request,
    actor: Annotated[ActorContext, Depends(resolve_bearer_actor)],
) -> ActorContext:
    try:
        return synthetic_agent_social_mutation(actor)
    except HTTPException as exc:
        if exc.status_code == 403:
            emit_security_event(
                request,
                event_class="wrong_authority",
                status_code=exc.status_code,
                outcome_class="denied",
                actor=actor,
            )
        raise


def require_harness_authority(
    request: Request,
    actor: Annotated[ActorContext, Depends(resolve_bearer_actor)],
) -> ActorContext:
    try:
        return harness_only_route(actor)
    except HTTPException as exc:
        if exc.status_code == 403:
            emit_security_event(
                request,
                event_class="wrong_authority",
                status_code=exc.status_code,
                outcome_class="denied",
                actor=actor,
            )
        raise
