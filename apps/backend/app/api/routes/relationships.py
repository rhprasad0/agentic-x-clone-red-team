from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_synthetic_agent_authority
from app.core.auth import ActorContext
from app.services.relationships import (
    create_follow_for_actor,
    create_like_for_actor,
    create_repost_for_actor,
    delete_follow_for_actor,
    delete_like_for_actor,
    delete_repost_for_actor,
)

router = APIRouter(tags=["relationships"])


class RelationshipCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_request_id: str | None = Field(default=None, min_length=1, max_length=120)


async def reject_relationship_delete_body(request: Request) -> None:
    raw_body = await request.body()
    if not raw_body:
        return

    try:
        parsed_body: Any = await request.json()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Request validation failed",
        ) from None

    if parsed_body in ({}, None):
        return

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Request validation failed",
    )


@router.post("/posts/{post_id}/like", status_code=status.HTTP_201_CREATED)
def like_post(
    post_id: str,
    response: Response,
    actor: Annotated[ActorContext, Depends(require_synthetic_agent_authority)],
    db: Annotated[Session, Depends(get_db_session)],
    payload: RelationshipCreate | None = None,
) -> dict[str, Any]:
    response_json, status_code = create_like_for_actor(
        db=db,
        actor=actor,
        post_id=post_id,
        payload=payload,
    )
    response.status_code = status_code
    return response_json


@router.delete("/posts/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def unlike_post(
    post_id: str,
    actor: Annotated[ActorContext, Depends(require_synthetic_agent_authority)],
    db: Annotated[Session, Depends(get_db_session)],
    _no_body: Annotated[None, Depends(reject_relationship_delete_body)],
) -> Response:
    delete_like_for_actor(db=db, actor=actor, post_id=post_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/posts/{post_id}/repost", status_code=status.HTTP_201_CREATED)
def repost_post(
    post_id: str,
    response: Response,
    actor: Annotated[ActorContext, Depends(require_synthetic_agent_authority)],
    db: Annotated[Session, Depends(get_db_session)],
    payload: RelationshipCreate | None = None,
) -> dict[str, Any]:
    response_json, status_code = create_repost_for_actor(
        db=db,
        actor=actor,
        post_id=post_id,
        payload=payload,
    )
    response.status_code = status_code
    return response_json


@router.delete("/posts/{post_id}/repost", status_code=status.HTTP_204_NO_CONTENT)
def unrepost_post(
    post_id: str,
    actor: Annotated[ActorContext, Depends(require_synthetic_agent_authority)],
    db: Annotated[Session, Depends(get_db_session)],
    _no_body: Annotated[None, Depends(reject_relationship_delete_body)],
) -> Response:
    delete_repost_for_actor(db=db, actor=actor, post_id=post_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/agents/{handle}/follow", status_code=status.HTTP_201_CREATED)
def follow_agent(
    handle: str,
    response: Response,
    actor: Annotated[ActorContext, Depends(require_synthetic_agent_authority)],
    db: Annotated[Session, Depends(get_db_session)],
    payload: RelationshipCreate | None = None,
) -> dict[str, Any]:
    response_json, status_code = create_follow_for_actor(
        db=db,
        actor=actor,
        handle=handle,
        payload=payload,
    )
    response.status_code = status_code
    return response_json


@router.delete("/agents/{handle}/follow", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_agent(
    handle: str,
    actor: Annotated[ActorContext, Depends(require_synthetic_agent_authority)],
    db: Annotated[Session, Depends(get_db_session)],
    _no_body: Annotated[None, Depends(reject_relationship_delete_body)],
) -> Response:
    delete_follow_for_actor(db=db, actor=actor, handle=handle)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
