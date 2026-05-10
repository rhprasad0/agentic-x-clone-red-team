# Strix observability runbook

This runbook captures the public-safe Strix configuration and prompting pattern for the x-clone / CARBOTS controlled-destructive app-state assessment.

Sources checked:

- Strix CLI reference: `https://docs.strix.ai/usage/cli`
- Strix configuration reference: `https://docs.strix.ai/advanced/configuration`
- Strix custom instructions: `https://docs.strix.ai/usage/instructions.md`
- Strix scan modes: `https://docs.strix.ai/usage/scan-modes.md`
- Strix HTTP proxy docs: `https://docs.strix.ai/tools/proxy`
- Strix browser docs: `https://docs.strix.ai/tools/browser`

## Observability goal

For this project, "full observability" means we can reconstruct what Strix did without publishing unsafe raw traces:

1. **Run metadata** — Strix version, scan mode, model class, target classes, repo commit, image tags, time window, and operator.
2. **Agent reasoning/events** — local Strix telemetry in `strix_runs/<run_name>/events.jsonl`.
3. **HTTP traffic** — Caido proxy request/response capture and sitemap, kept private/ignored.
4. **Browser evidence** — screenshots and browser-driven flow notes when relevant.
5. **Command evidence** — terminal/security-tool commands Strix ran inside the sandbox, summarized publicly and retained privately.
6. **Findings** — final Strix report plus manual verification notes, promoted to `pentest-findings-ledger.md` only after verification.
7. **Reset/retest receipts** — app-state reset/reseed and retest status after destructive synthetic-data runs.

Public docs should contain sanitized summaries. Raw Strix workspaces, proxy traces, request bodies, bearer material, private hostnames, and exploit payload details stay private.

## Local configuration

Use an ignored local env file such as `.env.strix.local`; do not commit it.

Expected public-safe shape:

```bash
export STRIX_LLM="openai/gpt-5.5"
export LLM_API_BASE="http://127.0.0.1:4000/v1"
export LLM_API_KEY="<local bridge bearer; never commit or print>"
export STRIX_REASONING_EFFORT="xhigh"
export LLM_TIMEOUT="600"
export STRIX_SANDBOX_EXECUTION_TIMEOUT="600"
```

Optional observability controls:

```bash
export STRIX_TELEMETRY="1"
export STRIX_OTEL_TELEMETRY="1"
export STRIX_POSTHOG_TELEMETRY="0"
# Leave TRACELOOP_* unset unless a private OTEL collector is intentionally configured.
```

Important behavior from the Strix docs:

- If remote OTEL variables are unset, Strix still writes complete local run telemetry to `strix_runs/<run_name>/events.jsonl`.
- If `TRACELOOP_BASE_URL` and `TRACELOOP_API_KEY` are set, Strix dual-writes telemetry locally and remotely.
- Browser traffic is automatically routed through the Caido proxy, giving request/response visibility.
- In interactive mode, Strix displays the Caido URL in the TUI sidebar; open it with Caido Desktop and continue as guest to inspect traffic in real time.
- In headless mode (`-n`), Strix prints findings and a final report, and exits `2` when vulnerabilities are found.

## Recommended run modes

Use two passes rather than one mega-goblin blob:

### Pass A — interactive observability pass

Purpose: watch Strix work, capture Caido/sitemap/browser evidence, and learn how it attacks the app.

Use interactive TUI mode, not `-n`, so the Caido URL is visible and the run can be observed live.

```bash
set -a
source .env.strix.local
set +a
PATH="$HOME/.strix/bin:$PATH" \
  strix \
  --target . \
  --target https://xclone.ryans-lab.click \
  --target https://api.xclone.ryans-lab.click \
  --scan-mode standard \
  --instruction-file docs/security/strix-xclone-instructions.md
```

Operator checklist during Pass A:

- Record start/end time and Strix version.
- Copy the Caido URL from the TUI sidebar into private notes only.
- Open Caido Desktop and inspect sitemap/request classes in real time.
- Note which endpoints Strix reaches by class, not raw private target names.
- If Strix begins DoS-like, broad fuzzing, credential-exfiltration, or cloud-infra mutation behavior, stop or narrow the run.

### Pass B — reproducible headless evidence pass

Purpose: produce repeatable logs and final report output after the interactive pass has shaped the scope.

```bash
set -a
source .env.strix.local
set +a
mkdir -p .hermes/tmp/strix
PATH="$HOME/.strix/bin:$PATH" \
  strix -n \
  --target . \
  --target https://xclone.ryans-lab.click \
  --target https://api.xclone.ryans-lab.click \
  --scan-mode deep \
  --instruction-file docs/security/strix-xclone-instructions.md \
  2>&1 | tee .hermes/tmp/strix/strix-headless-$(date -u +%Y%m%dT%H%M%SZ).log
```

Do not treat exit code `2` as a shell failure; in Strix headless mode it means vulnerabilities were found. Triage and manually verify before ledgering.

## Instruction file template

Create the instruction file as a public-safe document when it contains no secrets. Put live private target details and credentials in `.env.strix.local` or private notes, not here.

```markdown
# x-clone / CARBOTS Strix instructions

## Authorization and safety

You are authorized to test only the x-clone / CARBOTS synthetic social app targets supplied by the CLI. This is a scoped AI-assisted web/API security assessment with controlled destructive app-state testing.

Allowed destructive behavior is limited to resettable synthetic app state: synthetic agents, posts, replies, quote posts, likes, reposts, follows, counters, feeds, and app consistency. Do not perform denial-of-service, stress testing, volumetric fuzzing, cost-spike behavior, cloud infrastructure mutation, credential exfiltration, third-party attacks, or destructive AWS/Kubernetes actions.

If a test starts behaving like DoS, broad fuzzing, cloud-chaos, secret exfiltration, or cost amplification, stop that path and document why it was skipped.

## Target model

- FastAPI backend and React/Vite frontend.
- Public frontend is intended to be read-only.
- Public API is intended for read routes and public mutation denial.
- Private/operator mutation path is authorized only when supplied as an explicit target or credential context.
- Data is fictional synthetic social activity only.
- Synthetic agent identity should be resolved server-side from bearer credentials, not trusted from request bodies.

## Required observability behavior

During the scan, maintain notes sufficient to reconstruct:

1. route classes discovered;
2. browser flows attempted;
3. Caido/proxy request classes used for replay;
4. payload categories, without exposing secrets;
5. actor class used: anonymous, synthetic agent, wrong synthetic agent, harness/operator;
6. expected vs observed status class;
7. whether app state was changed;
8. whether reset/reseed or retest is required.

For every potential finding, include:

- finding title;
- affected route or component class;
- vulnerability class;
- attacker persona;
- preconditions;
- concise reproduction steps;
- observed impact;
- evidence summary;
- false-positive checks performed;
- remediation idea;
- retest steps.

## Priority attack paths

1. Public read-only boundary bypass: anonymous public mutation attempts against posts, replies, quotes, likes, reposts, follows, signup, and validation/export routes.
2. Cross-agent authorization / IDOR: one synthetic agent attempting to modify, delete, like, repost, follow, or otherwise act as another.
3. Function-level authorization: ordinary synthetic agent attempting harness/operator-only routes.
4. Mass assignment: protected fields in signup and mutation payloads.
5. Token handling: bearer/token leakage in responses, logs, frontend bundles, exports, errors, or redirects.
6. XSS and unsafe rendering: harmless HTML/script/URL/control-character probes in synthetic post/profile text.
7. Business logic: duplicate likes/reposts/follows, delete-only-caller behavior, quote/reply edge cases, stale tokens, replayed request IDs, idempotency-key reuse across actors/routes/targets/bodies.
8. Race/consistency: bounded concurrency only; check counters, timelines, profiles, and thread consistency without load testing.
9. Query/resource bounds: cursor tampering, malformed cursors, excessive limits, filter/sort abuse, and error disclosure.
10. Deployment exposure: public docs/debug/CORS posture and accidental mutation path exposure, without cloud-infra mutation.

## Evidence boundaries

Keep raw request/response bodies, tokens, cookies, private hostnames, exploit payload details, and tool workspaces private. Public outputs should use route classes, status classes, synthetic object IDs only when safe, and sanitized summaries.

Do not claim a finding is confirmed unless you validated it with a working proof or a clear manual reproduction. Mark uncertain items as hypotheses.
```

## Post-run evidence promotion

After each Strix run:

1. Copy or move raw Strix artifacts under an ignored private workspace such as `.hermes/tmp/strix/`.
2. Record the run in `docs/security/pentest-methodology.md` or the retest log with only public-safe metadata.
3. Review `strix_runs/<run_name>/events.jsonl` privately for coverage gaps and notable agent decisions.
4. Review Caido sitemap/request classes privately; summarize route classes publicly.
5. Verify every material finding manually before adding it to `docs/security/pentest-findings-ledger.md`.
6. For destructive app-state findings, reset/reseed and record the reset receipt before retest.
7. Run `python3 scripts/public_safety_scan.py README.md docs/security docs/pre-pentest-receipts.md` before committing public docs.

## Open question

Strix docs say local telemetry goes to `strix_runs/<run_name>/events.jsonl`, but the exact run-name convention is tool-generated. After the first pass, inspect the created `strix_runs/` directory privately and update this runbook if Ryan wants a stricter artifact naming convention.
