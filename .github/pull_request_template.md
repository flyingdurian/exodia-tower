## EXODIA integration checklist

- [ ] Target branch is `development/exodia-foundation`; PR #1 to `main` remains draft/unmerged.
- [ ] Feature branch has a distinct `feature/cursor/...` or `feature/lead/...` working tree.
- [ ] Latest integration baseline SHA: `____________________` (checked before this change).
- [ ] Worktree status, recent upstream changes and existing PRs reviewed; no personal data/secrets added.
- [ ] Affected files and owners listed; shared-file changes reviewed across Cursor and Lead Developer.
- [ ] Stable provider IDs, transport selection, task persistence, stored prompt and private instructions retained.
- [ ] 29 protected Albedo pairs unchanged; production release not enabled (if art-related).
- [ ] Mock/contract tests, local API integration tests, Node and Python regressions provided with results.
- [ ] Real signed-in provider E2E clearly separated from fake browser tests; no invented sign-in evidence.
- [ ] Real desktop/mobile Chromium captured where visual changes warrant it; explain any blocker.
- [ ] Feature branch synchronized with latest integration before merge; current-head CI links attached.
- [ ] Safe rollback/revert plan and any unresolved risk documented.

**Integration owner:** verify, review, and merge only after gates. Do not bypass `main` release or portrait-production approval.
