# EXODIA Tower — Permanent Multi-Agent Development Contract

**Contract:** `exodia.multi-agent-development/v1`  
**Owner directive:** 2026-11-04  
**Integration branch:** `development/exodia-foundation`  
**Protected release boundary:** draft PR #1 targets `main` and must remain draft and unmerged without express owner approval.

This is an operational repository contract, not evidence that GitHub branch protection is enabled. The owner retains the permanent Windows checkout at `C:\Users\TFBOSS\Documents\GitHub\exodia-tower`. Neither developer may reset, clean, replace, or mutate that checkout without verifying its state and the owner's intent. This document does **not** authorize a production-art release, provider credential use, or a `main` merge.

## 1. Developers, paths, and ownership

| Developer | Primary responsibility | Default feature branch | Typical paths |
|---|---|---|---|
| Cursor Agent | ChatGPT/Gemini/DeepSeek Chronos browser automation; official API transports; custom/private instructions; provider reliability and provider-specific tests | `feature/cursor/<ticket>-<topic>` | `orchestrator/app/automation/`, provider-specific adapters/tests, provider API implementation |
| ChatGPT Lead Developer | Architecture, companion orchestration, task workflows, frontend consistency, art integration, integration audit and acceptance | `feature/lead/<ticket>-<topic>` | `orchestrator/app/companions/`, `orchestrator/frontend/`, portrait pipeline/docs, cross-system tests |
| Integration owner | Reviewed merges, cross-provider acceptance, release decision | `development/exodia-foundation` | Integrates PRs only after verification |

**Shared integration surfaces:** `orchestrator/app/api/server.py`, `orchestrator/app/automation/provider_catalog.py`, `orchestrator/app/operations/inbox.py`, `orchestrator/frontend/albedo_command.*`, `orchestrator/frontend/exodia_workstations.html`, `orchestrator/app/config.py`, and schemas/contract tests. These require reviewing current upstream changes and coordinating interfaces with the other developer before editing. Code ownership is a *review responsibility*, not permission to discard someone else's work. No blanket overwrite, force push, destructive reset, unreviewed auto-merge, or silent migration.

## 2. Mandatory preflight per work item

1. Read the latest explicit owner directive, this contract, `docs/EXODIA_PROVIDER_INTEGRATION_CONTRACT.md`, `SKILL.md`, and any stricter art/governance specification relevant to the changed files.
2. In the **specific checkout**, run `git status --porcelain=v1`, `git branch --show-current`, `git rev-parse HEAD`, `git remote -v`, then `git fetch origin`. Inspect `git rev-parse origin/development/exodia-foundation` and `git log --oneline --decorate -10`. Preserve any unstaged or untracked work; do not silently stash or discard it.
3. Check current open PRs and diff against the target branch. Find whether Cursor or the lead developer already implemented the requested behavior. Read recent modifications in shared files. Establish a conflict/ownership note in the feature PR.
4. Create a **new feature branch from the verified integration SHA** in its own Git worktree. Never use the owner's permanent checkout as a disposable test sandbox. Keep each feature branch synchronized with the integration branch using a reviewed merge or rebase on the *feature branch only*. Never rewrite published integration history.
5. Record source commit, changed paths, test commands, real-vs-mocked evidence and accepted asset SHA locks in the PR. Keep commits small, focused, reversible, and free of credentials.

## 3. Recommended Windows worktrees and service isolation

In PowerShell, after verifying that the permanent checkout is clean or safely preserving its existing changes:

```powershell
$Repo = 'C:\Users\TFBOSS\Documents\GitHub\exodia-tower'
git -C $Repo status --short
git -C $Repo fetch origin
$Base = git -C $Repo rev-parse origin/development/exodia-foundation
# Substitute a unique ticket/feature slug for each new piece of work.
git -C $Repo worktree add -b feature/lead/EXODIA-001-contracts 'C:\Users\TFBOSS\Documents\GitHub\exodia-tower-lead-EXODIA-001' $Base
# Cursor uses its own different feature/cursor/<ticket>-<topic> worktree.
```

Do **not** point two simultaneous servers to the same worktree. By default, SQLite lives in `orchestrator/app_data/`, saved model instructions and signed-in Chromium sessions in `orchestrator/session_data/`, browser debug images in `orchestrator/debug_snapshots/`; these paths resolve inside each worktree. Never copy signed-in profiles or secrets between worktrees. Install per-worktree environments and make sure `orchestrator/.env` is local and ignored. `HOST` must remain `127.0.0.1` or `localhost`.

| Environment | Worktree | Example port | Database and sessions |
|---|---|---:|---|
| Stable integrated application | Owner's `exodia-tower` | `8765` | Existing local data; **never replace** |
| Cursor provider experiment | Separate `exodia-tower-cursor-*` | `8766` | Separate ignored `app_data/`, `session_data/` |
| Lead/frontend preview | Separate `exodia-tower-lead-*` | `8767` | Separate ignored `app_data/`, `session_data/` |

Within the respective worktree's `orchestrator` directory, set `$env:HOST='127.0.0.1'; $env:PORT='8766'` (or `8767`) before `python main.py`. Open the port corresponding to that worktree. On Windows, don't reuse a Chromium user-data directory while another process has it open. Integration tests should use temporary SQLite paths/fake browser objects; authenticated provider E2E is separate and requires the owner's legitimate, authorized session. Do not share personal accounts, cookies, user profiles, API keys, or developer tokens via artifacts or commits.

## 4. PR-only delivery and integration protocol

- Every feature PR **targets `development/exodia-foundation`** and starts from a named `feature/cursor/...` or `feature/lead/...` branch. PR #1 is an independent draft release PR targeting `main`; it is **not** a feature PR target.
- Include: upstream base SHA; reason/scope; ownership notice; changed-file list; database compatibility; sample API payload/error; mock/contract tests; real application/browser evidence when relevant; before/after screenshots only if actually captured; full test/CI run URL; and rollback approach.
- Shared-file edits require cross-agent review of the current implementation, then integration-owner approval. Cursor validates provider behavior; the lead validates frontend/orchestration and end-to-end task ownership. Both protect each other's tested functionality.
- The integration owner confirms the feature PR is up to date with the **latest** integration HEAD, resolves conflict hunks deliberately, checks approved 29 Albedo SHA pairs, runs relevant regression tests and merges the verified PR into `development/exodia-foundation`. No direct feature pushes to integration, and never merge integration into `main` without separate owner authorization.
- When the integration branch advances during review, synchronize the feature branch and rerun impacted tests. Do not treat CI from an older SHA as acceptance evidence.
- Revert regression with an additive, reviewed revert commit/PR rather than destructive history rewriting. Maintain preserved tags and SHA-bound evidence.

## 5. Required acceptance matrix

| Level | Proves | Does not prove |
|---|---|---|
| Static/unit | Stable IDs, transport selection, JSON validation, mock success/error/cancel, private instruction filtering, migration safety | Live provider access |
| FastAPI integration | Actual routes, task persistence/restart handling, UI build metadata, local model routing, 33 art URLs and hashes | Signed-in website compatibility |
| Browser mock + Chromium UI | Correct DOM and user controls at desktop/mobile widths, no stale UI or fake completion badges | Authenticated provider output reliability |
| Authenticated E2E | User-authorized send/receive in real provider session, task-linked answers/media, timing/diagnostic evidence | Unlimited access or future API readiness |
| GitHub CI and integration replay | Correct changed SHA and reproducible headless build | Owner approval of native portrait masters, production release |

Compare ChatGPT, Gemini and DeepSeek with the same authorized text-only prompts: record provider ID, transport, task ID, transition sequence, response match/completeness, `metrics` fields, errors, media and actual total time. Label synthetic timing as **mocked**. Do not manually copy consumer outputs into tests or claim automated extraction until a controlled authenticated run has passed.

## 6. GitHub governance configuration (owner/admin enforcement)

`/.github/CODEOWNERS` requests the repository owner's review. The PR template lists evidence. **Neither file by itself blocks pushes.** At the time of adoption the existing `development/exodia-foundation` branch is reported as **unprotected** by GitHub; the current GitHub connector has no administration mutation capability. The integration owner or a GitHub administrator must enable an actual branch ruleset for `development/exodia-foundation` requiring pull requests, at least one human/code-owner review and the project CI/contract/visual checks. Disallow force pushes and deletions; restrict bypass permissions; do not require a specific CI check name until it is observed running reliably. Apply a separate stricter rule to `main` and retain PR #1 in draft.

Do not call these controls enforced until GitHub reports the protection/ruleset as active. Workflow checks cannot stop a user with direct write access from bypassing PR review without an enforced server-side rule.

## 7. Current protected baseline and follow-ups

The first governed feature should restore the two `test_zero_api.py` typing-delay assertions after the Cursor `type_composer_text()` optimization: the implementation deliberately emits keyboard events with `delay=0`, whereas the old tests expect `10`. Preserve event semantics, multiline-safe typing and provider DOM behavior; do not make the browser artificially slower just to satisfy old assertions. The base for this contract was `96a85f46e6bebfdfd69500cc3a10ac7447d75ab5`, where the four Albedo review replacements are already committed and indexed and native release remains disabled. Verify the real current SHA on every new task.

**Non-negotiable:** 29 protected Albedo original/review SHA pairs unchanged, all 33 review states valid; 4 low-resolution development-only corrections do not imply native certification. No change to `release.enabled` without an explicit SHA-bound owner decision.
