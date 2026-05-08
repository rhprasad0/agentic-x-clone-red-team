#!/usr/bin/env python3
"""Skeleton for the V2 AI activity runner.

This module intentionally implements only the configuration and LLM-bridge seam for the
future synthetic activity runner. It does not create agents or mutate the V2 backend yet.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

LOCAL_CODEX_BRIDGE = "local_codex_bridge"
DEFAULT_LLM_MODEL = "gpt-5.4-nano-2026-03-17"


class ConfigError(ValueError):
    """Raised when runner configuration is missing or unsafe."""


class LLMBridgeError(RuntimeError):
    """Raised when the configured compatible LLM bridge fails."""


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _is_loopback_host(hostname: str | None) -> bool:
    return hostname in {"localhost", "127.0.0.1", "::1"}


def _validate_loopback_or_https(url: str, *, label: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError(f"{label} must be an absolute HTTP(S) URL")
    if parsed.scheme == "http" and not _is_loopback_host(parsed.hostname):
        raise ConfigError(f"non-loopback {label} URLs must use HTTPS")


@dataclass(frozen=True)
class AIActivityConfig:
    """Public-safe config seam for the future AI activity runner."""

    llm_provider: str = LOCAL_CODEX_BRIDGE
    llm_base_url: str = "http://localhost:4000/v1"
    llm_api_key: str = ""
    llm_model: str = DEFAULT_LLM_MODEL
    llm_timeout_seconds: float = 45.0
    llm_max_retries: int = 2
    llm_temperature: float = 0.8
    llm_response_budget: int = 500

    @classmethod
    def from_env(cls) -> AIActivityConfig:
        config = cls(
            llm_provider=_env("AI_ACTIVITY_LLM_PROVIDER", LOCAL_CODEX_BRIDGE) or LOCAL_CODEX_BRIDGE,
            llm_base_url=_env("AI_ACTIVITY_LLM_BASE_URL", "http://localhost:4000/v1")
            or "http://localhost:4000/v1",
            llm_api_key=_env("AI_ACTIVITY_LLM_API_KEY", "") or "",
            llm_model=_env("AI_ACTIVITY_LLM_MODEL", DEFAULT_LLM_MODEL) or DEFAULT_LLM_MODEL,
            llm_timeout_seconds=float(_env("AI_ACTIVITY_LLM_TIMEOUT_SECONDS", "45") or "45"),
            llm_max_retries=int(_env("AI_ACTIVITY_LLM_MAX_RETRIES", "2") or "2"),
            llm_temperature=float(_env("AI_ACTIVITY_LLM_TEMPERATURE", "0.8") or "0.8"),
            llm_response_budget=int(_env("AI_ACTIVITY_LLM_RESPONSE_BUDGET", "500") or "500"),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.llm_provider != LOCAL_CODEX_BRIDGE:
            raise ConfigError(f"unsupported LLM provider: {self.llm_provider}")
        _validate_loopback_or_https(self.llm_base_url, label="LLM bridge")
        if not self.llm_api_key:
            raise ConfigError(
                "local_codex_bridge requires a bridge-local API key in AI_ACTIVITY_LLM_API_KEY"
            )
        if self.llm_timeout_seconds <= 0:
            raise ConfigError("AI_ACTIVITY_LLM_TIMEOUT_SECONDS must be positive")
        if self.llm_max_retries < 0:
            raise ConfigError("AI_ACTIVITY_LLM_MAX_RETRIES must be non-negative")
        if not (0 <= self.llm_temperature <= 2):
            raise ConfigError("AI_ACTIVITY_LLM_TEMPERATURE must be between 0 and 2")
        if self.llm_response_budget <= 0:
            raise ConfigError("AI_ACTIVITY_LLM_RESPONSE_BUDGET must be positive")


class LocalCodexBridgeClient:
    """Tiny OpenAI-compatible chat-completions client for local Codex bridge mode."""

    def __init__(self, config: AIActivityConfig) -> None:
        config.validate()
        self.config = config

    def complete(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.config.llm_model,
            "messages": messages,
            "temperature": self.config.llm_temperature,
            "max_tokens": self.config.llm_response_budget,
        }
        endpoint = self.config.llm_base_url.rstrip("/") + "/chat/completions"
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.llm_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.config.llm_timeout_seconds,
            ) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise LLMBridgeError(f"LLM bridge returned HTTP {exc.code}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise LLMBridgeError("LLM bridge request failed") from exc

        choices = response_payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMBridgeError("LLM bridge response did not include choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise LLMBridgeError("LLM bridge response did not include message content")
        return content


def _run_llm_smoke() -> int:
    if os.getenv("AI_ACTIVITY_LIVE_LLM_SMOKE") != "1":
        print("Skipped live LLM smoke; set AI_ACTIVITY_LIVE_LLM_SMOKE=1 to call the local bridge.")
        return 0

    try:
        config = AIActivityConfig.from_env()
        content = LocalCodexBridgeClient(config).complete(
            [{"role": "user", "content": "Reply with only OK."}]
        )
    except (ConfigError, LLMBridgeError) as exc:
        print(f"LLM bridge smoke failed: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "provider": config.llm_provider,
                "model": config.llm_model,
                "sample": content,
            }
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V2 AI activity runner skeleton")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("llm-smoke", help="Opt-in live smoke for the local Codex bridge")
    args = parser.parse_args(argv)

    if args.command == "llm-smoke":
        return _run_llm_smoke()
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
