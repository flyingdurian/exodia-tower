# EXODIA Tower — Albedo Room Behavior Phase 3 (stacked on PR #10)

This change depends on PR #10’s real command-dashboard chibi floor. It must be merged only after PR #10 is independently reviewed and merged, then synchronized against its exact integration commit. Provider transports and authentication remain Cursor-owned and unchanged. No non-Albedo artwork is authorized.

## Actual task-state routing

A narrow event projection from the command dashboard includes only public `taskId`, `agentId`, `provider`, lifecycle `state`, and `updatedAt`. The dedicated room behavior reducer translates states into movement cues and target zones:

- Draft/idle/cancelled → Home (cancellation is local; remote provider may still run)
- Queued/opening/cooldown → Terminal, approaching the workstation
- Researching/typing/submitting/running/rendering_media → Terminal, working
- Waiting for reply/operator → Waiting, holding near station
- Answered → Results
- Failed → Recovery

The reducer accepts an operator-selected older historical task when the *task ID changes*, but rejects an older `updatedAt` event for the *same task*, preventing late polls from undoing a newer cancellation. The task owner and selected companion must both be Albedo (`kiko`) to show the actor. Switching to another companion hides Albedo immediately, without erasing selected task history. Unknown states fail safe to Home.

The floor status cue is plain text only. It is derived from the fixed state vocabulary; prompts, answers, private instructions and browser profiles do not enter this module. No remote stop guarantee or provider authentication can be inferred from these events.

The runtime still has only technical heading/position markers and no approved 40-frame chibi art. `release.enabled=false` remains unchanged. Portrait production certification is a separate gate.

**Validation:** Node reducer lifecycle, privacy, stale-update and companion-selection tests; full FastAPI/Chromium frontend simulation on PR CI. Authenticated real-provider E2E remains a separate run in the owner’s own signed-in environment.
