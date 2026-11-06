# EXODIA Tower — Riven A0 Identity Gate / Five-State Pilot

**Authorized:** Owner requested a *controlled* Riven-only pilot after lifting the prior Riven freeze. **Not authorized:** all-33 bulk generation, any Mira/Lyra/Pip/Aurelia/Nyx/Mochi/Orion/Nova artwork, production release, or extraction of source images from a collage.

## What already exists (do not recreate)

- Internal ID **`router`**, public name **Riven**, class **Pathfinder Knight / Dual-Blade Router**. The roster and the existing manifest at `assets/review/riven_pilot/pilot_manifest.json` remain authoritative.
- Actual historical reference: `orchestrator/frontend/companions/source_masters/router.png`; 1122×1402 RGB PNG; SHA-256 `65562dfd75c83ac46cf6ec2dec05bff9d59812bd22287750bd48833f94bc584e`. This is a *composite poster*. The face, costume and color cues are useful, but the poster is **not** a native independent source image.
- The existing pilot is exactly five state keys: **`neutral`**, **`confident`**, **`angered`** (distinct expressions), **`working`**, **`pointing`** (distinct connected-hand actions). All source hashes remain null until real independent artwork is present.

## Identity continuity plan (one master before a five-image set)

1. **A0 identity candidate**: separately author one actual native 1536×1920 portrait PNG at correct 4:5. It must be Riven (black/dark hair in long twin tails with recognizable red ribbons/highlights, deep red eyes, black/red/gold intricate battle armor, twin blades), **not Albedo**, with believable body anatomy, natural connected hands, no labels/UX blocks/castle background. Unseen costume elements from the poster are *undetermined design work*, not already accepted canon.
2. Camera/geometry contract: center x=768px; eye y=633.6px ±2; shoulder baseline y=980px ±2; head width 614.4px ±4; 1536×1920 canvas. These are **targets**, not measured evidence. Source reviewer must annotate eye corners/centres, shoulder landmarks, jawline, hair ties, and blade hand-grips directly on actual pixels.
3. Preserve original standalone PNG bytes; record actual SHA-256 and independently inspect at full pixels. Validate correct original source method, not crop, poster extraction, upscale or single-base expression repaint. A source photo/export is not automatically proved independent merely because its hash differs.
4. Send **only the A0 identity original** for exact-image owner review. Obtain owner authorization explicitly tied to that SHA before producing more states. Its geometry/design approval cannot be inferred from automated image validation or the current poster.
5. After A0 approval, produce the **five distinct independently authored** states as separate native PNGs. Distinguish neutral vs confident vs angered in eyes, brows and shoulders. Working must visibly interact with a route map/terminal using connected fingers. Pointing must have a plausible extended index finger, wrist, forearm, shoulder and clear target. Do not simply change captions or swap eye colors. Owner reviews each actual state with matching SHA.
6. Only after all five pass provenance, measured geometry, actual visual QA and owner SHA-specific acceptance may the pilot be considered art-accepted. **Do not** change `release.enabled=false` or the 33-state production registry automatically.

## Read-only A0 technical gate

From the repository root:

```powershell
cd orchestrator
python tools/riven_native_identity_gate.py
python tools/riven_native_identity_gate.py --root . --candidate path/to/independent_riven_master.png --expected-sha256 <EXACT_ORIGINAL_SHA> --require-native-candidate
python -m pytest tests/test_riven_native_identity_gate.py tests/test_fleet_portrait_pilot.py -q
```

The first command confirms the poster SHA and correctly reports that identity art is **pending**. The second requires genuine source bytes and checks PNG, **native canvas**, SHA, path safety and a minimal non-flat image sanity check. A technical pass still reports `source_authenticity_verified=false`, `image_bound_landmark_review=pending`, `owner_identity_approval=pending`, and `five_state_pilot=blocked_until_identity_approval`. The human gate cannot be overridden by metadata.

## Product integration priority

Do **not** hold command-center/provider work for fleet art. This Riven pilot changes neither Cursor provider automation nor any Albedo or other character runtime asset. PRs must target `development/exodia-foundation`, with independent review and active Foundation/Portrait checks. No direct pushes to protected integration or merging draft PR #1 into `main`.
