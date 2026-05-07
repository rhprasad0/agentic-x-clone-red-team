from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.auth import ActorContext, parse_bearer_token, resolve_actor_from_token
from app.db.session import get_db_session


def get_current_actor(
    db: Annotated[Session, Depends(get_db_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> ActorContext:
    token = parse_bearer_token(authorization)
    return resolve_actor_from_token(db, token)
