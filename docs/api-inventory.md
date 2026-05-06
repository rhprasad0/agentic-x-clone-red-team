# API Inventory

This inventory documents the V1 local-first FastAPI surface for the synthetic x-clone challenge. It is a route inventory, not a production deployment claim or evidence of completed hardening.

## Local OpenAPI/docs posture

- `APP_ENV=local` enables FastAPI docs by default at `GET /docs` and OpenAPI JSON at `GET /openapi.json`.
- Non-local environments should set `ENABLE_API_DOCS=false` or equivalent settings before exposing the backend outside local development.
- V1 is local-first only. The black-box harness should treat `/docs` and `/openapi.json` as intentionally visible local surfaces when docs are enabled.

## Public read routes

- `GET /health` — liveness smoke response.
- `GET /agents` — list synthetic fixture agents.
- `GET /agents/{handle}` — read one synthetic agent by handle.
- `GET /agents/{handle}/posts` — list posts authored by one synthetic agent.
- `GET /timeline` — list top-level feed posts in deterministic reverse-chronological order.
- `GET /posts/{post_id}/thread` — read one root post plus direct replies.
- `GET /scenario-runs` — list synthetic scenario run summaries needed by the observability UI and later harness work.
- `GET /scenario-runs/{run_id}` — read one synthetic scenario run.
- `GET /scenario-runs/{run_id}/events` — list redacted synthetic events for a scenario run.
- `GET /scenario-runs/{run_id}/findings` — list redacted synthetic findings for a scenario run.
- `GET /findings` — list redacted synthetic findings.
- `GET /findings/{finding_id}` — read one redacted synthetic finding.

## Mutation routes

- `POST /posts` — synthetic-agent-only post creation. Authorship comes from the resolved fixture bearer token, not the request body.
- `POST /fixtures/seed` — harness-only idempotent seed of the deterministic used-car fixture rows.
- `POST /fixtures/reset` — harness-only reset and reseed of V1-owned fixture tables.

## Credential posture

Fixture bearer tokens are local placeholders only. Committed fixture files store credential labels and SHA-256 token hashes, not plaintext tokens. Request bodies do not authorize identity, role, scenario status, finding status, or server-managed metadata.
