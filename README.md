# EXODIA Tower — Albedo 33-State Development Workbench

The development branch `development/exodia-foundation` contains the actual **FastAPI
and Playwright-backed EXODIA Tower** and a 33-state art-review workbench. This
is **not** a 33-image production-art release. Production assets, image-specific
owner approvals, and the final artwork release gate remain missing.

## Start the working application

**Windows** from repository root: double-click `launch_workbench.bat`. It
launches `orchestrator/main.py` under FastAPI and opens
`http://127.0.0.1:8765/test-workbench`.

**Linux/macOS**: `bash launch_workbench.sh` (uses the same FastAPI service).

To install dependencies before first launch, run from the repository root:

```bash
python -m pip install -r orchestrator/requirements.txt -r orchestrator/requirements-portrait-qa.txt
python -m playwright install chromium
```

Alternatively start the server manually:

```bash
cd orchestrator
python main.py
```

The EXODIA command center remains at `http://127.0.0.1:8765/`.
`/test-workbench` and `/state33-review` open the same 33-state review UI.
`/core5-review` opens the older five-source QA page.

**Important:** Do **not** run `python -m http.server` for the workbench.
The new UI uses `/api/albedo/state33/manifest` and other real FastAPI routes;
static hosting returns missing API responses and cannot run the 33-state demo.

## What is and is not present

- **33 real state definitions**: 20 expression states and 13 action/status
  states. All are selectable, including the 28 newly authorized review states.
- **Five SHA-verified concept references**: the Gate 1 review ZIP contains
  independently authored Idle, Working, Explaining, Monitoring and genuine
  extended-finger Pointing concepts. Their original sources measure 1122×1402.
- **28 distinct production art briefs**:
  `assets/review/albedo_core5/authorized_28_state_art_queue.json`. Each brief
  requires a unique original body/face pose and source-generation provenance.
- **33 verified independently generated review originals**: five new 1856×2304
  Core-Five artwork candidates plus all 28 individual expansion states.
  The 27 remaining expansion PNGs and five Core-Five candidates were generated
  as separate high-resolution portrait renders via Runway, and Celebrating
  was generated separately via Higgsfield. Their actual bytes, source hashes,
  job IDs, and 1536×1920 normalized PNGs are committed.
- **66 real PNG files in the workbench**: 33 original high-resolution sources
  under `orchestrator/app_data/albedo_33_review/sources/`, and 33 native-size
  review PNGs under `orchestrator/app_data/albedo_33_review/images/`.
  The FastAPI workbench prefers actual generated Core-Five artwork over
  optional 1122×1402 concept previews.
- **Artwork generation is complete for visual review, but geometry, facial
  identity continuity, anatomical articulation and owner sign-off remain
  open**. The recorded Celebrating pixel scan fails eye and shoulder anchors.
  No verified numeric proof yet exists for the other 32 image states. All
  production-masters remain unapproved.
- **All 33 production portrait registry entries remain
  `pending_production_art`**, release remains disabled and PR #1 stays draft.

## Import the five original concept review previews

After opening `/test-workbench`, use **Gate 1 Core-Five review ZIP** to select
`EXODIA_CORE5_GATE1_REAL_SOURCE_VISUAL_REVIEW_2026-11-02.zip` from the Gate 1
conversation artifact package and select **Load 5 references**.

The FastAPI importer checks all five standalone `originals/*.png` SHA-256
hashes **and** all five `aligned_previews/*_aligned_review.png` SHA-256
hashes against pinned provenance in the repository. Imported images stay
**locally** under `orchestrator/app_data/core5_review`, excluded from production
registry promotion. After a successful import, switch between all five actual
art pieces with the state menu or keyboard arrows.

Use **Additional native artwork review ZIP** to import separately generated
native 1536×1920 state candidates. The ZIP must include
`review_batch_manifest.json`, `sources/<state>_original.png` and
`images/<state>.png` for one or more of the 28 additional states, with
independent original generator job IDs, manifest hashes, matching source/output
SHA-256, native-size proof, and distinct state-specific pose descriptions.
The importer checks for duplicate SHA, near-cloned compositions, mismatched
dimensions and unsafe ZIP entries. It does **not** certify anatomy or convert
unapproved art into a production master.

### Controls and safety

Use the state rail to navigate all 33 states, change cross-fade duration,
toggle autoplay, use Left/Right arrows, copy SHA telemetry, and enable read-only
following of the active local task state. The main task app still uses the
approved Gemini and supervised ChatGPT integration; this art room does not
interfere with task dispatch or provider sessions. Warning/focus/celebration
auras are simulated UI effects and are independent of PNG artwork.

All 33 state selections now resolve to individually generated, SHA-checked
PNG review images served by the same FastAPI workbench. The portrait camera
remains stationary through transitions. The state rail and inspector scroll
independently on desktop, with mobile Chromium regression testing. The
underlying production registry remains intentionally disabled.

## Engineering verification

```bash
cd orchestrator
python -m pytest tests -q
# Browser checks require Chromium and Playwright:
EXODIA_VISUAL_QA=1 python -m pytest tests/test_gate3_33_browser.py -q
cd ..
python orchestrator/tools/audit_33_state_candidates.py --project-root orchestrator --report 28_review_audit_report.json
```

The 28-state audit command now reads real image files, measures what has
genuine annotated pixel search windows, and intentionally fails until every
state has independent measured anatomical landmarks and image-specific owner
approval. A red **production** audit after artwork generation is correct and
does not mean the 33 real file hashes are invalid. The separate
`portrait_registry_audit.py` production-release check must remain fail closed
until all 33 owner-certified originals exist.

GitHub Actions checks the primary application Python/Node suites, image
source/registry gates, and real desktop/mobile Chromium workbench screenshots.
Review the status of the latest commit before reporting CI success.

## Immutable geometry and owner gate

Every native 1536×1920 (4:5) Albedo master must satisfy measured iris midpoint
`y=633.6±2` px, true anatomical shoulder baseline `y=980±2` px, head width
`614.4±4` px, and center `x=768` px with consistent apparent perspective.
The audit must report left and right landmarks separately, correct image SHA,
eye separation, asymmetry, image cropping and unique provenance. A single CV
gradient peak is not proof of anatomical identity, and a numeric PASS is not
a production approval.

The Core-Five tentative visual sign-off is recorded in the production registry
as **reference metadata only**. Final production activation requires
independently authored native portraits, image-specific owner approval and
all 33 production release audits. **Never insert automatic owner approvals,
relabeled clones or composite-board crops as missing assets.**

## Gate 4 — 33 genuinely independent 2K source portraits verified

- **Production review images:** 33 of 33 independent original PNGs plus 33
  **1536×1920 PNG review images**, each source and output bound to exact SHA-256
  in `orchestrator/app_data/albedo_33_review/review_index.json`.
- **Runway:** 32 separately rendered 1856×2304 PNGs; provider task IDs,
  original SHA and normalized SHA are in
  `assets/review/albedo_core5/gate4_runway_verified_batch_{1,2,3,4}.json`.
- **Celebrating:** one Higgsfield 1856×2304 original, SHA-256
  `25affe7f46d60cdee0c016ec691a997d22963ee62f77bb8107dcaee4cbb24759`,
  normalized SHA `cc4612e7565f6659e5349fdf20d9daa9c795fbb0e9a7fab87fd45c8e9c56c08e`.
- **Original file verification:** automated GitHub art-staging run
  `41754197781` succeeded and committed all 66 PNGs on development.
- **Geometric calibration not approved:** Celebrating's provisional actual
  iris midpoint y=519.427 vs target 633.6 ±2, shoulder midpoint y=869.5
  vs target 980 ±2; fails both. Other states have no owner-certified
  eye, shoulder, head-width and center landmarks yet. Do **not** mark
  any production master approved on basis of correct canvas or hashes alone.
- **Distinctness:** all 33 source SHA-256 hashes and all 33 review PNG SHA-256
  hashes are unique. Structural near-duplicate image screening surfaces
  pairs for manual human review; a distinct file hash does not establish
  distinctive facial acting or full character identity preservation.
- **Owner safety:** the production registry still has all 33 entries
  `pending_production_art`, `release.enabled=false`, and draft PR #1
  remains unmerged. The 33/33 artwork-intake metric does not change the
  separate 0/33 owner-certified production-art count.

See `assets/review/albedo_core5/gate4_all_real_33_state_byte_audit.json`
and the state33 FastAPI manifest for per-state evidence. GitHub Actions runs
the 33-state delivery/asset/Chromium tests.

### Launching the complete illustrated review

```bash
git checkout development/exodia-foundation
python -m pip install -r orchestrator/requirements.txt -r orchestrator/requirements-portrait-qa.txt
python -m playwright install chromium
bash launch_workbench.sh
```

On Windows, substitute `launch_workbench.bat` for the last command. Open
`http://127.0.0.1:8765/test-workbench`, enable **Auto cycle**, and watch the
same camera cross-fade through 33 distinct individual portrait files. Click
any state to see source/output SHA-256 and honest geometry status.
