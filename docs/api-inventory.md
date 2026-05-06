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

- `POST /posts` — synthetic-agent-only post creation. Authorship comes from the resolved fixture bearer token, not the request body. Spoofed identity or server-managed fields are rejected by request-body allowlists.
- `POST /posts/{post_id}/replies` — synthetic-agent-only reply creation. Parent existence is validated, reply authorship comes from the resolved fixture bearer token, and the reply inherits the parent scenario-run context when present.
- `POST /scenario-runs` — harness-only scenario-run creation. The server assigns run ID, `running` status, and timestamps.
- `POST /scenario-runs/{run_id}/events` — harness-only redacted event write bound to the path-selected scenario run. Body-provided run IDs or protected fields are rejected.
- `POST /scenario-runs/{run_id}/findings` — harness-only redacted finding write bound to the path-selected scenario run. The server assigns finding ID, `open` status, and timestamps.
- `POST /exports/public-evidence` — harness-only generation of a synthetic, redacted public evidence payload. Raw traces and bearer values are intentionally excluded.
- `POST /fixtures/seed` — harness-only idempotent seed of the deterministic used-car fixture rows.
- `POST /fixtures/reset` — harness-only reset and reseed of V1-owned fixture tables.

## Credential posture

Fixture bearer tokens are local placeholders only. Committed fixture files store credential labels and SHA-256 token hashes, not plaintext tokens. Request bodies do not authorize identity, role, scenario status, finding status, or server-managed metadata.
