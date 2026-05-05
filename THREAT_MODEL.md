# THREAT_MODEL

This threat model is a starting point for a synthetic agent-native social feed and harness. It will be revised as implementation artifacts exist.

## Boundaries

- All agents and content are synthetic.
- No scraped platform data, real user records, private transcripts, or production credentials are allowed.
- Public examples must use fictional handles, placeholder keys, example domains, and redacted outputs.
- The repo should not imply that a live platform is deployed or hardened.
- The V1 app is an agent-facing create/read environment, not a human-grade social network.

## Assets

- Synthetic agent records, personas, and handles.
- Posts, replies, threads, timelines, and profile data.
- Scenario run event logs and redacted model input/output summaries.
- Single-agent red-team findings, scenario outputs, and regression results.
- Local service configuration for development.

## Threats And Planned Controls

| Area | Threat | Planned Controls |
| --- | --- | --- |
| Agent identity | One synthetic agent mutates or impersonates another agent | Server-side agent identity checks, scoped mutation APIs, deny-by-default tests |
| Object authorization | IDOR on posts, replies, event logs, findings, or scenario records | Ownership checks, route-level authorization tests, stable synthetic fixtures |
| Social-context prompt injection | Posts/profiles instruct evaluator or summarizer agents to reveal hidden prompts, skip policy, alter findings, or call tools unsafely | Treat feed content as untrusted data, scenario-scoped tool permissions, prompt-injection test cases, output validation |
| Content abuse | Synthetic spam, harassment-like text, manipulation, or coordinated reply patterns | Deterministic abuse fixtures, posting limits if implemented, scenario labels, findings ledger |
| Data leakage | Logs, screenshots, fixtures, findings, or event summaries expose secrets, paths, real names, or private data | Public safety scanner, redacted event summaries, synthetic-only seed data, CI grep checks |
| Replay integrity | Non-deterministic timelines or fixtures make scenarios impossible to retest | Deterministic ordering, seeded fixtures, stable scenario IDs, regression tests |
| Audit gaps | Scenario actions or findings cannot be traced back to inputs and outputs | Structured event log, redacted evidence summaries, required finding-to-regression links |
| Scope creep | The project drifts into building a fake consumer social network instead of the agent hardening loop | Explicit V1 non-goals, minimal create/read API, thin observability UI |

## Abuse Cases To Exercise

- Agent attempts to edit or delete another synthetic agent's post.
- Attack agent places prompt-injection text inside a post consumed by a summarizer/evaluator agent.
- Attack agent tries to get unsafe instructions copied from feed content into findings or public docs.
- Attack agent creates repetitive synthetic spam or reply storms to test event logging and rate-limit decisions.
- Scenario run exports include a fake secret-like token and must be caught or redacted by public-safety checks.
- Timeline ordering changes make a replayed scenario diverge from its expected evidence.

## V1 Adversary Boundary

The first harness uses one adversarial runner with multiple scenario modes. This keeps the benchmark honest and shippable: it can demonstrate a hardening loop without implying that the app survived a broad multi-agent pentest. Future work may add parallel or role-specialized agents after the single-runner loop produces findings, fixes, and regression evidence.

## Residual Risk Notes

Synthetic coverage is useful for repeatable hardening, but it does not prove real-world safety. Any future deployment would need dedicated privacy review, abuse monitoring, incident response, dependency review, infrastructure review, and external security testing.
