from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.auth import (
    ActorContext,
    hash_bearer_token,
    parse_bearer_token,
    require_harness,
    resolve_actor_from_token,
)
from app.services.fixtures import _load_fixture, reset_used_car_world, seed_used_car_world

router = APIRouter(tags=["fixtures"])


def get_fixture_actor(
    db: Annotated[Session, Depends(get_db_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> ActorContext:
    token = parse_bearer_token(authorization)
    try:
        return resolve_actor_from_token(db, token)
    except Exception:
        token_hash = hash_bearer_token(token)
        for fixture in _load_fixture("auth_fixtures"):
            if fixture["token_hash"] == token_hash and fixture["enabled"]:
                return ActorContext(
                    credential_label=fixture["credential_label"],
                    authority_type=fixture["authority_type"],
                )
        raise


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
