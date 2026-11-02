# REJECTED FOR PRODUCTION — owner superseding directive 2026-11-01

Any earlier conditionally approved small-camera-lock storyboard GIFs are rejected in full as production animation. Historical artifact ONLY. New V2 native standards supersede these storyboard methods. See `docs/ALBEDO_NATIVE_MOTION_GATE_V2.md`.

---

# Albedo A3 — Stationary Camera & Native Loop Acceptance (2026-11-01)

The owner approved the visual concept of Idle, Working and Explaining portrait loops **conditional on the camera not flying around**. Inspection of the actual A2 source GIF cells found genuine horizontal position drift of approximately **15–28 pixels** (source images are only about 200 px wide). This was a source storyboard extraction problem, not a harmless screen-recording effect.

## Corrected result
- Re-register the decorative gold floral-crown anchor across four concept frames, with one fixed camera and static backdrop.
- Produce corrected **256×320 (4:5) storyboard-only** GIF previews using source frames in a 1→2→3→4→3→2 sequence; do not simulate whole-body movement with CSS zoom, translation or rotation.
- Compare original and camera-locked outputs in the standalone A3 comparison HTML delivered in the downloadable package.
- The conceptual illustrations remain small; the output is NOT approved HD animation or production art.

## Mandatory production gates
- Every individually authored frame must be **1536×1920 (4:5)** and maintain identical camera scale, viewpoint and screen-space registration.
- Eye midpoint x/y registration spread must not exceed **0.008 normalized units**, and head width spread must not exceed **0.012**. These are technical gates, not evidence of artistic consistency.
- At least four **distinct** rendered frames, with actual expression/hand/pose changes and no duplicated frame bytes.
- No automatic frame camera motion, recentering, crop animation or whole-body cutout wiggle. Allowed: subtle expression, blink, breath and natural hand movement within a stationary frame.
- Holographic ambient scenery is separate from character layers. Reduced-motion mode holds a neutral still frame.
- Operations Deck sprite dimensions remain a distinct asset family.

## Reproduction
The package includes original A2 storyboard GIFs and corrected A3 previews for direct comparison; code is committed under `orchestrator/tools/albedo_camera_lock.py`, with tests in `orchestrator/tests/test_albedo_camera_lock.py`.

Run the visual QA tools independently of the live server:

```powershell
cd orchestrator
python -m pip install -r requirements-portrait-qa.txt
python -m pytest -q tests/test_albedo_camera_lock.py
python tools/albedo_camera_lock.py --storyboard-source "C:\path\to\previous\A2\assets\storyboard" --output "C:\path\to\A3\preview"
```

The source storyboard directory may be extracted from the earlier downloaded A2 review package. The live Companion Task Workstation and AI provider connections have **not** been modified; the production replacement remains blocked until native artwork and real loop verification are complete.

Local QA: 6/6 camera-lock tests passed. Chromium checked the self-contained A3 comparison at desktop and mobile widths, including loop switching, image decoding and zero JS exceptions. GitHub CI results remain independently subject to GitHub Actions.
