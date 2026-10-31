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
