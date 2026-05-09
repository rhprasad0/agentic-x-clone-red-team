#!/usr/bin/env python3
# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
"""CLI for the V2 AI activity runner."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ai_activity_runner_lib.config import (
    DEFAULT_LLM_MODEL,
    LOCAL_CODEX_BRIDGE,
    AIActivityConfig,
    ConfigError,
)
from scripts.ai_activity_runner_lib.llm_client import LLMBridgeError, LocalCodexBridgeClient
from scripts.ai_activity_runner_lib.runner import SyntheticLoadRunner
from scripts.ai_activity_runner_lib.state_store import LocalAgentStateStore

__all__ = ["AIActivityConfig", "ConfigError", "LLMBridgeError", "LocalCodexBridgeClient", "DEFAULT_LLM_MODEL", "LOCAL_CODEX_BRIDGE", "main"]

def _run_llm_smoke() -> int:
    if os.getenv("AI_ACTIVITY_LIVE_LLM_SMOKE") != "1":
        print("Skipped live LLM smoke; set AI_ACTIVITY_LIVE_LLM_SMOKE=1 to call the local bridge.")
        return 0
    try:
        config = AIActivityConfig.from_env()
        content = LocalCodexBridgeClient(config).complete([{"role": "user", "content": "Reply with only OK."}])
    except (ConfigError, LLMBridgeError) as exc:
        print(f"LLM bridge smoke failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "ok", "provider": config.llm_provider, "model": config.llm_model, "sample": content}))
    return 0

def _run_validate_config() -> int:
    try:
        config = AIActivityConfig.from_env()
    except ConfigError as exc:
        print(f"Config validation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "ok", "config": config.redacted_summary()}, sort_keys=True))
    return 0

def _run_synthetic_load() -> int:
    try:
        config = AIActivityConfig.from_env()
        result = SyntheticLoadRunner(config).run()
    except ConfigError as exc:
        print(f"Runner config failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": result.status, "run_id": result.run_id, "steps": result.steps, "issues": result.issues, "actions": result.actions, "artifact_dir": ".hermes/tmp/ai-activity-runner/<run_id>"}, sort_keys=True))
    return 0 if result.status == "ok" else 1

def _run_clear_state(*, yes: bool) -> int:
    if not yes:
        print("Refusing to clear local runner state without --yes.", file=sys.stderr)
        return 2
    try:
        config = AIActivityConfig.from_env()
    except ConfigError as exc:
        print(f"Config validation failed: {exc}", file=sys.stderr)
        return 2
    store = LocalAgentStateStore(config.state_dir, target_fingerprint=config.state_target_fingerprint)
    removed = store.clear()
    print(json.dumps({"status": "ok", "target_class": config.redacted_summary()["api_target_class"], "target_fingerprint": config.state_target_fingerprint, **removed}, sort_keys=True))
    return 0

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V2 AI activity runner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate-config", help="Validate public-safe runner config without network calls")
    subparsers.add_parser("llm-smoke", help="Opt-in live smoke for the local Codex bridge")
    subparsers.add_parser("synthetic-load", help="Run bounded synthetic social activity")
    subparsers.add_parser("fake-llm-server", help="Run a fake OpenAI-compatible LLM endpoint")
    clear_state = subparsers.add_parser("clear-state", help="Delete ignored local reusable bot state for the configured API target")
    clear_state.add_argument("--yes", action="store_true", help="Confirm deletion of local ignored runner state")
    args = parser.parse_args(argv)
    if args.command == "validate-config": return _run_validate_config()
    if args.command == "llm-smoke": return _run_llm_smoke()
    if args.command == "synthetic-load": return _run_synthetic_load()
    if args.command == "clear-state": return _run_clear_state(yes=args.yes)
    if args.command == "fake-llm-server":
        from scripts.fake_openai_compatible_llm import main as fake_main
        return fake_main([])
    parser.error(f"unknown command: {args.command}")
    return 2

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
