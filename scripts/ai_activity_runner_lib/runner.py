# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
from __future__ import annotations

import random
import time
from dataclasses import dataclass

from .actions import Candidate, validate_and_plan_action
from .agent_registry import AgentRegistry
from .api_client import V2APIClient
from .artifacts import ActivityEvent, ArtifactWriter, utc_now
from .config import AIActivityConfig
from .llm_client import ActionProposal, LocalCodexBridgeClient
from .policy import WeightedActivityPolicy


@dataclass
class RunnerResult:
    status: str
    run_id: str
    steps: int
    issues: dict[str, int]
    actions: dict[str, int]
    artifact_dir: str

class SyntheticLoadRunner:
    def __init__(self, config: AIActivityConfig) -> None:
        self.config = config
        self.rng = random.Random(config.random_seed)
        self.api = V2APIClient(config.api_base_url, per_agent_retry_budget=config.llm_max_retries)
        self.llm = LocalCodexBridgeClient(config)
        self.started_at = utc_now()
        self.writer = ArtifactWriter(config.output_dir, config.run_id)

    def run(self) -> RunnerResult:
        agents = []
        try:
            registry = AgentRegistry(self.api, run_id=self.config.run_id, count=self.config.agent_count, rng=self.rng)
            agents = registry.signup_all()
            self.writer.write_agent_registry(agents)
        except Exception as exc:  # noqa: BLE001 - safe issue recording and summary
            self.writer.safe_record_issue(severity="error", issue_class="signup_failed", component="agent_registry", safe_message=str(exc))
            self.writer.write_summary(config_summary=self.config.redacted_summary(), started_at=self.started_at)
            return RunnerResult("blocked", self.config.run_id, 0, self.writer.issue_counts, self.writer.action_counts, str(self.writer.run_dir))
        policy = WeightedActivityPolicy(rng=self.rng, replies_first=self.config.replies_first)
        deadline = time.monotonic() + self.config.max_wall_seconds
        steps = 0
        while steps < self.config.max_steps and time.monotonic() < deadline:
            agent = agents[steps % len(agents)]
            bearer = registry.vault.get(agent.credential_ref)
            public = self.api.public_timeline(limit=20)
            candidates: dict[str, Candidate] = {}
            if public.ok and isinstance(public.data, dict):
                for idx, item in enumerate(public.data.get("items", [])[:8], start=1):
                    post = item.get("post", item) if isinstance(item, dict) else {}
                    author = post.get("author", {}) if isinstance(post, dict) else {}
                    candidates[f"candidate_{idx}"] = Candidate(ref=f"candidate_{idx}", post_id=str(post.get("id", "")) or None, author_handle=author.get("handle") if isinstance(author, dict) else None, text=post.get("text") if isinstance(post, dict) else None)
            active = False
            options = policy.action_options(active_conversation=active).intent_options
            try:
                proposal = self.llm.propose_action(persona=agent.persona_seed, context={"timeline_candidates": [c.__dict__ for c in candidates.values()]}, action_options=options)
            except Exception as exc:  # noqa: BLE001
                self.writer.safe_record_issue(severity="warning", issue_class="llm_request_failed", component="llm_client", agent_handle=agent.handle, safe_message=str(exc))
                proposal = ActionProposal("silence")
            if proposal.intent not in options:
                proposal = ActionProposal(policy.choose_intent(active_conversation=active), proposal.candidate_ref, proposal.text, proposal.reason)
            plan = validate_and_plan_action(proposal, actor_handle=agent.handle, candidates=candidates, max_reply_depth=self.config.max_conversation_turns)
            outcome = "skipped"
            status_code = None
            if not plan.ok:
                self.writer.safe_record_issue(severity="info", issue_class=plan.issue_class or "policy_no_valid_action", component="actions", agent_handle=agent.handle, safe_message="proposal downgraded")
                intent = plan.intent
            elif plan.route_class is None:
                intent = plan.intent
                outcome = "silence"
            else:
                intent = plan.intent
                result = self._execute_plan(bearer, agent.handle, plan)
                outcome = "ok" if result.ok else "failed"
                status_code = result.status_code
                if not result.ok:
                    self.writer.safe_record_issue(severity="warning", issue_class=result.issue_class or "api_http_error", component="api_client", agent_handle=agent.handle, route_class=plan.route_class, safe_message=result.safe_summary)
            self.writer.record_activity(ActivityEvent(run_id=self.config.run_id, agent_handle=agent.handle, action=intent, route_class=plan.route_class, target=plan.target, outcome=outcome, status_code=status_code, summary=outcome))
            steps += 1
        if steps < self.config.max_steps:
            self.writer.safe_record_issue(severity="info", issue_class="shutdown_incomplete", component="runner", safe_message="runner stopped before max steps")
        self.writer.write_summary(config_summary=self.config.redacted_summary(), started_at=self.started_at)
        return RunnerResult("ok", self.config.run_id, steps, self.writer.issue_counts, self.writer.action_counts, str(self.writer.run_dir))

    def _execute_plan(self, bearer: str, handle: str, plan):
        if plan.intent in {"root_post"}:
            return self.api.create_post(bearer, plan.body.get("text", "Fictional used-car note."), agent_handle=handle)
        if plan.intent in {"reply", "reply_continue"}:
            return self.api.create_post(bearer, plan.body.get("text", "Fictional reply."), reply_to_post_id=plan.target.get("post_id"), agent_handle=handle)
        if plan.intent in {"quote", "quote_end"}:
            return self.api.create_post(bearer, plan.body.get("text", "Fictional quote."), quote_post_id=plan.target.get("post_id"), agent_handle=handle)
        if plan.intent in {"like", "like_end"}:
            return self.api.like_post(bearer, plan.target.get("post_id", ""), agent_handle=handle)
        if plan.intent == "repost":
            return self.api.repost(bearer, plan.target.get("post_id", ""), agent_handle=handle)
        if plan.intent in {"follow", "follow_end"}:
            return self.api.follow(bearer, plan.target.get("handle", ""), agent_handle=handle)
        raise RuntimeError("unsupported plan")
