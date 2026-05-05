# agentic-x-clone-red-team

Public scaffold for a synthetic agentic-engineering portfolio project: a production-style X/Twitter clone, synthetic AI user activity, and a single-agent red-team hardening loop.

This repository is work in progress. It currently contains the public planning artifacts for the system, threat model, red-team harness, and safety checks. It does not yet claim a complete app, deployed system, live users, or completed hardening.

## Project Frame

The intended artifact is the hardening loop:

```text
spec -> app -> synthetic activity -> red-team scenarios -> findings -> fixes -> regression tests -> public writeup
```

All users, posts, messages, logs, findings, and examples in this repository must be synthetic. The project is designed to demonstrate engineering judgment around agentic product development, abuse modeling, and regression-driven security hardening without using real platform data or real user content.

The current scope intentionally scales the adversarial phase down to **one red-team agent runner**. The runner may execute multiple scenario types, but V1 is not a 10-agent swarm benchmark or a claim of comprehensive pentesting. See [docs/project-scope.md](docs/project-scope.md).

## Architecture Sketch

Planned components:

- Next.js-style web app for feed, posting, profiles, notifications, and admin review surfaces.
- Postgres for relational app state.
- Redis for queues, counters, rate-limit state, and synthetic activity coordination.
- Synthetic activity generator that creates fictional traffic and test data.
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

- V0: Public artifact scaffold, scaled scope, threat model, single-agent red-team harness plan, and safety scanner.
- V1: Minimal social app surface with auth, posting, feed, profiles, moderation queue, and admin review.
- V1.1: Synthetic activity generator with deterministic fixtures and replayable traffic.
- V1.2: Single-agent red-team harness runner, findings ledger, regression tests, and public hardening writeup.
- Later: Broader abuse simulations, rate-limit tuning, richer moderation workflows, and benchmark packaging.

## Resume-Safe Language

Current wording should describe this as a WIP scaffold and planned hardening harness. Do not describe it as a shipped product, real social network, production deployment, completed red-team benchmark, or hardened system until the corresponding artifacts exist.

Suggested current phrasing:

> Building a public synthetic single-agent red-team harness around a production-style X/Twitter clone, with planning artifacts for threat modeling, synthetic activity, findings tracking, and regression-driven hardening.

