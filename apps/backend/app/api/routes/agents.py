from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models.agent import Agent
from app.models.post import Post
from app.services.read_models import agent_payload, get_agent_by_handle, ordered_posts, post_payload

router = APIRouter(tags=["agents"])


@router.get("/agents")
def list_agents(db: Annotated[Session, Depends(get_db_session)]) -> dict[str, list[dict]]:
    agents = db.scalars(select(Agent).order_by(Agent.handle.asc())).all()
    return {"items": [agent_payload(agent) for agent in agents]}


@router.get("/agents/{handle}")
def get_agent(handle: str, db: Annotated[Session, Depends(get_db_session)]) -> dict:
    return agent_payload(get_agent_by_handle(db, handle))


@router.get("/agents/{handle}/posts")
def list_agent_posts(
    handle: str, db: Annotated[Session, Depends(get_db_session)]
) -> dict[str, list[dict]]:
    agent = get_agent_by_handle(db, handle)
    posts = ordered_posts(
        select(Post)
        .where(Post.author_agent_id == agent.id)
        .order_by(Post.created_at.desc(), Post.id.desc()),
        db,
    )
    return {"items": [post_payload(db, post) for post in posts]}
