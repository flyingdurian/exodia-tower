# Albedo Core-Five Gate 1 — source recovery and measured calibration

**Current checkpoint:** BLOCKED by unreadable source ZIP bytes in the project Library.
This is distinct from an incorrect SHA-256 or actual measured anchor failure: no
five-source anatomical measurement has yet been performed.

## Canonical source provenance

The approved design references are five **independently authored 1122×1402
concept PNGs**, with the exact expected filenames and SHA-256 values frozen in
`orchestrator/tools/recover_core5_sources.py`. The revised Idle is
`albedo_in_a_celestial_orbital_halo.png`; the real extended-index-finger Pointing
is `albedo_s_celestial_pointing_portrait.png`. **Never use the old GitHub Idle
preview or a proxy Pointing to replace them.**

The source bundle is reported in the Library at
`/EXODIA Command/EXODIA_TOWER_HANDOFF_WITH_CORE5_SOURCES_2026-11-02.zip`
(13,938,835 bytes). In this execution environment `files.materialize`
returned `This Project file does not have an authorized raw-byte materialization
path.` No source images were extracted from this reported Library file.
The metadata does not establish image hashes, actual source dimensions or anatomy.

The extraction utility refuses missing images, duplicate basename collisions,
ZIP traversal, oversized members, mismatched SHA-256, invalid PNGs or wrong
concept dimensions. It preserves valid originals without modification and
records any included asset-manifest filenames and hashes.

## Execute in strict order on Windows from the repository root

After placing the **actual ZIP bytes** on your local filesystem:

```powershell
python -m pip install -r orchestrator/requirements-portrait-qa.txt

python orchestrator/tools/recover_core5_sources.py `
  --bundle "EXODIA_TOWER_HANDOFF_WITH_CORE5_SOURCES_2026-11-02.zip" `
  --out-dir "review_art/original_core5" `
  --report "review_art/core5_source_recovery.json"
```

The recovery utility must emit `PASS_CONCEPT_RECOVERY_ONLY` for **all five**.
A valid 1122×1402 concept is not a true native 1536×1920 production master.

Open each original at pixel-level resolution. Use the exact source-bound
`assets/review/albedo_core5/source_anatomy_annotation_template.json` to record
the visible left/right iris centers and **true outer upper shoulder positions**
(not hair, collar, shoulder ornament or garment edge), and approximate true
head width, all measured in the **1122×1402 original coordinate system**.
Set `review_status` to `human_anatomical_review_completed` only after real
human inspection; this is not owner sign-off for production.

```powershell
python orchestrator/tools/calibrate_core5_concepts.py `
  --originals "review_art/original_core5" `
  --annotations "review_art/source_anatomy_annotations.json" `
  --output-dir "review_art/aligned_concept_previews" `
  --report "review_art/core5_alignment_review.json" `
  --board "review_art/core5_comparison.png"
```

The output contains distinct uniform-scale and translation review previews,
per-image original/output SHA, transform, predicted anchor positions, **actual
pixel-scanned** eye and shoulder locations/deltas (or explicit detection error),
scale/head-width warnings, and a five-column comparison with cyan/gold target
guides. This script invokes the existing production
`audit_portrait_anchors.audit()` on the resulting output images with the
SHA-bound search windows.

**The production audit must fail:** converted concepts are marked
`resampled_concept_preview`, not `independent_standalone_native`; no genuine
owner-signature ledger is supplied. Numerical output can contain false iris or
collar/hair edge picks: human review of exact pixels and anatomical features
remains mandatory. A predicted affine coordinate is not a pixel measurement.

## Native production art and authorizations

Corrected concept previews are for review only. Fresh independently authored
native 1536×1920 PNG masters are required for **all five** states before
production certification. Never pass resampled previews as genuine native
source artwork. Measure resulting native masters against eye y=633.6±2px,
upper shoulder y=980±2px, center x=768px and approximate head width 614.4px.
The independent native-source SHA, anatomical verification and actual owner
approval must agree on the exact image before any gate is advanced.

The **28 remaining portraits** and the full 33-state release are separately
locked. The benchmark artworks and Gemini/ChatGPT/Ollama task integrations
must not be modified by this recovery work.

## Gate status

See `assets/review/albedo_core5/source_access_report.json` for the per-state
failure matrix. It contains no fabricated detected landmarks or delta values.
Visual comparison cannot be completed until the actual originals are accessible.

Tests: `python -m pytest -q orchestrator/tests/test_core5_gate1_recovery.py`.
These prove safety using synthetic fixtures, not production-art acceptance.
