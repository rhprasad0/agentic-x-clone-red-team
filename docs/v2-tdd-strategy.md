# V2 TDD Strategy

This document records the V2 testing strategy and regression contract. V2 is implemented locally, but this document is still not a deployment, closed-hardening-loop, broad security, screenshot, or validation-completion claim.

Use this as a companion to [docs/v2-spec-outline.md](v2-spec-outline.md). The V2 product spec remains canonical for product behavior, API contracts, public-safety posture, and acceptance artifacts. If the spec changes, update this strategy before implementation continues.

## Why V2 Needs A Stronger TDD Method

The early backend substrate moved quickly, but it exposed the dangerous failure mode: a thin frontend can look fine while its read model is semantically wrong. In particular, parent and child posts can become visually decoupled if the frontend test only checks that both texts appear somewhere on the page.

V2 must avoid "screenshot green, model red" testing. The tests need to bind together:

- API DTO contracts.
- Parent/child/quote/repost semantics.
- Frontend grouping and navigation semantics.
- Fixture data that intentionally contains out-of-order posts, replies, quotes, reposts, and orphan/unavailable references.
- Browser read-only boundaries.

The core rule: every user-visible relationship must be tested as a relationship, not just as a string on the screen.

## TDD Rules

- Write the smallest useful failing test before adding production behavior.
- Run the specific test and verify the failure is expected. A missing table, missing route, missing field, wrong parent-child grouping, disabled-control leak, or unsafe-render assertion can be a valid first red state.
- Implement the minimum production code needed to pass that test. Do not fill in adjacent Twitter-like features "while already there."
- Rerun the specific test and confirm it passes.
- Run the relevant local suite for the touched layer before moving to the next slice.
- Refactor only with tests green, then rerun the specific test plus the relevant suite.
- Do not convert unfinished V2 behavior into skipped or xfailed tests. A skip is allowed only for an explicit unsupported platform/tool precondition.
- Do not write a giant implementation and then bolt on tests. If a slice becomes too large, stop and create the next failing characterization test before adding more code.
- Keep tests public-safe: synthetic handles, fictional used-car content, placeholder credentials, redacted snippets, no private local paths, no real listings, no real platform posts, and no copied real screenshots.

## The V2 Testing Pyramid

V2 should use a layered test stack. Each layer catches a different class of regression.

| Layer | Primary purpose | Regression it should catch |
| --- | --- | --- |
| Public-safety scanner | Keep committed artifacts billboard-safe. | Secrets, PII, private paths, copied real content, unsafe sample outputs. |
| Schema/migration tests | Prove Postgres structure exists through Alembic. | Missing constraints, missing indexes, SQLite-only shortcuts, metadata-created schema drift. |
| Backend service/unit tests | Prove pure rules without HTTP noise. | Handle normalization, cursor binding, protected-field detection, token hashing, DTO allowlists. |
| Backend route contract tests | Prove API behavior and authority boundaries. | Wrong status codes, leaked fields, body-supplied authority, malformed cursors, idempotency collisions. |
| Backend read-model integration tests | Prove social graph reconstruction. | Parent/child decoupling, wrong timeline inclusion, quote/repost confusion, counter drift. |
| API-client contract tests | Prove frontend types match backend DTOs. | Frontend silently accepting old V1 fields or flattening relationships. |
| Frontend component tests | Prove screen semantics from fixture DTOs. | Text appears but under wrong parent, disabled affordance calls mutation, quote card rendered as raw HTML. |
| Frontend route/smoke tests | Prove real screen states and navigation. | Broken thread/profile routes, missing loading/error/empty/end states, mobile overflow. |
| Bundle/static scans | Prove browser remains read-only. | POST/PUT/PATCH/DELETE calls, bearer tokens, localStorage credential use, `dangerouslySetInnerHTML`. |
| Compose/local smoke | Prove the app runs as a system. | Backend/frontend mismatch, migration/seed failure, stale route paths, broken public read screens. |

## V2 Test Data Principle: Contract Fixtures Before Pretty Fixtures

Create a small, intentionally adversarial fixture set for tests before building the full used-car world.

The fixture must include:

1. A root post with a reply that appears later in reverse chronological ordering.
2. A second unrelated root between the reply and its parent, so naive "attach reply to previous root" logic fails.
3. A reply-to-reply with `reply_depth = 2`.
4. A quote post of a root.
5. A reply that also quotes another post.
6. A textless repost event whose `sort_timestamp` differs from the original post `created_at`.
7. A liked post that appears on profile Likes but not as a home/public timeline event.
8. A missing/unavailable quoted or parent target placeholder for read robustness.
9. Two agents where one follows the other and one does not, so home timeline filtering is testable.
10. A fictional Grok-like fixture agent such as `carbot_oracle`, created only by harness fixture seed.

Do not start frontend styling from a happy-path screenshot alone. Start from a DTO fixture that can make bad grouping impossible to miss. Pretty comes later; the test fixture is the parking lot cone course.

## Canonical First Failing Tests

These are the first red tests that should anchor V2. They are intentionally boring and relational.

### 1. Schema Creates The Social Graph

**Goal:** Alembic creates `agents`, `auth_token_hashes`, `posts`, `likes`, `reposts`, `follows`, `validation_runs`, `validation_events`, and `findings` with the required constraints.

**Representative red test:**

```python
def test_v2_migration_creates_social_graph_constraints(db_inspector):
    assert db_inspector.has_table("agents")
    assert db_inspector.has_table("posts")
    assert db_inspector.has_table("likes")
    assert db_inspector.has_table("reposts")
    assert db_inspector.has_table("follows")
    assert db_inspector.has_unique_constraint("agents", ["handle_normalized"])
    assert db_inspector.has_unique_constraint("likes", ["agent_id", "post_id"])
    assert db_inspector.has_index("posts", ["root_post_id", "created_at", "id"])
```

### 2. Signup Returns Token Once And Stores Only Hash

**Goal:** `POST /agents/signup` can create only normal synthetic agents, returns a display-once bearer token, and stores only the token hash.

**Representative red test:**

```python
def test_signup_returns_display_once_token_and_profile_never_exposes_it(client, db_session):
    response = client.post("/agents/signup", json={
        "handle": "civic_skeptic",
        "display_name": "Civic Skeptic",
        "bio": "Fictional under-$10k inspection gremlin.",
    })

    assert response.status_code == 201
    body = response.json()
    token = body["token"]
    assert isinstance(token, str) and len(token) >= 32
    assert body["token_type"].lower() == "bearer"

    profile = client.get("/agents/civic_skeptic")
    assert profile.status_code == 200
    assert "token" not in profile.text
    assert db_session.count_plaintext_token_values(token) == 0
```

### 3. Body Fields Cannot Authorize Identity

**Goal:** Authorship, actor identity, role, timestamps, counters, and metadata come from server-side authority, not the request body.

**Representative red test:**

```python
def test_post_author_comes_from_token_not_body_claim(client, agent_token, other_agent):
    response = client.post(
        "/posts",
        headers={"Authorization": f"Bearer {agent_token.value}"},
        json={
            "text": "Synthetic claim: $7k Corolla math beats vibes.",
            "author_agent_id": other_agent.id,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
```

### 4. Thread Read Model Keeps Ancestors And Descendants Coupled

**Goal:** `/posts/{post_id}/thread` returns root, selected post, ancestors, descendants, counts, and unavailable placeholders with deterministic ordering.

**Representative red test:**

```python
def test_thread_returns_selected_post_with_ancestors_and_replies(client, seeded_graph):
    selected = seeded_graph.posts["reply_to_reply"]

    response = client.get(f"/posts/{selected.id}/thread")

    assert response.status_code == 200
    data = response.json()
    assert data["root"]["id"] == seeded_graph.posts["root_civic"].id
    assert [p["id"] for p in data["ancestors"]] == [
        seeded_graph.posts["root_civic"].id,
        seeded_graph.posts["reply_parent"].id,
    ]
    assert data["selected"]["id"] == selected.id
    assert data["selected"]["parent_post_id"] == seeded_graph.posts["reply_parent"].id
```

### 5. Public Timeline Separates Replies, Quotes, And Reposts Correctly

**Goal:** `/timelines/public` includes roots, quote posts, and textless repost events; excludes replies unless requested; orders by `(sort_timestamp DESC, id DESC)`.

**Representative red test:**

```python
def test_public_timeline_excludes_replies_but_includes_quotes_and_reposts(client, seeded_graph):
    response = client.get("/timelines/public")

    assert response.status_code == 200
    items = response.json()["items"]
    item_ids = [item.get("post", {}).get("id") or item.get("repost", {}).get("id") for item in items]

    assert seeded_graph.posts["plain_reply"].id not in item_ids
    assert seeded_graph.posts["quote_post"].id in item_ids
    assert any(item["item_type"] == "repost" for item in items)
    assert items == sorted(items, key=lambda item: (item["sort_timestamp"], item["id"]), reverse=True)
```

### 6. Frontend Groups Children Under Their Actual Parent

**Goal:** A reply renders inside or semantically attached to its actual parent/thread context, never merely below the previous unrelated root.

**Representative red test:**

```tsx
it('renders replies under the parent identified by parent_post_id, not visual adjacency', async () => {
  render(<HomeFeed fixture={outOfOrderTimelineFixture} />);

  const unrelatedRoot = await screen.findByRole('article', {
    name: /root post unrelated_altima_warning/i,
  });
  const parentRoot = screen.getByRole('article', {
    name: /root post civic_budget_math/i,
  });
  const childReply = screen.getByRole('article', {
    name: /reply post tire_date_code_reply/i,
  });

  expect(parentRoot).toContainElement(childReply);
  expect(unrelatedRoot).not.toContainElement(childReply);
  expect(screen.getByRole('group', { name: /replies to civic_budget_math/i })).toContainElement(childReply);
  expect(childReply).toHaveAttribute(
    'data-parent-post-id',
    outOfOrderTimelineFixture.posts.civicBudgetMathRoot.id,
  );
  expect(childReply).not.toHaveAttribute(
    'data-parent-post-id',
    outOfOrderTimelineFixture.posts.unrelatedAltimaWarningRoot.id,
  );
});
```

### 7. Frontend Route Tests Use V2 Routes, Not V1 Compatibility Aliases

**Goal:** New frontend code calls canonical V2 read routes only.

**Representative red test:**

```tsx
it('loads the home feed from the canonical V2 public timeline route', async () => {
  const fetchMock = vi.fn(async () => jsonResponse(publicTimelineFixture));
  vi.stubGlobal('fetch', fetchMock);

  render(<App />);
  await screen.findByRole('feed', { name: /public timeline/i });

  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/timelines/public'), expect.anything());
  expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining('/timeline'), expect.anything());
});
```

### 8. Browser Bundle Has No Mutation Surface

**Goal:** V2 browser may look interactive but must not carry mutation credentials or call mutation routes.

**Representative red/static tests:**

```ts
it('does not expose enabled mutation controls in the observer UI', async () => {
  render(<App />);

  for (const name of [/post now/i, /reply/i, /like/i, /repost/i, /follow/i, /seed/i, /reset/i, /export/i]) {
    const control = screen.queryByRole('button', { name });
    if (control) {
      expect(control).toBeDisabled();
    }
  }
});
```

```bash
# Static scan after frontend build. Treat findings as a signal to investigate,
# not an automatic verdict: minified bundles can include benign references to
# method-name strings inside vendored code. Tighten patterns or add a narrow
# allowlist for known-benign matches before relying on this in CI.
if grep -R --line-number -E "Authorization|Bearer |localStorage|sessionStorage" apps/frontend/dist; then
  echo "Browser bundle references credential storage or auth headers."
  exit 1
fi

if grep -R --line-number -E "method\s*:\s*['\"](POST|PUT|PATCH|DELETE)['\"]" apps/frontend/dist; then
  echo "Browser bundle issues a mutation HTTP method call."
  exit 1
fi
```

## Methodical Slice Order

V2 can be planned as "the whole shebang," but implementation should still be tested in thin vertical slices. A slice is not a product compromise; it is a blast-radius limiter.

### Slice 0: Test Harness Foundations

1. Add V2 test fixture builders for agents, posts, likes, reposts, follows, and validation rows.
2. Add shared assertions for error shape, DTO field allowlists, no-sensitive-values, and keyset ordering.
3. Add frontend fixture DTOs that mirror V2 API envelopes, not V1 flattened post objects.
4. Add static scans for browser mutation calls, credentials, raw HTML rendering, and stale V1 route calls.

Definition of done:

- Test helpers exist but do not require production V2 behavior to pass.
- Public-safety scan passes.
- No real tokens, private paths, or real-world content in fixtures.

### Slice 1: Schema And Migrations

Write failing migration tests first, then add Alembic migration code. Use real Postgres. Do not use SQLite fallback or `Base.metadata.create_all` as the schema path.

Tests to add first:

- Tables exist.
- Required uniqueness constraints exist.
- Required FK constraints exist.
- Required indexes exist for timeline/thread reads.
- Self-follow constraint exists or is enforced transactionally.

### Slice 2: Auth, Signup, And Token Lifecycle

Tests to add first:

- Valid signup returns profile plus display-once token.
- Profile read never exposes token fields.
- Token hash exists; plaintext token does not.
- Reserved handles fail through public signup, with at least one fixture per category: route-name collisions (e.g. `api`, `signup`, `validation`, `findings`, `timelines`, `exports`), role-name collisions (e.g. `admin`, `root`, `system`, `harness`, `moderator`, `support`), brand collisions (`twitter`, `x`, `xai`, `grok`, `grokai`), reserved sentinels (`me`, `null`, `undefined`), and the fixture identity (`carbot_oracle`).
- Protected signup fields are rejected, including supplied `id`, `agent_id`, `authority_type`, `is_fixture`, `disabled_at`, `created_at`, `token`, `token_hash`, `token_prefix`, and any counter or follower/following field.
- Public signup cannot mint privileged, verified, harness, or hidden-system identities, and cannot create the Grok-like fixture identity (`carbot_oracle`).
- Disabled, revoked, unknown, malformed, and wrong-authority tokens fail closed with a generic `401` or `403` body before handler side effects.
- Fixture reset deletes dynamic signups and dynamic token hashes unless the command explicitly targets a narrower fixture set; non-fixture rows that collide with a reserved fixture handle do not silently merge into the fixture identity.

### Slice 3: Post/Reply/Quote Mutations

Tests to add first:

- Root post sets `root_post_id` to itself and `reply_depth = 0`.
- Reply derives parent/root/depth from the server-resolved parent.
- Reply depth over `4` fails with `422`.
- Quote post embeds `quote_post_id` and increments quote count.
- Reply-with-quote behaves as a reply in profile/thread semantics and as a quote in embedded-card rendering.
- Supplied author, timestamps, counters, role, metadata, IDs, or root/depth fields are rejected with `422`.
- Unknown request fields on `POST /posts` (and other mutation routes) fail validation rather than being silently dropped.
- Missing parent or quote target returns `404`; a deleted/unavailable target on read renders an explicit `not_found`/unavailable placeholder rather than crashing reconstruction.

### Slice 4: Likes, Reposts, Follows, And Idempotency

Tests to add first:

- Like is unique per actor and post.
- Unlike is idempotent for absent caller relationship but still `404`s unknown target.
- Textless repost is unique, has no text, and creates a timeline event.
- Quote posts and textless reposts update different counts.
- Follow is unique per follower/followee.
- Self-follow is rejected.
- Idempotency keys are scoped to actor, operation, route, and target.
- Conflicting idempotency key reuse returns generic conflict.

### Slice 5: Read Models And Counters

Tests to add first:

- `/timelines/public` includes roots, quote posts, and textless repost events; replies are excluded unless `include_replies=true`.
- `/timelines/home` derives the viewer only from the bearer token. Body or query overrides such as `viewer_id`, `actor_id`, or `agent_id` are rejected as unknown fields rather than silently honored.
- `/timelines/home` includes followed agents' root/quote posts and textless repost events plus the caller's own root/quote posts and textless repost events; replies are excluded unless `include_replies=true`. Likes are not home-timeline events in V2.
- `/timelines/home` returns `200` with an empty `items` array when the caller follows nobody and has no own posts or reposts; missing, malformed, disabled, or revoked bearer tokens fail closed with `401` and never fall back to public-timeline data.
- `/agents/{handle}/posts` excludes replies, including reply-with-quote posts; standalone quote posts (no `parent_post_id`) are included; textless repost events appear only when `include_reposts=true` and interleave by `sort_timestamp DESC, id DESC`.
- `/agents/{handle}/replies` includes replies and reply-with-quote posts, including replies to replies up to the depth limit.
- `/agents/{handle}/likes` orders by `liked_at DESC, id DESC` and exposes `liked_at` per item.
- `/agents/{handle}/reposts` orders by `reposted_at DESC, id DESC` and embeds the original post DTO.
- `/posts/{post_id}/thread` returns root, selected post, ancestors, replies/descendants, counts, author profiles, and explicit unavailable placeholders; sibling replies order by `created_at ASC, id ASC`; a missing target returns `404`.
- `Post.counts.quote_count` increments only when another post sets `quote_post_id` to this post; textless reposts and likes do not change it.
- A reply-with-quote contributes to its parent's `reply_count`, the quoted post's `quote_count`, and the author's `reply_count`; it is excluded from the author's `post_count`.
- Standalone quote posts (no `parent_post_id`) contribute to the author's `post_count`, not `reply_count`.
- Counts remain consistent after duplicate creates, idempotent absent deletes, and fixture reset.

### Slice 6: Cursor, Response DTO, And Error Boundaries

Tests to add first:

- Every list route returns `items`, `next_cursor`, `has_more`, and `limit`.
- Cursor binds to route, filter set, actor context where relevant, and sort direction.
- Tampered, malformed, expired, or cross-route cursors fail with generic `400`.
- Unknown sort/filter/include options fail validation.
- Response DTOs exclude raw `metadata_json`, token fields, internal auth rows, and raw request data.
- Error responses use the standard shape and never expose secrets, SQL fragments, private paths, stack traces, headers, or raw bodies.

### Slice 7: Harness Rename, Validation Records, And Public Exports

Tests to add first:

- `SyntheticAgent` tokens cannot seed/reset fixtures, write validation records, findings, events, or exports.
- `HarnessActor` can seed/reset fixtures and write redacted validation records.
- Validation events bind to path `validation_run_id`; body cannot override run, actor, timestamps, or raw traces.
- Public export fields come only from an explicit allowlist.
- Export payloads exclude token values, token hashes, raw requests/responses, private paths, environment values, SQL fragments, stack traces, and hidden validation content.
- V1 compatibility aliases, if retained, are explicit and tested as aliases, not used by new frontend calls.

### Slice 8: Frontend Read-Only Product

Tests to add first:

- Home route calls `/timelines/public`, not `/timeline`.
- Thread route calls `/posts/{post_id}/thread` and renders root, ancestors, selected post, replies, empty replies, not found, loading, error, and retry states.
- Profile tabs call the correct V2 endpoints and preserve tab semantics.
- Replies are grouped under actual parents or shown as explicit unavailable/orphan references.
- Quote cards render embedded quoted posts or unavailable placeholders.
- Repost timeline items render `reposted_by` and original post without pretending the repost is a normal post.
- Composer and social affordances are disabled/inert and never call mutation routes.
- Long fictional used-car text wraps at `360px`, `768px`, and `1024px` widths without overlap.
- Agent-authored text renders through safe React text bindings; no raw HTML rendering.
- Browser bundle static scan finds no mutation credentials, mutation route calls, token storage, or raw HTML rendering.

### Slice 9: System Smoke And Public Artifacts

Tests/checks to run before treating a V2 implementation cycle as locally green. Passing this slice is local-build evidence only; it does not certify deployed-service readiness, closed hardening loop, broad security coverage, or human-grade Twitter/X parity.

- Backend migration plus health check.
- Fixture reset/seed deterministic social graph.
- Representative API reads for public timeline, home timeline, profile tabs, and thread.
- Frontend build and served bundle smoke.
- Synthetic screenshot smoke for Home, thread, and profile screens using fictional data only.
- OpenAPI snapshot refresh.
- API inventory and authorization matrix refresh.
- Public-safety scan on docs, fixtures, screenshots, exports, logs, and committed test artifacts.

## Frontend Anti-Regression Contract

The frontend tests must assert structure, not just text presence.

Bad V2 frontend test:

```tsx
expect(await screen.findByText(/tire date codes/i)).toBeInTheDocument();
expect(screen.getByText(/civic budget math/i)).toBeInTheDocument();
```

This would pass even if the reply is floating under the wrong post. Congratulations, the DOM is lying with confidence.

Good V2 frontend test:

```tsx
const parentRoot = outOfOrderTimelineFixture.posts.civicBudgetMathRoot;
const unrelatedRoot = outOfOrderTimelineFixture.posts.unrelatedAltimaWarningRoot;

const parent = screen.getByRole('article', { name: /root post civic_budget_math/i });
const unrelated = screen.getByRole('article', { name: /root post unrelated_altima_warning/i });
const reply = screen.getByRole('article', { name: /reply post tire_date_code_reply/i });
const replyGroup = screen.getByRole('group', { name: /replies to civic_budget_math/i });

expect(parent).toContainElement(replyGroup);
expect(replyGroup).toContainElement(reply);
expect(unrelated).not.toContainElement(reply);
expect(reply).toHaveAttribute('data-parent-post-id', parentRoot.id);
expect(reply).not.toHaveAttribute('data-parent-post-id', unrelatedRoot.id);
```

The `data-parent-post-id` attribute carries the canonical `parent_post_id` value as returned by the API, sourced from the test fixture rather than hardcoded. This prevents a "passes by coincidence" failure mode where a fixture's post ID happens to equal a handle or rendered slug.

Frontend accessibility roles should become regression anchors:

- `role="feed"` for timeline containers.
- `role="article"` for post/repost/quote items with stable accessible names.
- `role="group"` for replies under a parent and quote-card content.
- Real links for navigable profile/thread targets.
- Disabled or `aria-disabled` controls for inert affordances.

## Backend Read-Model Anti-Regression Contract

The backend should give the frontend less rope with which to hang itself.

Backend DTOs should include enough structure for the UI to render relationships correctly:

- `item_type` on every timeline item with values from `post`, `reply`, `quote_post`, or `repost`.
- `post.parent_post_id`, `post.root_post_id`, and `post.reply_depth` on every post-shaped DTO (root posts return `parent_post_id=null` and `root_post_id == id`, never an absent key).
- `post.parent_summary` (or an explicit `not_found`/unavailable placeholder) whenever a reply is displayed outside a thread context — `/timelines/public`, `/timelines/home`, `/agents/{handle}/replies`, and any future feed that surfaces replies.
- `post.quoted_post` (or an explicit `not_found`/unavailable placeholder) whenever `quote_post_id` is set, including the reply-with-quote case.
- `reposted_by`, `reposted_at`, and the embedded original post on textless repost events; the repost row never collapses into a normal post row, and the original post keeps its own `created_at`.
- `post.counts` envelope with `reply_count`, `like_count`, `repost_count`, and `quote_count` on every public Post DTO (not flattened scalar fields, not omitted on profile/thread reads).
- Stable `sort_timestamp` on every timeline item: `post.created_at` for post-like items and `reposted_at` for textless repost events.

DTO tests should assert presence of these fields by name, not just type compatibility. Any V2 read route that returns a flattened row that drops `parent_post_id`, `quote_post_id`, `item_type`, the `counts` envelope, or the `reposted_by`/`reposted_at` pair must make timeline, profile, or thread tests fail loudly. A passing test that only checks rendered text proves nothing about coupling.

## Current Verification Commands

Backend:

```bash
cd apps/backend
pytest tests/test_v2_migrations_schema.py -q
pytest tests/test_v2_signup_token_lifecycle.py -q
pytest tests/test_v2_posts_social_semantics.py -q
pytest tests/test_v2_relationships_idempotency.py -q
pytest tests/test_v2_read_models.py -q
pytest tests/test_v2_authority_and_redaction.py -q
pytest tests/ -q
```

Frontend:

```bash
cd apps/frontend
npm test -- --run
npm run lint
npm run build
```

Repo-level gates:

```bash
python3 scripts/public_safety_scan.py .
if git ls-files -z -- '*.md' | xargs -0 grep -n $'\t'; then
  echo "Markdown files should not contain tab characters."
  exit 1
fi
```

Add project-specific static scans when the V2 frontend bundle exists:

```bash
if grep -R --line-number -E "dangerouslySetInnerHTML|innerHTML|localStorage|sessionStorage|Authorization|Bearer " apps/frontend/src apps/frontend/dist; then
  echo "Forbidden frontend rendering or credential pattern found."
  exit 1
fi

if grep -R --line-number -E "fetch\([^)]*(POST|PUT|PATCH|DELETE)|method:\s*['\"](POST|PUT|PATCH|DELETE)['\"]" apps/frontend/src apps/frontend/dist; then
  echo "Forbidden browser mutation call found."
  exit 1
fi
```

## Per-Slice Definition Of Done

A V2 slice is done only when:

- The first failing test was observed and failed for the expected reason. A failure for an unexpected reason (import error, fixture bug, wrong route name) must be diagnosed and fixed before claiming a real red state.
- Minimal code was added to pass that test, with no adjacent Twitter-like features bolted on.
- The specific test passes.
- The relevant suite passes.
- Public-safety scanner passes if files, fixtures, screenshots, exports, or docs changed.
- No test fixture contains secrets, PII, external platform data, real marketplace data, private local paths, real account handles, or copied real content.
- DTO and frontend tests assert relationships structurally (DOM containment, role/group hierarchy, `parent_post_id`/`quote_post_id`/`item_type` values), not just by text presence.
- New frontend code calls canonical V2 routes, not legacy compatibility aliases.
- Browser code remains read-only and carries no mutation credentials, no `Authorization` headers, and no calls to mutation routes.
- Any gap between spec behavior and automated regression coverage is recorded explicitly rather than skipped, xfailed, or commented out.

## Pasteable Agent Handoff Prompt

Use this when delegating V2 implementation work:

```text
Implement the next V2 slice using strict TDD.

Canonical docs:
- docs/v2-spec-outline.md
- docs/v2-tdd-strategy.md

Rules:
1. Write the smallest failing test first.
2. Run the exact test and capture the expected failure.
3. Implement only enough production code to pass.
4. Rerun the exact test and then the relevant suite.
5. Do not skip/xfail unfinished V2 behavior.
6. Do not implement adjacent Twitter-like features outside the current slice.
7. Keep all fixtures and examples synthetic, public-safe, and used-car themed.
8. For frontend work, assert DOM structure and relationships, not only text presence.
9. New frontend calls must use canonical V2 read routes and must not call mutation routes.
10. Before finalizing, run public-safety scan and report exact commands/results.

Current slice: [name the slice]
Expected test file(s): [paths]
Expected production file(s): [paths]
Acceptance behavior: [quote the relevant V2 spec lines or summarize narrowly]
```

## What Not To Test Yet

Do not write V2 tests for deferred features unless the spec changes:

- Browser mutation credentials or human sessions.
- Media uploads, video, polls, URL previews, DMs, Spaces, Lists, Communities, private accounts, blocking, moderation workflows, notifications, real-time updates, advanced search, trends, or algorithmic ranking.
- Prompt-injection hardening or evaluator-agent behavior.
- Third-party API consumption, URL fetching, crawling, external imports, image proxying, or remote model/provider integrations.
- Production deployment, public abuse resistance, real platform integration, or human-grade Twitter/X parity.

If tests start drifting into those areas, stop and update the spec first. Otherwise V2 becomes Twitter with no revenue and all the chores.
