# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
import io
import json

import pytest

from scripts.ai_activity_runner_lib.api_client import V2APIClient
from scripts.ai_activity_runner_lib.operational_logging import RunnerOperationalLogger, safe_event_payload

FORBIDDEN = [
    "runtime_token",
    "bridge_local_key_placeholder",
    "Bearer ",
    "Traceback",
    "http://127.0.0.1:4000/v1",
    "/tmp/private/repo",
    "raw prompt text",
]


@pytest.fixture
def io_string():
    return io.StringIO()


def parse_lines(stream):
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def assert_public_safe(text: str) -> None:
    for marker in FORBIDDEN:
        assert marker not in text


def test_safe_event_payload_drops_and_redacts_sensitive_values() -> None:
    payload = safe_event_payload(
        {
            "event_class": "runner_started",
            "run_id": "run_test",
            "llm_base_url": "http://127.0.0.1:4000/v1",
            "authorization": "Bearer runtime_token",
            "safe_message": "Traceback (most recent call last): raw prompt text",
            "artifact_dir": "/tmp/private/repo/.hermes/tmp/ai-activity-runner/run_test",
            "raw_prompt": "raw prompt text",
            "step": 3,
        }
    )

    rendered = json.dumps(payload, sort_keys=True)
    assert payload["event_class"] == "runner_started"
    assert payload["run_id"] == "run_test"
    assert payload["step"] == 3
    assert "raw_prompt" not in payload
    assert_public_safe(rendered)


def test_runner_operational_logger_writes_jsonl_to_stream(io_string):
    logger = RunnerOperationalLogger(run_id="run_test", stream=io_string)

    logger.emit("runner_started", agent_count=2, target_class="loopback", target_fingerprint="abcdef1234567890")
    logger.emit("llm_request_failed", safe_message="Bearer runtime_token Traceback (most recent call last): raw prompt text")

    events = parse_lines(io_string)
    assert [event["event_class"] for event in events] == ["runner_started", "llm_request_failed"]
    assert events[0]["component"] == "ai_activity_runner"
    assert events[0]["run_id"] == "run_test"
    assert events[0]["redaction_status"] == "redacted"
    assert_public_safe(io_string.getvalue())


def test_api_client_emits_attempt_retry_and_result_events(io_string):
    logger = RunnerOperationalLogger(run_id="run_test", stream=io_string)
    client = V2APIClient("http://localhost:9", timeout=0.01, per_agent_retry_budget=1, logger=logger)

    result = client.create_post("runtime_token", "Fictional safe post.", agent_handle="synthetic_a")

    assert not result.ok
    events = parse_lines(io_string)
    event_classes = [event["event_class"] for event in events]
    assert "api_request_attempt" in event_classes
    assert "api_retry" in event_classes
    assert "api_request_completed" in event_classes
    completion = [event for event in events if event["event_class"] == "api_request_completed"][-1]
    assert completion["route_class"] == "POST /posts"
    assert completion["outcome_class"] == "failure"
    assert completion["api_retry_count"] >= 1
    assert_public_safe(io_string.getvalue())


def test_api_client_route_refusal_logs_without_network(io_string):
    logger = RunnerOperationalLogger(run_id="run_test", stream=io_string)
    client = V2APIClient("http://localhost:9", logger=logger)

    result = client._request("GET", "/debug/private", route_class="GET /debug/private")

    assert result.issue_class == "api_route_forbidden"
    events = parse_lines(io_string)
    assert events[-1]["event_class"] == "api_request_blocked"
    assert events[-1]["issue_class"] == "api_route_forbidden"
    assert_public_safe(io_string.getvalue())
