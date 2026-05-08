# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
from __future__ import annotations

import random
from dataclasses import dataclass

CONVERSATION_WEIGHTS = {"reply_continue": 55, "like_end": 15, "silence_end": 10, "quote_end": 10, "follow_end": 5}
FEED_WEIGHTS = {"root_post": 24, "reply": 22, "quote": 14, "like": 14, "repost": 10, "follow": 8, "silence": 8}

@dataclass
class PolicyDecision:
    intent_options: list[str]
    policy_class: str

class WeightedActivityPolicy:
    def __init__(self, *, rng: random.Random | None = None, replies_first: bool = True) -> None:
        self.rng = rng or random.Random()
        self.replies_first = replies_first

    def choose_intent(self, *, active_conversation: bool) -> str:
        weights = CONVERSATION_WEIGHTS if active_conversation and self.replies_first else FEED_WEIGHTS
        return self.rng.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]

    def action_options(self, *, active_conversation: bool) -> PolicyDecision:
        weights = CONVERSATION_WEIGHTS if active_conversation and self.replies_first else FEED_WEIGHTS
        return PolicyDecision(list(weights.keys()), "conversation" if weights is CONVERSATION_WEIGHTS else "feed")
