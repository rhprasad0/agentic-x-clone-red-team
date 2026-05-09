import json
import logging

from fastapi.testclient import TestClient

from app.core.logging_config import (
    APP_LOGGER_NAME,
    JsonLogFormatter,
    safe_log_payload,
)
from app.main import create_app

FORBIDDEN_MARKERS = {
    "Authorization",
    "Bearer ",
    "runtime_secret_marker",
    "token_hash_marker",
    "raw_body_marker",
    "Traceback",
    "/" + "home" + "/" + "sample/private",
    "http://127.0.0.1:4000/v1",
}


def operational_events(caplog) -> list[dict[str, object]]:
    return [
        record.operational_event
        for record in caplog.records
        if hasattr(record, "operational_event")
    ]


def assert_no_forbidden_markers(caplog, *responses) -> None:
    text = caplog.text + json.dumps(operational_events(caplog), sort_keys=True)
    text += "\n".join(getattr(response, "text", "") for response in responses)
    for marker in FORBIDDEN_MARKERS:
        assert marker not in text


def test_json_formatter_serializes_safe_record_context() -> None:
    record = logging.LogRecord(
        APP_LOGGER_NAME,
        logging.INFO,
        __file__,
        10,
        "operational_event",
        (),
        None,
    )
    record.operational_event = safe_log_payload(
        {
            "event_class": "request_completed",
            "correlation_id": "abc123",
            "status_code": 200,
            "raw_body": "raw_body_marker",
            "authorization": "Bearer runtime_secret_marker",
            "artifact_path": "/" + "home" + "/" + "sample/private",
        }
    )

    formatted = json.loads(JsonLogFormatter().format(record))

    assert formatted["level"] == "INFO"
    assert formatted["logger"] == APP_LOGGER_NAME
    assert formatted["message"] == "operational_event"
    assert formatted["event"]["event_class"] == "request_completed"
    assert formatted["event"]["correlation_id"] == "abc123"
    rendered = json.dumps(formatted, sort_keys=True)
    for marker in FORBIDDEN_MARKERS:
        assert marker not in rendered


def test_create_app_logging_setup_is_idempotent() -> None:
    first = create_app()
    second = create_app()
    assert first.title == second.title
    logger = logging.getLogger(APP_LOGGER_NAME)
    handler_ids = [id(handler) for handler in logger.handlers]
    assert len(handler_ids) == len(set(handler_ids))


def test_health_request_logs_completion_with_response_request_id(caplog) -> None:
    caplog.set_level(logging.INFO, logger=APP_LOGGER_NAME)
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    events = operational_events(caplog)
    completion = [event for event in events if event.get("event_class") == "request_completed"][-1]
    assert completion["correlation_id"] == request_id
    assert completion["route_class"] == "health"
    assert completion["target_object_class"] == "health"
    assert completion["status_code"] == 200
    assert completion["outcome_class"] == "success"
    assert isinstance(completion["duration_ms"], int)
    assert completion["redaction_status"] == "redacted"
    assert_no_forbidden_markers(caplog, response)


def test_auth_failure_request_logs_redacted_completion(client: TestClient, caplog) -> None:
    caplog.set_level(logging.INFO, logger=APP_LOGGER_NAME)
    response = client.post(
        "/posts",
        headers={"Authorization": "Bearer runtime_secret_marker"},
        json={"text": "Synthetic unauthenticated logging check.", "raw_body": "raw_body_marker"},
    )

    assert response.status_code in {401, 422}
    events = operational_events(caplog)
    completion = [event for event in events if event.get("event_class") == "request_completed"][-1]
    assert completion["method"] == "POST"
    assert completion["route_class"] == "social_mutation"
    assert completion["target_object_class"] == "post"
    assert completion["outcome_class"] == "client_error"
    assert completion["status_code"] == response.status_code
    assert_no_forbidden_markers(caplog, response)


def test_domain_operations_emit_redacted_class_level_events(
    client: TestClient,
    seeded_world: dict,
    harness_headers: dict[str, str],
    caplog,
) -> None:
    del seeded_world
    caplog.set_level(logging.INFO, logger=APP_LOGGER_NAME)

    signup = client.post(
        "/agents/signup",
        json={
            "handle": "synthetic_logging_probe",
            "display_name": "Synthetic Logging Probe",
            "bio": "Fictional logging probe.",
            "persona_seed": "public safe synthetic probe",
        },
    )
    timeline = client.get("/timelines/public?limit=5&cursor=cursor_secret_marker")
    run = client.post(
        "/validation-runs",
        headers=harness_headers,
        json={"scenario_id": "RT-V2-LOGGING", "objective": "Synthetic logging check."},
    )
    export = client.post("/exports/public-evidence", headers=harness_headers)

    assert signup.status_code == 201
    assert timeline.status_code in {200, 400}
    assert run.status_code == 201
    assert export.status_code == 200
    event_classes = {event.get("event_class") for event in operational_events(caplog)}
    assert "agent_signup" in event_classes
    assert "timeline_read" in event_classes or timeline.status_code == 400
    assert "validation_write" in event_classes
    assert "export_write" in event_classes
    assert_no_forbidden_markers(caplog, signup, timeline, run, export)
