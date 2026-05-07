import json
from pathlib import Path

from conftest import FIXTURE_CREDENTIAL_VALUES
from fastapi.testclient import TestClient


def auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {FIXTURE_CREDENTIAL_VALUES[label]}"}


def test_public_evidence_export_is_harness_only_redacted_and_synthetic(
    client: TestClient, seeded_world: dict
) -> None:
    del seeded_world

    assert client.post("/exports/public-evidence").status_code == 401
    agent_export = client.post(
        "/exports/public-evidence", headers=auth_headers("agent_alex_fixture")
    )
    assert agent_export.status_code == 403

    response = client.post("/exports/public-evidence", headers=auth_headers("harness_fixture"))
    assert response.status_code == 200
    payload = response.json()

    assert payload["export_type"] == "public_evidence"
    assert payload["scope"] == "validation_runs"
    assert payload["redaction_mode"] == "synthetic_redacted"
    assert payload["validation_runs"]
    exported_text = json.dumps(payload, sort_keys=True).lower()
    assert "synthetic" in exported_text
    assert "raw_trace" not in exported_text
    assert "metadata_json" not in exported_text
    assert "agent_alex_fixture_token_placeholder" not in exported_text
    assert "harness_fixture_token_placeholder" not in exported_text
    private_home_marker = "/" + "home" + "/" + "example"
    assert private_home_marker not in exported_text


def test_export_public_evidence_script_writes_scanner_safe_json(tmp_path: Path) -> None:
    output_path = tmp_path / "public-evidence.json"

    from scripts.export_public_evidence import build_public_evidence_file

    payload = build_public_evidence_file(output_path=output_path)

    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written == payload
    exported_text = json.dumps(written, sort_keys=True).lower()
    assert "synthetic" in exported_text
    assert "raw_trace" not in exported_text
    assert "metadata_json" not in exported_text
    assert "token_placeholder" not in exported_text
    private_home_marker = "/" + "home" + "/" + "example"
    assert private_home_marker not in exported_text
