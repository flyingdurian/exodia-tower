# EXODIA Tower — Provider Integration and Compatibility Contract

**Contract:** `exodia.provider-integration/v1`  
**Owner directive:** 2026-11-04  
**Consumers:** Cursor provider specialist; ChatGPT Lead Developer integration owner; local UI and task clients.

This is the authoritative boundary for browser/Chronos, local inference and *future* official API transports. It describes both the **observed existing contract** at integration commit `96a85f46e6bebfdfd69500cc3a10ac7447d75ab5` and **requirements for subsequent implementations**. A desired feature is not proof that an adapter exists. Cursor owns provider-specific implementation and changes to private instruction composition; the lead owns central routing, frontend synchronization and integration acceptance. Shared files require coordinated review.

## 1. Seven stable model choices — exact UI order

| Order | Visible label | `model_choice` (wire) | Legacy `provider_id` / stored `provider` | Transport | Current implementation status |
|---|---|---|---|---|---|
| 1 (default) | ChatGPT (chronos) | `chatgpt` | `chatgpt` | `browser` | Browser task automation + response collection, best-effort, signed-in E2E **not certified by CI** |
| 2 | Gemini (chronos) | `gemini` | `gemini` | `browser` | Browser task automation, best-effort; authenticated E2E separately required |
| 3 | DeepSeek (chronos) | `deepseek` | `deepseek` | `browser` | Browser task automation, best-effort; authenticated E2E separately required |
| 4 | Ollama (automatic local) | `ollama` | `ollama` | `local` | Existing local model inference |
| 5 | ChatGPT (api) | `chatgpt:api` | `chatgpt` **only after actual integration** | `api` | Not configured; fail closed |
| 6 | Gemini (api) | `gemini:api` | `gemini` **only after actual integration** | `api` | Not configured; fail closed |
| 7 | DeepSeek (api) | `deepseek:api` | `deepseek` **only after actual integration** | `api` | Not configured; fail closed |

`chronos` is only an owner-selected **display label for browser-assisted execution**, not an official model name, model version, API or entitlement. Preserve the legacy persisted `provider` strings in SQLite. `orchestrator/app/automation/provider_catalog.py` owns wire values and ordering; `GET /api/command/model-options` exposes `default`, `options`, and optional `advanced`. `custom_web`, `web_slot_2`, `web_slot_3` remain compatible **advanced** browser slots, not replacements for these seven choices.

The `api` choices **must not** dispatch through `browser` or automatically incur paid usage. Configured feature flags, official client/key management, supported models, consent/authorization, rate limits, spend safeguards and mocked/non-mocked tests are prerequisites for enabling any slot. API secrets remain local server-side only.

## 2. Current HTTP APIs and request/response semantics

- `GET /api/command/model-options`: stable public catalog; `available=false` plus `status=not_configured` for placeholder API modes.
- `GET /api/command/providers`: runtime capability/status snapshots for real transports. Capability presence is not evidence that the user is signed in or a website is stable.
- `GET /api/web/sessions`: browser session state; status and `automatic_extraction` describe implementation capability, not login verification.
- `POST /api/command/tasks`: authenticated **local dashboard** task creation. Requires `X-Exodia-Client: exodia-dashboard`; this header is a prototype local operator guard, **not** public authentication. The current accepted request fields include `agent_id`, `prompt`, `model_choice`, optional `transport`, optional `custom_instructions`, and `web_research`. The server derives the stable stored provider from the requested choice.
- `GET /api/command/tasks`: return task history with provider attribution, lifecycle state, result/error, optional artifacts, media and timings; **never** return `private_instructions`.
- `GET /api/command/model-instructions` and `PUT /api/command/model-instructions`: local settings editor endpoints, requiring the local dashboard header. These endpoints **intentionally return saved instruction content** to the authorized editor; task endpoints do not.
- `POST /api/ask`: existing general assistant route. `ollama` must route locally. API placeholders must reject and must never invoke the browser as a fallback.

Current task-create example (browser):

```http
POST /api/command/tasks
X-Exodia-Client: exodia-dashboard
Content-Type: application/json

{"model_choice":"gemini","transport":"browser","agent_id":"kiko","prompt":"Explain the decision","custom_instructions":"Use concise paragraphs."}
```

Response is an HTTP `201` task record with a stable generated `id`, original unmodified `prompt`, `provider:"gemini"`, and an initial execution `state` (normally `opening`). Execution is asynchronous; poll the task list/state for `answered` or `failed`. Do not interpret the initial `201` as a completed model response. The current SQLite inbox retains provider, prompt, task states, answer, artifact, error, sources, metrics, media and an internal `private_instructions` column; those stored identifiers are compatibility invariants. The current schema **does not persist a dedicated transport column**. Future API adapters may add an explicit transport field by additive migration; historical browser/local task records must remain readable with a documented legacy interpretation, not silently rewritten.

Failure examples: invalid provider/transport combination → HTTP `422`; unavailable official API slot → HTTP `422` and a clear `not configured` detail, with **no task created**; inaccessible signed-in browser/composer → task `failed` with a safe diagnostic; Ollama unavailable → truthful local failure, never a browser fallback. Error messages must not include account cookies, API keys, token strings or private instructions.

## 3. Task lifecycle and cancellation boundary

Existing task states include `draft`, `queued`, `cooldown`, `opening`, `typing`, `submitting`, `waiting_for_reply`, `researching`, `running`, `rendering_media`, `awaiting_operator` (legacy/manual), `answered` and `failed`. Not every transport uses every state. Route all responses by **task ID**, not by “most recent browser tab”; write at most one final answer per task and do not overwrite an existing completed task with a late callback.

A future transport adapter must return a normalized result containing `answer`, `provider`, transport, completion status, and optional `media`, `sources`, `metrics`. Server and UI must agree on statuses, provider labels and fallback guidance. Persist original prompt, never replace it with a composed private-instruction payload. For media, store only local, validated `/artifacts/...` references; ensure provenance and provider-specific download errors are observable.

Cancellation is **not a uniformly completed cross-provider contract** today. The ChatGPT bridge includes a task-tab cancellation path; actual cancellation behavior and other providers require separate adapter testing. Any new unified cancel endpoint must be idempotent, prevent further state/answer updates after cancellation, free owned browser resources, and distinguish client cancellation from provider timeout. No "cancelled" success claim based only on deleting a UI card. Restarts may mark active tasks `failed` via `Inbox.fail_interrupted()` to prevent false running statuses; this does not guarantee a remote provider stopped processing a previously submitted request.

## 4. Custom instructions, privacy and backwards compatibility

Current private instruction implementation is in `orchestrator/app/automation/model_instructions.py` and `docs/MODEL_INSTRUCTIONS.md`. It supports saved browser-provider instructions (ChatGPT/Gemini/DeepSeek) and optional per-task `custom_instructions`. Saved text is in an **ignored worktree-local** `orchestrator/session_data/model_instructions.json`; do not commit or copy it into unrelated worktrees. Combined saved+task instructions ≤4,000 characters; prompt+instructions ≤12,000; violations fail before dispatch. Compose directions **only at send time**, with the original prompt stored unchanged. `public_task()` filters the private column from task APIs. Settings read/write deliberately expose authorized editable text; status, logs, events, error payloads, browser screenshots, task history and media metadata must not leak it.

When adding official APIs, preserve instruction semantics and specify whether instructions become a system/developer instruction or a user-message prefix *per official API contract*; don't assume all providers accept the same roles or persist instructions remotely. Never return user/private instructions in unauthenticated endpoints. Migrations require schema-version notes, pre-migration SQLite backup, additive columns, explicit rollback strategy and tests covering records created before the change.

## 5. Integration checklist for provider changes

1. Cursor provides adapter changes and mock/contract tests on `feature/cursor/...`; no unreviewed overwrites of `server.py` or shared UI. The lead implements frontend/cross-provider coordination on `feature/lead/...` and confirms the exact upstream adapter interface before edits.
2. Keep `model_choice`, `provider_id`, `transport` and human-facing `label` separate. Preserve all seven choices and the legacy IDs. Unsupported transport should fail closed without creating tasks or starting browsers.
3. Test: successful text; partial-stream avoidance; media-only completion; timeout; unavailable editor; 4xx/5xx official API failure; cancellation; restart; concurrent task isolation; retries that cannot double-submit; user-instruction redaction; old SQLite task round trips; Ollama locality; the three unconfigured API choices.
4. Run Python/Node and FastAPI tests, then headless desktop/mobile Chromium using *the current code SHA*. Record screenshot and artifacts after change. Log real vs mocked probes separately.
5. For **authenticated E2E** (only from the owner's legitimately signed-in test profile), use matched safe prompts with ChatGPT/Gemini/DeepSeek. Record stable response extraction, media file provenance, terminal task state, latency submetrics, selected model label, success/failure and actual date. Do not claim consumer-site browser automation supports unrestricted scraping, bypass or stable undocumented DOM selectors.
6. Ensure the current application version marker reports its real commit SHA (`GET /api/build-info`) and no UI label falsely identifies a placeholder API as configured. Obtain integration-owner approval and merge via PR into `development/exodia-foundation` only when current-head CI is green.

## 6. Authority, ownership and current gaps

- User's newest explicit directive and repository-verified code > these descriptions > older assistant handoffs. Preserve stricter owner-approved artistic/security governance and local-first protections.
- Existing `docs/EXODIA_CHATGPT_INTEGRATION.md` and `scripts/test-exodia-api.mjs` were **not present at this reviewed upstream GitHub SHA**; they may exist in Cursor's uncommitted/local worktree. Do not invent their contents or erase them; Cursor should include them in its own feature PR after review.
- Provider DOM automation and official API implementations remain Cursor-owned. This contract documents integration boundaries; it does not certify official API readiness or authenticated website E2E.
- The accepted Albedo four-portrait GitHub review assets are development-only. All 29 protected originals and review images remain immutable; `release.enabled=false`, 33 production portraits remain subject to the separately governed native-art gate.
