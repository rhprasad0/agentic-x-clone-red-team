#!/usr/bin/env python3
"""Run public-safe executable checks for the documented V2 scenarios."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

try:
    from v2_scenario_inventory import Scenario, load_inventory
except ModuleNotFoundError:  # pragma: no cover - exercised when imported as a package
    from scripts.v2_scenario_inventory import Scenario, load_inventory

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "apps" / "backend"
FRONTEND_DIR = REPO_ROOT / "apps" / "frontend"

BATCH_SCENARIOS: dict[str, tuple[str, ...]] = {
    "signup": (
        "V2-N-001",
        "V2-N-002",
        "V2-N-003",
        "V2-N-004",
        "V2-N-005",
        "V2-N-006",
        "V2-N-007",
        "V2-N-008",
        "V2-RT-004",
        "V2-RT-005",
        "V2-RT-006",
        "V2-RT-014",
        "V2-RT-015",
        "V2-RT-029",
    ),
    "posts": (
        "V2-N-014",
        "V2-N-015",
        "V2-N-016",
        "V2-N-017",
        "V2-N-018",
        "V2-RT-001",
        "V2-RT-003",
        "V2-RT-016",
        "V2-RT-017",
        "V2-RT-019",
        "V2-RT-021",
        "V2-RT-032",
    ),
    "relationships": (
        "V2-N-019",
        "V2-N-020",
        "V2-N-021",
        "V2-N-022",
        "V2-N-023",
        "V2-N-024",
        "V2-N-025",
        "V2-N-026",
        "V2-RT-002",
        "V2-RT-018",
        "V2-RT-020",
        "V2-RT-025",
        "V2-RT-027",
    ),
    "timelines": (
        "V2-N-009",
        "V2-N-010",
        "V2-N-011",
        "V2-N-012",
        "V2-N-013",
        "V2-RT-010",
        "V2-RT-011",
        "V2-RT-012",
        "V2-RT-013",
    ),
    "harness": (
        "V2-N-027",
        "V2-N-028",
        "V2-N-029",
        "V2-N-030",
        "V2-N-031",
        "V2-N-032",
        "V2-RT-007",
        "V2-RT-008",
        "V2-RT-009",
        "V2-RT-026",
        "V2-RT-028",
        "V2-RT-030",
        "V2-RT-031",
    ),
    "frontend": (
        "V2-N-033",
        "V2-N-034",
        "V2-N-035",
        "V2-N-036",
        "V2-RT-022",
        "V2-RT-023",
        "V2-RT-024",
        "V2-RT-033",
        "V2-RT-034",
        "V2-RT-035",
        "V2-RT-036",
        "V2-RT-037",
    ),
}

BACKEND_UV_PYTEST = (
    "uv",
    "run",
    "--no-project",
    "--python",
    "python3.12",
    "--with-editable",
    ".",
    "--with",
    "pytest",
    "--with",
    "ruff",
    "pytest",
    "-q",
)


@dataclass(frozen=True)
class Check:
    name: str
    cwd: Path
    argv: tuple[str, ...]

    def public_command(self) -> str:
        return " ".join(self.argv)


@dataclass
class CheckResult:
    name: str
    command: str
    cwd: str
    status: str
    exit_code: int | None


@dataclass
class ScenarioResult:
    id: str
    title: str
    kind: str
    batch: str
    regression_test_name: str
    status: str
    checks: list[CheckResult]


CHECKS: dict[str, tuple[Check, ...]] = {
    "signup": (
        Check(
            "backend-signup-profile-public-read",
            BACKEND_DIR,
            (
                *BACKEND_UV_PYTEST,
                "tests/test_v2_signup_token_lifecycle.py",
                "tests/test_v2_profiles.py",
                "tests/test_v2_timelines.py",
                "tests/test_v2_cursor_pagination.py",
                "tests/test_v2_threads.py",
                "tests/test_v2_headers_cors_cache.py",
            ),
        ),
    ),
    "posts": (
        Check(
            "backend-post-reply-quote-authority",
            BACKEND_DIR,
            (
                *BACKEND_UV_PYTEST,
                "tests/test_v2_post_mutations.py",
                "tests/test_v2_object_authorization.py",
                "tests/test_v2_query_construction.py",
                "tests/test_v2_response_allowlists.py",
                "tests/test_v2_threads.py",
                "tests/test_v2_route_contracts.py",
                "tests/test_posts_write_authority.py",
            ),
        ),
    ),
    "relationships": (
        Check(
            "backend-relationships-idempotency-counters",
            BACKEND_DIR,
            (
                *BACKEND_UV_PYTEST,
                "tests/test_v2_social_relationships.py",
                "tests/test_v2_social_relationship_races.py",
                "tests/test_v2_social_counters.py",
                "tests/test_v2_idempotency.py",
                "tests/test_v2_idempotency_races.py",
                "tests/test_v2_post_idempotency_races.py",
            ),
        ),
    ),
    "timelines": (
        Check(
            "backend-timelines-cursors-pagination",
            BACKEND_DIR,
            (
                *BACKEND_UV_PYTEST,
                "tests/test_v2_timelines.py",
                "tests/test_v2_profiles.py",
                "tests/test_v2_cursor_pagination.py",
                "tests/test_v2_cursor_index_alignment.py",
                "tests/test_v2_route_contracts.py",
            ),
        ),
    ),
    "harness": (
        Check(
            "backend-harness-fixtures-evidence-redaction",
            BACKEND_DIR,
            (
                *BACKEND_UV_PYTEST,
                "tests/test_fixtures_seed_reset.py",
                "tests/test_v2_validation_routes.py",
                "tests/test_v2_export_allowlists.py",
                "tests/test_public_evidence_exports.py",
                "tests/test_public_metadata_redaction.py",
                "tests/test_v2_security_logging.py",
                "tests/test_v2_docs_artifacts.py",
            ),
        ),
        Check(
            "public-evidence-export-script",
            REPO_ROOT,
            ("python3", "scripts/export_public_evidence.py"),
        ),
        Check(
            "public-safety-scan",
            REPO_ROOT,
            ("python3", "scripts/public_safety_scan.py", "."),
        ),
    ),
    "frontend": (
        Check(
            "frontend-vitest-read-only-ui",
            FRONTEND_DIR,
            ("npm", "test", "--", "--run"),
        ),
        Check("frontend-eslint", FRONTEND_DIR, ("npm", "run", "lint")),
        Check("frontend-build", FRONTEND_DIR, ("npm", "run", "build")),
        Check(
            "backend-browser-boundary-headers",
            BACKEND_DIR,
            (
                *BACKEND_UV_PYTEST,
                "tests/test_v2_headers_cors_cache.py",
                "tests/test_v2_external_fetch_boundary.py",
            ),
        ),
    ),
}

OUTPUT_REDACTION_PATTERNS = (
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"agent_[a-z]+_fixture_token_placeholder"),
    re.compile(r"harness_fixture_token_placeholder"),
    re.compile(r'("token"\s*:\s*")[^"]+(")'),
)


def batch_for_scenario(scenario_id: str) -> str:
    matches = [batch for batch, ids in BATCH_SCENARIOS.items() if scenario_id in ids]
    if not matches:
        raise KeyError(f"no batch maps scenario {scenario_id}")
    return matches[0]


def validate_runner_contract(scenarios: Iterable[Scenario]) -> None:
    inventory_ids = {scenario.id for scenario in scenarios}
    mapped_ids = {scenario_id for ids in BATCH_SCENARIOS.values() for scenario_id in ids}
    mapped_sequence = [scenario_id for ids in BATCH_SCENARIOS.values() for scenario_id in ids]
    duplicate_mappings = sorted(
        {scenario_id for scenario_id in mapped_sequence if mapped_sequence.count(scenario_id) > 1}
    )
    if duplicate_mappings:
        raise ValueError(f"duplicate scenario mappings: {duplicate_mappings}")

    missing = sorted(inventory_ids - mapped_ids)
    extra = sorted(mapped_ids - inventory_ids)
    if missing or extra:
        raise ValueError(f"scenario mapping mismatch: missing={missing}, extra={extra}")

    missing_checks = sorted(set(BATCH_SCENARIOS) - set(CHECKS))
    extra_checks = sorted(set(CHECKS) - set(BATCH_SCENARIOS))
    if missing_checks or extra_checks:
        raise ValueError(f"batch check mismatch: missing={missing_checks}, extra={extra_checks}")


def redact_output(text: str) -> str:
    redacted = text
    for pattern in OUTPUT_REDACTION_PATTERNS:
        if pattern.pattern.startswith('("token"'):
            redacted = pattern.sub(r'\1[redacted]\2', redacted)
        else:
            redacted = pattern.sub("[redacted-token]", redacted)
    return redacted


def check_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("UV_PROJECT_ENVIRONMENT", "/tmp/agentic-x-v2-scenario-backend-uv")
    env.setdefault("UV_NO_PROGRESS", "1")
    env.setdefault("CI", "1")
    return env


def run_check(check: Check, *, dry_run: bool) -> CheckResult:
    public_cwd = str(check.cwd.relative_to(REPO_ROOT))
    if dry_run:
        print(f"DRY-RUN {check.name}: ({public_cwd}) {check.public_command()}")
        return CheckResult(check.name, check.public_command(), public_cwd, "dry-run", None)

    print(f"RUN {check.name}: ({public_cwd}) {check.public_command()}")
    completed = subprocess.run(
        check.argv,
        cwd=check.cwd,
        env=check_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = redact_output(completed.stdout)
    if output.strip():
        print(output, end="" if output.endswith("\n") else "\n")
    status = "passed" if completed.returncode == 0 else "failed"
    return CheckResult(
        check.name,
        check.public_command(),
        public_cwd,
        status,
        completed.returncode,
    )


def selected_scenarios(
    scenarios: list[Scenario], *, scenario_id: str | None, batch: str | None, all_scenarios: bool
) -> list[Scenario]:
    if scenario_id is not None:
        selected = [scenario for scenario in scenarios if scenario.id == scenario_id]
        if not selected:
            raise ValueError(f"unknown scenario ID: {scenario_id}")
        return selected
    if batch is not None:
        if batch not in BATCH_SCENARIOS:
            raise ValueError(f"unknown batch: {batch}")
        ids = set(BATCH_SCENARIOS[batch])
        return [scenario for scenario in scenarios if scenario.id in ids]
    if all_scenarios:
        return scenarios
    return []


def run_scenarios(
    scenarios: list[Scenario],
    *,
    dry_run: bool,
    stop_on_fail: bool,
) -> list[ScenarioResult]:
    batches = []
    for scenario in scenarios:
        batch = batch_for_scenario(scenario.id)
        if batch not in batches:
            batches.append(batch)

    check_results_by_batch: dict[str, list[CheckResult]] = {}
    for batch in batches:
        batch_results: list[CheckResult] = []
        for check in CHECKS[batch]:
            result = run_check(check, dry_run=dry_run)
            batch_results.append(result)
            if stop_on_fail and result.status == "failed":
                break
        check_results_by_batch[batch] = batch_results
        if stop_on_fail and any(result.status == "failed" for result in batch_results):
            break

    scenario_results: list[ScenarioResult] = []
    for scenario in scenarios:
        batch = batch_for_scenario(scenario.id)
        checks = check_results_by_batch.get(batch, [])
        if not checks:
            status = "not-run"
        elif any(check.status == "failed" for check in checks):
            status = "failed"
        elif all(check.status == "dry-run" for check in checks):
            status = "dry-run"
        else:
            status = "passed"
        scenario_results.append(
            ScenarioResult(
                id=scenario.id,
                title=scenario.title,
                kind=scenario.kind,
                batch=batch,
                regression_test_name=scenario.regression_test_name,
                status=status,
                checks=checks,
            )
        )
    return scenario_results


def write_json(path: Path, results: list[ScenarioResult], *, dry_run: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "dry_run": dry_run,
        "counts": {
            "passed": sum(1 for result in results if result.status == "passed"),
            "failed": sum(1 for result in results if result.status == "failed"),
            "dry_run": sum(1 for result in results if result.status == "dry-run"),
            "not_run": sum(1 for result in results if result.status == "not-run"),
            "total": len(results),
        },
        "results": [asdict(result) for result in results],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def print_list(scenarios: list[Scenario]) -> None:
    for scenario in scenarios:
        print(
            f"{scenario.id}\t{batch_for_scenario(scenario.id)}\t"
            f"{scenario.regression_test_name}\t{scenario.title}"
        )


def print_summary(results: list[ScenarioResult]) -> None:
    counts = {
        "passed": sum(1 for result in results if result.status == "passed"),
        "failed": sum(1 for result in results if result.status == "failed"),
        "dry-run": sum(1 for result in results if result.status == "dry-run"),
        "not-run": sum(1 for result in results if result.status == "not-run"),
    }
    print(
        "V2 scenario run summary: "
        f"{counts['passed']} passed, {counts['failed']} failed, "
        f"{counts['dry-run']} dry-run, {counts['not-run']} not-run"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--id", dest="scenario_id", help="run one scenario ID")
    selection.add_argument("--batch", choices=sorted(BATCH_SCENARIOS), help="run one scenario batch")
    selection.add_argument("--all", action="store_true", help="run all scenario batches")
    parser.add_argument("--list", action="store_true", help="list known scenarios and exit")
    parser.add_argument("--dry-run", action="store_true", help="print checks without executing them")
    parser.add_argument("--stop-on-fail", action="store_true", help="stop after the first failing check")
    parser.add_argument("--json", type=Path, help="write a public-safe JSON result summary")
    args = parser.parse_args(argv)

    try:
        scenarios = load_inventory()
        validate_runner_contract(scenarios)
        if args.list:
            print_list(scenarios)
            return 0
        selected = selected_scenarios(
            scenarios,
            scenario_id=args.scenario_id,
            batch=args.batch,
            all_scenarios=args.all,
        )
    except (KeyError, ValueError) as exc:
        print(f"scenario runner error: {exc}", file=sys.stderr)
        return 2

    if not selected:
        parser.error("choose --list, --id, --batch, or --all")

    if not args.dry_run and shutil.which("uv") is None:
        print("scenario runner requires uv for backend test execution", file=sys.stderr)
        return 2

    results = run_scenarios(selected, dry_run=args.dry_run, stop_on_fail=args.stop_on_fail)
    if args.json is not None:
        write_json(args.json, results, dry_run=args.dry_run)
    print_summary(results)
    return 1 if any(result.status == "failed" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
