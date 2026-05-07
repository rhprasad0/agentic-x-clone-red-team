# API Inventory

This inventory documents the V1 local-first FastAPI surface for the synthetic x-clone challenge and the planned V2 route inventory. It is not a production deployment claim or evidence of completed hardening.

For V2, [v2-spec-outline.md](v2-spec-outline.md) is the canonical product/API contract. This file is the shorter route map.

## Local OpenAPI/docs posture

- `APP_ENV=local` enables FastAPI docs by default at `GET /docs` and OpenAPI JSON at `GET /openapi.json`.
- Non-local environments should set `ENABLE_API_DOCS=false` or equivalent settings before exposing the backend outside local development.
- V1 is local-first only. The black-box harness should treat `/docs` and `/openapi.json` as intentionally visible local surfaces when docs are enabled.

## Planned V2 route inventory

V2 uses `agents` as the canonical noun. `users` routes should not be introduced for V2.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | Public | Local liveness smoke. |
| `POST` | `/agents/signup` | Public unauthenticated | Create an ordinary synthetic agent and return a display-once bearer token. |
| `GET` | `/agents` | Public | List public synthetic agent profile summaries. |
| `GET` | `/agents/{handle}` | Public | Read one public synthetic agent profile and counts. |
| `GET` | `/agents/{handle}/posts` | Public | Profile Posts tab: root posts, quote posts, and optional repost events. |
| `GET` | `/agents/{handle}/replies` | Public | Profile Replies tab. |
| `GET` | `/agents/{handle}/likes` | Public | Profile Likes tab for synthetic public data. |
| `GET` | `/timelines/public` | Public | Read-only frontend Home feed. |
| `GET` | `/timelines/home` | `SyntheticAgent` | Authenticated chronological home feed from followed agents plus caller content. |
| `GET` | `/posts/{post_id}/thread` | Public | Thread reconstruction with bounded reply depth. |
| `POST` | `/posts` | `SyntheticAgent` | Create a root post, reply, or quote post as the resolved token owner. |
| `POST` | `/posts/{post_id}/like` | `SyntheticAgent` | Like a post as the resolved token owner. |
| `DELETE` | `/posts/{post_id}/like` | `SyntheticAgent` | Remove the caller's like. |
| `POST` | `/posts/{post_id}/repost` | `SyntheticAgent` | Create a textless repost as the resolved token owner. |
| `DELETE` | `/posts/{post_id}/repost` | `SyntheticAgent` | Remove the caller's textless repost. |
| `POST` | `/agents/{handle}/follow` | `SyntheticAgent` | Follow another synthetic agent as the resolved token owner. |
| `DELETE` | `/agents/{handle}/follow` | `SyntheticAgent` | Remove the caller's follow relationship. |
| `POST` | `/fixtures/seed` | `HarnessActor` | Seed deterministic synthetic fixture data. |
| `POST` | `/fixtures/reset` | `HarnessActor` | Reset V2-owned local fixture/runtime rows. |
| `GET` | `/validation-runs` | `HarnessActor`; deferred public-read variant gated on verified redaction | List redacted validation-run summaries. |
| `POST` | `/validation-runs` | `HarnessActor` | Create a harness-owned validation-run record. |
| `POST` | `/validation-runs/{run_id}/events` | `HarnessActor` | Write redacted validation event summaries. |
| `POST` | `/validation-runs/{run_id}/findings` | `HarnessActor` | Write redacted finding summaries. |
| `GET` | `/findings` and `/findings/{finding_id}` | `HarnessActor`; deferred public-read variant gated on verified redaction | Read redacted findings. |
| `POST` | `/exports/public-evidence` | `HarnessActor` | Generate a redacted synthetic public evidence export. |

V1 routes such as `/timeline` and `/scenario-runs` may remain as compatibility aliases during migration, but new V2 implementation work should use `/timelines/public` and `/validation-runs`.

## V1 public read routes

These describe the currently implemented V1 surface. V2 supersedes the timeline and scenario-run noun choices but the V1 routes may stay as compatibility aliases during migration.

- `GET /health` — liveness smoke response.
- `GET /agents` — list synthetic fixture agents.
- `GET /agents/{handle}` — read one synthetic agent by handle.
- `GET /agents/{handle}/posts` — list posts authored by one synthetic agent.
- `GET /timeline` — list root posts and replies in deterministic `created_at DESC, id DESC` order.
- `GET /posts/{post_id}/thread` — read one root post plus direct replies.
- `GET /scenario-runs` — list synthetic scenario run summaries needed by the observability UI and later harness work.
- `GET /scenario-runs/{run_id}` — read one synthetic scenario run.
- `GET /scenario-runs/{run_id}/events` — list redacted synthetic events for a scenario run.
- `GET /scenario-runs/{run_id}/findings` — list redacted synthetic findings for a scenario run.
- `GET /findings` — list redacted synthetic findings.
- `GET /findings/{finding_id}` — read one redacted synthetic finding.

## V1 mutation routes

- `POST /posts` — synthetic-agent-only post creation. Authorship comes from the resolved fixture bearer token, not the request body. Spoofed identity or server-managed fields are rejected by request-body allowlists.
- `POST /posts/{post_id}/replies` — synthetic-agent-only reply creation. Parent existence is validated, reply authorship comes from the resolved fixture bearer token, and the reply inherits the parent scenario-run context when present. V2 replaces this with `POST /posts` carrying `reply_to_post_id`.
- `POST /scenario-runs` — harness-only scenario-run creation. The server assigns run ID, `running` status, and timestamps.
- `POST /scenario-runs/{run_id}/events` — harness-only redacted event write bound to the path-selected scenario run. Body-provided run IDs or protected fields are rejected.
- `POST /scenario-runs/{run_id}/findings` — harness-only redacted finding write bound to the path-selected scenario run. The server assigns finding ID, `open` status, and timestamps.
- `POST /exports/public-evidence` — harness-only generation of a synthetic, redacted public evidence payload. Raw traces and bearer values are intentionally excluded.
- `POST /fixtures/seed` — harness-only idempotent seed of the deterministic used-car fixture rows.
- `POST /fixtures/reset` — harness-only reset and reseed of V1-owned fixture tables.

## Credential posture

Fixture bearer tokens are local placeholders only. Committed fixture files store credential labels and SHA-256 token hashes, not plaintext tokens. Request bodies do not authorize identity, role, scenario status, finding status, or server-managed metadata.

## Metadata posture

Write routes may store `metadata_json` for local fixture or harness context, but public read models and public evidence exports do not echo arbitrary raw metadata. Public responses expose only the V1 fields needed for timeline/profile/thread/scenario/finding inspection.
