from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.auth import (
    ActorContext,
    parse_bearer_token,
    require_harness,
    resolve_actor_from_token,
)
from app.services.fixtures import reset_used_car_world, seed_used_car_world

router = APIRouter(tags=["fixtures"])


def get_fixture_actor(
    db: Annotated[Session, Depends(get_db_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> ActorContext:
    token = parse_bearer_token(authorization)
    return resolve_actor_from_token(db, token)


@router.post("/fixtures/seed")
def seed_fixtures(
    actor: Annotated[ActorContext, Depends(get_fixture_actor)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, int | str]:
    require_harness(actor)
    return seed_used_car_world(db)


@router.post("/fixtures/reset")
def reset_fixtures(
    actor: Annotated[ActorContext, Depends(get_fixture_actor)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, int | str]:
    require_harness(actor)
    return reset_used_car_world(db)
