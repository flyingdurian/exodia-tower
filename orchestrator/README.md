# Exodia Tower — Local Orchestrator v0.3

**Authoritative project:** https://github.com/flyingdurian/exodia-tower

The approved V0.2 backend and artwork are preserved. The current dashboard is the redesigned technology-first Exodia operations interface. Nova is the tenth specialist for YouTube, TikTok and Instagram editorial planning. **Navigation projections are not articulated character rigs.** No publishing adapters have been authorized or connected.

Run: `pip install -r requirements.txt` then `python main.py`. Browse `http://127.0.0.1:8765`. Your `.env` is local and must stay uncommitted.

Local workflow API: `GET /api/social/status`, `GET /api/social/jobs`, `POST /api/social/jobs`, `PATCH /api/social/jobs/{id}`, `POST /api/social/jobs/{id}/advance`, `POST /api/social/jobs/{id}/approve`, `GET /api/social/jobs/{id}/brief`. Mutations require `X-Exodia-Client: exodia-dashboard` in the localhost environment. These measures are not sufficient for public exposure.

For more details and release limitations see the repository root README and `/docs/`.


## V0.4 — Operator-assisted model workspaces

Exodia Tower does not require paid developer API keys for the local model handoff workflow. It can launch **three persistent Chromium profiles** for ChatGPT, Gemini and DeepSeek under ignored `session_data/`. Install once: `playwright install chromium`, then open the sessions from the dashboard. Log in yourself. Prompt filling requires an operator action; browser submission and output extraction are deliberately manual. This is not unlimited or automated consumer-chat inference.

Model session endpoints: `GET /api/web/sessions`, `POST /api/web/sessions/start`, `POST /api/web/sessions/{model_choice}/prepare`, `POST /api/web/sessions/{model_choice}/record`.

All mutation routes require `X-Exodia-Client: exodia-dashboard` and localhost; these are only local guardrails, not full authentication. Never commit browser profiles, .env, databases, or DOM screenshots.

## Articulated animation engineering

Ten rig manifests define 22 joints and 24 emotional poses per character. Use `/api/rigs` and `/rig-lab` to inspect motion **diagnostics**. Existing approved portraits are flattened; production-quality animated characters still require transparent registered body segments, complete face/eye/mouth layers, mesh deformation, lip-sync and fidelity review. Do not label these debug skeletons as finished characters.

## Automatic companion inference — local Ollama

To run tasks without manual response copying **or a developer key**, install [Ollama](https://ollama.com/download) on Windows, then in PowerShell run:

```powershell
ollama pull llama3.2:3b
ollama list
```

Start Exodia Tower as before (`py main.py` inside the project environment). In Task Dispatch choose **Local model (automatic · Ollama)** and your assigned companion, then **Create task**. Exodia persists the task, starts the local inference, displays Working, and saves the answer automatically to the companion's terminal. If Ollama isn't installed/running or the selected model is missing, it displays Failed with an actionable error instead of inventing a reply.

No background browser scraping is performed. The ChatGPT, Gemini, and DeepSeek consumer-web modes remain manually operated because their consumer sessions are not a supported automatic-inference contract. An authorized ChatGPT route using Sign in with ChatGPT / approved plan-usage OAuth is separately documented for supported client eligibility; no user credentials or cookies are copied.

This is **local text inference**, not an image generator, autonomous web researcher, or social publishing agent. For useful research/analytics, add authorized external retrieval tools. Performance depends on PC hardware and the selected downloaded model.

If a local inference task is interrupted by an application restart, the task changes to Failed and may be resubmitted. The `/api/command/providers` endpoint checks whether Ollama is reachable and the desired model is installed.

## U3 — Autonomous live public-web research

In **Command Center**, choose **Local model (automatic · Ollama)**, select a companion, check **Research public web sources**, and submit a request. For precise live information, include one to three `https://` source URLs within the prompt. Exodia uses a fresh, cookie-free Playwright Chromium context to read each permitted page, then gives cited evidence to local Ollama. The companion shows `RESEARCHING → RUNNING → ANSWERED` or `FAILED` and clickable source links. There is **no manual response copying** in this flow.

Safety: Only hosts explicitly listed in `RESEARCH_ALLOWED_HOSTS` can be visited. The default is `en.wikipedia.org`. To read other *public* sites, edit your local `.env`, e.g. `RESEARCH_ALLOWED_HOSTS=en.wikipedia.org,example.org` and restart Exodia. The browser checks DNS for public IPs, rejects credentials/localhost/IP URLs, blocks third-party requests, runs without accounts/cookies, and never disables anti-bot protections. Content may be incomplete on dynamic or restricted pages; failures remain visible, not invented.

Without a URL, Exodia performs a free Wikipedia encyclopedia search (which is **not** a broad current-news or trends search). For current trends and analytics, provide specific permitted sources or add an authorized search connector later. Do not assume Wikipedia search alone answers rapidly changing questions. A research-enabled task is capped at 4,000 prompt characters because of the added evidence context. The local model still requires its Ollama download and may hallucinate; verify citations.

This implementation does **not** scrape prompts or answers from the ChatGPT, Gemini or DeepSeek consumer websites. Those workflows still require authorized provider integration. See issue #6 for ChatGPT authorization-based integration.

## React-rich text input correction

The operator-assisted browser preparation now clicks rich-text/contenteditable prompt editors and sends actual keyboard events (`ControlOrMeta+A`, then typed characters). Native `textarea` inputs still use Playwright's `fill()`. This improves editor compatibility but deliberately does not press Send or extract consumer chat responses.

A general DOM stream-stability watcher for **authorized, automatable sites** is provided separately in `app/automation/interactive_dom.py`. It requires a page that the operator has rights to automate and is not connected to the consumer ChatGPT, Gemini or DeepSeek sessions.

## Custom authorized website automation — complete task loop

A complete, configurable Playwright runner is available at `app/automation/configured_web.py`. It uses an isolated persistent Chromium profile, real keyboard events for contenteditable fields, submit click, detection of a **new** answer, stream-stability and stop-button checking, serialization, diagnostics, and automatic delivery to the assigned companion's terminal.

To try it with the safe local simulation (no third-party account required):

```powershell
cd orchestrator
New-Item -ItemType Directory -Force session_data | Out-Null
Copy-Item examples/custom_web.example.json session_data/custom_web.json
.\\.venv\\Scripts\\python.exe -m playwright install chromium
.\\.venv\\Scripts\\python.exe main.py
```

Choose **Configured website (automatic)** in the Command Center, assign Kiko/Nova, and submit a prompt. The runner opens `http://127.0.0.1:8765/automation-demo`, types, clicks Send, waits until the demo stops streaming, then delivers its simulated response to the companion. The demo response is **not an AI model**.

To adapt the code to a website you are authorized to automate, change the URL and selectors in the ignored `session_data/custom_web.json` profile, and verify that the site's terms and your access rights allow automation. Do not supply account credentials to Exodia; sign in manually within the persistent browser profile. The app does not include consumer ChatGPT/Gemini/DeepSeek auto-scraping connectors or anti-detection code.

Task states: `opening -> typing -> submitting -> waiting_for_reply -> answered`, or `failed`. Browser errors save screenshots in ignored `debug_snapshots`; incomplete tasks are marked failed upon restart. This system does not bypass paywalls, CAPTCHAs, or account security challenges.


### Three independent authorized browser slots

Custom browser configurations are `session_data/custom_web.json`, `session_data/web_slot_2.json` and `session_data/web_slot_3.json`. All three are optional, private and gitignored. Their persistent profiles live in separate folders. The Command Center provides **Configured browser A, B, C** task choices. Separate tasks on different slots run concurrently; tasks on the same slot serialize to avoid interleaving prompts. To test all slots, copy the example JSON to each filename. These are configurable authorized-site slots—not prewired consumer account scrapers.

## Gemini automatic text tasks (experimental)

Gemini browser (automatic · text) runs a task in the Gemini Playwright browser profile under ignored `session_data/gemini`. Open Browser Workspaces and sign in manually when required; then choose Gemini in Task Dispatch, assign a companion, and Create task. Exodia prepares React-rich text, submits using Gemini's visible send button (or Enter if unavailable), waits for **new** streamed text to finish, and puts it into the companion's terminal without manual copying. Task states are opening/typing/submitting/waiting_for_reply/answered or failed. The original model answer is displayed as text, not recomposed by Ollama.

This is a **best-effort experimental website integration**, not an official Gemini API contract. DOM selectors can change; no end-to-end live authenticated Google account test is included in CI. Session login, rate limits, permissions, verification challenges and website access instructions still apply. This implementation does not evade bot detection or authentication challenges. Debug screenshots of failed browser interactions are saved privately in ignored `debug_snapshots`. Any automatically generated images are not yet captured by this text-only adapter.
