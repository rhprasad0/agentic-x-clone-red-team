# ruff: noqa: E501
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass

CONVERSATION_WEIGHTS = {"reply_continue": 55, "like_end": 15, "silence_end": 10, "quote_end": 10, "follow_end": 5}
FEED_WEIGHTS = {"root_post": 24, "reply": 22, "quote": 14, "like": 14, "repost": 10, "follow": 8, "silence": 8}


@dataclass
class PolicyDecision:
    intent_options: list[str]
    policy_class: str


class ActionDiversityTracker:
    def __init__(self, *, target_cooldown_steps: int = 6, recent_action_window: int = 12, max_reply_share: float = 0.45) -> None:
        self.target_cooldown_steps = target_cooldown_steps
        self.recent_action_window = recent_action_window
        self.max_reply_share = max_reply_share
        self.recent_actions: deque[str] = deque(maxlen=recent_action_window)
        self.recent_targets: dict[str, int] = {}
        self.agent_recent_targets: dict[str, set[str]] = {}

    def record(self, action: str, target: str | None, *, step: int, actor: str) -> None:
        self.recent_actions.append(action)
        if target:
            self.recent_targets[target] = step
            self.agent_recent_targets.setdefault(actor, set()).add(target)

    def reply_share_too_high(self) -> bool:
        if not self.recent_actions:
            return False
        replies = sum(1 for action in self.recent_actions if action in {"reply", "reply_continue"})
        return (replies / len(self.recent_actions)) > self.max_reply_share

    def target_on_cooldown(self, target: str | None, *, step: int) -> bool:
        if not target or self.target_cooldown_steps <= 0:
            return False
        last = self.recent_targets.get(target)
        return last is not None and (step - last) < self.target_cooldown_steps

    def allowed_candidate_refs(self, candidate_targets: dict[str, str | None], *, step: int) -> list[str]:
        allowed = [ref for ref, target in candidate_targets.items() if not self.target_on_cooldown(target, step=step)]
        return allowed or list(candidate_targets.keys())


class WeightedActivityPolicy:
    def __init__(self, *, rng: random.Random | None = None, replies_first: bool = True, diversity: ActionDiversityTracker | None = None) -> None:
        self.rng = rng or random.Random()
        self.replies_first = replies_first
        self.diversity = diversity

    def _weights(self, *, active_conversation: bool) -> dict[str, int]:
        weights = dict(CONVERSATION_WEIGHTS if active_conversation and self.replies_first else FEED_WEIGHTS)
        if self.diversity and self.diversity.reply_share_too_high() and not active_conversation:
            weights.pop("reply", None)
            weights["root_post"] = max(weights.get("root_post", 0), 30)
            weights["quote"] = max(weights.get("quote", 0), 18)
            weights["like"] = max(weights.get("like", 0), 18)
            weights["repost"] = max(weights.get("repost", 0), 12)
            weights["follow"] = max(weights.get("follow", 0), 12)
        return weights

    def choose_intent(self, *, active_conversation: bool) -> str:
        weights = self._weights(active_conversation=active_conversation)
        return self.rng.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]

    def action_options(self, *, active_conversation: bool) -> PolicyDecision:
        weights = self._weights(active_conversation=active_conversation)
        return PolicyDecision(list(weights.keys()), "conversation" if active_conversation and self.replies_first else "feed")
