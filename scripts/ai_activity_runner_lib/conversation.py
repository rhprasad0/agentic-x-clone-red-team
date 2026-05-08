# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
from __future__ import annotations

from dataclasses import dataclass

END_ACTIONS = {"like_end", "quote_end", "follow_end", "silence_end"}

@dataclass
class ConversationState:
    agent_handle: str
    root_post_id: str
    counterpart_handle: str
    latest_observed_post_id: str | None = None
    last_agent_action_post_id: str | None = None
    turn_count: int = 0
    ended: bool = False
    ended_reason: str | None = None
    guardrail_rejection_count: int = 0

class ConversationManager:
    def __init__(self, *, max_turns: int = 4, guardrail_limit: int = 3) -> None:
        self.max_turns = max_turns
        self.guardrail_limit = guardrail_limit
        self._states: dict[tuple[str, str], ConversationState] = {}

    def get_or_create(self, agent_handle: str, root_post_id: str, counterpart_handle: str) -> ConversationState:
        key = (agent_handle, root_post_id)
        if key not in self._states:
            self._states[key] = ConversationState(agent_handle, root_post_id, counterpart_handle)
        return self._states[key]

    def active_states(self, agent_handle: str) -> list[ConversationState]:
        return [s for s in self._states.values() if s.agent_handle == agent_handle and not s.ended and s.turn_count < self.max_turns and s.guardrail_rejection_count < self.guardrail_limit]

    def record_action(self, state: ConversationState, intent: str, post_id: str | None = None) -> None:
        if intent in END_ACTIONS:
            state.ended = True
            state.ended_reason = intent
        if intent in {"reply_continue", "reply"}:
            state.turn_count += 1
            state.last_agent_action_post_id = post_id

    def record_guardrail_rejection(self, state: ConversationState) -> None:
        state.guardrail_rejection_count += 1
        if state.guardrail_rejection_count >= self.guardrail_limit:
            state.ended = True
            state.ended_reason = "guardrail_circuit_breaker"

    def reactivate_if_newer_reply(self, state: ConversationState, latest_post_id: str) -> bool:
        if latest_post_id and latest_post_id != state.latest_observed_post_id:
            state.latest_observed_post_id = latest_post_id
            if state.ended:
                state.ended = False
                state.ended_reason = None
                return True
        return False
