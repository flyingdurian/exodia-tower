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
- **Zero newly generated native expansion masters**: 28 slots deliberately
  display an honest *ART PENDING* visual. They do **not** reuse the Idle portrait,
  change its color, or substitute a thumbnail collage.
- **No certified native Core-Five masters**: tentative sign-off is explicitly
  limited to visual reference direction. The resampled 1536×1920 concept
  previews are not native masters; the strict head-width target was not met.
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

Each pending state uses a textual **no-art** placeholder with its own state
label and signal. The portrait camera/stage remains stationary. On desktop the
state rail and inspector scroll independently without pushing the portrait
offscreen. Mobile layout is separately checked in Chromium.

## Engineering verification

```bash
cd orchestrator
python -m pytest tests -q
# Browser checks require Chromium and Playwright:
EXODIA_VISUAL_QA=1 python -m pytest tests/test_gate3_33_browser.py -q
cd ..
python orchestrator/tools/audit_33_state_candidates.py --project-root orchestrator --report 28_review_audit_report.json
```

The last command **intentionally exits with code 1** until all 28 independent
source PNGs and SHA-bound human anatomical measurements exist. Its JSON report
lists the exact missing files and geometry evidence; a nonzero audit exit is
correct and is expected in the portrait CI workflow. The separate full
`portrait_registry_audit.py` production-release check must likewise remain
fail-closed until all 33 approved standalone masters exist.

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
