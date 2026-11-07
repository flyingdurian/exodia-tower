# ALBEDO LIVE COMMAND STAGE — V1 DEVELOPMENT CHECKPOINT

## Accepted design and implemented controls

The owner accepted the Albedo command-center visual direction (celestial navy, violet, crystalline gold, holographic response screen, dedicated operator column). The current page at `/` is implemented as `frontend/albedo_command.html`, `albedo_command.css`, and `albedo_command.js`. Previous UI remains under `/operations-legacy`.

The public-facing companion is now **Albedo**, while the internal legacy ID **kiko** is intentionally preserved to avoid breaking files, task ownership, stored references, and simulation keys.

### Working
- Albedo main view includes real multi-frame animated idle playback (existing 4-second Kiko source clip), moving celestial VFX, phase-aware stage states, and interactive emotion-state controls.
- Create Task routes to existing automatic Gemini, local Ollama, and custom browser implementations, with assigned agent and task IDs retained.
- Event-linked states: opening/typing/submitting/researching -> processing, running -> thinking, waiting_for_reply -> waiting, answered -> happy/excited/proud, failed -> failed/frustrated. Idle/sleeping previews.
- Holographic response display shows live task status, prompt, results, imported images and source links. A compact weather or TSLA card is derived **only from actual provider text**, never generated with fabricated prices. Such cards are explicitly marked as not independently verified.
- Safe model-text renderer supports headings, paragraphs, inline bold/code/link, lists, tables, code blocks, and collapses 1D/5D/1M/6M/YTD/1Y/5Y/MAX labels into chips without injected model HTML.
- Separate operator column includes model selection, agent assignment, task dispatch, mission history, browser session launch and diagnostics.
- Responsive sizing and reduced-motion support.

### NOT IMPLEMENTED / visual acceptance blockers
- **Not a production-quality skeletal Albedo**. The existing idle.mp4 contains 48 video frames but predominantly subtle motion; the original approved art remains flattened. Existing source cutouts are engineering QA and explicitly not accepted full-body performances. Animated stage VFX and state labels do not equate to facial/lip/body rigging.
- No new video animations were produced for emotional key states in this checkpoint. There is currently one idle video; individual emotional performance clips must be authored/approved before the runtime switches videos for those states.
- Stock and weather results are extracted from the text provided by the selected model. This is not a licensed finance quote or weather feed, and source/time must be independently checked for high-stakes decisions.
- No mocked live stock prices, model/provider operational percentages, fabricated charts, or fake weather observations.
- Browser tests and CI do not prove visual parity with the owner's approved AI concept art.

### Next art pipeline requirements
1. Obtain and register one consistent, artwork-approved and transparent, deformation-ready Albedo character master (hidden body sections included; no environmental background baked into limbs).
2. Produce genuine multi-frame performance footage or an independently deformable 3D/Live2D skeletal rig, including 10 emotion states and body/face controls.
3. Author an animation-state manifest for idle, sleep, process, wait, think, failure, frustration, happy, excited, proud, including durations and loop/transition flags; render with native video/rigger playback, not moving still images.
4. Visual QA: play all states, verify animation frame changes, lip/eye/articulation, clipping, identity fidelity, transitions, no placeholder wiggle, and accessible reduced-motion alternative.
5. Source-fidelity check against the user's Albedo benchmark before production acceptance.

This milestone is an actual functional dashboard and motion-stage implementation but **does not satisfy** the owner's final fully-rigged animated avatar acceptance gate.
