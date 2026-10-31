# ✦ The Command Tower — local prototype v0.1

A local-first, chibi-themed **operator dashboard and routing foundation** for GitHub, Etsy, YouTube and Gmail. **Kiko** has four animated operating states. This is a functioning scaffold, not a production-ready autonomous agent or a promise of unlimited access to commercial AI chat services.

## Quick start

Python 3.11+ is recommended. In **PowerShell** or another terminal:

```bash
cd orchestrator
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env  # PowerShell: Copy-Item .env.example .env
python main.py
```

Open **http://127.0.0.1:8765** on the same machine. Runs with **no credentials** in local mode. Click **Index workspace** to index accessible source and documents; search with the **Local** route. Sample questions: `check system status`, `search indexed documentation`, `check GitHub repo stats`.

Run automated tests:

```bash
python -m pip install pytest
python -m pytest -q
```

### Configure services

Edit `.env` based on `.env.example`:

| Provider | Configuration | MVP capability |
| --- | --- | --- |
| GitHub | `GITHUB_TOKEN`, `GITHUB_REPO=owner/name` | Repository metadata and issue count |
| Etsy | `ETSY_API_KEY`, `ETSY_ACCESS_TOKEN`, `ETSY_SHOP_ID` | Shop metadata and active listing count |
| YouTube | `YOUTUBE_ACCESS_TOKEN` (OAuth Analytics scope) | Recent 28-day views, watch time and subscribers gained |
| Gmail | `GMAIL_ACCESS_TOKEN` (OAuth Gmail read-only scope) | Unread estimate and sample message IDs, **no email bodies** |
| Reasoning API | `OPENAI_API_KEY`, `OPENAI_MODEL` | Text answers via the OpenAI Responses API |

**MCP support:** the main dashboard calls the same read-only REST adapters directly. An **optional genuine MCP stdio server** is provided at `app/mcp/server.py`, exposing the four provider checks plus local archive search to an MCP-compatible client. Install and run:

```bash
python -m pip install -r requirements-mcp.txt
python -m app.mcp.server
```

The separate process communicates over stdin/stdout; an MCP client must launch it. This project does *not yet* include OAuth sign-in, secure token-refresh workflows, GitHub PR writes, Etsy inventory mutations, Gmail draft creation, or YouTube upload controls. User-granted tokens expire; use appropriately scoped credentials and rotate them. Setup is not synonymous with verified access: press the ↗ icon on a network card to test.

**Etsy:** Your app must use a properly configured Etsy developer key and OAuth grant. Token/key headers and rate limits are documented at [Etsy developer docs](https://developers.etsy.com/documentation/). Never bypass quotas.

**YouTube:** channel Analytics requires user authorization with the [Analytics report scopes](https://developers.google.com/youtube/analytics/reference/reports/query); the report is not a real-time subscriber counter.

### Local vector search

Default: SQLite FTS5, no model downloads. Optional hybrid dense search uses `sqlite-vec` (the actively developed successor to deprecated `sqlite-vss`) plus a local sentence-transformer:

```bash
python -m pip install -r requirements-vector.txt
# set DENSE_SEARCH=true in .env, then restart
```

The first dense-enabled index may download a `sentence-transformers/all-MiniLM-L6-v2` model; use only when you agree to that download. Dense indexing may be slower; FTS5-only works without it. Vector data is stored in `app_data/command_tower.sqlite`. Local document search results are **extracts**, not hallucinated summaries. The exact-answer cache is intentionally limited to RAG search and is invalidated on reindex.

### Browser-assisted session (optional)

To use the read-only Playwright inspection channel, install Chromium:

```bash
python -m playwright install chromium
```

Set `BROWSER_ENABLED=true`, `BROWSER_ALLOWED_HOSTS=example.com` and `BROWSER_READ_URL=https://example.com/your-page` in `.env`. Browser mode opens the **allowlisted page** in a persistent desktop Chromium profile and returns a limited body-text snapshot. Login can be completed manually in the open window when needed. State is saved in `session_data/approved_browser/` (gitignored). On navigation/DOM errors, the tool may save a screenshot in `debug_snapshots/` and report a fallback. Screenshots can contain sensitive content: review before sharing.

No browser-fingerprint spoofing, anti-bot evasion, CAPTCHAs, or authentication-wall bypass. **No automatic scraping or message submission on consumer AI chat websites.** Paid chat subscriptions are **not** assumed to authorize programmatic access or unlimited inference; respect each service's terms and limits. The browser route only reads permitted pages. If it fails, the router switches to the configured API reasoning channel, or provides an honest local error if no API credentials exist.

### What each of the eight pillars does in this build

1. **Dual-Blade Router:** deterministic rule-based routing to local search, four official REST adapters, optional API reasoning, or supervised browser page reading; error-state fallback.
2. **Scroll of Memories:** system persona and untrusted user-state, metric, and knowledge blocks in `app/prompts/builder.py`; an optional `USER_STATE` value supplied from `.env`, and trusted local snippets / recent non-sensitive provider metrics in reasoning prompts.
3. **Crystal Archives:** FTS5 document search, optional dense local vectors, source snippets.
4. **Relic Inventory:** read-only REST adapters and an optional MCP stdio tool server; writing tools are future milestones.
5. **Master Key Vault:** environment secrets, gitignored profile and debug directories; OS keychain and token encryption are not yet implemented.
6. **Browser Assistance:** HTTPS origin allowlist, persistent sessions, captures on failure. Intentionally **no stealth**.
7. **Speedrunner Cache:** TTL exact-answer cache for RAG only; no cached live finance/mail data.
8. **Strategy Map:** FastAPI/WebSocket real-time event feed, stateful Kiko, result details and route/latency display. Snapshot file viewer and historical persistence are future milestones.

### Local security boundaries

- HTTP only binds to loopback by default; server rejects public binding. No remote authentication or multi-user access.
- `.env`, cookie profiles, local DB, and debug captures are ignored by Git. Protect local computer access; tokens are not encrypted at rest by this prototype.
- The local indexer ignores hidden files, build folders and saved session data; it never uploads them through the local search route.
- External service content is **untrusted**. Do not treat retrieved text as instructions.
- **Read-only integrations** are deliberate until a permission/approval/confirmation layer exists.
- Do not deploy as-is to a cloud server or shared LAN.

## Folder map

```text
orchestrator/
  app/
    api/server.py             # HTTP endpoints and /ws/events
    automation/stealth.py     # safe browser assistance (legacy spec path)
    core/{classifier,router,cache}.py
    mcp/clients.py            # REST provider adapters
    mcp/server.py             # optional official MCP stdio tool server
    prompts/builder.py
    rag/engine.py
    security/vault.py
    monitoring/logger.py
  frontend/{index.html,styles.css,app.js}
  app_data/                  # local DB (gitignored)
  session_data/              # browser credentials (gitignored)
  debug_snapshots/           # local error snapshots (gitignored)
  tests/test_engine.py
  main.py
```

## Next gates

**Gate 2:** full OAuth PKCE or native service SDK authorization and refresh (no raw manual tokens), encrypted keychain integration, connector health checks, rate-limit backoff. **Gate 3:** deeper MCP tool permissions, human approvals and audit log (basic read-only MCP stdio tools are already included). **Gate 4:** richer local reasoning model, proper semantic-cache evaluation, background jobs, dashboard screenshot inspection and replay tests. **Gate 5:** packaging, OS integration and authentication for any remote access.

---

## Companion Studio · animation integration (v0.2)

Open **http://127.0.0.1:8765/companions**. The original dashboard also contains a Companion Studio shortcut and now uses the approved Kiko Prime illustration instead of the CSS-only avatar.

**Assets provided:** all nine approved portrait illustrations converted to high-quality WebP, nine thumbnail portraits, one cast illustration and **nine 4-second silent H.264 ambient motion loops** (608 × 760, 12 fps). All clips are local, with no paid generation credits used. The idle loops feature seamless camera movement, gently drifting light particles and glow pulses; these are *not articulated face or body animations*. The 2.5D browser renderer adds pointer parallax, rotating halos, procedural particles, lighting sweeps and distinctive task-mode reactions around the original artwork.

**The nine companions:** Kiko Prime (Overseer), Riven (Vanguard / Router), Mira (Scholar / Prompt Scribe), Lyra (Archivist), Pip (Artificer / MCP), Aurelia (Guardian / Security), Nyx (Scout / Browser), Mochi (Support / Cache), and Orion (Tactician / Monitoring). Each has a biography, unique visual identity and dialog for six preview states: `idle`, `thinking`, `working`, `success`, `rest`, and `alert`. These are visual roles linked to existing router operations, **not nine separately running LLMs**.

**Live integration:** the backend `CompanionDirector` sends sanitized state events over the existing `/ws/events` channel. `/api/ask` changes the relevant specialist and Kiko to `working`, then `success`, `rest` or `alert` according to the genuine result. Indexing activates Lyra; network checks activate Pip; clearing the cache activates Mochi. The Studio receives real events and also has manual preview controls. Preview reactions do not run external tools.

**API:**

- `GET /api/companions` returns the roster, latest UI states, and available video-loop file URLs.
- `POST /api/companions/{agent_id}/react` with `{"state":"thinking"}` triggers only a local visual reaction/event. Invalid IDs or states return HTTP 422.
- `GET /companions` serves the interactive studio.

**Media replacement contract:** for higher-quality character animation, add your generated or rigged `.webm`/`.mp4` to `frontend/companions/clips/<agent_id>/<state>.webm`, where `agent_id` is one of `kiko`, `router`, `memory`, `archives`, `inventory`, `vault`, `ninja`, `cache`, or `strategy` and `state` is `idle`, `thinking`, `working`, `success`, `rest`, or `alert`. Restart the server to rediscover new clips. Each state should loop naturally, preserve the approved character design, and return to a matching resting pose. Keep the same aspect ratio, framing, costume, hairstyle and face across every state. Use footage without baked-in text for production UI; labels should remain live DOM text.

**Quality gate before calling these fully animated agents:** asset separation into foreground/midground/background, isolated and registered face/eye/mouth/hand components, intentional blinking and speaking/gesture performances, clean state-to-state continuity, and no image-text warping. The present 2.5D loops intentionally do not claim this gate is complete.

**Performance:** the default high-fidelity stage runs on current desktop browsers using ordinary canvas, video and CSS, without a WebGL requirement. A reduced-motion toggle freezes decorative animation and stops video loops; OS-level `prefers-reduced-motion` is respected. All media is served locally. The design works without API credentials. The fullscreen Studio also has arrow-key companion navigation and number keys 1–6 for reactions.
