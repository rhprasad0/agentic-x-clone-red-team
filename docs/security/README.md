# Security assessment packet

Public-safe documentation for the x-clone / CARBOTS scoped AI-assisted pentest-style assessment.

Read in this order:

1. [Pentest scope](pentest-scope.md) — authorized target, rules of engagement, in-scope and out-of-scope surfaces.
2. [Pentest methodology](pentest-methodology.md) — run phases, tool usage, evidence handling, triage, remediation, and retest workflow.
3. [Strix observability runbook](strix-observability.md) — configuration, run modes, telemetry/proxy expectations, and evidence-promotion workflow.
4. [Strix instruction file](strix-xclone-instructions.md) — public-safe prompt used to steer Strix toward scoped x-clone attack paths and observability.
5. [Strix results receipt](strix-pentest-results-2026-05-10.md) — earlier operational harness receipt and same-day smoke follow-up; not a completed pentest claim.
6. [Strix live Sonnet results](strix-live-sonnet-results-2026-05-10.md) — follow-up Sonnet-backed live tool-calling verification and bounded public-read-only standard pass with candidate findings.
7. [Controlled destructive app-state results](destructive-app-state-results-2026-05-10.md) — bounded synthetic-state probes for public/private boundary, replay, cross-agent behavior, and inert text handling.
8. [Pentest findings ledger](pentest-findings-ledger.md) — current findings, status values, severity model, and detailed finding template.
9. [Pentest retest log](pentest-retest-log.md) — retest status, retest entry template, and closure quality bar.

The pre-pentest live baseline receipt is tracked separately at [`../pre-pentest-receipts.md`](../pre-pentest-receipts.md).

## Claim boundary

This packet supports a scoped, authorized, AI-assisted web/API security assessment of a synthetic social app. It does not claim formal third-party certification, production-grade security, real-user testing, or comprehensive cloud/account coverage.

Use public wording like:

> scoped AI-assisted pentest-style hardening pass

or:

> scoped AI-assisted web/API security assessment

Avoid blanket claims such as "unhackable," "certified secure," or "survived a pentest" unless stronger third-party/human-reviewed evidence exists.
