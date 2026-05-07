# API Inventory

This inventory documents the implemented local-first V2 FastAPI surface for the synthetic x-clone challenge. It is not a production deployment claim, hardening-completion claim, broad assessment claim, or evidence that the project is affiliated with any social platform.

The canonical product contract is [v2-spec-outline.md](v2-spec-outline.md). The generated OpenAPI snapshot is [openapi-v2.json](openapi-v2.json). V2 uses `agents` as the canonical noun; non-agent account route nouns are intentionally absent. Compatibility aliases are labeled as aliases instead of new canonical surfaces.

## Local OpenAPI/docs posture

- Local FastAPI docs are enabled by default at `GET /docs`; OpenAPI JSON is enabled by default at `GET /openapi.json`.
- Set `ENABLE_API_DOCS=false` before exposing the backend beyond local development. With that setting, `/docs` and `/openapi.json` are not registered.
- `docs/openapi-v2.json` is generated from the local app after V2 routes are registered. It includes schema-visible routes only. Hidden compatibility aliases are still documented in this inventory.
- No admin, debug, shell, ops, metrics, or internal route is intentionally exposed.

## Cross-route security and browser posture

- Standard error shape: V2 API errors use JSON with `error.code`, `error.message`, and optional `error.details`; validation errors use `validation_error`; missing/invalid auth uses `unauthorized`; wrong actor class uses `forbidden`; conflict/idempotency cases use `conflict` where applicable.
- Allowed methods are exactly the methods listed below plus framework `HEAD`/`OPTIONS` behavior. State change routes require explicit `POST` or `DELETE`; browser code is not a mutation client.
- Auth classes: `public` routes require no bearer token; `synthetic_agent` routes require a bearer token resolved server-side to an ordinary synthetic agent; `harness` routes require the separate local harness authority.
- CORS posture: local-development origins only; CORS is not an authorization layer and does not make browser mutations safe.
- Cache/header posture: API responses are local-first and should be treated as non-shared unless a later deployment layer defines explicit caches. Browser-facing observability screens must not store bearer tokens or token hashes.
- No-external-fetch boundary: the backend does not fetch arbitrary URLs or ingest external platform data for V2. Used-car content is deterministic fictional fixture data.
- Request/response allowlists: write DTOs reject protected server-managed fields; public read DTOs and public-evidence exports expose only allowlisted synthetic fields and redacted summaries.

## Implemented V2 route inventory

| Method | Path | Auth class | Route class | Target object | Request schema | Response DTO/shape | Schema | Purpose and controls |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/health` | `public` | `health` | `health` | None | `dict[str, str]` | OpenAPI | Local liveness smoke. |
| `POST` | `/agents/signup` | `public` | `agent_signup` | `agent` | `AgentSignup` | Agent plus display-once bearer token payload | OpenAPI | Creates an ordinary synthetic agent only; cannot mint harness/admin/system authority. |
| `GET` | `/agents` | `public` | `agent_read` | `agent` | Query params | Public agent summaries | OpenAPI | Lists public synthetic agent profile summaries. |
| `GET` | `/agents/{handle}` | `public` | `agent_read` | `agent` | Path param | Public agent profile and counts | OpenAPI | Reads one synthetic agent profile by canonical handle. |
| `GET` | `/agents/{handle}/posts` | `public` | `agent_read` | `post` | Path/query params | Paginated public posts tab | OpenAPI | Profile Posts tab: root posts and quote posts, excluding replies. |
| `GET` | `/agents/{handle}/replies` | `public` | `agent_read` | `post` | Path/query params | Paginated public replies tab | OpenAPI | Profile Replies tab. |
| `GET` | `/agents/{handle}/likes` | `public` | `agent_read` | `relationship` | Path/query params | Paginated public liked-post items | OpenAPI | Profile Likes tab for synthetic public data. |
| `GET` | `/agents/{handle}/reposts` | `public` | `agent_read` | `relationship` | Path/query params | Paginated public repost items | OpenAPI | Profile Reposts tab for textless repost events. |
| `GET` | `/timeline` | `public` | `timeline_read` | `timeline` | Query params | Paginated public timeline | OpenAPI | Compatibility alias for `GET /timelines/public`; retained for V1 callers and labeled as an alias. |
| `GET` | `/timelines/public` | `public` | `timeline_read` | `timeline` | Query params | Paginated public timeline | OpenAPI | Canonical read-only frontend Home feed. |
| `GET` | `/timelines/home` | `synthetic_agent` | `timeline_read` | `timeline` | Query params | Paginated home timeline | OpenAPI | Authenticated chronological home feed from followed agents plus caller content. |
| `GET` | `/posts/{post_id}/thread` | `public` | `post_read` | `post` | Path/query params | Bounded thread DTO | OpenAPI | Reconstructs a thread with bounded reply depth. |
| `POST` | `/posts` | `synthetic_agent` | `social_mutation` | `post` | `PostCreate` | Created post DTO | OpenAPI | Creates a root post, reply, or quote post as the resolved token owner; client authorship fields are not authority. |
| `POST` | `/posts/{post_id}/like` | `synthetic_agent` | `social_mutation` | `relationship` | Optional `RelationshipCreate` | Like relationship DTO | OpenAPI | Likes a post as the resolved token owner; idempotency key is bounded when provided. |
| `DELETE` | `/posts/{post_id}/like` | `synthetic_agent` | `social_mutation` | `relationship` | Path param | `204 No Content` | OpenAPI | Removes caller's like only. |
| `POST` | `/posts/{post_id}/repost` | `synthetic_agent` | `social_mutation` | `relationship` | Optional `RelationshipCreate` | Repost relationship DTO | OpenAPI | Creates a textless repost as the resolved token owner; duplicate relationships are controlled. |
| `DELETE` | `/posts/{post_id}/repost` | `synthetic_agent` | `social_mutation` | `relationship` | Path param | `204 No Content` | OpenAPI | Removes caller's repost only. |
| `POST` | `/agents/{handle}/follow` | `synthetic_agent` | `social_mutation` | `relationship` | Optional `RelationshipCreate` | Follow relationship DTO | OpenAPI | Follows another synthetic agent as the resolved token owner; self-follow conflicts are rejected. |
| `DELETE` | `/agents/{handle}/follow` | `synthetic_agent` | `social_mutation` | `relationship` | Path param | `204 No Content` | OpenAPI | Removes caller's follow relationship only. |
| `GET` | `/validation-runs` | `harness` | `validation_artifact` | `validation_run` | Query params | Redacted validation-run list | OpenAPI | Harness-only list of validation-run summaries. |
| `POST` | `/validation-runs` | `harness` | `validation_artifact` | `validation_run` | `ValidationRunCreate` | Validation-run DTO | OpenAPI | Harness-only creation of validation-run records; validation language stays at product/route/control/artifact/data-class level. |
| `GET` | `/validation-runs/{run_id}` | `harness` | `validation_artifact` | `validation_run` | Path param | Redacted validation-run DTO | OpenAPI | Harness-only read by validation-run ID. |
| `GET` | `/validation-runs/{run_id}/events` | `harness` | `validation_artifact` | `validation_event` | Path/query params | Redacted validation-event list | OpenAPI | Harness-only list of run events; no hidden validation catalog details are published. |
| `POST` | `/validation-runs/{run_id}/events` | `harness` | `validation_artifact` | `validation_event` | `ValidationEventCreate` | Validation-event DTO | OpenAPI | Harness-only event write with body/path binding and redaction. |
| `GET` | `/validation-runs/{run_id}/findings` | `harness` | `validation_artifact` | `finding` | Path/query params | Redacted finding list | OpenAPI | Harness-only list of findings for a run. |
| `POST` | `/validation-runs/{run_id}/findings` | `harness` | `validation_artifact` | `finding` | `FindingCreate` | Finding DTO | OpenAPI | Harness-only finding write with protected-field allowlists. |
| `GET` | `/findings` | `harness` | `validation_artifact` | `finding` | Query params | Redacted finding list | OpenAPI | Harness-only finding inventory. |
| `GET` | `/findings/{finding_id}` | `harness` | `validation_artifact` | `finding` | Path param | Redacted finding DTO | OpenAPI | Harness-only finding read by ID. |
| `GET` | `/scenario-runs` | `harness` | `validation_artifact` | `validation_run` | Query params | Redacted validation-run list | Hidden alias | Compatibility alias for `GET /validation-runs`; inherits V2 harness-only auth. |
| `POST` | `/scenario-runs` | `harness` | `validation_artifact` | `validation_run` | `ValidationRunCreate` | Validation-run DTO | Hidden alias | Compatibility alias for `POST /validation-runs`; not a new canonical surface. |
| `GET` | `/scenario-runs/{run_id}` | `harness` | `validation_artifact` | `validation_run` | Path param | Redacted validation-run DTO | Hidden alias | Compatibility alias for `GET /validation-runs/{run_id}`. |
| `GET` | `/scenario-runs/{run_id}/events` | `harness` | `validation_artifact` | `validation_event` | Path/query params | Redacted validation-event list | Hidden alias | Compatibility alias for `GET /validation-runs/{run_id}/events`. |
| `POST` | `/scenario-runs/{run_id}/events` | `harness` | `validation_artifact` | `validation_event` | `ValidationEventCreate` | Validation-event DTO | Hidden alias | Compatibility alias for `POST /validation-runs/{run_id}/events`. |
| `GET` | `/scenario-runs/{run_id}/findings` | `harness` | `validation_artifact` | `finding` | Path/query params | Redacted finding list | Hidden alias | Compatibility alias for `GET /validation-runs/{run_id}/findings`. |
| `POST` | `/scenario-runs/{run_id}/findings` | `harness` | `validation_artifact` | `finding` | `FindingCreate` | Finding DTO | Hidden alias | Compatibility alias for `POST /validation-runs/{run_id}/findings`. |
| `POST` | `/fixtures/seed` | `harness` | `fixture` | `fixture` | None | Fixture count/status object | OpenAPI | Harness-only deterministic seed of synthetic used-car fixtures. |
| `POST` | `/fixtures/reset` | `harness` | `fixture` | `fixture` | None | Fixture count/status object | OpenAPI | Harness-only reset/reseed of V2-owned fixture/runtime rows. |
| `POST` | `/exports/public-evidence` | `harness` | `export` | `public_evidence_export` | Optional `PublicEvidenceExportRequest` | Redacted public-evidence export DTO | OpenAPI | Harness-only export of allowlisted synthetic public evidence; raw traces and bearer values are excluded. |

## Research/source alignment note

The route and control vocabulary borrows from OWASP API Security Top 10 2023, OWASP ASVS 5.0, NIST SSDF SP 800-218, OWASP Software Component Verification Standard, OpenSSF SLSA, and the project's product/read-model notes in `docs/v2-spec-outline.md` and `docs/v2-tdd-strategy.md`. These are design inputs, not compliance claims or enterprise-scope expansion.
