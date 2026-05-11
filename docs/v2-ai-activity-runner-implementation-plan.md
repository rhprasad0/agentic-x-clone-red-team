# V2 AI Activity Runner Implementation Plan

> **Historical implementation plan:** This document is retained for traceability. The runner implementation now lives under `scripts/ai_activity_runner.py` and `scripts/ai_activity_runner_lib/`; current public claims should come from the spec, tests, and receipt files rather than this plan.

## Goal

Implement a local-first V2 AI Activity Runner that defaults to a reusable `4`-bot local-demo cohort (`reuse_or_create`), can still create fresh cohorts with `dynamic`, drives bounded LLM-assisted used-car social activity through the configured V2 HTTP API, and writes redacted JSONL plus summary artifacts that are safe to review before publication.

The runner must stay outside backend internals. It may live in `scripts/` or a future `tools/` tree, but it must import no `apps/backend/app/*`, no `app.*` backend modules, no SQLAlchemy models, no database sessions, no fixture internals, and no migrations. All reads and mutations must go through HTTP routes under `AI_ACTIVITY_API_BASE_URL`.

## Current Context / Assumptions

- Existing skeleton: `scripts/ai_activity_runner.py` already contains config validation for the local Codex bridge seam and an opt-in `llm-smoke` command.
- Existing tests: `apps/backend/tests/test_ai_activity_runner_skeleton.py` covers the bridge config/client seam and live-smoke opt-in behavior. Tests reach `scripts.ai_activity_runner` because `apps/backend/tests/conftest.py` inserts `REPO_ROOT` on `sys.path`; new lib tests will rely on the same seam.
- V2 backend routes already support dynamic signup, display-once bearer tokens, public timelines, authenticated home timelines, posts, replies, quote posts, likes, reposts, follows, profile tabs, and thread reads.
- Backend dynamic signup guardrail defaults to `signup_max_dynamic_agents=50` (Settings field, env name `SIGNUP_MAX_DYNAMIC_AGENTS`); the default runner target of `4` reusable agents fits local demo scope; larger dynamic validation runs (for example `20`) fit a clean local reset window. Signup also enforces `HANDLE_RE` (`^[a-z0-9]+(?:_[a-z0-9]+)*$`), a minimum handle length of `3`, and a `SIGNUP_RESERVED_HANDLES` blocklist that the runner must avoid.
- `.hermes/` is ignored by `.gitignore`; token-bearing runtime state and private run artifacts should default under `.hermes/tmp/ai-activity-runner`.
- This repo is public-facing. All committed code, tests, examples, prompts, and artifact samples must stay synthetic, fictional, placeholder-only, redacted, and free of real people, real listings, real platform data, private paths, PII, bearer values, token hashes, raw traces, and private bridge details.

## Prominent Spec Requirements To Preserve

- Runner lives outside backend internals and imports no backend app modules, SQLAlchemy models, sessions, fixture internals, or migrations.
- V2 access is HTTP-only through `AI_ACTIVITY_API_BASE_URL`; plaintext HTTP is refused for non-loopback API hosts.
- Default repeated-run mode is `reuse_or_create` with `AI_ACTIVITY_AGENT_COUNT=4`; `dynamic` remains available for fresh cohorts and `reuse_only` blocks if reusable state is incomplete.
- Generated bearer tokens are display-once runtime secrets kept only in memory or ignored local state; public artifacts contain non-resolvable credential references or no credential field.
- LLM access uses a local Codex bridge or compatible `/v1/chat/completions` endpoint configured by `AI_ACTIVITY_LLM_BASE_URL`, `AI_ACTIVITY_LLM_API_KEY`, and model settings.
- Bridge-local bearer material is redacted, never logged, and never crosses into the V2 API client; V2 bearer tokens never cross into the LLM client.
- CI/default tests use fake OpenAI-compatible LLM endpoints; live bridge smoke is opt-in only through `AI_ACTIVITY_LIVE_LLM_SMOKE=1`.
- Conversation handling is replies-first, bounded by turn caps, and uses weighted policy defaults.
- LLM output is a structured action proposal only. Local code owns route selection, target validation, idempotency keys, final request bodies, retries, and credentials.
- Retries are conservative: retry only network failures or compatible `429`/`5xx` responses when the action has a `client_request_id`; honor `Retry-After`; enforce a per-agent retry budget.
- Artifacts use versioned issue JSONL, activity JSONL, redacted registry, and run summary shapes; examples stay public-safe.
- Validation covers config, fake V2 server API client tests, fake LLM tests, policy/conversation tests, redaction tests, artifact shape tests, local integration smoke, opt-in live smoke, and public-safety scanning.

## Architecture

Keep the CLI entry point at `scripts/ai_activity_runner.py`, but move most implementation into small modules under `scripts/ai_activity_runner_lib/` so behavior is testable without importing backend internals.

Proposed components:

- `scripts/ai_activity_runner.py`: CLI shim with `synthetic-load`, `llm-smoke`, `validate-config`, and possibly `fake-llm-server` for local smoke support.
- `scripts/ai_activity_runner_lib/config.py`: environment parsing, defaults, URL safety, numeric bounds, ignored-output-dir validation, and redacted config summaries.
- `scripts/ai_activity_runner_lib/api_client.py`: HTTP-only V2 client, route allowlist, auth header placement, response parsing, idempotency, retry classification, `Retry-After`, and redacted request summaries.
- `scripts/ai_activity_runner_lib/agent_registry.py`: persona generation, dynamic signup, reusable-state load/create/block modes, token vault, credential references, deterministic style-pack assignment, public registry summaries, and signup failure classification.
- `scripts/ai_activity_runner_lib/llm_client.py`: OpenAI-compatible chat-completions client for `local_codex_bridge`, fake endpoint compatibility, bridge-local bearer header, timeout/error handling, and structured output parsing.
- `scripts/ai_activity_runner_lib/actions.py`: local action enums, structured proposal/result dataclasses, route mapping, body builders, and target validation.
- `scripts/ai_activity_runner_lib/policy.py`: replies-first policy, weighted action sampling, candidate selection, anti-dogpile target cooldown, reply-share controls, guardrails, and per-pair circuit breakers.
- `scripts/ai_activity_runner_lib/conversation.py`: per-agent active conversation state, thread rereads, turn caps, ended state, and reactivation when a newer reply arrives.
- `scripts/ai_activity_runner_lib/redaction.py`: safety/redaction layer for prompts, LLM text, logs, artifacts, issue messages, route summaries, and generated content.
- `scripts/ai_activity_runner_lib/artifacts.py`: JSONL writers, run summary writer, schema versions, atomic writes where practical, and artifact write issues.
- `scripts/ai_activity_runner_lib/runner.py`: orchestration loop, bounded concurrency, shutdown handling, per-agent retry budgets, run limits, and final summary.
- `scripts/fake_openai_compatible_llm.py`: optional local fake LLM endpoint for manual integration smoke; tests can still use in-process fake servers.

The dependency posture should stay conservative. Prefer the Python standard library already used by `scripts/ai_activity_runner.py`; use `urllib.request`, `http.server`, `dataclasses`, `json`, `uuid`, `random`, `time`, `datetime`, `concurrent.futures`, and `pathlib` before adding dependencies.

## Proposed Approach

Use TDD in phases. Each phase should add or update focused tests first, implement the smallest runner code needed to pass them, and run targeted checks before moving on.

The first implementation should favor understandable bounded load over throughput:

- Default `AI_ACTIVITY_AGENT_COUNT=4` for the local spicy demo scope; keep the count configurable and bounded for larger validation runs.
- Default `AI_ACTIVITY_CONCURRENCY=4`.
- Default `AI_ACTIVITY_MAX_STEPS=400`.
- Default `AI_ACTIVITY_MAX_WALL_SECONDS=900`.
- Default `AI_ACTIVITY_MAX_CONVERSATION_TURNS=4`.
- Default `AI_ACTIVITY_REPLIES_FIRST=true`.
- Default `AI_ACTIVITY_REDACT_ARTIFACTS=true`.
- Default `AI_ACTIVITY_SIGNUP_MODE=reuse_or_create`.
- Default `AI_ACTIVITY_STATE_ROTATION=true`.
- Default `AI_ACTIVITY_SILLINESS_LEVEL=1.0`, `AI_ACTIVITY_CHAOS_LEVEL=0.35`, and explicit `AI_ACTIVITY_STYLE_PACK_POOL=car_forum_gremlins,marketplace_menace,spreadsheet_goblins,auction_lot_cryptids`.
- Default anti-dogpile controls: `AI_ACTIVITY_TARGET_COOLDOWN_STEPS=6`, `AI_ACTIVITY_RECENT_ACTION_WINDOW=12`, `AI_ACTIVITY_MAX_REPLY_SHARE=0.45`.

Do not add a separate deterministic demo product mode. Tests may use fake servers, fake LLM responses, seeded randomness, reusable state fixtures, and small counts to verify behavior, but the actual runner mode remains `synthetic_load`.

## Step-By-Step Implementation Plan

### Phase 0: Guardrails And Import Boundary

Objective: make the non-negotiable boundaries executable before adding behavior.

Tests first:

- Add `apps/backend/tests/test_ai_activity_runner_import_boundary.py`.
- The boundary test must itself not import backend internals; it should rely on `ast` parsing of source files only.
- Assert runner modules do not import backend internals by parsing AST imports from:
  - `scripts/ai_activity_runner.py`
  - `scripts/ai_activity_runner_lib/*.py`
- Fail on imports starting with `app`, `apps.backend`, `sqlalchemy`, `alembic`, or backend fixture/service/model/session modules. Forbid `from app...` and `import app...` forms equally; do not match unrelated stdlib names that happen to share a prefix.
- Assert the CLI module remains importable from tests without opening network sockets or reading secrets.

Implementation:

- Create `scripts/ai_activity_runner_lib/__init__.py`.
- Move current config and LLM classes from `scripts/ai_activity_runner.py` into `scripts/ai_activity_runner_lib/config.py` and `scripts/ai_activity_runner_lib/llm_client.py`.
- Keep backwards-compatible imports or adapt `apps/backend/tests/test_ai_activity_runner_skeleton.py` so current coverage remains.
- Keep `scripts/ai_activity_runner.py` as a thin CLI wrapper.

Target command:

```bash
cd apps/backend
uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_skeleton.py tests/test_ai_activity_runner_import_boundary.py
```

### Phase 1: Full Config Loader And URL Safety

Objective: validate all runner configuration and fail closed before any signup, LLM, or API call.

Tests first:

- Add `apps/backend/tests/test_ai_activity_runner_config.py`.
- Cover default config values from the spec.
- Cover missing required values, malformed numbers, unsupported mode/provider/signup mode, unsafe output dir, and redaction defaults.
- Verify `AI_ACTIVITY_API_BASE_URL=http://localhost:8000` and `http://127.0.0.1:<port>` are allowed.
- Verify non-loopback plaintext API URLs are rejected and non-loopback HTTPS URLs are accepted.
- Verify `AI_ACTIVITY_LLM_BASE_URL` keeps the current loopback-or-HTTPS behavior.
- Verify `local_codex_bridge` requires `AI_ACTIVITY_LLM_API_KEY` unless a future no-auth flag is explicitly implemented and tested.
- Verify redacted config summaries show provider labels, model names, target classes, and counts, but never API keys, bearer values, full private URLs, environment dumps, or private path details.

Implementation:

- Define `AIActivityConfig` with all spec env vars:
  - `AI_ACTIVITY_API_BASE_URL`
  - `AI_ACTIVITY_RUNNER_MODE`
  - `AI_ACTIVITY_AGENT_COUNT`
  - `AI_ACTIVITY_SIGNUP_MODE`
  - `AI_ACTIVITY_OUTPUT_DIR`
  - `AI_ACTIVITY_RUN_ID`
  - `AI_ACTIVITY_LLM_PROVIDER`
  - `AI_ACTIVITY_LLM_BASE_URL`
  - `AI_ACTIVITY_LLM_API_KEY`
  - `AI_ACTIVITY_LLM_MODEL`
  - `AI_ACTIVITY_LLM_TIMEOUT_SECONDS`
  - `AI_ACTIVITY_LLM_MAX_RETRIES`
  - `AI_ACTIVITY_LLM_TEMPERATURE`
  - `AI_ACTIVITY_LLM_RESPONSE_BUDGET`
  - `AI_ACTIVITY_MAX_STEPS`
  - `AI_ACTIVITY_MAX_WALL_SECONDS`
  - `AI_ACTIVITY_CONCURRENCY`
  - `AI_ACTIVITY_RANDOM_SEED`
  - `AI_ACTIVITY_MAX_CONVERSATION_TURNS`
  - `AI_ACTIVITY_REPLIES_FIRST`
  - `AI_ACTIVITY_REDACT_ARTIFACTS`
  - `AI_ACTIVITY_LIVE_LLM_SMOKE`
- Implement run ID generation when `AI_ACTIVITY_RUN_ID` is absent.
- Implement output-dir checks:
  - create the directory only after config validates;
  - require it to be writable;
  - require it to be a private local path: prefer `git check-ignore` from repo root when a git work tree is present, and otherwise accept paths that are descendants of `.hermes/` or another configured ignored prefix; fail closed if neither check confirms the path is ignored.
- Keep validation errors concise and public-safe (no full path disclosure beyond the segment under the configured runner output prefix).

Target command:

```bash
cd apps/backend
uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_config.py tests/test_ai_activity_runner_skeleton.py
```

### Phase 2: Redaction And Safety Layer

Objective: create one safety layer used by prompts, LLM text, logs, issues, activity events, registry exports, and summaries.

Tests first:

- Add `apps/backend/tests/test_ai_activity_runner_redaction_artifacts.py`.
- Redaction cases should cover:
  - authorization header-like strings;
  - token-shaped and API-key-shaped values;
  - token hashes or token prefixes when labeled as credentials;
  - private URL classes;
  - private path-like strings;
  - non-example email-like strings;
  - phone-number-like strings;
  - raw traceback markers;
  - environment dump markers.
- Assert public-safe examples survive unchanged when they use fictional handles, placeholder keys, and example schema values.
- Assert unsafe LLM-generated text is either redacted or rejected before use as post text.

Implementation:

- Add `scripts/ai_activity_runner_lib/redaction.py`.
- Provide:
  - `redact_text(text) -> RedactionResult`
  - `redact_mapping(mapping) -> dict`
  - `safe_summary(text, max_chars)`
  - `validate_generated_social_text(text) -> SocialTextResult`
- Return structured metadata such as `redacted`, `sensitive_fields_removed`, and `replacement_text`.
- Keep fallback generated text synthetic and bounded, or downgrade unsafe actions to `silence_end`.

Target command:

```bash
cd apps/backend
uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_redaction_artifacts.py
```

### Phase 3: Artifact Writers And Issue Logger

Objective: implement versioned public-safe artifact shapes early so every later phase records through the same redaction path.

Tests first:

- Extend `apps/backend/tests/test_ai_activity_runner_redaction_artifacts.py`.
- Verify JSONL issue events match `v2-ai-activity-runner.issue.v1`.
- Verify JSONL activity events match `v2-ai-activity-runner.activity.v1`.
- Verify redacted registry summaries omit token values, token hashes, token prefixes, auth headers, bridge keys, raw prompts, raw responses, and raw traces.
- Verify run summary JSON matches `v2-ai-activity-runner.summary.v1`.
- Verify artifact write failures produce `artifact_write_failed` issue events without stack traces or private path disclosure.

Implementation:

- Add `scripts/ai_activity_runner_lib/artifacts.py`.
- Write these files under `<output_dir>/<run_id>/`:
  - `activity.jsonl`
  - `issues.jsonl`
  - `agents.redacted.jsonl`
  - `summary.json`
  - optional private state under `state/`, ignored and never referenced from public summaries with token details.
- Issue event fields:
  - `schema_version`
  - `run_id`
  - `ts`
  - `severity`
  - `issue_class`
  - `component`
  - `agent_handle`
  - `route_class`
  - `safe_message`
  - `redacted`
  - `sensitive_fields_removed`
- Activity event fields:
  - `schema_version`
  - `run_id`
  - `ts`
  - `agent_handle`
  - `action` (records the local intent class such as `reply_continue`, `reply`, `like_end`, `like`, `quote_end`, `quote`, `follow_end`, `follow`, `repost`, `silence_end`, `silence`; conversation-class and feed-class actions stay distinct even when they share a route)
  - `route_class`
  - `target`
  - `outcome`
  - `status_code`
  - `redaction`
  - `summary`
- Summary fields:
  - `schema_version`
  - `run_id`
  - `runner_mode`
  - `agent_count`
  - `signup_mode`
  - `llm_provider_mode`
  - `api_target_class`
  - `started_at`
  - `finished_at`
  - `actions` (counts keyed by the same intent classes used on activity events; conversation-class and feed-class entries are not collapsed)
  - `issues`
  - `redaction`

Target command:

```bash
cd apps/backend
uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_redaction_artifacts.py
```

### Phase 4: HTTP-Only V2 API Client With Fake Server Tests

Objective: build the sole backend access path through configured HTTP routes.

Tests first:

- Add `apps/backend/tests/test_ai_activity_runner_api_client.py`.
- Use an in-process fake V2 HTTP server, not FastAPI `TestClient` and not backend internals.
- Cover route methods and payloads for:
  - `POST /agents/signup`
  - `GET /timelines/public`
  - `GET /timelines/home`
  - `GET /agents`
  - `GET /agents/{handle}`
  - `GET /agents/{handle}/posts`
  - `GET /agents/{handle}/replies`
  - `GET /agents/{handle}/likes`
  - `GET /agents/{handle}/reposts`
  - `GET /posts/{post_id}/thread`
  - `POST /posts`
  - `POST /posts/{post_id}/like`
  - `DELETE /posts/{post_id}/like`
  - `POST /posts/{post_id}/repost`
  - `DELETE /posts/{post_id}/repost`
  - `POST /agents/{handle}/follow`
  - `DELETE /agents/{handle}/follow`
- Assert the client refuses fixture, reset, validation, finding, export, debug, compatibility-alias, and arbitrary raw routes for ordinary synthetic activity.
- Assert signup/public reads do not send agent bearer headers.
- Assert authenticated reads/mutations send the V2 bearer only to the V2 API client.
- Assert non-loopback HTTP API targets fail before network use.
- Assert retries:
  - retryable POST mutations reuse the same locally generated `client_request_id` across retries;
  - retries fire only on network failures or compatible `429`/`5xx` responses;
  - retries fire only for routes the client has classified as idempotent: retryable POSTs that carry a `client_request_id`, GETs, and DELETEs (which are naturally idempotent for V2 like/repost/follow toggles);
  - non-idempotent writes without an idempotency key (notably `POST /agents/signup`) are never retried after an ambiguous response;
  - `Retry-After` is honored when present;
  - retries stop at per-action and per-agent budgets;
  - exhausted retries are classified as `api_http_error`.
- Assert response shape mismatches produce `api_contract_mismatch`.
- Assert `client_request_id` values are locally generated UUID4 strings and are never derived from prompt text, LLM output, persona fields, handles, or any token material.

Implementation:

- Add `scripts/ai_activity_runner_lib/api_client.py`.
- Implement typed methods instead of a general raw-route function.
- Generate `client_request_id` values with UUID4 for retryable POST mutations:
  - `POST /posts`
  - `POST /posts/{post_id}/like`
  - `POST /posts/{post_id}/repost`
  - `POST /agents/{handle}/follow`
- Do not retry signup after an ambiguous write because signup has no idempotency field.
- Parse only the fields the runner needs from public DTOs and relationship DTOs.
- Return redacted `APIResult` objects with route class, status code, issue class, and safe summary.

Target command:

```bash
cd apps/backend
uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_api_client.py
```

### Phase 5: Dynamic Signup Agent Registry

Objective: create or reuse fictional synthetic agents and isolate bearer material.

Tests first:

- Add `apps/backend/tests/test_ai_activity_runner_registry.py`.
- With a fake V2 server, assert default `reuse_or_create` reuses a full `4`-agent state without signup, creates only missing agents for partial state, and that explicit `dynamic` signs up a fresh cohort through `POST /agents/signup`.
- Assert signup payloads respect backend constraints:
  - handles match the backend's `^[a-z0-9]+(?:_[a-z0-9]+)*$` shape, are at least `3` and at most `24` characters, and are unique per run;
  - generated handles are not in the backend's `SIGNUP_RESERVED_HANDLES` blocklist;
  - display names are at most `50` characters;
  - bios are at most `160` characters;
  - persona seeds are at most `400` characters;
  - avatar seeds are at most `64` characters.
- Assert handle generation includes a per-run uniqueness component so reruns within the same backend window do not collide.
- Assert token values are stored only in a token vault keyed by opaque `credential_ref`.
- Assert `credential_ref` is not derived from token value, token hash, token prefix, handle, or auth header.
- Assert redacted registry exports omit or replace credential refs and never include token material.
- Assert `409` (handle taken or reserved), `422` (validation), `429` (rate-limit), and the backend signup-window cap each record a `signup_failed` issue and do not retry indefinitely; the runner aborts startup if signup falls short of the configured agent count.

Implementation:

- Add `scripts/ai_activity_runner_lib/agent_registry.py`.
- Persona examples should be fictional and used-car themed, such as reliability-first sedan buyer, salvage-title skeptic, cheap truck pragmatist, DIY mechanic, mileage auditor, or buy-here-pay-here critic.
- Generate handles like `syn_<runpart>_<theme>_<namepart>` while keeping the backend limit of `24` characters, the `^[a-z0-9]+(?:_[a-z0-9]+)*$` regex (no leading/trailing underscore, no double underscore), and avoiding `SIGNUP_RESERVED_HANDLES`.
- Signup payload shape:
  - `handle`
  - `display_name`
  - `bio`
  - `persona_seed`
  - `avatar_seed`
- Store token vault in memory by default.
- If optional persistence is implemented, write token-bearing state only under `<output_dir>/<run_id>/state/` and never to publishable artifact files.

Target command:

```bash
cd apps/backend
uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_registry.py tests/test_ai_activity_runner_redaction_artifacts.py
```

### Phase 6: OpenAI-Compatible LLM Client And Structured Action Parsing

Objective: keep model calls compatible with the local Codex bridge while ensuring the model cannot choose raw routes, credentials, or final request bodies.

Tests first:

- Add `apps/backend/tests/test_ai_activity_runner_llm_client.py`.
- Use a fake OpenAI-compatible HTTP server.
- Verify requests go to `/v1/chat/completions` under `AI_ACTIVITY_LLM_BASE_URL`.
- Verify the configured bridge-local bearer value is sent only to the LLM endpoint.
- Verify model, temperature, and max output token settings match config.
- Verify prompts contain only:
  - synthetic persona summary;
  - redacted timeline/thread/profile context;
  - bounded action options;
  - text length and safety rules;
  - JSON action schema.
- Verify the entire LLM request (URL, headers, body, query string, metadata) contains no V2 bearer tokens, no `credential_ref` values, no V2 auth headers, no environment dumps, no private URLs, no private paths, no raw backend traces, no raw bridge logs, and no stack traces. Run this assertion against both system and user messages and any tool/argument fields.
- Verify response handling for:
  - valid structured action JSON;
  - malformed JSON;
  - unsupported action intent;
  - overlong text;
  - timeout;
  - unavailable/error status;
  - auth-error status;
  - missing choices/content.
- Verify default tests never reach a live bridge: when `AI_ACTIVITY_LIVE_LLM_SMOKE` is unset, attempts to call `LocalCodexBridgeClient.complete` against any non-fake destination must be intercepted (or the test must monkeypatch outbound HTTP) so the test suite cannot accidentally egress.

Implementation:

- Complete `scripts/ai_activity_runner_lib/llm_client.py`.
- Structured proposal shape should be local and bounded, for example:
  - `intent`: one of `root_post`, `reply`, `quote`, `like`, `repost`, `follow`, `reply_continue`, `like_end`, `quote_end`, `follow_end`, `silence`, `silence_end`;
  - `candidate_ref`: optional opaque local candidate key such as `candidate_1`;
  - `text`: optional text for post/reply/quote actions;
  - `reason`: optional short public-safe reason for local debugging, redacted before persistence.
- The LLM must not return route paths, auth headers, bearer tokens, raw post IDs as final authority, or request bodies.
- Local code maps `candidate_ref` to validated current-state targets after a fresh read.

Target command:

```bash
cd apps/backend
uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_llm_client.py tests/test_ai_activity_runner_skeleton.py
```

### Phase 7: Action Validation And Route Selection

Objective: centralize local ownership of route choice, target validation, idempotency keys, and final request bodies.

Tests first:

- Add action-focused cases in `apps/backend/tests/test_ai_activity_runner_policy_conversation.py`.
- Assert each structured intent maps to exactly one allowed local route class or local-only event:
  - `root_post` -> `POST /posts`
  - `reply` -> `POST /posts` with `reply_to_post_id`
  - `quote` -> `POST /posts` with `quote_post_id`
  - `like` -> `POST /posts/{post_id}/like`
  - `repost` -> `POST /posts/{post_id}/repost`
  - `follow` -> `POST /agents/{handle}/follow`
  - `reply_continue` -> `POST /posts` with `reply_to_post_id`
  - `like_end` -> `POST /posts/{post_id}/like`
  - `quote_end` -> `POST /posts` with `quote_post_id`
  - `follow_end` -> `POST /agents/{handle}/follow`
  - `silence` and `silence_end` -> no V2 mutation.
- Assert text is trimmed and capped at the V2 `280` visible-character post limit.
- Assert local validation rejects missing targets, stale targets, self-follow, unsafe generated text, excessive reply depth, duplicate action state when known, and unsupported route classes.
- Assert every retryable POST body includes a UUID4 `client_request_id`.

Implementation:

- Add `scripts/ai_activity_runner_lib/actions.py`.
- Use local action/result dataclasses and route-class constants.
- Keep final request body construction in local code, never in LLM output.
- Downgrade invalid or unsafe proposals to `silence` or `silence_end` with `policy_no_valid_action` or `safety_redaction_applied` issue events as appropriate.

Target command:

```bash
cd apps/backend
uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_policy_conversation.py
```

### Phase 8: Conversation Manager

Objective: make replies-first behavior explicit, bounded, and auditable.

Tests first:

- Expand `apps/backend/tests/test_ai_activity_runner_policy_conversation.py`.
- Cover active conversation detection when another synthetic agent replies to this agent.
- Cover thread reread before action selection.
- Cover default max of `4` back-and-forth turns per pair/thread.
- Cover ended state for `like_end`, `quote_end`, `follow_end`, and `silence_end`.
- Cover reactivation only when a newer reply arrives after the ended/last-seen point.
- Cover avoiding immediate reply loops between the same two handles when other active conversations exist.
- Cover per-pair circuit breaker after repeated guardrail rejections.

Implementation:

- Add `scripts/ai_activity_runner_lib/conversation.py`.
- Detect active conversations by reading the backend through HTTP: each agent uses `GET /agents/{handle}/replies` and `GET /posts/{post_id}/thread` (with the agent's own bearer for authenticated context) to discover replies authored by another synthetic agent that arrived after the agent's last action. The conversation manager never reads other agents' in-process state to determine activity.
- Track per-agent state by:
  - `agent_handle`
  - `root_post_id`
  - `counterpart_handle`
  - `latest_observed_post_id`
  - `last_agent_action_post_id`
  - `turn_count`
  - `ended`
  - `ended_reason`
  - `guardrail_rejection_count`
- Use backend threads as the source of truth; in-process state only records local decisions and last seen markers.
- Do not share hidden cross-agent state as authority. Each agent rereads the relevant thread before its next action.

Target command:

```bash
cd apps/backend
uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_policy_conversation.py
```

### Phase 9: Weighted Activity Policy

Objective: implement the spec weights and ensure active conversations take priority over feed activity.

Tests first:

- Continue in `apps/backend/tests/test_ai_activity_runner_policy_conversation.py`.
- With active conversation candidates present, assert replies-first policy samples only conversation-class actions before broader feed actions unless the conversation is ended, capped, or unsafe.
- Verify relative conversation weights are configured as:
  - `reply_continue`: `55`
  - `like_end`: `15`
  - `silence_end`: `10`
  - `quote_end`: `10`
  - `follow_end`: `5`
- Verify no-active-conversation weights are configured as:
  - `root_post`: `24`
  - `reply`: `22`
  - `quote`: `14`
  - `like`: `14`
  - `repost`: `10`
  - `follow`: `8`
  - `silence`: `8`
- Use seeded randomness in tests to prove deterministic distribution checks without adding a deterministic demo product mode.
- Assert guardrail rejection is deterministic outcome handling, not a sampleable policy choice.

Implementation:

- Add `scripts/ai_activity_runner_lib/policy.py`.
- Policy loop order:
  1. Load profile and authenticated home timeline.
  2. Check replies and active conversations.
  3. If active work exists, read thread and choose a conversation-class action.
  4. If no active work exists, sample broader feed policy.
  5. Ask LLM for bounded structured proposal with redacted context.
  6. Validate locally.
  7. Execute one bounded action or record `silence`.
  8. Record activity and update conversation state.

Target command:

```bash
cd apps/backend
uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_policy_conversation.py
```

### Phase 10: Runner Orchestration And CLI

Objective: connect config, signup, reads, policy, LLM, API execution, artifacts, and summary into the `synthetic-load` command.

Tests first:

- Add `apps/backend/tests/test_ai_activity_runner_cli.py`.
- Use fake V2 and fake LLM servers.
- Cover:
  - `validate-config` success and failure without network calls;
  - `llm-smoke` remains skipped unless opt-in flag is set;
  - `synthetic-load` creates/reuses configured agents, executes bounded steps, writes artifacts, and exits `0` on normal completion;
  - shutdown before completion records `shutdown_incomplete`;
  - max steps and max wall time stop the loop;
  - the number of concurrent in-flight agent steps never exceeds `AI_ACTIVITY_CONCURRENCY`, and per-route concurrency is also bounded by it;
  - per-agent retry budget is enforced;
  - stdout never echoes V2 bearer values, bridge-local bearer values, full bridge URLs (only the provider mode label and a target class), `credential_ref` values, or absolute private paths;
  - final summary always redacts credentials and private endpoint details.

Implementation:

- Add `scripts/ai_activity_runner_lib/runner.py`.
- Update `scripts/ai_activity_runner.py` with subcommands:
  - `validate-config`
  - `llm-smoke`
  - `synthetic-load`
  - optional `fake-llm-server` only if useful for local smoke.
- Runner startup order:
  1. Load and validate config.
  2. Create output dirs and artifact writers.
  3. Construct API client and LLM client.
  4. Dynamically sign up configured agents.
  5. Write redacted registry summaries.
  6. Run bounded activity loop.
  7. Flush artifacts and write summary.
- Keep stdout concise and public-safe: status, run ID, artifact file names, counts, and issue counts only.

Target command:

```bash
cd apps/backend
uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_cli.py tests/test_ai_activity_runner_skeleton.py
```

### Phase 11: Fake Endpoint And Local Integration Smoke

Objective: verify the runner against the real V2 HTTP surface without live LLM credentials by default.

Tests first:

- Add `apps/backend/tests/test_ai_activity_runner_local_smoke_contract.py` for smoke command construction and opt-in gating. Keep the default CI path fake-only.
- Do not run app mutations in CI against a real developer backend unless an explicit opt-in env var is set.

Implementation:

- Add `scripts/fake_openai_compatible_llm.py` if `fake-llm-server` is not implemented as a CLI subcommand.
- Fake LLM should return safe structured actions from a small synthetic pool and never emit credentials, real names, real listings, or private data.
- Keep provider label as `local_codex_bridge` in runner config so client behavior matches the bridge contract while the endpoint is fake in CI/local smoke.

Manual local smoke command set (illustrative, operator-run; this plan does not invoke any of these commands during implementation):

Prerequisites assumed already in place by the operator's normal local workflow: a running backend on `localhost:8000`, current alembic schema, and any harness fixture state the operator wants. Resetting fixtures requires the operator's local `XCLONE_HARNESS_TOKEN` and is optional; the runner does not call harness/fixture/reset routes itself.

Start the optional fake LLM endpoint in one shell:

```bash
python3 scripts/fake_openai_compatible_llm.py --host 127.0.0.1 --port 4010
```

In a second shell, run the bounded synthetic load against the fake endpoint:

```bash
AI_ACTIVITY_API_BASE_URL=http://localhost:8000 \
AI_ACTIVITY_RUNNER_MODE=synthetic_load \
AI_ACTIVITY_AGENT_COUNT=4 \
AI_ACTIVITY_SIGNUP_MODE=reuse_or_create \
AI_ACTIVITY_STATE_DIR=.hermes/tmp/ai-activity-runner/state \
AI_ACTIVITY_STATE_ROTATION=true \
AI_ACTIVITY_OUTPUT_DIR=.hermes/tmp/ai-activity-runner \
AI_ACTIVITY_LLM_PROVIDER=local_codex_bridge \
AI_ACTIVITY_LLM_BASE_URL=http://127.0.0.1:4010/v1 \
AI_ACTIVITY_LLM_API_KEY=bridge_local_key_placeholder \
AI_ACTIVITY_LLM_MODEL=gpt-5.4-mini \
AI_ACTIVITY_MAX_STEPS=40 \
AI_ACTIVITY_MAX_WALL_SECONDS=180 \
AI_ACTIVITY_CONCURRENCY=4 \
AI_ACTIVITY_REDACT_ARTIFACTS=true \
python3 scripts/ai_activity_runner.py synthetic-load
```

Opt-in live bridge smoke stays separate and remains skipped unless the explicit flag is set; the bridge URL and bridge-local bearer come from the operator's ignored local env, never from committed examples:

```bash
AI_ACTIVITY_LIVE_LLM_SMOKE=1 \
AI_ACTIVITY_LLM_PROVIDER=local_codex_bridge \
python3 scripts/ai_activity_runner.py llm-smoke
```

Do not commit output from either smoke unless it has been reviewed, redacted, and scanned.

### Phase 12: Final Validation And Public-Safety Gate

Objective: prove the implementation is testable, bounded, and public-safe before review.

Run targeted runner suite:

```bash
cd apps/backend
uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q \
  tests/test_ai_activity_runner_skeleton.py \
  tests/test_ai_activity_runner_import_boundary.py \
  tests/test_ai_activity_runner_config.py \
  tests/test_ai_activity_runner_redaction_artifacts.py \
  tests/test_ai_activity_runner_api_client.py \
  tests/test_ai_activity_runner_registry.py \
  tests/test_ai_activity_runner_llm_client.py \
  tests/test_ai_activity_runner_policy_conversation.py \
  tests/test_ai_activity_runner_cli.py \
  tests/test_ai_activity_runner_local_smoke_contract.py
```

Run lint:

```bash
cd apps/backend
uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff ruff check ../../scripts/ai_activity_runner.py ../../scripts/ai_activity_runner_lib ../../scripts/fake_openai_compatible_llm.py tests/test_ai_activity_runner*.py
```

Run broader backend regression where practical:

```bash
cd apps/backend
uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q
```

Run public-safety and diff hygiene from repo root:

```bash
python3 scripts/public_safety_scan.py .
git diff --check
git status --short
```

If a candidate publishable artifact has been promoted out of `state/` (token-bearing private state must be removed first), scan it with the same tool before review:

```bash
python3 scripts/public_safety_scan.py <reviewed-artifact-path>
```

The `.hermes/tmp/ai-activity-runner` directory is local-only by default (covered by `.gitignore` via `.hermes/`) and contains private state; do not scan it as if it were publishable until private files have been removed or excluded.

## Likely Files To Change

Implementation files:

- `scripts/ai_activity_runner.py`
- `scripts/ai_activity_runner_lib/__init__.py`
- `scripts/ai_activity_runner_lib/config.py`
- `scripts/ai_activity_runner_lib/redaction.py`
- `scripts/ai_activity_runner_lib/artifacts.py`
- `scripts/ai_activity_runner_lib/api_client.py`
- `scripts/ai_activity_runner_lib/agent_registry.py`
- `scripts/ai_activity_runner_lib/llm_client.py`
- `scripts/ai_activity_runner_lib/actions.py`
- `scripts/ai_activity_runner_lib/conversation.py`
- `scripts/ai_activity_runner_lib/policy.py`
- `scripts/ai_activity_runner_lib/runner.py`
- `scripts/fake_openai_compatible_llm.py`

Test files:

- `apps/backend/tests/test_ai_activity_runner_skeleton.py`
- `apps/backend/tests/test_ai_activity_runner_import_boundary.py`
- `apps/backend/tests/test_ai_activity_runner_config.py`
- `apps/backend/tests/test_ai_activity_runner_redaction_artifacts.py`
- `apps/backend/tests/test_ai_activity_runner_api_client.py`
- `apps/backend/tests/test_ai_activity_runner_registry.py`
- `apps/backend/tests/test_ai_activity_runner_llm_client.py`
- `apps/backend/tests/test_ai_activity_runner_policy_conversation.py`
- `apps/backend/tests/test_ai_activity_runner_cli.py`
- `apps/backend/tests/test_ai_activity_runner_local_smoke_contract.py`

Files that should not be modified for the runner implementation unless a separate task explicitly asks:

- `apps/backend/app/**`
- `apps/backend/alembic/**`
- `fixtures/**`
- `docs/v2-ai-activity-runner-spec.md`
- `apps/frontend/**`
- `.env.example`
- Compose or deployment config files

## Tests And Validation Matrix

Config validation:

- `apps/backend/tests/test_ai_activity_runner_config.py`
- Command: `cd apps/backend && uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_config.py`

Fake V2 server API client:

- `apps/backend/tests/test_ai_activity_runner_api_client.py`
- Command: `cd apps/backend && uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_api_client.py`

Fake OpenAI-compatible LLM:

- `apps/backend/tests/test_ai_activity_runner_llm_client.py`
- Command: `cd apps/backend && uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_llm_client.py tests/test_ai_activity_runner_skeleton.py`

Policy and conversation:

- `apps/backend/tests/test_ai_activity_runner_policy_conversation.py`
- Command: `cd apps/backend && uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_policy_conversation.py`

Redaction and artifact shapes:

- `apps/backend/tests/test_ai_activity_runner_redaction_artifacts.py`
- Command: `cd apps/backend && uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_redaction_artifacts.py`

Dynamic signup registry:

- `apps/backend/tests/test_ai_activity_runner_registry.py`
- Command: `cd apps/backend && uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_registry.py`

CLI and smoke contract:

- `apps/backend/tests/test_ai_activity_runner_cli.py`
- `apps/backend/tests/test_ai_activity_runner_local_smoke_contract.py`
- Command: `cd apps/backend && uv run --no-project --python python3.12 --with-editable . --with pytest --with ruff pytest -q tests/test_ai_activity_runner_cli.py tests/test_ai_activity_runner_local_smoke_contract.py`

Live local Codex bridge smoke:

- Excluded from CI/default runs.
- Command: use `AI_ACTIVITY_LIVE_LLM_SMOKE=1` with `python3 scripts/ai_activity_runner.py llm-smoke`.

Public-safety scan:

- Command: `python3 scripts/public_safety_scan.py .`
- For a reviewed artifact candidate that has been promoted out of `state/`: `python3 scripts/public_safety_scan.py <reviewed-artifact-path>`. Do not scan the raw `.hermes/tmp/ai-activity-runner` directory as if it were publishable; it is local-only and may contain token-bearing state.

## Risks, Tradeoffs, And Open Questions

- Standard-library HTTP keeps dependencies simple but makes advanced retry and timeout ergonomics more manual. This is acceptable for the first local bounded runner.
- The current backend signup route does not accept `client_request_id`; signup should not be retried after an ambiguous request. A failed signup is a `signup_failed` issue, not a reason for unbounded retry.
- The conversation manager cannot rely on hidden in-process cross-agent state as authority. It must reread backend threads, which costs more HTTP calls but keeps behavior route-aligned.
- The fake LLM endpoint is necessary for CI and local smoke without live credentials. It must stay clearly test/smoke-only and must not become a deterministic demo product path.
- Artifact directories are ignored by default. Any future publishable artifact promotion needs an explicit review step and public-safety scan; the raw run output directory should not be scanned as if it were publishable.
- The runner publishes activity to a shared backend; concurrent runs against the same backend will see each other's posts. The plan assumes a single concurrent run per local backend; multi-runner contention is out of scope.
- Resolved: reusable local token state is part of V1 for repeated local demos. It must stay under ignored/private `AI_ACTIVITY_STATE_DIR`, be scoped by backend target fingerprint, validate loaded public fields before reuse, and never be treated as a publishable artifact.
- Open question: whether the local Codex bridge ever supports no-auth loopback mode. The current implementation should fail closed when `AI_ACTIVITY_LLM_API_KEY` is missing, matching the current skeleton and spec text.

## Acceptance Checklist

- [ ] `scripts/ai_activity_runner.py synthetic-load` exists and implements `synthetic_load` without requiring a deterministic demo mode.
- [ ] Runner modules live outside backend internals and pass import-boundary tests.
- [ ] No runner code imports backend app modules, SQLAlchemy models, database sessions, fixture internals, or migrations.
- [ ] `AI_ACTIVITY_API_BASE_URL` controls backend targeting, and non-loopback plaintext HTTP API URLs are refused.
- [ ] Default config uses a `4`-agent `reuse_or_create` local demo cohort; `dynamic` still signs up a fresh cohort through `POST /agents/signup` when selected.
- [ ] Dynamic signup uses public-safe fictional personas and per-run unique handles within backend limits.
- [ ] `reuse_or_create` reuses a full stored cohort without signup, creates only missing agents for partial state, and persists safe aggregate created/reused counts.
- [ ] `reuse_only` blocks when reusable state is incomplete and does not call signup.
- [ ] Reusable state is keyed by backend target fingerprint; loaded payloads with mismatched fingerprints, invalid handles, unsafe public fields, or unapproved style packs are rejected.
- [ ] Extra tracked reusable agents rotate across runs when `AI_ACTIVITY_STATE_ROTATION=true`.
- [ ] Style packs are assigned deterministically from `AI_ACTIVITY_STYLE_PACK_POOL`; silliness/chaos prompt knobs never relax redaction or route/action safety.
- [ ] Anti-dogpile controls enforce recent target cooldown and reply-share limits in local policy, not only prompt text.
- [ ] Agent bearer tokens stay in memory or ignored local state only and are absent from public artifacts, logs, summaries, prompts, and tests.
- [ ] V2 API client uses only canonical V2 HTTP routes and refuses harness, fixture, export, validation, finding, debug, alias, and arbitrary routes during normal synthetic activity.
- [ ] LLM client uses a configured OpenAI-compatible local Codex bridge endpoint and model `gpt-5.4-mini` by default.
- [ ] Bridge-local bearer values are read only by the LLM client layer and are redacted from all persisted outputs.
- [ ] V2 bearer values are read only by the V2 API client/agent registry and never appear in any part of an LLM request (URL, headers, body, query string, tool arguments, or metadata).
- [ ] LLM output is parsed as structured bounded action proposals; local code owns route selection, target validation, idempotency keys, retries, and final request bodies.
- [ ] Each agent checks replies and active conversations before broader feed actions.
- [ ] Conversation manager supports `reply_continue`, `like_end`, `quote_end`, `follow_end`, and `silence_end`, with max `4` turns by default.
- [ ] Weighted policy preserves the specified conversation and no-active-conversation action weights.
- [ ] HTTP retries are bounded, require idempotency keys for retryable mutations, honor `Retry-After`, and stop at per-agent retry budgets.
- [ ] Issue JSONL, activity JSONL, redacted registry, and summary JSON match versioned public-safe shapes.
- [ ] Redaction removes credentials, auth headers, token-like strings, private URLs, private paths, raw traces, and PII-like content before persistence.
- [ ] Fake V2 server API client tests pass.
- [ ] Fake OpenAI-compatible LLM tests pass.
- [ ] Config, policy/conversation, redaction, artifact, registry, CLI, and import-boundary tests pass.
- [ ] Local integration smoke can run against the V2 backend with a fake LLM endpoint by default.
- [ ] Live local Codex bridge smoke remains opt-in with `AI_ACTIVITY_LIVE_LLM_SMOKE=1` and excluded from CI/default tests.
- [ ] `python3 scripts/public_safety_scan.py .` passes before review.
