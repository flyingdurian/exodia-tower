# Exodia Tower: ChatGPT automatic browser submission — development gate

## Implemented

Exodia's ChatGPT option now creates a real task, launches (or reuses) a
persistent Playwright Chrome profile in `orchestrator/session_data/chatgpt`,
opens a **separate temporary ChatGPT task tab**, finds the composer, injects the
user-requested prompt through keyboard events, and clicks the visible Send
button exactly once. The app never retries an ambiguous click, never attempts
to sign in or solve challenges, and does not read assistant output.

The companion stage reflects `opening`, `queued`, `cooldown`, `typing`,
`submitting`, `awaiting_operator`, `answered`, `failed`.
Tasks are keyed by their UUID; at most two browser review tabs can be open.
Each submitted tab stays open for review and is closed when the user delivers
an answer or cancels the task. The primary signed-in Chrome profile remains.

## How to run on Windows

1. Update the project:

```powershell
cd C:\Users\TFBOSS\Documents\GitHub\exodia-tower
git switch development/exodia-foundation
git pull --ff-only origin development/exodia-foundation
cd orchestrator
.\.venv\Scripts\python.exe main.py
```

2. In the Exodia command screen, choose **Open ChatGPT browser**. Sign in and
finish any account verification yourself in that visible window. Do not start
other Chrome processes with the same Playwright user-data directory.

3. Select **ChatGPT · auto send / manual result**, choose a companion, and
type a task. Click **Send command**.

4. The app opens a new task tab and automatically types/clicks Send. If the
site changes its selector or login is needed, the task fails visibly and
captures a local-only screenshot under `debug_snapshots/`.

5. The task transitions to **awaiting_operator**. Review the ChatGPT output in
the task tab and use the **Deliver through companion** panel to enter the
result. Exodia stores it as `operator_supplied`, closes that tab, updates the
agent's success state, and shows the formatted answer in its terminal.
Alternatively, choose **Cancel task** to close that task's tab.

## Invariants and limitations

- **Automatic prompt submission: YES. Automatic ChatGPT output extraction: NO.**
  Consumer ChatGPT Terms prohibit automatic/programmatic extraction of output.
  This bridge intentionally does not include scraping selectors or hidden APIs,
  Chrome extension hacks, DOM watches for output, or network interception.
- There is no claim that ChatGPT accepted or completed the prompt merely
  because a click succeeded; the response must be reviewed and supplied by the
  operator, or an authorized first-party/API integration built separately.
- Account/login challenges are handled only by the person in the browser.
  Persistent cookies remain in the local Playwright profile and are ignored
  by Git. Never commit `session_data`, `.env`, or debug screenshots.
- Selectors are brittle because the consumer website UI can change. The
  bridge fails closed with a screenshot; no blind retries or duplicate sends.
- The browser code preserves an extension boundary: `ChatGPTSubmissionBridge`
  handles task-bound input and tab lifetime; `server.py` accepts task-result
  delivery independently via `/api/command/tasks/{task_id}/response`.
  A permitted future provider integration can implement its own authorized
  delivery method without altering companion state logic.
- This is not a ChatGPT API feature, and it does not grant access to any
  subscription entitlements in automated model requests.
- The development tests use fake ChatGPT DOM and local Chromium synthetic task
  screens, not a real authenticated ChatGPT account.
