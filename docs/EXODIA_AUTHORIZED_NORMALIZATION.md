# Authorized high-resolution portrait normalization (2026-11-02)

The permanent ban on board slicing, collage crops and upscaling remains in force. **--normalize** is an explicitly authorized exception for independently rendered *larger-than-target original standalone images*. It performs center-crop and Lanczos downsampling without upscaling, never adjusts the character's face to fit target anchors, and preserves both the source and normalized PNGs in production for hash verification.

Place a standalone high-resolution PNG at assets/staging_intake/incoming/<state>.png. Registration/<state>.json must include:
- source_image_sha256, source_points_px (all seven coordinates independently reviewed on the original image)
- method="human_annotated_from_actual_image", human_review="completed", owner_confirmation_reference
- source_provenance with schema="exodia.independent-portrait-source/v1", source_kind="independent_standalone_native", derived_from_composite=false, native_canvas=[ACTUAL_SOURCE_WIDTH,ACTUAL_SOURCE_HEIGHT], original_sha256, original_filename, source_method and human_source_review="completed".

Approvals/<state>.json must include state_key, category, source_image_sha256, **identical source_provenance**, allow_normalization=true, normalized_visual_review="completed", approved_by="owner", owner_confirmation_reference (matching registration), and reviewed_by.

The approval evidence must be authentic and checked against the actual source and normalized composition; JSON alone cannot authenticate owner signoff. Without these fields the CLI fails with exit code 1. No landmarks are guessed or replaced with specification targets.

From the repository root, dry-run and commit:

```bash
python orchestrator/tools/ingest_standalone_portrait.py --state idle --source assets/staging_intake/incoming/idle.png --normalize --report normalize_idle_report.json
python orchestrator/tools/ingest_standalone_portrait.py --state idle --source assets/staging_intake/incoming/idle.png --normalize --commit --report normalize_idle_commit_report.json
```
The production asset is stored under frames/actions/<state>.png and its intact source original under sources/actions/<state>_original.png (expressions use their own family directory). The independent auditor reproduces the PNG using the stored original and transform, requiring exact normalized SHA-256. Individual acceptance does not enable release of the 33-state UI.

**Known blocker:** the 1856×2304 candidate is at a generation-job URL, not available as a local original PNG in this session; it cannot be committed or reviewed until its actual bytes and independently measured landmarks are available.