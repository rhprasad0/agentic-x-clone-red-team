# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
from __future__ import annotations

import random
import re
import uuid
from dataclasses import dataclass
from typing import Any

from .api_client import V2APIClient

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

    def redacted_summary(self) -> dict[str, str]:
        return {"handle": self.handle, "display_name": self.display_name, "bio": self.bio, "persona_seed": self.persona_seed, "avatar_seed": self.avatar_seed, "credential_ref": "redacted-runtime-only"}

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
    def __init__(self, api: V2APIClient, *, run_id: str, count: int, rng: random.Random | None = None) -> None:
        self.api = api
        self.run_id = run_id
        self.count = count
        self.rng = rng or random.Random()
        self.vault = TokenVault()
        self.agents: list[AgentIdentity] = []
        self.issues: list[dict[str, Any]] = []

    def _handle(self, index: int) -> str:
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
        return {
            "handle": handle,
            "display_name": f"{name} {theme.title()} Scout"[:50],
            "bio": f"Fictional used-car shopper focused on {theme} tradeoffs."[:160],
            "persona_seed": f"Synthetic {theme} buyer. Discusses public-safe fictional listings only."[:400],
            "avatar_seed": f"{theme}-{name.lower()}"[:64],
        }

    def signup_all(self) -> list[AgentIdentity]:
        seen: set[str] = set()
        for idx in range(self.count):
            payload = self.persona_payload(idx)
            while payload["handle"] in seen:
                payload["handle"] = f"syn_{uuid.uuid4().hex[:10]}"
            seen.add(payload["handle"])
            result = self.api.signup_agent(payload)
            if not result.ok:
                self.issues.append({"issue_class": "signup_failed", "safe_message": result.safe_summary, "status_code": result.status_code})
                break
            data = result.data if isinstance(result.data, dict) else {}
            token = str(data.get("bearer_token") or data.get("token") or data.get("access_token") or "")
            if not token:
                self.issues.append({"issue_class": "signup_failed", "safe_message": "signup response missing display-once token"})
                break
            agent_data = data.get("agent") if isinstance(data.get("agent"), dict) else data
            ref = self.vault.put(token)
            self.agents.append(AgentIdentity(
                handle=str(agent_data.get("handle", payload["handle"])),
                display_name=str(agent_data.get("display_name", payload["display_name"])),
                bio=str(agent_data.get("bio", payload["bio"])),
                persona_seed=payload["persona_seed"],
                avatar_seed=payload["avatar_seed"],
                credential_ref=ref,
            ))
        if len(self.agents) != self.count:
            self.issues.append({"issue_class": "signup_failed", "safe_message": "configured agent count was not reached"})
            raise RuntimeError("dynamic signup did not reach configured agent count")
        return self.agents
