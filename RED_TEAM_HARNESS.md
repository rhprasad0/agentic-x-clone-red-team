# RED_TEAM_HARNESS

The red-team harness is planned, not implemented. Its purpose is to run repeatable synthetic scenarios against the app, produce findings, drive fixes, and preserve regressions.

## Planned Attack Agents

- AuthProbeAgent: exercises sign-in, sign-up, enumeration, session, and rate-limit behavior.
- AccessControlAgent: attempts IDOR and role-boundary violations.
- ContentAbuseAgent: creates synthetic spam, harassment-like, and manipulation patterns.
- PromptInjectionAgent: embeds instructions in posts, bios, reports, and moderation notes.
- ModerationBypassAgent: mutates content with encoding, spacing, quote, and repost tactics.
- AdminAbuseAgent: attempts privileged mutations and audit-log gaps.
- DataLeakAgent: inspects logs, exports, findings, and screenshots for unsafe data.

## Scenario Schema

```yaml
id: RT-001
title: Short scenario name
agent: AccessControlAgent
surface: posts
risk: high
preconditions:
  - synthetic users and posts exist
steps:
  - action: attempt forbidden mutation
expected_result: request is denied and audited when applicable
evidence:
  - route response
  - relevant audit event
regression:
  required: true
  test_name: access_control_denies_cross_user_delete
status: planned
```

## Initial Scenario Set

| ID | Agent | Scenario | Expected Result |
| --- | --- | --- | --- |
| RT-001 | AuthProbeAgent | Repeated failed sign-in attempts against a synthetic account | Generic errors and rate limit trigger |
| RT-002 | AuthProbeAgent | Sign-up enumeration using existing and missing synthetic handles | Responses do not reveal account existence beyond intended UX |
| RT-003 | AccessControlAgent | Delete another synthetic user's post by changing an ID | Server denies the request |
| RT-004 | AccessControlAgent | View another user's private moderation report payload | Server denies the request |
| RT-005 | ContentAbuseAgent | Burst-post repetitive synthetic spam | Posting limits and moderation signals trigger |
| RT-006 | ContentAbuseAgent | Coordinate synthetic likes and reposts from many agents | Abuse signals are recorded and limits apply |
| RT-007 | PromptInjectionAgent | Place hidden instructions in a post consumed by a summary agent | Agent ignores untrusted content instructions |
| RT-008 | DataLeakAgent | Inspect exported findings for secrets, local paths, or real contact data | Scanner and review fail unsafe output |
| RT-009 | ModerationBypassAgent | Use spacing, casing, and Unicode variants to bypass moderation checks | Canonicalization catches or flags variants |
| RT-010 | AdminAbuseAgent | Moderator attempts an admin-only role change | Request is denied and audit trail records attempt |

Detailed scenario drafts are in [docs/red-team-scenarios.md](docs/red-team-scenarios.md).

## Findings Ledger Format

Findings should be tracked in a public-safe ledger:

```yaml
id: F-001
scenario_id: RT-003
title: Cross-user post deletion accepted
severity: high
status: open
affected_surface: posts
synthetic_evidence: redacted request and response summary
fix_pr: pending
regression_test: pending
residual_risk: none recorded yet
public_notes: safe summary suitable for README or writeup
```

## Regression Policy

- Every confirmed high or medium finding needs a regression test before closure.
- Low findings need either a test, a lint/check rule, or a documented reason for deferral.
- Prompt-injection and data-leak findings require both behavioral tests and public-safety scan coverage when applicable.
- A finding is not closed until the scenario can be replayed and the expected result is observed.

## Residual Risk

The harness will exercise known synthetic scenarios. It should be presented as evidence of disciplined hardening, not proof of comprehensive security or real-world abuse resistance.

