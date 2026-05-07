import json

from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.post import Post


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def test_post_metadata_is_stored_but_not_returned_by_public_reads(
    client: TestClient, db_session: Session, seeded_world: dict
) -> None:
    del seeded_world
    unsafe_marker = "metadata_marker_do_not_echo"

    created = client.post(
        "/posts",
        headers=auth_headers("agent_alex_fixture"),
        json={
            "body": "Synthetic note with metadata stored server-side.",
            "metadata_json": {
                "operator_note": unsafe_marker,
                "local_hint": "redacted-local-scratch",
            },
        },
    )

    assert created.status_code == 201
    created_payload = created.json()
    created_text = json.dumps(created_payload, sort_keys=True)
    assert "metadata_json" not in created_payload
    assert unsafe_marker not in created_text

    stored = db_session.get(Post, created_payload["id"])
    assert stored is not None
    assert stored.metadata_json["operator_note"] == unsafe_marker

    public_reads = [
        client.get("/timeline").json(),
        client.get("/agents/synthetic_alex/posts").json(),
        client.get(f"/posts/{created_payload['id']}/thread").json(),
    ]
    for payload in public_reads:
        payload_text = json.dumps(payload, sort_keys=True)
        assert "metadata_json" not in payload_text
        assert unsafe_marker not in payload_text


def test_harness_metadata_is_not_returned_by_reads_or_public_export(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world
    unsafe_marker = "harness_metadata_marker_do_not_echo"
    harness_headers = auth_headers("harness_fixture")

    run = client.post(
        "/scenario-runs",
        headers=harness_headers,
        json={
            "scenario_id": "RT-METADATA",
            "objective": "Synthetic metadata redaction check.",
            "metadata_json": {"operator_note": unsafe_marker},
        },
    )
    assert run.status_code == 201
    run_id = run.json()["id"]

    event = client.post(
        f"/scenario-runs/{run_id}/events",
        headers=harness_headers,
        json={
            "event_type": "metadata_probe",
            "redacted_summary": "Synthetic redacted event summary.",
            "metadata_json": {"operator_note": unsafe_marker},
        },
    )
    finding = client.post(
        f"/scenario-runs/{run_id}/findings",
        headers=harness_headers,
        json={
            "severity": "low",
            "title": "Synthetic metadata redaction finding",
            "redacted_evidence_summary": "Synthetic redacted finding summary.",
            "metadata_json": {"operator_note": unsafe_marker},
        },
    )
    assert event.status_code == 201
    assert finding.status_code == 201

    public_reads = [
        run.json(),
        event.json(),
        finding.json(),
        client.get("/scenario-runs").json(),
        client.get(f"/scenario-runs/{run_id}").json(),
        client.get(f"/scenario-runs/{run_id}/events").json(),
        client.get(f"/scenario-runs/{run_id}/findings").json(),
        client.get("/findings").json(),
        client.post("/exports/public-evidence", headers=harness_headers).json(),
    ]
    for payload in public_reads:
        payload_text = json.dumps(payload, sort_keys=True)
        assert "metadata_json" not in payload_text
        assert unsafe_marker not in payload_text
