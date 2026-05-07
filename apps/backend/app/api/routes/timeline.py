from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models.post import Post
from app.services.read_models import get_post_by_id, ordered_posts, post_payload

router = APIRouter(tags=["timeline"])


@router.get("/timeline")
def get_timeline(db: Annotated[Session, Depends(get_db_session)]) -> dict[str, list[dict]]:
    posts = ordered_posts(
        select(Post).order_by(Post.created_at.desc(), Post.id.desc()),
        db,
    )
    return {"items": [post_payload(db, post) for post in posts]}


@router.get("/posts/{post_id}/thread")
def get_post_thread(
    post_id: str, db: Annotated[Session, Depends(get_db_session)]
) -> dict[str, dict | list[dict]]:
    root = get_post_by_id(db, post_id)
    replies = ordered_posts(
        select(Post)
        .where(Post.parent_post_id == root.id)
        .order_by(Post.created_at.asc(), Post.id.asc()),
        db,
    )
    return {
        "root": post_payload(db, root),
        "replies": [post_payload(db, reply) for reply in replies],
    }
