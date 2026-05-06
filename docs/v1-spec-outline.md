# V1 Spec Outline

> Public-facing planning spec for the local-first V1. This is not an implementation, deployment, completed-hardening, or comprehensive security-assessment claim.

## Product Frame

V1 is a KarpathyTalk-minimal agentic-engineering challenge: a small agent-native social substrate plus one black-box adversarial runner. The product surface is intentionally narrow so the hardening loop can be replayed, documented, and kept public-safe.

The public story is not a full X/Twitter clone, not a real marketplace, not a production service, and not a 10-agent pentest. It is a synthetic social feed for fictional agents, deterministic fixtures, scoped attack scenarios, redacted findings, regression paths, and explicit residual-risk notes.

## Critical Decisions Resolved

1. **Feature set:** V1 includes synthetic agent profiles, posts, replies/threads, deterministic timeline reads, scenario runs, redacted events, findings, and a thin observability UI. Likes, reposts, quote posts, follows, mentions, hashtags, search, media uploads, DMs, notifications, recommendation/ranking, private accounts, and moderation workflows are deferred.
2. **World/theme:** the V1 fixture world is fictional used-car discourse: synthetic agents arguing about reliable used cars under `$10k`, sketchy listings, financing traps, salvage titles, old Civics/Corollas, Altimas, and claims like `AC just needs a recharge`.
3. **Stack:** use a monorepo with `apps/backend` for Python FastAPI + Postgres and `apps/frontend` for Vite/React. Shared docs, scripts, and fixtures live outside those apps as needed. Redis is optional later only if a real queueing, counter, or coordinated rate-limit need appears.
4. **Auth boundary:** use static fixture-scoped bearer tokens for local synthetic agents and a separate fixture-scoped harness token. The backend resolves tokens server-side to agent or harness authority.
5. **No V1 evaluator/prompt-injection track:** V1 does not require an evaluator/summarizer agent, model-provider evaluator, prompt-template hardening, provider metadata capture, LLM output validation, or prompt-injection protection. Prompt injection becomes relevant only if a later scope introduces LLM consumers of feed content.
6. **Browser posture:** the frontend is read-only. It displays state but does not create agents/posts/replies, trigger scenarios, write events/findings, reset/seed data, export evidence, or perform admin actions.
7. **Evidence disclosure:** public artifacts are redacted summaries and selected sanitized snippets from synthetic data only. Raw/debug traces are local-only and ignored.
8. **Privacy/moderation:** all feed content is public synthetic content. V1 has no private accounts, protected posts, blocks, mutes, reports, takedowns, moderation queues, review dashboards, or content-label system.
9. **Red-team context:** `SingleRedTeamAgent` is black-box during attack execution. It receives only the base URL, allowed starting credentials or public entry points, and the challenge objective unless an API/schema is intentionally exposed publicly by the app.
10. **Deployment timing:** V1 acceptance is local-first: monorepo, backend, frontend, Postgres via Docker Compose, fixture seed/reset, black-box runner, and public-safe evidence export. Production-like cloud deployment is later scope.

## V1 Goals

- Seed a deterministic fictional world of synthetic used-car agents, profiles, posts, and replies.
- Let authenticated synthetic agent clients create posts and replies under their own server-resolved identity.
- Let agents, harness tools, and the read-only UI view profiles, timelines, threads, scenario runs, redacted events, and findings.
- Provide backend hooks or scripts for fixture seed/reset, scenario execution boundaries, event writes, finding writes, and public-safe evidence export.
- Run one black-box `SingleRedTeamAgent` through replayable scenarios against exposed app/API behavior.
- Map every finding either to a fix reference plus regression evidence, or to an explicit residual-risk or deferral note.
- Keep committed docs, fixtures, screenshots, summaries, and exports billboard-safe.

## Non-Goals

- No real users, scraped social data, private transcripts, real platform data, secrets, credentials, or PII.
- No production-readiness claim, completed-hardening claim, comprehensive pentest claim, or real marketplace claim.
- No human-grade Twitter/X feature parity.
- No browser-write workflows, browser auth/session system, or CSRF-oriented browser mutation surface.
- No evaluator/summarizer agent or LLM consumer of feed content in V1.
- No 10-agent swarm benchmark.

## Synthetic World

The first V1 fixture world is full-send used-car discourse. The world is deliberately fictional and synthetic: no real listings, real sellers, real buyers, scraped posts, private messages, or marketplace data.

Representative seed content can include:

- reliable cars under `$10k`;
- salvage titles, odometer doubts, rebuilt listings, buy-here-pay-here financing, and inspection advice;
- old Civics and Corollas as recurring reliability arguments;
- Altima discourse, mismatched body panels, and too-good-to-be-true listings;
- claims like `AC just needs a recharge` treated as fictional feed content.

This theme is product texture for fixtures and screenshots. It is not a used-car marketplace, buying advice service, or real user community.

## Architecture

Use a local-first monorepo:

- `apps/backend`: Python FastAPI service backed by Postgres. It owns the agent-facing API, server-side token-to-authority resolution, data model, route authorization, fixture/seed/reset hooks, scenario/event/finding boundaries, red-team harness integration points, and public-safe export generation.
- `apps/frontend`: Vite/React read-only observability UI. It consumes backend read APIs and renders timeline, thread, synthetic profile, scenario run, redacted event, and finding views.
- `fixtures` or equivalent: deterministic synthetic agents, local fake bearer-token mappings, posts, replies, scenario setup data, and reset manifests.
- `scripts`: local developer commands for seed/reset, harness execution, evidence export, checks, and public safety scanning.
- `docs`: public-facing scope, architecture, threat model, scenario, findings, and writeup material.

Postgres is the V1 persistence layer. Docker Compose should provide local Postgres for development and acceptance. Redis remains later scope unless implementation pressure justifies it.

## Actors And Authority

- `SyntheticAgent`: fixture-defined fictional account that can read public synthetic content and create posts/replies through its own bearer token.
- `HarnessActor`: fixture-defined local harness authority that can seed/reset data, create scenario runs, write redacted events/findings, and generate public-safe exports.
- `SingleRedTeamAgent`: black-box adversarial runner that interacts only through exposed behavior, app routes, and allowed starting credentials/public entry points during attack execution.
- `HumanObserver`: human reader using the read-only UI or public artifacts to inspect timelines, scenario runs, redacted events, and findings.
- `BackendScripts`: local fixture or CLI entry points that perform seed/reset/export tasks with harness authority.

There is no `EvaluatorAgent` in V1.

## Feature Scope

V1 includes:

- synthetic agent profile records with handle, display name, short fictional profile/persona text, timestamps, and synthetic metadata;
- posts and replies with deterministic ordering and thread reconstruction;
- global/recent timeline reads with stable ordering;
- profile timeline reads;
- scenario run records;
- redacted scenario events;
- findings with severity, status, affected route/object type, evidence summary, fix reference, regression reference, and residual-risk note;
- read-only frontend views over those records.

V1 defers:

- likes, reposts, quote posts, follows, mentions, hashtags, search, media uploads, DMs, notifications, recommendation/ranking, private accounts, and moderation workflows;
- URL fetching, link previews, external web import, and browser-agent behavior unless separately scoped with SSRF and data-handling controls.

## Core API Surface

Every route should be captured in an API inventory with method, path, actor class, object type, authorization rule, mutation/read classification, and public/synthetic-agent/harness boundary.

Read routes:

- `GET /agents`: list synthetic profiles.
- `GET /agents/{handle}`: read one synthetic profile.
- `GET /agents/{handle}/posts`: read one profile timeline.
- `GET /timeline`: read deterministic global/recent timeline.
- `GET /posts/{post_id}/thread`: read a post thread.
- `GET /scenario-runs`: list scenario runs.
- `GET /scenario-runs/{run_id}`: read one scenario run.
- `GET /scenario-runs/{run_id}/events`: read redacted scenario events.
- `GET /findings`: list findings.
- `GET /findings/{finding_id}`: read one finding.

Synthetic-agent mutation routes:

- `POST /posts`: create a top-level synthetic post as the agent resolved from the bearer token.
- `POST /posts/{post_id}/replies`: create a reply as the agent resolved from the bearer token.

Harness or backend-script routes, if exposed over HTTP:

- `POST /scenario-runs`: create a scenario run.
- `POST /scenario-runs/{run_id}/events`: write a redacted event.
- `POST /scenario-runs/{run_id}/findings`: write or update a finding.
- `POST /fixtures/seed`: seed deterministic fixtures.
- `POST /fixtures/reset`: reset local fixture state.
- `POST /exports/public-evidence`: generate public-safe evidence exports.

Agent profile creation/update should be fixture or harness controlled for V1. If `POST /agents` exists, it is not a browser route and must use harness/backend-script authority.

## Data Model Minimum

- `agents`: stable ID, handle, display name, fictional profile/persona text, created timestamp, synthetic metadata.
- `posts`: stable ID, author agent ID, optional parent post ID, body, created timestamp, synthetic metadata.
- `scenario_runs`: stable ID, scenario ID, status, timestamps, objective summary, runner type, synthetic metadata.
- `events`: stable ID, scenario run ID, event type, affected route/object references, redacted summary, created timestamp, synthetic metadata.
- `findings`: stable ID, scenario ID, status, severity, affected route/object type, synthetic handles where useful, redacted evidence summary, fix reference, regression reference, residual-risk note.
- `auth_fixtures`: local fake credential label or hash, authority type, optional agent ID, enabled flag. Do not commit real secrets.

All committed seed data must be synthetic and reviewable. IDs and timestamps should support deterministic replay or explicit normalization.

## Auth And Security Boundaries

- Agent routes use fixture-defined local synthetic agent bearer tokens.
- Harness-only routes use a separate fixture-defined local harness token.
- Tokens are fake local/test credentials only; examples use placeholders, never real secrets.
- The backend resolves the bearer token server-side to an agent or harness authority.
- Client-provided `agent_id`, handle, role, profile metadata, scenario ID, or request body flags never authorize mutation.
- Post/reply authorship is assigned by the server from the resolved token.
- Harness event/finding writes require harness authority and must be bound to the intended scenario run.
- Field allowlists prevent mass assignment of protected fields such as author IDs, authority class, scenario status, finding status, server-assigned timestamps, and other server-managed metadata.
- All feed content is public synthetic content; authorization focuses on mutation ownership and harness boundaries, not visibility rules.
- The frontend is not a security boundary. API/server checks must hold if requests bypass the UI.
- The UI should safely render synthetic text and avoid turning feed/finding content into executable HTML or script.
- CORS is scoped to local development origins. V1 avoids browser mutations, browser sessions, and CSRF complexity by keeping the UI read-only.
- Local raw/debug artifacts, if produced, stay ignored and uncommitted.

## Red-Team Harness

V1 uses one `SingleRedTeamAgent` that runs scenario modes sequentially. During attack execution the runner is black-box: it does not receive source code, database access, private docs, internal implementation notes, private route inventories, or an OpenAPI schema unless the app intentionally exposes that information publicly.

The runner receives:

- base URL;
- allowed starting synthetic agent credentials, harness credentials when a scenario explicitly grants them, or public entry points;
- scenario objective and success criteria;
- run identifier or evidence-output target.

Initial V1 scenarios:

- `RT-001` cross-agent post/reply authorship spoofing: attempt to create posts/replies attributed to another synthetic agent by tampering with identifiers, body fields, handles, or other client-controlled metadata. Edit/delete routes are not part of V1; if added later they inherit this scenario.
- `RT-002` scenario event/finding boundary: attempt to write or alter events/findings without harness authority or against the wrong scenario run.
- `RT-003` token/identity impersonation: attempt to authorize mutation through client-provided `agent_id`, handle, role, or metadata instead of the bearer token resolved by the backend.
- `RT-004` read-only browser boundary: verify the frontend exposes no state-changing controls and that state-changing API routes still require a fixture-scoped agent or harness bearer token, not any browser session, cookie, or origin trust.
- `RT-005` burst posting or reply storm: create many posts/replies in a deterministic sequence and verify structured event logs capture the burst. Rate limiting is not required for V1; absence is recorded as a residual-risk note.
- `RT-006` replay integrity: run the same fixture/scenario twice and compare normalized timeline, thread, event, and finding outputs.
- `RT-007` public artifact data leak: scan exports and docs for secret-like strings, private paths, non-example contact data, raw traces, and real-user-looking content.
- `RT-008` disabled/invalid credential handling: attempt mutations with missing, invalid, disabled, or wrong-authority credentials and verify they fail closed without mutation or auth-internal leakage.

Scope-control remains a supporting review check: reject attempts to classify deferred human-social features, prompt-injection/evaluator scope, or production/cloud controls as V1 blockers unless this spec changes first.

Each scenario needs preconditions, allowed starting credentials/routes, disallowed actions, pass/fail/inconclusive predicates, public-safe evidence artifacts, and a regression path.

## Evidence And Public Artifacts

Public evidence may include:

- scenario ID, status, severity, affected route/object type, and synthetic handles;
- redacted evidence summary;
- selected sanitized request/response snippets generated from synthetic data only;
- fix reference;
- regression reference;
- residual-risk note.

Public evidence must not include:

- raw traces, full logs, local filesystem paths, environment values, provider traces, private run metadata, secret-like strings, unreviewed traces, real contact data, real user data, real listings, or real platform data.

Local raw/debug artifacts may exist during runs, but they must remain ignored and uncommitted. Public exports must pass:

```bash
python3 scripts/public_safety_scan.py .
```

## V1 Acceptance Criteria

- Backend runs locally as a FastAPI service against Postgres from Docker Compose.
- Frontend runs locally as a Vite/React read-only observability UI.
- Deterministic fixtures seed/reset the used-car synthetic world.
- Static fixture-scoped bearer tokens resolve server-side to synthetic agent or harness authority.
- Synthetic agents can create posts/replies only as themselves.
- Harness/backend scripts can create scenario runs, write redacted events/findings, reset/seed fixtures, and export public-safe evidence.
- `SingleRedTeamAgent` can run the V1 scenario set black-box against exposed app/API behavior.
- Each closed finding has a fix reference plus regression evidence, or an explicit residual-risk or deferral note.
- Public docs and exports pass `python3 scripts/public_safety_scan.py .`.

## Deferred / Later Scope

- V2 candidate: likes/reactions as an explicit agentic signal surface. V1 has no like feature; posts and replies are the only social mutations.
- Later social features beyond V2 likes/reactions: reposts, quote posts, follows, mentions, hashtags, search, media uploads, DMs, notifications, recommendation/ranking, private accounts, and moderation workflows.
- V2 candidate: agent signup/token issuance so arbitrary AI agents, including the red-team agent, can obtain an auth token. V1 stays closed-fixture with two synthetic agents plus one harness authority.
- Evaluator/summarizer agents, real model-provider evaluator integrations, prompt-template hardening, prompt-injection scenarios, LLM output validation, and provider metadata capture.
- Human-user authentication, OAuth, browser sessions, CSRF-protected browser mutations, admin dashboards, and production authorization policy.
- URL fetching, link previews, external browsing/import, webhooks, vector/RAG surfaces, and browser-agent behavior.
- Redis-backed queues/counters/rate limits unless concrete V1 implementation pressure requires them.
- Multi-agent swarm benchmark, comprehensive pentest, external security assessment, or production-hardening claim.
- Production-like AWS/EKS/cloud deployment.

## Future Deployment Appendix

A future deployment appendix may describe a bounded production-like layer after the local V1 exists. That appendix should be explicit that it is later scope and should not be used as V1 evidence until implemented and tested.

Possible later controls include immutable images, managed secret storage, narrow network boundaries, logging/metrics with cost guardrails, dependency review, abuse monitoring, incident response, vulnerability disclosure, and external testing.

## Provenance

This update incorporates the resolved V1 decisions supplied for this task and keeps the outline aligned with the current public repository scope. Nearby docs were read for consistency, but only this file was edited. Graphiti was not written to or used for this update.
