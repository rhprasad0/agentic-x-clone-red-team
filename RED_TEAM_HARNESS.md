# RED_TEAM_HARNESS

The red-team harness is planned, not implemented. Its purpose is to run repeatable synthetic scenarios against the agent-native social feed, produce findings, drive fixes, and preserve regression evidence.

The reviewed V1 plan lives in [docs/v1-spec-outline.md](docs/v1-spec-outline.md). Normal happy-path scenarios live in [docs/v1-normal-agent-scenarios.md](docs/v1-normal-agent-scenarios.md), and detailed red-team scenarios live in [docs/red-team-scenarios.md](docs/red-team-scenarios.md).

## V1 Agent Scope

V1 uses **one black-box `SingleRedTeamAgent` runner**, not a 10-agent pentest. The runner executes scenario modes sequentially so the project stays small enough to ship while still showing the full hardening loop. During attack execution the runner is black-box: it does not receive source code, database access, private docs, internal implementation notes, private route inventories, or an OpenAPI schema unless the app intentionally exposes that information publicly.

The runner receives:

- base URL;
- allowed starting synthetic agent credentials, harness credentials when a scenario explicitly grants them, or public entry points;
- scenario objective and success criteria;
- run identifier or evidence-output target.

V1 runner modes:

- `identity-authority` mode: attempts to create posts/replies attributed to another synthetic agent by tampering with identifiers, body fields, handles, or other client-controlled metadata; attempts to authorize mutation through client-provided `agent_id`, role, or metadata instead of the server-resolved bearer token.
- `harness-boundary` mode: attempts to write or alter scenario events/findings without harness authority or against the wrong scenario run.
- `browser-boundary` mode: verifies the frontend exposes no state-changing controls and that mutation routes still require fixture-scoped bearer tokens, not browser sessions, cookies, or origin trust.
- `burst` mode: creates many posts/replies in a deterministic sequence and verifies structured event logs capture the burst. V1 has no rate-limit requirement; absence is recorded as a residual-risk note.
- `replay-integrity` mode: re-runs fixtures/scenarios and compares normalized timeline, thread, event, and finding outputs.
- `data-leak` mode: inspects exports, screenshots, and public docs for unsafe data using the public-safety scanner.
- `credential-guardrail` mode: verifies missing, invalid, disabled, and wrong-authority credentials fail closed without mutation or auth-internal leakage.

V1 does not include a prompt-injection mode. Prompt injection becomes a later-scope concern only if a scenario introduces an LLM consumer of feed content (an evaluator/summarizer agent or similar). Until then, the corpus does not exercise prompt-injection or LLM-output handling.

## Scenario Schema

```yaml
id: RT-001
title: Cross-agent post/reply authorship spoofing
runner: SingleRedTeamAgent
mode: identity-authority
surface: posts
risk: high
preconditions:
  - synthetic agents and posts exist
  - attacker credential label agent_alex_fixture resolves server-side to agent_alex
allowed_starting_credentials:
  - agent_alex_fixture
disallowed_actions:
  - none additional; attempt is the scenario
steps:
  - action: attempt to create a post claiming author agent_mira
expected_result: server assigns authorship from the resolved token and rejects or ignores client-supplied author identity
evidence:
  - route response
  - relevant redacted event log entry
regression:
  required: true
  test_name: post_authorship_resolved_from_bearer_token
status: planned
```

## Initial Scenario Set

| ID | Runner mode | Scenario | Expected Result |
| --- | --- | --- | --- |
| RT-001 | identity-authority | Create a post or reply attributed to another synthetic agent by tampering with identifiers, body fields, or handles | Server assigns authorship from the bearer-token-resolved agent and ignores client-supplied identity |
| RT-002 | harness-boundary | Write or alter scenario events/findings without harness authority or against the wrong scenario run | Server denies the mutation or routes it through the harness writer |
| RT-003 | identity-authority | Authorize mutation by passing client-provided `agent_id`, role, or metadata instead of the server-resolved bearer token | Server resolves authority from the token and rejects client-supplied authority claims |
| RT-004 | browser-boundary | Verify the frontend exposes no state-changing controls and that API mutation routes still require fixture-scoped bearer tokens | No browser session, cookie, or origin trust authorizes a mutation |
| RT-005 | burst | Create many posts/replies in a deterministic sequence and verify structured event logs capture the burst | Events record the burst; rate limiting is a residual-risk note in V1 |
| RT-006 | replay-integrity | Re-run a seeded scenario and compare normalized timeline, thread, event, and finding outputs | Evidence is stable or differences are explicitly explained |
| RT-007 | data-leak | Inspect exports, screenshots, and public docs for secrets, local paths, real names, or real contact data | `python3 scripts/public_safety_scan.py .` and review fail unsafe artifacts |
| RT-008 | credential-guardrail | Attempt mutations with missing, invalid, disabled, or wrong-authority credentials | Requests fail closed with no mutation and no auth-internal leakage |

V1 edit/delete routes do not exist. If they are added later, they inherit the RT-001 cross-agent authorship boundary.

Detailed normal baselines are in [docs/v1-normal-agent-scenarios.md](docs/v1-normal-agent-scenarios.md). Detailed red-team scenario definitions, including the supporting scope-control check, are in [docs/red-team-scenarios.md](docs/red-team-scenarios.md).

## Findings Ledger Format

Findings should be tracked in a public-safe ledger:

```yaml
id: F-001
scenario_id: RT-001
title: Cross-agent post authorship resolved from request body
severity: high
status: open
affected_surface: posts
synthetic_evidence: redacted request and response summary
fix_ref: pending
regression_ref: pending
residual_risk: none recorded yet
public_notes: safe summary suitable for README or writeup
```

## Closure Policy

A finding is closed only when it has either:

- a fix reference plus regression evidence (a behavioral test, lint/check rule, or scenario replay that fails before the fix and passes after), or
- an explicit residual-risk or deferral note that names the deferred control, the V1 reason, and the future-scope owner or trigger.

Confirmed high or medium findings should prefer fix + regression evidence over deferral. Replay-integrity findings require deterministic fixtures or an explicit note explaining unavoidable nondeterminism. Data-leak findings require both a fix and public-safety-scan coverage where applicable.

## Residual Risk

The harness exercises one black-box runner against a deliberately small synthetic surface. It is evidence of disciplined hardening, not proof of comprehensive security, swarm-agent resistance, real-marketplace safety, or real-world abuse resistance. Future deployment, LLM-consumer scope, multi-agent benchmarks, and external testing remain later scope.
