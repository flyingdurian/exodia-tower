# EXODIA Tower — Riven (router) Five-State Pilot, A0 Intake

**Status: PREPARATION ONLY; no production portrait generated or approved.**

This pilot uses `docs/EXODIA_FLEET_33_STATE_ART_STANDARD.md` and the immutable 33-key production vocabulary. Its locked five test states are `neutral`, `confident`, `angered`, `working` and `pointing`: three expressions and two distinct actions. These are **five separately authored future images**, not five crops or minor expression edits of a single base.

## Source assessment

The current real `orchestrator/frontend/companions/source_masters/router.png` is a **1122×1402 composite environment/character/poster**, containing interface labels, a full-body dynamic Riven pose and the command-tower background. It is useful to preserve identity cues (dark twin-tail hair, red highlights, ornate dark armored costume, dual blades and route-themed visual effects), but **is not** a standalone native 1536×1920 portrait source. Its specific SHA-256 is pinned in `assets/review/riven_pilot/pilot_manifest.json` and verified by the tooling.

No Riven A0 native identity master has yet received SHA-bound owner approval. The five distinct native portraits must therefore remain `awaiting_native_source`; the current pipeline is a planning and technical preflight, not a claim that those five images already exist.

## Reusable workflow

1. Check `orchestrator/frontend/companions/roster.json` against the ten stable IDs and the 20/13 Albedo canonical keys. Keep Riven's internal ID `router`.
2. Have an art source produce a new **independent standalone** native 1536×1920 A0 identity master, consistent with Riven, free of labels and dashboard framing; obtain owner's exact-image signoff before deriving a five-state plan. A native source requires genuine native detail, not upscale from the poster.
3. Author the five independent state artworks with anatomically connected hands and distinct acting, original source SHA-256, no composites/atlases/recolors, and real measured left/right iris, shoulder and head boundaries against eye y=633.6±2, shoulder y=980±2, head width=614.4±4, x center 768.
4. For each separately authored PNG, set its relative `source_file`, `source_sha256`, `source_kind=independent_standalone_native`, `derived_from_composite=false` in the pilot manifest. Run `cd orchestrator && python tools/fleet_portrait_pilot.py --manifest ../assets/review/riven_pilot/pilot_manifest.json --root <source-directory>`.
5. Only a passing technical source audit is automatic. Human reviewers must separately inspect source authenticity, silhouette/costume, facial expression, gesture/armor alignment, measured geometry and style continuity. A new image SHA requires fresh approval. The tool deliberately reports `native_production_certified=0` and never sets `release.enabled=true`.
6. Review the pilot side by side, at full original pixels, before expanding to Riven's remaining 28 states or any other companion. A future review board may be created from *copies* of source files for review only; never extract assets from a review board.

**Hard boundary:** Albedo remains independently locked; Operations Deck motion is a separate workstream. Riven or other fleet production images are not authorized by this A0 manifest alone. Functional model/provider development proceeds independently.
