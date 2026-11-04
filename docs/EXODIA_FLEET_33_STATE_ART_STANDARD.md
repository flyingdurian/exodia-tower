# EXODIA Tower — Fleet Portrait & Expression Production Standard

**Canonical repository location:** `docs/EXODIA_FLEET_33_STATE_ART_STANDARD.md`  
**Specification:** `exodia.fleet-portrait/v1`  
**Prepared:** 2026-11-04 (America/Vancouver)  
**Scope:** Albedo + nine additional companions; **static 33-state portraits**. Operations Deck sprites, native character animation, rigging and provider integrations are separate workstreams.

> **Governance status:** This is the adopted specification, a consolidation of existing owner directives, GitHub source standards and the current canonical 33-key Albedo registry. It is a **ready-to-commit proposal**, not proof that the file has been committed. When incorporated into GitHub, compare it to `SKILL.md`, `docs/EXODIA_STRICT_INSTRUCTION_COMPLIANCE.md`, `docs/EXODIA_STANDALONE_ASSET_ONLY.md`, `docs/ALBEDO_NATIVE_MOTION_GATE_V2.md`, and the actual production registry; preserve any stricter owner-approved rule. In the event of a conflict, latest explicit owner directive and factual evidence prevail. **Do not interpret this document as authorizing production release, retroactive approval or rewriting accepted images.**

## 1. Purpose and rollout policy

- Lock the shared **portrait format, measurable spatial anchors, 33-state semantics, independent-asset rules, provenance, QA and release stages** before authoring the other nine agents.
- **Immediate priority remains Albedo delivery**: actual protected four-image review import -> push to development branch -> real FastAPI/Chromium verification -> UI version/provider improvements. No additional fleet art generation before Albedo delivery and a new owner-approved fleet production phase.
- Existing Albedo: 29 owner-accepted-for-development original/review pairs are immutable; four latest standalone 1122×1402 owner-accepted-for-development replacements require protected review import; resampled images remain non-native. A separate native-source pass remains open for all unapproved masters.
- **Art direction is shared, not character identity**. Each member has distinct facial structure, silhouette, colors and costume. No turning all fleet portraits into Albedo in different clothes.
- No arbitrary manual sign-offs per technical substep. Owner visual review is mandatory only for new source master/release boundaries; automated test success cannot impersonate the owner.

## 2. Fixed portrait geometry and camera formula

| Field | Locked value / governance |
|---|---|
| Master source | One independently authored native **1536 × 1920 PNG** per state (or genuinely higher-detail standalone source with documented uniform downsample); final master remains 1536×1920 |
| Ratio | Width:height = **4:5**; 1536 / 1920 = 0.8 |
| Horizontal center | x = **768 px** |
| Primary iris eye-line midpoint | y = **633.6 px** with **±2 px** tolerance, based on actual left/right iris pixel evidence |
| Secondary upper anatomical shoulder baseline midpoint | y = **980 px** with **±2 px** tolerance; inspect left and right independently |
| Head apparent width | **614.4 px**, tolerance **±4 px**, measured using genuine left/right head boundaries |
| Vertical eye-to-shoulder separation | **346.4 px** target |
| Foreground safe area | At least **5.5%** inset where possible, without clipping approved expressive gestures |
| Camera / presentation | Matched frontal or narrowly defined near-front angle, head-to-shoulder scale, torso crop, lighting and focus; static view, no per-state camera moves |
| UI presentation | Shared CSS `aspect-ratio:4 / 5`, centered `object-fit:contain`; full image opacity crossfades only; do not use CSS translation to hide source drift |

### Mathematical preflight

For state `s`, independently annotate **observed image pixels**: left iris `(xL,yL)`, right iris `(xR,yR)`, left shoulder `(xSL,ySL)`, right shoulder `(xSR,ySR)`, left/right head silhouette boundaries `xHL,xHR`. Then calculate:

```text
observed_eye_y        = (yL + yR) / 2
observed_shoulder_y   = (ySL + ySR) / 2
observed_head_width   = xHR - xHL
observed_head_center  = (xHL + xHR) / 2
abs(observed_eye_y - 633.6) <= 2.0
abs(observed_shoulder_y - 980.0) <= 2.0
abs(observed_head_width - 614.4) <= 4.0
observed_head_center ~= 768.0  [horizontal tolerance must be fixed and approved before native release]
```

- The 633.6 and 980 targets are **not** landmark detections. Numeric detectors that search a conveniently placed hair/collar edge instead of anatomy **FAIL** until independently inspected.
- Do not average away asymmetry: record left/right values and inspect eye tilt, shoulder landmarks, head width and fit. A real intentional head tilt may need approved state-specific exception; do not falsify measurements to force a pass.
- Uniform scale and translation cannot generally satisfy incompatible head-width and eye-to-shoulder ratios. If incompatible, create genuinely new source artwork; never use nonuniform stretch, perspective warp, cutout patchwork or auto-crop to fake compliance.
- A genuinely 1122×1402 independently rendered concept may become a **resampled development-review PNG** only, with exact provenance and labels. It does **not** count as a native source simply because the output file is 1536×1920.
- For the other nine identities, preserve species/face morphology and the 1536×1920 stage. If a non-human or distinctive silhouette genuinely cannot share Albedo's human-shaped head/shoulder measurement, require a documented **character-specific approved anatomical anchor profile**, not silent target bending.

## 3. Fleet identity registry (stable internal IDs)

| Stable ID | Public name | Responsibility | Identity policy |
|---|---|---|---|
| `kiko` | Albedo | Central Command | Approved silver/lavender hair, violet eyes, celestial floral/gold ornaments, detailed white/lilac/black/gold outfit; approved Albedo master hashes only |
| `router` | Riven | Task routing / Pathfinder Knight | Preserve Riven-specific approved source masters; do not apply Albedo facial features or costume |
| `memory` | Mira | Context / Prompt Scribe | Preserve Mira-specific face, silhouette, costume and established source masters |
| `archives` | Lyra | Knowledge / Crystal Librarian | Preserve Lyra-specific identity and approved source masters |
| `inventory` | Pip | Tools / Guild Engineer | Preserve Pip-specific identity and approved source masters |
| `vault` | Aurelia | Secrets / Keywarden Paladin | Preserve Aurelia-specific identity and approved source masters |
| `ninja` | Nyx | Browser / Shadow Scout | Preserve Nyx-specific identity and approved source masters |
| `cache` | Mochi | Cache / Bento Sprinter | Preserve Mochi-specific identity and approved source masters |
| `strategy` | Orion | Strategy / Star Cartographer | Preserve Orion-specific identity and approved source masters |
| `nova` | Nova | Social / Creative Intelligence | Preserve Nova-specific identity; authoritative reference must be verified, not invented |

**Canonical roster source:** `orchestrator/app/companions/roster.json` (and the synchronized frontend mirror `orchestrator/frontend/companions/roster.json`), `orchestrator/frontend/companions/source_masters/`, any character-specific approved benchmark and a future explicit owner sign-off ledger. Internal `kiko` must remain Albedo's ID to preserve persisted tasks and paths. Source masters are **identity references**, not proof that 33 finished portraits exist. The nine other companions need their own A0 identity/benchmark review before production. Do not invent their unseen back, boots or costume components.

## 4. Frozen 33-state vocabulary (shared by the fleet)

**Source of truth for keys and signal defaults:** `orchestrator/frontend/companions/production/kiko/portrait_registry.json` at handoff HEAD `7f99a9a8e755`. Exactly **20 expressions and 13 actions/statuses**. Key strings are frozen; new aliases or deprecated older naming maps require explicit migration and tests. Every character can render its own independent artwork for the same key, but the state meaning stays stable. An optional runtime `signal_overlay` is a separate UI layer, **never the only visual difference between two portrait states**.

### 20 expressions

| Key | State intent / visual requirement | Must distinguish from | Existing Albedo default signal |
|---|---|---|---|
| `neutral` | Emotionally level; resting brows and mouth; neither smile, frown, concentration, nor sadness. | gentle / serious | `none` |
| `happy` | Warm delighted smile and lifted cheeks; controlled happy eye expression. | joyful / smiling_closed | `triumphant_halo` |
| `joyful` | Open, radiant happiness with more energetic eye/arm acting than happy. | happy / excited | `triumphant_halo` |
| `excited` | Anticipatory enthusiasm; widened bright eyes; eager, connected hands. | joyful / surprised | `triumphant_halo` |
| `gentle` | Tender, softened gaze with quiet compassion; restrained hands. | happy / neutral | `none` |
| `smiling_closed` | Clearly closed-eye smile; relaxed warm expression without full laughter. | gentle / laughing | `none` |
| `laughing` | Unmistakable active laugh: mouth and eyes acting together. | smiling_closed / amused | `triumphant_halo` |
| `amused` | Subtle private amusement or wry smile; controlled half-grin. | laughing / confident | `none` |
| `confident` | Assured grounded posture, decisive direct gaze; not hostility. | serious / angered | `focus_resonance` |
| `serious` | Sober attention with closed mouth, level firm brow and minimal gesture. | focused / neutral | `focus_resonance` |
| `focused` | Deep task attention with intent gaze toward task target; shoulders grounded. | serious / thinking | `focus_resonance` |
| `thinking` | Reflective problem-solving, gaze/hand thoughtfully poised; not bewildered. | curious / thinking_deeper | `focus_resonance` |
| `curious` | Investigative inquisitiveness: mild asymmetric brows and exploring gaze. | surprised / thinking | `focus_resonance` |
| `surprised` | Immediate unexpected discovery; genuinely widened eyes and raised brow. | excited / worried | `warning_pulse` |
| `concerned` | Careful sympathetic worry; eyes/brows show protective caution. | worried / sad | `warning_pulse` |
| `worried` | Stronger anxious uncertainty and tension than concerned. | concerned / surprised | `warning_pulse` |
| `sad` | Sustained sadness with downturned features; grief legible in eyes. | disappointed / worried | `none` |
| `disappointed` | Deflated expectation; resigned lowered energy rather than active sadness. | sad / defeat | `none` |
| `angered` | Controlled unmistakable irritation: lowered brows, tight lips, tense but connected arm/hand. | tantrum / confident | `strain_glitch` |
| `blushing` | Clearly embarrassed/flushed cheeks and bashful gaze, without altered identity. | gentle / happy | `none` |

### 13 actions and task statuses

| Key | State intent / visual requirement | Must distinguish from | Existing Albedo default signal |
|---|---|---|---|
| `idle` | Natural calm availability; relaxed hands, neutral grounded shoulder silhouette. | neutral / awaiting_command | `none` |
| `working` | Clearly interacting with workstation; plausible connected wrists, fingers, gaze. | monitoring / explaining | `focus_resonance` |
| `monitoring` | Attentive reading/scanning of live status; perceptible watchfulness. | working / focused | `focus_resonance` |
| `pointing` | Unmistakable extended index finger connected through wrist/arm to torso; meaningful direction. | explaining / awaiting_command | `focus_resonance` |
| `explaining` | Distinct open explanatory gesture that clearly communicates instructions. | pointing / working | `focus_resonance` |
| `celebrating` | Visible joyful achievement with connected lifted arms/hands, not just smiling. | excited / joyful | `triumphant_halo` |
| `defeat` | Deflated loss with posture collapse and facial resignation; not generic sadness. | disappointed / sad | `strain_glitch` |
| `stretching` | Recognizable deliberate stretch with correct connected shoulder/arm anatomy. | waking_up / celebrating | `none` |
| `sleeping` | Genuinely asleep; closed eyes and settled restful pose. | smiling_closed / idle | `none` |
| `waking_up` | Transition from rest: drowsy gaze, natural posture change, distinct from active stretch. | stretching / idle | `none` |
| `tantrum` | Kinetic frustrated outburst with expressive shoulders and both connected arms; more intense than angered. | angered / celebrating | `strain_glitch` |
| `thinking_deeper` | Extended introspection with more complex concentrated acting than thinking. | thinking / focused | `focus_resonance` |
| `awaiting_command` | Calm listening readiness; receptive eye contact and poised body language; no generic greeting palm. | neutral / idle | `none` |

**Runtime signals currently documented:** `none`, `warning_pulse`, `focus_resonance`, `strain_glitch`, `triumphant_halo`, `casting_arcana`, `low_hp`. Signals and task events can enhance the presentation, not replace unique facial acting/body poses. For example, `angered` is controlled irritation, whereas `tantrum` must be a more kinetic frustrated outburst. `neutral`, `idle`, and `awaiting_command` must have visibly different postures and facial intent.

## 5. Independent source artwork and anti-cloning

1. Exactly **one single-portrait independently authored source file per `(companion_id,state_key)`**. Native art must originate as a standalone 4:5 PNG. Contact sheets, labeled montages, dashboard mockups, summary boards or extracted panels are never production source material.
2. No shared-base repaints, label-only swaps, palette-only changes, copied gestures, fake emotion overlay variants, padded 100px atlas tiles, paper-puppet cutouts or static-body wiggle substituted for character motion.
3. Keep original source **bytes** and a distinct cryptographic SHA-256 per state. Also run perceptual/full-image and face-region similarity checks; different file hashes alone do not guarantee distinct art.
4. Require meaningful, anatomically credible expression/body acting for every state, physically connected hands/arms, consistent costume/ornament anchoring, and review of face, eyes, hand geometry and clothing seams at full pixel scale.
5. If using an outside generator, log actual `model`, transport, request version and job ID *if actually available*. Never invent operation IDs, source SHA, prompt hash, anatomy coordinates or owner approval. Provider credits, output ratio and rights need real verification.
6. A visual approval of a low-resolution prototype **does not transfer** to a newly rendered native image with a different hash. Distinguish development-art direction sign-off from native-source identity and final production approval.

## 6. State asset manifest / provenance ledger

For production each state requires image-bound evidence covering:

```json
{
  "schema": "exodia.independent-portrait-source/v1",
  "character_id": "kiko",
  "state_key": "angered",
  "source_kind": "independent_standalone_native",
  "source_method": "independent_image_render",
  "derived_from_composite": false,
  "original_filename": "angered_original.png",
  "native_canvas": [1536, 1920],
  "original_sha256": "ACTUAL_SHA256_RECORDED_AFTER_CREATION",
  "landmark_method": "image_bound_human_reviewed_actual_pixels",
  "registration_sha256": "ACTUAL_REGISTRATION_FILE_HASH",
  "state_specific_visual_review": "pending",
  "owner_confirmation_reference": null,
  "production_status": "pending_production_art"
}
```

**Schema illustration only**, not a valid production record. Exact accepted keys/paths must be reconciled with the current importer; do not copy fake placeholder SHA values into a released ledger.

Recommended storage for each future companion follows the active registry conventions: `orchestrator/frontend/companions/production/<stable_id>/frames/expressions/<key>.png` and `/frames/actions/<key>.png`, matching registration JSON and approval ledger; review-only assets under a separately labeled review directory. Confirm the real path layout from the current repo before creating new folders.

Every audit/report should separately count: planned states, independent original sources, playable UI states, SHA verified states, measured geometry PASS, visual-development accepted states, native-source verified states, final production-approved states, and actual release-enabled states.

## 7. Production and quality gates

| Gate | Required evidence | Decision boundary |
|---|---|---|
| A0 identity | Character-specific high-resolution original identity master and owner-approved benchmark file hash | Owner visual identity approval per *new companion*, not per script |
| A1 asset source | One standalone native source per state with actual bytes, dimensions, SHA, rights/provenance | Engineer verifies; missing data FAIL |
| A2 dual anchors | Actual left/right iris, shoulders, head width and center inspected on image-bound landmarks; per-state report | Failing geometry returns for artwork correction, not silent normalization |
| A3 distinctness | Expression/pose readability vs nearest states; duplicate image/perceptual/face tests; full anatomy review | False acting/costume drift FAIL |
| A4 state registry | Per-image source, registration and approval ledger exact-hash correspondence, 33/33 valid production art | No invented owner approvals |
| A5 real runtime | Live FastAPI stage, 33 individual assets, tasks trigger correct state, desktop/mobile Chromium, reduced-motion and error fallbacks | Failures fixed before review |
| A6 owner release | Explicit owner approval of actual final image SHA(s) and release action | `release.enabled` may change **only** with explicit permission |
| A7 motion (deferred) | Native individually authored frame sequences, fixed anchors/camera, pixel-lock mask, ≥72 Idle/≥48 Working-Explaining unique frames at 24–30 fps, seam playback | Separate owner motion gate; no fake static wiggles |

**Strict separation:** Review-only installed art may be viewed and accepted as a **development/demo release** with `release.enabled=false`. That does not satisfy native-production approval. The current 33-state Albedo demo is the first integration target, not evidence of ten completed fleets.

## 8. Rendering and test rules

- UI swaps whole portraits in one fixed 4:5 box with opacity-only transitions. UI auras, holograms and workstation animations remain separate layers. Avoid stage jump, movement of the shoulders when switching states, stale filenames, missing-art badges on loaded states, or fake completion metrics.
- UI supports reduced motion. Validation checks unique img paths, HTTP 200, bytes/hash, image dimensions, state->asset mapping, error placeholders only when files truly missing, 1→33 autoplay, desktop/mobile visual captures.
- Every companion's 33-state artwork remains independent of Ops Deck directional sprites (different resolution/poses) and any deferred 3D/Live2D/native motion pipeline.
- No provider/account, browser profile, API token, local app SQLite database, or personal media in source archives or Git commits; allowlist exact intended art and manifest files.
- GitHub CI green must correspond to the **post-change commit SHA**, never inherited from an older commit.

## 9. Rollout sequence and owner's current release boundary

**Now (Albedo, Gate 4):** Apply reconstructed four-image owner-accepted *review-only* archive on a complete 33-pair checkout; verify protected 29 hashes, transactional rollback, real HTTP integration, push to `development/exodia-foundation`, run Chromium/CI and show build version. This authorizes development/demo delivery without falsely certifying native originals.

**Next (frontshell):** Show actual version + short commit SHA consistently; clean provider selector and prepare truthful API slots. Do not break browser tasks or change stored provider identifiers in a way that loses task history.

**Then (fleet):** After Albedo's integrated demo is accepted and this spec is recorded in GitHub, author each other companion's **identity standards and 33 independent state sources** in separately gated batches, respecting individual art look and source masters. No silent 297-image generation. Operations Deck sprites/animation are separate future approvals.

## 10. Authority and supersession

- Latest explicit owner request > exact hash-backed master and approved asset source > project governance docs > documented engineering plans > legacy lower-fidelity prototype policy.
- This new document consolidates and tightens the **current Albedo 33-state registry** while preserving stricter signed-off rules. Older `docs/companion_art_contract.json` contains a partly different vocabulary; do not quietly replace the present 33 keys. If desired, add a tested legacy-to-canonical mapping with no destructive change to stored history.
- Owner's 29 protected development portraits remain frozen; four newly accepted review art originals remain low-resolution, so native production stays blocked even after development integration. This is a **deliberate distinction, not a contradiction**.

## 11. Reconciliation with the active November 2026 governance

**Authority:** The repository-wide `SKILL.md`, `docs/EXODIA_STRICT_INSTRUCTION_COMPLIANCE.md`, `docs/EXODIA_STANDALONE_ASSET_ONLY.md`, `docs/ALBEDO_CANONICAL_DUAL_ANCHOR_GATE.md`, and `docs/ALBEDO_NATIVE_MOTION_GATE_V2.md` remain normative wherever stricter. This fleet specification does not weaken them.

| Older rule or apparent conflict | Enforced fleet rule |
|---|---|
| `docs/ALBEDO_PORTRAIT_STANDARD.md` historically allowed ±4.5% eye position and ±5.5% head width | Apply tightened **±2 px eyes / ±2 px shoulders / ±4 px head width**, physically measured; old loose thresholds are insufficient for native approval |
| That document suggested 4–8 frames for loops | Native motion remains separate: **≥72 unique Idle frames / ≥48 Working or Explaining frames at 24–30 fps**, and only after explicit motion authorization |
| `docs/companion_art_contract.json` contains older vocabulary | The actual `production/kiko/portrait_registry.json` canonical 20 expression and 13 action keys govern; never rewrite a legacy task record |
| Owner accepted 33 development designs and four lower-resolution replacements | A development demonstration is **not** proof of per-hash native art, human-confirmed physical geometry, or production release. Production registry stays pending for all 33 |
| Stated horizontal center x=768 without tolerance | **No automatic head-center geometry PASS** until an owner-approved horizontal tolerance and image-bound manual annotation exist |

The backend's real ten-companion roster (`orchestrator/app/companions/roster.json`) is the sole source of companion IDs; no additional alias or fleet identity may be introduced by this document. Albedo's internal ID remains `kiko`. No remaining companion artwork is authorized for generation by this spec alone.
