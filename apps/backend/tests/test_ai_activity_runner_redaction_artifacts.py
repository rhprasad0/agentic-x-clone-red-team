# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037
import json

from scripts.ai_activity_runner_lib.artifacts import ActivityEvent, ArtifactWriter, IssueEvent
from scripts.ai_activity_runner_lib.redaction import (
    redact_mapping,
    redact_text,
    validate_generated_social_text,
)


def test_redaction_removes_sensitive_classes():
    raw = " ".join(
        [
            "Authorization: Bearer ***",
            "token=" + "samplevalue",
            "person" + "@example.net",
            "/home/" + "sample/private",
            "http://127.0.0.1:4000/v1",
            "Traceback (most recent call last): boom",
        ]
    )
    r = redact_text(raw)
    assert r.redacted
    assert "Bearer abc" not in r.text
    assert "/home/" not in r.text
    assert "example.net" not in r.text
    assert "Traceback" not in r.text


def test_public_safe_examples_survive():
    text = "synthetic_alex posts about a fictional sedan; contact test@example.com; key=placeholder"
    assert "synthetic_alex" in redact_text(text).text


def test_redaction_removes_json_token_shapes():
    raw = '{"token":"sample-secret-value", "bearer_token":"another-secret", "access_token":"third-secret"}'
    redacted = redact_text(raw)
    assert redacted.redacted
    assert "sample-secret-value" not in redacted.text
    assert "another-secret" not in redacted.text
    assert "third-secret" not in redacted.text


def test_mapping_and_generated_social_text():
    assert redact_mapping({"bearer_token": "runtime_secret"})["bearer_token"] == "[REDACTED]"
    assert validate_generated_social_text("Fictional Civic math under budget.").ok
    assert not validate_generated_social_text("email me at " + "person" + "@example.net").ok


def test_artifact_writer_rejects_path_traversal_run_id(tmp_path):
    try:
        ArtifactWriter(tmp_path, "../escape")
        raise AssertionError("path traversal run_id was accepted")
    except ValueError as exc:
        assert "safe slug" in str(exc)


def test_artifact_shapes_are_redacted(tmp_path):
    w = ArtifactWriter(tmp_path, "run_test")
    w.record_issue(
        IssueEvent(
            run_id="run_test",
            severity="warning",
            issue_class="api_http_error",
            component="api",
            safe_message="Authorization: Bearer *** " + "token=" + "samplevalue",
        )
    )
    w.record_activity(
        ActivityEvent(
            run_id="run_test",
            agent_handle="syn_test",
            action="silence",
            route_class=None,
            target={},
            outcome="ok",
            summary="done",
        )
    )

    class A:
        def redacted_summary(self):
            return {"handle": "syn_test", "credential_ref": "runtime_secret"}

    w.write_agent_registry([A()])
    w.write_summary(
        config_summary={
            "runner_mode": "synthetic_load",
            "agent_count": 1,
            "signup_mode": "dynamic",
            "llm_provider_mode": "local_codex_bridge",
            "api_target_class": "loopback",
        },
        started_at="now",
    )
    for p in [w.issues_path, w.activity_path, w.registry_path, w.summary_path]:
        txt = p.read_text()
        assert "runtime_secret" not in txt
        assert "Bearer nope" not in txt
    assert json.loads(w.summary_path.read_text())["schema_version"] == "v2-ai-activity-runner.summary.v1"
