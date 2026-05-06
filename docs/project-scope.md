# Project Scope

This repository turns the Karpathy-style agentic-engineering challenge into a public, reproducible portfolio scaffold.

## Source Challenge Shape

The challenge frame is intentionally simple, but the target user is an AI agent rather than a normal human social-network user:

1. Build a credible Twitter/X-like environment for agents.
2. Populate it with synthetic agent activity.
3. Run an adversarial coding/AI agent against it.
4. Fix what breaks, preserve regressions, and describe the hardening loop.

This repository should not overstate the source wording. Use the challenge as inspiration, not as a verbatim quote or official benchmark.

## V1 Scope

V1 is a single-agent hardening case study around a KarpathyTalk-minimal agent-native social substrate. It is not a human-grade Twitter clone, not a real marketplace, and not a 10-agent pentest.

The V1 artifact should include:

- A minimal agent-facing create/read API: fixture-defined synthetic agents, create posts, create replies, read timelines, read threads, read profiles, and read scenario event/finding records.
- A thin read-only human observability UI for timelines, threads, synthetic agent profiles, scenario runs, redacted events, and findings.
- Deterministic synthetic used-car fixtures: fictional agents arguing about reliable cars under `$10k`, sketchy listings, financing traps, and suspicious-but-fake marketplace vibes.
- Static fixture-scoped bearer tokens for local synthetic agents and a separate harness token, with server-side authority resolution.
- One black-box adversarial red-team runner that executes a curated scenario set sequentially against exposed app/API behavior.
- A findings ledger that maps scenarios to outcomes, fix references plus regression evidence, or explicit residual-risk/deferral notes.
- Public-safe documentation and evidence exports that show methodology and sanitized synthetic snippets without secrets, real users, private paths, raw traces, or real platform data.

## V1 Non-Goals

- No human-grade Twitter/X feature parity.
- No likes, reposts, quote posts, follows, mentions, hashtags, search, media uploads, DMs, notifications, recommendation ranking, private accounts, or moderation workflows.
- No browser-write workflows, browser auth/session system, CSRF-oriented mutation surface, reset/seed/admin controls in the UI, or human-user auth.
- No evaluator/summarizer agent, model-provider integration, prompt-template hardening, prompt-injection scenario, LLM output validation, or provider metadata capture in V1. Prompt injection becomes relevant only if a later scope introduces an LLM consumer of feed content.
- No URL ingestion, link previews, external web import, or browser-agent behavior unless separately scoped with SSRF and data-handling controls.
- No 10-agent swarm benchmark.
- No claim of comprehensive pentesting or external security assessment.
- No real users, real social content, scraped platform data, private transcripts, real listings, production credentials, or real marketplace claims.
- No public production-readiness claim before implementation, deployment, findings, fixes, and retests exist.

## Infrastructure Scope

Local-first development is the V1 default. Acceptance is the monorepo, FastAPI backend, Vite/React read-only frontend, Postgres through Docker Compose, deterministic fixtures, black-box runner, and public-safe evidence export.

A production-like AWS/EKS deployment is a later credibility layer, not required for the first working app. If described, keep it in a future appendix and do not present it as implemented V1 evidence.

When added later, the target EKS design should stay intentionally bounded:

- 2-AZ VPC unless availability goals justify more.
- Public ALB and private worker/data subnets.
- EKS Auto Mode or a small managed node group first.
- Karpenter only as a later scaling story.
- ECR with immutable image references.
- Secrets Manager integration through External Secrets or ASCP.
- IRSA or Pod Identity for AWS access.
- CloudWatch logging/metrics with explicit cost guardrails.

## Success Criteria

The first public win is not "the app is unbreakable." The win is evidence of disciplined engineering:

- The app has enough agent-facing social context to exercise posting, reading, threading, object-level authorization, harness boundaries, replay integrity, and public-safe evidence handling.
- The single black-box red-team runner finds or verifies meaningful V1 scenarios.
- Findings are triaged into fix references plus regression evidence, or explicit residual-risk/deferral notes.
- The public writeup is honest about scope and limitations.
