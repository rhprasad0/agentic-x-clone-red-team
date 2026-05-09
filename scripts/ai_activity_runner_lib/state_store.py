# ruff: noqa: E501
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .personas import STYLE_PACK_PROMPTS
from .redaction import validate_generated_social_text

LOCAL_STATE_SCHEMA = "v2-ai-activity-runner.local-state.v1"
HANDLE_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


@dataclass
class LocalAgentState:
    agents: list[dict[str, Any]] = field(default_factory=list)
    rotation_cursor: int = 0
    malformed: bool = False


class LocalAgentStateStore:
    def __init__(self, state_dir: str | Path, *, target_fingerprint: str) -> None:
        self.state_dir = Path(state_dir)
        self.target_fingerprint = target_fingerprint
        self.path = self.state_dir / f"agents.{target_fingerprint}.local.json"

    def load(self) -> LocalAgentState:
        if not self.path.exists():
            return LocalAgentState()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return LocalAgentState(malformed=True)
        if not isinstance(data, dict) or data.get("schema_version") != LOCAL_STATE_SCHEMA:
            return LocalAgentState(malformed=True)
        if data.get("target_fingerprint") != self.target_fingerprint:
            return LocalAgentState(malformed=True)
        agents = data.get("agents")
        if not isinstance(agents, list):
            return LocalAgentState(malformed=True)
        usable: list[dict[str, Any]] = []
        for item in agents:
            if not isinstance(item, dict):
                continue
            if not all(isinstance(item.get(k), str) and item.get(k) for k in ("handle", "display_name", "bio", "persona_seed", "avatar_seed", "style_pack", "token")):
                continue
            handle = str(item["handle"])
            style_pack = str(item["style_pack"])
            public_text = " ".join(str(item[k]) for k in ("display_name", "bio", "persona_seed", "avatar_seed"))
            if not HANDLE_RE.fullmatch(handle) or style_pack not in STYLE_PACK_PROMPTS or not validate_generated_social_text(public_text).ok:
                return LocalAgentState(malformed=True)
            usable.append(dict(item))
        rotation_cursor = data.get("rotation_cursor", 0)
        if not isinstance(rotation_cursor, int) or rotation_cursor < 0:
            rotation_cursor = 0
        return LocalAgentState(agents=usable, rotation_cursor=rotation_cursor)

    def save(self, agents: list[dict[str, Any]], *, rotation_cursor: int = 0) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": LOCAL_STATE_SCHEMA,
            "target_fingerprint": self.target_fingerprint,
            "rotation_cursor": rotation_cursor,
            "agents": agents,
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def clear(self) -> dict[str, int]:
        state = self.load()
        removed_records = len(state.agents)
        removed_files = 0
        try:
            self.path.unlink()
            removed_files = 1
        except FileNotFoundError:
            pass
        return {"removed_files": removed_files, "removed_records": removed_records}

    def remove_handles(self, handles: set[str]) -> tuple[list[dict[str, Any]], int]:
        state = self.load()
        kept = [record for record in state.agents if str(record.get("handle")) not in handles]
        removed = len(state.agents) - len(kept)
        self.save(kept, rotation_cursor=0)
        return kept, removed

    @staticmethod
    def select_rotating(records: list[dict[str, Any]], *, count: int, rotation: bool, cursor: int = 0) -> list[dict[str, Any]]:
        if len(records) <= count or not rotation:
            return list(records[:count])
        start = cursor % len(records)
        ordered = records[start:] + records[:start]
        return ordered[:count]
