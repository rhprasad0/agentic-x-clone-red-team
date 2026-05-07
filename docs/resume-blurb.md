# Resume Blurb

## Current Wording

Use this for the current local V2 state:

> Built `agentic-x-clone-red-team`, a public synthetic agentic-engineering project: a local FastAPI/Postgres social feed for fictional AI agents arguing about used cars, with read-only React observability UI, synthetic signup/tokens, posts/replies/quotes/likes/reposts/follows, server-side authority resolution, route/control documentation, redacted evidence exports, and public-safety checks.

Short version:

> Local synthetic X/Twitter-like feed for AI agents plus bounded red-team/hardening surface, focused on server-side authority, social-object authorization, deterministic fixtures, redacted evidence, and regression-friendly public artifacts.

## If Discussing Hardening

Use only evidence-backed language:

> The repo documents a bounded single-runner red-team/hardening surface and includes route/control artifacts for local validation. I avoid claiming a closed hardening loop unless the finding, fix, and regression artifacts exist.

## Avoid Until Evidence Exists

- Do not call the app deployed-service ready.
- Do not claim non-synthetic people, external platform data, real listings, or a live social network.
- Do not describe it as a human-grade Twitter/X clone or real marketplace.
- Do not claim closed hardening loop before findings, fixes, and regression tests exist.
- Do not present synthetic coverage as proof of broad security.
- Do not imply a multi-agent pentest, 10-agent pentest, external assessment, or swarm benchmark.
- Do not describe prompt-injection/evaluator/model-provider hardening unless a later scope actually introduces an LLM consumer of feed content.
