# Exodia Tower — task-stage and media reliability gate

## Current checkpoint

The task dashboard at `/` shows a **selected companion performance stage**, not the
old baked-in command-room illustration. Facial expressions, state-linked computer
animations, arcade idle mode, and success handoff are driven by actual task statuses
rather than developer mood-preview controls.

Artwork: only Albedo's concept-grade expression atlas is available today. Other
companions show their existing authored portrait in the same performance stage.
They are not falsely described as having unique multi-expression production art.

To install the optional expression pack, download
`exodia_albedo_expression_art_pack.zip` from the development handoff,
then extract its `orchestrator/frontend/companions/expressions/` directory into
the repository root. This is intentionally not pushed into Git as a binary
artifact; the UI shows the agent portrait if the atlas is missing.

## Gemini reliability

- Two concurrently executing tasks maximum, each in its own temporary tab
  inside the **same signed-in persistent browser context**.
- 2.5-second minimum start spacing to avoid simultaneous prompt activation.
- The task tab closes on success or failure. Browser profile and sign-in remain.
- Distinct states `queued`, `cooldown`, `opening`, `typing`,
  `submitting`, `waiting_for_reply`, `rendering_media`,
  `answered`, `failed`.
- Media watcher detects generated images/video in model responses, including
  open Shadow DOM where accessible; it does not require a markdown paragraph.
- Deduplicated media gallery, with one preview/download per unique local
  artifact. Exact visual media capture depends on Gemini's changing DOM and CORS.
- Selenium/Playwright **not required for viewing** the finished local output;
  required for the browser wrapper itself.
- Mock and Chromium DOM checks are not a real signed-in Gemini media test.
  Return a debug screenshot if your signed-in site still fails.

## Natural voice: local Kokoro-FastAPI

The default voice choice is natural neural speech, **not** Microsoft system TTS.
A compatible Kokoro TTS service must be running locally on port 8880.
The desktop browser voice option remains an explicit fallback, not the default.

Install Docker Desktop, then run the CPU version (copy in PowerShell):

```powershell
docker run --rm -p 127.0.0.1:8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu:latest
```

Or use NVIDIA GPU acceleration if supported:

```powershell
docker run --rm --gpus all -p 127.0.0.1:8880:8880 ghcr.io/remsky/kokoro-fastapi-gpu:latest
```

Docker images may download substantial weights at first startup. Check
`http://127.0.0.1:8880/web` for a working voice demo. Then use Exodia's
"Natural local voices" setting and click Speak to test.
The FastAPI proxy only sends text to `127.0.0.1:8880`. It uses the actual
companion ID to select a voice and caps text length to reduce generation latency.
Voice quality/speed are machine-dependent; the app cannot guarantee sub-second
speech on CPU. The first request may incur model warm-up.

Companion-to-voice mapping can be adjusted in `app/api/server.py`'s
`VOICE_IDS`. The UI shows a useful service-unavailable error when missing.

The Gemini mobile application's proprietary speech voices are not used or
extracted by this integration.

## ChatGPT

The consumer ChatGPT website is available as a manually supervised web
workspace, not as an automated output scraper. OpenAI's consumer Terms
of Use prohibit automatic/programmatic extraction of ChatGPT output.
An authorized API connection would be a separately configured and metered
provider, not a hidden browser-based workaround. No ChatGPT account
authentication or output extraction has been changed in this gate.
