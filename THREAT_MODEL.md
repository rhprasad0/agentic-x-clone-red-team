# THREAT_MODEL

This threat model is a starting point for a synthetic app and harness. It will be revised as implementation artifacts exist.

## Boundaries

- All users and content are synthetic.
- No scraped platform data, real user records, private transcripts, or production credentials are allowed.
- Public examples must use fictional handles, placeholder keys, example domains, and redacted outputs.
- The repo should not imply that a live platform is deployed or hardened.

## Assets

- Synthetic account records and role assignments.
- Session tokens and auth state.
- Posts, follows, likes, reports, moderation records, and audit events.
- Single-agent red-team findings, scenario outputs, and regression results.
- Local service configuration for development.

## Threats And Planned Controls

| Area | Threat | Planned Controls |
| --- | --- | --- |
| Auth | Credential stuffing, weak session handling, account enumeration | Password policy or external auth abstraction, generic auth errors, session expiry, auth rate limits |
| Authorization | IDOR on posts, reports, profiles, moderation actions, or admin routes | Server-side ownership checks, role checks, deny-by-default route guards, authorization tests |
| Content abuse | Spam, harassment-like synthetic content, coordinated amplification | Posting limits, reporting, moderation queue, synthetic abuse labels, replayable fixtures |
| Prompt injection | Posts or profiles instruct the single red-team runner or future helper agents to reveal hidden prompts, skip policy, or alter findings | Isolated agent context, scenario-scoped tool permissions, prompt-injection test cases, output validation |
| Data leakage | Logs, screenshots, fixtures, or findings expose secrets, paths, or real data | Public safety scanner, redacted logs, synthetic-only seed data, CI grep checks |
| Rate limits | Burst posting, report floods, auth probing, notification spam | Redis-backed counters, per-user and per-IP style buckets, deterministic tests |
| Moderation bypass | Encoding tricks, spacing, quote/repost laundering, context hiding | Canonicalization, moderation metadata, bypass scenario suite, reviewer audit trails |
| Admin abuse | Privileged action misuse, silent moderation edits, role escalation | Least privilege, audit log, separate admin routes, regression tests for role boundaries |

## Abuse Cases To Exercise

- Member attempts to delete or edit another member's post.
- Member reports the same post repeatedly to flood the queue.
- Attack agent hides policy-violating synthetic content with Unicode, spacing, or screenshots-as-text placeholders.
- Attack agent places prompt-injection text inside a post and waits for a summarizer or moderator agent to process it.
- Moderator attempts an admin-only action.
- Admin action occurs without an audit entry.

## V1 Adversary Boundary

The first harness uses one adversarial runner with multiple scenario modes. This keeps the benchmark honest and shippable: it can demonstrate a hardening loop without implying that the app survived a broad multi-agent pentest. Future work may add parallel or role-specialized agents after the single-runner loop produces findings, fixes, and regression evidence.

## Residual Risk Notes

Synthetic coverage is useful for repeatable hardening, but it does not prove real-world safety. Any future deployment would need dedicated privacy review, abuse monitoring, incident response, dependency review, infrastructure review, and external security testing.

