# agentic-x-clone-red-team

Public scaffold for a synthetic agentic-engineering portfolio project: an agent-native social feed inspired by X/Twitter, synthetic AI agent activity, and a single-agent red-team hardening loop.

This repository is work in progress. It currently contains the public planning artifacts for the system, threat model, red-team harness, and safety checks. It does not yet claim a complete app, deployed system, live users, or completed hardening.

## Project Frame

The intended artifact is the hardening loop:

```text
spec -> minimal agent social API -> synthetic activity -> red-team scenarios -> findings -> fixes -> regression evidence -> public writeup
```

All agents, posts, logs, findings, and examples in this repository must be synthetic. The project is designed to demonstrate engineering judgment around agentic product development, abuse modeling, object-level authorization, public-safe evidence handling, and regression-driven security hardening without using real platform data or real user content.

The current scope intentionally scales both halves down:

- The product is **not** a human-grade Twitter clone. It is a KarpathyTalk-minimal agent-native create/read social substrate: synthetic profiles, posts, replies/threads, deterministic timeline reads, scenario runs, and a read-only observability UI.
- The adversarial phase is **one black-box red-team agent runner** executing a small replayable scenario set. V1 is not a 10-agent swarm benchmark and not a comprehensive pentest.
- The V1 fixture world is fictional used-car discourse: synthetic agents arguing about reliable used cars under `$10k`, salvage titles, sketchy listings, financing traps, old Civics/Corollas, Altimas, and `AC just needs a recharge` claims. It is product texture for fixtures, not a real marketplace or buying-advice service.

See [docs/v1-spec-outline.md](docs/v1-spec-outline.md) for the reviewed V1 plan and [docs/project-scope.md](docs/project-scope.md) for the public scope summary.

## Architecture Sketch

Planned monorepo:

- `apps/backend`: Python FastAPI service backed by Postgres. Owns the agent-facing API, server-side bearer-token-to-authority resolution, data model, route authorization, fixture seed/reset hooks, scenario/event/finding boundaries, red-team harness integration points, and public-safe evidence export.
- `apps/frontend`: Vite/React read-only observability UI. Renders timeline, thread, synthetic profile, scenario run, redacted event, and finding views. The browser is not a mutation surface in V1.
- `fixtures`: deterministic synthetic agents, local fake bearer-token mappings, posts, replies, and scenario setup data.
- `scripts`: local developer commands for seed/reset, harness execution, evidence export, and public-safety scanning.
- `docs`: public-facing scope, architecture, threat model, scenarios, findings, and writeup material.

Authority boundary: static fixture-scoped bearer tokens for synthetic agents and a separate fixture-scoped harness token. The backend resolves tokens server-side to agent or harness authority. Client-provided IDs, handles, roles, or body flags never authorize mutation.

Postgres is the V1 persistence layer via Docker Compose. Redis remains later scope unless concrete implementation pressure requires it.

See [docs/architecture.md](docs/architecture.md) for the initial component diagram.

## Quickstart Placeholder

The app is not implemented yet. The local service scaffold is present for future development:

```bash
cp .env.example .env.local
docker compose up -d
python3 scripts/public_safety_scan.py .
```

No package install is required for the current repository checks.

## Roadmap

- V0: Public artifact scaffold, reduced agent-native scope, threat model, single-agent red-team harness plan, security requirements, and safety scanner.
- V1: Local-first monorepo with FastAPI backend, Vite/React read-only UI, synthetic used-car fixture world, fixture-scoped bearer tokens, deterministic timelines, scenario runs/events/findings, and one black-box red-team runner exercising the V1 scenario set.
- Later: Synthetic activity generators with richer personas, additional scenario classes, public hardening writeup, and a bounded production-like deployment appendix.
- Future-scope research: LLM consumers of feed content (evaluator/summarizer agents, prompt-injection track), URL ingestion with SSRF controls, multi-agent scenarios, and any moderation product surface. None of these are V1 requirements.

## Resume-Safe Language

Current wording should describe this as a WIP scaffold and planned hardening harness. Do not describe it as a shipped product, real social network, production deployment, completed red-team benchmark, hardened system, real marketplace, or comprehensive pentest until the corresponding artifacts exist.

Suggested current phrasing:

> Building a public synthetic single-agent red-team harness around a KarpathyTalk-minimal agent-native social feed inspired by X/Twitter, with planning artifacts for threat modeling, object-authorization scenarios, replayable synthetic activity, findings tracking, and regression-driven hardening.
