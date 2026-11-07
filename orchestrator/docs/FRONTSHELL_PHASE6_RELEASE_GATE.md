# EXODIA Frontshell — Phase 6 Technical Release Gate

This document records the **technical release candidate**, not final art or
production-provider authentication. Development branch merges are not promotion
to the Windows operator's installed build.

## Automated acceptance
- All Python tests and Node UI contracts must pass at the exact merge head.
- Chromium screenshots and layout/no-overflow checks must cover desktop,
  tablet and narrow mobile views, with separate reduced-motion Chibi proof.
- Each provider task card is an observed local read model; the single
  /ws/events socket is **not** a verified ChatGPT/Gemini/DeepSeek/Ollama socket.
- Local reconnect is backoff-bounded, polls pause when offline/hidden,
  errors cannot silently mark an old snapshot fresh.
- Operator palette and terminal allowlisted; no shell, arbitrary provider
  dispatch, credentials, prompt or response bodies are written to browser
  storage or diagnostics.
- Chibi movement controller is deterministic; full 40 independent directional
  sprite PNGs still require provenance, geometry, SHA and owner approval.

## External gates that CI does not certify
- **Owner Windows acceptance:** manual Windows application launch and navigation
  smoke test remains pending until the operator provides local evidence.
- **Production artwork:** Chibi 40-frame owner release remains disabled.
- **Provider sessions:** local event transport does not assert remote login
  or authenticated vendor control.

No new backend route, SQLite migration, provider transport or art promotion
is authorized by this release-check milestone.
