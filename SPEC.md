# SPEC

## Scope

Build a synthetic X/Twitter-style application and single-agent red-team harness that demonstrates a full agentic hardening workflow. The system should support fictional users, posts, social interactions, moderation workflows, and controlled attack simulations.

The V1 goal is not feature parity with X/Twitter and not a 10-agent pentest. The goal is a credible product surface large enough for one adversarial agent runner to exercise authentication, authorization, content moderation, rate limits, prompt-injection defenses, and admin controls.

## Non-Goals

- No real users, real platform data, private transcripts, scraped posts, or production claims.
- No public deployment until security, data handling, and abuse controls are documented.
- No recommendation algorithm beyond simple deterministic ranking in V1.
- No payment flows, private messaging, ad targeting, or third-party contact import in V1.
- No claim that synthetic red-team coverage proves comprehensive security.
- No 10-agent swarm benchmark in V1; the first hardening loop uses one adversarial red-team agent runner.

## User Model

Planned synthetic roles:

- Visitor: unauthenticated reader of public synthetic content.
- Member: authenticated synthetic account that can post, follow, like, repost, and report.
- Moderator: synthetic reviewer that can inspect reports and apply moderation actions.
- Admin: privileged operator role for configuration and audit review.
- Activity generator: controlled synthetic fixture runner used to generate traffic and test behaviors.
- Red-team agent runner: one controlled adversarial actor used by the red-team harness. It can switch between scenario modes, but it remains a single runner for V1.

Synthetic users should use fictional names, handles, avatars, and content. Test fixtures must be deterministic enough for regression tests.

## V1 Product Surface

- Sign up, sign in, sign out, and session handling for synthetic accounts.
- Home feed with posts from followed synthetic accounts and seed accounts.
- Create, delete, like, repost, and report posts.
- Basic profile page with follow and unfollow.
- Notifications for likes, reposts, follows, and moderation outcomes.
- Moderation queue for reported content.
- Admin audit log for privileged actions.
- Rate limits for auth, posting, reports, and moderation actions.
- Structured event logs safe for public synthetic examples.

## Acceptance Criteria

- All seeded data is synthetic and safe to publish.
- Authenticated actions require a valid session.
- Users cannot mutate posts, profiles, reports, or moderation records they do not own unless authorized by role.
- Rate limits are applied to high-risk routes.
- Moderation actions are auditable.
- Synthetic activity can be generated from deterministic fixtures.
- Single-agent red-team scenarios can be executed repeatedly and mapped to findings.
- Each accepted finding has a fix, regression test, or documented residual-risk note.
- Public docs avoid claims of production readiness before implementation evidence exists.

## Deployment Scope

V1 starts local-first with Docker Compose for Postgres and Redis. A production-like AWS/EKS deployment is a later credibility layer once the app and single-agent loop exist.

The future EKS baseline should be bounded: 2-AZ VPC, public ALB, private workers, EKS Auto Mode or a small managed node group, ECR immutable images, Secrets Manager integration, IRSA or Pod Identity, CloudWatch logging/metrics, and explicit cost guardrails.

