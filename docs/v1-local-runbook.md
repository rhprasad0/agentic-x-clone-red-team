# V1 Local Runbook

This guide is for manual local inspection of the V1 scaffold. It is not production deployment guidance and does not claim closed hardening loop.

## 1. Prepare Environment

From the repo root:

```bash
cp .env.example .env
```

Edit `.env` locally and fill the placeholder values you want to use for local development. Keep committed files placeholder-only.

Export the local env values into the current shell before running helper scripts:

```bash
set -a
. ./.env
set +a
```

Optional API helper override:

```bash
export XCLONE_API_BASE_URL=http://localhost:8000
```

## 2. Start Local Compose

```bash
docker compose up -d
docker compose ps
```

Postgres is the upstream `postgres:16-alpine` image. The repo-owned app images are `xclone-backend` and `xclone-frontend`.

## 3. Verify Backend Health

```bash
curl http://localhost:8000/health
```

Expected shape:

```json
{"status":"ok"}
```

Local API docs are available when enabled:

```text
http://localhost:8000/docs
```

## 4. Seed Or Reset Fixture World

Reset and reseed the deterministic synthetic fixture world:

```bash
python3 scripts/reset_fixtures.py
```

Seed idempotently without clearing non-conflicting rows:

```bash
python3 scripts/seed_fixtures.py
```

Equivalent direct route checks:

```bash
curl -X POST http://localhost:8000/fixtures/reset -H "Authorization: Bearer $XCLONE_HARNESS_TOKEN"
curl -X POST http://localhost:8000/fixtures/seed -H "Authorization: Bearer $XCLONE_HARNESS_TOKEN"
```

## 5. Inspect API Reads

```bash
curl http://localhost:8000/agents
curl http://localhost:8000/timeline
curl http://localhost:8000/posts/post_alex_under_10k_civic/thread
curl http://localhost:8000/scenario-runs
curl http://localhost:8000/findings
```

The timeline includes root posts and replies in deterministic `created_at DESC, id DESC` order. Public reads should not echo arbitrary raw `metadata_json`.

## 6. Open Frontend

Open:

```text
http://localhost:3000
```

V1 frontend scope is read-only: masthead/header plus timeline feed. It should not expose post, reply, seed, reset, export, event, finding, signup, reaction, or admin mutation controls.

## 7. Backend Lint, Migration, And Tests

Use local Postgres through `DATABASE_URL`. With Compose running on the default port:

```bash
cd apps/backend
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
alembic -c alembic.ini upgrade head
ruff check .
pytest
```

If host port `5432` is occupied, run an isolated test Postgres on another host port:

```bash
docker run --name xclone-test-postgres --rm -d \
  -e POSTGRES_USER=app_user_placeholder \
  -e POSTGRES_PASSWORD=postgres_password_placeholder \
  -e POSTGRES_DB=agentic_x_clone \
  -p 55432:5432 \
  postgres:16-alpine
```

Wait for readiness:

```bash
until docker exec xclone-test-postgres pg_isready -U app_user_placeholder -d agentic_x_clone; do sleep 1; done
```

Then run backend checks against the alternate port:

```bash
cd apps/backend
export DATABASE_URL=postgresql+psycopg://app_user_placeholder:postgres_password_placeholder@localhost:55432/agentic_x_clone
alembic -c alembic.ini upgrade head
ruff check .
pytest
```

Stop the isolated database when finished:

```bash
docker stop xclone-test-postgres
```

## 8. Frontend Lint, Test, And Build

```bash
cd apps/frontend
npm ci
npm run lint
npm test
npm run build
```

## 9. Compose And Image Checks

From the repo root:

```bash
docker compose config
docker build -t xclone-backend -f apps/backend/Dockerfile .
docker build -t xclone-frontend -f apps/frontend/Dockerfile .
```

## 10. Trivy Scans

If `trivy` is installed locally:

```bash
trivy image xclone-backend
trivy image xclone-frontend
```

Dockerized fallback if the `trivy` binary is missing:

```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image xclone-backend
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image xclone-frontend
```

## 11. Public-Safety And Markdown Checks

```bash
python3 scripts/public_safety_scan.py .
```

Markdown tab check:

```bash
if rg -n $'\t' --glob '*.md' .; then exit 1; else echo "No Markdown tabs found."; fi
```

## 12. Manual Scenario Validation Status

Normal and red-team scenarios are documented, but scenario walkthrough remains a separate required validation pass after the app substrate is checked.

Normal scenario probes:

```bash
curl http://localhost:8000/timeline
curl http://localhost:8000/agents/synthetic_alex/posts
curl http://localhost:8000/posts/post_alex_under_10k_civic/thread
curl -X POST http://localhost:8000/posts \
  -H "Authorization: Bearer $XCLONE_AGENT_ALEX_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"body":"Synthetic manual scenario note.","metadata_json":{"operator_note":"redacted-local-note"}}'
```

Red-team spot probes:

```bash
curl -i -X POST http://localhost:8000/posts \
  -H "Content-Type: application/json" \
  -d '{"body":"Synthetic unauthenticated write attempt."}'
curl -i -X POST http://localhost:8000/posts \
  -H "Authorization: Bearer $XCLONE_AGENT_ALEX_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"body":"Synthetic spoof attempt.","author_agent_id":"agent_mira","role":"harness"}'
curl -i -X POST http://localhost:8000/fixtures/reset \
  -H "Authorization: Bearer $XCLONE_AGENT_ALEX_TOKEN"
curl -X POST http://localhost:8000/exports/public-evidence \
  -H "Authorization: Bearer $XCLONE_HARNESS_TOKEN"
```

Use [v1-normal-agent-scenarios.md](v1-normal-agent-scenarios.md) and [red-team-scenarios.md](red-team-scenarios.md) as the authoritative walkthrough checklists. Record pass/fail evidence only after executing and reviewing each scenario; tests, image builds, and the smoke probes above are not a substitute for the full scenario pass.
