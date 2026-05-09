# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import urllib.parse
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .personas import DEFAULT_STYLE_PACK_POOL, STYLE_PACK_PROMPTS

LOCAL_CODEX_BRIDGE = "local_codex_bridge"
DEFAULT_LLM_MODEL = "gpt-5.4-mini"
DEFAULT_OUTPUT_DIR = ".hermes/tmp/ai-activity-runner"
MAX_AGENT_COUNT = 100
SIGNUP_MODES = {"dynamic", "reuse_or_create", "reuse_only"}
_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")


class ConfigError(ValueError):
    """Raised when runner configuration is missing or unsafe."""


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _bool_env(name: str, default: bool) -> bool:
    value = _env(name)
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{name} must be a boolean")


def _int_env(name: str, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    raw = _env(name, str(default)) or str(default)
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ConfigError(f"{name} must be <= {maximum}")
    return value


def _float_env(name: str, default: float, *, minimum: float | None = None, maximum: float | None = None) -> float:
    raw = _env(name, str(default)) or str(default)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number") from exc
    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ConfigError(f"{name} must be <= {maximum}")
    return value


def _csv_env(name: str, default: list[str]) -> list[str]:
    raw = _env(name)
    if raw is None:
        return list(default)
    values = [v.strip() for v in raw.split(",") if v.strip()]
    return values or list(default)


def _is_loopback_host(hostname: str | None) -> bool:
    return hostname in {"localhost", "127.0.0.1", "::1"}


def _is_kubernetes_service_host(hostname: str | None) -> bool:
    if hostname is None:
        return False
    return hostname.endswith(".svc") or ".svc." in hostname


def _validate_http_url(url: str, *, label: str, allow_plaintext_loopback: bool = True) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError(f"{label} must be an absolute HTTP(S) URL")
    if parsed.scheme == "http" and not (
        allow_plaintext_loopback
        and (_is_loopback_host(parsed.hostname) or _is_kubernetes_service_host(parsed.hostname))
    ):
        raise ConfigError(f"non-loopback {label} URLs must use HTTPS")


def target_class(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if _is_loopback_host(parsed.hostname):
        return "loopback"
    if _is_kubernetes_service_host(parsed.hostname):
        return "kubernetes_service"
    if parsed.scheme == "https":
        return "https"
    return "unsafe"


def target_fingerprint(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    normalized = urllib.parse.urlunparse((parsed.scheme.lower(), (parsed.netloc or "").lower(), parsed.path.rstrip("/"), "", "", ""))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _short_path(path: str) -> str:
    p = Path(path)
    parts = p.parts
    if ".hermes" in parts:
        idx = parts.index(".hermes")
        return str(Path(*parts[idx:]))
    return p.name


def _path_is_git_ignored(path: Path) -> bool:
    try:
        result = subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=Path.cwd(), check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except OSError:
        return False


def _path_outside_repo(path: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(Path.cwd().resolve(strict=False))
        return False
    except ValueError:
        return True


def _validate_private_dir(path_value: str, *, label: str) -> None:
    p = Path(path_value)
    raw = str(p)
    if raw in {".", "", "/"}:
        raise ConfigError(f"{label} must be an ignored private runner directory")
    parts = p.parts
    is_default_private = raw.startswith(".hermes/") or raw == ".hermes"
    is_external_private = p.is_absolute() and _path_outside_repo(p) and ".hermes" in parts
    if not (is_default_private or is_external_private or (".hermes" in parts and _path_is_git_ignored(p)) or _path_is_git_ignored(p)):
        raise ConfigError(f"{label} must be ignored/private, such as .hermes/tmp/ai-activity-runner")
    parent = p if p.exists() else p.parent
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    if parent.exists() and not os.access(parent, os.W_OK):
        raise ConfigError(f"{label} is not writable: {_short_path(raw)}")


def _validate_output_dir(output_dir: str) -> None:
    _validate_private_dir(output_dir, label="AI_ACTIVITY_OUTPUT_DIR")


def _validate_state_dir(state_dir: str) -> None:
    try:
        _validate_private_dir(state_dir, label="AI_ACTIVITY_STATE_DIR")
    except ConfigError as exc:
        raise ConfigError("AI_ACTIVITY_STATE_DIR must be ignored/private, such as .hermes/tmp/ai-activity-runner/state") from exc


def _validate_run_id(run_id: str) -> None:
    if run_id in {".", ".."} or not _SAFE_RUN_ID.fullmatch(run_id) or ".." in run_id:
        raise ConfigError("AI_ACTIVITY_RUN_ID must be a safe slug without path traversal")


def _safe_run_dir(output_dir: str, run_id: str) -> Path:
    _validate_run_id(run_id)
    root = Path(output_dir)
    run_dir = root / run_id
    try:
        resolved_root = root.resolve(strict=False)
        resolved_run = run_dir.resolve(strict=False)
        resolved_run.relative_to(resolved_root)
    except ValueError as exc:
        raise ConfigError("AI_ACTIVITY_RUN_ID must stay within AI_ACTIVITY_OUTPUT_DIR") from exc
    return run_dir


def _validate_style_pack(name: str, label: str = "AI_ACTIVITY_STYLE_PACK") -> None:
    if name not in STYLE_PACK_PROMPTS:
        raise ConfigError(f"{label} must be one of the public-safe style packs")


@dataclass(frozen=True)
class AIActivityConfig:
    api_base_url: str = "http://localhost:8000"
    runner_mode: str = "synthetic_load"
    agent_count: int = 4
    signup_mode: str = "reuse_or_create"
    output_dir: str = DEFAULT_OUTPUT_DIR
    state_dir: str = DEFAULT_OUTPUT_DIR + "/state"
    state_rotation: bool = True
    run_id: str = ""
    llm_provider: str = LOCAL_CODEX_BRIDGE
    llm_base_url: str = "http://localhost:4000/v1"
    llm_api_key: str = ""
    llm_model: str = DEFAULT_LLM_MODEL
    llm_timeout_seconds: float = 45.0
    llm_max_retries: int = 2
    llm_temperature: float = 0.8
    llm_response_budget: int = 500
    max_steps: int = 400
    max_wall_seconds: int = 900
    concurrency: int = 4
    random_seed: int | None = None
    max_conversation_turns: int = 4
    replies_first: bool = True
    target_cooldown_steps: int = 6
    recent_action_window: int = 12
    max_reply_share: float = 0.45
    spicy_style: bool = True
    silliness_level: float = 1.0
    chaos_level: float = 0.35
    style_pack: str = "car_forum_gremlins"
    style_pack_pool: list[str] = field(default_factory=lambda: list(DEFAULT_STYLE_PACK_POOL))
    redact_artifacts: bool = True
    live_llm_smoke: bool = False

    @classmethod
    def from_env(cls) -> AIActivityConfig:
        seed_raw = _env("AI_ACTIVITY_RANDOM_SEED")
        run_id = _env("AI_ACTIVITY_RUN_ID") or f"run_{uuid.uuid4().hex[:12]}"
        config = cls(
            api_base_url=_env("AI_ACTIVITY_API_BASE_URL", "http://localhost:8000") or "http://localhost:8000",
            runner_mode=_env("AI_ACTIVITY_RUNNER_MODE", "synthetic_load") or "synthetic_load",
            agent_count=_int_env("AI_ACTIVITY_AGENT_COUNT", 4, minimum=1, maximum=MAX_AGENT_COUNT),
            signup_mode=_env("AI_ACTIVITY_SIGNUP_MODE", "reuse_or_create") or "reuse_or_create",
            output_dir=_env("AI_ACTIVITY_OUTPUT_DIR", DEFAULT_OUTPUT_DIR) or DEFAULT_OUTPUT_DIR,
            state_dir=_env("AI_ACTIVITY_STATE_DIR", DEFAULT_OUTPUT_DIR + "/state") or DEFAULT_OUTPUT_DIR + "/state",
            state_rotation=_bool_env("AI_ACTIVITY_STATE_ROTATION", True),
            run_id=run_id,
            llm_provider=_env("AI_ACTIVITY_LLM_PROVIDER", LOCAL_CODEX_BRIDGE) or LOCAL_CODEX_BRIDGE,
            llm_base_url=_env("AI_ACTIVITY_LLM_BASE_URL", "http://localhost:4000/v1") or "http://localhost:4000/v1",
            llm_api_key=_env("AI_ACTIVITY_LLM_API_KEY", "") or "",
            llm_model=_env("AI_ACTIVITY_LLM_MODEL", DEFAULT_LLM_MODEL) or DEFAULT_LLM_MODEL,
            llm_timeout_seconds=_float_env("AI_ACTIVITY_LLM_TIMEOUT_SECONDS", 45.0, minimum=0.001),
            llm_max_retries=_int_env("AI_ACTIVITY_LLM_MAX_RETRIES", 2, minimum=0),
            llm_temperature=_float_env("AI_ACTIVITY_LLM_TEMPERATURE", 0.8, minimum=0, maximum=2),
            llm_response_budget=_int_env("AI_ACTIVITY_LLM_RESPONSE_BUDGET", 500, minimum=1),
            max_steps=_int_env("AI_ACTIVITY_MAX_STEPS", 400, minimum=0),
            max_wall_seconds=_int_env("AI_ACTIVITY_MAX_WALL_SECONDS", 900, minimum=1),
            concurrency=_int_env("AI_ACTIVITY_CONCURRENCY", 4, minimum=1),
            random_seed=_int_env("AI_ACTIVITY_RANDOM_SEED", 0) if seed_raw not in {None, ""} else None,
            max_conversation_turns=_int_env("AI_ACTIVITY_MAX_CONVERSATION_TURNS", 4, minimum=1),
            replies_first=_bool_env("AI_ACTIVITY_REPLIES_FIRST", True),
            target_cooldown_steps=_int_env("AI_ACTIVITY_TARGET_COOLDOWN_STEPS", 6, minimum=0, maximum=1000),
            recent_action_window=_int_env("AI_ACTIVITY_RECENT_ACTION_WINDOW", 12, minimum=1, maximum=1000),
            max_reply_share=_float_env("AI_ACTIVITY_MAX_REPLY_SHARE", 0.45, minimum=0.0, maximum=1.0),
            spicy_style=_bool_env("AI_ACTIVITY_SPICY_STYLE", True),
            silliness_level=_float_env("AI_ACTIVITY_SILLINESS_LEVEL", 1.0, minimum=0.0, maximum=1.0),
            chaos_level=_float_env("AI_ACTIVITY_CHAOS_LEVEL", 0.35, minimum=0.0, maximum=1.0),
            style_pack=_env("AI_ACTIVITY_STYLE_PACK", "car_forum_gremlins") or "car_forum_gremlins",
            style_pack_pool=_csv_env("AI_ACTIVITY_STYLE_PACK_POOL", DEFAULT_STYLE_PACK_POOL),
            redact_artifacts=_bool_env("AI_ACTIVITY_REDACT_ARTIFACTS", True),
            live_llm_smoke=_bool_env("AI_ACTIVITY_LIVE_LLM_SMOKE", False),
        )
        config.validate()
        return config

    @property
    def state_target_fingerprint(self) -> str:
        return target_fingerprint(self.api_base_url)

    def validate(self) -> None:
        if self.runner_mode != "synthetic_load":
            raise ConfigError(f"unsupported runner mode: {self.runner_mode}")
        if self.signup_mode not in SIGNUP_MODES:
            raise ConfigError(f"unsupported signup mode: {self.signup_mode}")
        if self.llm_provider != LOCAL_CODEX_BRIDGE:
            raise ConfigError(f"unsupported LLM provider: {self.llm_provider}")
        _validate_http_url(self.api_base_url, label="API")
        _validate_http_url(self.llm_base_url, label="LLM bridge")
        if not self.llm_api_key:
            raise ConfigError("local_codex_bridge requires a bridge-local API key in AI_ACTIVITY_LLM_API_KEY")
        _validate_output_dir(self.output_dir)
        _validate_state_dir(self.state_dir)
        _validate_style_pack(self.style_pack)
        for pack in self.style_pack_pool or []:
            _validate_style_pack(pack, "AI_ACTIVITY_STYLE_PACK_POOL")
        if self.run_id:
            _safe_run_dir(self.output_dir, self.run_id)

    def ensure_output_dir(self) -> Path:
        self.validate()
        if not self.run_id:
            raise ConfigError("AI_ACTIVITY_RUN_ID must be set before writing artifacts")
        path = _safe_run_dir(self.output_dir, self.run_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def redacted_summary(self) -> dict[str, object]:
        return {
            "runner_mode": self.runner_mode,
            "agent_count": self.agent_count,
            "signup_mode": self.signup_mode,
            "state_target_fingerprint": self.state_target_fingerprint,
            "state_rotation": self.state_rotation,
            "llm_provider_mode": self.llm_provider,
            "llm_model": self.llm_model,
            "api_target_class": target_class(self.api_base_url),
            "llm_target_class": target_class(self.llm_base_url),
            "output_dir": _short_path(self.output_dir),
            "max_steps": self.max_steps,
            "concurrency": self.concurrency,
            "target_cooldown_steps": self.target_cooldown_steps,
            "recent_action_window": self.recent_action_window,
            "max_reply_share": self.max_reply_share,
            "spicy_style": self.spicy_style,
            "silliness_level": self.silliness_level,
            "chaos_level": self.chaos_level,
            "style_pack": self.style_pack,
            "style_pack_pool": list(self.style_pack_pool or []),
            "redact_artifacts": self.redact_artifacts,
        }
