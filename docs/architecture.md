# Architecture

This is the planned V1 architecture. It documents the target shape before the app and harness are implemented.

```mermaid
flowchart LR
  Browser[Browser UI] --> App[Next.js App]
  App --> Auth[Auth and Session Layer]
  App --> API[Route Handlers / Server Actions]
  API --> Postgres[(Postgres)]
  API --> Redis[(Redis)]
  API --> Mod[Moderation Queue]
  API --> Audit[Audit Log]

  Synth[Synthetic Activity Agents] --> API
  RedTeam[Red-Team Harness] --> API
  RedTeam --> Findings[Findings Ledger]
  Findings --> Tests[Regression Tests]
  Tests --> CI[Public CI Checks]
  CI --> Docs[Public Writeup Docs]
```

## Components

- Browser UI: feed, compose, profile, notifications, report flow, moderation queue, and admin review surfaces.
- Next.js app: planned web framework boundary for rendering, route handlers, and server-side authorization.
- Auth and session layer: planned authentication, session validation, and role checks for synthetic users.
- Postgres: relational storage for accounts, posts, follows, reports, moderation actions, and audit events.
- Redis: rate-limit counters, queues, and synthetic activity coordination.
- Synthetic activity agents: deterministic agents that create fictional users, posts, follows, likes, reposts, and reports.
- Red-team harness: scenario runner for auth, authorization, abuse, prompt-injection, data-leak, rate-limit, and admin-boundary tests.
- Findings ledger: public-safe record of scenario outcomes, fixes, regressions, and residual-risk notes.
- CI checks: markdown hygiene and public-safety scanning without package installation.

## Data Principles

- Synthetic fixtures only.
- Public examples use fictional handles and placeholder values.
- Logs and findings should be redacted before publication.
- Any future screenshots must be generated from synthetic data.

