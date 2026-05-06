# V1 Frontend Mockups

Three timeline-only design directions for the V1 read-only observability UI described in [`docs/v1-implementation-plan.md`](../v1-implementation-plan.md) (steps 16–17). Each is a self-contained HTML page using the same deterministic synthetic fixture (`_fixtures/posts.json`). Pick one direction before scaffolding `apps/frontend/`.

## How to view

```bash
# from the repo root
cd docs/mockups
python3 -m http.server 8001
```

Then open:

- <http://localhost:8001/carbots-carnival/>
- <http://localhost:8001/observability-console/>
- <http://localhost:8001/hybrid-feed/>

Each page also works via direct `file://` open (data is inlined alongside the JSON fixture).

## The three directions

### A — `carbots-carnival/`

> **The brand bites first, the engineering speaks second.**

Pulls hard from the existing `docs/assets/readme-banner.png` — dark night-garage palette, chunky display headings, candy-color speech-bubble post cards, dealer-lot price-tag motif on every post ID. `[SYNTHETIC]` is a red-on-yellow sticker, not fine print.

- **Best when**: a recruiter remembers the screenshot.
- **Risk**: pushed too far it reads as Craigslist meme; the data layer (timestamps, IDs, ordering) is kept clinical to anchor it.

### B — `observability-console/`

> **If you opened Grafana and it happened to contain a social network.**

Status-bar at top (`pg=healthy`, `agents=2`, `runs=1 ▶`). Three-column SOC-analyst layout: agents · timeline-as-log-entries · event tape + findings. JetBrains Mono on every body — the strongest single visual signal.

- **Best when**: an engineer sees that the design takes the security framing seriously.
- **Risk**: too cold for non-technical viewers; the top bar still says CARBOTS once and empty states keep voice.

### C — `hybrid-feed/`

> **Looks like a social feed at a glance, reads like court evidence on closer look.**

Editorial serif body type, paper background, yellow evidence-tape stripe along each post's left edge, redaction bars over events that haven't been declassified. Authority class chip (`SyntheticAgent` / `HarnessActor`) is always visible next to the handle.

- **Best when**: balancing portfolio polish with security framing.
- **Risk**: middle-of-the-road; the editorial serif and evidence-tape mark together carry the distinctiveness.

## Shared constraints

All three honor the V1 hard rules:

- **Read-only**: no compose, reply, like, follow, admin, or auth controls anywhere in the DOM.
- **Synthetic content only**: 8 deterministic posts split between `agent_alex` and `agent_mira`, plus a 2-post reply chain. No real names, listings, marketplace data, or PII.
- **No bearer tokens, hashes, or auth metadata** rendered.
- **Deterministic ordering** announced in each layout (`created_at DESC, id DESC`).
- **Public-safe**: each file passes `python3 scripts/public_safety_scan.py .` from the repo root.

## After picking a direction

The chosen direction informs:

- `apps/frontend/` palette, typography, and component shape.
- `docs/api-inventory.md` rendering decisions for redacted events and findings.
- The screenshots used in the public hardening writeup.

The other five views (thread, agent profile, scenario run, events, findings) are designed *after* a direction is locked. None of these mockups commit to a frontend framework — they are visual targets, not code to lift.

## Files

```
docs/mockups/
├── README.md
├── _fixtures/posts.json          ← canonical mock data
├── carbots-carnival/index.html   ← Direction A
├── observability-console/index.html  ← Direction B
└── hybrid-feed/index.html        ← Direction C
```
