# V2 pre-infra local red-team report

Public-safe report for Kanban board `xclone-v2-redteam-preinfra`.

## Scope

This was a bounded, local-first pre-infra red-team pass for the synthetic V2 social substrate. It covered the FastAPI backend, Postgres-backed read/write paths, Vite/React observability UI, validation/export harness, local Compose readiness, and public documentation claims.

This is **not** a production security audit, a comprehensive platform assessment, a real-user test, or a claim of deployment hardening. The app remains a local-first synthetic social substrate with backend/API-scoped mutations and read-only browser observability.

Commit under test at audit start: `65fdd5b5968d`.

## Fix policy used

Ryan's execution policy for this pass:

- Fix only confirmed `critical`, `high`, or `medium` findings.
- Document `low`, `info`, false-positive, and deferred items without fixing them in this pass.
- Leave frontend, backend, and database services running for continued manual testing.

## Executive summary

| Severity | Confirmed | Fixed in this pass | Skipped / deferred |
| --- | ---: | ---: | ---: |
| Critical | 0 | 0 | 0 |
| High | 0 | 0 | 0 |
| Medium | 1 | 1 | 0 |
| Low | 0 | 0 | 2 document-only |
| Info | 0 | 0 | 5 document-only |

Result: no confirmed critical/high findings. One confirmed medium backend resource-bound issue was fixed and reviewed. Low/info items were intentionally skipped per policy and are listed below.

## Audit tracks

| Task | Surface | Result |
| --- | --- | --- |
| `RT0.2` | Baseline local stack and fixture reset smoke | Pass; services running |
| `RT1.1` | Frontend read-only / safe-rendering audit | No confirmed critical/high/medium findings |
| `RT1.2` | API authority, token, signup, mass-assignment audit | No confirmed critical/high/medium findings |
| `RT1.3` | Social mutation invariants and ownership audit | No confirmed route-invariant finding; test-session caveat documented |
| `RT1.4` | Cursor pagination, idempotency, resource-bound audit | One medium confirmed finding |
| `RT1.5` | Harness validation export and log redaction audit | No confirmed critical/high/medium findings |
| `RT1.6` | Bounded black-box V2 scenario runner | 73/73 aggregate checks passed |
| `RT1.7` | Docs claims, API inventory, deployment-boundary audit | No confirmed critical/high/medium findings |
| `RT1.8` | Local infra readiness and dependency hygiene audit | No confirmed critical/high/medium findings |

## Confirmed finding and fix

### RT2-FIX-001 — cursor-paginated read feeds paged after unbounded materialization

- Severity: medium
- Status: fixed
- Affected area: backend read-model feed assembly
- Primary file: `apps/backend/app/services/read_models.py`
- Regression file: `apps/backend/tests/test_v2_read_model_resource_bounds.py`

Public-safe finding summary: several cursor-paginated feed/thread/profile paths fetched and assembled all matching rows, then sorted/sliced in memory after the route-level page limit was already known. Response limits and signed cursor scope held, but large synthetic datasets could amplify database work, memory use, and DTO fanout beyond the requested page size.

Fix summary: read-model paths now apply signed cursor keyset predicates, ordering, and `limit + 1` SQL bounds before DTO expansion/materialization where feasible. The fix preserves response shape and cursor semantics, including merged post/repost feeds by bounding each source stream before merge.

Review status:

- `RT3.1` spec/security review: PASS.
- `RT3.2` code-quality review initially requested cleanup of unintended generated `apps/backend/uv.lock` churn.
- `RT3.3` re-review after removing the untracked lockfile: APPROVED.

## Skipped / deferred items

These were not fixed because they are low/info/document-only under the policy for this pass.

| ID | Severity | Status | Note |
| --- | --- | --- | --- |
| `RT2-DOC-001` | Low | Deferred | Local FastAPI docs routes are enabled in the local environment; acceptable for local observability, but disable docs before any non-local exposure or hardening claim. |
| `RT2-DOC-002` | Low/info | Deferred | While docs are enabled, FastAPI registers `/docs/oauth2-redirect`; this is a framework docs helper, not app API surface. |
| `RT2-DOC-003` | Info | Deferred | Public evidence contains a lowercase explanatory credential-safety word; scanner/custom marker checks passed and no credential value/header/hash was exposed. |
| `RT2-DOC-004` | Info | Deferred | Frontend audit found 0 npm vulnerabilities, with minor available updates for `@types/node` and `vite`; dependency pinning policy is later-scope. |
| `RT2-DOC-005` | Info | Deferred | Local image vulnerability scanners such as Docker Scout/Trivy were unavailable; install a repeatable scanner before making container vulnerability claims. |
| `RT2-DOC-006` | Info | Deferred | Concurrent local workers observed dirty workspace / non-canonical local image tags; treat as local hygiene context, not product vulnerability. |
| `RT2-DOC-007` | Info | Deferred | Browser hardening headers such as CSP are later-scope for non-local exposure; not a V2 local-first defect. |

## Black-box scenario signal

A separate public-safe black-box runner report was generated at `docs/v2-black-box-scenario-run-report.md`.

Aggregate result:

| Status | Count |
| --- | ---: |
| Passed | 73 |
| Failed | 0 |
| Error | 0 |
| Dry-run | 0 |
| Not run | 0 |

The runner report intentionally avoids scenario catalogs, walkthroughs, per-scenario predicates, raw traces, auth headers, bearer values, token values, token hashes, private paths, and PII.

## Validation commands and results

Commands run after the medium fix:

```bash
python3.12 -m compileall apps/backend/app apps/backend/tests/test_v2_read_model_resource_bounds.py
# passed

cd apps/backend && uv run --no-project --python python3.12 --with-editable . --with pytest --with 'httpx>=0.27,<1.0' --with 'psycopg[binary]>=3.2,<4.0' pytest tests/test_v2_read_model_resource_bounds.py tests/test_v2_timelines.py -q
# 7 passed in 1.21s

cd apps/backend && uv run --no-project --python python3.12 --with ruff ruff check app tests/test_v2_read_model_resource_bounds.py
# All checks passed

python3.12 scripts/public_safety_scan.py docs apps/backend/app apps/backend/tests scripts/run_v2_scenarios.py
# Public safety scan passed
```

Kanban board final state: 14 tasks done, 0 running, 0 blocked.

## Services left running

Per Ryan's instruction, services were left up for continued application testing.

| Service | Host URL / port | Status |
| --- | --- | --- |
| Frontend | `http://localhost:3000` | healthy; HTTP 200 from nginx and browser rendered public timeline with clean console |
| Backend | `http://localhost:8000/health` | healthy; `{"status":"ok"}` |
| Postgres | `localhost:5432` | healthy container |

`docker compose ps` showed backend, frontend, and Postgres containers healthy after the pass.

## Public-safety posture

This report uses synthetic scope language and avoids secrets, credentials, real user data, private local paths, raw traces, token values, token hashes, auth headers, and hidden scenario predicates. It should be safe to commit as a public pre-infra local red-team artifact.

## Go / no-go recommendation

Go for continued local application testing and pre-infra iteration. Do **not** represent this as production hardening or comprehensive security assessment. Before non-local exposure, close the documented deployment-boundary items: docs route disabling, browser hardening headers, container scanner selection, and dependency policy decisions.
