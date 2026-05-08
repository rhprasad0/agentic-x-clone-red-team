# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from scripts import ai_activity_runner as runner

REPO_ROOT = Path(__file__).resolve().parents[3]


class _FakeBridgeHandler(BaseHTTPRequestHandler):
    requests: list[dict[str, object]] = []

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        _FakeBridgeHandler.requests.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "body": json.loads(body.decode("utf-8")),
            }
        )
        payload = {
            "id": "chatcmpl_fake",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": '{"action":"silence"}'},
                    "finish_reason": "stop",
                }
            ],
        }
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


@pytest.fixture()
def fake_bridge() -> str:
    _FakeBridgeHandler.requests = []
    server = HTTPServer(("127.0.0.1", 0), _FakeBridgeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1"
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_local_codex_bridge_config_uses_bridge_key_and_requested_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_ACTIVITY_LLM_PROVIDER", "local_codex_bridge")
    monkeypatch.setenv("AI_ACTIVITY_LLM_BASE_URL", "http://localhost:4000/v1")
    monkeypatch.setenv("AI_ACTIVITY_LLM_API_KEY", "bridge_local_key_placeholder")
    monkeypatch.setenv("AI_ACTIVITY_LLM_MODEL", "gpt-5.4-mini")

    config = runner.AIActivityConfig.from_env()

    assert config.llm_provider == "local_codex_bridge"
    assert config.llm_base_url == "http://localhost:4000/v1"
    assert config.llm_api_key == "bridge_local_key_placeholder"
    assert config.llm_model == "gpt-5.4-mini"


def test_local_codex_bridge_requires_bridge_local_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_ACTIVITY_LLM_PROVIDER", "local_codex_bridge")
    monkeypatch.setenv("AI_ACTIVITY_LLM_BASE_URL", "http://localhost:4000/v1")
    monkeypatch.delenv("AI_ACTIVITY_LLM_API_KEY", raising=False)

    with pytest.raises(runner.ConfigError, match="bridge-local API key"):
        runner.AIActivityConfig.from_env()


def test_config_rejects_plaintext_non_loopback_llm_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_ACTIVITY_LLM_PROVIDER", "local_codex_bridge")
    monkeypatch.setenv("AI_ACTIVITY_LLM_BASE_URL", "http://llm-bridge.example.com/v1")
    monkeypatch.setenv("AI_ACTIVITY_LLM_API_KEY", "bridge_local_key_placeholder")

    with pytest.raises(runner.ConfigError, match="non-loopback LLM bridge URLs must use HTTPS"):
        runner.AIActivityConfig.from_env()


def test_llm_client_posts_openai_compatible_request_with_bridge_authorization(
    fake_bridge: str,
) -> None:
    config = runner.AIActivityConfig(
        llm_provider="local_codex_bridge",
        llm_base_url=fake_bridge,
        llm_api_key="bridge_local_key_placeholder",
        llm_model="gpt-5.4-mini",
        llm_timeout_seconds=5,
        llm_temperature=0.4,
        llm_response_budget=123,
    )

    content = runner.LocalCodexBridgeClient(config).complete(
        [{"role": "user", "content": "Pick one bounded action."}]
    )

    assert content == '{"action":"silence"}'
    assert _FakeBridgeHandler.requests == [
        {
            "path": "/v1/chat/completions",
            "authorization": "Bearer bridge_local_key_placeholder",
            "body": {
                "model": "gpt-5.4-mini",
                "messages": [{"role": "user", "content": "Pick one bounded action."}],
                "temperature": 0.4,
                "max_tokens": 123,
            },
        }
    ]


def test_llm_smoke_cli_skips_live_bridge_without_explicit_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AI_ACTIVITY_LIVE_LLM_SMOKE", raising=False)

    completed = subprocess.run(
        [sys.executable, "scripts/ai_activity_runner.py", "llm-smoke"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "skipped" in completed.stdout.lower()
    assert "AI_ACTIVITY_LIVE_LLM_SMOKE=1" in completed.stdout


def test_llm_smoke_cli_reports_bridge_errors_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("AI_ACTIVITY_LIVE_LLM_SMOKE", "1")
    monkeypatch.setenv("AI_ACTIVITY_LLM_PROVIDER", "local_codex_bridge")
    monkeypatch.setenv("AI_ACTIVITY_LLM_BASE_URL", "http://localhost:4000/v1")
    monkeypatch.setenv("AI_ACTIVITY_LLM_API_KEY", "bridge_local_key_placeholder")

    def fail_complete(self: runner.LocalCodexBridgeClient, messages: list[dict[str, str]]) -> str:
        raise runner.LLMBridgeError("LLM bridge returned HTTP 500")

    monkeypatch.setattr(runner.LocalCodexBridgeClient, "complete", fail_complete)

    assert runner.main(["llm-smoke"]) == 1
    captured = capsys.readouterr()

    assert "LLM bridge smoke failed: LLM bridge returned HTTP 500" in captured.err
    assert "Traceback" not in captured.err
    assert "/home/" not in captured.err
