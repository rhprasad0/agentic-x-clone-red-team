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

V1 is a single-agent hardening case study around a minimal agent-native social substrate. It is not a human-grade Twitter clone and not a 10-agent pentest.

The V1 artifact should include:

- A minimal agent-facing create/read API: create synthetic agents, create posts, create replies, read timelines, read threads, read profiles, and read scenario event logs.
- A thin human observability UI for timelines, threads, synthetic agent profiles, scenario runs, and findings.
- Deterministic synthetic agents, posts, replies, personas, and prompt-injection fixtures.
- One adversarial red-team agent runner that executes a curated scenario set sequentially.
- A findings ledger that maps scenarios to outcomes, fixes, regression tests, and residual risk.
- Public-safe documentation that shows methodology and evidence without secrets, real users, private paths, or real platform data.

## V1 Non-Goals

- No human-grade Twitter/X feature parity.
- No complex auth, DMs, notifications, payments, ads, or contact import.
- No recommendation system beyond deterministic timeline ordering.
- No rich moderation product surface unless a scenario explicitly needs it.
- No 10-agent swarm benchmark.
- No claim of comprehensive pentesting.
- No real users, real social content, scraped platform data, private transcripts, or production credentials.
- No public production-readiness claim before implementation, deployment, findings, fixes, and retests exist.

## Infrastructure Scope

Local-first development is the default. A production-like AWS/EKS deployment is a later credibility layer, not required for the first working app.

The target EKS design, when added, should stay intentionally bounded:

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

- The app has enough agent-facing social context to exercise posting, reading, threading, prompt-injection, object-level authorization, and public-safe logging risks.
- The single red-team agent finds or verifies meaningful scenarios.
- Findings are triaged into fixes, regression tests, or explicit residual-risk notes.
- The public writeup is honest about scope and limitations.
