# Exodia Tower — Portrait Continuity Standard (locked 2026-11-01)

**Decision:** The 4:5 portrait canvas is mandatory for **all ten AI companions**, all 20 emotions, 13 action/status portraits, and every frame of an authored animated portrait. This replaces earlier mixed landscape, square, and differently framed artwork. It does not affect the smaller directional sprites used for Operations Deck navigation.

## Fixed master image contract

| Item | Production contract |
| --- | --- |
| Native artwork canvas | **1536 × 1920 pixels** |
| Aspect ratio | **4:5** (W:H), no exceptions |
| Orientation | Portrait, character facing mostly forward; modest head angle permitted for expression |
| Face landmark / eye-line midpoint | **(50%, 33%)** of canvas, tolerance ±4% horizontal and ±4.5% vertical |
| Head width relative to canvas | Target **40%**, tolerance ±5.5% before release; compare apparent scale across states |
| Artwork safe area | 5.5% inset on all edges for headpiece, hair, hands, accessories |
| Composition | Head-to-waist/bust with comparable shoulder position; gestures stay within the same portrait boundary |
| Background | Neutral studio artwork plate or transparency; **animated sci-fi scene in a separate UI layer** |
| Photo geometry | **No nonuniform scaling, auto-zoom, automatic face crop, or per-state object positioning** |
| Native WebP export | 1536 × 1920 4:5, progressive-quality/sRGB visually faithful to PNG |
| Optional streaming format | 768 × 960 4:5 (exact 1/2), scaled down uniformly from approved master |
| Animated action frames | Every source frame 1536 × 1920; every web frame 768 × 960; registered eye-line and consistent face scale; 4+ independently drawn frames; natural motion only |

**Important:** A fixed rectangle is not sufficient. Each character must have the *same apparent head size and eye level*, and the torso must occupy a comparable amount of the portrait; otherwise the viewer perceives a jump in camera distance. The numerical anchor in the art metadata is an artist annotation, not reliable image understanding or automatic identity verification. Manual side-by-side visual inspection and owner sign-off are still mandatory.

## UI slot (independent from source pixels)

- Render a single centered, responsive **4:5** portrait container, no larger than the intended central companion display area; preserve adjacent negative space for ambient holo-scenes.
- All states share the same slot and CSS `aspect-ratio:4 / 5`; use `object-fit:contain; width:100%; height:100%; object-position:center center;` in the image element. **Never apply per-emotion `scale()`**, `object-position`, or `object-fit:cover` to mask inconsistent source art.
- Keep holographic ambient effects, state badges and task console in separate DOM layers. Respect `prefers-reduced-motion`.
- Never use sprite atlas face snippets or wide hero art as 4:5 portrait masters. They may only be shown as clearly labeled legacy review placeholders.

## State changes and short loops

- Expressions can swap the same-size portrait image without changing the surrounding layout; `idle` is the fallback for no ongoing task.
- Idle / breathing: use 4–8 *independently authored registered* frames with subtle breathing and blink, ideally 4–6 seconds per natural cycle. Do not substitute global transform scaling or repeated copies of one still.
- Typing / Working and Explaining: use independently authored registered frame sets with real hand/mouth/eye position changes; allow loop speed to differ without changing image size or camera perspective.
- Encode as a frame-indexed WebP/PNG sequence or tested animated WebP. Do not imply video/animation functionality from a static storyboard.

## Existing legacy artwork and current status

The four original Wave 1 files are **not in compliance** with this contract:

- Happy: 1199 × 1312 (ratio 0.914)
- Thinking: 1312 × 1199 (ratio 1.094)
- Serious: 1312 × 1199 (ratio 1.094)
- Typing/Working: 1536 × 1024 (ratio 1.500)

Previously generated “Actions/Status Set A/B” and “20 Emotions” composites are **concept sheets**, not individually approved master canvas files. They cannot demonstrate native pixel dimensions or full-frame continuity without new production originals.

A **review-only** reframe script preserves the original image's aspect ratio by containing it within a 1536×1920 backdrop. That makes the outer pixel dimension consistent but **does not normalize head size or camera distance**. For final production, regenerate/refine each state directly to the shared canvas and facial landmark specifications.

Install optional art QA tooling with `python -m pip install -r orchestrator/requirements-portrait-qa.txt`.

Run: `python orchestrator/tools/portrait_standard.py check PATH_TO_PNG path_to_metadata.json` (format-and-anchor gate only). To create a labeled legacy review copy: `python orchestrator/tools/portrait_standard.py reframe-review LEGACY_PNG REVIEW_ONLY_PNG`.

## Release criteria

1. Source canvas exactly 1536×1920 (not merely resized at display time).
2. Same identity, haircut, gold flower/halo, eyes, collar crystal and costume across states.
3. Same eye-line, head size, shoulder position, and safe margins at one fixed zoom.
4. Action hands/anatomy correct; no clipped elbows/fingers.
5. Animated loops have independent painted poses, no static whole-body wiggle or duplicate frames.
6. Inspect state switching at desktop/mobile; no layout shift; owner visual approval required.
7. Do not promote unapproved adaptations or concept-board crops to production or other fleet agents.
## Superseding V2 high-resolution fluid motion gate (2026-11-01)

The old minimum 4–8 frame portrait loop language in this historical specification is SUPERSEDED for production: **24–30fps** requires **≥72 unique Idle frames over ≥3 seconds** and **≥48 unique Working/Explaining frames over ≥2 seconds**. Every frame is original native 1536×1920 PNG, no CSS/camera transforms or corrected storyboards, zero changes to locked eye corners, ornament and shoulder anchor regions; only localized microgesture regions may change. See `docs/ALBEDO_NATIVE_MOTION_GATE_V2.md` and `orchestrator/tools/validate_portrait_motion.py`. The old A3 GIF proofs have been rejected as production animation.
