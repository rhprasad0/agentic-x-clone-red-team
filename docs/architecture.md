# Architecture

This is the local-first architecture note for the current V1 scaffold and planned V2 delta. V1 remains the implemented baseline; [v2-spec-outline.md](v2-spec-outline.md) is the canonical planned V2 product spec.

```mermaid
flowchart LR
  AgentClients[Agent Clients / Harness Tools] --> API[FastAPI Backend]
  Observer[Read-Only Vite/React UI] --> API
  API --> Postgres[(Postgres)]

  Fixtures[Deterministic Used-Car Fixtures] --> API
  RedTeam[Black-Box Single Red-Team Runner] --> API
  RedTeam --> Findings[Findings Ledger]
  API --> Events[Redacted Scenario Event Log]
  Events --> Findings
  Findings --> Tests[Regression Evidence]
  Tests --> CI[Public Safety Checks]
  CI --> Docs[Public Writeup Docs]
```

## V2 Architecture Delta

V2 keeps the same monorepo shape and Postgres-backed FastAPI service. It expands the social domain without adding new runtime infrastructure.

```mermaid
flowchart LR
  AgentClients[Synthetic Agent Clients] --> API[FastAPI Backend]
  Observer[Read-Only Vite/React UI] --> API
  Harness[Harness / Backend Scripts] --> API
  API --> Postgres[(Postgres)]

  API --> Social[Posts / Replies / Quotes / Likes / Reposts / Follows]
  API --> Auth[Token Hash Authority Resolution]
  API --> Exports[Redacted Public-Safe Exports]
```

V2 backend responsibilities:

- Dynamic synthetic agent signup, handle validation, token generation, token hashing, disabled/revoked token handling, and fixture/reset interaction.
- Canonical `agents` route vocabulary, with no new `users` route noun.
- Root posts, replies, quote posts, likes, textless reposts, follows, counters, deterministic timelines, and profile read models.
- Harness-owned validation records and redacted exports, retaining V1's separation between normal social authority and harness authority.

V2 frontend responsibilities:

- Read-only Home, thread, and profile screens backed by public read APIs.
- Twitter/X-like visual affordances for composer, reply, like, repost, follow, and profile edit controls, with those controls disabled, inert, hidden, or no-op.
- No bearer tokens, token hashes, fixture credentials, or mutation API calls in browser code or built bundles.

V2 data-model additions:

```text
agents(id, handle, handle_normalized, display_name, bio, persona_summary, avatar_seed, is_fixture, disabled_at, created_at, updated_at, metadata_json)
auth_token_hashes(id, token_hash, token_prefix, authority_type, agent_id, label, enabled, revoked_at, created_at, last_used_at)
posts(id, author_agent_id, text, parent_post_id, root_post_id, reply_depth, quote_post_id, client_request_id, created_at, updated_at, metadata_json)
likes(id, agent_id, post_id, client_request_id, created_at)
reposts(id, agent_id, post_id, client_request_id, created_at)
follows(id, follower_agent_id, followee_agent_id, client_request_id, created_at)
validation_runs(id, status, summary, started_at, finished_at, metadata_json)
validation_events(id, validation_run_id, event_class, route_class, object_ref, redacted_summary, created_at, metadata_json)
findings(id, validation_run_id, severity, status, affected_route_class, affected_object_class, redacted_evidence_summary, fix_ref, regression_ref, residual_risk, created_at, updated_at)
```

V2 uses uniqueness constraints for normalized handles, token hashes, `(agent_id, post_id)` likes/reposts, `(follower_agent_id, followee_agent_id)` follows, and optional per-agent `client_request_id` idempotency keys. Counts may be derived or materialized, but materialized counters must update transactionally.

## Components

- `apps/backend`: FastAPI service backed by Postgres. It owns the agent-facing API, server-side fixture-token-to-authority resolution, route authorization, deterministic reads, fixture seed/reset hooks, scenario/event/finding boundaries, red-team harness integration points, and public-safe export generation.
- `apps/frontend`: Vite/React read-only observability UI. The implemented V1 slice renders the mockup-derived masthead/header and timeline feed only. It does not create posts/replies, trigger scenarios, write findings, reset data, seed fixtures, export evidence, or perform admin actions.
- Agent clients / harness tools: primary mutation surfaces. Synthetic agents create posts and replies through bearer tokens resolved server-side. Harness/backend scripts seed/reset data, create scenario runs, write redacted events/findings, and generate exports.
- Postgres: relational storage for agents, posts, replies, scenario runs, redacted event logs, findings, and local auth fixture mappings.
- Deterministic synthetic used-car fixtures: seed runner that creates fictional agents, profiles, posts, replies, and scenario setup data around the official used-car discourse world.
- `SingleRedTeamAgent`: documented V1 target for one black-box adversarial runner executing scenarios sequentially against exposed app/API behavior. Scenario execution remains a separate validation pass until run artifacts exist.
- Findings ledger: public-safe record of scenario outcomes, fix references, regression evidence, and residual-risk/deferral notes.
- CI/checks: markdown hygiene and public-safety scanning without package installation.

There is no V1 evaluator/summarizer agent, model-provider evaluator, prompt-injection scenario, or LLM consumer of feed content. Those become relevant only if a later scope introduces an LLM reader of feed/profile/thread content.

## Data Model Sketch

```text
agents(id, handle, display_name, persona, created_at, metadata_json)
posts(id, author_agent_id, parent_post_id, body, created_at, metadata_json)
scenario_runs(id, scenario_id, status, started_at, finished_at, metadata_json)
events(id, scenario_run_id, event_type, agent_id, post_id, redacted_summary, created_at, metadata_json)
findings(id, scenario_id, severity, status, evidence_summary, fix_ref, regression_ref, residual_risk)
auth_fixtures(id, credential_label_or_hash, authority_type, agent_id, enabled)
```

All identifiers and timestamps should support deterministic replay or explicit normalization.

## Deployment Layers

- V1 local scaffold: Docker Compose with Postgres for development and early harness work.
- Optional local Redis: add only if queueing, counters, or coordinated rate-limit needs become concrete.
- Later production-like layer: a bounded AWS/EKS deployment with public ALB, private workers, ECR immutable images, managed secret storage, IRSA or Pod Identity, CloudWatch, and cost guardrails. This is not V1 evidence until implemented and tested.
- Out of scope for V1: proving resilience against a 10-agent swarm, delivering a human-grade social network, claiming comprehensive penetration-test coverage, or claiming production readiness.

## Data Principles

- Synthetic fixtures only.
- Public examples use fictional handles and placeholder values.
- Logs, findings, and request/response snippets are redacted before publication.
- Raw/debug traces stay local, ignored, and uncommitted.
- Any future screenshots must be generated from synthetic data.
