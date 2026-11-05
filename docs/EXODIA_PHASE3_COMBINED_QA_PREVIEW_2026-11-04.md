# EXODIA Phase 3 combined QA preview — NOT an integration or production release

Authoritative inputs at initial assembly:
- PR #10 chibi scaffold: `bba478b764b102aa6936f8cbf613b22f75495025`.
- PR #12 room behavior (stacked on #10): `a6c6783a2abea34a3cb0180a3b2f97b5edb8f269`.
- PR #11 history/provider visibility: `1d982f9512545fac42a524c3a944ab07b01454c2`.
- Protected development baseline: `e2398b7ef74bc183ad9f747f836d11b921bc041e`.

This isolated preview preserves the existing app, Cursor-owned provider transports, SQLite/task records, original feature PR heads, and production artwork locks. It does **not** merge into protected integration or main.

Shared conflict-resolution notes:
- `albedo_command.js`: retain task-driven chibi status, runtime events, and selected-companion/model listeners while adding mission-history filters, history descriptions, and honest API statuses.
- `albedo_command.html`: preserve the chibi boot and status panels and add history search/filter controls and API-status rows.
- `albedo_command.css`: add history filters without deleting operations/chibi styling.
- `.github/workflows/ci.yml`: retain all chibi/room Node/Chromium tests while adding mission-history Node tests; Python full suite includes new provider-contract test.
- `test_gate3_33_browser.py`: retain existing browser cases and incorporate history search/provider configuration checks.

**Safety gate:** Draft review/QA proof only. Do not merge this preview into `development/exodia-foundation`. Review/merge original PRs #10, then re-synchronized #11, then re-synchronized #12 through required independent approval, exact-head CI and desktop/mobile visual checks. PR #1 remains draft/unmerged into main. CI mocks are not live authenticated provider proof. Riven source art and native release remain pending.
