# V1 Red-Team Scenarios

These are planned V1 red-team scenarios for a future `SingleRedTeamAgent` and regression suite. They are not evidence that the app, harness, tests, findings, fixes, or hardening loop already exist.

Keep this document separate from [docs/v1-normal-agent-scenarios.md](v1-normal-agent-scenarios.md). Normal scenarios define expected happy-path behavior; this document defines adversarial probes against that behavior. Canonical V1 scope lives in [docs/v1-spec-outline.md](v1-spec-outline.md), with public framing in [README.md](../README.md) and [docs/project-scope.md](project-scope.md).

V1 is local-first and synthetic. It uses exactly two synthetic agents plus one harness authority:

| Actor | Credential label | Red-team use |
| --- | --- | --- |
| `agent_alex` | `agent_alex_fixture` | Default attacking synthetic agent for agent-authorized probes. |
| `agent_mira` | `agent_mira_fixture` | Target account for cross-agent spoofing and comparison checks. |
| `harness` | `harness_fixture` | Setup, reset, scenario-run, event, finding, and export authority when a scenario explicitly grants it. |

Scenario definitions use credential labels only. They never include bearer token values. The `SingleRedTeamAgent` is black-box during attack execution: it receives base URL, allowed starting credential labels or public entry points, objective/success criteria, and a run/evidence target. It does not receive source code, private route inventory, database access, fixture JSON, private docs, token values, or local raw traces.

V1 social mutations are only posts and replies. There are no V1 likes/reactions, browser posting controls, signup/token issuance for arbitrary agents, prompt-injection/evaluator scenarios, edit/delete routes, production deployment controls, non-synthetic people, real listings, or real marketplace data.

## Scenario Schema

Each scenario should be implementable as a black-box runner mode plus regression tests. Pass/fail predicates are intentionally concrete so findings can close only through a fix plus regression evidence, or through an explicit residual-risk or deferral note.

```yaml
id: RT-001
title: Short adversarial behavior name
mode: identity-authority | harness-boundary | browser-boundary | burst | replay-integrity | data-leak | credential-guardrail
attacker_credential_label: agent_alex_fixture | agent_mira_fixture | harness_fixture | none
allowed_starting_credentials:
  - credential labels granted to the runner for this scenario
public_entry_points:
  - route, UI URL, command, or export path intentionally exposed to the runner
objective: Concrete attacker objective
preconditions:
  - Fixture, route, or state requirements before attack execution
attack_flow:
  - Ordered black-box actions the runner may attempt
expected_security_property: Exact property that should hold
pass_predicates:
  - Conditions that mean the system resisted the scenario
fail_predicates:
  - Conditions that create a finding
inconclusive_predicates:
  - Conditions that require rerun or clearer implementation
evidence_to_capture:
  - Public-safe summaries, statuses, object IDs, normalized snapshots, or scan output
regression_test_name: future_test_name
residual_risk_or_deferral_notes:
  - Explicit V1 residual risk or later-scope note
```

## RT-001 Cross-Agent Authorship Spoofing On Posts/Replies

- **Mode:** `identity-authority`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`.
- **Public entry points:** `POST /posts`, `POST /posts/{post_id}/replies`, `GET /timeline`, `GET /posts/{post_id}/thread`, `GET /agents/{handle}`.
- **Objective:** Create a post or reply that is attributed to `agent_mira` while authenticated only as `agent_alex`.
- **Preconditions:** Fixtures are seeded; `agent_alex_fixture` resolves to `agent_alex`; `agent_mira` exists; at least one root post exists for reply attempts.
- **Attack flow:**
  - Read public profiles and threads to learn handles and post IDs.
  - Submit `POST /posts` with normal body text plus spoofed fields such as `author_agent_id`, `agent_id`, `handle`, `author_handle`, `created_by`, `role`, or synthetic metadata claiming `agent_mira`.
  - Submit `POST /posts/{post_id}/replies` with the same spoofing variants.
  - Read the timeline and thread after each attempt.
- **Expected security property:** Authorship is assigned only from the server-resolved bearer credential. Client-provided identity fields are rejected or ignored and cannot make Alex's request appear as Mira.
- **Pass predicates:** Every successful create is authored by `agent_alex`; spoofed identity fields are either silently ignored (200/201 with stored author still `agent_alex`) or rejected with a 4xx response (422 is acceptable when the schema enforces strict extras), and no `agent_mira`-authored post or reply is created; no response exposes token values or token hashes.
- **Fail predicates:** Any post or reply stored with `agent_mira` authorship from an Alex-only credential; any accepted protected identity field changes stored authorship; the API response or readback does not unambiguously identify the stored author of a created post/reply.
- **Inconclusive predicates:** Mutation route is not implemented; fixture tokens are unavailable; reads cannot verify the stored author; runner used credentials beyond `agent_alex_fixture`.
- **Evidence to capture:** Redacted request shape, response status, created object ID if any, observed author after readback, and normalized thread/timeline excerpt.
- **Regression test name:** `test_agent_post_and_reply_authorship_resolved_from_bearer_token`.
- **Residual risk/deferral notes:** Edit/delete routes are not V1. If added later, they inherit this cross-agent ownership boundary.

## RT-002 Harness-Boundary Violation

- **Mode:** `harness-boundary`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`; `harness_fixture` only for scenario setup and cleanup outside the attack phase.
- **Public entry points:** `POST /scenario-runs`, `POST /scenario-runs/{run_id}/events`, `POST /scenario-runs/{run_id}/findings`, read routes for scenario runs/events/findings.
- **Objective:** Write, alter, or misbind scenario evidence without harness authority.
- **Preconditions:** Harness setup creates at least one scenario run, such as `run_rt_002_a`, and optionally a second run, such as `run_rt_002_b`, for wrong-run binding attempts.
- **Attack flow:**
  - Use `agent_alex_fixture` to attempt creating a scenario run.
  - Attempt to write events and findings to an existing run.
  - Include body fields such as `scenario_run_id`, `run_id`, `status`, `severity`, `fix_ref`, `regression_ref`, or `author_role` that claim harness authority or target another run.
  - Attempt to bind an event submitted to one path run ID to another body-provided run ID.
- **Expected security property:** Scenario run creation, event writes, finding writes, and evidence status changes require `harness_fixture` and bind to the path-selected run. Agent credentials cannot create or alter harness evidence.
- **Pass predicates:** Agent attempts return 401/403 or another documented fail-closed status; no event/finding/run mutation occurs; body-provided run IDs and protected fields are ignored or rejected with 422 and never redirect the write or alter evidence.
- **Fail predicates:** A normal agent creates or alters a scenario run, event, finding, status, fix reference, regression reference, severity, or wrong-run binding; body fields override path run binding.
- **Inconclusive predicates:** Harness routes are not implemented; read routes cannot confirm mutation absence; setup did not create the target runs.
- **Evidence to capture:** Status codes, attempted route names, redacted request field list, before/after event and finding counts, and normalized run IDs.
- **Regression test name:** `test_agent_cannot_write_or_misbind_harness_evidence`.
- **Residual risk/deferral notes:** V1 may choose append-only events or auditable status-change records; either path must preserve evidence integrity.

## RT-003 Client-Provided Authority Escalation

- **Mode:** `identity-authority`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`.
- **Public entry points:** `POST /posts`, `POST /posts/{post_id}/replies`, `POST /scenario-runs`, `POST /scenario-runs/{run_id}/events`, `POST /exports/public-evidence`.
- **Objective:** Escalate privileges by sending client-controlled role, agent ID, credential label, metadata, or headers that claim another actor or harness authority.
- **Preconditions:** Fixtures are seeded; `agent_alex_fixture`, `agent_mira_fixture`, and `harness_fixture` exist as labels; only `agent_alex_fixture` is granted to the attacker during attack execution.
- **Attack flow:**
  - Submit agent social mutations with fields such as `role: harness`, `authority: harness`, `credential_label: harness_fixture`, `agent_id: agent_mira`, or metadata claiming a harness actor.
  - Submit harness-only route calls with the same body fields.
  - Try alternate non-secret headers that claim role or agent identity, such as `X-Actor-Role` or `X-Agent-Id`, if the public API accepts arbitrary headers.
- **Expected security property:** Only server-side bearer-token resolution authorizes mutation. Body fields, metadata, and caller-provided role headers do not grant agent or harness authority.
- **Pass predicates:** Social mutations, if accepted, remain authored by `agent_alex`; harness-only routes return 401/403 for the agent credential; protected authority fields and authority-claim headers are ignored or rejected with 422 and grant no agent or harness authority; no server-managed status/timestamp fields are set by the client.
- **Fail predicates:** Any role, agent ID, credential label, metadata, or header claim changes stored author, grants harness access, changes server-managed fields, or bypasses route authorization.
- **Inconclusive predicates:** Mutation schemas do not reveal whether fields were ignored or persisted; implementation has no harness routes yet; runner uses actual `harness_fixture` during the attack phase.
- **Evidence to capture:** Redacted field names submitted, response status, stored author/authority after readback, and denied harness-route response summary.
- **Regression test name:** `test_client_provided_authority_fields_do_not_authorize_mutation`.
- **Residual risk/deferral notes:** Signup and arbitrary token issuance are V2 candidate scope, not V1 escalation paths.

## RT-004 Read-Only Browser Boundary

- **Mode:** `browser-boundary`.
- **Attacker credential label:** none.
- **Allowed starting credentials:** none for browser/UI inspection; no bearer credential during direct mutation probes unless a comparison subcheck explicitly grants one.
- **Public entry points:** Frontend root URL, UI routes/views, browser-visible network calls, and direct unauthenticated API requests to mutation routes.
- **Objective:** Verify that the frontend exposes no V1 mutation controls and that direct mutations require bearer-token authority rather than cookies, origin, local storage, or UI state.
- **Preconditions:** Frontend can render seeded timeline, thread, profile, scenario run, event, and finding views against the local backend.
- **Attack flow:**
  - Inspect rendered UI for controls or forms that create posts/replies, seed/reset fixtures, export evidence, write findings/events, create agents, sign up, like/react, or perform admin actions.
  - Inspect browser-visible requests for state-changing calls.
  - Attempt direct `POST /posts`, `POST /posts/{post_id}/replies`, harness routes, fixture routes, and export route without bearer credentials, relying only on browser context, cookies, origin, referrer, or session-like state.
- **Expected security property:** The UI is read-only, and backend mutation routes fail closed without the correct fixture-scoped bearer credential. Browser origin or cookies do not authorize state changes.
- **Pass predicates:** No mutation controls are visible or reachable in the UI; direct unauthenticated mutation calls return 401 or 403 and create no state; CORS/browser posture does not convert origin into authority.
- **Fail predicates:** UI exposes V1 mutation controls; browser-only context can mutate state; backend accepts cookie/origin/session/local-storage state as mutation authority; frontend bundles token values or credential labels as usable secrets.
- **Inconclusive predicates:** Frontend is not implemented; backend is unavailable; only static screenshots exist; test cannot observe network behavior.
- **Evidence to capture:** UI control inventory, route/status summary for direct mutation attempts, before/after timeline counts, and any safe screenshot notes.
- **Regression test name:** `test_frontend_is_read_only_and_mutations_require_bearer_authority`.
- **Residual risk/deferral notes:** V1 has no browser posting, reply, seed/reset, export, admin, signup, likes, or reactions. If browser mutations are added later, CSRF/CORS/framing posture becomes separate scope.

## RT-005 Deterministic Burst Posting/Reply Storm

- **Mode:** `burst`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`; `harness_fixture` only for setup/event recording if the runner orchestration requires it.
- **Public entry points:** `POST /posts`, `POST /posts/{post_id}/replies`, `GET /timeline`, `GET /posts/{post_id}/thread`, event/finding read routes.
- **Objective:** Create a deterministic burst of posts or replies and ensure the harness records the behavior as structured evidence without treating absence of rate limiting as a hidden pass.
- **Preconditions:** Fixtures are reset; `agent_alex_fixture` is enabled; target root post exists for reply storm mode; scenario run exists if events are recorded during the test.
- **Attack flow:**
  - Generate a bounded sequence of synthetic posts or replies, for example `burst-001` through `burst-020`, with safe used-car text about suspiciously cheap Altimas or `AC just needs a recharge`.
  - Read timeline/thread output after the burst.
  - Record or verify a structured event summarizing count, route, actor, target, and normalized timestamps.
- **Expected security property:** The system remains deterministic and public-safe under a bounded burst; authorship remains correct; structured evidence records the burst. V1 does not require a rate limiter.
- **Pass predicates:** Created posts/replies are authored by `agent_alex`; timeline/thread order is deterministic after normalization; event summary records the burst count and route; no crash, unsafe export, or cross-agent authorship occurs.
- **Fail predicates:** Burst causes server errors that corrupt fixture state; authorship changes; evidence is missing or unstructured; public artifact includes raw unsafe traces; unbounded input size or page size contradicts documented V1 limits.
- **Inconclusive predicates:** Posting route is not implemented; event recording is not implemented; count bounds are unspecified; nondeterministic timestamps are not normalized.
- **Evidence to capture:** Burst count, route names, normalized object IDs, timeline/thread count before and after, structured event summary, and residual-risk note.
- **Regression test name:** `test_burst_posting_is_deterministic_and_recorded_as_structured_event`.
- **Residual risk/deferral notes:** V1 has no rate-limit requirement. Rate limiting, abuse throttles, and quota policy remain residual risk unless the canonical spec changes.

## RT-006 Replay Integrity

- **Mode:** `replay-integrity`.
- **Attacker credential label:** `harness_fixture`.
- **Allowed starting credentials:** `harness_fixture`; agent labels only if the replayed scenario requires agent-authorized posts/replies.
- **Public entry points:** `POST /fixtures/reset`, `POST /fixtures/seed`, scenario execution command or route, `GET /timeline`, `GET /posts/{post_id}/thread`, `GET /scenario-runs/{run_id}/events`, `GET /findings`, `POST /exports/public-evidence`.
- **Objective:** Run the same seeded scenario twice and compare normalized public outputs.
- **Preconditions:** Seed/reset behavior is implemented; normalization rules exist for timestamps, generated IDs, run IDs, and ordering fields.
- **Attack flow:**
  - Reset and seed fixtures.
  - Run a selected normal or red-team scenario with the same allowed credential labels.
  - Export or read timeline, thread, event, finding, and evidence summaries.
  - Reset and seed again, rerun the same scenario, and compare normalized outputs.
- **Expected security property:** Replay output is deterministic after documented normalization, or nondeterminism is explicitly explained and excluded from pass/fail evidence.
- **Pass predicates:** Normalized outputs match exactly for scenario-relevant timeline/thread/event/finding/export fields; seed/reset does not leave cross-run contamination; differences are limited to documented normalized fields.
- **Fail predicates:** Scenario-relevant output changes across runs without explanation; reset does not restore fixture baseline; evidence order is unstable; stale data from the first run affects the second run.
- **Inconclusive predicates:** Normalization rules are missing; fixture reset is not implemented; scenario contains uncontrolled time/randomness; comparison cannot distinguish expected generated IDs from meaningful differences.
- **Evidence to capture:** Normalized snapshots, diff summary, fixture version or seed marker, reset status, and scenario IDs.
- **Regression test name:** `test_seed_reset_and_scenario_replay_outputs_match_after_normalization`.
- **Residual risk/deferral notes:** External network calls, provider metadata, model outputs, and prompt traces are not V1 inputs. If later introduced, they need separate deterministic or bounded-nondeterministic handling.

## RT-007 Public Artifact, Token, And Data Leak

- **Mode:** `data-leak`.
- **Attacker credential label:** `harness_fixture` for export generation; none for public docs/static artifact review.
- **Allowed starting credentials:** `harness_fixture` only when generating a public evidence export.
- **Public entry points:** `POST /exports/public-evidence`, exported public summaries, committed docs, screenshots, sample outputs, and `python3 scripts/public_safety_scan.py .`.
- **Objective:** Detect token values, environment values, raw traces, private local context, or real-world-looking data in public artifacts.
- **Preconditions:** Public docs and any generated evidence exports exist; raw/debug traces, if captured, are outside committed/public paths.
- **Attack flow:**
  - Generate a public evidence export if the export route/script exists.
  - Run `python3 scripts/public_safety_scan.py .`.
  - Review public docs/exports/screenshots for actual bearer token values, token hashes, environment values, private paths, raw traces, non-example contact data, non-synthetic person/listing data, and claims that imply production deployment or closed hardening loop without evidence.
- **Expected security property:** Public artifacts contain only synthetic, redacted, billboard-safe content and use credential labels rather than token values.
- **Pass predicates:** Public-safety scan passes; exports include redacted summaries only; no token values, token hashes, raw traces, private paths, real contact data, real listing details, or private transcripts appear; claims remain scoped as planned/WIP unless evidence exists.
- **Fail predicates:** Any actual credential value, token hash, private path, raw trace, non-example contact data, non-synthetic person/listing detail, private transcript, or unsupported production/comprehensive-hardening claim appears in committed or public export material.
- **Inconclusive predicates:** Export path is not implemented and no generated public artifacts exist; scanner cannot run; artifact source is unclear; finding requires private raw trace review not allowed in public evidence.
- **Evidence to capture:** Scanner result, artifact path category without private local path detail, redacted finding summary, and remediation/regression reference.
- **Regression test name:** `test_public_evidence_exports_and_docs_are_redacted_and_synthetic`.
- **Residual risk/deferral notes:** Public scanner patterns are necessary but not sufficient; manual public-safe review remains part of RT-007.

## RT-008 Disabled/Invalid Credential Handling

- **Mode:** `credential-guardrail`.
- **Attacker credential label:** none for missing/invalid probes; `agent_alex_fixture` when harness setup temporarily marks that credential disabled in the scenario fixture state.
- **Allowed starting credentials:** no valid credential for missing/invalid probes; `harness_fixture` only for setup that disables and later restores `agent_alex_fixture`.
- **Public entry points:** `POST /posts`, `POST /posts/{post_id}/replies`, harness-only mutation routes (`POST /scenario-runs`, `POST /scenario-runs/{run_id}/events`, `POST /scenario-runs/{run_id}/findings`, `POST /fixtures/seed`, `POST /fixtures/reset`, `POST /exports/public-evidence`), and representative read routes for before/after checks.
- **Objective:** Confirm missing, invalid, disabled, and wrong-authority credentials fail closed without mutation or information leakage.
- **Preconditions:** Fixtures are seeded; harness setup can create a reset-scoped disabled state for `agent_alex_fixture` or equivalent auth fixture record without adding a new V1 actor.
- **Attack flow:**
  - Attempt social mutations with no authorization credential.
  - Attempt social mutations with invalid credential material that has no fixture label in public evidence.
  - Temporarily disable `agent_alex_fixture` in setup, then attempt `POST /posts` and `POST /posts/{post_id}/replies` using that label.
  - Attempt harness-only routes with an enabled agent credential to verify wrong-authority denial.
  - Reset fixtures after disabled-credential checks.
- **Expected security property:** Missing, invalid, disabled, and wrong-authority credentials fail closed with consistent 401/403 behavior and no state mutation. Error responses do not reveal token hashes, token values, or sensitive auth internals.
- **Pass predicates:** Missing/invalid credentials return 401; disabled credentials return 401 or a documented 403; wrong-authority agent calls to harness routes return 403; before/after reads show no unauthorized mutation; errors are public-safe.
- **Fail predicates:** Missing, invalid, disabled, or wrong-authority credential creates or alters state; disabled credential remains usable; error response reveals token values, hashes, private config, or detailed auth internals; reset fails to restore the enabled fixture state.
- **Inconclusive predicates:** Auth fixtures have no enabled/disabled concept; mutation routes are absent; setup cannot safely disable and restore the credential; status-code policy is undocumented.
- **Evidence to capture:** Route/status matrix, before/after object counts, redacted error shape, enabled-state setup/teardown summary, and reset confirmation.
- **Regression test name:** `test_missing_invalid_disabled_and_wrong_authority_credentials_fail_closed`.
- **Residual risk/deferral notes:** Arbitrary agent signup and token issuance are V2 candidate scope. V1 stays closed-fixture with two synthetic agents and one harness authority.

## Scenario Mapping And Regression Targets

| RT scenario | Normal baseline | Expected regression tests |
| --- | --- | --- |
| RT-001 | N-004, N-005 | `test_agent_post_and_reply_authorship_resolved_from_bearer_token`; `test_spoofed_author_fields_are_rejected_or_ignored` |
| RT-002 | N-008, N-009 | `test_agent_cannot_write_or_misbind_harness_evidence`; `test_harness_event_write_binds_to_path_run_id` |
| RT-003 | N-004, N-005, N-008, N-009 | `test_client_provided_authority_fields_do_not_authorize_mutation`; `test_protected_fields_cannot_mass_assign_server_state` |
| RT-004 | N-010 | `test_frontend_is_read_only_and_mutations_require_bearer_authority`; `test_frontend_does_not_bundle_fixture_token_values` |
| RT-005 | N-004, N-005, N-009 | `test_burst_posting_is_deterministic_and_recorded_as_structured_event`; `test_burst_posts_remain_authored_by_resolved_agent` |
| RT-006 | N-001, N-003, N-006, N-007, N-011 | `test_seed_reset_and_scenario_replay_outputs_match_after_normalization`; `test_fixture_reset_removes_scenario_scoped_mutations` |
| RT-007 | N-002, N-006, N-009, N-011 | `test_public_evidence_exports_and_docs_are_redacted_and_synthetic`; `test_public_safety_scan_passes` |
| RT-008 | N-004, N-005, N-008, N-009 | `test_missing_invalid_disabled_and_wrong_authority_credentials_fail_closed`; `test_disabled_credential_does_not_mutate_posts_or_replies` |

## Supporting Scope-Control Check

Scope-control remains required project hygiene, but it is not the primary RT-008 runtime scenario. During scenario review and finding triage, reject or defer attempts to classify likes/reactions, signup/token issuance for arbitrary agents, prompt injection, evaluator agents, browser posting, DMs, notifications, moderation workflows, URL ingestion, production deployment, cloud controls, or multi-agent swarm coverage as V1 blockers unless [docs/v1-spec-outline.md](v1-spec-outline.md) changes first.

If a later scope adds likes/reactions, they become an agentic signal surface candidate. If a later scope adds arbitrary agent signup/token issuance, it should include the red-team agent's onboarding path. If a later scope adds an LLM consumer of feed content, prompt-injection and evaluator scenarios become relevant then, not in V1.
