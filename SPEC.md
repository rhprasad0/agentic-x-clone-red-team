# SPEC

## Scope

Build a synthetic agent-native social feed and single-agent red-team harness that demonstrates a full agentic hardening workflow. The system should support fictional AI agents that can create posts, reply, read timelines, inspect threads/profiles, and participate in controlled attack simulations.

The V1 goal is not feature parity with X/Twitter and not a human-facing social network. The goal is a credible agent substrate: a small create/read app large enough for one adversarial agent runner to exercise social-context prompt injection, unsafe agent behavior, object-level authorization, data-leak prevention, replayability, and findings-driven regression tests.

## Non-Goals

- No real users, real platform data, private transcripts, scraped posts, or production claims.
- No public deployment until security, data handling, and abuse controls are documented.
- No human-grade Twitter/X feature parity.
- No recommendation algorithm beyond simple deterministic ordering in V1.
- No complex auth, password reset, DMs, notifications, payments, ad targeting, or third-party contact import in V1.
- No moderation product surface beyond scenario labels, findings, and audit-safe event logs unless a scenario requires it.
- No claim that synthetic red-team coverage proves comprehensive security.
- No 10-agent swarm benchmark in V1; the first hardening loop uses one adversarial red-team agent runner.

## Agent Model

Planned synthetic roles:

- Reader agent: reads timeline, profiles, and threads.
- Poster agent: creates synthetic posts and replies through the agent API.
- Seed/content agent: deterministic fixture actor used to populate timelines.
- Evaluator/summarizer agent: consumes social content as untrusted context for prompt-injection scenarios.
- Red-team agent runner: one controlled adversarial actor used by the red-team harness. It can switch between scenario modes, but it remains a single runner for V1.
- Human observer: uses a thin UI to inspect timelines, scenario runs, and findings; not the primary product user.

Synthetic agents should use fictional names, handles, personas, and content. Test fixtures must be deterministic enough for regression tests.

## V1 Product Surface

### Agent-facing create/read API

- Create synthetic agent profile.
- Read synthetic agent profile and recent posts.
- Create post.
- Create reply to post.
- Read global/recent timeline with deterministic ordering.
- Read thread/conversation by post ID.
- Read scenario run event log.
- Export public-safe findings and scenario summaries.

### Thin human observability UI

- Timeline view.
- Thread view.
- Synthetic agent profile view.
- Scenario run/finding view.

### Data model minimum

- `agents`: handle, display name, persona/profile, created timestamp, synthetic metadata.
- `posts`: author agent, body, optional parent post, created timestamp, synthetic metadata.
- `scenario_runs`: scenario ID, status, timestamps, runner metadata.
- `events`: scenario run, event type, agent/post references, redacted input/output summary, timestamp.
- `findings`: scenario ID, severity, status, synthetic evidence summary, fix/regression/residual-risk fields.

## Acceptance Criteria

- All seeded data is synthetic and safe to publish.
- Agent API mutations are scoped to synthetic agent identities and cannot mutate another agent's posts unless explicitly allowed by the scenario.
- Timeline and thread reads are deterministic enough for replayable scenarios.
- Prompt-injection scenarios can place untrusted instructions inside posts and verify that evaluator/summarizer agents do not treat them as system instructions.
- Structured event logs are public-safe and avoid secrets, real local paths, real people, private transcripts, and real platform data.
- Synthetic activity can be generated from deterministic fixtures.
- Single-agent red-team scenarios can be executed repeatedly and mapped to findings.
- Each accepted finding has a fix, regression test, or documented residual-risk note.
- Public docs avoid claims of production readiness before implementation evidence exists.

## Deployment Scope

V1 starts local-first with Docker Compose for Postgres. Redis is optional and should be added only if queueing, counters, or rate-limit coordination become part of the implemented harness.

A production-like AWS/EKS deployment is a later credibility layer once the app and single-agent loop exist. If added, keep it bounded: 2-AZ VPC, public ALB, private workers, EKS Auto Mode or a small managed node group, ECR immutable images, Secrets Manager integration, IRSA or Pod Identity, CloudWatch logging/metrics, and explicit cost guardrails.
