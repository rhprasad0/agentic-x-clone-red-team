# THREAT_MODEL

This threat model is a starting point for a synthetic agent-native social feed and single-runner red-team harness. It will be revised as implementation artifacts exist. The reviewed V1 plan lives in [docs/v1-spec-outline.md](docs/v1-spec-outline.md).

## Boundaries

- All agents and content are synthetic.
- No scraped platform data, real user records, private transcripts, real listings, or production credentials are allowed.
- Public examples must use fictional handles, placeholder keys, example domains, and redacted outputs.
- The repo should not imply that a live platform is deployed, hardened, or operating as a real marketplace.
- The V1 app is a KarpathyTalk-minimal agent-facing create/read environment with a read-only observability UI, not a human-grade social network and not a production service.
- The V1 fixture world is fictional used-car discourse. It is product texture, not a buying-advice service.

## Assets

- Synthetic agent records, personas, handles, and fictional profile text.
- Posts, replies, threads, timelines, and profile data.
- Scenario run records, redacted scenario events, and redacted evidence summaries.
- Single-runner red-team findings, scenario outputs, and regression results.
- Local service configuration, fixture-scoped bearer-token mappings, and reset manifests.

## Threats And Planned Controls

| Area | Threat | Planned Controls |
| --- | --- | --- |
| Synthetic identity / authority resolution | Synthetic agent attempts to create posts/replies attributed to another agent by tampering with IDs, body fields, handles, or metadata; client-provided role/authority claims used to authorize mutation | Server-side bearer-token-to-authority resolution; server-assigned authorship; field allowlists; deny-by-default route tests; client identity claims never authorize mutation |
| Object-level authorization | IDOR-class access to scenario runs, events, findings, or per-agent data through ID swaps or body overrides | Object-level authorization checks in the trusted service layer; route-level authorization tests; stable synthetic fixtures; mass-assignment resistance |
| Harness boundary | Non-harness actor writes or alters scenario events/findings, or writes them against the wrong scenario run | Function-level authorization for harness-only routes; separate fixture-scoped harness token; bind events/findings to the intended scenario run; append-only or change-tracked evidence |
| Read-only browser posture | UI assumed to be a security boundary; browser session/cookie/origin trust used to authorize mutation | Frontend is read-only; mutation routes require fixture-scoped bearer tokens regardless of UI; CORS scoped to local development origins; no V1 browser sessions or CSRF surface |
| Content abuse and resource exhaustion | Synthetic spam, reply storms, oversized inputs, or unbounded queries | Deterministic abuse fixtures; documented input/page-size limits; structured event logs; explicit residual-risk notes for deferred rate limits |
| Data leakage in public artifacts | Logs, screenshots, fixtures, findings, or event summaries expose secrets, local paths, real names, or real platform data | Public-safety scanner; redacted event summaries; synthetic-only seed data; raw/debug traces stay local and ignored |
| Replay integrity | Non-deterministic timelines, threads, or scenario outputs make findings impossible to retest | Deterministic ordering; seeded fixtures; stable scenario IDs; normalized snapshot comparisons; regression evidence required for closure |
| Audit gaps | Scenario actions or findings cannot be traced back to inputs and outputs | Structured event log with actor, target, decision, redaction status, and safe summary; required finding-to-regression-or-residual-risk links |
| Scope creep | Project drifts into a fake consumer social network, real marketplace, production-deployment claim, or comprehensive-pentest claim instead of the agent hardening loop | Explicit V1 non-goals; minimal create/read API; read-only UI; scope-control scenario; later-scope deployment appendix kept separate from V1 evidence |

## Abuse Cases To Exercise

- Synthetic agent attempts to create a post or reply attributed to another synthetic agent through identifier, body, or handle tampering.
- Non-harness actor attempts to write or alter scenario events/findings, or attempts to bind a write to the wrong scenario run.
- Synthetic agent attempts to authorize mutation through client-provided `agent_id`, role, or metadata instead of the server-resolved bearer token.
- A reviewer probes the read-only UI for any state-changing control or browser-trusted mutation path.
- Attack agent creates repetitive synthetic spam or reply storms to test event logging and rate-limit decisions.
- Scenario run exports include a fake secret-like token and must be caught or redacted by public-safety checks.
- Re-running a seeded scenario produces divergent timeline/thread evidence without explicit normalization.

## V1 Adversary Boundary

The first harness uses one black-box `SingleRedTeamAgent` with multiple scenario modes. It receives only the base URL, allowed starting credentials or public entry points, and the scenario objective. It does not receive source code, database access, private docs, or an OpenAPI schema unless the app intentionally exposes that information publicly. This keeps the benchmark honest and shippable: it demonstrates a hardening loop without implying that the app survived a broad multi-agent pentest.

## Future-Scope LLM/Agent Risks

V1 has no LLM consumer of feed content (no evaluator/summarizer agent, no model-provider integration, no prompt-template hardening, no LLM output validation, no provider metadata capture). Indirect prompt injection via posts/profiles, system-prompt leakage, improper output handling, excessive agency, and provider failure-mode handling are recognized as later-scope risk classes that become relevant only if a future scope introduces such an LLM consumer. They are documented in [SECURITY_REQUIREMENTS.md](SECURITY_REQUIREMENTS.md) as research notes, not V1 acceptance criteria.

## Residual Risk Notes

Synthetic coverage is useful for repeatable hardening, but it does not prove real-world safety. Any future deployment would need separate review for authentication, privacy, infrastructure, dependency management, abuse monitoring, incident response, vulnerability disclosure, cost controls, URL ingestion or browser-agent behavior if added, vector/RAG surfaces if added, and external testing.
