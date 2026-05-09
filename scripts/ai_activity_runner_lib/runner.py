# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
from __future__ import annotations

import random
import time
from dataclasses import dataclass

from .actions import ActionPlan, Candidate, validate_and_plan_action
from .agent_registry import AgentRegistry
from .api_client import APIResult, V2APIClient
from .artifacts import ActivityEvent, ArtifactWriter, utc_now
from .config import AIActivityConfig, target_class, target_fingerprint
from .llm_client import ActionProposal, LocalCodexBridgeClient
from .operational_logging import RunnerOperationalLogger
from .policy import ActionDiversityTracker, WeightedActivityPolicy


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
        self.logger = RunnerOperationalLogger(run_id=config.run_id)
        self.api = V2APIClient(config.api_base_url, per_agent_retry_budget=config.llm_max_retries, logger=self.logger)
        self.llm = LocalCodexBridgeClient(config)
        self.started_at = utc_now()
        self.writer = ArtifactWriter(config.output_dir, config.run_id)
        self.diversity = ActionDiversityTracker(target_cooldown_steps=config.target_cooldown_steps, recent_action_window=config.recent_action_window, max_reply_share=config.max_reply_share)
        self.reused_agent_count = 0
        self.created_agent_count = 0
        self.proposal_repair_count = 0
        self.fallback_to_root_post_count = 0

    def run(self) -> RunnerResult:
        self.logger.emit(
            "runner_started",
            phase="startup",
            agent_count=self.config.agent_count,
            target_class=target_class(self.config.api_base_url),
            target_fingerprint=target_fingerprint(self.config.api_base_url),
            limit=self.config.max_steps,
        )
        agents = []
        try:
            registry = AgentRegistry(self.api, config=self.config, rng=self.rng)
            agents = registry.register_agents()
            self.writer.write_agent_registry(agents)
            self.created_agent_count = registry.created_count
            self.reused_agent_count = registry.reused_count
            self.logger.emit("agent_registry_completed", phase="signup", outcome_class="success", agent_count=len(agents), created_count=self.created_agent_count, reused_count=self.reused_agent_count)
        except Exception as exc:  # noqa: BLE001 - safe issue recording and summary
            self.logger.emit("agent_registry_failed", phase="signup", outcome_class="blocked", issue_class="signup_failed", safe_message=str(exc))
            self.writer.safe_record_issue(severity="error", issue_class="signup_failed", component="agent_registry", safe_message=str(exc))
            self.writer.write_summary(config_summary=self.config.redacted_summary(), started_at=self.started_at)
            self.logger.emit("runner_completed", phase="summary", outcome_class="blocked", agent_count=0, unique_action_classes=0, artifact_path_class="runner_private_artifacts")
            return RunnerResult("blocked", self.config.run_id, 0, self.writer.issue_counts, self.writer.action_counts, str(self.writer.run_dir))
        policy = WeightedActivityPolicy(rng=self.rng, replies_first=self.config.replies_first, diversity=self.diversity)
        deadline = time.monotonic() + self.config.max_wall_seconds
        steps = 0
        while steps < self.config.max_steps and time.monotonic() < deadline:
            agent = agents[steps % len(agents)]
            bearer = registry.vault.get(agent.credential_ref)
            candidates = self._build_candidates(actor_handle=agent.handle)
            active = False
            options = policy.action_options(active_conversation=active).intent_options
            candidates = self._apply_candidate_cooldown(candidates, step=steps)
            options = self._prefer_interactions_when_available(options, candidates)
            self.logger.emit(
                "runner_step_started",
                phase="activity_step",
                step=steps,
                safe_synthetic_actor_id=agent.handle,
                candidate_count=len(candidates),
                post_candidate_count=sum(1 for candidate in candidates.values() if candidate.post_id),
                unique_action_classes=len(self.writer.action_counts),
            )
            context = {
                "timeline_candidates": [c.__dict__ for c in candidates.values() if c.post_id],
                "agent_candidates": [c.__dict__ for c in candidates.values() if c.handle],
                "recent_actions": list(self.diversity.recent_actions),
                "recently_targeted_refs": list(self.diversity.recent_targets.keys())[-8:],
                "reply_share_too_high": self.diversity.reply_share_too_high(),
                "style_pack": agent.style_pack,
                "silliness_level": self.config.silliness_level,
                "chaos_level": self.config.chaos_level,
            }
            try:
                proposal = self.llm.propose_action(persona=agent.persona_seed, context=context, action_options=options)
                self.logger.emit("llm_proposal_received", phase="llm", outcome_class="success", step=steps, safe_synthetic_actor_id=agent.handle, intent=proposal.intent)
            except Exception as exc:  # noqa: BLE001
                self.logger.emit("llm_request_failed", phase="llm", outcome_class="failure", step=steps, safe_synthetic_actor_id=agent.handle, issue_class="llm_request_failed", safe_message=str(exc))
                self.writer.safe_record_issue(severity="warning", issue_class="llm_request_failed", component="llm_client", agent_handle=agent.handle, safe_message=str(exc))
                proposal = ActionProposal("silence")
            if proposal.intent not in options:
                self.proposal_repair_count += 1
                self.logger.emit("proposal_repaired", phase="policy", outcome_class="success", step=steps, safe_synthetic_actor_id=agent.handle, intent=proposal.intent, proposal_repair_count=self.proposal_repair_count)
                proposal = ActionProposal(self.rng.choice(options), proposal.candidate_ref, proposal.text, proposal.reason)
            repaired = self._repair_proposal_target(proposal, candidates)
            if repaired is not proposal:
                self.proposal_repair_count += 1
                self.logger.emit("proposal_repaired", phase="policy", outcome_class="success", step=steps, safe_synthetic_actor_id=agent.handle, intent=proposal.intent, proposal_repair_count=self.proposal_repair_count, target_ref_class="candidate_ref")
            proposal = repaired
            plan = validate_and_plan_action(proposal, actor_handle=agent.handle, candidates=candidates, max_reply_depth=self.config.max_conversation_turns)
            fallback_plan = self._fallback_missing_target_to_root_post(proposal, plan, actor_handle=agent.handle, candidates=candidates)
            if fallback_plan is not None:
                self.fallback_to_root_post_count += 1
                self.logger.emit("proposal_fallback_applied", phase="policy", outcome_class="success", step=steps, safe_synthetic_actor_id=agent.handle, intent=fallback_plan.intent, fallback_to_root_post_count=self.fallback_to_root_post_count)
                plan = fallback_plan
            outcome = "skipped"
            status_code = None
            if not plan.ok:
                self.logger.emit("action_skipped", phase="action", outcome_class="policy_rejected", step=steps, safe_synthetic_actor_id=agent.handle, intent=plan.intent, issue_class=plan.issue_class or "policy_no_valid_action")
                self.writer.safe_record_issue(severity="info", issue_class=plan.issue_class or "policy_no_valid_action", component="actions", agent_handle=agent.handle, safe_message="proposal downgraded")
                intent = plan.intent
            elif plan.route_class is None:
                intent = plan.intent
                outcome = "silence"
                self.logger.emit("action_silence", phase="action", outcome_class="silence", step=steps, safe_synthetic_actor_id=agent.handle, intent=intent)
            else:
                intent = plan.intent
                result = self._execute_plan(bearer, agent.handle, plan)
                outcome = "ok" if result.ok else "failed"
                status_code = result.status_code
                self.logger.emit("action_executed", phase="action", outcome_class="success" if result.ok else "failure", step=steps, safe_synthetic_actor_id=agent.handle, intent=intent, route_class=plan.route_class, status_code=status_code, issue_class=result.issue_class)
                if not result.ok:
                    self.writer.safe_record_issue(severity="warning", issue_class=result.issue_class or "api_http_error", component="api_client", agent_handle=agent.handle, route_class=plan.route_class, safe_message=result.safe_summary)
            target_key = plan.target.get("post_id") or plan.target.get("handle")
            self.diversity.record(intent, str(target_key) if target_key else None, step=steps, actor=agent.handle)
            self.writer.record_activity(ActivityEvent(run_id=self.config.run_id, agent_handle=agent.handle, action=intent, route_class=plan.route_class, target=plan.target, outcome=outcome, status_code=status_code, summary=outcome))
            steps += 1
        if steps < self.config.max_steps:
            self.writer.safe_record_issue(severity="info", issue_class="shutdown_incomplete", component="runner", safe_message="runner stopped before max steps")
        self.writer.write_summary(config_summary=self.config.redacted_summary(), started_at=self.started_at, extra={"reused_agent_count": self.reused_agent_count, "created_agent_count": self.created_agent_count, "action_diversity": {"unique_action_classes": len(self.writer.action_counts), "max_reply_share": self.config.max_reply_share}, "style_mode": "spicy_public_safe" if self.config.spicy_style else "public_safe"})
        self.logger.emit(
            "runner_completed",
            phase="summary",
            outcome_class="success",
            agent_count=len(agents),
            reused_count=self.reused_agent_count,
            created_count=self.created_agent_count,
            unique_action_classes=len(self.writer.action_counts),
            proposal_repair_count=self.proposal_repair_count,
            fallback_to_root_post_count=self.fallback_to_root_post_count,
            artifact_path_class="runner_private_artifacts",
        )
        return RunnerResult("ok", self.config.run_id, steps, self.writer.issue_counts, self.writer.action_counts, str(self.writer.run_dir))

    def _build_candidates(self, *, actor_handle: str) -> dict[str, Candidate]:
        candidates: dict[str, Candidate] = {}
        public = self.api.public_timeline(limit=20)
        authors: set[str] = set()
        actor_replied_to_posts, actor_replied_to_authors = self._actor_reply_history(actor_handle)
        fallback_post_candidates: dict[str, Candidate] = {}
        if public.ok and isinstance(public.data, dict):
            for idx, item in enumerate(public.data.get("items", [])[:20], start=1):
                post = item.get("post", item) if isinstance(item, dict) else {}
                post_id = str(post.get("id", "")) or None
                author = post.get("author", {}) if isinstance(post, dict) else {}
                author_handle = author.get("handle") if isinstance(author, dict) else None
                if author_handle:
                    authors.add(str(author_handle))
                if author_handle == actor_handle or not post_id or post_id in actor_replied_to_posts:
                    continue
                candidate = Candidate(ref=f"post_candidate_{idx}", post_id=post_id, author_handle=author_handle, text=post.get("text") if isinstance(post, dict) else None)
                fallback_post_candidates[candidate.ref] = candidate
                if str(author_handle) not in actor_replied_to_authors:
                    candidates[candidate.ref] = candidate
        if not any(candidate.post_id for candidate in candidates.values()):
            candidates.update(fallback_post_candidates)
        listed = self.api.list_agents()
        if listed.ok and isinstance(listed.data, dict):
            for item in listed.data.get("items", [])[:20]:
                if isinstance(item, dict) and item.get("handle"):
                    authors.add(str(item["handle"]))
        for idx, handle in enumerate(sorted(h for h in authors if h and h != actor_handle)[:8], start=1):
            candidates[f"agent_candidate_{idx}"] = Candidate(ref=f"agent_candidate_{idx}", handle=handle)
        return candidates

    def _actor_reply_history(self, actor_handle: str) -> tuple[set[str], set[str]]:
        replied_to_posts: set[str] = set()
        replied_to_authors: set[str] = set()
        replies = self.api.agent_posts(actor_handle, tab="replies", limit=50)
        if not replies.ok or not isinstance(replies.data, dict):
            return replied_to_posts, replied_to_authors
        for item in replies.data.get("items", []):
            post = item.get("post", item) if isinstance(item, dict) else {}
            if not isinstance(post, dict):
                continue
            target = post.get("reply_to_post_id") or post.get("parent_post_id") or post.get("reply_to")
            if target:
                replied_to_posts.add(str(target))
            parent = post.get("parent_summary")
            if isinstance(parent, dict):
                parent_author = parent.get("author")
                if isinstance(parent_author, dict) and parent_author.get("handle"):
                    replied_to_authors.add(str(parent_author["handle"]))
        return replied_to_posts, replied_to_authors

    def _apply_candidate_cooldown(self, candidates: dict[str, Candidate], *, step: int) -> dict[str, Candidate]:
        target_map = {ref: c.post_id or c.handle for ref, c in candidates.items()}
        allowed = set(self.diversity.allowed_candidate_refs(target_map, step=step))
        return {ref: c for ref, c in candidates.items() if ref in allowed} or candidates

    def _prefer_interactions_when_available(self, options: list[str], candidates: dict[str, Candidate]) -> list[str]:
        has_post_candidate = any(candidate.post_id for candidate in candidates.values())
        has_agent_candidate = any(candidate.handle for candidate in candidates.values())
        if not (has_post_candidate or has_agent_candidate) or "root_post" not in options:
            return options
        recent = list(self.diversity.recent_actions)
        root_count = sum(1 for action in recent if action == "root_post")
        interaction_count = sum(1 for action in recent if action in {"reply", "quote", "like", "repost", "follow", "reply_continue", "quote_end", "like_end", "follow_end"})
        root_posts_dominate = root_count >= 2 and root_count > interaction_count
        if not root_posts_dominate:
            return options
        filtered = [option for option in options if option != "root_post"]
        if has_post_candidate:
            for intent in ("reply", "quote", "like", "repost"):
                if intent not in filtered:
                    filtered.append(intent)
        if has_agent_candidate and "follow" not in filtered:
            filtered.append("follow")
        return filtered or options

    def _repair_proposal_target(self, proposal: ActionProposal, candidates: dict[str, Candidate]) -> ActionProposal:
        if proposal.candidate_ref in candidates:
            return proposal
        wants_agent = proposal.intent in {"follow", "follow_end"}
        wants_post = proposal.intent in {"reply", "reply_continue", "quote", "quote_end", "like", "like_end", "repost"}
        for ref, candidate in candidates.items():
            if wants_agent and candidate.handle:
                return ActionProposal(proposal.intent, ref, proposal.text, proposal.reason)
            if wants_post and candidate.post_id:
                return ActionProposal(proposal.intent, ref, proposal.text, proposal.reason)
        return proposal

    def _fallback_missing_target_to_root_post(
        self,
        proposal: ActionProposal,
        plan: ActionPlan,
        *,
        actor_handle: str,
        candidates: dict[str, Candidate],
    ) -> ActionPlan | None:
        if plan.ok or plan.issue_class != "missing_target":
            return None
        if proposal.intent not in {"reply", "reply_continue", "quote", "quote_end"}:
            return None
        fallback = ActionProposal("root_post", None, proposal.text, proposal.reason)
        fallback_plan = validate_and_plan_action(fallback, actor_handle=actor_handle, candidates=candidates, max_reply_depth=self.config.max_conversation_turns)
        return fallback_plan if fallback_plan.ok else None

    def _execute_plan(self, bearer: str, handle: str, plan: ActionPlan) -> APIResult:
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
