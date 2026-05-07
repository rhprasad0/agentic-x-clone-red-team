from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_harness_authority
from app.core.auth import ActorContext
from app.core.security_logging import emit_security_event, v2_route_metadata
from app.services.authorization import fixture_reset_route
from app.services.fixtures import reset_used_car_world, seed_used_car_world

router = APIRouter(tags=["fixtures"])


@router.post("/fixtures/seed")
@v2_route_metadata(auth_class="harness", route_class="fixture", target_object_class="fixture")
def seed_fixtures(
    request: Request,
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, int | str]:
    fixture_reset_route(actor)
    response_json = seed_used_car_world(db)
    emit_security_event(
        request,
        event_class="fixture_invocation",
        status_code=200,
        outcome_class="success",
        actor=actor,
    )
    return response_json


@router.post("/fixtures/reset")
@v2_route_metadata(auth_class="harness", route_class="fixture", target_object_class="fixture")
def reset_fixtures(
    request: Request,
    actor: Annotated[ActorContext, Depends(require_harness_authority)],
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, int | str]:
    fixture_reset_route(actor)
    response_json = reset_used_car_world(db)
    emit_security_event(
        request,
        event_class="fixture_invocation",
        status_code=200,
        outcome_class="success",
        actor=actor,
    )
    return response_json
