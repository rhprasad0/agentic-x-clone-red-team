# SECURITY_REQUIREMENTS

This document defines the current public security requirements for the implemented local-first V2 synthetic social feed and bounded harness surface. It is not a compliance claim and not a broad hardening claim.

Route/control artifacts:

- [docs/api-inventory.md](docs/api-inventory.md)
- [docs/openapi-v2.json](docs/openapi-v2.json)
- [docs/v2-security-control-matrix.md](docs/v2-security-control-matrix.md)

## Purpose

The project has two top-level security goals:

### R0.1 Public Credibility

Public artifacts should make a technical recruiter, hiring manager, or AI/security peer reasonably conclude that the builder understands credible security engineering for agentic systems.

That means the repo should show:

- scoped assumptions and non-goals;
- concrete route/control documentation;
- threat classes mapped to implementation evidence;
- redacted evidence expectations;
- finding lifecycle with regression and residual-risk handling;
- public-safe examples, fixtures, logs, and writeups;
- no claims of deployed-service readiness or comprehensive hardening before evidence exists.

### R0.2 Anticipatory Coverage

A future red-team/hardening pass should discover bugs inside anticipated risk classes, not obvious risk categories that were never modeled.

A good final finding looks like:

> `SR-101` anticipated client-side authorship spoofing, but implementation accepted a body-provided `agent_id` instead of resolving the bearer token server-side.

A bad final finding looks like:

> Nobody realized a synthetic agent could claim another handle in the request body.

Bugs are allowed. Security clown-nose moments are not the goal.

## In Scope

- Synthetic agents, handles, personas, posts, replies, quote posts, likes, reposts, follows, profiles, timelines, threads, validation runs, redacted events, and findings.
- Local FastAPI/Postgres backend and Vite/React read-only observability UI.
- Dynamic synthetic signup and display-once token issuance for ordinary synthetic agents.
- Static fixture-scoped tokens for deterministic agents and a separate local harness authority.
- Harness-only fixture reset/seed, validation-record, finding, and public-evidence export routes.
- Deterministic fictional used-car fixtures and replayable local validation paths.
- Public-safe findings, redacted event summaries, and regression evidence.

## Out of Scope

- Non-synthetic people, real X/Twitter data, scraped content, private transcripts, real listings, production credentials, or real platform claims.
- Human-grade social network feature parity; mentions, hashtags, search, media uploads, DMs, notifications, recommendation/ranking, private accounts, blocks/mutes/reports, and moderation workflows.
- Browser sessions, browser-driven mutations, CSRF surface, password reset, OAuth, admin dashboards, payments, ads, or contact import.
- Production deployment, AWS/EKS deployment, or claims of production hardening.
- Multi-agent swarm benchmark, comprehensive penetration test, or external security assessment claim.
- Evaluator/summarizer agents, model-provider integrations, prompt-template hardening, prompt-injection scenarios, LLM output validation, provider metadata capture, and moderation/content-label systems until a later scope introduces an LLM consumer of feed content.

## Requirement Language

- **MUST**: required for current local security credibility.
- **SHOULD**: expected unless explicitly deferred with residual-risk notes.
- **MAY**: acceptable future hardening or optional implementation.

## Finding Classification

| Class | Meaning | Required response |
| --- | --- | --- |
| `anticipated-risk/failed-implementation` | The risk class was modeled, but code/config failed the requirement. | Fix or document residual risk; add regression evidence. |
| `anticipated-risk/incomplete-requirement` | The risk class was modeled, but the requirement was underspecified. | Update requirements, then fix/test or document residual risk. |
| `unanticipated-risk-class` | The pass found a major category not represented here or in the threat model. | Update threat model and requirements before claiming closure. |
| `documented-residual-risk` | The issue is known, bounded, and intentionally deferred. | Link to residual-risk note and future trigger. |
| `out-of-scope` | The issue belongs to a later deployment/product/security layer. | Confirm it is listed in non-goals or later-scope docs. |

## Requirements

### SR-000 Public-safe synthetic boundary

**Requirement:** All committed data, examples, screenshots, logs, fixtures, findings, and docs MUST be synthetic and billboard-safe.

**Evidence expected:** Public-safety scanner, synthetic fixtures, `.env.example` placeholders, docs language checks.

### SR-001 Claims must match evidence

**Requirement:** Public docs MUST distinguish implemented local behavior, tested checks, planned validation, fixed findings, and residual risk.

**Evidence expected:** README/spec/threat-model wording review; stale-phrase search; public writeup review.

### SR-101 Server-side synthetic identity

**Requirement:** Synthetic agent identity MUST be resolved server-side from the bearer token/token hash. Client-provided handles, IDs, roles, or body metadata MUST NOT authorize mutation. Post/reply/quote authorship and social relationships MUST be assigned to the resolved token owner.

**Evidence expected:** Route tests for valid actor context, spoofed actor IDs/handles/roles, missing actor context, and protected-field attempts.

### SR-102 Object-level authorization

**Requirement:** Any route that reads or mutates an object by ID MUST enforce object-level authorization in the trusted service layer where the object is not public-read.

**Evidence expected:** Deny-by-default tests for cross-agent mutations; success tests for authorized access; negative tests that mutate IDs in path/query/body.

### SR-103 Harness-only authority

**Requirement:** Fixture reset/seed, validation-run creation, validation-event writes, finding writes, and public-evidence export MUST require explicit harness authority.

**Evidence expected:** Tests where ordinary synthetic agents attempt harness-only operations; route inventory of privileged functions.

### SR-104 Field/property allowlists

**Requirement:** API write schemas MUST allowlist writable fields and reject or ignore protected fields such as author IDs, validation-run IDs, status, severity, fix refs, regression refs, token hashes, authority type, and timestamps unless the actor is explicitly authorized.

**Evidence expected:** Schema tests with extra protected fields; database assertions that protected fields were not changed.

### SR-105 Route inventory and OpenAPI posture

**Requirement:** The repo MUST maintain a route/API inventory for create/read/export/reset/harness endpoints, allowed actor classes, object types, authorization checks, schema/debug posture, compatibility aliases, and route class.

**Evidence expected:** [docs/api-inventory.md](docs/api-inventory.md), [docs/openapi-v2.json](docs/openapi-v2.json), and tests or review when routes are added.

### SR-106 Signup cannot mint special authority

**Requirement:** `POST /agents/signup` MUST create ordinary synthetic agents only. It MUST NOT mint harness, admin, system, verified, moderator, or special-purpose authority.

**Evidence expected:** Signup tests for reserved roles/fields, handle normalization, duplicate handles, unsafe lengths, and display-once token behavior.

### SR-107 Token handling and redaction

**Requirement:** Runtime bearer values MUST stay local-only. Generated signup tokens are display-once. Public DTOs, logs, docs, exports, fixtures, and screenshots MUST NOT expose raw bearer values or token hashes.

**Evidence expected:** Public-safety scanner, redacted DTO tests, export allowlists, and docs review.

### SR-108 Read-only browser boundary

**Requirement:** Browser code MUST NOT store bearer credentials or call mutation routes. Mutation APIs remain backend/local/API scoped and require bearer authority independent of CORS or origin.

**Evidence expected:** Frontend tests/source review for no mutation fetches; CORS/header tests; route auth tests.

### SR-109 Deterministic replay and idempotency

**Requirement:** Fixture reset/seed, chronological timelines, profile tabs, threads, counts, and optional idempotency keys SHOULD produce stable, reviewable behavior or document unavoidable nondeterminism.

**Evidence expected:** Reset/seed tests, migration preservation tests, deterministic ordering tests, and idempotency tests.

### SR-110 Public evidence export allowlists

**Requirement:** Public-evidence exports MUST include only allowlisted synthetic summaries and metadata classes. They MUST exclude bearer values, token hashes, raw traces, private paths, unredacted request bodies, and hidden validation details.

**Evidence expected:** Export tests, public-safety scan over generated exports, and manual review before staging.

### SR-111 No external fetch/data-ingestion surface

**Requirement:** The backend SHOULD NOT fetch agent-supplied URLs, generate link previews, follow webhooks, import remote social content, or ingest external marketplace data. If added later, that scope requires SSRF, redirect, content-type, size, timeout, credential-forwarding, and data-handling controls.

**Evidence expected:** Route inventory review and dependency/code search.

### SR-112 Local-first infrastructure boundary

**Requirement:** Redis, AWS/EKS, managed secrets, WAFs, production logging, and cost guardrails MAY be later credibility layers but MUST NOT be implied as current security evidence until implemented.

**Evidence expected:** README/spec/deployment docs avoid production-readiness claims.

## Minimum Evidence Gates

Before calling a local security/hardening pass complete, the repo SHOULD have:

- public-safety scan passing for the repo and any generated public exports;
- `git diff --check` passing;
- route inventory current with implementation;
- backend auth/authorization/validation tests passing;
- frontend read-only tests passing;
- findings linked to fix refs plus regression evidence or residual-risk notes;
- public writeup language reviewed against [README.md](README.md), [SPEC.md](SPEC.md), and [THREAT_MODEL.md](THREAT_MODEL.md).

## Unsafe Public Claims

Do not say:

- “Deployed production service.”
- “Comprehensive pentest.”
- “Multi-agent swarm benchmark.”
- “Real users” or “real Twitter/X data.”
- “Fully secure” or “hardened against real-world abuse.”
- “Marketplace” in a way that implies real listings, sellers, or buyers.

Prefer:

- “local-first synthetic challenge”;
- “fictional used-car fixture world”;
- “bounded single-runner red-team/hardening surface”;
- “public-safe route/control evidence”;
- “read-only observability frontend.”
