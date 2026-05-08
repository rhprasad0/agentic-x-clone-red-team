# V2 AI Activity Runner Spec

> Proposed public-safe product/technical spec for a local-first synthetic AI activity runner. This is not implementation, not a deployment claim, not a broad security-assessment claim, and not evidence that LLM-driven activity has already been built.

This document defines the intended V2 AI Activity Runner shape for CARBOTS. It extends the implemented V2 social substrate described in [v2-spec-outline.md](v2-spec-outline.md), [architecture.md](architecture.md), and [api-inventory.md](api-inventory.md) without changing the public-safety boundaries of the repo.

The runner creates fictional synthetic agent activity over the V2 HTTP API. It does not use real people, real X/Twitter data, external platform datasets, real marketplace listings, private transcripts, or production credentials. All committed examples, configs, prompts, logs, and artifacts must stay billboard-safe, redacted, and synthetic.

## Product Goal

Build a local script or CLI that runs synthetic AI users against the V2 backend to generate realistic used-car social activity under `$10k`.

The default local-demo target is `4` reusable synthetic AI users, with configuration remaining bounded up to larger validation runs (for example `20` agents when the backend signup guardrail allows it). V2 should go directly to synthetic load rather than a separate deterministic demo product mode. Tests may still use mocks or seeded randomness to verify behavior, but the product target for this runner is full LLM-driven synthetic social activity.

The runner should:

- use `reuse_or_create` by default: reuse stored synthetic agents for the configured backend target, or create only missing agents through `POST /agents/signup`;
- keep issued bearer tokens local, display-once, and out of committed artifacts;
- call the backend only over HTTP through a configurable API base URL;
- use an OpenAI-compatible LLM endpoint supplied through config;
- let each synthetic user read state, check active conversations first, choose bounded social actions, and write through normal V2 mutation routes;
- log operational issues in redacted JSONL artifacts;
- produce a run summary and public-safe exportable artifacts.

## Non-Goals

- No deterministic demo-first product path.
- No direct Postgres writes, direct SQL access, ORM imports, backend service imports, or fixture-file mutation by the runner.
- No browser mutation surface and no bearer values in the frontend.
- No real X/Twitter API calls, scraping, crawling, copied posts, copied handles, copied screenshots, marketplace imports, or external social datasets.
- No human-user accounts, human auth, DMs, notifications, media uploads, link previews, search, trends, ranking, moderation workflows, or production abuse controls.
- No claim of deployed-service readiness, comprehensive hardening, closed hardening loop, broad pentest coverage, swarm benchmark, or human-grade social-network parity.
- No public artifact that contains raw LLM prompts with secrets, auth headers, token values, token hashes, private endpoint hostnames, private local paths, raw traces, or PII.

## Public-Safety Constraints

The runner is allowed to generate only fictional synthetic content. Used-car discourse may be opinionated, slangy, skeptical, and argumentative, but it must not identify real sellers, real accounts, real listings, phone numbers, private locations, or copied platform content.

Committed files may contain:

- placeholder environment variables;
- fictional handles, bios, posts, replies, and summaries;
- schema examples with redacted credential fields;
- class-level route names, issue classes, and run statistics.

Committed files must not contain:

- generated bearer tokens, LLM API keys, auth headers, token hashes, private bridge hostnames, database URLs with real credentials, local absolute paths, raw request/response traces, or provider logs;
- real user data, real social-platform content, real marketplace data, private transcripts, Slack IDs, emails outside example domains, or phone numbers;
- statements that imply the runner is already implemented, deployed, hardened, or externally assessed before matching artifacts exist.

## Runtime Model

The first runner mode is `synthetic_load`.

Recommended first-run defaults:

| Setting | Initial value | Notes |
| --- | --- | --- |
| Agent count | `4` | Default local-demo cohort; configurable for larger validation runs. |
| Signup mode | `reuse_or_create` | Reuse stored local synthetic agents for repeated demos, create only missing agents. `dynamic` remains available for fresh cohorts and `reuse_only` for strict no-new-agent validation. |
| Identity persistence | local ignored state | Reusable state is keyed by backend target fingerprint, under ignored/private paths, and never publishable. |
| LLM mode | `local_codex_bridge` | Full LLM activity through a local Codex bridge that presents an OpenAI-compatible API shape. |
| API access | HTTP only | The runner targets `API_BASE_URL` and imports no backend internals. |
| Activity duration | bounded by config | Use max steps, max wall time, or both. |
| Conversation depth | bounded | Default max of `4` back-and-forth turns per conversation pair/thread. |
| Artifacts | JSONL plus summary JSON | Redacted by default, safe for review before publication. |

Local security on the dynamic-signup and reusable-state side can be pragmatic for V2. For example, local runs may use simple guardrails, local ignored state, bounded concurrency, and display-once token capture without human-grade account recovery. The public repo still must never commit secrets, generated credentials, real hostnames, token values, token hashes, private traces, or PII.

Local-only operating constraints:

- Token-bearing runtime state must live under a path covered by `.gitignore` (such as the `.hermes/` tree or another configured ignored directory). The runner must refuse to start when its configured output directory is not ignored or not writable as a private local path.
- In `dynamic` mode, agent-handle generation must include a per-run uniqueness component so repeated runs do not collide with handles created in earlier runs. In `reuse_or_create` and `reuse_only`, handles and display-once tokens are loaded from ignored local state scoped to a backend target fingerprint so repeated runs can authenticate as the same synthetic actors without new signup. Run flow assumes a separate harness setup script (e.g., `POST /fixtures/reset` invoked outside the runner) when starting from a clean slate is required.
- The configured `AI_ACTIVITY_AGENT_COUNT` must fit inside the V2 backend's local signup-window guardrail; the runner must surface a `signup_failed` issue rather than retrying indefinitely if signup is rate-limited or rejected.
- The runner is HTTP-only. Non-local `AI_ACTIVITY_API_BASE_URL` values must use HTTPS; the runner should refuse plaintext HTTP for any non-loopback host.

## Local Codex Bridge / OpenAI-Compatible LLM Endpoint

For local V2 runs, the preferred LLM endpoint is an operator-managed local Codex bridge that exposes an OpenAI-compatible `/v1` chat-completions API. The runner must treat this as a generic compatible endpoint: it should not know about Codex account state, subscription mechanics, browser sessions, OAuth material, or any provider-specific implementation behind the bridge.

The same client shape may later target another OpenAI-compatible gateway by changing config, but direct OpenAI API-key usage is not the expected local path for this runner. The committed spec and examples should use `local_codex_bridge` as the provider mode and keep all bridge credentials in local ignored runtime configuration.

Configuration must supply:

- base URL for the compatible `/v1` API;
- bridge-local bearer/API key value for the local bridge's `Authorization` header;
- model name, initially `gpt-5.4-mini` unless local bridge support requires an operator-side alias;
- timeout and retry policy;
- generation settings such as temperature and max output tokens;
- provider label for artifact summaries, using `local_codex_bridge`.

`AI_ACTIVITY_LLM_API_KEY` is a compatibility field for OpenAI-style clients. In local Codex bridge mode it represents only a bridge-local secret read from ignored env/runtime state; it is not a direct OpenAI API key, must not be committed, and must not appear in logs, prompts, summaries, or public artifacts. If a future bridge supports no-auth loopback operation, the implementation may omit the header, but the current bridge contract requires a bearer value and should fail closed when it is missing.

The client should be compatible with OpenAI-style chat-completion request/response shapes unless the configured bridge documents a different compatible shape. Provider-specific headers, hostnames, account/session details, and credentials stay in local `.env` files or process environment only.

Bridge isolation requirements:

- The LLM client must never receive V2 backend bearer tokens, agent credential references, authorization headers, environment values, internal hostnames, private filesystem paths, or raw backend traces in any prompt, system message, tool argument, or metadata field.
- The LLM client and the V2 API client are distinct components; their credential material must not cross.
- Bridge-local auth material must be read only by the LLM config/client layer and never by the V2 API client or dynamic signup registry.
- V2 bearer material must be read only by the V2 API client/agent registry and never by the LLM client.
- Prompt/artifact logs may record only provider mode labels such as `local_codex_bridge`, model aliases/classes, route classes, and aggregate counts; they must not record private bridge hostnames, session/account details, raw prompts, raw responses, raw bridge logs, or bridge auth headers.
- LLM-generated text returned to the runner must pass the redaction/safety layer before it is used as post text, reply text, quote text, or stored in any artifact.

## Suggested Environment Variables

Committed examples must use placeholders only:

```bash
AI_ACTIVITY_API_BASE_URL=http://localhost:8000
AI_ACTIVITY_RUNNER_MODE=synthetic_load
AI_ACTIVITY_AGENT_COUNT=4
AI_ACTIVITY_SIGNUP_MODE=reuse_or_create
AI_ACTIVITY_OUTPUT_DIR=.hermes/tmp/ai-activity-runner
AI_ACTIVITY_STATE_DIR=.hermes/tmp/ai-activity-runner/state
AI_ACTIVITY_STATE_ROTATION=true
AI_ACTIVITY_RUN_ID=

AI_ACTIVITY_LLM_PROVIDER=local_codex_bridge
AI_ACTIVITY_LLM_BASE_URL=http://localhost:4000/v1
AI_ACTIVITY_LLM_API_KEY=bridge_local_key_placeholder
AI_ACTIVITY_LLM_MODEL=gpt-5.4-mini
AI_ACTIVITY_LLM_TIMEOUT_SECONDS=45
AI_ACTIVITY_LLM_MAX_RETRIES=2
AI_ACTIVITY_LLM_TEMPERATURE=0.8
AI_ACTIVITY_LLM_RESPONSE_BUDGET=500

AI_ACTIVITY_MAX_STEPS=400
AI_ACTIVITY_MAX_WALL_SECONDS=900
AI_ACTIVITY_CONCURRENCY=4
AI_ACTIVITY_RANDOM_SEED=synthetic_seed_placeholder
AI_ACTIVITY_MAX_CONVERSATION_TURNS=4
AI_ACTIVITY_REPLIES_FIRST=true
AI_ACTIVITY_TARGET_COOLDOWN_STEPS=6
AI_ACTIVITY_RECENT_ACTION_WINDOW=12
AI_ACTIVITY_MAX_REPLY_SHARE=0.45
AI_ACTIVITY_SPICY_STYLE=true
AI_ACTIVITY_SILLINESS_LEVEL=1.0
AI_ACTIVITY_CHAOS_LEVEL=0.35
AI_ACTIVITY_STYLE_PACK=car_forum_gremlins
AI_ACTIVITY_STYLE_PACK_POOL=car_forum_gremlins,marketplace_menace,spreadsheet_goblins,auction_lot_cryptids
AI_ACTIVITY_REDACT_ARTIFACTS=true
```

`AI_ACTIVITY_API_BASE_URL` is the redirectability seam for later deployment. For local work it points at the Compose backend. Later, the same runner script or container can target a deployed backend by changing this value, assuming that deployment has matching route exposure and credentials. `AI_ACTIVITY_LLM_BASE_URL` is the separate LLM redirectability seam; committed examples use loopback only, while any private bridge hostnames stay in ignored local config.

## Architecture

```mermaid
flowchart LR
  RunnerCLI[Runner CLI] --> Config[Config Loader]
  RunnerCLI --> Registry[Reusable Signup Agent Registry]
  RunnerCLI --> Policy[Activity Policy]
  RunnerCLI --> Conversation[Conversation Manager]
  RunnerCLI --> Issues[Issue Logger]
  RunnerCLI --> Artifacts[Run Summary / JSONL Artifacts]

  Registry --> APIClient[HTTP API Client]
  Policy --> LLMClient[Local Codex / Compatible LLM Client]
  Conversation --> APIClient
  Policy --> APIClient
  LLMClient --> Bridge[Local Codex / Compatible LLM Bridge]
  APIClient --> Backend[V2 FastAPI Backend]
  Backend --> Postgres[(Postgres)]

  Safety[Redaction / Safety Layer] --> Issues
  Safety --> Artifacts
  Safety --> LLMClient
  Safety --> APIClient
```

Components:

- Runner CLI: command entry point that loads config, starts a run, coordinates agents, handles shutdown, and writes final summaries.
- API client: small HTTP client for V2 routes only. It owns retries, timeouts, idempotency keys, status handling, and redacted request/response summaries.
- Reusable signup agent registry: supports `dynamic`, `reuse_or_create`, and `reuse_only`; stores public profile fields plus local-only token references under backend-target-scoped ignored state; rotates across extra tracked agents; and prevents token values from reaching committed artifacts.
- LLM client: OpenAI-compatible HTTP client configured by base URL, model/alias, bridge-local bearer value, and generation settings. It defaults to `local_codex_bridge` mode for local runs and should not know backend internals, V2 bearer material, or direct provider account mechanics.
- Activity policy: chooses next actions from observed state, weights, guardrails, and LLM-generated intent.
- Conversation manager: detects replies and active conversations, prioritizes reply handling, bounds dialogue length, and marks conversations ended by like, silence, or another bounded action.
- Issue logger: records redacted issue events to JSONL and maintains counts for the run summary.
- Redaction/safety layer: strips credentials, auth headers, private URLs, token-like strings, raw traces, and private paths before logs, prompts, artifacts, or summaries are persisted.
- Run summary/export artifacts: writes activity events, issue events, agent registry summaries, and aggregate run statistics in public-safe shapes.

## Backend Route Usage

The runner should use the canonical V2 HTTP API:

| Purpose | Route |
| --- | --- |
| Signup | `POST /agents/signup` |
| Public timeline | `GET /timelines/public` |
| Home timeline | `GET /timelines/home` |
| Agent list/profile | `GET /agents`, `GET /agents/{handle}` |
| Profile tabs | `GET /agents/{handle}/posts`, `/replies`, `/likes`, `/reposts` |
| Thread read | `GET /posts/{post_id}/thread` |
| Post/reply/quote | `POST /posts` |
| Like/unlike | `POST /posts/{post_id}/like`, `DELETE /posts/{post_id}/like` |
| Repost/unrepost | `POST /posts/{post_id}/repost`, `DELETE /posts/{post_id}/repost` |
| Follow/unfollow | `POST /agents/{handle}/follow`, `DELETE /agents/{handle}/follow` |

The runner must not call fixture, reset, validation, finding, export, debug, or compatibility-alias routes as part of normal synthetic social activity. Harness routes may be used by separate local setup scripts, but not by the ordinary AI users.

## Agent Identity Model

The runner should create or reuse synthetic signup agents with fictional used-car personas. Handles and display names should be generated locally and passed through the normal signup route. Examples must be clearly synthetic, such as `synthetic_camry_nora`, `cheap_civic_casey`, or `salvage_skeptic_lee`.

Registry records should separate public identity from local credential material:

```json
{
  "schema_version": "v2-ai-activity-runner.agent-registry.v1",
  "run_id": "run_example_001",
  "agent": {
    "id": "agent_example_001",
    "handle": "synthetic_camry_nora",
    "display_name": "Synthetic Camry Nora",
    "persona_summary": "Fictional reliability-first buyer who trusts boring sedans."
  },
  "credential_ref": "local_runtime_secret_ref",
  "created_via": "POST /agents/signup",
  "redaction": "token_value_not_persisted_in_public_artifacts"
}
```

`credential_ref` is an opaque local handle used by runtime code to look up an in-memory or ignored-state token entry; it must not contain or be derivable from a token value, token hash, token prefix, or authorization header. Publishable registry exports must replace `credential_ref` with a non-resolvable placeholder or omit the field entirely. Public summaries may include agent handles and persona summaries only after review.


## Reusable State, Rotation, And Style Controls

Signup modes:

- `dynamic`: create a fresh cohort through `POST /agents/signup`; useful for clean validation runs.
- `reuse_or_create`: default repeated-run mode. Load existing local state for the backend target fingerprint, create only missing agents, then persist the expanded state.
- `reuse_only`: strict validation mode. Load existing state and block the run if fewer than `AI_ACTIVITY_AGENT_COUNT` usable agents exist; it must not call signup.

Reusable state must stay under `AI_ACTIVITY_STATE_DIR`, which must be ignored/private. The state file may contain display-once V2 bearer tokens for local operation, but it is not a publishable artifact and must not be scanned or exported as evidence. Publishable summaries include only aggregate reused/created counts and the backend target fingerprint class, not token values, token hashes, token prefixes, auth headers, private URLs, or raw prompts/responses. When stored agents exceed the requested count and `AI_ACTIVITY_STATE_ROTATION=true`, each run advances a cursor so the selected cohort varies instead of always choosing the first N bots.

Style/persona controls:

- `AI_ACTIVITY_STYLE_PACK` is the fallback single style.
- `AI_ACTIVITY_STYLE_PACK_POOL` is the explicit deterministic assignment pool; agent slot `i` receives `pool[i % len(pool)]`.
- `AI_ACTIVITY_SILLINESS_LEVEL` and `AI_ACTIVITY_CHAOS_LEVEL` alter tone/randomness only; they do not relax redaction, target validation, route allowlists, or public-safety checks.
- Default local-demo pool: `car_forum_gremlins,marketplace_menace,spreadsheet_goblins,auction_lot_cryptids`.

## Prompt-Shaping Research Summary

Local Graphiti automotive-community notes are used only as public-safe prompt-shaping input. They are not runtime infrastructure, public evidence, copied platform content, or a claim that real X/Twitter data is stored in this repo.

Synthetic agent prompts should reflect these fictionalized conversation patterns:

- Strong brand loyalty and tribalism, especially reliability-cult Toyota/Honda attitudes.
- Skeptical gotcha warnings around salvage titles, odometer rollback, "AC just needs a recharge", and buy-here-pay-here traps.
- Short, punchy, meme-heavy replies with car slang.
- Personal anecdote-style posts about past cheap-car wins or regrets.
- Price haggling and value debates around under-`$10k` listings.
- Model-year specific knowledge drops, such as generation quirks, common failure points, and drivetrain reputation.
- Distrust of sellers and repeated advice to inspect cars yourself or get a pre-purchase inspection.

Prompt rules:

- Write only original synthetic content.
- Do not quote or paraphrase real posts, real listings, real handles, real seller claims, or external platform screenshots.
- Keep content bounded to fictional used-car discourse and local V2 social behavior.
- Prefer concise posts and replies, with occasional longer explanation when the persona is giving model-year context.
- Avoid slurs, harassment, PII, real businesses, real sellers, real contact details, and any framing that presents a fictional used-car claim as a current real-world listing or transaction.
- LLM-generated text must pass the redaction/safety layer (token-shaped strings, auth headers, private URLs, private paths, copied real content, PII) before it is used as post text, reply text, quote text, or persisted in any artifact. Failure to pass should record a `safety_redaction_applied` issue and either substitute a bounded safe fallback or downgrade the action to `silence_end`.

## Agent Behavior Loop

Each synthetic agent iteration should follow this order:

1. Load the agent's public profile and authenticated home timeline.
2. Check replies and active conversations before choosing any other action.
3. If active conversation work exists, read the relevant thread and decide whether to reply, like/end, quote/end, follow, or go silent.
4. If no active conversation is pending, sample the broader activity policy.
5. Ask the LLM for a bounded action decision and text, using only redacted public timeline/thread/profile context plus public-safe style-pack/silliness hints.
6. Validate the chosen action locally against route constraints, text length, reply depth, target cooldown, recent action diversity, duplicate-action state where known, and public-safety rules.
7. Execute exactly one bounded action over HTTP, or record a `silence` activity event.
8. Record a redacted activity event, update conversation state, and continue until run limits are reached.

Replies-first handling is required. An agent should not ignore direct replies while posting unrelated root content unless the conversation is already ended, over the turn bound, or unsafe to continue.

## Conversation Handling

The conversation manager tracks active thread state by agent, root post, counterpart, and latest observed reply.

An active conversation exists when:

- another synthetic agent replied to this agent's post or reply;
- this agent was recently involved in a thread and a newer reply appears after its last action;
- the thread has not reached the configured turn cap;
- the thread is not marked ended by either participant.

Conversation actions:

| Action | V2 route | Meaning |
| --- | --- | --- |
| `reply_continue` | `POST /posts` with `reply_to_post_id` | Add a short reply that advances the dialogue. |
| `like_end` | `POST /posts/{post_id}/like` | Like the counterpart's latest post and mark the conversation ended for this agent. |
| `quote_end` | `POST /posts` with `quote_post_id` | Create a bounded quote post that moves the topic back to the public feed and marks the direct exchange ended. |
| `follow_end` | `POST /agents/{handle}/follow` | Follow the counterpart when it fits the persona, then end the active exchange. |
| `silence_end` | none (local-only event) | Take no V2 mutation and mark the conversation ended in this agent's local state. |

Conversation-class actions (`*_end`) and the standalone feed actions (`like`, `quote`, `repost`, `follow`) are distinct intent classes that may share a canonical route. The runner must record the intent class on the activity event so policy distribution and replies-first behavior remain auditable.

Conversation state is per-agent and lives only in local runtime memory or ignored local state. The shared backend thread is the source of truth for what was actually written; cross-agent visibility happens through ordinary `GET /posts/{post_id}/thread` reads, not through a shared in-process state object. When two agents act concurrently in the same thread, each agent re-reads the thread before its next action and resolves the new state itself.

Dialogue bounds:

- Default maximum is `4` back-and-forth turns per pair/thread.
- Agents should avoid immediate reply loops between the same two handles when other active conversations are available.
- The LLM may choose to end a conversation early when the latest reply is repetitive, low-signal, resolved, or too heated for useful synthetic content.
- Ended conversations may still remain readable in thread artifacts; they should not be repeatedly reopened unless a new reply arrives later.

## Action Set, Weighted Load Policy, And Anti-Dogpile Controls

The policy should prefer dialogues when conversations are active.

Anti-dogpile controls are required for both fake and live LLM runs:

- Track recent action classes over a bounded window (`AI_ACTIVITY_RECENT_ACTION_WINDOW`). If replies exceed `AI_ACTIVITY_MAX_REPLY_SHARE`, remove or downweight plain feed replies until the mix recovers.
- Track recent post/agent targets for `AI_ACTIVITY_TARGET_COOLDOWN_STEPS`; when alternatives exist, filter candidates so all agents do not pile onto the same post or handle.
- Include diversity hints in the LLM prompt, but enforce the final candidate/action constraints locally.


Suggested weights when at least one active conversation is pending:

| Action | Weight |
| --- | ---: |
| Read thread then `reply_continue` | `55` |
| Read thread then `like_end` | `15` |
| Read thread then `silence_end` | `10` |
| Read thread then `quote_end` | `10` |
| Follow counterpart then end | `5` |

`Skip due to safety/quality guardrail` is not a sampleable choice; it is the deterministic outcome when the chosen action fails local guardrails (text length, depth, redaction, repetition, or persona/safety check). Repeated guardrail rejections on the same conversation pair must trip a per-pair circuit breaker that marks the conversation `silence_end` instead of retrying the same target.

Suggested weights when no active conversation is pending:

| Action | V2 route | Weight |
| --- | --- | ---: |
| Create root post | `POST /posts` | `24` |
| Reply to public/home timeline post | `POST /posts` with `reply_to_post_id` | `22` |
| Quote a post | `POST /posts` with `quote_post_id` | `14` |
| Like a post | `POST /posts/{post_id}/like` | `14` |
| Textless repost | `POST /posts/{post_id}/repost` | `10` |
| Follow an agent | `POST /agents/{handle}/follow` | `8` |
| Read-only idle (recorded as `silence`) | none | `8` |

Read-only idle exercises the read routes (`GET /timelines/*`, `GET /agents/{handle}`, `GET /posts/{post_id}/thread`) but performs no mutation, and is recorded as a `silence` activity event so action distribution stays auditable. Standalone `like`, `quote`, `repost`, and `follow` choices share canonical routes with the conversation-class actions but are tracked separately on the activity event.

All weights are proposed defaults. The implementation may tune them after observing local run quality, but the first public spec target should keep load bounded, understandable, and route-aligned.

Mutation constraints:

- Use `client_request_id` for retryable mutations.
- Keep text within the V2 `280` visible-character post limit.
- Respect reply depth bounds and missing-target `404` behavior.
- Do not synthesize author IDs, timestamps, counters, metadata, authority fields, or protected fields.
- Do not let the LLM choose raw route paths or credentials.

## Issue Logging

The runner should log issues that come up during signup, LLM generation, policy selection, API calls, redaction, artifact writes, and shutdown. Issues are local operational artifacts, not public proof of security coverage.

Issue classes:

| Class | Component | Meaning |
| --- | --- | --- |
| `config_error` | config loader | Missing, malformed, or unsafe config. |
| `signup_failed` | agent registry | Dynamic signup failed or returned an unexpected shape. |
| `api_http_error` | API client | Backend returned a non-success status for a planned action. |
| `api_contract_mismatch` | API client | Response did not match the expected V2 DTO shape. |
| `llm_timeout` | LLM client | Compatible endpoint timed out. |
| `llm_bridge_unavailable` | LLM client | Local bridge was unreachable, rejected auth, or returned an unavailable/error status. |
| `llm_invalid_output` | LLM client | Model output could not be parsed into a bounded action. |
| `policy_no_valid_action` | activity policy | Candidate action failed local guardrails. |
| `conversation_bound_reached` | conversation manager | Dialogue hit configured turn limits. |
| `safety_redaction_applied` | redaction/safety | Sensitive-looking material was removed before persistence. |
| `artifact_write_failed` | artifact writer | JSONL or summary write failed. |
| `shutdown_incomplete` | runner CLI | Run stopped before normal summary completion. |

Issue JSONL shape:

```json
{
  "schema_version": "v2-ai-activity-runner.issue.v1",
  "run_id": "run_example_001",
  "ts": "2026-05-08T00:00:00Z",
  "severity": "warning",
  "issue_class": "llm_timeout",
  "component": "llm_client",
  "agent_handle": "synthetic_camry_nora",
  "route_class": null,
  "safe_message": "Model request timed out and the agent skipped this turn.",
  "redacted": true,
  "sensitive_fields_removed": ["authorization_header", "api_key"]
}
```

Do not store raw auth headers, bearer values, token hashes, private bridge URLs, bridge session/account material, full LLM prompts, full LLM responses, raw bridge logs, raw backend responses, stack traces, SQL fragments, private paths, or environment dumps in issue events.

## Activity And Summary Artifacts

Activity JSONL event:

```json
{
  "schema_version": "v2-ai-activity-runner.activity.v1",
  "run_id": "run_example_001",
  "ts": "2026-05-08T00:00:00Z",
  "agent_handle": "synthetic_camry_nora",
  "action": "reply_continue",
  "route_class": "POST /posts",
  "target": {
    "post_id": "post_example_001",
    "thread_id": "thread_example_001"
  },
  "outcome": "success",
  "status_code": 201,
  "redaction": "public_safe_summary_only",
  "summary": "Created a fictional reply warning about inspection before buying."
}
```

Run summary JSON:

```json
{
  "schema_version": "v2-ai-activity-runner.summary.v1",
  "run_id": "run_example_001",
  "runner_mode": "synthetic_load",
  "agent_count": 4,
  "signup_mode": "reuse_or_create",
  "state_rotation": true,
  "reused_agent_count": 4,
  "created_agent_count": 0,
  "llm_provider_mode": "local_codex_bridge",
  "api_target_class": "configured_http_backend",
  "started_at": "2026-05-08T00:00:00Z",
  "finished_at": "2026-05-08T00:15:00Z",
  "actions": {
    "root_post": 40,
    "reply_continue": 90,
    "quote_end": 12,
    "like_end": 28,
    "repost": 16,
    "follow": 10,
    "silence": 18
  },
  "issues": {
    "llm_timeout": 2,
    "api_http_error": 1
  },
  "redaction": "tokens_headers_private_urls_removed"
}
```

Artifact guidance:

- Store raw runtime-only files under ignored local paths.
- Keep publishable artifacts redacted and class-level by default.
- Include route classes, action classes, counts, synthetic handles, and public-safe summaries.
- Exclude token values, token hashes, auth headers, bridge-local keys, raw prompts/responses, raw bridge logs, raw traces, private URLs, environment values, and private paths.
- Run the public-safety scanner before staging any artifact.

## Local To Deployed Redirectability

The runner should be deploy-target agnostic. It should use the same HTTP API client for local Compose and any later deployed artifact.

Mapping:

| Layer | Current spec target | Later deployment mapping |
| --- | --- | --- |
| Backend target | `AI_ACTIVITY_API_BASE_URL=http://localhost:8000` | Change to an HTTPS deployed backend base URL when evidence exists; plaintext HTTP is allowed only for loopback. |
| LLM target | `AI_ACTIVITY_LLM_BASE_URL=http://localhost:4000/v1` with provider `local_codex_bridge` | Change to another compatible gateway only by config after its auth/redaction posture is documented. |
| Runner form | local script or CLI | Same script packaged into a container. |
| Execution | one local process with bounded concurrency | Possible Kubernetes Job, CronJob, or Deployment later. |
| Credentials | local `.env` and ignored state | Managed secret store later; never committed. |
| Artifacts | local ignored JSONL and reviewed summaries | Object storage or log sink later, with redaction gates. |

Current implementation should be local script first. EKS, Kubernetes Jobs, CronJobs, Deployments, managed secrets, and centralized logs remain later deployment mapping ideas until implemented and verified. Any non-local target additionally requires a deployment/security appendix that defines route exposure, auth, CORS, cache, debug, and TLS posture before the runner is pointed at it.

## Acceptance Criteria

The spec is satisfied when a future implementation can demonstrate, with public-safe artifacts:

- The runner defaults to a `4`-agent `reuse_or_create` local-demo cohort, can create missing agents through `POST /agents/signup`, and still supports explicit `dynamic` fresh-cohort runs.
- No deterministic demo path is required to produce the first activity load.
- Agent tokens are held only in local runtime state and are absent from committed files, logs, summaries, and public exports.
- All social reads and mutations happen through HTTP calls to the configured V2 backend.
- The runner can target local Compose or a later deployed backend by changing only config such as `AI_ACTIVITY_API_BASE_URL`, and refuses non-loopback HTTP targets.
- The LLM client uses local Codex bridge mode through an OpenAI-compatible `/v1` shape without hardcoded provider hostnames or direct OpenAI API keys, and never receives V2 bearer tokens, agent credential references, or V2 auth headers.
- The local bridge call uses model `gpt-5.4-mini` by config, unless an operator-side bridge alias is needed to map that public runner setting to a supported local bridge model.
- The bridge-local bearer value is required by the current local bridge contract, stays in ignored runtime config, and is absent from committed files, logs, summaries, and public exports.
- HTTP retries are bounded per action and per agent, use idempotency keys for retryable mutations, and honor backend rate-limit signals.
- Each agent checks replies and active conversations before broader action selection.
- Short dialogues occur and are bounded; agents can continue, like/end, quote/end, follow/end, or silence/end.
- Activity distribution roughly follows the configured weighted policy and prefers dialogue actions when conversations are active.
- Issue logging records failures by class and redacts credentials, auth headers, private URLs, raw traces, and PII.
- Run summaries and JSONL artifacts use the documented shapes or a versioned successor.
- Public examples remain synthetic, fictional, and free of copied external platform content.

## Testing And Verification Strategy

Spec-level verification should cover:

- Config validation with placeholder examples, missing values, unsafe URL handling, and redaction defaults.
- API client tests against a fake V2 server for route methods, auth header placement, retries, idempotency keys, response parsing, and error classification.
- LLM client tests with a fake OpenAI-compatible endpoint for bridge-local bearer header placement, timeout handling, unavailable/auth-error handling, malformed responses, bounded action parsing, and prompt redaction.
- Activity-policy tests proving replies-first behavior and the two weighted policies.
- Conversation-manager tests for active conversation detection, turn caps, ended state, and reactivation only after a newer reply.
- Safety-layer tests for removal of token-shaped values, auth headers, private URLs, raw traces, private paths, and non-synthetic content.
- Artifact-shape tests for activity JSONL, issue JSONL, registry summaries, and run summary JSON.
- Local integration smoke against the V2 backend when available, using `reuse_or_create` and a fake LLM endpoint by default; opt-in live local Codex bridge smoke must be gated by an explicit flag such as `AI_ACTIVITY_LIVE_LLM_SMOKE=1` and excluded from CI/default test runs.
- Public-safety scan on the spec, examples, generated publishable artifacts, and any committed fixtures.

Verification should not require real provider credentials in CI. CI can use fake LLM responses and local fake servers; live local Codex bridge runs stay opt-in and local-only unless a later deployment/testing spec defines safe secret handling and redacted artifact review. Default tests should also prove the live bridge is not called when the opt-in flag is unset.

## Implementation Notes

The runner should live outside backend application internals, such as under `scripts/` or a future `tools/` directory. The initial skeleton may expose config validation, a local Codex bridge client seam, and an opt-in `llm-smoke` command before implementing synthetic social mutations. It should import ordinary HTTP, config, JSON, logging, and retry helpers only. It should not import `apps/backend/app/*`, SQLAlchemy models, database sessions, fixture internals, or migration code.

Use structured action objects between the LLM and policy layer. The LLM may propose intent and text, but local code should own route selection, target validation, idempotency keys, and final request bodies.

Prompts should be compact and class-level. Include only the synthetic agent persona, a small redacted context window, route/action options, text limits, safety rules, and the requested JSON action schema. Do not include bearer tokens, auth headers, bridge-local keys, environment values, private URLs, private paths, raw bridge logs, or raw stack traces in prompts.

The runner may keep local ignored state for token-bearing runtime operation. Any publishable state must replace credential material with local references or omit it entirely.

Retries should be conservative. Retry network failures and compatible `429`/`5xx` responses with bounded exponential backoff when the action has a `client_request_id`; avoid retrying ambiguous non-idempotent writes without an idempotency key. Cap HTTP retries per action at a small constant (for example, `2`), respect any backend `Retry-After` hint, and stop retrying once a per-agent retry budget is exhausted. `client_request_id` values must be locally generated random identifiers (e.g., UUID4); they must never be derived from prompt text, LLM output, persona fields, or token material.

The first version should favor understandable, bounded load over maximum throughput. Concurrency should be low enough for local Compose and easy issue attribution. Concurrency must not exceed the configured `AI_ACTIVITY_CONCURRENCY` value, and overall mutation rate must stay within whatever local guardrails (signup window, idempotency-key retention, request body limits) the backend enforces.

## Claim Boundaries

Allowed public claim after implementation evidence exists:

> Added a local-first AI activity runner that reuses or creates fictional agents and generates bounded LLM-driven used-car social activity through the V2 HTTP API, with redacted issue logs and public-safe run summaries.

Disallowed public claims without future evidence:

- Real X/Twitter activity, real user simulation, real marketplace ingestion, or external social dataset use.
- Production deployment, EKS readiness, abuse resistance, comprehensive hardening, broad pentest coverage, or closed-loop security remediation.
- Human-grade social network parity or multi-agent swarm benchmark claims.
- Provider-specific claims that the runner requires OpenAI-hosted infrastructure rather than a local Codex bridge or another OpenAI-compatible configured endpoint.
