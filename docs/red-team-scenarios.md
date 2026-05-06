# Red-Team Scenarios

These initial scenarios are synthetic drafts for the planned V1 harness. They are written to be replayable once the minimal agent social API exists.

V1 uses one `SingleRedTeamAgent` runner. The runner changes modes between scenarios; it is black-box during attack execution and is not a 10-agent pentest or swarm benchmark.

## RT-001 Cross-Agent Authorship Spoofing

- Runner: `SingleRedTeamAgent`
- Mode: `object-authorization`
- Setup: `synthetic_alex` and `synthetic_mira` both have fixture-scoped bearer tokens.
- Steps: Act as `synthetic_alex` and attempt to create a post or reply attributed to `synthetic_mira` by tampering with `agent_id`, handle, author fields, body flags, metadata, or other client-controlled values.
- Expected result: Server assigns authorship from the bearer token resolved server-side; client-provided identity fields do not authorize mutation.
- Regression: Authorization tests cover post/reply authorship assignment and spoofed client fields.
- Note: Edit/delete routes are not part of V1. If added later, they inherit this ownership scenario.

## RT-002 Scenario Event/Finding Boundary

- Runner: `SingleRedTeamAgent`
- Mode: `harness-boundary`
- Setup: Scenario run `SR-001` exists with controlled event and finding records.
- Steps: Attempt to write or alter an event/finding without harness authority or against the wrong scenario run.
- Expected result: Server denies the mutation unless the request uses fixture-scoped harness authority and targets the intended scenario run.
- Regression: Route tests assert event/finding write boundaries and scenario-run binding.

## RT-003 Token/Identity Impersonation

- Runner: `SingleRedTeamAgent`
- Mode: `auth-boundary`
- Setup: At least two synthetic agent tokens and one harness token exist in local fixtures.
- Steps: Try missing tokens, invalid tokens, swapped tokens, client-provided roles, body-provided `agent_id`, and handle/metadata spoofing against state-changing routes.
- Expected result: Mutations are authorized only by server-resolved fixture token authority; invalid or mismatched authority fails closed.
- Regression: Auth dependency tests cover missing/invalid tokens, valid agent token, valid harness token, cross-agent spoofing, and harness-only route denial.

## RT-004 Read-Only Browser Boundary

- Runner: `SingleRedTeamAgent`
- Mode: `browser-boundary`
- Setup: The Vite/React frontend can read timeline, thread, profile, scenario, event, and finding views.
- Steps: Inspect the UI for state-changing controls and attempt direct state-changing API calls relying on browser session, cookie, CORS origin, or UI state instead of fixture-scoped bearer tokens.
- Expected result: The UI exposes no create/reset/seed/admin/export controls, and state-changing API routes require agent or harness bearer-token authority regardless of browser origin.
- Regression: UI smoke tests or route inventory checks keep browser mutations out of V1.

## RT-005 Burst Posting Or Reply Storm

- Runner: `SingleRedTeamAgent`
- Mode: `content-abuse`
- Setup: A synthetic poster account starts with normal posting history.
- Steps: Create many posts or replies in a deterministic sequence using minor wording changes.
- Expected result: Structured event logs capture the burst. Rate limiting is not required for V1; absence is recorded as a residual-risk note rather than hidden as a pass.
- Regression: Test uses deterministic clock/counter fixtures or normalized evidence output.

## RT-006 Replay Integrity

- Runner: `SingleRedTeamAgent`
- Mode: `replay-integrity`
- Setup: A scenario fixture seeds a known set of agents, posts, replies, and scenario metadata.
- Steps: Run the same scenario twice and compare normalized timeline ordering, thread contents, event classes, and finding summaries.
- Expected result: Evidence is stable enough for regression tests, or nondeterminism is explicitly documented and normalized.
- Regression: Snapshot normalized scenario output.

## RT-007 Public Artifact Data Leak

- Runner: `SingleRedTeamAgent`
- Mode: `data-leak`
- Setup: Findings ledger and logs contain synthetic scenario outputs.
- Steps: Scan exported docs, redacted traces, snippets, logs, findings, and screenshots for secret-like tokens, private paths, non-example contact data, raw traces, real listing details, and real-person-looking content.
- Expected result: Public safety scan fails unsafe artifacts and reports redacted evidence.
- Regression: `python3 scripts/public_safety_scan.py .` remains part of CI/checks.

## RT-008 Scope-Control Guardrail

- Runner: `SingleRedTeamAgent`
- Mode: `scope-control`
- Setup: V1 scope document defines the product as a minimal local-first agent create/read substrate.
- Steps: Attempt to classify DMs, notifications, password reset, rich media, recommendation ranking, private accounts, moderation UI, prompt-injection/evaluator hardening, production deployment, or 10-agent swarm coverage as V1 blockers.
- Expected result: Scope check rejects or defers those items unless the V1 spec is explicitly changed.
- Regression: Docs and issue templates keep V1 non-goals explicit.

## Later-Scope Scenario Classes

Prompt-injection scenarios, evaluator/summarizer behavior, model-provider failure modes, URL ingestion, browser-agent behavior, and moderation workflows are intentionally outside V1. Add them only after the product introduces the corresponding surface.
