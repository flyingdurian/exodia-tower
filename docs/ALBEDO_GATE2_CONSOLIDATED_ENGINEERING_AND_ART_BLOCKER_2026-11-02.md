# EXODIA Tower — Gate 2 consolidated engineering and artwork checkpoint

**Date:** 2026-11-02 | **Branch:** `development/exodia-foundation`

## Actual disposition

- Five authoritative original 1122×1402 Albedo concepts: **5/5 SHA-verified** (from user-provided ZIP).
- Numerical eye/shoulder **midpoints** on five resampled review previews: 5/5 within ±2px, provisional only.
- Complete fixed-camera geometry with separate L/R shoulders, head width ±4px, center and coherent perspective: **not passed**.
- Native independently authored portrait masters: **0/5**.
- Production registry approvals: **0/33**.
- Remaining 28 generated artwork states: **0/28**.
- `release.enabled`: **false**. Draft PR #1 stays open, no merge.

The earlier conversion of 1122×1402 concept artwork into 1536×1920 review previews **does not create genuine native image detail**. The review images are not production candidates.

## Why uniform alignment is insufficient

For a single rigidly scaled portrait the invariant source ratio is:

`head_width / (shoulder_midpoint_y - eye_midpoint_y)`

The canonical output ratio is `614.4/(980-633.6)`. Changing translation cannot fix this ratio. The model-estimated original anatomical landmarks show incompatible required scale intervals for **Working, Explaining, Monitoring** (see
`assets/review/albedo_core5/gate2_rigid_geometry_feasibility.json`). The Idle and true extended-finger Pointing originals are closer in the scale feasibility model, but even their current review-preview head widths miss ±4px. Anatomical source landmark estimates require human confirmation.

The actual review-preview output head widths, measured relative to the locked head-width annotation model, are:

| State | Eye midpoint y | Shoulder midpoint y | Approx head width | Head target ±4 | Native |
|---|---:|---:|---:|---|---|
| Idle | 633.672 | 980.5 | 587.93 | FAIL | NO |
| Working | 633.659 | 980.0 | 692.98 | FAIL | NO |
| Explaining | 633.613 | 979.5 | 649.28 | FAIL | NO |
| Monitoring | 633.642 | 980.0 | 635.65 | FAIL | NO |
| Pointing | 633.676 | 980.0 | 592.25 | FAIL | NO |

The pixel scanner's shoulders are candidate horizontal gradients, not guaranteed anatomical contours: further human-verified L/R contour inspection and independently authored native artwork are required.

## Real application integration

The existing FastAPI app now serves `/core5-review` and includes a link from the live command center. It does not replace any Gemini, ChatGPT manual-result workflow, the local task processing or the Operations Deck.

The owner-local review uploader accepts **the exact Gate 1 visual review ZIP** containing `originals/` and `aligned_previews/`. It verifies the correct five independently sourced original hashes and the five committed SHA-256 output hashes before placing review-only images under `orchestrator/app_data/core5_review`. It rejects unsafe/duplicated ZIP paths, oversized members, missing art, wrong dimensions, corrupted bytes and manifest tampering. It cannot edit production registry, owner approvals or 28-state queue.

After running the normal Exodia Tower launcher, open `/core5-review`, choose `EXODIA_CORE5_GATE1_REAL_SOURCE_VISUAL_REVIEW_2026-11-02.zip` (or the Gate 2 ZIP containing the same originals/previews), and click **Import 5 verified previews**. Five states are then selectable with SHA-checked browser loading, fixed 4:5 image stage, 260ms crossfades, measured values, visual risk disclaimer, desktop/mobile responsive layout and optional **read-only** live task state observation.

Until importing the exact ZIP, the workbench correctly shows all five states as unavailable—**never old proxy artwork**. The system automatically reports `production_masters_loaded=0`, `generated_28_states=0`, and `release_enabled=false`.

## Security and negative tests

- `orchestrator/tools/core5_geometry_gate.py`: strict geometric feasibility and reviewed left/right anatomical checks, head width, center and asymmetry.
- `orchestrator/tools/core5_native_candidate_gate.py`: candidate binary checks, original/output hashes, size (no upscale), transform metadata, distinct action tags, near-image clones/color-shift detection, provenance and owner gate.
- `orchestrator/tools/audit_portrait_anchors.py`: native candidates cannot PASS without enhanced head geometry/actual L/R pixel points and SHA-bound owner-reviewed annotations. Prior valid synthetic midpoint checks still do not release production.
- `orchestrator/app/companions/core5_review_assets.py`: local SHA-verified five-review importer, no registry writes.
- `orchestrator/frontend/core5_review_workbench.html` and `.mjs`: real application five-state UI.
- `orchestrator/tests/test_core5_gate2.py`, `test_core5_native_candidates.py`, `test_core5_browser.py`, expanded `test_audit_portrait_anchors.py`: import negative cases, clone detection, false shoulder, head size, invalid approval, source-provenance and actual Chromium desktop/mobile behavior.

The Chromium test images are **synthetic QA shapes**, never Albedo art quality evidence. Real per-state original/preview visual evidence is supplied in the separate downloadable review ZIP.

## Native artwork blocker and rendering attempts

Two built-in image-generation requests produced combined presentation dashboard illustrations with invented numerical PASS/checksum text rather than five separate standalone Albedo paintings. They were quarantined and **not registered**; no numbers from those images entered the telemetry or GitHub.

The connected third-party generator reported **2 available credits**. Preflight quotes for appropriate 2K image generation were approximately **2 credits per image**, while the required coherent five-state batch would need at least five such separate jobs, each with the original reference and its own verifiable source output. Locally extracted images could not be uploaded through the sandbox's disabled external network. Thus no native candidate source bytes / generation job IDs / authentic candidate SHA-256 values exist.

The five source-SHA-bound independent art briefs are frozen in
`assets/review/albedo_core5/gate2_native_production_briefs.json`.
There is no false claim that briefs constitute rendered artwork.

## Next genuine approval

No production-image sign-off can be requested until five independently authored minimum 1536×1920 (or higher-resolution and *downsampled*) paintings exist. Validate each exact PNG's source hash, separate irises, anatomical upper shoulders, head width within 614.4±4, center x, perspective, arm/hand anatomy, true pose difference, framing and owner visual acceptance. Working especially needs fresh art with correct head/torso proportions.

Do **not** use the prior resampled concept preview hashes as production approval targets. Never create owner-signature ledgers or activate `release.enabled` without actual owner review. The remaining 28 states remain locked.

## Standalone user artifacts

The originating conversation provides:

- `EXODIA_GATE2_CORE5_ENGINEERING_AND_VISUAL_EVIDENCE_2026-11-02.zip`: five verified originals, five calibrated review PNGs, an offline 1:1 viewer, real five-way geometry board and complete per-state engineering telemetry.
- `CORE5_GEOMETRY_DEVIATIONS_REAL_REVIEW.png`: unified visual comparison with actual pixel-scanned eye/shoulder locations and obvious failed head scale.
- GitHub Actions `exodia-core5-workbench-responsive-qa`: desktop/mobile **synthetic** UI interaction screenshots.
