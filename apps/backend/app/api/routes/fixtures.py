from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_harness_authority
from app.core.auth import ActorContext
from app.services.authorization import fixture_reset_route
from app.services.fixtures import reset_used_car_world, seed_used_car_world

router = APIRouter(tags=["fixtures"])


@router.post("/fixtures/seed")
def seed_fixtures(
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, int | str]:
    fixture_reset_route(actor)
    return seed_used_car_world(db)


@router.post("/fixtures/reset")
def reset_fixtures(
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, int | str]:
    fixture_reset_route(actor)
    return reset_used_car_world(db)
