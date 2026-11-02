## EXODIA_STRICT_INSTRUCTION_COMPLIANCE — STRICT SUPERSEDING RULE (2026-11-01)

NO premature images, speculative storyboards, 2D frames, rig proofs or sequence renders. Follow the exact multi-step owner directive in order. Before any master image, verify source/benchmark SHA-256, effective generator output at NATIVE 1536 × 1920 (4:5), camera and required anchor plan. If a model changes 4:5 to 3:4 or any locked spec, HALT and report; never pad/upscale to disguise deviation. Create ONLY one state-specific master keyframe after successful preflight; inspect real resolution, silhouette, face/ornament/shoulder registration, anatomy and hash; present to owner for explicit approval. Do not generate 72/48-frame sequences until the exact master is approved by the owner and recorded. Then validate pixel-lock, only localized motion, 24–30 fps, all frame dimensions, seam fluidity and CI before production release. No fabricated approval flags, invented artifacts, false visual claims or skipping failed checkpoints. See docs/EXODIA_STRICT_INSTRUCTION_COMPLIANCE.md. Previous storyboard loops are rejected; the separate Operations Deck sprite family is preserved.


## SUPERSEDING OWNER DIRECTIVE — 2026-11-01: ZERO-DRIFT NATIVE PORTRAIT ANIMATION
**All previously made low-resolution A2/A3 storyboard GIFs, shifted cells, and apparent camera-lock corrections are REJECTED IN FULL as production animations.** An earlier conditional acceptance is withdrawn. Do not reframe or upscale old storyboard cells into release assets. Preserve them only as historical debugging evidence.
Every agent's true portrait animation requires independent native **1536×1920 4:5** PNG frames, a **completely fixed camera**, rigid **pixel-locked eye-corner, hair-ornament and shoulder anchor regions**, and strictly localized changes to eyelids, mouth, chest, fingers, and approved secondary hair/cloth regions. Do not globally slide, bounce, zoom, crop or recenter the portrait. Separate holographic background motion. Use **24–30 fps**, at least **72 unique Idle** frames spanning ≥3 seconds and **48 unique Working/Explaining** frames spanning ≥2 seconds, with smooth last-to-first continuity; no repeated/duplicated stills disguised as inbetweens. A native-frame manifest, exact static-pixel mask, anchored-patch check, interframe and seam checks are mandatory before visual review. **Automated success never proves painted origin, fluidity or artistic acceptance.** No runtime production promotion without explicit owner sign-off.
See docs/ALBEDO_NATIVE_MOTION_GATE_V2.md and orchestrator/tools/validate_portrait_motion.py. The accepted 2D Operations Deck sprite family is separate; 3D is deferred.

## 2026-11-01 — OWNER'S SUPERSEDING 2D DELIVERY DIRECTION

High-fidelity 3D character sculpting/rigging is DEFERRED to a future project. The current approved task is separate 2D painted image masters for 20 facial emotions and 13 action poses, plus transparent directional sprite sets and authored sprite animation frames for roaming and idle behaviors on the Operations Deck. **Do not claim crop-derived 100px thumbnails are individually authored high-definition images.** Keep them out of a large hero portrait and reject static whole-body wiggles as movement animation. Visual benchmark hashes, complete requirements, and release gates are in `docs/ALBEDO_2D_PIVOT.md` and `docs/companion_2d_requirements.json`.

# Exodia Tower — Companion Art & Rigging Skill
Status: owner-approved visual benchmark LOCKED; individual production assets and genuine rigs NOT YET APPROVED.
Updated: 2026-11-01. Applies to all 10 companions.

## When to use
Use this skill whenever creating/editing companion identity art, expressions, pose references, rigged models, workstation animation, task stage, showcase, or new fleet companions. Preserve existing code, agent IDs, provider logic and task events.

## Approved benchmark — Albedo / Central Command
- Approved scene: **Albedo mission-complete command-center artwork** created 2026-11-01. Source file: `albedo_s_mission_complete_command_center.png`, 1448×1086 PNG; SHA-256 `bfc233740851980021ea0b479a1b4254574f6ca614e3a1e9cbb7bd66c03dc409`. The original PNG is preserved in the user's persistent ChatGPT Library at `/Exodia Tower/Benchmarks/Albedo - approved mission-complete benchmark.png` and distributed as a handoff artifact; **do not claim it is committed to GitHub** until separately imported into `orchestrator/frontend/companions/benchmarks/albedo_mission_complete_v1.png`.
- Approved: silver-to-pale-lavender flowing hair (NOT saturated pink), violet eyes, refined flower/metal hair ornament, white/lilac and black/gold costume accents and violet crystal, expressive softly lit face, premium anime painted finish, luminous violet orbital command interface, lavender/indigo/cyan/mint/gold UI.
- Layout benchmark, NOT a completed five-view character identity model: the visible reference primarily defines the character's face/upper body; unseen back/boots/limb geometry require new design review. Do not substitute pink-haired sheets or the blurry 100px expression atlas.
- Preserve public character name Albedo, internal ID `kiko`; do not migrate IDs casually. Preserve unique established appearances of other agents. Apply the *rendering style and interface quality* to the fleet, NOT Albedo's face, hair, costume or gender to everyone.

## Required per companion: complete contract
**Emotions (20):** Happy; Excited; Laugh; Smile; Thinking; Curious; Surprised; Confused; Determined; Serious; Sad; Disappointed; Pouting; Angry; Hurt; Bored; Sleepy; Dizzy; Pain; Cheerful Wink.
**Actions/poses (13):** Idle; Walk; Run; Jump; Sit; Work (computer); Typing (working); Pointing; Explaining; Celebrating; Stretching; Sleeping; Waking up.
**Turnaround views (5):** Front; Front angle; Side; Back; Back angle.
**Details (4):** Face & eyes; Accessories; Outfit details; Boots.

**Fleet canonical IDs:** `kiko` → Albedo; `router` → Riven; `memory` → Mira; `archives` → Lyra; `inventory` → Pip; `vault` → Aurelia; `ninja` → Nyx; `cache` → Mochi; `strategy` → Orion; `nova` → Nova.
These requirements are machine-readable in `docs/companion_art_contract.json`; do not silently reduce the count. Emotions like Hurt versus Pain, Happy versus Smile, or Bored versus Sleepy need visibly distinct art, not just rewritten captions.

## Production order: asset-quality gates
1. **A0 identity lock:** 1 clean full-body neutral master per companion + one separate face master, minimum 2048px tall for full-body concept; maintain fixed face, irises, hairline, outfit/ornament across subsequent renders. No UI, poster text, environment scenery, or baked masks in source art. Deliver transparent/clean backgrounds and keep raw originals.
2. **A1 turnaround:** 5 fully coherent orthographic/model views with believable reverse clothing geometry; no mirrored back substitutions. Unseen costume details require approval, not assumed canon.
3. **A2 expressions:** 20 independently authored high-detail registered expressions, NOT a contact sheet sliced into 100px thumbnails. Per-expression recommended >=1024px face artwork with matched head scale, eye line, registration and consistent resolution. Export PNG/WebP with alpha and a manifest. Include the neutral/base facial geometry for rig deformation.
4. **A3 actions:** 13 named animation clips or rig poses with transitions; static pose sheets are only storyboards and do not count as movement. Match hands to the keyboard, feet to ground, gaze to screen/human, clothing and hair to motion.
5. **A4 real rig:** create deforming **skinned geometry and/or mesh-deformed Live2D-style geometry** with bone weights/meshes, visemes/blendshapes, independent left/right limbs, foot IK and physical secondary motion. Prefer GLB/VRM skeletal 3D for full turnarounds and locomotion, or artist-authored Live2D deformable meshes for a fixed-front stage. The existing polygon/cutout wobble prototype is explicitly REJECTED as final motion. Do not claim fake sway/crossfaded stills are rigging.
6. **A5 acceptance:** produce actual runtime screen captures/clips for idle→typing→waiting→success, 8+ frame walk with planted feet, run/jump/sit, sleep/wake, look/point/explain, facial morphs, and side/back turn. Check seams at 300% zoom; test desktop, mobile, reduced motion, perf and fallback. Owner sign-off per character is required before marking final.

## Living companion use of negative space
Surround the modestly sized character stage with **event-driven** scene interactions: a separate animated workstation linked to actual task state; contextual holo-cards showing grounded task stages (routing, checking, waiting, result) not fake feeds; a glance/gesture toward the user's result panel; quiet rest activities; eye contact and gaze tracking within reasonable limits; ambient particles and parallax which never masquerade as body motion. No fake stock/health/weather readings, arbitrary sentiment scoring, manual public mood buttons or overcrowded UI. Character identity and genuine motion remain foreground; secondary effects remain subtle and optional. Honor `prefers-reduced-motion`.

## Engineering / trust rules
- Keep `orchestrator/frontend/companions/source_masters` and existing art labs intact for historical provenance; do not promote old cutouts to production.
- Store manifests in version control, keep approved high-resolution masters at explicit stable paths, maintain SHA-256 fingerprints, and avoid invented binaries/links.
- Production runtime must use a verified character-specific manifest and not automatically load the low-resolution experimental atlas. A missing asset shows a coherent high-quality fallback, not corrupted crops.
- Task actions are driven by real application state. Never imply a browser submission, provider completion, speech or media is verified merely because an animation played.
- No external account write/publishing without owner authorization.

## Explicit exclusions
Previously generated pink-haired 20-emotion composite boards were exploratory STORYBOARDS ONLY. They are not the approved silver-haired Albedo identity, not high-definition individual sprites, and not motion rigs; their printed “rig ready” claims are not real verification.

## References
`docs/COMPANION_ART_BIBLE.md`; `docs/companion_art_contract.json`; `docs/ANIMATION_CONTRACT.md`; `docs/A1_ART_PRODUCTION_GATE.md`; `docs/ART_PRODUCTION_A1_3_2.md`.

## 2026-11-01 — High-definition 2D Wave 1 staging

Four independent 1K+ illustrations (Happy, Thinking, Serious, Typing/Working) are supplied via a separate downloadable artifact package and require visual acceptance. The existing 4-direction deck stills remain small-scale navigation prototypes, not completed walk animation. The fail-closed installer in `orchestrator/tools/import_albedo_wave1.py` places the approved-source review files only into `frontend/companions/review/kiko_wave1`. Do not promote unreviewed art to the live stage or rest of fleet. See `docs/ALBEDO_2D_HD_WAVE1.md`.

## LOCKED — 4:5 PORTRAIT CONTINUITY (2026-11-01)
All 10 companions: every emotion, action, status and every real animation frame must use 1536 × 1920 native pixels (4:5), eye midpoint (50%,33%), approx 40% head-width proportion, and 5.5% safe margin around hair, hands and headpiece.
The portrait remains a centered fixed-size slot. No per-state zoom, nonuniform stretch, object-fit cover, or zoom-cropped image. Separate the atmospheric animated UI from portrait art. 4+ genuinely distinct, registered frames for Idle/Typing/Explaining loops.
Wave 1 originals (1199×1312, 1312×1199 and 1536×1024) are source-noncompliant and may only be reframed for review; consistent canvas size alone does NOT fix apparent head size. New artwork must be authored to the canonical canvas, and pass identity/anatomy and user acceptance review.
Authoritative standard: docs/ALBEDO_PORTRAIT_STANDARD.md. Gate: orchestrator/tools/portrait_standard.py. Operations Deck sprite dimensions stay separate.

## OWNER-LIKED PORTRAIT PHASE 2 BOARDS — 2026-11-01

The owner approved Albedo's silver-lavender portrait style, the 4:5 1536×1920 master specification, and the distinct Operations Deck sprite family. Lock board fingerprints as visual references, **not as individual HD masters**: Expressions & Emotions `albedo_s_neon_portrait_review_board.png` (`92bc46363077858bb0df`); Actions/Status Set A `albedo_s_futuristic_portrait_production_board.png` (`7b489427ca55c9c0d6f1`); Actions/Status Set B (Revised) `albedo_exodia_tower_portrait_review.png` (`17a3f1308be2293f3cac`); Idle/Working/Explaining storyboard `albedo_portrait_loops_review_board.png` (`686bbe9fe56f9006cf26`); original command artwork `albedo_s_mission_complete_command_center.png` (`bfc233740851980021ea`). The images live in a separate Phase 2 review ZIP, not GitHub binaries.

Portrait scope is 20 emotions, 13 actions, and four command statuses (Awaiting Command, Monitoring, Defeat, Tantrum). Idle/Working/Explaining require 4+ registered, individually drawn 1536×1920 frames; the three 200-px-wide extracted GIFs are **storyboard-only** and never production quality. Four previous Wave 1 PNGs also fail the native canvas check. Review/loader: `orchestrator/frontend/companions/review/kiko_wave2/` and `orchestrator/tools/import_albedo_phase2.py`; full phase report `docs/ALBEDO_2D_PHASE2.md`. No live art replacement or fleet rollout until actual visual acceptance.


## 2026-11-01 — MANDATORY PORTRAIT CAMERA LOCK
Owner conditionally approved Idle, Working and Explaining *art direction*, but A2 GIF extraction had real 15–28px horizontal camera/framing drift in ~200px cells. A3 corrects this in **storyboard preview only**. Production loops MUST retain a fixed camera and the 1536×1920 (4:5) master for every frame, with constant eye midpoint (spread <=0.008 normalized x/y) and head width (spread <=0.012). Four or more independently authored frames, natural face/hand changes, and no global portrait translation, zoom or rotation. Ambient holograms may move as independent layers, not as a fake moving body. Operations Deck sprites remain separate. Source and tests: `orchestrator/tools/albedo_camera_lock.py`, `orchestrator/tests/test_albedo_camera_lock.py`, `docs/ALBEDO_A3_CAMERA_LOCK.md`. NEVER promote the corrected 256×320 storyboard GIFs to HD workstation assets; live art replacement remains blocked.

## 2026-11-01 OWNER AUTHORIZED REVIEW NORMALIZATION EXCEPTION

The owner explicitly superseded the previous rejection of *resized master previews*: a generator's ~4:5 1122×1402 output may be **uniformly upsampled with Lanczos and padded, without cropping**, to a 1536×1920 **visual-review normalization master**. This does NOT mean the generator rendered native 1536×1920 detail, and it does NOT relax the independent-native-frame requirement for future animations. Never label normalized images original native art.

Use `orchestrator/tools/portrait_standard.py normalize-generated SOURCE.png OUTPUT.png ANNOTATED_LANDMARKS.json METADATA.json`. The mathematical registration uses manually annotated source eye midpoint and head left/right bounds, mapping to y=633.6 and width=614.4 (±1px). Its `PASSED` and exit 0 mean **dimension and declared-transform technical pass only**; facial landmarks are not automatically image-verified. Hashes preserve original PNG and output + registration record. Owner visual inspection of the resized art, its provenance, and its eye/head annotations is still mandatory. If alignment requires crop/warp, or 3:4 output is supplied, HALT. Sequence generation remains blocked until explicit owner master approval and native-frame gate.


## 2026-11-02 — State-driven portrait registry gate
The permanent Albedo/fleet portrait matrix has 20 expressions + 13 actions + three loop hooks. Canonical \`portrait_registry.json\` is at \`orchestrator/frontend/companions/production/kiko/\`. Static assets must be native 1536×1920 with image SHA-256 and a second SHA-256-bound human landmark annotation. Required eye midpoint: (768,633.6) px; head width 614.4 px (tolerances in registry). Do not treat image metadata as automatic facial measurement. \`portrait_registry_audit.py\` must pass before release.enabled can be set true. Never fabricate hashes or promote composite review boards. On failure, the state manager must retain the legacy workstation portrait and keep all providers working. Crossfade ONLY whole approved portrait state changes (opacity; no crop/scale); never cross-dissolve open/closed eyes. Operations Deck sprite family remains separate.


## STATIC-ONLY COMPANION PORTRAIT RELEASE — 2026-11-02
The owner postponed animation loops/GIFs. The new 33-state static system (20 Expressions & Emotions, 13 Actions/Statuses) may ship without the three deferred loop assets, but only after **all 33 distinct native 1536×1920 stills** pass dimension, SHA-256, reviewed actual face coordinates (eye-line y=633.6±2px, horizontal eye midpoint x=768±8px, head width=614.4±4px), image-bound registration file and explicit owner approval checks. The three loop hooks remain DEFERRED, never shown as working animations. Composite concept boards, small atlas crops, normalized review adapters and copied duplicates are not release assets. Never flip the runtime release flag merely to demonstrate functionality. Existing provider workflows and Operations Deck sprites must remain unchanged. See docs/ALBEDO_STATIC_PORTRAIT_INGESTION.md and tools/portrait_registry_audit.py. 

## 2026-11-02 — APPROVED MASTER BOARD SLICING GATE
Use `orchestrator/tools/slice_master_boards.py` for auditable extraction of approved board cells. This is **review-only** for the current boards: 20 Expressions concept cells and 11 Action/Status concept cells; only 21 unambiguous labels match the newer 33-state registry. All crop cells are substantially below native 1536×1920, and no actual eye/head landmarks have been independently confirmed. Preserve original board SHA and crop SHA, crop dimensions, and provenance. Never upscale/pad a small cropped panel and label it an independent native HD production asset. Never synthesize missing state matches, fake eye-line y=633.6, fake approval ledger, or flip `release.enabled` after a failed audit. Full asset verification + owner approval + `portrait_registry_audit.py` exit code 0 is mandatory before live activation. Operations Deck sprite family remains separate; animated loops deferred.


## EXODIA_STANDALONE_ASSET_ONLY — PERMANENT RULE (2026-11-02)

The owner rejects all auto-sliced production character artwork. Never crop portraits or sprites from composite summary boards, contact sheets, UI grids, thumbnail atlases, collage montages, or compressed review sheets. Never promote such crops by padding, upscaling, or changing their filename. Approved source boards remain style references only. The retired grid slicer and its CI are banned.

Each of the 33 production portraits must originate as a truly independent, standalone, native 1536×1920 PNG, with an image SHA-256, image-bound human-annotated facial landmarks, and direct owner approval. Every registration record and matching owner approval ledger row must include the same independently reviewed provenance record: schema exodia.independent-portrait-source/v1, source_kind independent_standalone_native, derived_from_composite false, native_canvas [1536,1920], original_sha256 matching the actual file, original_filename, source_method independent_image_render or standalone_artist_export, human_source_review completed.

Metadata alone does not prove source authenticity or owner consent; reviewers must inspect the original standalone file and the actual approval evidence. Missing or suspicious provenance MUST fail the importer and independent registry audit. No live promotion until all 33 pass. Deferred animation loops and Operations Deck sprites remain separate. Preserve live provider workflows.

See docs/EXODIA_STANDALONE_ASSET_ONLY.md.
