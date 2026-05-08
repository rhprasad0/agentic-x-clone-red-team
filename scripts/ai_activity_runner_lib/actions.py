# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .llm_client import ActionProposal
from .redaction import validate_generated_social_text

ROUTE_BY_INTENT = {
    "root_post": "POST /posts",
    "reply": "POST /posts",
    "quote": "POST /posts",
    "like": "POST /posts/{post_id}/like",
    "repost": "POST /posts/{post_id}/repost",
    "follow": "POST /agents/{handle}/follow",
    "reply_continue": "POST /posts",
    "like_end": "POST /posts/{post_id}/like",
    "quote_end": "POST /posts",
    "follow_end": "POST /agents/{handle}/follow",
    "silence": None,
    "silence_end": None,
}
TEXT_INTENTS = {"root_post", "reply", "quote", "reply_continue", "quote_end"}
TARGET_POST_INTENTS = {"reply", "quote", "like", "repost", "reply_continue", "like_end", "quote_end"}
TARGET_AGENT_INTENTS = {"follow", "follow_end"}
END_INTENTS = {"like_end", "quote_end", "follow_end", "silence_end"}

@dataclass
class Candidate:
    ref: str
    post_id: str | None = None
    handle: str | None = None
    author_handle: str | None = None
    text: str | None = None

@dataclass
class ActionPlan:
    ok: bool
    intent: str
    route_class: str | None
    body: dict[str, Any] = field(default_factory=dict)
    target: dict[str, Any] = field(default_factory=dict)
    issue_class: str | None = None


def validate_and_plan_action(proposal: ActionProposal, *, actor_handle: str, candidates: dict[str, Candidate], max_reply_depth: int = 4, current_depth: int = 0) -> ActionPlan:
    intent = proposal.intent
    if intent not in ROUTE_BY_INTENT:
        return ActionPlan(False, "silence", None, issue_class="unsupported_intent")
    if intent in {"silence", "silence_end"}:
        return ActionPlan(True, intent, None)
    candidate = candidates.get(proposal.candidate_ref or "")
    if intent in TARGET_POST_INTENTS and not (candidate and candidate.post_id):
        return ActionPlan(False, "silence", None, issue_class="missing_target")
    if intent in TARGET_AGENT_INTENTS and not (candidate and candidate.handle):
        return ActionPlan(False, "silence", None, issue_class="missing_target")
    if candidate and candidate.author_handle == actor_handle and intent in TARGET_POST_INTENTS:
        return ActionPlan(False, "silence", None, issue_class="stale_or_self_target")
    if candidate and candidate.handle == actor_handle and intent in TARGET_AGENT_INTENTS:
        return ActionPlan(False, "silence", None, issue_class="self_follow")
    if intent in {"reply", "reply_continue"} and current_depth >= max_reply_depth:
        return ActionPlan(False, "silence_end", None, issue_class="excessive_reply_depth")
    body: dict[str, Any] = {}
    target: dict[str, Any] = {}
    if intent in TEXT_INTENTS:
        text = validate_generated_social_text(proposal.text)
        if not text.ok:
            return ActionPlan(False, "silence_end" if intent.endswith("_end") else "silence", None, issue_class=text.issue_class)
        body["text"] = text.text
    if intent in {"reply", "reply_continue"} and candidate:
        body["reply_to_post_id"] = candidate.post_id
        target["post_id"] = candidate.post_id
    if intent in {"quote", "quote_end"} and candidate:
        body["quote_post_id"] = candidate.post_id
        target["post_id"] = candidate.post_id
    if intent in {"like", "repost", "like_end"} and candidate:
        target["post_id"] = candidate.post_id
    if intent in TARGET_AGENT_INTENTS and candidate:
        target["handle"] = candidate.handle
    return ActionPlan(True, intent, ROUTE_BY_INTENT[intent], body, target)
