# Exodia Tower

A local-first AI operations system with specialist companions, live workflow instrumentation, and an approval-gated Social Media Division for **YouTube, TikTok and Instagram**.

**Status:** V0.4 development checkpoint (draft PR). The uploaded Command Tower V0.2 code and original nine approved portrait assets are preserved under `orchestrator/`. Exodia's new interface is live in code; character projections navigate the operations floor, but **there are no completed articulated rigs**. Nova is the tenth registered specialist; her approved illustration and rig are pending.

## Run locally

```powershell
cd orchestrator
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python main.py
```

Open http://127.0.0.1:8765 for the Exodia command center. `/companions` is the legacy portrait studio. If port 8765 is already occupied, set `PORT=8775` in `.env` and use that address instead.

## Functionality today

- FastAPI and WebSockets with local knowledge, caching, read-only GitHub/Etsy/YouTube/Gmail checks, and task routing.
- Modernized multi-pane operations interface with **real client-side roaming projection navigation** and selectable agents; this is not face/body animation.
- Ten registered specialist agents, including Nova for social production planning. Event-driven emotions are names/states only until true art rigs are commissioned.
- Persistent SQLite social editorial queue: idea → research → script → assets → edit → review → approved. Approval is explicitly recorded and invalidated when protected content changes.
- Per-platform planning prompts for YouTube, TikTok and Instagram. No invented engagement metrics or fabricated research results.
- **No automatic posting**: authenticated OAuth/upload/scheduling integrations are future development gates.

## Test

```bash
cd orchestrator
python -m pytest tests -q
node --check frontend/app.js
```

See `docs/ROADMAP.md`, `docs/ANIMATION_CONTRACT.md`, and `docs/SOCIAL_MEDIA_DIVISION.md` for remaining acceptance gates. Do not expose this local API to the public internet until authentication and authorization are implemented. Never commit `.env`, local SQLite, account session profiles, or tokens.


## V0.4 — Operator-assisted model workspaces

Exodia Tower does not require paid developer API keys for the local model handoff workflow. It can launch **three persistent Chromium profiles** for ChatGPT, Gemini and DeepSeek under ignored `session_data/`. Install once: `playwright install chromium`, then open the sessions from the dashboard. Log in yourself. Prompt filling requires an operator action; browser submission and output extraction are deliberately manual. This is not unlimited or automated consumer-chat inference.

Model session endpoints: `GET /api/web/sessions`, `POST /api/web/sessions/start`, `POST /api/web/sessions/{model_choice}/prepare`, `POST /api/web/sessions/{model_choice}/record`.

All mutation routes require `X-Exodia-Client: exodia-dashboard` and localhost; these are only local guardrails, not full authentication. Never commit browser profiles, .env, databases, or DOM screenshots.

## Articulated animation engineering

Ten rig manifests define 22 joints and 24 emotional poses per character. Use `/api/rigs` and `/rig-lab` to inspect motion **diagnostics**. Existing approved portraits are flattened; production-quality animated characters still require transparent registered body segments, complete face/eye/mouth layers, mesh deformation, lip-sync and fidelity review. Do not label these debug skeletons as finished characters.


### A1.1 — Articulated Motion Studio

Open `/puppet-lab` to manipulate actual joint transforms with blended emotions, 2-bone arm IK, arm gestures, walk cycles, gaze, blinks, talking-mouth visemes and hair secondary motion for ten existing rigs. The editor allows **local-only** upload and registration of individually painted RGBA sprite parts, exporting per-bone origins and scale. The approved illustrations remain flattened references: the production quality character-art gate is **not passed**. No portraits are presented as independently animated limbs.

Test with `node --test orchestrator/tests/puppet_engine.test.mjs`. See the development PR for exact acceptance criteria.
