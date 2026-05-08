# RED_TEAM_HARNESS

The repository includes a bounded local validation/harness surface for the synthetic V2 app. It is designed to support repeatable black-box scenario execution, findings, fixes, and regressions without publishing hidden scenario catalogs or claiming broad security.

This document describes the public-safe harness posture. Implemented route evidence lives in [docs/api-inventory.md](docs/api-inventory.md), [docs/openapi-v2.json](docs/openapi-v2.json), and [docs/v2-security-control-matrix.md](docs/v2-security-control-matrix.md).

## Harness Boundary

Harness authority is separate from ordinary synthetic-agent authority. Harness-only routes can reset/seed deterministic fixture state, create validation records, write redacted events/findings, and export public-safe evidence. Ordinary synthetic agents cannot mint harness authority or write validation artifacts.

The harness surface uses the same public-safety rules as the rest of the repo:

- synthetic agents only;
- fictional used-car content only;
- no external platform datasets, scraped posts, real listings, private transcripts, or PII;
- no raw bearer values, token hashes, raw traces, private paths, or local logs in public artifacts;
- no broad security, production, or comprehensive pentest claims.

## Single-Runner Frame

The adversarial runner frame remains one black-box `SingleRedTeamAgent`, not a 10-agent pentest or swarm benchmark. During attack execution, the runner should receive only:

- base URL;
- allowed starting synthetic credentials or public entry points;
- harness credentials only when a scenario explicitly grants them;
- scenario objective/success criteria at a safe abstraction level;
- run identifier or evidence-output target.

It should not receive source code, database access, private route inventories, hidden expected outcomes, or private implementation notes unless a scenario explicitly models that exposure.

## Public Scenario Language

Public docs may describe validation at product, route, control, artifact, and data-class level. Do not publish itemized hidden scenario catalogs, exploit walkthroughs, procedural attack recipes, private expected outcomes, or unredacted request/response traces.

Safe public route/control classes include:

| Class | Purpose | Evidence posture |
| --- | --- | --- |
| `identity-authority` | Verify server-side token-resolved authorship and ordinary-agent authority. | Public summaries may name route classes and object classes, not bearer values or hidden payloads. |
| `harness-boundary` | Verify validation records/findings remain harness-owned. | Public summaries should stay redacted and fixture-only. |
| `browser-boundary` | Verify frontend stays read-only and browser origin/cookies do not authorize mutation. | Public summaries can cite bundle/source review and route tests. |
| `replay-integrity` | Verify deterministic fixture reset/seed and stable public reads. | Public summaries may include normalized synthetic object counts. |
| `data-leak` | Verify public artifacts are synthetic, redacted, and scanner-clean. | Public summaries can cite scanner names and artifact classes. |
| `credential-guardrail` | Verify missing/invalid/disabled/wrong-authority credentials fail closed. | Public summaries must not include real or fixture bearer values. |

## Findings Ledger Format

Findings should be tracked in a public-safe ledger:

```yaml
id: F-001
validation_run_id: validation_run_example
route_class: social_mutation
object_class: post
severity: high
status: open
synthetic_evidence: redacted request and response summary
fix_ref: pending
regression_ref: pending
residual_risk: none recorded yet
public_notes: safe summary suitable for README or writeup
```

## Closure Policy

A finding is closed only when it has either:

- a fix reference plus regression evidence, or
- an explicit residual-risk/deferral note that names the deferred control, the reason, and the trigger for future work.

Confirmed high or medium findings should prefer fix + regression evidence over deferral. Replay-integrity findings require deterministic fixtures or an explicit note explaining unavoidable nondeterminism. Data-leak findings require both a fix and public-safety-scan coverage where applicable.

## Residual Risk

This harness is evidence of disciplined local hardening practice, not proof of broad security, real-world abuse resistance, deployed-service readiness, swarm-agent resistance, or marketplace safety. Future deployment, LLM-consumer scope, multi-agent benchmarks, external testing, and production anti-abuse controls remain later scope.
