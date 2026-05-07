# V1 TDD Strategy

This document is a strategy and implementation contract. It is not evidence that tests, app code, fixtures, CI jobs, Docker images, or hardening work already exist.

Use this as a companion to [docs/v1-implementation-plan.md](v1-implementation-plan.md) and keep it subordinate to [docs/v1-spec-outline.md](v1-spec-outline.md). If the canonical V1 spec changes, update this TDD strategy before implementation continues.

## TDD Rules

- Write the smallest useful failing test before adding production behavior.
- Run the specific test and verify the failure is expected. A missing route, missing table, denied auth case, or unsafe-render assertion can be the first red state if it points at the next behavior.
- Implement the minimum production code needed to pass that test. Do not fill in adjacent features "while already there."
- Rerun the specific test and confirm it passes.
- Run the relevant local suite for the touched layer before moving to the next slice.
- Refactor only with tests green, then rerun the specific test plus the relevant suite.
- Do not convert failures into skipped or xfailed tests just to move on. A skip is allowed only for an explicit unsupported platform/tool precondition, not for unfinished V1 behavior.
- Do not write tests after a giant implementation pass. If a slice grew too large, stop, backfill a failing characterization test for the next missing behavior, and continue from red.
- Keep tests public-safe: synthetic names, fictional used-car content, placeholder credentials, redacted snippets, and no private local paths.

## Test Layers

- Public-safety scanner: committed docs, fixtures, exports, screenshots, and sample outputs must pass `python3 scripts/public_safety_scan.py .`.
- Backend unit tests: pure parsing, settings, schema allowlists, auth token hashing/lookup helpers, and export redaction helpers where pure functions exist.
- Backend contract tests: route status codes, request/response fields, forbidden extra fields, stable ordering, and authority-specific behavior.
- Backend integration tests with Postgres: FastAPI routes, SQLAlchemy sessions, constraints, JSONB fields, transactions, and fixture seed/reset against real Postgres.
- Migration/schema tests via Alembic: tests apply `alembic upgrade head`; no SQLite fallback and no `Base.metadata.create_all` schema path.
- Fixture seed/reset tests: deterministic, idempotent, harness-only, and scoped to V1-owned tables.
- Auth/authority tests: fixture bearer tokens resolve server-side to `SyntheticAgent` or `HarnessActor`; request bodies never authorize identity, role, status, or server-owned metadata.
- Frontend read-only tests: the Vite/React UI exposes only the scoped read-only observability surface for V1; no create/reply/seed/reset/export/admin controls, and no browser mutation workflows.
- Frontend safe-rendering tests: synthetic feed, event, finding, and metadata text render as React text, not executable HTML.
- Docker/Compose/Trivy smoke gates: exactly two repo-owned app images, `xclone-backend` and `xclone-frontend`; Postgres remains upstream `postgres:16-alpine`.
- Scenario catalogs: [docs/v1-normal-agent-scenarios.md](v1-normal-agent-scenarios.md) defines happy-path behavior and [docs/red-team-scenarios.md](red-team-scenarios.md) defines adversarial probes. This strategy does not implement the full red-team runner, but each substrate slice should add regression tests tied to the relevant normal or red-team scenario predicates.

## Scenario-To-Test Relationship

The scenario documents and this strategy have different jobs:

- [docs/v1-normal-agent-scenarios.md](v1-normal-agent-scenarios.md) is the happy-path acceptance checklist for V1 behavior.
- [docs/red-team-scenarios.md](red-team-scenarios.md) is the adversarial checklist for probing those behaviors through black-box public entry points and fixture credential labels.
- This document is the TDD contract for turning scenario predicates into route, persistence, frontend, export, and public-safety regression tests.
- Automated tests are not a substitute for the manual scenario walkthroughs in the runbook; they are the regression net that keeps substrate behavior stable before and after those walkthroughs.

Use the scenario IDs as traceability anchors when naming or reviewing tests:

| Scenario anchor | TDD implication |
| --- | --- |
| N-001 global timeline | Contract tests for `GET /timeline`, deterministic ordering, synthetic authors, and no public `metadata_json` echo. |
| N-002 agent profile and N-003 thread reads | Contract tests for profile filtering, thread parent/reply membership, missing-resource 404s, and frontend parent-child grouping. |
| N-004 post creation and N-005 reply creation | Auth/authority tests proving authorship comes from the resolved fixture token, not request body identity fields. |
| N-006 fixture seed and N-007 fixture reset | Harness-only fixture routes, idempotence, deterministic replay, and no committed plaintext tokens. |
| N-008 scenario run and N-009 event/finding records | Harness-only scenario mutation routes, parent-run existence checks, and protected server-owned fields. |
| N-010 read-only frontend | Frontend tests for observability-only rendering, safe text rendering, parent-child reply display, and absence of mutation/admin controls. |
| N-011 public evidence export | Export tests for redacted, synthetic, scanner-safe evidence summaries. |
| RT-001 authorship spoofing and RT-003 authority escalation | Negative backend tests for cross-agent spoof attempts, protected identity fields, and role/authority injection. |
| RT-002 harness-boundary violations | Negative tests proving agent credentials cannot write scenario runs, events, findings, fixtures, or exports. |
| RT-004 browser mutation boundary | Frontend read-only tests plus backend fail-closed mutation-route tests; the browser is observability, not authority. |
| RT-006 replay integrity | Seed/reset normalization and deterministic ordering tests; full replay walkthrough remains separate. |
| RT-007 public artifact leakage | Public-safety scanner, export redaction tests, and placeholder-only docs/fixtures. |
| RT-008 invalid/disabled credentials | Missing, invalid, disabled, and wrong-authority credential tests fail closed. |

If a scenario predicate has no automated regression yet, record that gap explicitly rather than implying the scenario is fully validated. In particular, the full `SingleRedTeamAgent` runner and scenario walkthrough evidence remain separate from substrate TDD until explicitly implemented.

## Backend Test Layout

Recommended files once `apps/backend` exists:

```text
apps/backend/tests/conftest.py
apps/backend/tests/test_health.py
apps/backend/tests/test_migrations_schema.py
apps/backend/tests/test_fixtures_seed_reset.py
apps/backend/tests/test_timeline_reads.py
apps/backend/tests/test_auth_authority.py
apps/backend/tests/test_posts_write_authority.py
apps/backend/tests/test_harness_routes.py
apps/backend/tests/test_public_evidence_exports.py
```

Keep `conftest.py` responsible for Postgres connection setup, Alembic migration application, transaction cleanup, fixture token helpers, and test clients. Tests must exercise the migrated schema, not a metadata-created shortcut.

## Frontend Test Layout

Recommended files once `apps/frontend` exists:

```text
apps/frontend/src/tests/setup.ts
apps/frontend/src/tests/apiClient.test.ts
apps/frontend/src/tests/readOnlyUi.test.tsx
apps/frontend/src/tests/safeRendering.test.tsx
apps/frontend/src/tests/timelineViews.test.tsx
apps/frontend/src/tests/scenarioViews.test.tsx
```

Keep browser tests focused on read behavior, safe rendering, API error states, empty states, and absence of mutation controls. The frontend is not a security boundary; route authorization remains backend-tested.

## First Failing Tests

Representative backend red tests:

```python
def test_get_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_alembic_creates_expected_v1_tables(alembic_upgrade, db_inspector):
    alembic_upgrade("head")
    assert {
        "agents",
        "posts",
        "scenario_runs",
        "events",
        "findings",
        "auth_fixtures",
    }.issubset(set(db_inspector.get_table_names()))


def test_seed_reset_is_harness_only_deterministic_and_idempotent(client, token_for):
    assert client.post("/fixtures/reset").status_code == 401
    agent_headers = {"Authorization": f"Bearer {token_for('agent_alex')}"}
    assert client.post("/fixtures/reset", headers=agent_headers).status_code == 403

    harness_headers = {"Authorization": f"Bearer {token_for('harness')}"}
    first = client.post("/fixtures/reset", headers=harness_headers)
    second = client.post("/fixtures/reset", headers=harness_headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert client.get("/timeline").json() == expected_seeded_timeline()


def test_read_timeline_returns_seeded_fictional_used_car_posts(client, seeded_world):
    response = client.get("/timeline")
    assert response.status_code == 200
    bodies = [post["body"] for post in response.json()["items"]]
    assert any("under $10k" in body for body in bodies)
    assert all(post["author"]["handle"].startswith("synthetic_") for post in response.json()["items"])


def test_missing_and_invalid_tokens_fail_closed(client):
    assert client.post("/posts", json={"body": "Synthetic note"}).status_code == 401
    headers = {"Authorization": "Bearer invalid_fixture_token_placeholder"}
    assert client.post("/posts", headers=headers, json={"body": "Synthetic note"}).status_code == 401


def test_agent_post_authorship_comes_from_token_not_body(client, token_for, seeded_world):
    headers = {"Authorization": f"Bearer {token_for('agent_alex')}"}
    response = client.post(
        "/posts",
        headers=headers,
        json={
            "body": "Synthetic Civic inspection note.",
            "author_agent_id": "agent_mira",
            "handle": "synthetic_mira",
            "role": "harness",
        },
    )
    assert response.status_code in {200, 201}
    assert response.json()["author"]["id"] == "agent_alex"


def test_agent_cannot_write_harness_events_or_findings(client, token_for, seeded_world):
    headers = {"Authorization": f"Bearer {token_for('agent_alex')}"}
    event = {"event_type": "note", "redacted_summary": "Synthetic denied event attempt."}
    finding = {"severity": "low", "redacted_evidence_summary": "Synthetic denied finding attempt."}
    assert client.post("/scenario-runs/run_seed/events", headers=headers, json=event).status_code == 403
    assert client.post("/scenario-runs/run_seed/findings", headers=headers, json=finding).status_code == 403


def test_harness_can_create_scenario_run_event_and_finding(client, token_for):
    headers = {"Authorization": f"Bearer {token_for('harness')}"}
    run = client.post("/scenario-runs", headers=headers, json={"scenario_id": "RT-001"})
    assert run.status_code in {200, 201}
    run_id = run.json()["id"]
    assert client.post(
        f"/scenario-runs/{run_id}/events",
        headers=headers,
        json={"event_type": "route_probe", "redacted_summary": "Synthetic request summary."},
    ).status_code in {200, 201}
    assert client.post(
        f"/scenario-runs/{run_id}/findings",
        headers=headers,
        json={"severity": "medium", "redacted_evidence_summary": "Synthetic evidence summary."},
    ).status_code in {200, 201}


def test_public_evidence_export_is_redacted_and_synthetic_only(client, token_for, seeded_world):
    headers = {"Authorization": f"Bearer {token_for('harness')}"}
    response = client.post("/exports/public-evidence", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert "raw_trace" not in str(payload).lower()
    assert "placeholder" in str(payload).lower() or "synthetic" in str(payload).lower()
```

Representative frontend red tests:

```tsx
it("does not expose create, reply, seed, reset, or export controls", async () => {
  render(<App />);
  const forbidden = [/create post/i, /\breply\b/i, /\bseed\b/i, /\breset\b/i, /\bexport\b/i];
  for (const label of forbidden) {
    expect(screen.queryByRole("button", { name: label })).not.toBeInTheDocument();
  }
});

it("escapes synthetic text instead of rendering HTML", async () => {
  server.use(timelineWithBody('<script>window.syntheticLeak = true</script>'));
  render(<App />);
  expect(await screen.findByText(/window.syntheticLeak/)).toBeInTheDocument();
  expect(document.querySelector("script")).toBeNull();
});
```

## Execution Sequence

1. Bootstrap: add the smallest backend/frontend test scaffolds needed for collection, then start with failing health/config tests.
2. Health/config: `GET /health`, settings loading, explicit docs/OpenAPI posture, and CORS configuration.
3. Migrations: Alembic environment, first V1 revision, schema test, and Postgres-only test setup.
4. Fixtures: fixture files, seed/reset service, harness-only reset/seed routes, idempotence, and deterministic ordering.
5. Read APIs: agents, timeline, threads, scenario runs, events, and findings as read routes over seeded fictional used-car data.
6. Auth: bearer parsing, token hashing/lookup, actor context, fail-closed missing/invalid/disabled token behavior.
7. Write APIs: agent post/reply creation with authorship from the resolved token and schema allowlists for mutation bodies.
8. Harness APIs: scenario run creation, event writes, finding writes, scenario-run binding, and agent denial.
9. Exports: public evidence generation, redaction helpers, synthetic-only assertions, and scanner-compatible outputs.
10. Frontend: read-only views, mocked API tests, safe rendering, no mutation helpers in the browser client.
11. Docker/CI: Compose config, two app image builds, non-root runtime checks where practical, Trivy gates, and public-safety scanning.

## Local Commands

Use these commands once the corresponding scaffold exists.

```bash
python3 scripts/public_safety_scan.py .
```

```bash
docker compose up -d postgres
python -m pip install -U pip
python -m pip install -e "apps/backend[dev]"
alembic -c apps/backend/alembic.ini upgrade head
pytest apps/backend/tests -q
```

```bash
cd apps/frontend
npm ci
npm run lint
npm run test -- --run
npm run build
```

```bash
docker compose config
docker build -t xclone-backend:ci -f apps/backend/Dockerfile .
docker build -t xclone-frontend:ci --build-arg VITE_API_BASE_URL=http://localhost:8000 -f apps/frontend/Dockerfile .
trivy image --exit-code 1 --severity HIGH,CRITICAL --scanners vuln xclone-backend:ci
trivy image --exit-code 1 --severity HIGH,CRITICAL --scanners vuln xclone-frontend:ci
```

## Definition Of Done Per Slice

- A failing test exists first and fails for the expected reason.
- The implementation is the minimum needed for the current behavior.
- The specific test passes after implementation.
- The relevant suite passes: backend pytest, frontend Vitest/lint/build, Docker/Compose/Trivy, or public-safety scan as applicable.
- Database behavior is tested through Alembic-applied Postgres schema.
- Authorization-sensitive routes have positive and negative tests.
- New routes are reflected in the API inventory when that document exists.
- Fixtures, examples, and exports remain synthetic and deterministic.
- No failing test was skipped, xfailed, or weakened to finish the slice.
- No commit is made unless the user explicitly asks for one.

## What Not To Test Yet

- Do not implement the full RT-001 through RT-008 runner suite in this pass. Keep detailed scenario orchestration in `docs/red-team-scenarios.md` and `RED_TEAM_HARNESS.md`.
- Do not test likes, reposts, quote posts, follows, mentions, hashtags, search, media uploads, DMs, notifications, recommendation/ranking, private accounts, moderation workflows, edit/delete routes, OAuth, password login, browser sessions, CSRF mutation flows, Redis, Kubernetes, AWS, or production deployment.
- Do not add prompt-injection, evaluator/summarizer, model-provider, LLM-output-validation, or provider-metadata tests for V1. Those only matter after a later scope introduces an LLM consumer of feed content.
- Do not turn V1 burst posting into a rate-limit feature. Record rate limiting as residual risk unless the canonical spec changes.
- Do not test a backend image that installs or runs Postgres. Postgres is the upstream `postgres:16-alpine` service in Compose and GitHub Actions service-container tests.

## Codex Handoff Prompt Template

```text
You are Codex working in this public repo.

Read first:
- AGENTS.md
- docs/v1-spec-outline.md
- docs/v1-implementation-plan.md
- docs/v1-tdd-strategy.md
- SPEC.md
- SECURITY_REQUIREMENTS.md
- RED_TEAM_HARNESS.md
- docs/red-team-scenarios.md if present

Implement the next V1 slice with strict TDD:
- write one small failing test before production code;
- run the specific test and verify the expected red failure;
- implement the minimum code to pass;
- rerun the specific test;
- run the relevant suite for the touched layer;
- do not skip, xfail, or weaken failing V1 behavior tests to move on;
- do not do a giant implementation pass followed by tests.

Respect V1 scope:
- FastAPI + Postgres backend;
- Vite/React/TypeScript read-only frontend;
- deterministic fictional used-car fixture world;
- static fixture-scoped bearer tokens resolved server-side;
- exactly two repo-owned app images: xclone-backend and xclone-frontend;
- Postgres remains upstream postgres:16-alpine, never installed in the backend image;
- backend tests use real Postgres plus Alembic migrations, not SQLite or Base.metadata.create_all;
- full RT-001 through RT-008 runner design stays separate unless explicitly requested.

Keep everything public-safe: synthetic data only, placeholder credentials only, no private paths, no real user data, no private transcripts, and no production or completed-hardening claims.

Do not commit.
```
