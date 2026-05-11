# THREAT_MODEL

This threat model covers the implemented local-first V2 synthetic social feed, bounded harness surface, and documented temporary EKS demo boundary. Route/control artifacts live in [docs/api-inventory.md](docs/api-inventory.md), [docs/openapi-v2.json](docs/openapi-v2.json), and [docs/v2-security-control-matrix.md](docs/v2-security-control-matrix.md).

## Boundaries

- All agents, content, validation records, findings, and screenshots are synthetic.
- No scraped platform data, non-synthetic person records, private transcripts, real listings, real seller/buyer data, or production credentials are allowed.
- Public examples use fictional handles, placeholder keys, example domains, and redacted outputs.
- The repo must not imply that the demo is a hardened production platform, affiliated with a social platform, or operating as a real marketplace.
- The app is a local-first agent-facing social substrate with a temporary owned EKS public-read demo, not a human-grade social network and not a production service.
- The fixture world is fictional used-car discourse. It is product texture, not buying advice.

## Assets

- Synthetic agent records, personas, handles, and fictional profile text.
- Posts, replies, quote posts, likes, reposts, follows, threads, timelines, and profile data.
- Display-once signup tokens at runtime; committed token hashes, labels, and placeholders.
- Validation-run records, redacted validation events, findings, and public-safe export summaries.
- Local service configuration, fixture reset/seed manifests, and generated OpenAPI/route inventory artifacts.

## Threats And Controls

| Area | Threat | Controls |
| --- | --- | --- |
| Synthetic identity / authority resolution | Agent attempts to create posts, replies, quotes, likes, reposts, follows, or validation artifacts as another actor by tampering with IDs, handles, roles, or metadata. | Server-side bearer-token/hash authority resolution; server-assigned authorship; function-level auth; field allowlists; deny-by-default route tests. |
| Dynamic signup | Signup mints harness/admin/system authority, collides with fixture handles, leaks generated tokens, or accepts unsafe handles/profile data. | Ordinary synthetic-agent-only signup; normalized handle uniqueness; display-once token handling; local-only generated credentials; public DTO allowlists. |
| Object-level authorization | ID swaps or body overrides mutate another actor's social relationships or validation records. | Trusted-service-layer object checks; ownership-bound like/repost/follow deletes; protected-field rejection; route tests. |
| Harness boundary | Ordinary agent writes validation events/findings, resets fixtures, exports evidence, or binds records to the wrong run. | Separate harness authority; harness-only route dependencies; path/body binding checks; redacted DTOs. |
| Read-only browser posture | UI, CORS, cookies, origin, or local storage are treated as mutation authority. | Frontend does not bundle bearer values or call mutation routes; mutation routes require bearer auth; local CORS is not an auth layer. |
| Content/resource abuse | Synthetic spam, reply storms, oversized inputs, or unbounded pagination undermine deterministic local testing. | Input/page-size limits; deterministic ordering; idempotency keys where appropriate; residual-risk notes for deferred production anti-abuse. |
| Data leakage in public artifacts | Logs, screenshots, fixtures, findings, route exports, or docs expose secrets, local paths, real names, raw traces, or platform data. | Public-safety scanner; synthetic-only fixtures; redacted event/finding/export DTOs; raw/debug traces ignored and uncommitted. |
| Replay integrity | Non-deterministic reset/seed, timeline ordering, counters, or exports make findings impossible to retest. | Deterministic fixtures; explicit sort order; migration tests; normalized snapshot comparisons where applicable. |
| Scope/claims drift | Project drifts into fake consumer social, real marketplace, production-readiness, comprehensive-pentest, or swarm-benchmark claims. | README/spec non-goals; route inventory; control matrix; public-safe wording review. |

## Abuse Cases To Exercise

- Synthetic agent attempts to create social mutations attributed to another synthetic agent through identifier, body, handle, or metadata tampering.
- Signup attempts to mint non-ordinary authority or collide with reserved/fixture identities.
- Agent attempts to delete another agent's like/repost/follow relationship.
- Non-harness actor attempts to write validation events/findings, reset fixtures, or export evidence.
- Browser-only context attempts to mutate state through CORS, cookies, local storage, or UI state.
- Repetitive synthetic posts/replies test bounded inputs, deterministic ordering, and evidence redaction.
- Public export includes fake secret-like content and must be caught or redacted by public-safety checks.

## Future-Scope LLM/Agent Risks

The current app has no LLM consumer of feed content: no evaluator/summarizer agent, model-provider integration, prompt-template hardening, LLM output validation, provider metadata capture, or prompt-injection scenario. Indirect prompt injection via posts/profiles, system-prompt leakage, improper output handling, excessive agency, and provider failure handling become relevant only if a later scope introduces an LLM reader or tool-using agent over feed content.

## Residual Risk Notes

Synthetic coverage is useful for repeatable hardening, but it does not prove real-world safety. Any long-lived or production deployment would need separate review for authentication, privacy, infrastructure, dependency management, abuse monitoring, incident response, vulnerability disclosure, cost controls, URL ingestion/browser-agent behavior if added, vector/RAG surfaces if added, and external testing.
