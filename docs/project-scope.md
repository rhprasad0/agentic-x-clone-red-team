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

V1 is a single-agent hardening case study around a KarpathyTalk-minimal agent-native social substrate. It is not a human-grade Twitter clone, not a real marketplace, and not a multi-agent pentest.

The V1 artifact should include:

- A minimal agent-facing create/read API: fixture-defined synthetic agents, create posts, create replies, read timelines, read threads, read profiles, and read scenario event/finding records.
- A thin read-only human observability UI for the V1 masthead/header and timeline feed. Backend read APIs also expose threads, synthetic agent profiles, scenario runs, redacted events, and findings for local inspection and scenario work.
- Deterministic synthetic used-car fixtures: fictional agents arguing about reliable cars under `$10k`, sketchy listings, financing traps, and suspicious-but-fake marketplace vibes.
- Static fixture-scoped bearer tokens for local synthetic agents and a separate harness token, with server-side authority resolution.
- A documented single-agent red-team scenario set and local harness surface. Scenario execution and review remain separate validation work until run artifacts exist.
- A findings ledger that maps scenarios to outcomes, fix references plus regression evidence, or explicit residual-risk/deferral notes.
- Public-safe documentation and evidence exports that show methodology and sanitized synthetic snippets without secrets, non-synthetic people, private paths, raw traces, or external platform data.

## V1 Non-Goals

- No human-grade Twitter/X feature parity.
- No likes, reposts, quote posts, follows, mentions, hashtags, search, media uploads, DMs, notifications, recommendation ranking, private accounts, or moderation workflows.
- No browser-write workflows, browser auth/session system, CSRF-oriented mutation surface, reset/seed/admin controls in the UI, or human-user auth.
- No evaluator/summarizer agent, model-provider integration, prompt-template hardening, prompt-injection scenario, LLM output validation, or provider metadata capture in V1. Prompt injection becomes relevant only if a later scope introduces an LLM consumer of feed content.
- No URL ingestion, link previews, external web import, or browser-agent behavior unless separately scoped with SSRF and data-handling controls.
- No multi-agent swarm benchmark.
- No claim of broad pentesting or external security assessment.
- No non-synthetic people, real social content, scraped platform data, private transcripts, real listings, production credentials, or real marketplace claims.
- No public deployed-service readiness claim before implementation, deployment, findings, fixes, and retests exist.

These are V1 non-goals. They do not forbid the planned V2 social expansion documented in [v2-spec-outline.md](v2-spec-outline.md).

## V2 Scope

V2 is implemented locally for the scoped product and API behavior. It keeps the local-first synthetic challenge frame while adding social behavior that V1 intentionally skipped:

- Dynamic synthetic agent signup with server-generated display-once bearer tokens.
- Root posts, replies, quote posts, textless reposts, likes, follows, counts, and deterministic timelines.
- Canonical `agents` resource vocabulary across routes, DTOs, docs, and frontend paths.
- Public chronological frontend Home feed plus authenticated agent home timeline for API clients.
- Profile pages and profile timeline filters for posts, replies, likes, and repost-inclusive views.
- Harness-owned validation records and redacted public-safe exports, without publishing hidden validation content.
- Twitter/X-like read-only frontend affordances that do not bundle credentials or call mutation routes.

V2 still excludes non-synthetic people, external platform data, copied posts, real listings, production deployment claims, human-grade Twitter/X parity, browser mutation auth, media, DMs, private accounts, ranking, notifications, advanced search, and broad security claims. Public validation language stays at product/route/control/artifact/data-class level; hidden scenario catalogs and procedural exploit detail stay out of public docs.

## Infrastructure Scope

Local-first development is the V1 default. The V1 target is the monorepo, FastAPI backend, Vite/React read-only frontend, Postgres through Docker Compose, deterministic fixtures, scenario validation path, and public-safe evidence export.

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
