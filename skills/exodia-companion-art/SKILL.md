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
