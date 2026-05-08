# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
import random
from collections import Counter

from scripts.ai_activity_runner_lib.actions import Candidate, validate_and_plan_action
from scripts.ai_activity_runner_lib.conversation import ConversationManager
from scripts.ai_activity_runner_lib.llm_client import ActionProposal
from scripts.ai_activity_runner_lib.policy import (
    CONVERSATION_WEIGHTS,
    FEED_WEIGHTS,
    WeightedActivityPolicy,
)


def test_intents_map_to_allowed_routes_and_local_only_silence():
    post=Candidate("candidate_1", post_id="post_1", author_handle="other")
    agent=Candidate("candidate_2", handle="other")
    candidates={"candidate_1":post,"candidate_2":agent}
    assert validate_and_plan_action(ActionProposal("root_post", text="Fictional note"), actor_handle="syn", candidates=candidates).route_class == "POST /posts"
    assert validate_and_plan_action(ActionProposal("reply", "candidate_1", "Fictional reply"), actor_handle="syn", candidates=candidates).body["reply_to_post_id"] == "post_1"
    assert validate_and_plan_action(ActionProposal("quote", "candidate_1", "Fictional quote"), actor_handle="syn", candidates=candidates).body["quote_post_id"] == "post_1"
    assert validate_and_plan_action(ActionProposal("like", "candidate_1"), actor_handle="syn", candidates=candidates).route_class == "POST /posts/{post_id}/like"
    assert validate_and_plan_action(ActionProposal("repost", "candidate_1"), actor_handle="syn", candidates=candidates).route_class == "POST /posts/{post_id}/repost"
    assert validate_and_plan_action(ActionProposal("follow", "candidate_2"), actor_handle="syn", candidates=candidates).route_class == "POST /agents/{handle}/follow"
    assert validate_and_plan_action(ActionProposal("silence"), actor_handle="syn", candidates=candidates).route_class is None

def test_action_validation_rejects_bad_targets_and_unsafe_text():
    candidates={"selfpost":Candidate("selfpost", post_id="p", author_handle="syn"), "self":Candidate("self", handle="syn")}
    assert validate_and_plan_action(ActionProposal("reply","missing","x"), actor_handle="syn", candidates=candidates).issue_class == "missing_target"
    assert validate_and_plan_action(ActionProposal("like","selfpost"), actor_handle="syn", candidates=candidates).issue_class == "stale_or_self_target"
    assert validate_and_plan_action(ActionProposal("follow","self"), actor_handle="syn", candidates=candidates).issue_class == "self_follow"
    assert validate_and_plan_action(ActionProposal("root_post", text="person@example.net"), actor_handle="syn", candidates=candidates).issue_class == "safety_redaction_applied"
    assert validate_and_plan_action(ActionProposal("reply","selfpost","ok"), actor_handle="other", candidates=candidates, max_reply_depth=4, current_depth=4).issue_class == "excessive_reply_depth"

def test_conversation_manager_caps_end_and_reactivates():
    m=ConversationManager(max_turns=2, guardrail_limit=2)
    s=m.get_or_create("a","root","b")
    assert m.active_states("a") == [s]
    m.record_action(s,"reply_continue","p2"); m.record_action(s,"reply_continue","p3")
    assert m.active_states("a") == []
    m.record_action(s,"like_end"); assert s.ended and s.ended_reason == "like_end"
    assert m.reactivate_if_newer_reply(s,"p4") is True and not s.ended
    m.record_guardrail_rejection(s); m.record_guardrail_rejection(s)
    assert s.ended_reason == "guardrail_circuit_breaker"

def test_weighted_policy_preserves_weights_and_replies_first():
    assert CONVERSATION_WEIGHTS == {"reply_continue":55,"like_end":15,"silence_end":10,"quote_end":10,"follow_end":5}
    assert FEED_WEIGHTS == {"root_post":24,"reply":22,"quote":14,"like":14,"repost":10,"follow":8,"silence":8}
    p=WeightedActivityPolicy(rng=random.Random(1), replies_first=True)
    assert set(p.action_options(active_conversation=True).intent_options) == set(CONVERSATION_WEIGHTS)
    assert set(p.action_options(active_conversation=False).intent_options) == set(FEED_WEIGHTS)
    counts=Counter(p.choose_intent(active_conversation=True) for _ in range(200))
    assert counts["reply_continue"] > counts["follow_end"]
