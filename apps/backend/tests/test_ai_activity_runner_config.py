# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
import pytest
from scripts.ai_activity_runner_lib.config import AIActivityConfig, ConfigError


def base(monkeypatch):
    monkeypatch.setenv("AI_ACTIVITY_LLM_API_KEY", "bridge_local_key_placeholder")

def test_default_config_values(monkeypatch):
    base(monkeypatch)
    c=AIActivityConfig.from_env()
    assert c.agent_count == 20 and c.concurrency == 4 and c.max_steps == 400
    assert c.max_wall_seconds == 900 and c.max_conversation_turns == 4
    assert c.runner_mode == "synthetic_load" and c.signup_mode == "dynamic"
    assert c.redact_artifacts is True and c.replies_first is True
    assert c.llm_model == "gpt-5.4-mini"

def test_api_url_plaintext_safety(monkeypatch):
    base(monkeypatch); monkeypatch.setenv("AI_ACTIVITY_API_BASE_URL", "http://127.0.0.1:8001")
    assert AIActivityConfig.from_env().api_base_url.startswith("http://127.0.0.1")
    monkeypatch.setenv("AI_ACTIVITY_API_BASE_URL", "http://192.168.0.5:8001")
    with pytest.raises(ConfigError, match="non-loopback API URLs must use HTTPS"): AIActivityConfig.from_env()
    monkeypatch.setenv("AI_ACTIVITY_API_BASE_URL", "https://social.example.com")
    assert AIActivityConfig.from_env().api_base_url.startswith("https://")

def test_llm_requires_key_and_loopback_or_https(monkeypatch):
    monkeypatch.delenv("AI_ACTIVITY_LLM_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="bridge-local API key"): AIActivityConfig.from_env()
    base(monkeypatch); monkeypatch.setenv("AI_ACTIVITY_LLM_BASE_URL", "http://llm.example.com/v1")
    with pytest.raises(ConfigError, match="non-loopback LLM bridge URLs must use HTTPS"): AIActivityConfig.from_env()

def test_rejects_bad_numbers_modes_and_output(monkeypatch):
    base(monkeypatch); monkeypatch.setenv("AI_ACTIVITY_AGENT_COUNT", "zero")
    with pytest.raises(ConfigError, match="integer"): AIActivityConfig.from_env()
    monkeypatch.setenv("AI_ACTIVITY_AGENT_COUNT", "101")
    with pytest.raises(ConfigError, match="<= 100"): AIActivityConfig.from_env()
    monkeypatch.setenv("AI_ACTIVITY_AGENT_COUNT", "1"); monkeypatch.setenv("AI_ACTIVITY_RUNNER_MODE", "demo")
    with pytest.raises(ConfigError, match="unsupported runner mode"): AIActivityConfig.from_env()
    monkeypatch.setenv("AI_ACTIVITY_RUNNER_MODE", "synthetic_load"); monkeypatch.setenv("AI_ACTIVITY_OUTPUT_DIR", "public-output")
    with pytest.raises(ConfigError, match="ignored/private"): AIActivityConfig.from_env()


def test_rejects_path_traversal_run_id_and_bad_seed(monkeypatch):
    base(monkeypatch); monkeypatch.setenv("AI_ACTIVITY_RUN_ID", "../public-output")
    with pytest.raises(ConfigError, match="safe slug"): AIActivityConfig.from_env()
    monkeypatch.setenv("AI_ACTIVITY_RUN_ID", "run_safe_01"); monkeypatch.setenv("AI_ACTIVITY_RANDOM_SEED", "not-an-int")
    with pytest.raises(ConfigError, match="integer"): AIActivityConfig.from_env()

def test_redacted_summary_omits_secrets(monkeypatch):
    base(monkeypatch); c=AIActivityConfig.from_env(); s=c.redacted_summary()
    assert "bridge_local_key_placeholder" not in str(s)
    assert s["api_target_class"] == "loopback" and s["llm_provider_mode"] == "local_codex_bridge"
