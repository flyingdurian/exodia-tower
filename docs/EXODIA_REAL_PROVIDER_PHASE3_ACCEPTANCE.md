# EXODIA Tower — Real provider Phase 3 acceptance protocol

**Scope:** operator-run, real localhost task API testing. This does **not** create remote sign-in sessions, bypass provider authentication, change Cursor's transport implementations or certify the owner environment from CI mocks.

The owner machine must have the actual EXODIA build running in an isolated worktree on the selected localhost port, with distinct SQLite DBs and Playwright profiles. Existing Cursor providers remain the source of truth. Run the probe from that *same* local checkout with the real signed-in Chromium sessions as needed.

## Read-only first

```powershell
cd C:\Users\TFBOSS\Documents\GitHub\exodia-tower\orchestrator
python tools\provider_e2e_probe.py --base-url http://127.0.0.1:8767
```

The default reports status only, never treats `ready_for_next_prompt` as authenticated proof, and records API option configuration separately. It does **not** create a task, store session details or write evidence unless requested.

## Explicit live acceptance

Run only after signing in to the intended browser provider within its *own* existing Chromium profile, or starting Ollama locally with a model ready. Each invocation creates a **real** benign test task; these are not simulated calls:

```powershell
python tools\provider_e2e_probe.py --model chatgpt --mode respond --confirm-real-dispatch --timeout 120 --evidence .\evidence\chatgpt-response.json
python tools\provider_e2e_probe.py --model gemini --mode respond --confirm-real-dispatch --timeout 120 --evidence .\evidence\gemini-response.json
python tools\provider_e2e_probe.py --model deepseek --mode respond --confirm-real-dispatch --timeout 120 --evidence .\evidence\deepseek-response.json
python tools\provider_e2e_probe.py --model ollama --mode respond --confirm-real-dispatch --timeout 120 --evidence .\evidence\ollama-response.json
```

For **separate cancellation trials**, use the same model with `--mode cancel --cancel-delay 1`, a new evidence filename, and `--confirm-real-dispatch`. A cancellation is local; the remote consumer site may continue responding even though EXODIA suppresses late delivery. Timeout also attempts *local* cancellation to avoid leaving an unobserved EXODIA job. Explicitly distinguish `answered`, `failed`, `cancelled`, timed out, and `awaiting_operator` instead of treating any session open as success.

**Evidence fields:** build SHA/channel, timestamp, task UUID, states observed, locally reported first/total latency, nonempty-answer boolean, local cancellation persistence, and scope. Never store task text, provider response content, cookies, tokens, credentials, signed-in profile paths or raw browser diagnostics in the evidence JSON. Store evidence locally; share only redacted findings approved by the owner. Recheck persistent task UUID/history after app restart, which this runner deliberately does not perform automatically.

**Provider status:** ChatGPT/Gemini/DeepSeek Chronos are pending authenticated owner-run acceptance; Ollama awaits local service/model. ChatGPT/Gemini/DeepSeek official APIs remain unconfigured, and the probe never attempts them or asks for secrets. API implementation remains Cursor-owned.

**What CI can prove:** the runner blocks external hosts, defaults to read-only, rejects unconfirmed dispatch, correctly creates and polls mock HTTP tasks, honors local cancellation and timeout, and does not leak answer content. **CI does not prove authenticated provider execution.**

The `local_delivery_observed` result means an actual EXODIA task returned a response via the local API; it still requires independent authenticated session evidence to certify the model provider and automatic transport. Manual operator handoff is explicitly marked inconclusive for automatic-provider acceptance.
