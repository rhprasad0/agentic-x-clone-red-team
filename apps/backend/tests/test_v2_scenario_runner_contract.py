import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import scripts.run_v2_scenarios as runner
from scripts.run_v2_scenarios import BATCH_SCENARIOS, CHECKS, validate_runner_contract
from scripts.v2_scenario_inventory import load_inventory

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_v2_scenario_runner_maps_every_documented_scenario_to_checks() -> None:
    scenarios = load_inventory()
    validate_runner_contract(scenarios)

    mapped_ids = {scenario_id for ids in BATCH_SCENARIOS.values() for scenario_id in ids}
    assert mapped_ids == {scenario.id for scenario in scenarios}
    assert set(CHECKS) == set(BATCH_SCENARIOS)

    for batch, checks in CHECKS.items():
        assert checks, batch
        for check in checks:
            assert check.cwd.exists()
            assert check.argv


def test_v2_scenario_runner_rejects_duplicate_batch_mappings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    duplicate_mapping = {batch: tuple(ids) for batch, ids in BATCH_SCENARIOS.items()}
    duplicate_mapping["timelines"] = (*duplicate_mapping["timelines"], "V2-N-001")

    monkeypatch.setattr(runner, "BATCH_SCENARIOS", duplicate_mapping)

    with pytest.raises(ValueError, match="duplicate scenario mappings"):
        runner.validate_runner_contract(load_inventory())


def test_v2_scenario_runner_dry_run_json_is_public_safe(tmp_path: Path) -> None:
    output = tmp_path / "scenario-run.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_v2_scenarios.py",
            "--id",
            "V2-N-001",
            "--dry-run",
            "--json",
            str(output),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["dry_run"] is True
    assert payload["counts"] == {
        "dry_run": 1,
        "failed": 0,
        "not_run": 0,
        "passed": 0,
        "total": 1,
    }
    assert payload["results"][0]["id"] == "V2-N-001"
    assert payload["results"][0]["checks"][0]["status"] == "dry-run"
    combined = (completed.stdout + completed.stderr + output.read_text(encoding="utf-8")).lower()
    assert re.search(r"bearer\s+[a-z0-9._~+/=-]{16,}", combined) is None
    assert "token_placeholder" not in combined
