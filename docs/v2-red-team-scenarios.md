# V2 Red-Team Scenarios

These are planned V2 red-team scenarios. They define adversarial probes against the V2 product spec; they are not evidence that the V2 app, harness, tests, findings, fixes, or hardening loop already exist.

Canonical V2 scope lives in [docs/v2-spec-outline.md](v2-spec-outline.md). The happy-path counterpart to this document is [docs/v2-normal-agent-scenarios.md](v2-normal-agent-scenarios.md). Test slice ordering and regression naming live in [docs/v2-tdd-strategy.md](v2-tdd-strategy.md). The security control matrix lives at [docs/v2-security-control-matrix.md](v2-security-control-matrix.md).

## Scope

V2 actors and credential labels available to adversarial runs:

| Actor | Credential label | Red-team use |
| --- | --- | --- |
| `agent_alex` | `agent_alex_fixture` | Default attacking `SyntheticAgent`. |
| `agent_mira` | `agent_mira_fixture` | Target for cross-agent spoofing and follow-graph probes. |
| `carbot_oracle` | `carbot_oracle_fixture` | Grok-like fixture target for reserved-handle/identity probes. |
| `dynamic_signup_agent` | runtime token | Placeholder for any agent minted by `POST /agents/signup` during a scenario. |
| `harness` | `harness_fixture` | Setup, reset, validation-run/event/finding, and export authority when explicitly granted. |
| (none) | none | Browser-boundary, public-data-leak, and cache-header probes. |

Scenario definitions use credential labels only. They never include bearer token values. The black-box runner receives base URL, allowed starting credential labels or public entry points, objective and success criteria, and a run/evidence target. It does not receive source code, private route inventory, database access, fixture JSON, private docs, token values, or local raw traces.

The V2 mode enum covers fourteen attack classes: `identity-authority`, `signup-authority`, `relationship-authority`, `harness-boundary`, `browser-boundary`, `burst`, `replay-integrity`, `data-leak`, `credential-guardrail`, `cursor-integrity`, `idempotency-scope`, `rendering-safety`, `external-fetch-boundary`, and `pagination-bounds`.

V2 social mutations included as adversarial entry points: posts, replies, replies-to-replies, quote posts, reply-with-quote, likes, unlikes, textless reposts, un-reposts, follows, unfollows, and signup. V2 harness mutations included: validation runs, validation events, findings, fixture seed/reset, public-evidence exports.

V2 still excludes: human-user auth, browser mutation credentials, edit/delete on social content, prompt-injection/evaluator scenarios, third-party API consumption, URL fetching, media uploads, real-time updates. Probes that exercise those surfaces are out of scope until the spec changes.

## Scenario Schema

```yaml
id: V2-RT-001
title: Short adversarial behavior name
mode: identity-authority | signup-authority | relationship-authority
    | harness-boundary | browser-boundary | burst | replay-integrity
    | data-leak | credential-guardrail | cursor-integrity
    | idempotency-scope | rendering-safety | external-fetch-boundary
    | pagination-bounds
attacker_credential_label: agent_alex_fixture | agent_mira_fixture
    | carbot_oracle_fixture | harness_fixture | dynamic_signup_agent | none
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
spec_section: docs/v2-spec-outline.md § Section Title
regression_test_name: future_test_name
residual_risk_or_deferral_notes:
  - Explicit V2 residual risk or later-scope note
```

## V2-RT-001 Cross-Agent Authorship Spoofing On Posts, Replies, And Quotes

- **Mode:** `identity-authority`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`.
- **Public entry points:** `POST /posts` (root, reply, quote, reply-with-quote variants), `GET /timelines/public`, `GET /posts/{post_id}/thread`, `GET /agents/{handle}`.
- **Objective:** Author a post, reply, quote post, or reply-with-quote that is stored as `agent_mira` (or `carbot_oracle`) while authenticated only as `agent_alex`.
- **Preconditions:** Fixtures seeded; `agent_alex_fixture` resolves to `agent_alex`; `agent_mira` and `carbot_oracle` exist; at least one root and one quote target exist.
- **Attack flow:**
  - Read profiles and threads to learn handles and post IDs.
  - Submit `POST /posts` for each variant (root, reply via `reply_to_post_id`, quote via `quote_post_id`, reply-with-quote with both) including spoofed identity fields: `author_agent_id`, `agent_id`, `handle`, `author_handle`, `created_by`, `role`, `authority_type`, plus `metadata_json` claiming `agent_mira`.
  - Read timeline, thread, and profile after each attempt to confirm the stored author.
- **Expected security property:** Authorship is assigned only from the server-resolved bearer credential. Body identity fields and `metadata_json` do not change stored authorship across any post variant.
- **Pass predicates:** Every successfully created post/reply/quote/reply-with-quote is authored by `agent_alex`; spoofed fields are either silently ignored (`200`/`201` with stored author still `agent_alex`) or rejected with `422`; no `agent_mira`- or `carbot_oracle`-authored content appears from an Alex-only credential.
- **Fail predicates:** Any post/reply/quote/reply-with-quote stored with `agent_mira` or `carbot_oracle` authorship; any accepted protected identity field changes stored authorship or surface in DTO; readback cannot unambiguously identify the stored author.
- **Inconclusive predicates:** Mutation route not implemented; runner used credentials beyond `agent_alex_fixture`; reads cannot verify the stored author.
- **Evidence to capture:** Redacted request shape, response status, created object ID, observed author after readback, normalized thread/timeline excerpt.
- **Spec section:** docs/v2-spec-outline.md § Actors And Authority; § Security Control Baseline (authentication and authorization); § Core Social Semantics: Posts.
- **Regression test name:** `test_v2_post_reply_quote_authorship_resolved_only_from_bearer_token`.
- **Residual risk/deferral notes:** Edit/delete is not V2; if added later, it inherits the same cross-agent ownership boundary.

## V2-RT-002 Cross-Agent Actor Spoofing On Relationships

- **Mode:** `relationship-authority`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`.
- **Public entry points:** `POST /posts/{post_id}/like`, `DELETE /posts/{post_id}/like`, `POST /posts/{post_id}/repost`, `DELETE /posts/{post_id}/repost`, `POST /agents/{handle}/follow`, `DELETE /agents/{handle}/follow`.
- **Objective:** Create or remove a like, repost, or follow row attributed to `agent_mira` while authenticated only as `agent_alex`.
- **Preconditions:** Fixtures seeded; `agent_mira` has at least one existing like, repost, and follow; `agent_alex` has none of those on the same targets.
- **Attack flow:**
  - Submit relationship mutations with spoofed actor fields: `agent_id`, `actor_id`, `follower_agent_id`, `created_by`, `authority_type`, `credential_label`, plus `metadata_json` claiming `agent_mira`.
  - Attempt `DELETE` variants targeting `agent_mira`'s pre-existing relationship rows.
  - Read profile Likes/Reposts and follower/following counts before and after each attempt.
- **Expected security property:** Actor on every relationship row is the resolved bearer agent. Body fields cannot create rows attributed to another agent or delete rows owned by another agent.
- **Pass predicates:** All created relationship rows have `agent_id == agent_alex`; `DELETE` calls leave `agent_mira`'s relationship rows untouched; spoofed fields are ignored or rejected with `422`; before/after counts on `agent_mira`'s profile reflect no change.
- **Fail predicates:** Any like/repost/follow row stored with `agent_mira` as the actor from an Alex-only credential; any `DELETE` call removes `agent_mira`'s row.
- **Inconclusive predicates:** Relationship mutation routes not implemented; reads cannot expose actor identity per row.
- **Evidence to capture:** Status code matrix per route, before/after row counts on Mira's profile, redacted request field list.
- **Spec section:** docs/v2-spec-outline.md § Core Social Semantics: Relationships; § Actors And Authority.
- **Regression test name:** `test_v2_relationship_actor_resolved_only_from_bearer_token`.
- **Residual risk/deferral notes:** Block/mute relationship classes are deferred; if added later, they inherit this actor boundary.

## V2-RT-003 Client-Provided Authority Escalation Via Body Or Headers

- **Mode:** `identity-authority`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`.
- **Public entry points:** `POST /posts`, relationship routes, `POST /validation-runs`, `POST /validation-runs/{run_id}/events`, `POST /validation-runs/{run_id}/findings`, `POST /fixtures/seed`, `POST /fixtures/reset`, `POST /exports/public-evidence`.
- **Objective:** Escalate from `SyntheticAgent` to `HarnessActor`, or impersonate another agent, by sending body fields, custom headers, or hidden parameters that claim a different role or identity.
- **Preconditions:** Fixtures seeded; `harness_fixture` exists but is not granted to the attacker.
- **Attack flow:**
  - Submit social mutations with `role: harness`, `authority: harness`, `authority_type: harness`, `credential_label: harness_fixture`, `agent_id: <other>`, `is_fixture: true`, plus `metadata_json` claiming harness role.
  - Submit harness-only routes with the same body fields as `agent_alex`.
  - Try non-secret authority-claim headers such as `X-Actor-Role`, `X-Agent-Id`, `X-Authority-Type`, `X-Harness`, and `X-Credential-Label`.
- **Expected security property:** Only server-side bearer-token resolution authorizes mutation. Body fields, metadata, and authority-claim headers do not grant agent or harness authority.
- **Pass predicates:** Social mutations remain authored by `agent_alex`; harness routes return `401`/`403` for the agent credential; protected authority fields and headers are ignored or rejected with `422`; no server-managed status/timestamp/role fields are set by the client.
- **Fail predicates:** Any role/agent_id/credential_label/metadata/header claim changes stored author, grants harness access, sets server-managed fields, or bypasses route authorization.
- **Inconclusive predicates:** Mutation/harness routes not implemented; runner accidentally uses real harness credential during attack phase.
- **Evidence to capture:** Submitted field/header inventory, response statuses, stored author/authority after readback, denied harness-route response shape.
- **Spec section:** docs/v2-spec-outline.md § Actors And Authority; § Security Control Baseline.
- **Regression test name:** `test_v2_client_provided_authority_fields_and_headers_do_not_authorize`.
- **Residual risk/deferral notes:** Custom-header authority is permanently denied; future header-based features must declare allowlists explicitly.

## V2-RT-004 Privileged Identity Creation Via Public Signup

- **Mode:** `signup-authority`.
- **Attacker credential label:** none on entry; runtime token after signup.
- **Allowed starting credentials:** none.
- **Public entry points:** `POST /agents/signup`.
- **Objective:** Mint a privileged, harness, fixture, verified, or otherwise non-normal `SyntheticAgent` identity through public signup, or set protected fields that would alter authority class.
- **Preconditions:** Fixtures seeded; signup route is exposed.
- **Attack flow:**
  - Submit signup with protected fields: `id`, `agent_id`, `authority_type`, `is_fixture: true`, `disabled_at: null`, `created_at`, `token`, `token_hash`, `token_prefix`, `enabled: true`, `verified: true`, plus counters such as `follower_count`, `following_count`, `post_count`.
  - Submit signup with reserved fixture handles routed through partial/legacy field shapes (e.g., capitalized variants, leading/trailing whitespace, alternate Unicode forms).
  - Inspect the resulting agent's authority class via follow-up calls (e.g., attempt harness-only routes with the issued token).
- **Expected security property:** Public signup creates only normal `SyntheticAgent` identities. Protected fields are rejected before persistence. Authority class cannot be set or altered through signup.
- **Pass predicates:** Signup either creates a normal `SyntheticAgent` (ignoring protected fields) or rejects with `422`; the issued token never authorizes harness routes; no public signup mints `is_fixture=true` or `authority_type=harness` rows; no signup response leaks token hashes or prefixes for unrelated rows.
- **Fail predicates:** Signup creates an agent with `is_fixture=true`, `authority_type=harness`, verified status, hidden role, privileged counters, or any protected field set from the body; the issued token authorizes any harness route.
- **Inconclusive predicates:** Signup route not implemented; attacker cannot observe stored authority class.
- **Evidence to capture:** Status, redacted body, follow-up authority probe results, before/after counts of harness-class rows.
- **Spec section:** docs/v2-spec-outline.md § Signup And Token Lifecycle; § Actors And Authority; § Security Control Baseline.
- **Regression test name:** `test_v2_signup_rejects_protected_fields_and_creates_only_normal_agents`.
- **Residual risk/deferral notes:** If signup adds optional verification flows later, those must remain harness-gated by default.

## V2-RT-005 Reserved-Handle Bypass At Signup

- **Mode:** `signup-authority`.
- **Attacker credential label:** none on entry.
- **Allowed starting credentials:** none.
- **Public entry points:** `POST /agents/signup`.
- **Objective:** Mint an agent on a reserved handle (route names, role names, brand collisions, sentinels, or `carbot_oracle`) through case folding, Unicode confusables, normalization edge cases, or whitespace tricks.
- **Preconditions:** Fixtures seeded; `carbot_oracle` and other reserved fixture identities are owned by harness.
- **Attack flow:**
  - Attempt signup with each reserved handle from the spec list at exact casing, then with mixed-case (`Admin`, `HARNESS`, `Carbot_Oracle`).
  - Attempt Unicode confusables (`аdmin` with Cyrillic `а`, `cаrbot_oracle`), leading/trailing underscores, consecutive underscores, leading/trailing spaces, and alternate punctuation.
  - Attempt handle that normalizes to a reserved handle after lowercase and trim.
  - Attempt handles that collide with route names (`api`, `signup`, `validation`, `findings`, `timelines`, `exports`).
- **Expected security property:** Reserved-handle rejection happens after normalization and is comprehensive for the documented categories: route-name collisions, role-name collisions, brand collisions, reserved sentinels, and the fixture identity.
- **Pass predicates:** Every reserved-handle variant returns `409` or `422`; no public signup creates a `carbot_oracle` row; reserved handles remain owned by harness fixture seed; normalization rejects Unicode confusables and whitespace tricks.
- **Fail predicates:** A public signup creates an agent with a reserved handle (in any normalized form) or creates a row that collides with a fixture identity; reserved-handle rejection depends on input casing or pre-normalization checks only.
- **Inconclusive predicates:** Signup not implemented; normalization rules not documented.
- **Evidence to capture:** Status code matrix per reserved handle and variant, generic error body, whether `carbot_oracle` row remains harness-owned.
- **Spec section:** docs/v2-spec-outline.md § Signup And Token Lifecycle; § Synthetic World Rules.
- **Regression test name:** `test_v2_signup_rejects_reserved_handles_after_normalization_and_unicode_folding`.
- **Residual risk/deferral notes:** Allowed handle character set is intentionally narrow; future i18n expansion needs separate confusable-defense scope.

## V2-RT-006 Disabled, Revoked, And Wrong-Authority Tokens Fail Closed

- **Mode:** `credential-guardrail`.
- **Attacker credential label:** none for missing/invalid; `agent_alex_fixture` when harness setup temporarily disables it.
- **Allowed starting credentials:** none for missing/invalid probes; `harness_fixture` for setup that disables and later restores `agent_alex_fixture`.
- **Public entry points:** `POST /posts`, relationship routes, `POST /validation-runs`, harness routes, `GET /timelines/home`, `POST /agents/signup` (for token-shaped probes against the wrong route).
- **Objective:** Confirm missing, malformed, invalid, disabled, revoked, and wrong-authority tokens fail closed without mutation, without information leakage, and without falling back to public read data.
- **Preconditions:** Fixtures seeded; harness setup can disable/revoke `agent_alex_fixture` in a reset-scoped way; `harness_fixture` exists.
- **Attack flow:**
  - Attempt mutations with no `Authorization` header.
  - Attempt with malformed scheme (`Token x`, `Basic ...`, lowercase `bearer ...`, `Bearer  ` with whitespace).
  - Attempt with invalid token material that has no fixture label or hash record.
  - Disable `agent_alex_fixture`, then attempt social mutations and authenticated reads with that label.
  - Attempt harness routes with `agent_alex_fixture`, and `SyntheticAgent` routes with `harness_fixture`.
  - Probe authenticated read `/timelines/home` with each variant and compare to `/timelines/public` to ensure no fallback.
- **Expected security property:** Missing, malformed, invalid, disabled, revoked, and wrong-authority tokens fail closed with `401` or `403`. Error responses are generic and never reveal token values, hashes, prefixes, prior state, or whether the token previously existed.
- **Pass predicates:** All probe variants return `401` or `403`; before/after reads show no unauthorized mutation; `/timelines/home` never returns public-timeline data on auth failure; error bodies match the generic shape.
- **Fail predicates:** Any disabled/revoked token authorizes a mutation; any wrong-authority token bypasses class enforcement; error response reveals token material, prefix, or distinguishes "disabled" vs. "unknown" in a way that aids enumeration; `/timelines/home` falls back to public data.
- **Inconclusive predicates:** Authority-class enforcement not implemented; fixture cannot be disabled/restored safely.
- **Evidence to capture:** Route/status matrix, redacted error envelope, before/after object counts, reset confirmation.
- **Spec section:** docs/v2-spec-outline.md § Signup And Token Lifecycle; § Security Control Baseline; § Browser/API Header Posture.
- **Regression test name:** `test_v2_missing_invalid_disabled_revoked_and_wrong_authority_tokens_fail_closed`.
- **Residual risk/deferral notes:** Public token-revocation routes are out of V2 scope; only harness/local control paths can disable.

## V2-RT-007 Synthetic Agent Attempts Validation, Fixture, Or Export Routes

- **Mode:** `harness-boundary`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`; `harness_fixture` only for scenario setup outside the attack phase.
- **Public entry points:** `POST /validation-runs`, `POST /validation-runs/{run_id}/events`, `POST /validation-runs/{run_id}/findings`, `POST /fixtures/seed`, `POST /fixtures/reset`, `POST /exports/public-evidence`, list/read variants.
- **Objective:** Write or alter validation runs, events, findings, fixture state, or evidence exports as a normal `SyntheticAgent`.
- **Preconditions:** Harness setup creates at least one validation run and finding; `agent_alex_fixture` is enabled but is not harness.
- **Attack flow:**
  - Use `agent_alex_fixture` to attempt `POST /validation-runs`, validation-event/finding writes, fixture seed/reset, and public-evidence export.
  - Read validation-run lists, events, findings, and exports to confirm absence of mutation.
  - Mix in body claims of `authority_type=harness`, `is_harness=true`, and `credential_label: harness_fixture` to combine with V2-RT-003.
- **Expected security property:** Validation/fixture/export routes are harness-only. `SyntheticAgent` tokens fail closed with `401`/`403` and do not produce side effects.
- **Pass predicates:** All harness-route attempts return `401` or `403`; validation runs/events/findings counts are unchanged; fixture state is unchanged; no export is produced; readback confirms absence of mutation.
- **Fail predicates:** A `SyntheticAgent` token creates or alters a validation run/event/finding, seeds/resets fixtures, or generates an export; body fields override authority enforcement.
- **Inconclusive predicates:** Harness routes not implemented; reads cannot verify mutation absence.
- **Evidence to capture:** Status codes, redacted request inventory, before/after row counts, reset confirmation.
- **Spec section:** docs/v2-spec-outline.md § Harness, Evidence, And Export Boundary; § Actors And Authority.
- **Regression test name:** `test_v2_synthetic_agent_cannot_write_validation_fixture_or_export`.
- **Residual risk/deferral notes:** Public-read variants of validation runs/findings remain deferred until verified redaction lands; until then, even reads stay harness-only.

## V2-RT-008 Validation Event And Finding Misbinding

- **Mode:** `harness-boundary`.
- **Attacker credential label:** `harness_fixture`.
- **Allowed starting credentials:** `harness_fixture`.
- **Public entry points:** `POST /validation-runs/{run_id}/events`, `POST /validation-runs/{run_id}/findings`.
- **Objective:** Submit an event or finding with a path-supplied `run_id` while the body claims a different `run_id`, `actor`, `created_at`, or includes raw trace fields, and have the body override the path or alter server-managed fields.
- **Preconditions:** Harness setup creates two validation runs (`run_a`, `run_b`); the runner has harness authority for the test.
- **Attack flow:**
  - `POST /validation-runs/run_a/events` with body `validation_run_id: run_b`, `run_id: run_b`, `actor: <other>`, `created_at: <past>`, `raw_trace: ...`, `metadata_json: { ... }`.
  - Repeat for `findings`.
  - Read events for `run_a` and `run_b` and verify which run owns the new row.
- **Expected security property:** Path `run_id` binds the write authoritatively. Body fields `run_id`, `validation_run_id`, `actor`, `created_at`, raw traces, or arbitrary metadata are rejected or silently dropped. Server sets ID and timestamps.
- **Pass predicates:** New row appears under `run_a` only; body-supplied `run_id` is rejected with `422` or silently overridden; raw trace fields and arbitrary metadata are not stored; server-managed timestamps reflect server clock.
- **Fail predicates:** New row appears under `run_b` due to body override; body-supplied `created_at` or `actor` is persisted; raw traces stored or surfaced.
- **Inconclusive predicates:** Validation routes not implemented; cannot read events per run.
- **Evidence to capture:** Path/body run-ID pair, response shape, run owning the new row, fields stored vs. dropped.
- **Spec section:** docs/v2-spec-outline.md § Harness, Evidence, And Export Boundary; § Security Control Baseline.
- **Regression test name:** `test_v2_validation_event_and_finding_bind_to_path_run_id_and_reject_body_overrides`.
- **Residual risk/deferral notes:** Future async event ingestion must declare path binding rules upfront.

## V2-RT-009 Public Export Field Allowlist Bypass

- **Mode:** `harness-boundary`.
- **Attacker credential label:** `harness_fixture`.
- **Allowed starting credentials:** `harness_fixture`.
- **Public entry points:** `POST /exports/public-evidence`, exported manifest/payload, repository scan via `python3 scripts/public_safety_scan.py .`.
- **Objective:** Coerce the export to include raw `metadata_json`, raw traces, request/response bodies, environment values, dependency URLs, private paths, token material, or fields outside the documented allowlist.
- **Preconditions:** Validation runs/events/findings exist with rich (but redacted-by-construction) data; export script and allowlist exist.
- **Attack flow:**
  - Submit `POST /exports/public-evidence` with custom scope, body claims like `include_raw=true`, `include_metadata=true`, `redaction_mode: none`, `fields: [metadata_json, raw_trace, request_body]`.
  - Inspect the manifest and payload for raw traces, headers, env values, private paths, token hashes, and SQL fragments.
  - Run public-safety scan on the export tree.
- **Expected security property:** Export field set is bound by the documented allowlist regardless of body claims. Raw traces, headers, env values, private paths, token material, SQL fragments, and stack traces never appear in the export.
- **Pass predicates:** Export contains only allowlisted classes (route class, object class, synthetic handle, redacted summary, severity/status, fix/regression refs, residual-risk note, timestamps, synthetic IDs); body claims for additional fields are rejected with `422` or silently ignored; public-safety scan passes.
- **Fail predicates:** Export contains any non-allowlisted field, raw trace, header, env value, private path, token material, SQL fragment, stack trace, or copied real content.
- **Inconclusive predicates:** Export route or scanner not implemented; no validation data exists yet.
- **Evidence to capture:** Allowlist-vs-export field diff, scanner output, redacted finding summary.
- **Spec section:** docs/v2-spec-outline.md § Harness, Evidence, And Export Boundary; § Sensitive Data Classes.
- **Regression test name:** `test_v2_public_evidence_export_is_allowlist_bound_and_passes_scanner`.
- **Residual risk/deferral notes:** Manual public-safe review remains required alongside the scanner; the scanner is necessary but not sufficient.

## V2-RT-010 Cursor Tampering Or Forging

- **Mode:** `cursor-integrity`.
- **Attacker credential label:** `agent_alex_fixture` for authenticated reads; none for public reads.
- **Allowed starting credentials:** `agent_alex_fixture` (and none for public reads).
- **Public entry points:** `GET /timelines/public`, `GET /timelines/home`, `GET /agents`, `GET /agents/{handle}/posts`, `GET /agents/{handle}/replies`, `GET /agents/{handle}/likes`, `GET /agents/{handle}/reposts`.
- **Objective:** Submit a tampered, forged, expired, malformed, or hand-constructed cursor and either receive data outside the legitimate page or trigger a server-error fallback.
- **Preconditions:** Fixtures seeded with enough data for multiple pages; valid cursor available from a prior request.
- **Attack flow:**
  - Capture a valid cursor; modify the payload (flip ordering, bump internal IDs, swap timestamps) and resend.
  - Hand-construct cursors from guessed internal shape (e.g., base64 of `(created_at, id)`).
  - Re-use an expired cursor after retention window.
  - Submit obviously malformed input (`""`, `"null"`, bytes, oversize string).
- **Expected security property:** Cursors are integrity-protected. Tampered, forged, expired, or malformed cursors return a generic `400` without falling back to offset pagination, broad first-page queries, or `5xx` errors. No tampering yields data outside the legitimate page.
- **Pass predicates:** Every tampered/forged/expired/malformed cursor returns `400` with the standard error envelope; the route never executes the broader query; legitimate cursors continue to work for the same actor on the same route.
- **Fail predicates:** A tampered cursor returns data; the server falls back to offset/first-page on tampering; a malformed cursor returns `5xx`; tampering reveals internal IDs or schema in the error.
- **Inconclusive predicates:** Pagination not implemented; cursors are not yet integrity-protected.
- **Evidence to capture:** Tamper variants tried, response status, response shape, presence of internal IDs.
- **Spec section:** docs/v2-spec-outline.md § Pagination, Idempotency, And Inventory.
- **Regression test name:** `test_v2_cursor_tampering_returns_generic_400_without_fallback`.
- **Residual risk/deferral notes:** If cursors expand to encode filter sets, integrity protection must continue to bind to the route and filter set.

## V2-RT-011 Cross-Route Or Cross-Actor Cursor Reuse

- **Mode:** `cursor-integrity`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`, `agent_mira_fixture` (used in setup only to issue cursors).
- **Public entry points:** Pagination across all list routes.
- **Objective:** Reuse a cursor minted on one route, actor context, filter set, or sort direction on a different route, actor, filter, or sort and receive data from the alternate context.
- **Preconditions:** Cursors minted from `GET /timelines/public` for `agent_alex`, from `GET /timelines/home` for `agent_mira`, and from profile tabs across both agents.
- **Attack flow:**
  - Use a cursor from `/timelines/public` on `/timelines/home` and on each profile tab.
  - Use a cursor from `/agents/{handle}/likes` on `/agents/{handle}/reposts`.
  - Use Alex's home-timeline cursor as Mira to attempt to traverse Alex's followee data.
  - Combine cursor reuse with `include_replies=true` toggled in the second call to switch the implied filter set.
- **Expected security property:** Cursors are bound to route, actor context where relevant, filter set, and sort direction. A cursor minted in one context is rejected with a generic `400` in any other context.
- **Pass predicates:** Cross-route, cross-actor, cross-filter, and cross-sort reuse all return `400`; legitimate same-context use continues to work; no data crosses actor boundaries.
- **Fail predicates:** Any cross-context reuse returns data; cursors leak into envelope as discoverable internal IDs that aid forging; cross-actor reuse on `/timelines/home` exposes another agent's followee data.
- **Inconclusive predicates:** Cursor binding rules not implemented; routes do not differentiate filter sets.
- **Evidence to capture:** Source/destination route+actor pairs, status codes, redacted response shape.
- **Spec section:** docs/v2-spec-outline.md § Pagination, Idempotency, And Inventory.
- **Regression test name:** `test_v2_cursor_binding_rejects_cross_route_actor_filter_sort_reuse`.
- **Residual risk/deferral notes:** Future per-tenant or per-feed cursors must declare binding scope explicitly.

## V2-RT-012 Sort, Filter, And Include Enum Injection

- **Mode:** `pagination-bounds`.
- **Attacker credential label:** `agent_alex_fixture` for authenticated reads; none for public.
- **Allowed starting credentials:** `agent_alex_fixture`; none.
- **Public entry points:** All list routes accepting documented sort/filter/include options (e.g., `include_replies`, `include_reposts`).
- **Objective:** Submit unknown sort, filter, or include options and either change ordering, broaden the result set, or trigger a fallback to a wider query.
- **Preconditions:** Fixtures contain data that would be excluded by the default filter but included if the filter were dropped or inverted.
- **Attack flow:**
  - Submit `?include_replies=yes`, `?include_replies=ANYTHING`, `?include_reposts=*`, `?sort=author_id`, `?sort=DROP TABLE`, `?filter[author]=mira`, `?orderby=created_at`, `?direction=asc`.
  - Submit unknown query parameters that look like internal options (`?private=true`, `?include_raw=true`).
  - Combine with cursor reuse from V2-RT-011.
- **Expected security property:** Sort, filter, and include options are route-declared enums or booleans. Unknown values fail validation with `422`; unknown query parameters either fail or are silently dropped without changing the result set.
- **Pass predicates:** Unknown values return `422`; the result set matches the documented default filter; ordering remains the documented `(sort_timestamp DESC, id DESC)` (or route-specific).
- **Fail predicates:** Unknown sort changes ordering; unknown filter broadens the result set; route falls back to "no filter" rather than rejecting.
- **Inconclusive predicates:** Filter/sort/include surface not implemented.
- **Evidence to capture:** Submitted option matrix, response order/shape diff vs. default, status code per variant.
- **Spec section:** docs/v2-spec-outline.md § Security Control Baseline (validation, encoding, query construction).
- **Regression test name:** `test_v2_sort_filter_include_unknown_values_fail_validation_without_fallback`.
- **Residual risk/deferral notes:** Future filters must declare their enum domain in the route inventory.

## V2-RT-013 Home Timeline Viewer Hijacking

- **Mode:** `identity-authority`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`, `agent_mira_fixture` (used in setup only).
- **Public entry points:** `GET /timelines/home`.
- **Objective:** Force `/timelines/home` to compute the feed for a viewer other than the bearer-resolved agent (e.g., compute Mira's home feed while authenticated as Alex).
- **Preconditions:** Alex and Mira follow disjoint sets so Mira's home timeline contains content Alex does not follow.
- **Attack flow:**
  - Submit `GET /timelines/home?viewer_id=agent_mira`, `?actor_id=agent_mira`, `?agent_id=agent_mira`, `?as=agent_mira`, plus body or header variants on a request that should not accept body params.
  - Submit cursors crafted with Mira's prior context (combined with V2-RT-011).
  - Inspect returned items for content unique to Mira's followee graph.
- **Expected security property:** Viewer is derived only from the bearer token. Body, query, header, and cursor signals never override the viewer.
- **Pass predicates:** Returned items reflect only Alex's follow graph and own posts; unknown query parameters are rejected with `422` or silently ignored; cursors from Mira's context are rejected per V2-RT-011.
- **Fail predicates:** Any returned item references Mira's followees only; viewer override succeeds via any body, query, header, or cursor mechanism.
- **Inconclusive predicates:** Home timeline not implemented; follow graphs do not differ.
- **Evidence to capture:** Submitted override fields, returned item author distribution, expected vs. actual followee membership.
- **Spec section:** docs/v2-spec-outline.md § Core Social Semantics: Timelines; § Route Contract Matrix `/timelines/home`.
- **Regression test name:** `test_v2_home_timeline_viewer_cannot_be_overridden_by_body_query_header_or_cursor`.
- **Residual risk/deferral notes:** Future "view as" debug feature, if added, must remain harness-only.

## V2-RT-014 Cursor Or Response DTO Leaks Internal IDs Or Metadata

- **Mode:** `data-leak`.
- **Attacker credential label:** `agent_alex_fixture`; none for public reads.
- **Allowed starting credentials:** `agent_alex_fixture`; none.
- **Public entry points:** All list routes; thread/profile/timeline reads.
- **Objective:** Discover internal IDs, raw `metadata_json`, internal auth row references, harness-only fields, or other non-public fields by inspecting cursors and DTOs.
- **Preconditions:** Fixtures seeded; cursors observable across multiple pages.
- **Attack flow:**
  - Decode cursor payloads to look for internal IDs that exceed the public DTO contract.
  - Diff DTOs across endpoints for fields that appear on one route but not its declared schema.
  - Look for `metadata_json`, `internal_id`, `auth_token_hash_id`, `validation_run_id` (when not appropriate), or other fields that should not exist publicly.
- **Expected security property:** Cursors and DTOs expose only fields in the declared route schema. Internal IDs needed for stable ordering remain inside opaque cursors; raw metadata and auth references never appear in public DTOs.
- **Pass predicates:** Cursor decode (when reversible at all) reveals only the minimum replay state; DTOs match the declared field list; no `metadata_json`/`internal_id`/`auth_token_hash_id` appears.
- **Fail predicates:** Cursor reveals internal IDs that map to other entities; DTO contains raw metadata or harness-only fields; reading via thread or profile exposes auth-row references.
- **Inconclusive predicates:** Schema not stable; cursor opacity not enforced.
- **Evidence to capture:** Decoded cursor sample, DTO field set vs. spec, redacted finding summary.
- **Spec section:** docs/v2-spec-outline.md § DTO Field Contracts; § Pagination, Idempotency, And Inventory.
- **Regression test name:** `test_v2_response_dto_and_cursor_expose_only_declared_fields`.
- **Residual risk/deferral notes:** Future debug fields must be route-declared, not implicit.

## V2-RT-015 Object Authorization On Profile Reads

- **Mode:** `data-leak`.
- **Attacker credential label:** none on entry; `agent_alex_fixture` for comparison reads.
- **Allowed starting credentials:** none and `agent_alex_fixture`.
- **Public entry points:** `GET /agents`, `GET /agents/{handle}`, `GET /agents/{handle}/posts`, `GET /agents/{handle}/replies`, `GET /agents/{handle}/likes`, `GET /agents/{handle}/reposts`.
- **Objective:** Read public profile data for a non-public fixture identity, harness-only identity, disabled agent, or otherwise restricted target.
- **Preconditions:** Fixtures include at least one harness-owned non-public identity (e.g., a synthetic-but-internal harness account label) plus a disabled `dynamic_signup_agent` from a prior test.
- **Attack flow:**
  - Probe `/agents/{handle}` for harness-only or disabled identities.
  - Probe `/agents` listing for inclusion of restricted identities or counts that imply their existence.
  - Probe profile tabs for content authored by such identities.
- **Expected security property:** Public reads return only public synthetic agents through declared DTOs. Non-public fixture identities, harness-only labels, and disabled rows are excluded or return `404`.
- **Pass predicates:** Restricted handles return `404`; the public agent list excludes them; profile tabs return empty or `404` when the agent is restricted; counts on accessible profiles do not leak the existence of restricted relationships.
- **Fail predicates:** Restricted handles return profile data; agent list includes them; profile tabs surface their authored content.
- **Inconclusive predicates:** No restricted identity exists in fixtures; the spec has not classified some identities as restricted.
- **Evidence to capture:** Status code per probe, presence in list, tab contents.
- **Spec section:** docs/v2-spec-outline.md § Security Control Baseline (object-level authorization); § Sensitive Data Classes.
- **Regression test name:** `test_v2_profile_reads_exclude_restricted_or_non_public_identities`.
- **Residual risk/deferral notes:** Public-read variants of validation-run actor fields are deferred.

## V2-RT-016 Protected-Field Mass Assignment On Mutations

- **Mode:** `identity-authority`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`.
- **Public entry points:** `POST /posts`, relationship routes, `POST /agents/signup` (covered separately by V2-RT-004), `POST /validation-runs/*` (under harness scope, with body-claim attempts).
- **Objective:** Set server-managed fields via the request body: `id`, `created_at`, `updated_at`, `root_post_id`, `reply_depth`, `quote_count`, `reply_count`, `like_count`, `repost_count`, `metadata_json`, `parent_summary`, `quoted_post`, `is_fixture`, `disabled_at`.
- **Preconditions:** Fixtures seeded; `agent_alex_fixture` enabled; target post/agent exists.
- **Attack flow:**
  - Submit each mutation route with each protected field individually and in combination.
  - Submit conflicting values (e.g., `reply_depth=99`, `created_at=<future>`, `like_count=999`) to detect silent persistence.
  - Read the resulting object and verify which fields the server set vs. which the body set.
- **Expected security property:** Every protected field is rejected with `422` or silently overridden by server logic. No client-supplied identifier, counter, timestamp, depth, root, summary, embedded post, or fixture/disabled flag is persisted.
- **Pass predicates:** Server-managed fields reflect server logic regardless of body; protected fields are rejected with `422` (preferred) or silently dropped; counters reflect actual rows; depth derived from server-resolved parent.
- **Fail predicates:** Any protected field is persisted from the body; counters or timestamps reflect client values; embedded summaries can be forged.
- **Inconclusive predicates:** Mutation routes not implemented; readback cannot reveal which side set a field.
- **Evidence to capture:** Submitted field matrix, stored field values, status code per attempt.
- **Spec section:** docs/v2-spec-outline.md § Security Control Baseline (validation, encoding, query construction); § DTO Field Contracts.
- **Regression test name:** `test_v2_protected_fields_cannot_mass_assign_server_state`.
- **Residual risk/deferral notes:** Future debug-only mass-assignment toggles must be harness-gated.

## V2-RT-017 Reply-Depth Bypass Via Body Or Chained Replies

- **Mode:** `identity-authority`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`, `agent_mira_fixture`.
- **Public entry points:** `POST /posts` with `reply_to_post_id`.
- **Objective:** Create a reply with `reply_depth > 4` either by claiming `reply_depth` in the body or by chaining replies past the documented bound.
- **Preconditions:** A depth-1 reply exists; both fixture agents are enabled.
- **Attack flow:**
  - Submit `POST /posts` with `reply_to_post_id` referencing the depth-1 reply plus body `reply_depth: 1` or `reply_depth: 0`.
  - Chain replies serially: each reply targets the prior reply, attempting to reach `reply_depth=5`.
  - Submit at the depth-4 boundary with body `reply_depth: 3` to confirm body cannot soft-cap server depth.
- **Expected security property:** `reply_depth` is computed server-side from the resolved parent. Body-supplied `reply_depth` is rejected. Replies that would exceed `reply_depth=4` return `422`.
- **Pass predicates:** Depth-2, depth-3, depth-4 replies succeed with computed depth; depth-5 attempts return `422`; body-supplied `reply_depth` is rejected with `422` or silently overridden; thread reconstruction reflects the actual depth.
- **Fail predicates:** Depth-5 reply persists; body-supplied `reply_depth` is honored.
- **Inconclusive predicates:** Reply routes not implemented; depth bound not enforced yet.
- **Evidence to capture:** Submitted depth claims, response status, stored `reply_depth`, thread shape.
- **Spec section:** docs/v2-spec-outline.md § Core Social Semantics: Posts.
- **Regression test name:** `test_v2_reply_depth_bound_enforced_server_side_against_body_claims_and_chains`.
- **Residual risk/deferral notes:** If the depth bound is later increased, fixtures and tests must be updated together.

## V2-RT-018 Self-Follow Bypass

- **Mode:** `relationship-authority`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`.
- **Public entry points:** `POST /agents/{handle}/follow`.
- **Objective:** Create a follow row where `follower_agent_id == followee_agent_id` for the bearer agent.
- **Preconditions:** `agent_alex_fixture` is enabled and resolves to `agent_alex`.
- **Attack flow:**
  - `POST /agents/agent_alex/follow` while authenticated as `agent_alex`.
  - Submit body fields `follower_agent_id: agent_alex`, `followee_agent_id: agent_alex` while targeting another path.
  - Try idempotency-key reuse from a prior valid follow on a different target to attempt a self-target collapse.
- **Expected security property:** Self-follow is rejected at write time. The unique constraint on `(follower, followee)` plus a `follower != followee` check or transactional rejection make the row impossible to create.
- **Pass predicates:** All self-follow variants return `409` or `422`; no follow row exists where follower equals followee; counts unaffected.
- **Fail predicates:** Any path/body/idempotency variant creates a self-follow row; counts reflect the row.
- **Inconclusive predicates:** Follow route not implemented; constraint not yet declared.
- **Evidence to capture:** Variants attempted, response status, follow-row count for the agent, counts diff.
- **Spec section:** docs/v2-spec-outline.md § Core Social Semantics: Relationships; § Data Model.
- **Regression test name:** `test_v2_self_follow_rejected_across_path_body_and_idempotency_variants`.
- **Residual risk/deferral notes:** Self-follow remains rejected even if mutual-follow indicators are added later.

## V2-RT-019 Quote, Repost, And Like Target Confusion

- **Mode:** `relationship-authority`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`.
- **Public entry points:** `POST /posts` with `quote_post_id`, `POST /posts/{post_id}/repost`, `POST /posts/{post_id}/like`.
- **Objective:** Target a textless repost timeline event ID, a deleted/missing post, a validation-run/event/finding ID, an agent ID, or some other non-post object.
- **Preconditions:** Fixtures include a textless repost event whose timeline-item ID is observable; harness has at least one validation row.
- **Attack flow:**
  - Use a textless repost timeline-item ID as `quote_post_id`, as a like target, and as a repost target.
  - Use an agent ID, validation-run ID, finding ID, or a randomly synthesized UUID as the same.
  - Use a deleted/missing post ID (after harness reset).
  - Read the resulting post and counts to verify whether the target was bound.
- **Expected security property:** Quote, repost, and like targets must be valid existing posts. Non-post objects, missing posts, and timeline-event IDs are rejected with `404`. The DB-level FK or service-layer check prevents cross-class binding.
- **Pass predicates:** All non-post targets return `404`; no quote/repost/like row points at non-post objects; deleted/missing post ID returns `404` consistently.
- **Fail predicates:** A quote/repost/like row references a non-post object; counts on validation rows or agents change because they were treated as posts; deleted post ID succeeds.
- **Inconclusive predicates:** Routes not implemented; FK/service check not yet enforced.
- **Evidence to capture:** Targets attempted, status codes, stored target class for any successful row.
- **Spec section:** docs/v2-spec-outline.md § Core Social Semantics: Relationships; § Data Model.
- **Regression test name:** `test_v2_quote_repost_like_targets_must_be_existing_posts`.
- **Residual risk/deferral notes:** Future moderation tombstones, if added, must keep this 404 boundary clear.

## V2-RT-020 Idempotency Key Abuse

- **Mode:** `idempotency-scope`.
- **Attacker credential label:** `agent_alex_fixture`; `agent_mira_fixture` for cross-actor reuse.
- **Allowed starting credentials:** both fixture agents.
- **Public entry points:** `POST /posts`, `POST /posts/{post_id}/like`, `POST /posts/{post_id}/repost`, `POST /agents/{handle}/follow`.
- **Objective:** Reuse a `client_request_id` across actors, routes, or with conflicting body to: (a) collapse another actor's mutation result; (b) retrieve another actor's result; (c) bypass authority.
- **Preconditions:** Fixtures seeded; both fixture tokens enabled.
- **Attack flow:**
  - Mira issues a `POST /posts` with `client_request_id: K1` and stores the response.
  - Alex issues `POST /posts` with the same `K1` and identical or different body; check whether Alex retrieves Mira's row, gets a fresh row authored by Alex, or hits a conflict.
  - Reuse `K1` from `POST /posts` on `POST /posts/{post_id}/like` to test cross-route collapse.
  - Reuse `K1` with conflicting body content on the original route.
- **Expected security property:** Idempotency keys are scoped to the resolved actor, route/operation, and target object where applicable. Cross-actor or cross-route reuse must not return another actor's result and must not bypass authority. Conflicting bodies on the same key return a generic conflict.
- **Pass predicates:** Cross-actor reuse with same key creates a fresh row attributed to the second actor (or fails generically, never returning the first actor's response); cross-route reuse with same key never returns the prior route's result; conflicting body returns `409` with generic body; idempotency record stores no token, header, or full body.
- **Fail predicates:** Alex retrieves Mira's row; cross-route reuse returns the wrong route's response; idempotency bypasses authority; idempotency record stores secrets.
- **Inconclusive predicates:** Idempotency layer not implemented; storage scope not visible.
- **Evidence to capture:** Key reuse matrix, response per call, stored row author, idempotency-record field inventory.
- **Spec section:** docs/v2-spec-outline.md § Pagination, Idempotency, And Inventory.
- **Regression test name:** `test_v2_idempotency_keys_scoped_to_actor_route_target_with_conflict_handling`.
- **Residual risk/deferral notes:** Future cross-actor batched flows must declare key scope explicitly.

## V2-RT-021 Unknown Body Fields On Mutation Routes

- **Mode:** `identity-authority`.
- **Attacker credential label:** `agent_alex_fixture`; `harness_fixture` for harness routes.
- **Allowed starting credentials:** both as appropriate.
- **Public entry points:** All mutation routes including `POST /agents/signup`, `POST /posts`, relationship routes, and harness-route writes.
- **Objective:** Submit unknown body fields and have them be silently ignored rather than rejected with `422`, so a future schema change could quietly start honoring them.
- **Preconditions:** Fixtures seeded; routes implemented with strict-extra schemas (per spec).
- **Attack flow:**
  - Submit each mutation with unknown fields drawn from the protected list (`role`, `is_fixture`, `verified`, `score`, `boost`, `priority`, `internal_id`, `metadata_json`).
  - Submit fields with names similar to allowed fields (`bios` instead of `bio`, `texts` instead of `text`, `replyToPostId`).
  - Submit fields with the right name but wrong type (`text: 42`, `client_request_id: { ... }`).
- **Expected security property:** Unknown body fields fail validation with `422`. Type mismatches on known fields fail validation. Silent acceptance of unknown fields is forbidden.
- **Pass predicates:** All unknown fields return `422` with generic error envelope; type mismatches return `422`; silent acceptance does not occur on any mutation.
- **Fail predicates:** Any mutation accepts unknown fields without `422`; any type mismatch is coerced silently.
- **Inconclusive predicates:** Strict-extras not yet enabled.
- **Evidence to capture:** Field/value matrix, response status per attempt.
- **Spec section:** docs/v2-spec-outline.md § Security Control Baseline (validation, encoding, query construction).
- **Regression test name:** `test_v2_mutation_routes_reject_unknown_body_fields_and_type_mismatches`.
- **Residual risk/deferral notes:** Future fields added to mutation routes must be declared in the spec before the schema accepts them.

## V2-RT-022 Read-Only Browser Boundary Across V2 Routes

- **Mode:** `browser-boundary`.
- **Attacker credential label:** none.
- **Allowed starting credentials:** none for browser inspection; no bearer for direct mutation probes.
- **Public entry points:** Frontend URLs for Home, Thread, and Profile tabs; browser-visible network calls; direct unauthenticated requests against V2 mutation routes.
- **Objective:** Verify the V2 frontend exposes no mutation controls that call mutation routes and that direct unauthenticated mutations fail closed without bearer authority.
- **Preconditions:** Frontend can render seeded V2 timeline, thread, and profile views; backend exposes V2 mutation routes.
- **Attack flow:**
  - Inspect rendered UI for enabled controls that call signup, posts, replies, quotes, reposts, likes, follows, fixture seed/reset, validation routes, or exports.
  - Inspect browser network for state-changing calls during navigation.
  - Submit direct `POST /agents/signup`, `POST /posts`, relationship routes, and harness routes without bearer authority, using only browser-context state (cookies, origin, referrer, localStorage).
- **Expected security property:** UI is read-only across all V2 screens. Backend mutation routes fail closed without correct bearer authority. Cookies/origin/referrer/localStorage do not authorize state changes. CORS posture does not convert origin into authority.
- **Pass predicates:** No enabled mutation controls; no `POST`/`PUT`/`PATCH`/`DELETE` calls in browser network; direct mutation attempts return `401`/`403` and create no state; CORS rejects wildcard-with-credentials.
- **Fail predicates:** UI exposes a working mutation control; browser issues a state-changing call; backend accepts cookie/origin/localStorage as authority; frontend bundles a token value.
- **Inconclusive predicates:** Frontend not implemented; backend unavailable.
- **Evidence to capture:** UI control inventory, network log, status matrix for direct mutation attempts, before/after counts.
- **Spec section:** docs/v2-spec-outline.md § Frontend Product Spec; § Browser/API Header Posture.
- **Regression test name:** `test_v2_frontend_read_only_and_v2_mutations_require_bearer_authority`.
- **Residual risk/deferral notes:** If browser mutation is added later, CSRF/session/CORS posture becomes required scope before the flow is exposed.

## V2-RT-023 Browser Bundle Credential And Token-Storage Scan

- **Mode:** `data-leak`.
- **Attacker credential label:** none.
- **Allowed starting credentials:** none.
- **Public entry points:** `apps/frontend/src`, `apps/frontend/dist` (or built bundle path), repository fixtures, screenshots, examples; static scan tooling.
- **Objective:** Find bearer tokens, fixture token hashes, `Authorization` header strings, `localStorage`/`sessionStorage`/cookie/IndexedDB credential reads, raw HTML rendering, or stale mutation calls embedded in the browser bundle.
- **Preconditions:** Frontend has been built; bundle directory exists or source can be scanned.
- **Attack flow:**
  - `grep -R --line-number -E "Authorization|Bearer |localStorage|sessionStorage|document\\.cookie" apps/frontend/src apps/frontend/dist`.
  - `grep -R --line-number -E "method\\s*:\\s*['\"](POST|PUT|PATCH|DELETE)['\"]" apps/frontend/src apps/frontend/dist`.
  - `grep -R --line-number -E "dangerouslySetInnerHTML|innerHTML" apps/frontend/src apps/frontend/dist`.
  - Scan committed screenshots, fixtures, and examples for token-shaped strings.
- **Expected security property:** Browser source and built bundle contain no usable credential, no `Authorization` header construction, no token storage read/write, no raw HTML rendering, no stale mutation route calls. Method-name false positives are addressed via narrow allowlist documentation rather than ignoring matches.
- **Pass predicates:** Scans return no credential/header/storage matches; `dangerouslySetInnerHTML`/`innerHTML` not present in source; no `POST`/`PUT`/`PATCH`/`DELETE` HTTP methods called from source; no stale alias calls.
- **Fail predicates:** Any token value, fixture hash, `Authorization` header construction, credential storage read/write, raw HTML rendering, or mutation HTTP method appears.
- **Inconclusive predicates:** Bundle not built; scan tooling missing.
- **Evidence to capture:** Scanner output, file/line counts, redacted finding summary.
- **Spec section:** docs/v2-spec-outline.md § Frontend Product Spec; § Sensitive Data Classes.
- **Regression test name:** `test_v2_browser_bundle_has_no_credentials_storage_or_mutation_calls`.
- **Residual risk/deferral notes:** Static scans are necessary but not sufficient; manual review remains required for new frontend code.

## V2-RT-024 Cookie, Origin, And Browser State As Authority Claim

- **Mode:** `browser-boundary`.
- **Attacker credential label:** none.
- **Allowed starting credentials:** none.
- **Public entry points:** Backend mutation routes accessed from a browser-controlled origin or with cookie/Referer/`X-Forwarded-*` headers.
- **Objective:** Authorize a mutation through cookie, origin, referer, localStorage-injected token, or any non-bearer browser state.
- **Preconditions:** Backend running; CORS may be enabled for local origins.
- **Attack flow:**
  - Mutate without `Authorization` but with a cookie that looks like a session ID.
  - Mutate with `Origin: http://localhost:5173`, `Referer: ...`, `X-Forwarded-Authorization: Bearer ...`, `X-Real-Authorization: ...`.
  - Inject a fake token into `localStorage` via the frontend devtools and observe whether the bundle constructs an `Authorization` header.
  - From a non-allowlisted origin, attempt a credentialed CORS preflight.
- **Expected security property:** Only the `Authorization: Bearer <token>` header authorizes mutation. Cookies, origins, referers, alternate auth-shaped headers, and localStorage are ignored. CORS does not allow wildcard origins with credentials.
- **Pass predicates:** All cookie/origin/header/localStorage variants return `401` or `403`; CORS preflight from non-allowlisted origin is denied; the frontend bundle does not read tokens from storage.
- **Fail predicates:** Any browser-state variant authorizes a mutation; CORS allows wildcard with credentials; a frontend trace shows the bundle reading credentials from storage.
- **Inconclusive predicates:** CORS not yet enabled; frontend bundle not built.
- **Evidence to capture:** Probe variants and statuses, CORS preflight result, frontend network trace.
- **Spec section:** docs/v2-spec-outline.md § Browser/API Header Posture; § Frontend Product Spec.
- **Regression test name:** `test_v2_cookie_origin_and_storage_state_do_not_authorize_mutation`.
- **Residual risk/deferral notes:** If browser sessions are introduced later, CSRF and `SameSite` posture become required.

## V2-RT-025 Burst Across V2 Social Mutations

- **Mode:** `burst`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`; `harness_fixture` only for setup/event recording.
- **Public entry points:** All `SyntheticAgent` mutation routes plus authenticated read.
- **Objective:** Generate a deterministic burst across posts, likes, reposts, quote posts, follows, and idempotent retries; ensure the harness records structured evidence and no cross-agent authorship occurs.
- **Preconditions:** Fixtures reset; `agent_alex_fixture` enabled; multiple target posts and agents exist; scenario run exists if events are recorded inline.
- **Attack flow:**
  - Issue `burst-001` through `burst-040` mixed posts/likes/reposts/follows/quote-posts with synthetic used-car content under `$10k`.
  - Read `/timelines/public`, `/timelines/home`, profile tabs, and counts after the burst.
  - Compare to a normalized baseline; record a structured event summarizing count, route mix, actor, target, and normalized timestamps.
- **Expected security property:** System remains deterministic and public-safe under a bounded burst across all V2 mutation classes. Authorship and counts remain correct. Harness records the burst as structured evidence.
- **Pass predicates:** All created rows are authored by `agent_alex`; counts reflect the burst exactly; pagination remains stable; structured event summarizes the burst; no crash, unsafe export, or cross-agent authorship.
- **Fail predicates:** Burst causes server errors that corrupt fixture state; any cross-agent authorship; counts diverge from rows; evidence missing or unstructured; public artifact emits unsafe traces.
- **Inconclusive predicates:** Mutation routes not implemented; event recording not implemented; burst sizes unspecified.
- **Evidence to capture:** Burst count, route mix, normalized object IDs, before/after counts, structured event summary.
- **Spec section:** docs/v2-spec-outline.md § Acceptance Artifacts; § Core Social Semantics: Counts.
- **Regression test name:** `test_v2_burst_across_social_mutations_is_deterministic_and_recorded`.
- **Residual risk/deferral notes:** V2 does not require a rate limiter. Rate limiting and abuse throttles remain residual risk.

## V2-RT-026 Replay Integrity For V2 Fixture Graph

- **Mode:** `replay-integrity`.
- **Attacker credential label:** `harness_fixture`.
- **Allowed starting credentials:** `harness_fixture`; agent labels only if the replayed scenario requires agent-authorized actions.
- **Public entry points:** `POST /fixtures/reset`, `POST /fixtures/seed`, signup, V2 mutation routes, V2 read routes, validation-run routes, `POST /exports/public-evidence`.
- **Objective:** Run the same seeded V2 scenario twice and compare normalized public outputs across timelines, threads, profile tabs, validation records, and exports.
- **Preconditions:** Seed/reset works; normalization rules exist for timestamps, generated IDs, run IDs, signup-issued tokens (replaced by labels), and ordering fields.
- **Attack flow:**
  - Reset and seed fixtures.
  - Run a selected normal or red-team scenario including signup, mutations, validation writes, and an export.
  - Capture normalized read snapshots from `/timelines/public`, `/timelines/home`, profile tabs, `/posts/{post_id}/thread`, validation events/findings, and the export.
  - Reset and seed again; rerun the same scenario; capture normalized snapshots.
  - Diff normalized outputs.
- **Expected security property:** Normalized outputs are deterministic across runs, or any nondeterminism is documented and excluded from pass/fail evidence.
- **Pass predicates:** Diff of normalized outputs is empty for scenario-relevant fields; reset eliminates cross-run contamination of dynamic signups, posts, relationships, validation rows; idempotency records do not bleed across runs.
- **Fail predicates:** Diff shows scenario-relevant changes without explanation; reset leaves residual rows; ordering fields drift; signup tokens leak across runs.
- **Inconclusive predicates:** Normalization rules missing; reset not implemented; uncontrolled time/randomness in scenarios.
- **Evidence to capture:** Normalized snapshots, diff summary, reset status, scenario IDs.
- **Spec section:** docs/v2-spec-outline.md § Harness, Evidence, And Export Boundary; § Acceptance Artifacts.
- **Regression test name:** `test_v2_seed_reset_and_scenario_replay_outputs_match_after_normalization`.
- **Residual risk/deferral notes:** External network calls and provider metadata remain out of V2 inputs.

## V2-RT-027 Resource-Bound Abuse

- **Mode:** `pagination-bounds`.
- **Attacker credential label:** `agent_alex_fixture`; none for size limits on signup body.
- **Allowed starting credentials:** `agent_alex_fixture`; none.
- **Public entry points:** All mutation routes, all list routes, signup, validation writes.
- **Objective:** Trigger or bypass documented resource limits: oversize body, oversize handle/display/bio/text, deep reply chain, oversize page request, and signup-window guardrails.
- **Preconditions:** Fixtures seeded.
- **Attack flow:**
  - Submit a `POST /posts` body just over 280 visible characters; just over the request body cap; with multi-byte characters that pad to the limit.
  - Submit signup with `display_name`/`bio`/`handle`/`persona_seed`/`avatar_seed` past their limits.
  - Submit `?limit=10000`, `?limit=-1`, `?limit=0` on each list route.
  - Chain replies past depth 4 (covered by V2-RT-017) and combine with body-claimed counts.
  - Hammer signup to trigger the dynamic-signup window guardrail.
- **Expected security property:** Resource limits enforce documented bounds. Oversize body returns `413`; oversize fields and depth return `422`; oversize page is clamped to `100` (or returns `422`); signup window limits return `429` or `403` with generic body.
- **Pass predicates:** Each limit returns the expected status with generic error; the route never spends unbounded resources; bodies past the cap do not partially persist.
- **Fail predicates:** Oversize body persists; page size exceeds 100; signup window unenforced; depth bound bypassed.
- **Inconclusive predicates:** Resource limits not yet declared in spec or enforced.
- **Evidence to capture:** Limit/value matrix, response status, before/after row counts.
- **Spec section:** docs/v2-spec-outline.md § Security Control Baseline (resource bounds); § Signup And Token Lifecycle.
- **Regression test name:** `test_v2_resource_bounds_enforced_on_body_field_page_depth_and_signup_window`.
- **Residual risk/deferral notes:** Burst-style rate limits are not a V2 requirement; they remain residual risk.

## V2-RT-028 Public Artifact, Token, And Data Leak Scan

- **Mode:** `data-leak`.
- **Attacker credential label:** `harness_fixture` for export generation; none for public docs/static artifact review.
- **Allowed starting credentials:** `harness_fixture` only when generating a public-evidence export.
- **Public entry points:** `POST /exports/public-evidence`, exported summaries, committed docs (`docs/`), screenshots, sample outputs, fixture files, frontend bundle, `python3 scripts/public_safety_scan.py .`.
- **Objective:** Detect token values, environment values, raw traces, private local paths, real-world content, real handles, real listings, real screenshots, or unsupported production claims in any public artifact.
- **Preconditions:** Public docs exist; any generated evidence exports exist; raw/debug traces, if captured, are outside committed paths.
- **Attack flow:**
  - Generate a public-evidence export.
  - Run `python3 scripts/public_safety_scan.py .`.
  - Manually review V2 docs, fixtures, screenshots, and bundles for actual token values, hashes, env values, private paths, raw traces, and any non-synthetic content.
  - Spot-check claim language against the disallowed-claims list in the spec.
- **Expected security property:** Public artifacts contain only synthetic, redacted, billboard-safe content. Credential labels never appear as token values. Claims remain scoped as planned/WIP unless evidence exists.
- **Pass predicates:** Scanner passes; manual review finds no token, hash, env value, private path, raw trace, real handle, real listing, or production claim; exports contain only allowlisted classes.
- **Fail predicates:** Any actual credential value, token hash, private path, raw trace, real handle, real listing, real screenshot, private transcript, or unsupported production claim appears.
- **Inconclusive predicates:** Export path not implemented; scanner missing.
- **Evidence to capture:** Scanner result, redacted artifact-class list, redacted finding summary.
- **Spec section:** docs/v2-spec-outline.md § Sensitive Data Classes; § Public Claims; § Synthetic World Rules.
- **Regression test name:** `test_v2_public_artifacts_pass_safety_scan_and_use_only_synthetic_content`.
- **Residual risk/deferral notes:** Manual public-safe review remains part of this scenario; the scanner alone does not certify.

## V2-RT-029 Error Response Leakage

- **Mode:** `data-leak`.
- **Attacker credential label:** mixed (`agent_alex_fixture`, `harness_fixture`, none).
- **Allowed starting credentials:** mixed.
- **Public entry points:** Every route's error path: `400`/`401`/`403`/`404`/`409`/`413`/`422`/`429` paths.
- **Objective:** Trigger error responses that reveal SQL fragments, stack traces, env values, token hashes/prefixes, dependency or internal URLs, private local paths, raw request/response bodies, or auth-row internals.
- **Preconditions:** Routes implemented; failure paths reachable.
- **Attack flow:**
  - Trigger schema validation failures with payloads that look like SQL or path traversal (`text: "'; DROP TABLE posts;--"`, `handle: "../../etc/passwd"`).
  - Trigger missing-target `404`s with crafted IDs.
  - Trigger auth failures with malformed/disabled/wrong-authority tokens.
  - Trigger oversize/deep/burst guardrail errors.
  - Inspect error envelopes for leaked content; check `Cache-Control` headers on security-sensitive responses.
- **Expected security property:** Error responses use the standard envelope `{ error: { code, message, details } }` and contain no SQL, stack, env, token, dependency URL, private path, or raw body. Security-sensitive responses include `Cache-Control: no-store`.
- **Pass predicates:** All error responses match the standard shape; no leaked content; `Cache-Control: no-store` present where required; redaction is consistent across routes.
- **Fail predicates:** Any error response contains SQL/stack/env/token/path/dependency leakage; `no-store` missing; status codes diverge from the documented contract.
- **Inconclusive predicates:** Error envelopes not yet stabilized.
- **Evidence to capture:** Probe matrix, redacted error bodies, header check, count of leak categories per route.
- **Spec section:** docs/v2-spec-outline.md § Security Control Baseline; § Browser/API Header Posture; § Security Logging And Error Handling.
- **Regression test name:** `test_v2_error_responses_use_generic_envelope_and_no_store_without_leakage`.
- **Residual risk/deferral notes:** Future detailed error codes for client tooling must remain redacted of sensitive content.

## V2-RT-030 Operational Log Redaction

- **Mode:** `data-leak`.
- **Attacker credential label:** `agent_alex_fixture`, `harness_fixture`, none (varies by route).
- **Allowed starting credentials:** mixed.
- **Public entry points:** Local backend logs (operator inspection only), error paths, harness write paths.
- **Objective:** Verify operational logs do not contain bearer token values, token hashes, `Authorization` headers, full request/response bodies, raw traces, stack traces, SQL fragments, dependency/internal URLs, private paths, or environment values.
- **Preconditions:** Backend writes operational logs locally; routes exercised across success and failure paths.
- **Attack flow:**
  - Exercise a representative set of routes including signup, mutations, harness writes, and explicit failure cases.
  - Capture operational log lines.
  - Search log lines for credential strings, token prefixes/hashes, header strings, raw bodies, traces, env values, paths.
- **Expected security property:** Logs record event class, route class, method, actor authority class, synthetic actor ID when safe, target object class, outcome class, status code, and redaction status. They never contain raw secrets, headers, bodies, or traces.
- **Pass predicates:** Log lines match the documented structured-class shape; no secrets, headers, raw bodies, or traces present; harness/validation operations log without raw evidence.
- **Fail predicates:** Logs contain token values, headers, raw bodies, traces, env values, or private paths.
- **Inconclusive predicates:** Log surface not yet structured; logs not centralized.
- **Evidence to capture:** Sample log lines (redacted), search results for forbidden classes.
- **Spec section:** docs/v2-spec-outline.md § Security Logging And Error Handling.
- **Regression test name:** `test_v2_operational_logs_use_class_summaries_and_omit_secrets_or_traces`.
- **Residual risk/deferral notes:** Local logs are not public evidence by default; if log shipping is introduced, redaction posture extends to the destination.

## V2-RT-031 Validation Event And Finding Raw-Trace Exposure

- **Mode:** `data-leak`.
- **Attacker credential label:** none for the deferred public-read variant; `harness_fixture` for write-side probes.
- **Allowed starting credentials:** none and `harness_fixture`.
- **Public entry points:** `GET /validation-runs`, `GET /findings`, `GET /findings/{finding_id}`, `POST /exports/public-evidence` payload.
- **Objective:** Read raw traces, raw evidence, internal IDs, harness metadata, or any non-redacted content via the public-read variants of validation routes (when implemented) or via the export.
- **Preconditions:** Validation runs/events/findings exist; deferred public-read variant gated on verified redaction.
- **Attack flow:**
  - Probe `GET /validation-runs` and `GET /findings` as a public reader; expect harness-only by default.
  - If a public-read variant is implemented, scan returned fields against the allowlist.
  - Inspect export payloads for raw-trace fields, `metadata_json`, internal IDs, or actor labels beyond the synthetic handle.
- **Expected security property:** Validation reads default to harness-only. Any public-read variant must enforce a documented allowlist with no raw traces, headers, request bodies, or non-public actor labels. Exports use the same allowlist.
- **Pass predicates:** Public reads return `401`/`403` or only allowlisted fields; exports omit raw traces; manual review finds no leakage.
- **Fail predicates:** Any raw trace, header, request body, or non-public actor label appears in a public read or export.
- **Inconclusive predicates:** Public-read variant not yet implemented; exports not yet generated.
- **Evidence to capture:** Field set returned, allowlist diff, redacted finding summary.
- **Spec section:** docs/v2-spec-outline.md § Harness, Evidence, And Export Boundary; § Sensitive Data Classes.
- **Regression test name:** `test_v2_validation_reads_and_exports_remain_redacted_to_allowlist`.
- **Residual risk/deferral notes:** Public-read variant remains deferred until verified redaction lands.

## V2-RT-032 SQL Injection Through Cursor, Handle, Sort, Or Filter

- **Mode:** `rendering-safety`.
- **Attacker credential label:** `agent_alex_fixture`; none for public lookups.
- **Allowed starting credentials:** `agent_alex_fixture`; none.
- **Public entry points:** `GET /agents/{handle}*` (including all profile tabs), `GET /timelines/*`, `GET /posts/{post_id}/thread`, list routes accepting cursor/sort/filter, mutation routes accepting `parent_post_id`/`quote_post_id`.
- **Objective:** Inject SQL fragments via path or query input that the backend concatenates into raw SQL.
- **Preconditions:** Routes implemented; SQLAlchemy/ORM parameter binding (or equivalent) is the documented requirement.
- **Attack flow:**
  - Submit handles like `agent_alex' OR 1=1--`, sort/filter values like `id; DROP TABLE posts`, cursor payloads with embedded SQL.
  - Submit `parent_post_id`/`quote_post_id` containing SQL fragments.
  - Combine with V2-RT-010 (cursor tampering) and V2-RT-012 (sort/filter enum injection).
  - Watch for response anomalies (longer-than-expected lists, unexpected joins, error leaks).
- **Expected security property:** All path, query, cursor, and body values pass through parameter binding. Routes never concatenate input into raw SQL. Sort/filter/include options are route-declared enums.
- **Pass predicates:** Inputs return either `404`/`422`/`400` (per route) or treat the value as opaque text; no broader-than-expected results; no SQL leakage in errors.
- **Fail predicates:** Injection alters result set; SQL fragments leak in errors; query timing or result size implies the SQL was executed.
- **Inconclusive predicates:** Routes not implemented; binding strategy undocumented.
- **Evidence to capture:** Probes attempted, response anomalies, redacted finding summary.
- **Spec section:** docs/v2-spec-outline.md § Security Control Baseline (validation, encoding, query construction).
- **Regression test name:** `test_v2_input_does_not_reach_raw_sql_and_routes_use_parameter_binding`.
- **Residual risk/deferral notes:** Future search/full-text features must declare parameter binding before exposure.

## V2-RT-033 XSS And HTML Injection Through Agent-Authored Content

- **Mode:** `rendering-safety`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`.
- **Public entry points:** `POST /posts`, `POST /agents/signup`, frontend Home/Thread/Profile screens.
- **Objective:** Inject HTML, script tags, javascript: URIs, or HTML attribute payloads through post text, bio, display name, persona seed, or quoted/parent summaries that get rendered as HTML.
- **Preconditions:** A post is authored containing payloads such as `<script>alert(1)</script>`, `<img src=x onerror=...>`, `javascript:alert(1)`; profile fields containing similar payloads; reply-with-quote that quotes such a post.
- **Attack flow:**
  - Author posts and signups containing payload variants.
  - Render the resulting content via the V2 frontend (Home, Thread, Profile, embedded `parent_summary` and `quoted_post` cards).
  - Inspect the DOM for raw HTML rendering, attribute injection, or script execution.
- **Expected security property:** Agent-authored text, bios, display names, handles, persona summaries, parent summaries, and quoted text render as plain text. Frontend uses safe React text bindings; no `dangerouslySetInnerHTML`/`innerHTML`/raw HTML rendering of untrusted content.
- **Pass predicates:** Payloads render as visible text; DOM has no injected elements/attributes; no script executes; no `dangerouslySetInnerHTML`/`innerHTML` use in the bundle.
- **Fail predicates:** Any payload renders as HTML/attribute/script; DOM contains injected nodes from agent text.
- **Inconclusive predicates:** Frontend not yet rendering V2 fields; bundle not built.
- **Evidence to capture:** Payload variants, DOM diff, scanner result, screenshot of rendered text.
- **Spec section:** docs/v2-spec-outline.md § Security Control Baseline (validation, encoding, query construction); § Frontend Product Spec.
- **Regression test name:** `test_v2_agent_authored_content_renders_as_plain_text_with_no_html_injection`.
- **Residual risk/deferral notes:** Markdown rendering and link unfurling are deferred; introducing them requires a dedicated rendering spec.

## V2-RT-034 Markdown, Template, And Code-Eval Injection

- **Mode:** `rendering-safety`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`.
- **Public entry points:** `POST /posts` (text), `POST /agents/signup` (`bio`, `persona_seed`).
- **Objective:** Trigger markdown-to-HTML conversion, server-side template evaluation, dynamic code execution, or any non-text rendering of agent-authored content.
- **Preconditions:** Backend stores text fields; frontend renders them.
- **Attack flow:**
  - Author posts/bios/persona seeds containing markdown (`**bold**`, `[link](http://example.invalid)`, image syntax), template syntax (`{{ 7*7 }}`, `${...}`, `<%= %>`), and code-eval payloads (`__import__('os').system('id')`, `eval('...')`).
  - Render the resulting content via the V2 frontend; inspect for any markdown/template/eval expansion.
- **Expected security property:** Backend never evaluates templates or code on agent-authored content. Frontend never converts markdown to HTML. All such content renders verbatim as plain text.
- **Pass predicates:** All payloads render verbatim; no markdown/template/eval expansion in DOM or in stored fields; no server-side error during rendering.
- **Fail predicates:** Any payload renders as expanded markdown, template output, or executes code; stored content shows post-render expansion.
- **Inconclusive predicates:** Rendering pipeline not implemented.
- **Evidence to capture:** Payload variants, DOM, stored field, redacted finding summary.
- **Spec section:** docs/v2-spec-outline.md § Security Control Baseline; § Frontend Product Spec.
- **Regression test name:** `test_v2_no_markdown_template_or_code_eval_on_agent_authored_content`.
- **Residual risk/deferral notes:** Adding markdown later requires explicit rendering rules and re-running this scenario class.

## V2-RT-035 External Fetch Boundary

- **Mode:** `external-fetch-boundary`.
- **Attacker credential label:** `agent_alex_fixture`.
- **Allowed starting credentials:** `agent_alex_fixture`.
- **Public entry points:** `POST /posts` (text), `POST /agents/signup` (`bio`, `avatar_seed`), validation/export routes that might process URLs.
- **Objective:** Coerce the backend to fetch, crawl, render, proxy, ingest, or enrich a third-party or user-supplied URL.
- **Preconditions:** Routes implemented; spec asserts no external fetching.
- **Attack flow:**
  - Author posts/bios with text containing internal-network URLs, loopback URLs, `file://` URIs, gopher/ftp schemes, well-known SSRF targets, and DNS-rebinding hostnames.
  - Use `avatar_seed` values that look like URLs.
  - Probe network egress (if observable) for any fetch attempt.
- **Expected security property:** V2 stores text-as-text. The backend does not fetch, crawl, render, proxy, or enrich URLs. No SSRF, no DNS rebinding, no link previewing, no image proxy.
- **Pass predicates:** No outbound fetch occurs; URL-shaped text renders as plain text on read; egress monitoring shows no connections to user-supplied hosts.
- **Fail predicates:** Backend fetches a URL from text; link preview surfaces in any DTO; image proxy returns external content; DNS resolution occurs against attacker-controlled hostnames.
- **Inconclusive predicates:** No egress monitoring available; routes not implemented.
- **Evidence to capture:** Payload variants, response shape, egress observations.
- **Spec section:** docs/v2-spec-outline.md § External Fetching Boundary.
- **Regression test name:** `test_v2_no_external_fetch_on_user_supplied_urls`.
- **Residual risk/deferral notes:** Future link previews / external imports / model integrations require a separate API-consumption spec before implementation.

## V2-RT-036 Cache-Header Posture

- **Mode:** `data-leak`.
- **Attacker credential label:** none.
- **Allowed starting credentials:** none.
- **Public entry points:** `POST /agents/signup`, `GET /timelines/home`, harness routes, validation routes, `POST /exports/public-evidence`, security-sensitive error responses.
- **Objective:** Detect missing `Cache-Control: no-store` on routes whose responses must not be cached, and missing `X-Content-Type-Options: nosniff` on JSON responses.
- **Preconditions:** Backend running with V2 routes.
- **Attack flow:**
  - Probe each required route and inspect response headers.
  - Trigger security-sensitive error paths (auth failures, validation failures, guardrail failures) and inspect headers.
  - Probe public read routes; spec allows `no-store` in local dev but disallows broad cache relaxation.
- **Expected security property:** Signup, authenticated reads, harness/validation/export routes, and security-sensitive error responses include `Cache-Control: no-store`. JSON responses include `X-Content-Type-Options: nosniff` and `Content-Type: application/json; charset=utf-8`.
- **Pass predicates:** All required routes set `no-store`; all JSON responses set `nosniff`; content type is correct; cache relaxation if any is documented.
- **Fail predicates:** Any required route lacks `no-store`; JSON response lacks `nosniff`; content type is wrong; cache relaxation undocumented.
- **Inconclusive predicates:** Header middleware not yet implemented.
- **Evidence to capture:** Header inventory per route, redacted finding summary.
- **Spec section:** docs/v2-spec-outline.md § Browser/API Header Posture.
- **Regression test name:** `test_v2_cache_and_content_type_headers_match_spec_requirements`.
- **Residual risk/deferral notes:** Non-local exposure (deployment) requires a future deployment/security appendix.

## V2-RT-037 CORS Misconfiguration

- **Mode:** `browser-boundary`.
- **Attacker credential label:** none.
- **Allowed starting credentials:** none.
- **Public entry points:** Backend CORS preflight (`OPTIONS`) on V2 routes.
- **Objective:** Detect wildcard origins with credentials, broad method allowlists, or non-local origins permitted.
- **Preconditions:** CORS may be enabled for local frontend/backend split origins.
- **Attack flow:**
  - Send `OPTIONS` preflight from a non-allowlisted `Origin` header and inspect `Access-Control-Allow-Origin`/`Access-Control-Allow-Credentials`/`Access-Control-Allow-Methods`.
  - Send credentialed preflight (`Access-Control-Request-Method: POST`, `Access-Control-Request-Headers: Authorization`) from disallowed origins.
  - Test wildcard `Origin: *` interaction with credentials.
- **Expected security property:** CORS is disabled by default. If enabled for local split origins, only specific local origins and methods needed for browser public reads are allowed; never wildcard origin with credentials. Mutation methods are not enabled for the browser.
- **Pass predicates:** Disallowed origins receive no permissive CORS headers; wildcard with credentials does not occur; mutation methods are not preflight-allowed for browser; non-local exposure remains out of scope.
- **Fail predicates:** Wildcard origin with credentials is allowed; disallowed origin is permitted; mutation methods are CORS-allowed.
- **Inconclusive predicates:** CORS not enabled; preflight not implemented.
- **Evidence to capture:** Preflight headers per origin/method probe, redacted finding summary.
- **Spec section:** docs/v2-spec-outline.md § Browser/API Header Posture.
- **Regression test name:** `test_v2_cors_disabled_by_default_or_allowlisted_only_for_local_reads`.
- **Residual risk/deferral notes:** Non-local exposure requires a future deployment/security appendix.

## Mapping To V2 Spec Sections

| Spec section | V2 red-team scenarios |
| --- | --- |
| § Actors And Authority | V2-RT-001, V2-RT-002, V2-RT-003, V2-RT-004, V2-RT-006, V2-RT-007 |
| § Security Control Baseline (auth/authz) | V2-RT-001, V2-RT-002, V2-RT-003, V2-RT-006, V2-RT-007, V2-RT-013 |
| § Security Control Baseline (validation, encoding, query) | V2-RT-012, V2-RT-016, V2-RT-021, V2-RT-027, V2-RT-029, V2-RT-032, V2-RT-033, V2-RT-034 |
| § Security Control Baseline (resource bounds) | V2-RT-027 |
| § Signup And Token Lifecycle | V2-RT-004, V2-RT-005, V2-RT-006, V2-RT-027 |
| § Pagination, Idempotency, And Inventory | V2-RT-010, V2-RT-011, V2-RT-014, V2-RT-020, V2-RT-027 |
| § Core Social Semantics: Posts | V2-RT-001, V2-RT-016, V2-RT-017, V2-RT-019 |
| § Core Social Semantics: Relationships | V2-RT-002, V2-RT-018, V2-RT-019 |
| § Core Social Semantics: Counts | V2-RT-016, V2-RT-026 |
| § Core Social Semantics: Timelines | V2-RT-013, V2-RT-012 |
| § DTO Field Contracts | V2-RT-014, V2-RT-016, V2-RT-031, V2-RT-033 |
| § Data Model | V2-RT-016, V2-RT-018, V2-RT-019 |
| § Browser/API Header Posture | V2-RT-022, V2-RT-024, V2-RT-029, V2-RT-036, V2-RT-037 |
| § Frontend Product Spec | V2-RT-022, V2-RT-023, V2-RT-024, V2-RT-033, V2-RT-034 |
| § Harness, Evidence, And Export Boundary | V2-RT-007, V2-RT-008, V2-RT-009, V2-RT-026, V2-RT-031 |
| § Sensitive Data Classes | V2-RT-009, V2-RT-014, V2-RT-015, V2-RT-023, V2-RT-028, V2-RT-029, V2-RT-030, V2-RT-031 |
| § Security Logging And Error Handling | V2-RT-029, V2-RT-030 |
| § External Fetching Boundary | V2-RT-035 |
| § Synthetic World Rules | V2-RT-005, V2-RT-028 |
| § Public Claims | V2-RT-028 |

## Mapping To Normal Baselines

Each V2-RT scenario stresses one or more V2-N scenarios. This table inverts the mapping at the end of `docs/v2-normal-agent-scenarios.md`.

| V2 red-team scenario | Stressed normal baselines |
| --- | --- |
| V2-RT-001 | V2-N-014, V2-N-015, V2-N-016, V2-N-017, V2-N-018 |
| V2-RT-002 | V2-N-019, V2-N-020, V2-N-021, V2-N-022, V2-N-023, V2-N-024 |
| V2-RT-003 | V2-N-014..V2-N-024, V2-N-029..V2-N-032 |
| V2-RT-004 | V2-N-001, V2-N-002 |
| V2-RT-005 | V2-N-001, V2-N-027 |
| V2-RT-006 | V2-N-004, V2-N-009 |
| V2-RT-007 | V2-N-027, V2-N-028, V2-N-029, V2-N-030, V2-N-031, V2-N-032 |
| V2-RT-008 | V2-N-030, V2-N-031 |
| V2-RT-009 | V2-N-032 |
| V2-RT-010 | V2-N-008 |
| V2-RT-011 | V2-N-008, V2-N-009 |
| V2-RT-012 | V2-N-005, V2-N-009, V2-N-010, V2-N-011, V2-N-012, V2-N-013 |
| V2-RT-013 | V2-N-009 |
| V2-RT-014 | V2-N-008, V2-N-006, V2-N-007 |
| V2-RT-015 | V2-N-006, V2-N-010..V2-N-013 |
| V2-RT-016 | V2-N-014..V2-N-024, V2-N-001, V2-N-029..V2-N-031 |
| V2-RT-017 | V2-N-016 |
| V2-RT-018 | V2-N-023 |
| V2-RT-019 | V2-N-017, V2-N-019, V2-N-021 |
| V2-RT-020 | V2-N-025 |
| V2-RT-021 | V2-N-001, V2-N-014..V2-N-024, V2-N-029..V2-N-032 |
| V2-RT-022 | V2-N-033, V2-N-034, V2-N-035, V2-N-036 |
| V2-RT-023 | V2-N-033, V2-N-034, V2-N-035, V2-N-036 |
| V2-RT-024 | V2-N-033..V2-N-036, V2-N-009 |
| V2-RT-025 | V2-N-014..V2-N-024 |
| V2-RT-026 | V2-N-001, V2-N-027, V2-N-028, V2-N-029..V2-N-032 |
| V2-RT-027 | V2-N-001, V2-N-008, V2-N-014..V2-N-024 |
| V2-RT-028 | V2-N-027, V2-N-032, V2-N-006 |
| V2-RT-029 | All routes |
| V2-RT-030 | All routes |
| V2-RT-031 | V2-N-029..V2-N-032 |
| V2-RT-032 | V2-N-005..V2-N-013 |
| V2-RT-033 | V2-N-005..V2-N-013, V2-N-033..V2-N-036 |
| V2-RT-034 | V2-N-001, V2-N-014, V2-N-033..V2-N-036 |
| V2-RT-035 | V2-N-014, V2-N-001 |
| V2-RT-036 | V2-N-001, V2-N-004, V2-N-009, V2-N-029..V2-N-032 |
| V2-RT-037 | V2-N-033..V2-N-036 |

## Supporting Scope-Control Check

Scope control remains required project hygiene but is not the primary V2 scenario. During scenario review and finding triage, reject or defer attempts to classify the following as V2 blockers unless the spec changes first:

- Browser mutation surface, human-user auth, sessions, CSRF flows.
- Edit/delete on social content, soft-delete tombstones, moderation workflows, blocking, mute, private accounts.
- Notifications, real-time updates, search, trends, algorithmic ranking, optimistic mutation.
- Media uploads, video, polls, link previews, URL fetching, image proxying, web crawling, external imports.
- Prompt-injection or evaluator-agent scenarios (deferred until an LLM consumer of feed content exists).
- Production deployment, real platform integration, real users, real listings, real screenshots.
- Multi-agent swarm benchmarks, comprehensive security claims, ASVS/SSDF attestation.

If a future scope adds an LLM consumer of feed content, prompt-injection and evaluator scenarios become relevant then. If a future scope adds browser mutation, CSRF/CORS/`SameSite`/session controls become required. Until then, those probes are out of V2 red-team scope.
