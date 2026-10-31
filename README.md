# Exodia Tower

A local-first AI operations system with specialist companions, live workflow instrumentation, and an approval-gated Social Media Division for **YouTube, TikTok and Instagram**.

**Status:** V0.3 development checkpoint. The uploaded Command Tower V0.2 code and original nine approved portrait assets are preserved under `orchestrator/`. Exodia's new interface is live in code; character projections navigate the operations floor, but **there are no completed articulated rigs**. Nova is the tenth registered specialist; her approved illustration and rig are pending.

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
