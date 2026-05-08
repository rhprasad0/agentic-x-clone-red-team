import json
import re
import subprocess
import sys
from pathlib import Path

from scripts.v2_scenario_inventory import inventory_payload, load_inventory

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_v2_scenario_inventory_parses_expected_counts_and_regression_names() -> None:
    scenarios = load_inventory()
    payload = inventory_payload(scenarios)

    assert payload["counts"] == {"normal": 36, "red_team": 37, "total": 73}
    assert {scenario.id for scenario in scenarios} >= {"V2-N-001", "V2-N-036"}
    assert {scenario.id for scenario in scenarios} >= {"V2-RT-001", "V2-RT-037"}
    assert all(scenario.title for scenario in scenarios)
    assert all(scenario.regression_test_name.startswith("test_") for scenario in scenarios)
    assert len({scenario.regression_test_name for scenario in scenarios}) == 73


def test_v2_scenario_inventory_json_cli_has_public_safe_shape() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/v2_scenario_inventory.py", "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["counts"]["total"] == 73
    assert set(payload["scenarios"][0]) == {
        "id",
        "title",
        "kind",
        "source_path",
        "source_line",
        "regression_test_name",
    }
    serialized = completed.stdout.lower()
    assert re.search(r"bearer\s+[a-z0-9._~+/=-]{16,}", serialized) is None
    assert "token_placeholder" not in serialized
