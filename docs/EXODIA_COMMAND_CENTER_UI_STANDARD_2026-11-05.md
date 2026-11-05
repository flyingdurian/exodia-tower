# EXODIA TOWER — Command Center UI / UX standard (owner visual target, 2026-11-05)

**Status:** design and frontend behavior contract; this document and the supplied visual mockup do not certify features, merged PRs, authenticated providers, or native artwork.

## Canonical public frontshell

- Three-zone command center: prominent central operations floor with actual Albedo task-bound movement status; adjacent compact, content-sized response terminal and mission feed; modular controls and provider telemetry on the side.
- Cinematic deep-navy, cyan and violet accents, distinct panels, readable statuses, responsive desktop/mobile ordering. Preserve existing FastAPI/SQLite/task routing/portrait artwork identity and browser provider flows, never start a disconnected demo.
- The operations floor's 40 frame slots remain **missing artwork**; until independently verified, it shows a conspicuous technical marker, NOT an invented animated chibi. Do not use montage crops.
- The response panel auto-sizes for small output and scrolls internally for long content; keyboard focus and cancellation must remain accessible.
- History search and provider status are public functionality. The three official API catalog rows remain explicitly **Not configured** until real clients/configuration exist.

## Developer / Debug boundary

The collapsed-by-default, keyboard-accessible **Developer / Debug** drawer holds build metadata, SHA/branch diagnostics, internal QA navigation, exception diagnostics, and manual chibi movement test controls. Never show raw CI rows, head SHAs, checklist counts or synthetic performance metrics as normal mission telemetry. Real task state, real provider names, user-safe timing and result cues remain in the command screen.

The command-center reference mockup supplied by the owner shows target proportions, colors and panel organization. Its **Merged**, **Verified** and **Ready** labels are illustrative, NOT evidence; current protected GitHub PR and authenticated provider checks remain authoritative. The mockup's silver-haired male Riven is NOT the canonical character identity: Riven retains dark twin-tail hair, red accents/eyes, and black-red-gold twin-blade armor per the art contract. No production-portrait status is inferred from UI illustration.

## Engineering gates

Perform exact-head Foundation/Portrait CI, real FastAPI/Chromium desktop + mobile, default developer-drawer closed, keyboard/debug-toggle accessibility, chibi zone test event continuity, no horizontal overflow, short/long response sizing, and protected 33-portrait SHA locks. This polish is isolated on a stacked feature branch based on the draft PR #15 QA preview. It is NOT an authorization to merge PR #15 or to skip independent review of #10 → #11 → #12. Preserve Riven and other fleet release locks.

## Desktop spatial implementation (QA refinement)

At desktop widths of 1181px and above, the content-size response terminal and quick actions occupy the left support column, Albedo's real task-driven operations floor is the broad **center** column, and operator controls, history and provider status occupy the right column. The existing DOM order is preserved to avoid moving runtime elements and event listeners; the responsive/mobile layout stays in its previous documented DOM sequence. Browser QA explicitly verifies the floor is centered and wider than the response column.
