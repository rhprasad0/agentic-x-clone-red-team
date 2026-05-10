# x-clone / CARBOTS Strix instructions

## Authorization and safety

You are authorized to test only the x-clone / CARBOTS synthetic social app targets supplied by the CLI. This is a scoped AI-assisted web/API security assessment with controlled destructive app-state testing.

Allowed destructive behavior is limited to resettable synthetic app state: synthetic agents, posts, replies, quote posts, likes, reposts, follows, counters, feeds, and app consistency. Do not perform denial-of-service, stress testing, volumetric fuzzing, cost-spike behavior, cloud infrastructure mutation, credential exfiltration, third-party attacks, or destructive AWS/Kubernetes actions.

If a test starts behaving like DoS, broad fuzzing, cloud-chaos, secret exfiltration, or cost amplification, stop that path and document why it was skipped.

## Target model

- FastAPI backend and React/Vite frontend.
- Public frontend is intended to be read-only.
- Public API is intended for read routes and public mutation denial.
- Private/operator mutation path is authorized only when supplied as an explicit target or credential context.
- Data is fictional synthetic social activity only.
- Synthetic agent identity should be resolved server-side from bearer credentials, not trusted from request bodies.

## Required observability behavior

During the scan, maintain notes sufficient to reconstruct:

1. route classes discovered;
2. browser flows attempted;
3. Caido/proxy request classes used for replay;
4. payload categories, without exposing secrets;
5. actor class used: anonymous, synthetic agent, wrong synthetic agent, harness/operator;
6. expected vs observed status class;
7. whether app state was changed;
8. whether reset/reseed or retest is required.

For every potential finding, include:

- finding title;
- affected route or component class;
- vulnerability class;
- attacker persona;
- preconditions;
- concise reproduction steps;
- observed impact;
- evidence summary;
- false-positive checks performed;
- remediation idea;
- retest steps.

## Priority attack paths

1. Public read-only boundary bypass: anonymous public mutation attempts against posts, replies, quotes, likes, reposts, follows, signup, and validation/export routes.
2. Cross-agent authorization / IDOR: one synthetic agent attempting to modify, delete, like, repost, follow, or otherwise act as another.
3. Function-level authorization: ordinary synthetic agent attempting harness/operator-only routes.
4. Mass assignment: protected fields in signup and mutation payloads.
5. Token handling: bearer/token leakage in responses, logs, frontend bundles, exports, errors, or redirects.
6. XSS and unsafe rendering: harmless HTML/script/URL/control-character probes in synthetic post/profile text.
7. Business logic: duplicate likes/reposts/follows, delete-only-caller behavior, quote/reply edge cases, stale tokens, replayed request IDs, idempotency-key reuse across actors/routes/targets/bodies.
8. Race/consistency: bounded concurrency only; check counters, timelines, profiles, and thread consistency without load testing.
9. Query/resource bounds: cursor tampering, malformed cursors, excessive limits, filter/sort abuse, and error disclosure.
10. Deployment exposure: public docs/debug/CORS posture and accidental mutation path exposure, without cloud-infra mutation.

## Evidence boundaries

Keep raw request/response bodies, tokens, cookies, private hostnames, exploit payload details, and tool workspaces private. Public outputs should use route classes, status classes, synthetic object IDs only when safe, and sanitized summaries.

Do not claim a finding is confirmed unless you validated it with a working proof or a clear manual reproduction. Mark uncertain items as hypotheses.
