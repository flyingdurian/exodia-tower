# Gate A1.3.2 — Kiko Registered Cutout Review

**Status:** Technical compositor improvement implemented; production art **NOT accepted**.

## Actual implementation
- Source-approved silver-haired Kiko, not the unrelated pink-haired concept exploration.
- Independently encoded RGBA part images in `orchestrator/frontend/artwork/kiko_prime/` are now rendered as actual layers (source-space boxes, joint rotations, deterministic z-order).
- Workbench offers live comparison between *registered RGBA* and *original polygon-mask* render modes.
- Failed art files and invalid pivots/bounds are exposed in telemetry; the source scene is not silently substituted for missing parts.
- Existing 24 emotion controllers, hand IK and tests remain available.

## Visual failures blocking acceptance
1. The original image is a **composite fantasy environment**, not an animation-ready art source. Some large cutouts contain portions of blue holograms and architectural scenery.
2. Foreground hair and back hair overlap in ambiguous regions; isolated strand mattes still need hand painting.
3. Hidden shoulders, knees, elbow backs, and the reverse sides of clothing don't exist in the master and cannot be produced by cropping it.
4. Real mouth and eye animation requires repainted neutral skin occluders and multiple registered eyelid, brow and phoneme shapes, not alpha-transformed painted source mouth.
5. No claims of final Live2D, Spine, or 3D rig quality should be made until visual review, deformation review, and full motion footage pass.

## Required artist deliverables
- Clean transparent front/back hair; skin and face base **without baked eyes/mouth**.
- Separate open/closed eyelids, eyebrows, irises/pupils, cheek/blush and mouths A/E/I/O/U/M/F/rest.
- Independent torso, hips, skirt flaps, left/right upper/lower arms, hands/fingers, thighs, shins, boots and back-of-joint paint.
- Identical character identity, clothing, pose registration coordinates and approved colors across sprites.
- Review: 3x zoom on hair/joint seams, walk side-to-side, typing, wave, upset, sleepy and speech states. No baked scenery.

## Development workflow
Preview via `http://127.0.0.1:8765/art-studio`. Select **Registered transparent sprites**; compare against source masks.
The reference illustration is preserved; no irreversible modifications to the master.
