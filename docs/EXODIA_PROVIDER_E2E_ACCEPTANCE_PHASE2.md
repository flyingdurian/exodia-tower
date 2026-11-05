# EXODIA Tower — Phase 2 provider acceptance boundary and test protocol

Status: **frontend observability and local contract testing only**, not authenticated provider certification. Cursor owns transport and authentication. The Lead Developer may audit app tasks and display status but must not rewrite provider selectors, cookies, sign-in flows, or official API clients.

The seven canonical entries remain, in order: ChatGPT (chronos), Gemini (chronos), DeepSeek (chronos), Ollama (automatic local), ChatGPT (api), Gemini (api), DeepSeek (api). API entries are presently not configured; the UI shows each separately from the canonical backend catalog, not guessed from a saved key. No credentials should be logged, embedded into custom instructions, or committed.

For an actual operator-assisted E2E acceptance run, collect **per transport**: local branch/build SHA, provider selection, explicitly observed signed-in status (if browser), timestamp, task UUID, real submission evidence, final response text/media arrival, lifecycle transitions, measured first/complete latency, cancellation/timeout behavior, persistent history after restart, and evidence that the three browser profiles remained separate. Sensitive text/profile/cookies must be redacted; submit only nonsecret evidence to a reviewed PR. Do not infer success from unit mocks, authenticated UI tests in a separate browser, or the mere existence of a Playwright session.

Provider acceptance matrix (pending owner environment):

| Transport | Mock/contract | Real E2E status | Notes |
|---|---|---|---|
| ChatGPT (chronos) | Existing CI contract | NOT VERIFIED HERE | Cursor must capture authenticated response delivery and cancellation |
| Gemini (chronos) | Existing CI contract | NOT VERIFIED HERE | Verify real browser account/session, independent task tab |
| DeepSeek (chronos) | Existing CI contract | NOT VERIFIED HERE | Verify real browser account/session, independent task tab |
| Ollama (automatic local) | Existing local contract | NOT VERIFIED HERE | Requires owner's running Ollama service/model |
| ChatGPT/Gemini/DeepSeek (api) | Backend catalog rejects unconfigured selection | NOT CONFIGURED | No client or secrets accepted by this UI-only change |

The History toolbar searches only stored public task prompts/provider/agent IDs, and filters returned local tasks. It does not search private instructions or exported answers. Cancellation remains explicitly local. The provider status card reads current session and server catalog state. An external authentication prompt is never bypassed or silently automated by the Lead Developer.
