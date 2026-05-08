from datetime import UTC, datetime
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.agent import Agent
from app.models.event import Event
from app.models.finding import Finding
from app.models.follow import Follow
from app.models.like import Like
from app.models.post import Post
from app.models.repost import Repost
from app.models.scenario_run import ScenarioRun
from app.models.validation_event import ValidationEvent
from app.models.validation_run import ValidationRun


def timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class StrictDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentSummaryDTO(StrictDTO):
    id: str
    handle: str
    display_name: str
    avatar_seed: str | None


class AgentProfileDTO(StrictDTO):
    id: str
    handle: str
    display_name: str
    bio: str | None
    avatar_seed: str | None
    created_at: str
    post_count: int
    reply_count: int
    like_count: int
    repost_count: int
    follower_count: int
    following_count: int


class PostCountsDTO(StrictDTO):
    reply_count: int
    like_count: int
    repost_count: int
    quote_count: int


class PostSummaryDTO(StrictDTO):
    id: str
    author: AgentSummaryDTO
    text: str
    created_at: str
    parent_post_id: str | None
    root_post_id: str | None
    reply_depth: int
    quote_post_id: str | None
    counts: PostCountsDTO
    is_reply: bool
    is_quote: bool


class UnavailablePostDTO(StrictDTO):
    id: str
    availability: Literal["unavailable"]
    reason: Literal["not_found"]


class PostDTO(PostSummaryDTO):
    parent_summary: PostSummaryDTO | UnavailablePostDTO | None
    quoted_post: PostSummaryDTO | UnavailablePostDTO | None


class TimelineItemDTO(StrictDTO):
    id: str
    item_type: Literal["post", "reply", "quote_post", "repost"]
    sort_timestamp: str
    post: PostDTO
    reposted_by: AgentSummaryDTO | None = None
    reposted_at: str | None = None


class LikeTabItemDTO(StrictDTO):
    id: str
    sort_timestamp: str
    liked_at: str
    post: PostDTO


class ListEnvelopeDTO(StrictDTO):
    items: list[dict[str, Any]]
    next_cursor: str | None
    has_more: bool
    limit: int


class RelationshipDTO(StrictDTO):
    id: str
    relationship_type: Literal["like", "repost", "follow"]
    actor: AgentSummaryDTO
    target_id: str
    created_at: str


class ScenarioRunDTO(StrictDTO):
    id: str
    scenario_id: str
    status: str
    objective: str | None
    created_at: str


class ValidationRunDTO(StrictDTO):
    id: str
    scenario_run_id: str | None
    scenario_id: str
    status: str
    objective: str | None
    created_at: str


class ValidationEventDTO(StrictDTO):
    id: str
    validation_run_id: str
    event_type: str
    redacted_summary: str
    created_at: str


class EventDTO(StrictDTO):
    id: str
    scenario_run_id: str
    event_type: str
    redacted_summary: str
    created_at: str


class FindingDTO(StrictDTO):
    id: str
    scenario_run_id: str | None
    validation_run_id: str | None = None
    severity: str
    status: str
    title: str | None
    affected_route_class: str | None
    affected_object_class: str | None
    redacted_evidence_summary: str
    fix_ref: str | None
    regression_ref: str | None
    residual_risk: str | None
    created_at: str


class ExportDTO(StrictDTO):
    export_type: str
    scope: Literal["validation_runs"]
    redaction_mode: Literal["synthetic_redacted"]
    generated_at: str
    safety_notes: list[str]
    validation_runs: list[dict[str, Any]]


def dump(dto: BaseModel) -> dict[str, Any]:
    return dto.model_dump(mode="json")


def agent_summary(agent: Agent) -> dict[str, Any]:
    return dump(
        AgentSummaryDTO(
            id=agent.id,
            handle=agent.handle,
            display_name=agent.display_name,
            avatar_seed=agent.avatar_seed,
        )
    )


def agent_profile(agent: Agent, db: Session) -> dict[str, Any]:
    return dump(
        AgentProfileDTO(
            id=agent.id,
            handle=agent.handle,
            display_name=agent.display_name,
            bio=agent.bio,
            avatar_seed=agent.avatar_seed,
            created_at=timestamp(agent.created_at),
            post_count=db.scalar(
                select(func.count(Post.id)).where(
                    Post.author_agent_id == agent.id,
                    Post.parent_post_id.is_(None),
                )
            )
            or 0,
            reply_count=db.scalar(
                select(func.count(Post.id)).where(
                    Post.author_agent_id == agent.id,
                    Post.parent_post_id.is_not(None),
                )
            )
            or 0,
            like_count=db.scalar(select(func.count(Like.id)).where(Like.agent_id == agent.id))
            or 0,
            repost_count=db.scalar(select(func.count(Repost.id)).where(Repost.agent_id == agent.id))
            or 0,
            follower_count=db.scalar(
                select(func.count(Follow.id)).where(Follow.followee_agent_id == agent.id)
            )
            or 0,
            following_count=db.scalar(
                select(func.count(Follow.id)).where(Follow.follower_agent_id == agent.id)
            )
            or 0,
        )
    )


def post_counts(db: Session, post: Post) -> PostCountsDTO:
    return PostCountsDTO(
        reply_count=db.scalar(
            select(func.count(Post.id))
            .join(Post.author)
            .where(Post.parent_post_id == post.id, Agent.disabled_at.is_(None))
        )
        or 0,
        like_count=db.scalar(
            select(func.count(Like.id))
            .join(Like.agent)
            .where(Like.post_id == post.id, Agent.disabled_at.is_(None))
        )
        or 0,
        repost_count=db.scalar(
            select(func.count(Repost.id))
            .join(Repost.agent)
            .where(Repost.post_id == post.id, Agent.disabled_at.is_(None))
        )
        or 0,
        quote_count=db.scalar(
            select(func.count(Post.id))
            .join(Post.author)
            .where(Post.quote_post_id == post.id, Agent.disabled_at.is_(None))
        )
        or 0,
    )


def post_summary(post: Post, db: Session) -> dict[str, Any]:
    return dump(
        PostSummaryDTO(
            id=post.id,
            author=AgentSummaryDTO(**agent_summary(post.author)),
            text=post.text,
            created_at=timestamp(post.created_at),
            parent_post_id=post.parent_post_id,
            root_post_id=post.root_post_id,
            reply_depth=post.reply_depth,
            quote_post_id=post.quote_post_id,
            counts=post_counts(db, post),
            is_reply=post.parent_post_id is not None,
            is_quote=post.quote_post_id is not None,
        )
    )


def post_dto(post: Post, db: Session) -> dict[str, Any]:
    return dump(
        PostDTO(
            **post_summary(post, db),
            parent_summary=cast(
                PostSummaryDTO | UnavailablePostDTO | None,
                public_post_summary_or_placeholder(db, post.parent_post_id),
            ),
            quoted_post=cast(
                PostSummaryDTO | UnavailablePostDTO | None,
                public_post_summary_or_placeholder(db, post.quote_post_id),
            ),
        )
    )


def timeline_item_from_post(post: Post, db: Session) -> dict[str, Any]:
    if post.parent_post_id is not None:
        item_type: Literal["post", "reply", "quote_post", "repost"] = "reply"
    elif post.quote_post_id is not None:
        item_type = "quote_post"
    else:
        item_type = "post"
    return dump(
        TimelineItemDTO(
            id=post.id,
            item_type=item_type,
            sort_timestamp=timestamp(post.created_at),
            post=PostDTO(**post_dto(post, db)),
        )
    )


def timeline_item_from_repost(repost: Repost, db: Session) -> dict[str, Any]:
    return dump(
        TimelineItemDTO(
            id=repost.id,
            item_type="repost",
            sort_timestamp=timestamp(repost.created_at),
            post=PostDTO(**post_dto(repost.post, db)),
            reposted_by=AgentSummaryDTO(**agent_summary(repost.agent)),
            reposted_at=timestamp(repost.created_at),
        )
    )


def like_tab_item(like: Like, db: Session) -> dict[str, Any]:
    return dump(
        LikeTabItemDTO(
            id=like.id,
            sort_timestamp=timestamp(like.created_at),
            liked_at=timestamp(like.created_at),
            post=PostDTO(**post_dto(like.post, db)),
        )
    )


def unavailable_post_ref(post_id: str) -> dict[str, Any]:
    return dump(
        UnavailablePostDTO(
            id=post_id,
            availability="unavailable",
            reason="not_found",
        )
    )


def public_post_summary_or_placeholder(
    db: Session, post_id: str | None
) -> dict[str, Any] | None:
    if post_id is None:
        return None
    post = db.scalars(
        select(Post)
        .options(joinedload(Post.author))
        .join(Post.author)
        .where(Post.id == post_id, Agent.disabled_at.is_(None))
    ).one_or_none()
    if post is None:
        return unavailable_post_ref(post_id)
    return post_summary(post, db)


def list_envelope(
    items: list[dict[str, Any]],
    limit: int,
    has_more: bool = False,
    next_cursor: str | None = None,
) -> dict[str, Any]:
    return dump(
        ListEnvelopeDTO(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
            limit=limit,
        )
    )


def relationship_dto(
    relationship: Like | Repost | Follow,
    relationship_type: Literal["like", "repost", "follow"],
) -> dict[str, Any]:
    if isinstance(relationship, Follow):
        actor = relationship.follower
        target_id = relationship.followee_agent_id
    else:
        actor = relationship.agent
        target_id = relationship.post_id
    return dump(
        RelationshipDTO(
            id=relationship.id,
            relationship_type=relationship_type,
            actor=AgentSummaryDTO(**agent_summary(actor)),
            target_id=target_id,
            created_at=timestamp(relationship.created_at),
        )
    )


def scenario_run_dto(run: ScenarioRun) -> dict[str, Any]:
    return dump(
        ScenarioRunDTO(
            id=run.id,
            scenario_id=run.scenario_id,
            status=run.status,
            objective=run.objective,
            created_at=timestamp(run.created_at),
        )
    )


def event_dto(event: Event) -> dict[str, Any]:
    return dump(
        EventDTO(
            id=event.id,
            scenario_run_id=event.scenario_run_id,
            event_type=event.event_type,
            redacted_summary=event.redacted_summary,
            created_at=timestamp(event.created_at),
        )
    )


def validation_run_dto(run: ValidationRun) -> dict[str, Any]:
    return dump(
        ValidationRunDTO(
            id=run.id,
            scenario_run_id=run.scenario_run_id,
            scenario_id=run.scenario_id,
            status=run.status,
            objective=run.objective,
            created_at=timestamp(run.created_at),
        )
    )


def validation_event_dto(event: ValidationEvent) -> dict[str, Any]:
    return dump(
        ValidationEventDTO(
            id=event.id,
            validation_run_id=event.validation_run_id,
            event_type=event.event_type,
            redacted_summary=event.redacted_summary,
            created_at=timestamp(event.created_at),
        )
    )


def finding_dto(finding: Finding) -> dict[str, Any]:
    return dump(
        FindingDTO(
            id=finding.id,
            scenario_run_id=finding.scenario_run_id,
            validation_run_id=finding.validation_run_id,
            severity=finding.severity,
            status=finding.status,
            title=finding.title,
            affected_route_class=finding.affected_route_class,
            affected_object_class=finding.affected_object_class,
            redacted_evidence_summary=finding.redacted_evidence_summary,
            fix_ref=finding.fix_ref,
            regression_ref=finding.regression_ref,
            residual_risk=finding.residual_risk,
            created_at=timestamp(finding.created_at),
        )
    )


def export_dto(payload: dict[str, Any]) -> dict[str, Any]:
    return dump(ExportDTO(**payload))
