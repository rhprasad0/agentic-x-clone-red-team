from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.agent import Agent
from app.models.event import Event
from app.models.finding import Finding
from app.models.post import Post
from app.models.scenario_run import ScenarioRun


def timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def agent_payload(agent: Agent) -> dict[str, Any]:
    return {
        "id": agent.id,
        "handle": agent.handle,
        "display_name": agent.display_name,
        "bio": agent.bio,
        "metadata_json": agent.metadata_json,
        "created_at": timestamp(agent.created_at),
    }


def post_payload(db: Session, post: Post) -> dict[str, Any]:
    reply_count = db.scalar(select(func.count(Post.id)).where(Post.parent_post_id == post.id)) or 0
    return {
        "id": post.id,
        "body": post.body,
        "created_at": timestamp(post.created_at),
        "metadata_json": post.metadata_json,
        "reply_count": reply_count,
        "scenario_run_id": post.scenario_run_id,
        "author": {
            "id": post.author.id,
            "handle": post.author.handle,
            "display_name": post.author.display_name,
        },
    }


def scenario_run_payload(run: ScenarioRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "scenario_id": run.scenario_id,
        "status": run.status,
        "objective": run.objective,
        "metadata_json": run.metadata_json,
        "created_at": timestamp(run.created_at),
    }


def event_payload(event: Event) -> dict[str, Any]:
    return {
        "id": event.id,
        "scenario_run_id": event.scenario_run_id,
        "event_type": event.event_type,
        "redacted_summary": event.redacted_summary,
        "metadata_json": event.metadata_json,
        "created_at": timestamp(event.created_at),
    }


def finding_payload(finding: Finding) -> dict[str, Any]:
    return {
        "id": finding.id,
        "scenario_run_id": finding.scenario_run_id,
        "severity": finding.severity,
        "status": finding.status,
        "title": finding.title,
        "redacted_evidence_summary": finding.redacted_evidence_summary,
        "metadata_json": finding.metadata_json,
        "created_at": timestamp(finding.created_at),
    }


def get_agent_by_handle(db: Session, handle: str) -> Agent:
    agent = db.scalars(select(Agent).where(Agent.handle == handle)).one_or_none()
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


def get_post_by_id(db: Session, post_id: str) -> Post:
    post = db.scalars(
        select(Post).options(joinedload(Post.author)).where(Post.id == post_id)
    ).one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return post


def get_scenario_run_by_id(db: Session, run_id: str) -> ScenarioRun:
    run = db.scalars(select(ScenarioRun).where(ScenarioRun.id == run_id)).one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario run not found")
    return run


def ordered_posts(statement: Select[tuple[Post]], db: Session) -> list[Post]:
    return list(db.scalars(statement.options(joinedload(Post.author))).unique())
