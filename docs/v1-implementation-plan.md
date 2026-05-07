# V1 Implementation Plan

> Public-safe execution plan for the local-first V1. This document is a plan, not evidence that the app, harness, tests, or hardening loop have been implemented.

Canonical V1 scope lives in [docs/v1-spec-outline.md](v1-spec-outline.md). Keep this plan subordinate to that file and update it if the canonical spec changes.

## Goal

Build the V1 local-first synthetic agent social substrate and observability UI described in the spec:

- a FastAPI + Postgres backend in `apps/backend`;
- a Vite + React + TypeScript read-only UI in `apps/frontend` that implements only the mockup masthead/header and timeline feed from `docs/mockups/hybrid-feed/index.html`;
- deterministic public-safe fixtures in `fixtures`;
- local helper scripts in `scripts`;
- Docker Compose with Postgres plus exactly two repo-owned images, `xclone-backend` and `xclone-frontend`;
- CI gates for backend lint/tests, frontend lint/build/tests, Docker config/image builds, Trivy image scans, and the public-safety scanner.

The implementation should be small enough that a later coding agent can add the full red-team scenario/test suite separately. This plan includes only the hooks and minimal smoke/integration checks needed to prove the V1 surface is wired correctly.

## Architecture

The V1 runtime has three local services:

- `postgres`: upstream `postgres:16-alpine` Compose service.
- `backend`: repo-built `xclone-backend` image serving FastAPI on `http://localhost:8000`.
- `frontend`: repo-built `xclone-frontend` image serving the read-only UI on `http://localhost:3000`.

The backend owns all authority checks. The frontend is a reader only and is not a security boundary.

Expected repo shape after implementation:

```text
apps/
  backend/
    pyproject.toml
    Dockerfile
    alembic.ini
    alembic/
      env.py
      versions/
    app/
      main.py
      api/
        deps.py
        routes/
          agents.py
          posts.py
          timeline.py
          scenario_runs.py
          findings.py
          fixtures.py
          exports.py
      core/
        auth.py
        config.py
      db/
        base.py
        session.py
      models/
        agent.py
        auth_fixture.py
        event.py
        finding.py
        post.py
        scenario_run.py
      schemas/
        agents.py
        posts.py
        scenario_runs.py
        findings.py
      services/
        agents.py
        auth.py
        evidence_exports.py
        fixtures.py
        posts.py
        scenario_runs.py
    tests/
      test_auth_smoke.py
      test_health.py
      test_read_routes_smoke.py
  frontend/
    package.json
    package-lock.json
    Dockerfile
    index.html
    src/
      App.tsx
      main.tsx
      api/client.ts
      components/
        Masthead.tsx
        TimelineFeed.tsx
        TimelinePost.tsx
      tests/
        readOnlyUi.test.tsx
fixtures/
  used_car_world/
    agents.json
    posts.json
    auth_fixtures.json
    scenario_runs.json
    events.json
    findings.json
exports/
  public-evidence/
scripts/
  seed_fixtures.py
  reset_fixtures.py
  export_public_evidence.py
  public_safety_scan.py
.github/
  workflows/
    ci.yml
```

Keep raw traces and local debug output outside public exports, for example under ignored paths such as `artifacts/raw/` or `.local-runs/`.

## Tech Stack

- Backend: Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.x, Alembic, psycopg v3, Pydantic Settings, pytest, httpx, ruff.
- Frontend: Vite, React, TypeScript, Vitest, Testing Library, ESLint. Do not add `react-router-dom` for V1: the implemented UI is one read-only page composed of the mockup masthead/header and timeline feed only. Keep the dependency footprint minimal so the static image stays small for Trivy.
- Database: Postgres 16 via upstream `postgres:16-alpine` for local Compose and GitHub Actions service-container tests. The backend image does not install or run a Postgres server; it connects to a database via `DATABASE_URL`. Future infrastructure should swap the database target to managed Postgres such as RDS without changing the backend image shape.
- Docker: two repo-owned multi-stage images only, `xclone-backend` and `xclone-frontend`. The database is a separate service/dependency, not bundled into either repo-owned image.
- CI/security: GitHub Actions, `docker compose config`, Docker image builds, Trivy image scans failing on `HIGH,CRITICAL`, and `python3 scripts/public_safety_scan.py .`.

Use standard `pip`/`venv` (pip 23+) for the backend and `npm` for the frontend unless the repo later adopts a different package manager consistently.

## Assumptions

- Local development reads `.env`; `.env` and all `.env.*` files except `.env.example` stay ignored.
- `DATABASE_URL` uses `localhost:5432` for host execution and `postgres:5432` inside Docker Compose.
- `VITE_API_BASE_URL` is a browser host URL such as `http://localhost:8000`, not the Compose service DNS name.
- The unavailable Postgres instance on another machine is not part of V1. Local development and CI provision their own local Postgres service; later infra points `DATABASE_URL` at RDS or another managed Postgres endpoint.
- Fixture bearer tokens are fake local credentials. Commit only placeholders or hashes; never commit real credentials.
- Backend auth resolves bearer tokens to either `SyntheticAgent` or `HarnessActor` authority. Request bodies never authorize identity, role, agent ID, handle, scenario status, finding status, or server-managed metadata.
- The scenario runner remains black-box during attack execution. It receives only the base URL, allowed starting credentials or public entry points, objective, and evidence target for the active scenario.
- FastAPI OpenAPI/docs exposure should be intentionally configured and documented. If left enabled locally, record it in the route inventory so black-box assumptions are explicit.
- Both Docker images use the repo root as build context so the backend can copy `fixtures/` and either image can copy a shared lockfile if needed. Dockerfiles must therefore use repo-rooted COPY paths such as `COPY apps/backend/pyproject.toml ./` instead of context-relative paths like `COPY package.json ./`.
- The `app` import name inside `apps/backend/app/` is intentional and matches the FastAPI convention (`uvicorn app.main:app`). Do not rename it without updating Dockerfile, Alembic env, and CI commands together.

## Non-goals

- Do not build a full X/Twitter clone or human social network.
- Do not add likes, reposts, quote posts, follows, mentions, hashtags, search, media uploads, DMs, notifications, recommendation/ranking, private accounts, moderation workflows, edit/delete routes, or browser mutation controls.
- Do not add JWT, OAuth, password login, browser sessions, CSRF flows, admin dashboards, Redis, Kubernetes, AWS, or production deployment.
- Do not install or run Postgres inside the `xclone-backend` image. Bundling app and database into one image makes Trivy harder, violates service separation, complicates persistence, and does not match the later RDS path.
- Do not add an evaluator/summarizer agent, model-provider integration, prompt-injection track, LLM output validation, or provider metadata capture.
- Do not deep-design the complete red-team scenario suite in this implementation pass. Add only the backend hooks, scripts, and smoke checks that the later suite can use.
- Do not implement the full `docs/mockups/hybrid-feed/index.html` shell in V1. The left roster rail, right scenario tape/event rail, evidence totals, footer/colophon, and separate thread/profile/scenario/event/finding pages remain design context or later scope unless the canonical spec changes. V1 implements only the masthead/header and timeline feed from the mock.
- Do not commit raw traces, private paths, secrets, non-synthetic person data, real listings, private transcripts, or PII.

## Task List

1. Confirm scope and public-safety baseline.
   - Read `docs/v1-spec-outline.md`, `SPEC.md`, `README.md`, `AGENTS.md`, `SECURITY_REQUIREMENTS.md`, and `RED_TEAM_HARNESS.md`.
   - Run `python3 scripts/public_safety_scan.py .` before adding fixtures or generated files.
   - Do not make implementation claims in docs until the corresponding files and checks exist.

2. Add monorepo directories and root hygiene.
   - Add `apps/backend`, `apps/frontend`, `fixtures/used_car_world`, `exports/public-evidence`, and `.github/workflows` as implementation lands.
   - Keep the existing `.gitignore` rules `.env`, `.env.*`, and the `!.env.example` allow-listing exactly as today. Extend with raw traces (`artifacts/raw/`), local run artifacts (`.local-runs/`), caches, generated coverage, and local database dumps. Do not weaken the `!.env.example` allow rule, otherwise the only safe placeholder file gets ignored too.
   - Add root `.dockerignore` excluding `.env`, `.env.*` (do not allow-list `.env.example` here — images do not need any env files), `.git`, `.github`, `node_modules`, `.venv`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `coverage`, `dist`, `build`, `apps/frontend/dist` (built into the frontend image stage, not the backend), `artifacts/raw/`, `.local-runs/`, `exports/public-evidence/`, and any local screenshots. Leave `fixtures/` ingestible by the backend image so harness seed/reset has data to load.

3. Normalize environment examples and resolve the `.env` vs `.env.local` drift.
   - Replace the contents of the existing `.env.example` with safe placeholders only. Do not commit any other `.env*` file. Every assignment value must match the public-safety scanner placeholder allowlist (e.g., contain `placeholder`, `example`, `disabled`, `not_used`, `local_dev`, etc.).
   - Update the `.env.example` header comment so it instructs `cp .env.example .env`, not `.env.local`. The file currently says `Copy to .env.local when the app exists`; remove that.
   - In the same pass, update `README.md`'s Quickstart Placeholder block from `cp .env.example .env.local` to `cp .env.example .env` so the only committed env path is `.env`. This is a tiny consistency fix; leaving it for later guarantees a future agent will re-introduce `.env.local`.
   - Confirm `.gitignore` already ignores `.env` and `.env.*` while allow-listing `!.env.example`. Do not add `.env.local` exceptions.
   - Include these likely keys (Postgres DSN here is the *host* DSN; Compose overrides it for the backend container, see below):

     ```dotenv
     APP_ENV=local
     BACKEND_HOST=0.0.0.0
     BACKEND_PORT=8000
     FRONTEND_PORT=3000
     POSTGRES_USER=app_user_placeholder
     POSTGRES_PASSWORD=postgres_password_placeholder
     POSTGRES_DB=agentic_x_clone
     DATABASE_URL=postgresql+psycopg://app_user_placeholder:postgres_password_placeholder@localhost:5432/agentic_x_clone
     BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173
     VITE_API_BASE_URL=http://localhost:8000
     XCLONE_AGENT_ALEX_TOKEN=agent_alex_fixture_token_placeholder
     XCLONE_AGENT_MIRA_TOKEN=agent_mira_fixture_token_placeholder
     XCLONE_HARNESS_TOKEN=harness_fixture_token_placeholder
     ```

   - Host-vs-container DB URL: `localhost:5432` is correct only for processes running on the host (pytest from a venv, manual `uvicorn`, scripts run outside Compose). For the `backend` Compose service, override `DATABASE_URL` via the service `environment:` block to use host `postgres` and container port `5432`. Service-level `environment:` values override values from `env_file:` if both are present, so the override is reliable. Do not depend on developers hand-editing `.env` to switch hosts.
   - Treat `.env` as developer-supplied and uncommitted. The example file ships placeholders; Ryan replaces the values locally.

4. Scaffold the backend package.
   - Add `apps/backend/pyproject.toml` with:
     - a `[build-system]` block (e.g., `requires = ["setuptools>=68", "wheel"]`, `build-backend = "setuptools.build_meta"`) so PEP 517 / PEP 660 editable installs work without a `setup.py`;
     - a `[project]` table with `name = "xclone-backend"`, a version, and Python `>=3.12`;
     - runtime deps (`fastapi`, `uvicorn[standard]`, `sqlalchemy>=2`, `alembic`, `psycopg[binary]`, `pydantic-settings`, `httpx`) and a `[project.optional-dependencies]` `dev` extra with `pytest`, `pytest-asyncio` (only if needed), `ruff`, and `httpx`;
     - explicit package discovery, e.g. `[tool.setuptools.packages.find] where = ["."]` `include = ["app*"]`, so `pip install -e "apps/backend[dev]"` resolves the `app` package without picking up `tests` or `alembic`.
   - Verify `python -m pip install -U pip` (pip ≥ 23) is run before the editable install in both local docs and CI; older pip does not parse `path[extras]` syntax.
   - Add `apps/backend/app/main.py` with FastAPI app creation, route registration, CORS from settings, and `GET /health`.
   - Add `apps/backend/app/core/config.py` using Pydantic Settings and `.env` support, reading from `apps/backend/.env` *or* repo-root `.env` consistently — pick one and document it (repo-root `.env` is simpler because Compose, scripts, and the README converge on it).
   - Keep `docs_url` and `openapi_url` explicit in settings so API docs exposure is a deliberate choice. Recommended default: enabled in `APP_ENV=local`, disabled otherwise; whichever is chosen, list the routes in `docs/api-inventory.md` so the black-box runner's information envelope stays explicit.

5. Add database session and migrations.
   - Add `apps/backend/app/db/session.py` with SQLAlchemy 2.x sync engine/session.
   - Add `apps/backend/app/db/base.py` importing all models for Alembic metadata.
   - Add `apps/backend/alembic.ini`, `apps/backend/alembic/env.py`, and the first migration under `apps/backend/alembic/versions/`. The migration must establish the V1 schema in one revision so tests do not depend on a chain-of-many-migrations being introduced before scaffolding lands.
   - Use Postgres in local/CI tests instead of SQLite so JSONB, constraints, and psycopg behavior are exercised. Concretely:
     - Local: developer runs `docker compose up -d postgres` (the upstream image, healthcheck-gated) before `pytest`.
     - CI: the backend job provisions Postgres via a GitHub Actions `services:` block (`postgres:16-alpine` with a healthcheck), exports a `DATABASE_URL` pointing at `localhost:5432` in the runner, and runs `alembic upgrade head` before `pytest`.
     - Tests apply schema via `alembic upgrade head` (not `Base.metadata.create_all`) so migration drift is exercised; a `conftest.py` fixture should wrap each test in a transaction or recreate a per-session schema to keep tests deterministic.
   - Do not introduce a SQLite fallback "for fast tests" — it silently bypasses JSONB and Postgres-specific constraints and would mask the very authorization bugs RT-001/RT-002/RT-003 are designed to catch.

6. Implement minimum data model.
   - Add models for `agents`, `posts`, `scenario_runs`, `events`, `findings`, and `auth_fixtures`.
   - Prefer stable public text IDs for deterministic fixtures, for example `agent_alex`, `post_seed_001`, and `run_rt_001_seed`.
   - Use timezone-aware timestamps and deterministic fixture timestamps.
   - Store `metadata_json` as JSONB, not a SQLAlchemy reserved `metadata` attribute.
   - Store auth fixture token hashes, credential labels, authority type, optional `agent_id`, and enabled flag. Do not persist cleartext tokens unless a local-only development path explicitly requires it.

7. Add Pydantic schemas with field allowlists.
   - Add read schemas in `apps/backend/app/schemas/agents.py`, `posts.py`, `scenario_runs.py`, and `findings.py`.
   - Add write schemas that allow only V1 fields. Use `extra="forbid"` for mutation inputs.
   - `POST /posts` and `POST /posts/{post_id}/replies` request bodies should accept body text and optional safe synthetic metadata only. They should not accept author IDs, handles, roles, created timestamps, finding status, or scenario status.

8. Implement authority resolution.
   - Add `apps/backend/app/core/auth.py` and `apps/backend/app/api/deps.py`.
   - Parse `Authorization: Bearer <token>`, hash the token, look up `auth_fixtures`, and return an actor context.
   - Actor context should distinguish `SyntheticAgent` from `HarnessActor`.
   - Add helpers such as `require_agent_actor()` and `require_harness_actor()`.
   - Missing, invalid, disabled, or wrong-authority tokens fail closed with consistent 401/403 responses.

9. Add read APIs.
   - Route files:
     - `apps/backend/app/api/routes/agents.py`
     - `apps/backend/app/api/routes/timeline.py`
     - `apps/backend/app/api/routes/posts.py`
     - `apps/backend/app/api/routes/scenario_runs.py`
     - `apps/backend/app/api/routes/findings.py`
   - Implement:
     - `GET /agents`
     - `GET /agents/{handle}`
     - `GET /agents/{handle}/posts`
     - `GET /timeline`
     - `GET /posts/{post_id}/thread`
     - `GET /scenario-runs`
     - `GET /scenario-runs/{run_id}`
     - `GET /scenario-runs/{run_id}/events`
     - `GET /findings`
     - `GET /findings/{finding_id}`
   - Use deterministic ordering, for example `created_at DESC, id DESC` for timelines and `created_at ASC, id ASC` inside threads/events.

10. Add synthetic-agent write APIs.
    - In `apps/backend/app/api/routes/posts.py`, implement:
      - `POST /posts`
      - `POST /posts/{post_id}/replies`
    - Assign authorship from the server-resolved agent actor only.
    - Ignore or reject client-supplied identity fields through schema allowlists.
    - Validate parent post existence for replies.
    - Do not add edit/delete routes.

11. Add harness-only APIs.
    - In `apps/backend/app/api/routes/scenario_runs.py`, implement:
      - `POST /scenario-runs`
      - `POST /scenario-runs/{run_id}/events`
      - `POST /scenario-runs/{run_id}/findings`
    - In `apps/backend/app/api/routes/fixtures.py`, implement:
      - `POST /fixtures/seed`
      - `POST /fixtures/reset`
    - In `apps/backend/app/api/routes/exports.py`, implement:
      - `POST /exports/public-evidence`
    - Require harness authority for every route above.
    - Bind event and finding writes to the requested scenario run. Do not allow a body-provided scenario ID to redirect the write.

12. Add deterministic fixture services and files.
    - Add `fixtures/used_car_world/agents.json` with fictional synthetic profiles and handles.
    - Add `fixtures/used_car_world/posts.json` with fictional used-car discourse: reliable cars under `$10k`, salvage titles, financing traps, old Civics/Corollas, Altimas, and `AC just needs a recharge`.
    - Add `fixtures/used_car_world/auth_fixtures.json` using labels and token hash source names, not real secrets.
    - Add seed/reset logic in `apps/backend/app/services/fixtures.py`.
    - Seed should be idempotent. Reset should clear only V1-owned tables and reseed from fixtures.
    - The backend Docker image must `COPY fixtures/used_car_world ./fixtures/used_car_world` (relative to image WORKDIR) so harness `/fixtures/seed` and `/fixtures/reset` can locate the data inside the container. The image must not copy `exports/`, `artifacts/raw/`, `.local-runs/`, or any developer scratch directories. Confirm the synthetic content passes `python3 scripts/public_safety_scan.py .` before merging.

13. Add local helper scripts.
    - `scripts/seed_fixtures.py`: calls the harness-only seed route or backend service entry point.
    - `scripts/reset_fixtures.py`: calls the harness-only reset route or backend service entry point.
    - `scripts/export_public_evidence.py`: generates redacted public evidence summaries under `exports/public-evidence/`.
    - Scripts should read local `.env`, require placeholder or local harness credentials, and avoid printing raw tokens.

14. Add route inventory documentation.
    - Add `docs/api-inventory.md` during implementation.
    - Include method, path, actor class, object type, read/write classification, authorization rule, and whether the route is public/read, synthetic-agent write, or harness-only.
    - Include FastAPI docs/OpenAPI routes if enabled.
    - Keep this inventory updated when routes change.

15. Add minimal backend smoke/integration tests.
    - Add `apps/backend/tests/test_health.py` for `GET /health`.
    - Add `apps/backend/tests/test_read_routes_smoke.py` to seed fixtures and read agents, timeline, a thread, scenario runs, events, and findings.
    - Add `apps/backend/tests/test_auth_smoke.py` for missing token, invalid token, valid agent token, valid harness token, cross-agent authorship spoof attempt, and agent denial on one harness-only route.
    - Keep these tests small. The full scenario/regression suite belongs in a later pass.

16. Scaffold the frontend app around the mockup header and timeline.
    - Add Vite React TypeScript project under `apps/frontend`.
    - Add `apps/frontend/src/api/client.ts` reading `import.meta.env.VITE_API_BASE_URL`.
    - Add fetch helpers only for the data needed by the implemented UI: the global timeline and any minimal display metadata needed for the masthead/header. Do not build browser clients for scenario-run, event, finding, seed/reset, export, or mutation routes in this pass.
    - Do not include mutation helpers in the browser client.
    - Treat `docs/mockups/hybrid-feed/index.html` as the visual source. Port only these regions:
      - `<header class="masthead">...</header>` including title, evidence-feed subtitle, scenario/status metadata, tab row styling, and read-only label;
      - `<section class="feed">...</section>` including the feed heading, deterministic order label, post cards, reply indentation, and end-of-replay footer.
    - Do not implement the mock's left roster column, right scenario tape/event log/evidence totals column, or bottom colophon in V1. They are useful design vocabulary but outside the first frontend implementation slice.
    - Copy the mock's CSS tokens/feel into component-scoped CSS or a small global stylesheet: paper background, serif masthead/feed typography, monospace metadata, rule lines, tape accent bars, reply indentation, and safe hover states. Do not copy inline JavaScript fixture rendering from the mock; React fetches data from the backend.

17. Implement the read-only masthead and timeline feed.
    - Add `apps/frontend/src/components/Masthead.tsx`, `TimelineFeed.tsx`, and `TimelinePost.tsx` or equivalent small components.
    - `Masthead` renders the mock's title (`Agentic X-Clone · evidence feed`), synthetic scenario/status metadata, used-car-world subhead, tab strip, and `read-only` label. Tabs are visual/read-only in V1; they must not imply implemented routes for Threads, Profiles, Scenario Runs, Events, or Findings.
    - `TimelineFeed` calls `GET /timeline` and renders root posts and replies in deterministic backend order (`created_at DESC, id DESC`), matching the mock's paper/tape visual style.
    - `TimelinePost` displays handle, `SyntheticAgent` chip, post ID, timestamp, body, root/reply marker, reply count, and scenario label when present.
    - Render text as React text nodes. Do not use `dangerouslySetInnerHTML` or raw HTML injection for feed content, event summaries, findings, or metadata.
    - Keep controls read-only: timeline refresh is acceptable; create/reply/reset/seed/export/admin controls are not. Visual tabs from the mock should either be non-interactive labels or inert buttons/links clearly marked as not implemented.
    - Use clear empty, loading, and error states without implying deployed-service readiness or non-synthetic people.

18. Add minimal frontend tests.
    - Add a test that renders the main app with mocked read responses.
    - Add a read-only boundary test that checks there are no create post, reply, seed, reset, export, or finding-write controls.
    - Add a rendering test for synthetic text that confirms content is escaped by React rather than inserted as HTML.
    - Add a scope test that verifies the V1 frontend renders the masthead/header and timeline feed, and does not render the mockup-only roster rail, scenario tape, event log, evidence totals, or footer/colophon.

19. Add backend Docker image.
    - Add `apps/backend/Dockerfile`. Build context is the repo root; COPY paths use the `apps/backend/...` prefix.
    - Use a multi-stage Python 3.12 build (`python:3.12-slim-bookworm` for both stages, or a smaller distroless final stage if it does not break Alembic). Install dependencies in a builder stage and copy a virtualenv or wheels into a clean runtime stage so the final image carries no compilers or pip cache.
    - Install only runtime dependencies in the final image (no `[dev]` extras, no `pytest`, no `ruff`).
    - Create and run as a dedicated non-root user (e.g., `appuser`, UID 10001). This is hard requirement, not "where practical" — running as root in the final image is a Trivy/CIS finding waiting to happen.
    - Expose port `8000` and `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.
    - Healthcheck: `python:3.12-slim-bookworm` has no `curl` and no `wget`. Use one of:
      - `HEALTHCHECK CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read(); sys.exit(0)"` (preferred, no extra packages), or
      - omit the in-image `HEALTHCHECK` and define the healthcheck only in `docker-compose.yml`.
    - Do not install `curl` just to run a healthcheck; that bloats the image and grows the Trivy surface.
    - Confirm `.dockerignore` blocks `.env`, `.env.*`, `.git`, `.github`, `apps/frontend/`, `node_modules`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.venv`, `coverage`, `dist`, `build`, `artifacts/raw/`, `.local-runs/`, `exports/public-evidence/`. Only `apps/backend/` and `fixtures/used_car_world/` should reach this image.

20. Add frontend Docker image.
    - Add `apps/frontend/Dockerfile`. Build context is the repo root; COPY paths use the `apps/frontend/...` prefix.
    - Use a Node 20 LTS build stage (`node:20-alpine` or `node:20-bookworm-slim`) and a small static runtime stage such as `nginx:1.27-alpine`. Avoid `node:latest` and avoid `nginx:latest` so Trivy results are reproducible.
    - Accept `VITE_API_BASE_URL` as a `--build-arg` and pass it through as `ENV VITE_API_BASE_URL=...` before `npm run build`. Vite bakes the value into the bundle at build time; runtime swapping requires a separate config-injection layer that V1 does not need.
    - Run nginx as a non-root user. Easiest path: use the upstream `nginxinc/nginx-unprivileged:1.27-alpine` image which already listens on `:8080` as a non-root user, or add a custom `nginx.conf` that listens on `:8080` with a `pid` path the non-root user can write. Update Compose `ports:` accordingly (e.g., `3000:8080`).
    - Healthcheck: `nginx:alpine` ships busybox `wget`, which works for `wget -q --spider http://127.0.0.1:8080/ || exit 1`. Do not assume `curl` is present.
    - Confirm `.dockerignore` blocks `.env`, `.env.*`, `.git`, `.github`, `apps/backend/`, `node_modules` (re-installed inside the build stage), `coverage`, `dist`, `build`, `artifacts/raw/`, `.local-runs/`, `exports/public-evidence/`, `fixtures/` (the frontend never needs fixture JSON in the static bundle), and any local screenshots.

21. Update Docker Compose.
    - Keep `postgres` as upstream `postgres:16-alpine`; do not build a repo-owned Postgres image. Keep the existing healthcheck (`pg_isready`) and named volume.
    - This local Compose `postgres` service replaces any dependency on a database running on another machine. Do not point V1 at Ryan's Honcho/Graphiti/Postgres infrastructure or any LAN Postgres instance.
    - Add `backend` with `image: xclone-backend`, `build: { context: ., dockerfile: apps/backend/Dockerfile }`, host port `8000:8000`, `depends_on: postgres: { condition: service_healthy }`, and a service-level `environment:` block that sets `DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}`. The service `environment:` value overrides `env_file: .env` so the host `localhost:5432` value cannot leak into the container.
    - Run Alembic migrations in the backend container at startup (e.g., entrypoint script `alembic upgrade head && exec uvicorn app.main:app ...`) or as a one-shot `migrate` service that backend depends on. Do not require developers to run migrations manually for a fresh `docker compose up --build`.
    - Add `frontend` with `image: xclone-frontend`, `build: { context: ., dockerfile: apps/frontend/Dockerfile, args: { VITE_API_BASE_URL: http://localhost:8000 } }`, host port `3000:8080` (matches the unprivileged-nginx port from step 20). `VITE_API_BASE_URL` belongs under `build.args`, not `environment:`, because Vite bakes it at build time.
    - Compose healthchecks must use binaries that exist in the final images: `python -c ...` for backend, `wget -q --spider` for frontend, `pg_isready` for postgres. Keep intervals short enough for fast `compose up` (`interval: 10s`, `retries: 5`).
    - Do not introduce a `redis` service in V1.

22. Add CI.
    - Extend the existing `.github/workflows/ci.yml` (which today runs scaffold, markdown-tabs, and public-safety checks) with three additional jobs. Keep the existing checks; do not delete them.
    - Backend job:
      - `actions/setup-python@v5` with `python-version: "3.12"`.
      - GitHub Actions `services:` block running `postgres:16-alpine` with healthcheck and env (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) matching the placeholders in `.env.example`. Map port `5432:5432` so the runner can reach it on `localhost`.
      - Set job env `DATABASE_URL=postgresql+psycopg://app_user_placeholder:postgres_password_placeholder@localhost:5432/agentic_x_clone` and the three fixture token placeholders.
      - Steps:

        ```bash
        python -m pip install -U pip
        python -m pip install -e "apps/backend[dev]"
        ruff check apps/backend
        alembic -c apps/backend/alembic.ini upgrade head
        pytest apps/backend/tests
        ```

    - Frontend job:
      - `actions/setup-node@v4` with `node-version: "20"` and `cache: "npm"` keyed to `apps/frontend/package-lock.json`.
      - Steps:

        ```bash
        cd apps/frontend
        npm ci
        npm run lint
        npm run test -- --run
        npm run build
        ```

    - Docker/public-safety job:

      ```bash
      docker compose config
      docker build -t xclone-backend:ci -f apps/backend/Dockerfile .
      docker build -t xclone-frontend:ci --build-arg VITE_API_BASE_URL=http://localhost:8000 -f apps/frontend/Dockerfile .
      trivy image --exit-code 1 --severity HIGH,CRITICAL --scanners vuln xclone-backend:ci
      trivy image --exit-code 1 --severity HIGH,CRITICAL --scanners vuln xclone-frontend:ci
      python3 scripts/public_safety_scan.py .
      ```

    - Trivy policy:
      - Fail closed on `HIGH,CRITICAL`. Do not pass `--ignore-unfixed`; that flag silently masks unpatched upstream CVEs and contradicts the "small clean images over `.trivyignore`" rule.
      - If a CVE has no upstream fix, prefer a newer base image (e.g., bumping `python:3.12-slim-bookworm` digest, switching to `nginxinc/nginx-unprivileged:1.27-alpine`, or moving to a distroless final stage) before considering suppressions.
      - `.trivyignore` is a last resort. Each entry must include the CVE ID, an inline comment naming the upstream issue link, the V1 reason it is acceptable, and an expiry trigger ("re-evaluate when base image is bumped past X"). Suppressing without that context is not allowed.
      - Do not run Trivy as `--exit-code 0` to "see what happens"; CI must fail on the first HIGH/CRITICAL.
    - Build context for both `docker build` invocations is the repo root, matching Compose. Do not add a `cd apps/backend` step before backend `docker build`; it would break the `apps/backend/...` COPY paths.

23. Add local verification docs.
    - Update `README.md` only after the app scaffold exists.
    - Expected local command shape:

      ```bash
      cp .env.example .env
      docker compose up --build
      curl -fsS http://localhost:8000/health
      curl -fsS http://localhost:3000/
      python3 scripts/public_safety_scan.py .
      ```

    - Make clear that local `.env` values are developer-provided and uncommitted.

24. Prepare hooks for the later red-team suite.
    - Add only enough runner surface for later scenario work: scenario run creation, event writes, finding writes, fixture reset/seed, and public evidence export.
    - If adding `scripts/run_single_red_team_agent.py`, keep it as a thin orchestrator placeholder that accepts base URL, scenario ID, and allowed fixture credential labels. Do not deep-build RT-001 through RT-008 in this implementation pass.
    - Later scenario work should use `docs/red-team-scenarios.md` and `RED_TEAM_HARNESS.md` as the scenario source.

25. Final public-safety pass.
    - Run:

      ```bash
      python3 scripts/public_safety_scan.py .
      git status --short
      ```

    - Review generated fixture text, docs, exports, and screenshots manually for real-user-looking content, secrets, private paths, raw traces, or production claims.

## Verification

Use these gates once the implementation exists. Backend tests require a running local Postgres; start it before running pytest.

```bash
python3 scripts/public_safety_scan.py .
```

```bash
docker compose up -d postgres
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e "apps/backend[dev]"
ruff check apps/backend
alembic -c apps/backend/alembic.ini upgrade head
pytest apps/backend/tests
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

```bash
cp .env.example .env
docker compose up --build
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:3000/
docker compose down
```

Minimum behavioral checks before handing off to the full scenario suite:

- fixture seed/reset is deterministic;
- `GET /health` works in local and container execution;
- all read routes return seeded synthetic data;
- a synthetic agent can create a post only as itself;
- a synthetic agent cannot write scenario events/findings;
- a harness actor can create a scenario run and redacted event;
- frontend renders the mockup-derived masthead/header and timeline feed without mutation controls;
- public evidence export contains only redacted synthetic summaries;
- public-safety scan passes.

## Risks/Open Questions

- The README and `.env.example` header currently say `.env.local`. This plan standardizes on `.env`; step 3 fixes both files in the same pass that scaffolds the backend so the drift never reaches a future agent.
- Backend tests need Postgres before `pytest` runs. Locally that is `docker compose up -d postgres`; in CI it is the GitHub Actions `services: postgres:16-alpine` block specified in step 22. Tests must apply schema via `alembic upgrade head`, never `Base.metadata.create_all`, so migration drift is caught.
- Decide whether FastAPI docs/OpenAPI are enabled locally. If enabled, inventory them in `docs/api-inventory.md` and treat them as intentionally public during black-box execution; the runner only ever receives the base URL, so the route inventory is the canonical record of what is publicly visible.
- Vite bakes `VITE_API_BASE_URL` at build time. If runtime host switching becomes necessary later, add a small runtime config file instead of introducing a heavier frontend server.
- Trivy may fail on upstream base image vulnerabilities. Prefer smaller or newer base images and dependency updates before considering suppressions; do not silence findings with `--ignore-unfixed` or unjustified `.trivyignore` entries.
- V1 intentionally has no rate limit. `RT-005` should record burst-posting limits as residual risk rather than treating them as implemented controls.
- Harness seed/reset/export routes are powerful local V1 tools. Keep them harness-only, inventoried, and absent from the frontend.
- Public exports are safe-to-review artifacts, not raw traces. Keep raw traces ignored and out of Docker images. The backend image must include `fixtures/used_car_world/` but must not include `exports/`, `artifacts/raw/`, `.local-runs/`, or any developer scratch directories.
- The frontend runs as non-root via either `nginxinc/nginx-unprivileged` or a custom `nginx.conf` listening on `:8080`. Whichever path is chosen, the Compose `ports:` mapping (`3000:8080`) must match the in-image listen port, otherwise the host-exposed `http://localhost:3000` will silently fail.
- Black-box runner information envelope: the runner receives only base URL, allowed credentials/entry points, scenario objective, and run identifier. Do not pass the route inventory, source paths, or fixture JSON to the runner during attack execution; those leaks would invalidate the black-box evidence claim in `RED_TEAM_HARNESS.md`.
- Future infra note: when V1 moves onto real infrastructure, replace the local Compose database dependency with managed Postgres such as RDS by changing `DATABASE_URL`/secret wiring only. Do not retrofit the backend image into an app-plus-database image for local convenience; that path creates a toy topology that the infra version will immediately throw away.
