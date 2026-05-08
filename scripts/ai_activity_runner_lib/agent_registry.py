# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
from __future__ import annotations

import random
import re
import uuid
from dataclasses import dataclass
from typing import Any

from .api_client import V2APIClient
from .config import AIActivityConfig
from .personas import assign_style_pack, persona_seed_for
from .state_store import LocalAgentStateStore

HANDLE_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
RESERVED = {"admin", "root", "system", "support", "null", "undefined"}
THEMES = ["sedan", "truck", "miles", "diy", "audit", "salvage", "hybrid", "budget", "wrench", "commute"]
NAMES = ["alex", "mira", "nova", "riley", "casey", "jules", "taylor", "quinn", "avery", "rowan", "sage", "drew"]


@dataclass
class AgentIdentity:
    handle: str
    display_name: str
    bio: str
    persona_seed: str
    avatar_seed: str
    credential_ref: str
    style_pack: str = "car_forum_gremlins"

    def redacted_summary(self) -> dict[str, str]:
        return {
            "handle": self.handle,
            "display_name": self.display_name,
            "bio": self.bio,
            "persona_seed": self.persona_seed,
            "avatar_seed": self.avatar_seed,
            "style_pack": self.style_pack,
            "credential_ref": "redacted-runtime-only",
        }


class TokenVault:
    def __init__(self) -> None:
        self._tokens: dict[str, str] = {}

    def put(self, token: str) -> str:
        ref = f"cred_{uuid.uuid4().hex[:16]}"
        self._tokens[ref] = token
        return ref

    def get(self, ref: str) -> str:
        return self._tokens[ref]

    def __len__(self) -> int:
        return len(self._tokens)


class AgentRegistry:
    def __init__(self, api: V2APIClient, *, run_id: str | None = None, count: int | None = None, rng: random.Random | None = None, config: AIActivityConfig | None = None) -> None:
        self.api = api
        self.config = config
        self.run_id = run_id or (config.run_id if config else "run")
        self.count = count or (config.agent_count if config else 20)
        self.rng = rng or random.Random()
        self.vault = TokenVault()
        self.agents: list[AgentIdentity] = []
        self.issues: list[dict[str, Any]] = []
        self.created_count = 0
        self.reused_count = 0

    @property
    def style_pool(self) -> list[str]:
        return list((self.config.style_pack_pool if self.config else None) or ["car_forum_gremlins"])

    def _handle(self, index: int) -> str:
        if self.config and self.config.signup_mode in {"reuse_or_create", "reuse_only"}:
            theme = THEMES[index % len(THEMES)]
            name = NAMES[index % len(NAMES)]
            return f"syn_bot_{index:02d}_{theme}_{name}"[:24].strip("_")
        runpart = re.sub(r"[^a-z0-9]", "", self.run_id.lower())[-5:] or uuid.uuid4().hex[:5]
        theme = THEMES[index % len(THEMES)]
        name = NAMES[index % len(NAMES)]
        base = f"syn_{runpart}_{theme}_{name}"
        return base[:24].strip("_")

    def persona_payload(self, index: int) -> dict[str, str]:
        handle = self._handle(index)
        if not HANDLE_RE.match(handle) or handle in RESERVED or len(handle) < 3:
            handle = f"syn_{uuid.uuid4().hex[:10]}"
        theme = THEMES[index % len(THEMES)]
        name = NAMES[index % len(NAMES)].title()
        style_pack = assign_style_pack(index, self.style_pool)
        return {
            "handle": handle,
            "display_name": f"{name} {theme.title()} Scout"[:50],
            "bio": f"Fictional used-car shopper focused on {theme} tradeoffs."[:160],
            "persona_seed": persona_seed_for(index=index, theme=theme, style_pack=style_pack, rng=self.rng),
            "avatar_seed": f"{theme}-{name.lower()}"[:64],
            "style_pack": style_pack,
        }

    def _identity_from_record(self, record: dict[str, Any]) -> AgentIdentity:
        ref = self.vault.put(str(record["token"]))
        return AgentIdentity(
            handle=str(record["handle"]),
            display_name=str(record["display_name"]),
            bio=str(record["bio"]),
            persona_seed=str(record["persona_seed"]),
            avatar_seed=str(record["avatar_seed"]),
            style_pack=str(record.get("style_pack") or "car_forum_gremlins"),
            credential_ref=ref,
        )

    @staticmethod
    def _record_from_identity(agent: AgentIdentity, token: str) -> dict[str, str]:
        return {
            "handle": agent.handle,
            "display_name": agent.display_name,
            "bio": agent.bio,
            "persona_seed": agent.persona_seed,
            "avatar_seed": agent.avatar_seed,
            "style_pack": agent.style_pack,
            "token": token,
        }

    def _signup_one(self, index: int, seen: set[str]) -> tuple[AgentIdentity, str]:
        payload = self.persona_payload(index)
        attempts = 0
        while payload["handle"] in seen and attempts < 3:
            payload["handle"] = f"syn_{uuid.uuid4().hex[:10]}"
            attempts += 1
        seen.add(payload["handle"])
        signup_payload = {k: v for k, v in payload.items() if k != "style_pack"}
        result = self.api.signup_agent(signup_payload)
        if not result.ok and result.status_code == 409:
            payload["handle"] = f"syn_{uuid.uuid4().hex[:10]}"
            signup_payload = {k: v for k, v in payload.items() if k != "style_pack"}
            result = self.api.signup_agent(signup_payload)
        if not result.ok:
            self.issues.append({"issue_class": "signup_failed", "safe_message": result.safe_summary, "status_code": result.status_code})
            raise RuntimeError("dynamic signup did not reach configured agent count")
        data = result.data if isinstance(result.data, dict) else {}
        token = str(data.get("bearer_token") or data.get("token") or data.get("access_token") or "")
        if not token:
            self.issues.append({"issue_class": "signup_failed", "safe_message": "signup response missing display-once token"})
            raise RuntimeError("dynamic signup did not reach configured agent count")
        agent_data = data.get("agent")
        if not isinstance(agent_data, dict):
            agent_data = data
        ref = self.vault.put(token)
        agent = AgentIdentity(
            handle=str(agent_data.get("handle", payload["handle"])),
            display_name=str(agent_data.get("display_name", payload["display_name"])),
            bio=str(agent_data.get("bio", payload["bio"])),
            persona_seed=payload["persona_seed"],
            avatar_seed=payload["avatar_seed"],
            style_pack=payload["style_pack"],
            credential_ref=ref,
        )
        return agent, token

    def signup_all(self) -> list[AgentIdentity]:
        seen: set[str] = set()
        for idx in range(self.count):
            agent, _token = self._signup_one(idx, seen)
            self.created_count += 1
            self.agents.append(agent)
        if len(self.agents) != self.count:
            self.issues.append({"issue_class": "signup_failed", "safe_message": "configured agent count was not reached"})
            raise RuntimeError("dynamic signup did not reach configured agent count")
        return self.agents

    def register_agents(self) -> list[AgentIdentity]:
        if not self.config or self.config.signup_mode == "dynamic":
            return self.signup_all()
        store = LocalAgentStateStore(self.config.state_dir, target_fingerprint=self.config.state_target_fingerprint)
        state = store.load()
        if state.malformed:
            self.issues.append({"issue_class": "state_load_failed", "safe_message": "local reusable agent state could not be loaded"})
            if self.config.signup_mode == "reuse_only":
                raise RuntimeError("reusable agent state incomplete")
        records = list(state.agents)
        if len(records) < self.count and self.config.signup_mode == "reuse_only":
            self.issues.append({"issue_class": "state_reuse_failed", "safe_message": "reusable agent state incomplete"})
            raise RuntimeError("reusable agent state incomplete")
        seen = {str(r.get("handle")) for r in records}
        while len(records) < self.count:
            agent, token = self._signup_one(len(records), seen)
            self.created_count += 1
            records.append(self._record_from_identity(agent, token))
        selected_records = store.select_rotating(records, count=self.count, rotation=self.config.state_rotation, cursor=state.rotation_cursor)
        next_cursor = (state.rotation_cursor + self.count) % len(records) if records else 0
        store.save(records, rotation_cursor=next_cursor)
        self.agents = [self._identity_from_record(record) for record in selected_records]
        self.reused_count = len(self.agents) - self.created_count
        return self.agents
