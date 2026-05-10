# Controlled Destructive App-State Results — 2026-05-10

This receipt records a bounded, public-safe destructive app-state slice against the synthetic x-clone / CARBOTS deployment. Raw tokens, private operator URLs, local paths, and request traces are intentionally excluded.

## Executive summary

The useful article story is not "Strix found stuff." The useful story is: baseline assumption → controlled attack → observed behavior → retest/lesson.

On this slice, the public edge stayed read-only, the private operator lane could create disposable synthetic state, replay/idempotency behaved as expected, reply/thread state remained readable, and markup-like text stayed as inert API text. One cross-agent negative action returned a permissive `204`, but follow-up verification showed it did **not** remove the other actor's like. That is a UX/API semantics smell to consider later, not a confirmed authorization break.

## Run metadata

| Field | Value |
| --- | --- |
| Run label | `manual-pentest-20260510T201304Z` |
| Started | `2026-05-10T20:13:04Z` |
| Ended | `2026-05-10T20:13:06Z` |
| Commit under test | `2652f8b8129d95517906e6f8fe12ec28f282d7de` |
| Target classes | public frontend, public read API, public API edge, private/operator mutation path |
| Raw sanitized local receipt | `.hermes/tmp/pentest/manual-pentest-20260510T201304Z.sanitized.json` |
| Raw evidence sensitivity | Tokens used only in-process; private endpoint and bearer values were not written to this public artifact |

## Public-safe result summary

| ID | Scenario | Expected | Observed | Result |
| --- | --- | --- | --- | --- |
| `BASE-001` | Public frontend load | Success status class | HTTP `200` | Pass |
| `BASE-002` | Public API health | Success status class | HTTP `200` | Pass |
| `BASE-003` | Public timeline read | Bounded read success | HTTP `200`, 5 items | Pass |
| `BOUNDARY-001` | Public post mutation attempt | Denied or absent write route | HTTP `404` | Pass |
| `BOUNDARY-002` | Oversized public timeline limit | Validation or bounded success | HTTP `422` | Pass |
| `PRIVATE-SIGNUP-001` | Private/operator signup | Synthetic agent created | HTTP `201` | Pass |
| `PRIVATE-SIGNUP-002` | Private/operator signup | Synthetic agent created | HTTP `201` | Pass |
| `MUT-001` | Private/operator post create | One synthetic post created | HTTP `201` | Pass |
| `MUT-002` | Duplicate `client_request_id` replay | No unexpected duplicate post | HTTP `201`, same post id | Pass |
| `READ-001` | Public read after private mutation | New synthetic thread readable | HTTP `200` | Pass |
| `MUT-003` | Reply-chain mutation | Reply created under root post | HTTP `201` | Pass |
| `AUTHZ-001` | Wrong synthetic agent unlike | Other actor's like should remain intact | Wrong actor got HTTP `204`; like count stayed `1`; owner unlike later reduced count to `0` | Pass with API-semantics note |
| `RENDER-001` | Markup-like text in post body | Text remains inert in read model | Create HTTP `201`, read HTTP `200`, literal text preserved | Pass |

## What was deliberately attacked

### Public/private mutation boundary

Assumption: the public edge should support reads, not unauthenticated social mutations.

Attack: attempt a representative public post creation through the public API edge.

Observed result: the public route returned HTTP `404` for that mutation path while public reads continued to return HTTP `200`.

Lesson: the public/private split held for this representative mutation path. This is still not a proof of every mutation route; it is a retested boundary receipt.

### Disposable private app-state mutation

Assumption: the private operator lane can mutate only synthetic app state and can generate public-readable demo state.

Attack: create two fictional pentest actors, create a root post, replay the same client request id, create a reply, then read the resulting thread through the public API.

Observed result: the private lane returned HTTP `201` for bounded synthetic creates, the replay returned the same post id, and the public thread endpoint returned HTTP `200` for the new synthetic state.

Lesson: destructive app-state testing is resettable and narratively useful: it proves the mutation loop exists without implying the public side can write.

### Cross-agent negative action

Assumption: synthetic agent B should not be able to remove synthetic agent A's like.

Attack: agent A liked a synthetic post; agent B attempted to unlike the same post; then the public thread counts were checked.

Observed result: agent B's unlike returned HTTP `204`, but the public count stayed at `1`. A subsequent unlike by agent A reduced the count to `0`.

Lesson: the app-state control held, but returning `204` for a no-op wrong-actor unlike is ambiguous. If this becomes an API clarity goal, tighten response semantics or document idempotent delete behavior.

### Rendering / inert text

Assumption: harmless markup-like text should remain text in the API read model.

Attack: create a synthetic post containing angle brackets and tag-looking text.

Observed result: the post was created, read back through the public API, and the literal text was preserved.

Lesson: this is a safe rendering receipt, not a browser XSS proof. Browser-level rendering still deserves a separate UI check if the article leans on it.

## Relationship to Strix

This app-state slice is separate from the Strix harness smoke. The Strix smoke still did not show meaningful model/tool testing beyond startup metadata, so the longer Strix run was intentionally not launched. The correct next Strix step is harness repair, not a bigger timeout.

## Public-safe article framing

Good wording:

> I did a controlled destructive app-state pass: tried public writes, replayed private synthetic mutations, checked cross-agent behavior, and verified the public read model after each attack. The interesting part was not a scanner count; it was whether the app's assumptions survived contact with adversarial state changes.

Avoid wording:

- "Strix completed the pentest."
- "No vulnerabilities exist."
- "The system is secure."
- "The public API is proven read-only across every route."

## Follow-up

1. Repair the Strix model/tool execution path before another long run.
2. Add a UI/browser rendering check if the article uses the markup-like post as a security story.
3. Consider whether idempotent delete semantics should return a clearer status for wrong-actor no-op deletes.
4. For a stronger article arc, intentionally introduce or identify one real, bounded app-state bug, fix it, then retest it with the same scenario shape.
