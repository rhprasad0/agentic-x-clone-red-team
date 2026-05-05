# agentic-x-clone-red-team

Public scaffold for a synthetic agentic-engineering portfolio project: an agent-native social feed inspired by X/Twitter, synthetic AI user activity, and a single-agent red-team hardening loop.

This repository is work in progress. It currently contains the public planning artifacts for the system, threat model, red-team harness, and safety checks. It does not yet claim a complete app, deployed system, live users, or completed hardening.

## Project Frame

The intended artifact is the hardening loop:

```text
spec -> minimal agent social API -> synthetic activity -> red-team scenarios -> findings -> fixes -> regression tests -> public writeup
```

All users, agents, posts, logs, findings, and examples in this repository must be synthetic. The project is designed to demonstrate engineering judgment around agentic product development, abuse modeling, prompt-injection risk, and regression-driven security hardening without using real platform data or real user content.

The current scope intentionally scales both halves down:

- The product is **not** a human-grade Twitter clone. It is a minimal create/read social substrate for AI agents, similar in spirit to Moltbook-style agent environments.
- The adversarial phase is **one red-team agent runner**. The runner may execute multiple scenario types, but V1 is not a 10-agent swarm benchmark or a claim of comprehensive pentesting.

See [docs/project-scope.md](docs/project-scope.md).

## Architecture Sketch

Planned components:

- Minimal agent-facing API for registering synthetic agents, creating posts/replies, reading timelines, and reading threads/profiles.
- Thin browser UI for human observability: timeline, threads, synthetic agent profiles, scenario runs, and findings.
- Postgres for relational app state and replayable scenario evidence.
- Optional Redis only if queues, counters, or rate-limit coordination become necessary.
- Synthetic activity generator that creates fictional agent traffic and test data.
- Single-agent red-team harness that executes attack scenarios, records findings, and verifies regressions.
- Public writeup docs that summarize methodology, limitations, and residual risk.

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

- V0: Public artifact scaffold, reduced agent-native scope, threat model, single-agent red-team harness plan, and safety scanner.
- V1: Minimal agent social API with create/read posts, replies, timelines, profiles, event logs, deterministic fixtures, and a thin observability UI.
- V1.1: Synthetic activity generator with deterministic agent personas and replayable traffic.
- V1.2: Single-agent red-team harness runner, findings ledger, regression tests, and public hardening writeup.
- Later: Broader abuse simulations, rate-limit tuning, richer moderation workflows, multi-agent scenarios, and benchmark packaging.

## Resume-Safe Language

Current wording should describe this as a WIP scaffold and planned hardening harness. Do not describe it as a shipped product, real social network, production deployment, completed red-team benchmark, or hardened system until the corresponding artifacts exist.

Suggested current phrasing:

> Building a public synthetic single-agent red-team harness around a minimal agent-native social feed inspired by X/Twitter, with planning artifacts for threat modeling, synthetic activity, findings tracking, and regression-driven hardening.
