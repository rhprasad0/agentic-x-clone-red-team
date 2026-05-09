# ruff: noqa: E501

import json
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from scripts.ai_activity_runner_lib.actions import Candidate, validate_and_plan_action
from scripts.ai_activity_runner_lib.agent_registry import AgentRegistry
from scripts.ai_activity_runner_lib.api_client import V2APIClient
from scripts.ai_activity_runner_lib.config import AIActivityConfig, ConfigError
from scripts.ai_activity_runner_lib.llm_client import ActionProposal
from scripts.ai_activity_runner_lib.policy import ActionDiversityTracker, WeightedActivityPolicy
from scripts.ai_activity_runner_lib.runner import SyntheticLoadRunner
from scripts.ai_activity_runner_lib.state_store import LocalAgentStateStore


class ReuseFakeHandler(BaseHTTPRequestHandler):
    requests = []
    signup_count = 0
    timeline_items = [
        {"post": {"id": "post_seen", "text": "Synthetic root already answered", "author": {"handle": "synthetic_mira"}}},
        {"post": {"id": "post_fresh", "text": "Synthetic root still fresh", "author": {"handle": "synthetic_alex"}}},
    ]

    def log_message(self, format, *args):
        return

    def _send(self, code, payload=None):
        raw = json.dumps(payload or {}).encode() if payload is not None else b""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        return json.loads(raw.decode() or "{}") if raw else {}

    def do_POST(self):
        body = self._body()
        type(self).requests.append(("POST", self.path, body))
        if self.path == "/agents/signup":
            type(self).signup_count += 1
            h = body.get("handle", f"syn_fake_{type(self).signup_count}")
            return self._send(201, {"agent": {"handle": h, "display_name": body.get("display_name", "Synthetic Agent"), "bio": body.get("bio", "fictional")}, "bearer_token": f"runtime_token_{type(self).signup_count}_not_public"})
        return self._send(201, {"ok": True})

    def do_GET(self):
        type(self).requests.append(("GET", self.path, None))
        if self.path.startswith("/timelines/public"):
            return self._send(200, {"items": type(self).timeline_items})
        if self.path.startswith("/agents/syn_actor/replies"):
            return self._send(200, {"items": [
                {"post": {"id": "reply_1", "reply_to_post_id": "post_seen", "text": "Synthetic prior reply", "author": {"handle": "syn_actor"}, "parent_summary": {"id": "post_seen", "author": {"handle": "synthetic_mira"}}}}
            ]})
        if self.path.startswith("/agents"):
            return self._send(200, {"items": [{"handle": "synthetic_mira"}, {"handle": "synthetic_alex"}]})
        return self._send(404, {"detail": "not found"})


def serve(handler=ReuseFakeHandler):
    handler.requests = []
    handler.signup_count = 0
    handler.timeline_items = [
        {"post": {"id": "post_seen", "text": "Synthetic root already answered", "author": {"handle": "synthetic_mira"}}},
        {"post": {"id": "post_fresh", "text": "Synthetic root still fresh", "author": {"handle": "synthetic_alex"}}},
    ]
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_port}"


def config(tmp_path, url="http://127.0.0.1:8001", **kwargs):
    c = AIActivityConfig(
        api_base_url=url,
        agent_count=kwargs.pop("agent_count", 4),
        signup_mode=kwargs.pop("signup_mode", "reuse_or_create"),
        output_dir=str(tmp_path / ".hermes" / "tmp" / "ai-activity-runner"),
        state_dir=str(tmp_path / ".hermes" / "tmp" / "ai-activity-runner" / "state"),
        run_id=kwargs.pop("run_id", "run_test_01"),
        llm_api_key="bridge_local_key_placeholder",
        **kwargs,
    )
    c.validate()
    return c


def test_config_accepts_reuse_modes_rejects_unsafe_state_and_style_pool(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_ACTIVITY_LLM_API_KEY", "bridge_local_key_placeholder")
    monkeypatch.setenv("AI_ACTIVITY_OUTPUT_DIR", str(tmp_path / ".hermes" / "tmp" / "ai-activity-runner"))
    monkeypatch.setenv("AI_ACTIVITY_STATE_DIR", str(tmp_path / ".hermes" / "tmp" / "ai-activity-runner" / "state"))
    monkeypatch.setenv("AI_ACTIVITY_AGENT_COUNT", "4")
    monkeypatch.setenv("AI_ACTIVITY_SIGNUP_MODE", "reuse_or_create")
    monkeypatch.setenv("AI_ACTIVITY_STYLE_PACK_POOL", "car_forum_gremlins,auction_lot_cryptids")
    assert AIActivityConfig.from_env().signup_mode == "reuse_or_create"
    monkeypatch.setenv("AI_ACTIVITY_SIGNUP_MODE", "reuse_only")
    assert AIActivityConfig.from_env().signup_mode == "reuse_only"
    monkeypatch.setenv("AI_ACTIVITY_SIGNUP_MODE", "dynamic")
    assert AIActivityConfig.from_env().signup_mode == "dynamic"
    monkeypatch.setenv("AI_ACTIVITY_SIGNUP_MODE", "oops")
    with pytest.raises(ConfigError, match="unsupported signup mode"):
        AIActivityConfig.from_env()
    monkeypatch.setenv("AI_ACTIVITY_SIGNUP_MODE", "reuse_or_create")
    monkeypatch.setenv("AI_ACTIVITY_STATE_DIR", "public-state")
    with pytest.raises(ConfigError, match="STATE_DIR"):
        AIActivityConfig.from_env()
    monkeypatch.setenv("AI_ACTIVITY_STATE_DIR", str(tmp_path / ".hermes" / "tmp" / "ai-activity-runner" / "state"))
    monkeypatch.setenv("AI_ACTIVITY_STYLE_PACK_POOL", "car_forum_gremlins,real_person_pack")
    with pytest.raises(ConfigError, match="STYLE_PACK"):
        AIActivityConfig.from_env()


def test_reuse_or_create_reuses_full_state_without_signup_and_scopes_by_target(tmp_path):
    server, thread, url = serve()
    try:
        c = config(tmp_path, url=url, agent_count=4, run_id="run_reuse_full")
        store = LocalAgentStateStore(c.state_dir, target_fingerprint=c.state_target_fingerprint)
        records = []
        for i, pack in enumerate(c.style_pack_pool):
            records.append({"handle": f"syn_reuse_{i}", "display_name": f"Reuse {i}", "bio": "fictional", "persona_seed": f"persona {i}", "avatar_seed": f"avatar-{i}", "style_pack": pack, "token": f"local_token_{i}"})
        store.save(records, rotation_cursor=0)
        reg = AgentRegistry(V2APIClient(url), config=c, rng=random.Random(1))
        agents = reg.register_agents()
        assert len(agents) == 4
        assert ReuseFakeHandler.signup_count == 0
        assert [a.style_pack for a in agents] == c.style_pack_pool
        other = config(tmp_path, url="http://127.0.0.1:9999", agent_count=4, run_id="run_other")
        assert LocalAgentStateStore(other.state_dir, target_fingerprint=other.state_target_fingerprint).load().agents == []
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_dynamic_mode_always_creates_fresh_cohort(tmp_path):
    server, thread, url = serve()
    try:
        c = config(tmp_path, url=url, agent_count=4, signup_mode="dynamic", run_id="run_dynamic")
        reg = AgentRegistry(V2APIClient(url), config=c, rng=random.Random(1))
        agents = reg.register_agents()
        assert len(agents) == 4
        assert ReuseFakeHandler.signup_count == 4
        assert reg.created_count == 4 and reg.reused_count == 0
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_reuse_or_create_partial_creates_missing_and_reuse_only_blocks(tmp_path):
    server, thread, url = serve()
    try:
        c = config(tmp_path, url=url, agent_count=4, run_id="run_partial")
        store = LocalAgentStateStore(c.state_dir, target_fingerprint=c.state_target_fingerprint)
        store.save([{"handle": f"syn_partial_{i}", "display_name": f"Partial {i}", "bio": "fictional", "persona_seed": f"persona {i}", "avatar_seed": f"avatar-{i}", "style_pack": c.style_pack_pool[i], "token": f"local_token_{i}"} for i in range(3)], rotation_cursor=0)
        reg = AgentRegistry(V2APIClient(url), config=c, rng=random.Random(1))
        assert len(reg.register_agents()) == 4
        assert ReuseFakeHandler.signup_count == 1
        c2 = config(tmp_path, url=url, agent_count=5, signup_mode="reuse_only", run_id="run_only")
        reg2 = AgentRegistry(V2APIClient(url), config=c2, rng=random.Random(1))
        with pytest.raises(RuntimeError, match="reusable agent state incomplete"):
            reg2.register_agents()
        assert ReuseFakeHandler.signup_count == 1
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_rotation_selects_different_cohorts_when_state_exceeds_count(tmp_path):
    c = config(tmp_path, agent_count=4, run_id="run_rotate")
    store = LocalAgentStateStore(c.state_dir, target_fingerprint=c.state_target_fingerprint)
    records = [{"handle": f"syn_rotate_{i}", "display_name": f"Rotate {i}", "bio": "fictional", "persona_seed": f"persona {i}", "avatar_seed": f"avatar-{i}", "style_pack": c.style_pack_pool[i % len(c.style_pack_pool)], "token": f"local_token_{i}"} for i in range(6)]
    store.save(records, rotation_cursor=0)
    first = store.select_rotating(records, count=4, rotation=True, cursor=0)
    store.save(records, rotation_cursor=4)
    second = store.select_rotating(records, count=4, rotation=True, cursor=4)
    assert [r["handle"] for r in first] != [r["handle"] for r in second]


def test_policy_tracker_downweights_replies_and_filters_recent_targets():
    tracker = ActionDiversityTracker(target_cooldown_steps=6, recent_action_window=12, max_reply_share=0.45)
    for step in range(8):
        tracker.record("reply", "post_same", step=step, actor="syn_a")
    policy = WeightedActivityPolicy(rng=random.Random(1), replies_first=True, diversity=tracker)
    options = policy.action_options(active_conversation=False).intent_options
    assert "reply" not in options
    candidates = {"a": "post_same", "b": "post_other"}
    assert tracker.allowed_candidate_refs(candidates, step=9) == ["b"]


def test_runner_excludes_posts_actor_already_replied_to_across_runs(tmp_path):
    server, thread, url = serve()
    try:
        c = config(tmp_path, url=url, agent_count=4, run_id="run_no_duplicate_replies")
        runner = SyntheticLoadRunner(c)
        candidates = runner._build_candidates(actor_handle="syn_actor")
        post_targets = {candidate.post_id for candidate in candidates.values() if candidate.post_id}
        author_targets = {candidate.author_handle for candidate in candidates.values() if candidate.post_id}
        assert "post_seen" not in post_targets
        assert "synthetic_mira" not in author_targets
        assert "post_fresh" in post_targets
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_runner_allows_fresh_posts_from_seen_authors_when_strict_author_filter_starves(tmp_path):
    server, thread, url = serve()
    try:
        ReuseFakeHandler.timeline_items = [
            {"post": {"id": "post_seen", "text": "Synthetic root already answered", "author": {"handle": "synthetic_mira"}}},
            {"post": {"id": "post_mira_fresh", "text": "Synthetic fresh post by a previously answered author", "author": {"handle": "synthetic_mira"}}},
        ]
        c = config(tmp_path, url=url, agent_count=4, run_id="run_author_fallback")
        runner = SyntheticLoadRunner(c)
        candidates = runner._build_candidates(actor_handle="syn_actor")
        post_targets = {candidate.post_id for candidate in candidates.values() if candidate.post_id}
        assert "post_seen" not in post_targets
        assert "post_mira_fresh" in post_targets
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_runner_missing_target_text_action_falls_back_to_root_post(tmp_path):
    c = config(tmp_path, agent_count=4, run_id="run_missing_target_fallback")
    runner = SyntheticLoadRunner(c)
    proposal = ActionProposal("reply", "stale_candidate", "Fictional fallback post about a harmless dashboard gremlin.", "stale target")
    plan = validate_and_plan_action(proposal, actor_handle="syn_actor", candidates={"fresh": Candidate(ref="fresh", post_id="post_fresh", author_handle="synthetic_alex")})
    assert plan.issue_class == "missing_target"
    fallback = runner._fallback_missing_target_to_root_post(proposal, plan, actor_handle="syn_actor", candidates={})
    assert fallback is not None
    assert fallback.ok is True
    assert fallback.intent == "root_post"
    assert fallback.body["text"] == "Fictional fallback post about a harmless dashboard gremlin."


def test_runner_recovers_reuse_or_create_stale_token_once(tmp_path):
    class RejectStaleOnce(ReuseFakeHandler):
        post_authorizations = []
        def do_POST(self):
            body = self._body()
            type(self).requests.append(("POST", self.path, body))
            if self.path == "/agents/signup":
                type(self).signup_count += 1
                h = body.get("handle", f"syn_fake_{type(self).signup_count}")
                return self._send(201, {"agent": {"handle": h, "display_name": body.get("display_name", "Synthetic Agent"), "bio": body.get("bio", "fictional")}, "bearer_token": "fresh_runtime_token_not_public"})
            if self.path == "/posts":
                auth = self.headers.get("Authorization", "")
                type(self).post_authorizations.append(auth)
                if "stale_runtime_token" in auth:
                    return self._send(401, {"detail": "Unauthorized"})
                return self._send(201, {"id": "post_recovered", **body})
            return super().do_POST()
    server, thread, url = serve(RejectStaleOnce)
    try:
        c = config(tmp_path, url=url, agent_count=1, run_id="run_stale_recovery", max_steps=1)
        store = LocalAgentStateStore(c.state_dir, target_fingerprint=c.state_target_fingerprint)
        store.save([{"handle": "syn_stale_0", "display_name": "Stale 0", "bio": "fictional", "persona_seed": "persona", "avatar_seed": "avatar", "style_pack": "car_forum_gremlins", "token": "stale_runtime_token"}], rotation_cursor=0)
        runner = SyntheticLoadRunner(c)
        class FixedLLM:
            def propose_action(self, **kwargs):
                return ActionProposal("root_post", None, "Fictional gremlin recovery post.", "test")
        runner.llm = FixedLLM()
        result = runner.run()
        assert result.status == "ok"
        assert result.issues.get("token_rejected_recovered") == 1
        assert RejectStaleOnce.signup_count == 1
        assert RejectStaleOnce.post_authorizations == ["Bearer stale_runtime_token", "Bearer fresh_runtime_token_not_public"]
        loaded = store.load().agents
        assert len(loaded) == 1
        assert loaded[0]["token"] == "fresh_runtime_token_not_public"
        assert loaded[0]["handle"] != "syn_stale_0"
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_runner_removes_root_post_when_interaction_candidates_exist_and_roots_dominate(tmp_path):
    c = config(tmp_path, agent_count=4, run_id="run_interaction_bias")
    runner = SyntheticLoadRunner(c)
    for step in range(4):
        runner.diversity.record("root_post", None, step=step, actor=f"syn_actor_{step}")
    candidates = {
        "post_candidate_1": Candidate(ref="post_candidate_1", post_id="post_fresh", author_handle="synthetic_alex"),
        "agent_candidate_1": Candidate(ref="agent_candidate_1", handle="synthetic_mira"),
    }

    options = runner._prefer_interactions_when_available(["root_post", "reply", "quote", "like", "follow", "silence"], candidates)

    assert "root_post" not in options
    assert {"reply", "quote", "like", "follow"}.issubset(set(options))


def test_default_four_personas_are_diverse_and_weird(tmp_path):
    c = config(tmp_path, agent_count=4, run_id="run_personas")
    server, thread, url = serve()
    try:
        reg = AgentRegistry(V2APIClient(url), config=c, rng=random.Random(42))
        payloads = [reg.persona_payload(i) for i in range(4)]
        assert [p["style_pack"] for p in payloads] == ["car_forum_gremlins", "marketplace_menace", "spreadsheet_goblins", "auction_lot_cryptids"]
        assert len({p["persona_seed"] for p in payloads}) == 4
        assert all("Fictional" in p["bio"] or "fictional" in p["bio"] for p in payloads)
    finally:
        server.shutdown()
        thread.join(timeout=2)

def test_different_random_seeds_change_persona_bits(tmp_path):
    c1 = config(tmp_path / "a", agent_count=4, run_id="run_seed_a")
    c2 = config(tmp_path / "b", agent_count=4, run_id="run_seed_b")
    server, thread, url = serve()
    try:
        p1 = [AgentRegistry(V2APIClient(url), config=c1, rng=random.Random(1)).persona_payload(i)["persona_seed"] for i in range(4)]
        p2 = [AgentRegistry(V2APIClient(url), config=c2, rng=random.Random(2)).persona_payload(i)["persona_seed"] for i in range(4)]
        assert p1 != p2
    finally:
        server.shutdown()
        thread.join(timeout=2)

def test_state_load_rejects_payload_fingerprint_mismatch(tmp_path):
    c = config(tmp_path, agent_count=4, run_id="run_fingerprint")
    store = LocalAgentStateStore(c.state_dir, target_fingerprint=c.state_target_fingerprint)
    store.save([{"handle": "syn_reuse_0", "display_name": "Reuse 0", "bio": "fictional", "persona_seed": "persona", "avatar_seed": "avatar", "style_pack": "car_forum_gremlins", "token": "local_token"}], rotation_cursor=0)
    payload = json.loads(Path(store.path).read_text())
    payload["target_fingerprint"] = "differenttarget00"
    Path(store.path).write_text(json.dumps(payload))
    loaded = store.load()
    assert loaded.malformed is True
    assert loaded.agents == []


def test_state_load_rejects_unapproved_style_pack_and_unsafe_public_fields(tmp_path):
    c = config(tmp_path, agent_count=4, run_id="run_state_safety")
    store = LocalAgentStateStore(c.state_dir, target_fingerprint=c.state_target_fingerprint)
    store.save([{"handle": "syn_reuse_0", "display_name": "Reuse 0", "bio": "email person@example.net", "persona_seed": "persona", "avatar_seed": "avatar", "style_pack": "real_person_pack", "token": "local_token"}], rotation_cursor=0)
    loaded = store.load()
    assert loaded.malformed is True
    assert loaded.agents == []
