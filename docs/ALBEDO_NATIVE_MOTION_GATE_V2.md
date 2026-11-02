# Exodia Tower — Zero Drift Native Portrait Animation (V2)
OWNER DIRECTIVE 2026-11-01. Supersedes the A2/A3 storyboard GIFs and camera-locked cropped previews; these are **REJECTED IN FULL** for production.

**Required original frames:** exactly 1536 × 1920 PNG, vertical 4:5, separately authored at native detail, fixed angle/scale/camera (translation [0,0], zoom 1, rotation 0, crop null). All 10 companion identities use this standard. Small Operations Deck sprites remain separate.

**Pixel-locked anchors:** left/right eye corners (lids may blink, corners do not shift), right floral head ornament, left/right shoulder attachment. Author must provide a binary 1536×1920 motion mask marking allowed local deformations (breath, eyelids, lips, fingers, selected hair and garment strands). All other pixels must exactly match frame 0. The 5.5% border is not a motion region, and mask area must not exceed 38% of the canvas. Background FX are separate UI layers.

**True fluidity:** minimum 24fps (up to 30fps); Idle ≥72 unique frames over ≥3 seconds; Working/Explaining ≥48 unique frames over ≥2 seconds; check adjacent frames AND final-to-first loop seam. No identical holds marketed as interpolated animation, sudden shifts or relabelled stills. Fixed camera is not equivalent to frozen body: local breath, blink, finger and mouth deformation is permitted in mask.

**Fail closed:** refuse unsafe frame paths, wrong formats, dimensions, duplicate hashes, motion outside masked regions, changing anchor pixels, altered camera metadata, short loops, abrupt changed-area jumps and mask violations. Reject any image filename containing STORYBOARD or reframe. Human visual comparison and animation playback review remain mandatory even after technical tests pass; artist-provided source metadata cannot independently prove true native authorship.

**Release:** inspector under orchestrator/frontend/companions/review/portrait_motion_inspector.html begins empty and cannot publish. Validator orchestrator/tools/validate_portrait_motion.py returns production_ready=false even on a technical pass. No changes to the existing live companion or providers; owner sign-off required after complete independent high-res artwork is available.

**QA:** install orchestrator/requirements-portrait-qa.txt; run pytest -q orchestrator/tests/test_validate_portrait_motion.py orchestrator/tests/test_motion_inspector_contract.py. Do not infer that synthetic test fixtures are character art.
