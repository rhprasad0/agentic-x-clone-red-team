# Strix Live Sonnet Results — 2026-05-10

This public-safe receipt documents the follow-up Strix run after the earlier LLM/tool-calling failure mode. Raw logs and event traces remain ignored locally; this file contains only sanitized summaries.

## Executive summary

The Sonnet-backed Strix configuration successfully crossed the previous failure boundary. A quick tool-calling gate completed real Strix tool executions against the live public targets, and a follow-up standard public-read-only assessment completed with Strix-reported candidate findings.

Important claim boundary: this is evidence that the Strix harness/tool-calling path worked and that Strix produced candidate findings. It is **not** a broad security attestation and does **not** prove the app is globally clean or hardened.

## Scope

Targets supplied to Strix:

- Public frontend: `https://xclone.ryans-lab.click`
- Public API: `https://api.xclone.ryans-lab.click`

Boundaries for these runs:

- Live deployed public surfaces only.
- No localhost, local repository, LAN/private network, cloud control plane, or third-party target testing.
- No authentication attempts, fuzzing, DoS, brute force, credential attacks, or destructive testing.
- The standard run used public read-only assessment instructions; no private/operator mutation lane was included.

## Run 1 — quick tool-calling verification

| Field | Value |
| --- | --- |
| Mode | `quick` |
| Model | `anthropic/claude-sonnet-4-6` |
| Strix exit | `0` |
| Strix trace status | `run.completed` |
| Duration | About 56.6 seconds |
| Event count | 27 |
| Vulnerability count | `0` |

Completed tools observed beyond startup:

- `think`
- `send_request`
- `create_note`
- `finish_scan`

Live public read actions observed:

- GET public frontend: HTTP `200`
- GET public API root: HTTP `404`
- GET public API health endpoint: HTTP `200`

Interpretation: this quick gate was healthy. It showed real tool execution beyond `scan_start_info`, including public HTTP reads against the supplied live targets.

## Run 2 — standard public-read-only assessment

| Field | Value |
| --- | --- |
| Mode | `standard` |
| Model | `anthropic/claude-sonnet-4-6` |
| Strix exit | `2` findings-found class |
| Strix trace status | `run.completed` |
| Duration | About 18.2 minutes |
| Event count | 220 |
| Agents observed | 4 |
| Vulnerability count | `3` |

Completed tool families included:

- `scan_start_info`
- `scope_rules`
- `think`
- `browser_action`
- `python_action`
- `terminal_execute`
- `list_requests`
- `create_agent`
- `create_note`
- `create_vulnerability_report`
- `finish_scan`

The Strix terminal status also showed non-zero model/tool activity: four agents, dozens of tools, millions of input/cache tokens, tens of thousands of output tokens, and non-zero cost. That is materially different from the earlier broken run where the status panel showed no meaningful model/tool activity.

## Strix-reported candidate findings

Strix reported three medium-severity candidate findings:

1. Missing HTTP security headers on the frontend and API.
2. Server technology/version disclosure through HTTP response headers and error pages.
3. Hardcoded development URL exposed in a production JavaScript bundle.

These should be treated as **candidate findings pending manual validation**. They are useful triage leads, not yet confirmed exploit narratives.

## Tooling notes

The standard run recorded a couple of early tool-schema errors while Strix attempted to create vulnerability reports without a required `impact` field. Strix recovered, completed the run, and emitted reviewed candidate findings. This is a Strix/tooling observation, not an app vulnerability.

## Comparison to the earlier failure mode

Earlier result:

- Strix initialized and configured targets.
- Only startup/info activity was observed.
- The run did not show meaningful model-driven tool use.
- The result was correctly classified as a harness receipt, not a completed assessment.

Sonnet follow-up result:

- Quick gate completed real target reads using Strix tools.
- Standard run completed with multiple agents and tool families.
- Strix produced candidate findings and a `run.completed` event.

Safe public phrasing:

> After switching to the Anthropic Sonnet-backed Strix configuration, Strix completed both a live tool-calling verification run and a bounded public-read-only standard pass against the deployed synthetic app. The standard pass produced three candidate findings that still require manual validation.

Avoid saying:

- The app passed a pentest.
- Strix proved the app is secure.
- The candidate findings are confirmed vulnerabilities before retest.
- The run covered private/operator mutation paths; it did not.

## Follow-up

Recommended next steps:

1. Manually validate the three candidate findings with public-safe commands/evidence.
2. Add confirmed items, if any, to the findings ledger and retest log.
3. Patch true positives, then rerun focused Strix/manual retests.
4. Keep raw Strix logs and event traces ignored/private.
