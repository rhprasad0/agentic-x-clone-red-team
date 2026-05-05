# Project Scope

This repository turns the Karpathy-style agentic-engineering challenge into a public, reproducible portfolio scaffold.

## Source Challenge Shape

The challenge frame is intentionally simple:

1. Build a credible Twitter/X-like application.
2. Make it good and secure enough to deploy.
3. Populate it with synthetic activity.
4. Run an adversarial coding/AI agent against it.
5. Fix what breaks, preserve regressions, and describe the hardening loop.

This repository should not overstate the source wording. Use the challenge as inspiration, not as a verbatim quote or official benchmark.

## V1 Scope

V1 is a single-agent hardening case study, not a 10-agent pentest.

The V1 artifact should include:

- A minimal X/Twitter-style app surface: public reading, authenticated posting, profiles, follows, likes/reposts, reports, moderation queue, and audit logs.
- Deterministic synthetic users, posts, follows, reports, and abuse fixtures.
- One adversarial red-team agent runner that executes a curated scenario set sequentially.
- A findings ledger that maps scenarios to outcomes, fixes, regression tests, and residual risk.
- Public-safe documentation that shows methodology and evidence without secrets, real users, private paths, or real platform data.

## V1 Non-Goals

- No 10-agent swarm benchmark.
- No claim of comprehensive pentesting.
- No real users, real social content, scraped platform data, private transcripts, or production credentials.
- No public production-readiness claim before implementation, deployment, findings, fixes, and retests exist.
- No complex recommendation system, DMs, payments, ads, or contact import.

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

- The app has realistic enough surface area to exercise auth, authz, content, abuse, and moderation risks.
- The single red-team agent finds or verifies meaningful scenarios.
- Findings are triaged into fixes, regression tests, or explicit residual-risk notes.
- The public writeup is honest about scope and limitations.
