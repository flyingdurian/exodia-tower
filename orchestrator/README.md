# Exodia Tower — Local Orchestrator v0.3

**Authoritative project:** https://github.com/flyingdurian/exodia-tower

The approved V0.2 backend and artwork are preserved. The current dashboard is the redesigned technology-first Exodia operations interface. Nova is the tenth specialist for YouTube, TikTok and Instagram editorial planning. **Navigation projections are not articulated character rigs.** No publishing adapters have been authorized or connected.

Run: `pip install -r requirements.txt` then `python main.py`. Browse `http://127.0.0.1:8765`. Your `.env` is local and must stay uncommitted.

Local workflow API: `GET /api/social/status`, `GET /api/social/jobs`, `POST /api/social/jobs`, `PATCH /api/social/jobs/{id}`, `POST /api/social/jobs/{id}/advance`, `POST /api/social/jobs/{id}/approve`, `GET /api/social/jobs/{id}/brief`. Mutations require `X-Exodia-Client: exodia-dashboard` in the localhost environment. These measures are not sufficient for public exposure.

For more details and release limitations see the repository root README and `/docs/`.
