# SECURITY_REQUIREMENTS

This document defines security requirements for a synthetic agent-native social feed and a single-runner red-team harness. It is written before the app and harness exist so implementation, tests, findings, and public claims can be traced back to a coherent security model instead of reverse-engineered after the demo works.

The reviewed V1 plan lives in [docs/v1-spec-outline.md](docs/v1-spec-outline.md) and is the canonical source for V1 scope decisions. V2 route/control artifacts now live in [docs/api-inventory.md](docs/api-inventory.md), [docs/openapi-v2.json](docs/openapi-v2.json), and [docs/v2-security-control-matrix.md](docs/v2-security-control-matrix.md). V1 has no LLM consumer of feed content (no evaluator/summarizer agent, no model-provider integration, no prompt-template hardening, no LLM output validation, no provider metadata capture). LLM/prompt-injection material in this document is preserved as future/later-scope research; it is not a V1 MUST or a mapped V1 scenario.

## Purpose

The project has two top-level security goals:

### R0.1 Public Credibility

Public artifacts MUST make a technical recruiter, hiring manager, or AI/security peer reasonably conclude that the builder understands credible security engineering for agentic systems.

That means the repo should show:

- scoped assumptions and non-goals;
- concrete security requirements;
- threat classes mapped to scenarios;
- evidence expectations before implementation;
- a finding lifecycle with regression and residual-risk handling;
- public-safe examples, fixtures, logs, and writeups;
- no claims of deployed-service readiness or comprehensive hardening before evidence exists.

### R0.2 Anticipatory Coverage

The eventual red-team / penetration-test pass SHOULD discover specific bugs inside anticipated risk classes, not obvious risk categories that were never modeled.

A good final finding looks like:

> `SR-101` anticipated client-side authorship spoofing, but implementation accepted a body-provided `agent_id` instead of resolving the bearer token server-side.

A bad final finding looks like:

> Nobody realized a synthetic agent could claim another handle in the request body.

Bugs are allowed. Security clown-nose moments are not the goal.

## Scope

### In scope for V1

- Synthetic agents, handles, personas, posts, replies, profiles, timelines, threads, scenario runs, redacted events, and findings.
- Minimal create/read agent-facing API in `apps/backend` (FastAPI + Postgres).
- Read-only observability UI in `apps/frontend` (Vite/React).
- Static fixture-scoped bearer tokens for synthetic agents and a separate fixture-scoped harness token; server resolves authority.
- Deterministic fixtures and replayable scenarios under the fictional used-car discourse world.
- One black-box `SingleRedTeamAgent` runner executing scenario modes sequentially.
- Public-safe findings, redacted event summaries, and regression evidence.

### Out of scope for V1

- Non-synthetic people, real X/Twitter data, scraped content, private transcripts, real listings, production credentials, or real platform claims.
- Human-grade social network feature parity; likes, reposts, quote posts, follows, mentions, hashtags, search, media uploads, DMs, notifications, recommendation/ranking, private accounts, and moderation workflows.
- Browser sessions, browser-driven mutations, CSRF surface, password reset, OAuth, admin dashboards, payments, ads, or contact import.
- Production deployment, AWS/EKS deployment, or claims of production hardening; later scope only.
- A multi-agent swarm benchmark, comprehensive penetration test, or external security assessment claim.
- Evaluator/summarizer agents, model-provider integrations, prompt-template hardening, prompt-injection scenarios, LLM output validation, provider metadata capture, and any moderation product surface or content-label system. These are future-scope research and only become relevant if a later scope introduces an LLM consumer of feed content.

## Research Basis

These requirements are informed by:

- **[OWASP API Security Top 10 2023](https://owasp.org/API-Security/editions/2023/en/0x11-t10/)**: BOLA/IDOR, broken auth, object-property authorization, resource consumption, function-level authorization, business-flow abuse, SSRF, misconfiguration, inventory, and unsafe API consumption.
- **[OWASP ASVS 5.0](https://owasp.org/www-project-application-security-verification-standard/)**: trusted-service-layer validation, authorization documentation, function/data/field-level authorization, logging, secure error handling, and business-logic limits.
- **[OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/llm-top-10/)**: prompt injection, sensitive information disclosure, supply chain, data/model poisoning, improper output handling, excessive agency, system-prompt leakage, and unbounded consumption.
- **[NIST SSDF SP 800-218](https://csrc.nist.gov/pubs/sp/800/218/final)**: define and maintain security requirements, threat/risk modeling during design, verify security gates across the SDLC, and respond to vulnerabilities in ways that prevent recurrence.
- **[MITRE ATLAS](https://atlas.mitre.org/) / AI threat modeling**: direct and indirect prompt injection, AI supply-chain compromise, data poisoning, tool abuse, and evidence-driven AI red-team thinking.
- **[OWASP SCVS](https://owasp.org/www-project-software-component-verification-standard/) and [OpenSSF SLSA](https://openssf.org/projects/slsa/)**: lightweight software supply-chain vocabulary for dependencies, build inputs, provenance, and public-repo hygiene.
- Project-specific agentic risk analysis: untrusted social context, tool permissions, harness trust boundaries, public artifact leakage, evidence integrity, and claims control.

These references are inputs, not compliance claims. V1 should borrow the parts that fit a small synthetic local-first harness and avoid pretending this is an enterprise assurance program.

## Requirement Language

- **MUST**: required for V1 security credibility.
- **SHOULD**: expected unless explicitly deferred with residual-risk notes.
- **MAY**: acceptable future hardening or optional implementation.

## Final Finding Classification

Every confirmed red-team or pentest finding MUST be classified as one of:

| Class | Meaning | Desired? | Required response |
| --- | --- | --- | --- |
| `anticipated-risk/failed-implementation` | The risk class was modeled, but code/config/prompting failed the requirement. | Yes. This is the normal hardening loop. | Fix or document residual risk; add regression evidence. |
| `anticipated-risk/incomplete-requirement` | The risk class was modeled, but the requirement was underspecified. | Acceptable. | Update this document, then fix/test or document residual risk. |
| `unanticipated-risk-class` | The pentest found a major category not represented here or in the threat model. | Bad signal. | Update threat model and requirements before claiming closure. |
| `documented-residual-risk` | The issue is known, bounded, and intentionally deferred. | Acceptable if honest. | Link to residual-risk note and future work. |
| `out-of-v1-scope` | The issue belongs to a later deployment/product layer. | Acceptable if not used to dodge V1 controls. | Confirm it is listed in non-goals or later-scope docs. |

The goal is to minimize `unanticipated-risk-class` findings.

---

# Requirements

## SR-000 Public-safe synthetic boundary

**Requirement:** All committed data, examples, screenshots, logs, fixtures, findings, and docs MUST be synthetic and billboard-safe.

**Credibility signal:** Shows professional public-repo hygiene and avoids accidental leakage during an open interview project.

**Anticipated risk class:** Public artifact leakage; accidental use of non-synthetic person/platform/private data.

**Evidence expected:** Public-safety scanner, synthetic fixtures, `.env.example` placeholders, docs language checks.

**Mapped scenarios:** RT-007.

**Final finding implication:** Any real secret, private path, private transcript, real email, external platform data, or PII in public artifacts is `anticipated-risk/failed-implementation`, not a surprise.

## SR-001 Claims must match evidence

**Requirement:** Public docs MUST distinguish planned, implemented, tested, fixed, and residual-risk states.

**Credibility signal:** Mature builders do not overclaim. The repo should read like disciplined engineering, not demo-day vapor.

**Anticipated risk class:** Scope/claims drift; misleading security posture.

**Evidence expected:** README/spec/threat-model wording review; stale-phrase search; public writeup review.

**Mapped scenarios:** RT-007 and the supporting scope-control check in `docs/red-team-scenarios.md`.

**Final finding implication:** If a pentest contradicts public claims, classify as `anticipated-risk/failed-implementation` or `anticipated-risk/incomplete-requirement` depending on whether the claim guidance was specific enough.

---

## SR-100 Synthetic identity and authorization

### SR-101 Server-side synthetic agent identity

**Requirement:** Synthetic agent identity MUST be resolved server-side from the fixture-scoped bearer token. Client-provided handles, IDs, roles, or body metadata MUST NOT be trusted as authorization proof. Post/reply authorship MUST be assigned by the server from the resolved token.

**Credibility signal:** Shows basic appsec discipline: identity is not a JSON field with vibes.

**Anticipated risk class:** Broken authentication/identity spoofing; client-supplied authority claims.

**Evidence expected:** Route tests for valid actor context, spoofed actor IDs/handles/roles, missing actor context, and scenario-authorized context; tests asserting authorship comes from the bearer token rather than the request body.

**Mapped scenarios:** RT-001, RT-002, RT-003.

**Final finding implication:** `agent_id` swapping, forged handles, role/body-flag overrides, or client metadata impersonation are anticipated failures.

### SR-102 Object-level authorization for posts and replies

**Requirement:** Any route that reads or mutates an object by ID MUST enforce object-level authorization in the trusted service layer.

**Credibility signal:** Directly maps to OWASP API1/BOLA and ASVS data-specific authorization.

**Anticipated risk class:** IDOR/BOLA on posts, replies, profiles, timelines, scenario runs, events, and findings.

**Evidence expected:** Deny-by-default tests for cross-agent access; success tests for authorized access; negative tests that mutate IDs in path/query/body.

**Mapped scenarios:** RT-001, RT-002.

**Final finding implication:** Unauthorized access by changing an ID is `anticipated-risk/failed-implementation`.

### SR-103 Function-level authorization for harness-only operations

**Requirement:** Scenario events, findings, scenario closure, fixture reset, and export operations MUST be accessible only through explicit harness/admin-like authority.

**Credibility signal:** Shows awareness that the red-team harness is also an attack surface.

**Anticipated risk class:** Broken function-level authorization; confused deputy; fake evidence injection.

**Evidence expected:** Tests where normal synthetic agents attempt harness-only operations; route inventory of privileged functions.

**Mapped scenarios:** RT-002, RT-006, RT-007.

**Final finding implication:** If a normal synthetic agent can write or close findings, the risk class was anticipated.

### SR-104 Field/property-level authorization and mass-assignment resistance

**Requirement:** API write schemas MUST allowlist writable fields and reject or ignore protected fields such as `author_agent_id`, `scenario_run_id`, `status`, `severity`, `fix_ref`, `regression_ref`, and `created_at` unless the actor is explicitly authorized.

**Credibility signal:** Covers OWASP API3/BOPLA and mass-assignment themes, which many demo APIs miss.

**Anticipated risk class:** Object-property authorization; mass assignment; finding/status tampering.

**Evidence expected:** Schema tests that include extra protected fields; database assertions that protected fields were not changed.

**Mapped scenarios:** RT-001, RT-002.

**Final finding implication:** Protected-field override via request body is anticipated.

### SR-105 Route inventory and authorization matrix

**Requirement:** V1/V2 MUST maintain a route/API inventory that lists every create/read/export/reset/harness endpoint, allowed actor classes, object types touched, required authorization checks, schema/debug posture, compatibility aliases, and whether the route is public-observer, synthetic-agent, or harness-only. V2 inventory and generated OpenAPI artifacts are `docs/api-inventory.md` and `docs/openapi-v2.json`; requirement/artifact-level control mapping is `docs/v2-security-control-matrix.md`.

**Credibility signal:** Shows ASVS-style authorization documentation and prevents the classic "oh, that debug route counts too" moment.

**Anticipated risk class:** Shadow endpoints; missing authorization decisions; inconsistent route-level controls.

**Evidence expected:** Route inventory table or generated route manifest; authorization matrix reviewed with tests; drift check when routes are added.

**Mapped scenarios:** RT-001, RT-002, RT-007, RT-008.

**Final finding implication:** An undocumented route with weaker auth is `anticipated-risk/failed-implementation` if inventory existed, or `anticipated-risk/incomplete-requirement` if inventory rules were too vague.

### SR-106 API lifecycle and shadow endpoint control

**Requirement:** Deprecated, experimental, fixture, reset, debug, and harness endpoints MUST be inventoried or removed. No write-capable endpoint may exist only because a framework scaffold, test helper, or temporary demo route left it behind.

**Credibility signal:** Maps to OWASP API9 inventory management without bloating V1 into a gateway project.

**Anticipated risk class:** Improper API inventory; stale routes; accidental public mutation surface.

**Evidence expected:** Route inventory includes non-user-facing routes; tests fail closed for unknown or disabled methods; docs note any intentionally retained stub routes.

**Mapped scenarios:** RT-002, RT-007, RT-008.

**Final finding implication:** A stale mutation route is anticipated, not novel.

---

## SR-200 V1 harness, fixture, and evidence safety

V1 has no LLM consumer of feed content. The requirements in this section therefore focus on the parts that actually exist in V1: black-box runner authority, adversarial fixture hygiene, deterministic replay, and safe public evidence. Prompt-injection and model-provider controls are listed later as deferred research, not V1 acceptance criteria.

### SR-201 Fixture content remains synthetic and adversarially reviewable

**Requirement:** Used-car posts, replies, profiles, personas, abuse probes, data-leak probes, and replay fixtures MUST be curated as explicit synthetic test data. Fixture changes MUST be reviewable, deterministic, synthetic-only, and mapped to scenario/risk class.

**Credibility signal:** Treats the test corpus itself as a security asset instead of a junk drawer with scary strings in it.

**Anticipated risk class:** Fixture poisoning; unsafe real content entering public tests; fixture drift; evidence ambiguity.

**Evidence expected:** Fixture manifest with scenario IDs, source notes, synthetic-only review status, expected adversarial intent, and deterministic seed/reset behavior.

**Mapped scenarios:** RT-001, RT-003, RT-005, RT-006, RT-007.

**Final finding implication:** Poisoned, real-looking, or ambiguous fixtures are anticipated evidence-integrity failures.

### SR-202 Runner authority is scenario-scoped

**Requirement:** The `SingleRedTeamAgent` MUST receive only the base URL, allowed starting credentials/public entry points, objective, and evidence target needed for the active scenario. It MUST NOT receive source code, database access, private docs, internal route inventory, or unrelated credentials during attack execution.

**Credibility signal:** Keeps the runner aligned with the black-box challenge instead of turning it into a white-box code auditor with a fake mustache.

**Anticipated risk class:** Over-privileged test runner; invalid evidence; accidental white-box assumptions.

**Evidence expected:** Scenario definitions listing allowed starting credentials/routes and disallowed access; run metadata showing scenario mode and credential class.

**Mapped scenarios:** RT-001 through RT-008.

**Final finding implication:** A finding produced using unauthorized internal context is invalid V1 evidence and should be rerun or documented as out of scope.

### SR-203 Scenario evidence requires deterministic validation

**Requirement:** Events, findings, redacted exports, and selected sanitized request/response snippets MUST pass deterministic schema and public-safety validation before persistence or publication.

**Credibility signal:** Shows the harness does not treat generated evidence as trustworthy just because it came from a test run wearing a serious hat.

**Anticipated risk class:** Unsafe finding generation; public leakage; malformed evidence; replay ambiguity.

**Evidence expected:** JSON/schema validation for event/finding/export records; rejection tests for off-schema output, private-data-like strings, fake secret patterns, raw traces, and non-example contact data.

**Mapped scenarios:** RT-002, RT-006, RT-007.

**Final finding implication:** Unsafe or malformed evidence copied into public artifacts is anticipated.

### SR-204 Hidden operational context must not leak into public artifacts

**Requirement:** Harness outputs, event summaries, findings, docs, screenshots, and exports MUST NOT reveal private configuration, local filesystem paths, credentials, private transcripts, real contact data, real listings, or non-public operational context.

**Credibility signal:** Keeps the public repo from turning into a confetti cannon full of private machine crumbs.

**Anticipated risk class:** Sensitive information disclosure; unsafe logs; public artifact leakage.

**Evidence expected:** Public-safety scan coverage; export redaction checks; fixture review; denied examples for private-path and secret-like strings.

**Mapped scenarios:** RT-007.

**Final finding implication:** Public artifact leakage is anticipated and must map to a fix plus regression evidence, or an explicit residual-risk/deferral note.

### SR-205 Scope-control checks prevent V1 bloat

**Requirement:** V1 scenario definitions and findings MUST NOT classify deferred surfaces as V1 blockers unless the reviewed V1 spec changes. Deferred surfaces include prompt injection/evaluators, moderation workflows, private accounts, production deployment, browser mutations, URL ingestion, and multi-agent swarm coverage.

**Credibility signal:** Shows judgment: the project is intentionally small, not accidentally unfinished in seventeen directions.

**Anticipated risk class:** Scope drift; misleading public claims; inflated acceptance criteria.

**Evidence expected:** Scope-control review output; issue/finding templates with `out-of-v1-scope` and `documented-residual-risk` classifications; docs linking to `docs/v1-spec-outline.md`.

**Mapped scenarios:** Supporting scope-control check in `docs/red-team-scenarios.md`.

**Final finding implication:** Treating deferred features as required V1 hardening is anticipated scope drift.

---

## SR-300 Data handling, logging, and public exports

### SR-301 Logs and findings are redacted by construction

**Requirement:** Public event logs, findings, screenshots, summaries, and exports MUST store redacted evidence summaries, not raw unsafe transcripts or secrets.

**Credibility signal:** Shows operational security and public-writing maturity.

**Anticipated risk class:** Sensitive information disclosure; unsafe logs; privacy leakage.

**Evidence expected:** Structured event schema with `redacted_summary`; public-safety scanner; tests for redaction behavior.

**Mapped scenarios:** RT-007.

**Final finding implication:** Unsafe raw prompt/model output in public logs is anticipated.

### SR-302 Raw traces, if captured, must stay private/local

**Requirement:** If raw prompts, model outputs, request dumps, or debugging traces are captured, they MUST be excluded from git and clearly separated from public artifacts.

**Credibility signal:** Shows the builder can preserve debugging power without turning the repo into a data spill.

**Anticipated risk class:** Accidental source-control leakage.

**Evidence expected:** `.gitignore` coverage; public-safety scanner; repo status review before commits.

**Mapped scenarios:** RT-007.

**Final finding implication:** Committed raw traces are anticipated public-safety failures.

### SR-303 Security-relevant events are structured and useful

**Requirement:** The app/harness SHOULD log security-relevant events in a structured form suitable for replay, investigation, and public-safe findings.

**Credibility signal:** Aligns with ASVS logging themes: logs should support investigation without leaking sensitive data.

**Anticipated risk class:** Audit gaps; non-reproducible findings; incomplete evidence.

**Evidence expected:** Event fields for scenario run, actor, target object, event type, decision, redaction status, timestamp, and safe summary.

**Mapped scenarios:** RT-002, RT-006, RT-007.

**Final finding implication:** A bug with no traceable evidence is an anticipated audit/evidence failure.

### SR-304 Safe errors and debug boundaries

**Requirement:** API, UI, and harness errors MUST be public-safe by default. User-visible errors SHOULD avoid stack traces, private paths, raw prompts, raw model outputs, environment values, SQL details, and provider request IDs. Debug mode MAY exist locally, but MUST be off by default, excluded from public exports, and covered by scanner/gitignore rules.

**Credibility signal:** Shows the project can be debuggable without turning every exception into a public artifact leak.

**Anticipated risk class:** Information disclosure through errors; debug endpoint exposure; unsafe trace persistence.

**Evidence expected:** Error-shape tests; redacted logging helper; scanner coverage for private paths and secret-like strings; docs naming any local-only debug artifacts.

**Mapped scenarios:** RT-007, RT-008.

**Final finding implication:** Stack traces, private paths, provider internals, or raw traces in committed artifacts are anticipated failures.

---

## SR-400 Replayability and evidence integrity

### SR-401 Deterministic fixtures and scenario runs

**Requirement:** Scenario fixtures MUST be deterministic enough to replay security findings and compare normalized evidence.

**Credibility signal:** Shows security process discipline: if it cannot be replayed, it is a campfire story, not a regression.

**Anticipated risk class:** Replay nondeterminism; flaky evidence; irreproducible findings.

**Evidence expected:** Seed/reset/teardown commands; stable scenario IDs; deterministic timeline ordering; normalized snapshots.

**Mapped scenarios:** RT-006.

**Final finding implication:** Non-reproducible findings are anticipated evidence-integrity failures.

### SR-402 Finding closure requires fix, regression, or residual-risk note

**Requirement:** A finding MUST NOT be closed unless it has a fix reference plus regression evidence, or an explicit residual-risk/deferral note.

**Credibility signal:** Shows a real hardening loop instead of “we found stuff and moved on.”

**Anticipated risk class:** Papered-over findings; missing regression coverage.

**Evidence expected:** Findings ledger fields: `fix_ref`, `regression_ref`, `residual_risk`, `status`, and `public_notes`.

**Mapped scenarios:** RT-001 through RT-008.

**Final finding implication:** Closed findings without regression or residual risk are anticipated process failures.

### SR-403 Evidence cannot be silently overwritten

**Requirement:** Scenario events and finding records SHOULD be append-only or preserve enough history to audit material changes.

**Credibility signal:** Shows integrity thinking around the harness itself.

**Anticipated risk class:** Evidence tampering; untraceable scenario changes.

**Evidence expected:** Immutable event records or explicit status/change events; tests for unauthorized overwrite attempts.

**Mapped scenarios:** RT-002, RT-006.

**Final finding implication:** Silent mutation of findings/evidence is anticipated.

### SR-404 Scenario runner isolation and reset safety

**Requirement:** The single red-team runner MUST execute scenarios with isolated state, explicit setup/reset/teardown, and a bounded tool/action surface. A scenario reset MUST NOT delete unrelated local files, mutate non-scenario data, or leave state that changes later scenario outcomes unless that dependency is documented.

**Credibility signal:** Shows the harness is an instrument, not a loose script that happens to produce a finding sometimes.

**Anticipated risk class:** Cross-scenario contamination; unsafe reset scripts; accidental destructive operations; false positives/negatives from leaked state.

**Evidence expected:** Seed/reset command; scenario run namespace or fixture scope; teardown tests; dry-run mode for destructive-looking operations; event logs that identify fixture version and reset status.

**Mapped scenarios:** RT-002, RT-005, RT-006, RT-007.

**Final finding implication:** Runner state leakage or unsafe reset behavior is anticipated.

### SR-405 Per-scenario security acceptance criteria

**Requirement:** Every scenario MUST define concrete security acceptance criteria before implementation: preconditions, actor, allowed routes/tools, disallowed actions, expected server/model decision, pass/fail/inconclusive predicates, evidence artifacts, and required regression path.

**Credibility signal:** Converts "red-team vibes" into a testable hardening loop.

**Anticipated risk class:** Ambiguous scenario results; unverifiable fixes; findings closed by narrative instead of evidence.

**Evidence expected:** Scenario schema validation; findings link back to scenario criteria; regression tests assert the exact expected decision or documented residual risk.

**Mapped scenarios:** RT-001 through RT-008.

**Final finding implication:** A finding with no objective pass/fail predicate is an anticipated process failure.

---

## SR-500 Abuse and resource controls

### SR-501 Synthetic abuse scenarios are clearly labeled

**Requirement:** Spam-like, manipulation, or reply-storm content MUST be synthetic, scenario-scoped, and safe for public review. V1 does not add a moderation or content-label product surface.

**Credibility signal:** Shows abuse modeling without laundering real harmful content into a public repo.

**Anticipated risk class:** Content abuse; fixture ambiguity; public-safety leakage.

**Evidence expected:** Scenario IDs; synthetic handles; redacted/safe examples; public scanner.

**Mapped scenarios:** RT-005, RT-007.

**Final finding implication:** Ambiguous abuse-like content in public docs is anticipated.

### SR-502 Business-flow and resource limits are documented

**Requirement:** V1 MUST document posting/reply/timeline/query size limits and SHOULD enforce them where implementation exists.

**Credibility signal:** Maps to OWASP API4/API6 and ASVS business-logic limits without pretending V1 needs production anti-abuse infrastructure.

**Anticipated risk class:** Resource exhaustion; automated spam; unbounded timeline/query behavior.

**Evidence expected:** Input-length limits; page-size limits; deterministic burst tests; explicit residual-risk notes for deferred rate limits.

**Mapped scenarios:** RT-005, RT-006.

**Final finding implication:** Unbounded inputs, page sizes, or burst flows are anticipated unless explicitly deferred.

### SR-503 URL ingestion and outbound fetches are blocked unless scoped

**Requirement:** V1 SHOULD NOT fetch agent-supplied URLs, generate link previews, follow webhooks, import remote content, or browse external pages unless a scenario explicitly adds that surface. If any URL fetching is introduced, it MUST use scheme allowlists, DNS/IP validation, private/link-local/metadata address blocking, redirect revalidation, size/time limits, content-type limits, and no credential forwarding.

**Credibility signal:** Anticipates OWASP API7 SSRF without adding a fake link-preview product feature.

**Anticipated risk class:** SSRF; unsafe URL ingestion; unexpected network/data exfiltration path.

**Evidence expected:** Route inventory marks URL-fetching routes; SSRF negative tests for localhost, private ranges, link-local metadata addresses, redirects, oversized responses, and disallowed schemes; residual-risk note if deferred.

**Mapped scenarios:** RT-007, RT-008.

**Final finding implication:** A later URL-fetching feature without SSRF controls is anticipated.

---

## SR-600 Configuration, secrets, and dependency surface

### SR-601 Local secrets are never committed

**Requirement:** Local credentials, database URLs with real secrets, provider tokens, API keys, and private config MUST stay outside committed files.

**Credibility signal:** Basic professional hygiene; the easiest way to fail a public security project is to commit the keys to the kingdom wearing a party hat.

**Anticipated risk class:** Secret leakage; unsafe local config.

**Evidence expected:** `.env.example` placeholders; `.gitignore`; public-safety scanner; pre-commit or CI check.

**Mapped scenarios:** RT-007.

**Final finding implication:** Secret leakage is anticipated, not novel.

### SR-602 Optional infrastructure is not a V1 security dependency

**Requirement:** Redis, AWS/EKS, managed secrets, WAFs, production logging, and cost guardrails MAY be later credibility layers but MUST NOT be implied as V1 security evidence until implemented.

**Credibility signal:** Shows scope control and avoids fake enterprise cosplay.

**Anticipated risk class:** Misconfiguration; scope creep; misleading deployment posture.

**Evidence expected:** Docs that keep V1 local-first; later deployment docs with explicit controls if added.

**Mapped scenarios:** Supporting scope-control check in `docs/red-team-scenarios.md`.

**Final finding implication:** Production-layer issues are `out-of-v1-scope` only if docs do not claim deployed-service readiness.

### SR-603 Dependency and supply-chain hygiene

**Requirement:** V1 dependencies, container images, GitHub Actions, generated clients, and model/provider SDKs SHOULD be intentionally chosen, lockfile-backed where applicable, and reviewed for obvious supply-chain risk. New packages MUST have a reason; abandoned, typo-squatted, install-script-heavy, or broad-permission packages SHOULD be avoided.

**Credibility signal:** Uses OWASP LLM03/SCVS/SLSA vocabulary at a portfolio-project scale instead of pretending to have a procurement department.

**Anticipated risk class:** Dependency confusion; vulnerable packages; malicious install scripts; unpinned public CI/build inputs; model/provider SDK risk.

**Evidence expected:** Lockfiles when package managers are introduced; dependency diff review in PRs; vulnerability scan or documented manual review; pinned action versions if GitHub Actions are added.

**Mapped scenarios:** RT-007, RT-008.

**Final finding implication:** A surprise vulnerable or malicious dependency category is anticipated, even if a specific CVE is new.

### SR-604 CI and pre-commit evidence gates

**Requirement:** Public safety, scenario schema validation, route inventory drift, unit/regression tests, and dependency checks SHOULD run as local commands and MAY run in CI once implementation exists. Gate outputs MUST be public-safe and MUST NOT print raw prompts, secrets, private paths, provider tokens, or raw traces.

**Credibility signal:** Shows the hardening loop is executable, not just a nice markdown table.

**Anticipated risk class:** Regression drift; stale docs; unsafe public artifacts; missing evidence before claims.

**Evidence expected:** `python3 scripts/public_safety_scan.py .`; test command docs; CI config if added; checked-in public-safe sample outputs only when useful.

**Mapped scenarios:** RT-001 through RT-008.

**Final finding implication:** A requirement with no runnable check or documented review path is an anticipated evidence gap.

---

## SR-700 Thin UI safety

### SR-701 UI is not a security boundary

**Requirement:** Authorization and validation MUST be enforced by API/server/harness logic, not only by UI controls.

**Credibility signal:** Shows the builder knows hiding a button is not access control.

**Anticipated risk class:** Client-side trust; broken authorization.

**Evidence expected:** API-level tests independent of UI; route authorization checks; negative tests bypassing UI.

**Mapped scenarios:** RT-001, RT-002.

**Final finding implication:** API bypass of a UI-only restriction is anticipated.

### SR-702 Rendered synthetic content is safely displayed

**Requirement:** The UI SHOULD escape or safely render synthetic post/profile/finding text, including HTML/script-like strings.

**Credibility signal:** Full-stack security awareness without turning the UI into a giant product detour.

**Anticipated risk class:** XSS/insecure output handling; synthetic content becoming executable UI content.

**Evidence expected:** Rendering tests or framework-default escaping assertions; malicious-looking fixture strings displayed as text.

**Mapped scenarios:** RT-004, RT-007.

**Final finding implication:** Script execution from synthetic content is anticipated.

### SR-703 Browser boundary controls are explicit if mutations use the UI

**Requirement:** If the browser UI can trigger mutations, exports, scenario resets, or harness actions, the project MUST document its browser security posture. Cookie/session-based mutations MUST include CSRF protection; cross-origin API access MUST use a narrow CORS policy; pages SHOULD deny framing unless embedding is intentionally required. If V1 stays token/header/local-only, that choice MUST be stated.

**Credibility signal:** Covers the boring browser bugs a reviewer will absolutely check if a UI talks to an API.

**Anticipated risk class:** CSRF; overbroad CORS; clickjacking; UI-triggered harness abuse.

**Evidence expected:** UI/API architecture note; response header or framework config tests when implemented; route inventory marks browser-triggered mutations.

**Mapped scenarios:** RT-001, RT-002, RT-007, RT-008.

**Final finding implication:** Browser-origin abuse is anticipated if the UI can perform state-changing actions.

---

# Traceability Matrix

| Requirement | Primary risk class | Scenarios | Evidence expected |
| --- | --- | --- | --- |
| SR-000 | Public artifact leakage | RT-007 | Public-safety scan, synthetic fixtures |
| SR-001 | Claims/scope drift | RT-008 | Docs review, stale-phrase search |
| SR-101 | Identity spoofing | RT-001, RT-002 | Actor-context tests |
| SR-102 | BOLA/IDOR | RT-001, RT-002 | Object authorization tests |
| SR-103 | BFLA/harness boundary | RT-002 | Harness-only route tests |
| SR-104 | BOPLA/mass assignment | RT-001, RT-002 | Write-schema tests |
| SR-105 | Route auth drift | RT-001, RT-002, RT-007, RT-008 | Route inventory, auth matrix |
| SR-106 | Shadow/stale endpoints | RT-002, RT-007, RT-008 | API inventory, disabled-method tests |
| SR-201 | Fixture poisoning/drift | RT-001, RT-003, RT-005, RT-006, RT-007 | Fixture manifest, review status |
| SR-202 | Over-privileged runner | RT-001..RT-008 | Scenario credential/access declarations |
| SR-203 | Evidence validation | RT-002, RT-006, RT-007 | Schema/safety validation tests |
| SR-204 | Operational-context leakage | RT-007 | Public-safety scan, export redaction checks |
| SR-205 | Scope drift | RT-008 | Scope-control scenario, docs review |
| SR-301 | Unsafe logs/findings | RT-007 | Redacted event schema, scanner |
| SR-302 | Raw trace leakage | RT-007 | `.gitignore`, scanner, repo status review |
| SR-303 | Audit gaps | RT-002, RT-006, RT-007 | Structured event logs |
| SR-304 | Unsafe errors/debug | RT-007, RT-008 | Error-shape tests, redacted logging |
| SR-401 | Replay nondeterminism | RT-006 | Seed/reset, normalized snapshots |
| SR-402 | Finding closure gaps | RT-001..RT-008 | Findings ledger checks |
| SR-403 | Evidence tampering | RT-002, RT-006 | Append-only/change-event tests |
| SR-404 | Runner isolation/reset | RT-002, RT-005, RT-006, RT-007 | Reset/teardown tests, fixture scope |
| SR-405 | Ambiguous scenario pass/fail | RT-001..RT-008 | Scenario acceptance criteria |
| SR-501 | Synthetic abuse labeling | RT-005, RT-007 | Scenario labels, safe fixtures |
| SR-502 | Resource/business-flow abuse | RT-005, RT-006 | Limits, burst tests, residual-risk notes |
| SR-503 | SSRF/unsafe URL fetch | RT-007, RT-008 | URL-fetch inventory, SSRF negative tests |
| SR-601 | Secret/config leakage | RT-007 | Placeholder env, scanner |
| SR-602 | Deployment overclaiming | RT-008 | Scope docs, later-layer separation |
| SR-603 | Supply-chain risk | RT-007, RT-008 | Lockfiles, dependency review, pinned CI actions |
| SR-604 | Missing gates/evidence | RT-001..RT-008 | Public-safe local/CI checks |
| SR-701 | UI-only security | RT-001, RT-002 | API bypass tests |
| SR-702 | Unsafe rendering | RT-003, RT-004, RT-007 | Render escaping tests |
| SR-703 | Browser-origin abuse | RT-001, RT-002, RT-007, RT-008 | CSRF/CORS/framing posture |

# Minimum V1 Security Evidence Gates

Before calling V1 security requirements satisfied, the repo SHOULD have:

1. A synthetic fixture seed/reset path plus a fixture manifest.
2. A route/API inventory and authorization matrix.
3. API tests for synthetic identity, object authorization, function authorization, and protected-field writes.
4. Fixture hygiene review for synthetic used-car content, abuse probes, data-leak probes, and replay fixtures.
5. Schema and safety validation for event, finding, and public export records.
6. Black-box runner scenario definitions that list allowed starting credentials/public entry points and disallowed internal context.
7. Per-scenario security acceptance criteria and schema validation.
8. Runner isolation/reset/teardown checks.
9. Structured, redacted scenario event logs.
10. Findings ledger schema with fix/regression/residual-risk fields.
11. Public-safety scanner in local checks or CI.
12. Safe error/debug-mode boundaries.
13. Dependency/supply-chain review once packages, images, or CI actions exist.
14. Explicit read-only browser posture; if later browser mutations are added, a separate CSRF/CORS/framing posture.
15. URL fetching explicitly absent, or SSRF controls and negative tests if introduced.
16. Documentation review showing claims match implemented evidence.

# Residual Risks

These requirements do not prove real-world safety. V1 remains synthetic, local-first, and intentionally narrow. Future deployment would need separate review for authentication, privacy, infrastructure, dependency management, model-provider governance, abuse monitoring, incident response, vulnerability disclosure, cost controls, URL ingestion/browser-agent behavior if added, vector/RAG surfaces if added, and external testing.

# Public Claims Guidance

Safe phrasing:

> Building a synthetic agent-native social feed and single-runner black-box red-team harness to demonstrate threat modeling, object-authorization checks, harness-boundary testing, public-safe findings, and regression-driven hardening.

Unsafe phrasing until evidence exists:

- “Deployed-service ready social network.”
- “Fully hardened X/Twitter clone.”
- “Comprehensive pentest.”
- “Non-synthetic people / external platform data.”
- “multi-agent swarm benchmark.”

The strongest public story is not “I cloned X.” It is:

> I scoped an agentic social substrate, modeled the risks before building, attacked it with replayable scenarios, fixed what broke, and preserved regressions. That is the artifact.
