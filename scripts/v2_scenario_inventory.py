#!/usr/bin/env python3
"""Parse the public V2 scenario catalogs into a machine-readable inventory."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
NORMAL_DOC = REPO_ROOT / "docs" / "v2-normal-agent-scenarios.md"
RED_TEAM_DOC = REPO_ROOT / "docs" / "v2-red-team-scenarios.md"
EXPECTED_COUNTS = {"normal": 36, "red_team": 37}

HEADING_RE = re.compile(r"^## (?P<id>V2-(?:N|RT)-\d{3}) (?P<title>.+?)\s*$")
REGRESSION_RE = re.compile(r"^- \*\*Regression test name:\*\* `(?P<name>[^`]+)`\.?\s*$")


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    kind: str
    source_path: str
    source_line: int
    regression_test_name: str


class InventoryError(ValueError):
    """Raised when the scenario docs cannot be parsed as a complete inventory."""


def parse_scenario_doc(path: Path, kind: str) -> list[Scenario]:
    lines = path.read_text(encoding="utf-8").splitlines()
    scenarios: list[Scenario] = []

    for index, line in enumerate(lines):
        heading = HEADING_RE.match(line)
        if heading is None:
            continue

        next_heading = next(
            (
                offset
                for offset in range(index + 1, len(lines))
                if HEADING_RE.match(lines[offset])
            ),
            len(lines),
        )
        regression_name: str | None = None
        for scenario_line in lines[index + 1 : next_heading]:
            regression = REGRESSION_RE.match(scenario_line)
            if regression is not None:
                regression_name = regression.group("name")
                break
        if regression_name is None:
            raise InventoryError(f"{heading.group('id')} is missing a regression test name")

        scenarios.append(
            Scenario(
                id=heading.group("id"),
                title=heading.group("title").strip(),
                kind=kind,
                source_path=str(path.relative_to(REPO_ROOT)),
                source_line=index + 1,
                regression_test_name=regression_name,
            )
        )

    return scenarios


def load_inventory() -> list[Scenario]:
    scenarios = [
        *parse_scenario_doc(NORMAL_DOC, "normal"),
        *parse_scenario_doc(RED_TEAM_DOC, "red_team"),
    ]
    validate_inventory(scenarios)
    return scenarios


def validate_inventory(scenarios: Iterable[Scenario]) -> None:
    items = list(scenarios)
    ids = [scenario.id for scenario in items]
    duplicate_ids = sorted({scenario_id for scenario_id in ids if ids.count(scenario_id) > 1})
    if duplicate_ids:
        raise InventoryError(f"duplicate scenario IDs: {', '.join(duplicate_ids)}")

    for kind, expected in EXPECTED_COUNTS.items():
        actual = sum(1 for scenario in items if scenario.kind == kind)
        if actual != expected:
            raise InventoryError(f"expected {expected} {kind} scenarios, found {actual}")

    missing_names = [scenario.id for scenario in items if not scenario.regression_test_name]
    if missing_names:
        raise InventoryError(
            "scenarios missing regression test names: " + ", ".join(missing_names)
        )


def inventory_payload(scenarios: Iterable[Scenario]) -> dict[str, object]:
    items = list(scenarios)
    counts = {
        "normal": sum(1 for scenario in items if scenario.kind == "normal"),
        "red_team": sum(1 for scenario in items if scenario.kind == "red_team"),
        "total": len(items),
    }
    return {"counts": counts, "scenarios": [asdict(scenario) for scenario in items]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print inventory as JSON")
    args = parser.parse_args(argv)

    try:
        scenarios = load_inventory()
    except InventoryError as exc:
        print(f"scenario inventory error: {exc}", file=sys.stderr)
        return 1

    payload = inventory_payload(scenarios)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        counts = payload["counts"]
        assert isinstance(counts, dict)
        print(
            "V2 scenario inventory: "
            f"{counts['normal']} normal, {counts['red_team']} red-team, {counts['total']} total"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
