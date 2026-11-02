# Albedo immutable dual-anchor gate — 2026-11-02

Canvas **1536×1920** (4:5). Eye-line **y=633.6 ±2 px**; upper-shoulder baseline **y=980 ±2 px**; horizontal midpoint x=768. Working, Explaining, Monitoring remain **visual style references**, not silently certified geometrical anchors. The existing gold previews currently fail the numerical audit, so the 28-state batch is locked.

`orchestrator/tools/audit_portrait_anchors.py` reads actual iris pigment and shoulder-edge pixels within image-bound search regions, rejects absent/ambiguous signals and checks distinct source hashes. It explicitly requires owner-reviewed search regions. This is *not* a general-purpose facial landmark detector; automated numeric output is not sufficient proof of a physically correct shoulder or anatomy.

`orchestrator/tools/reanchor_core5_preview.py` generates provisional rigid whole-image scale/translation previews for any of the five Core-Five states (including style references), without changing production assets. It requires real image-bound search regions and does not make normalized concepts into production masters. The script never sets approval flags. Local inspection measured Idle/Pointing near target after transform, but all five lack reviewed image-bound landmarks; gold Working/Explaining/Monitoring fail the new strict geometry, so the full 28-state batch must not start.

Run locally (with original core-five review PNGs and hash-bound search-region JSON):
```bash
python orchestrator/tools/audit_portrait_anchors.py --registry path/to/core5_registry.json --search-regions path/to/search_regions.json --asset-root path/to/core5_images --report core5_audit_report.json
```
A nonzero result is an expected hard gate, **not** permission to clone or fabricate states. The actual review package includes proof and hashes for two provisional reanchored images.

## Separate owner approval ledger — fail closed

The CV audit has two distinct evidence classes: pixel measurements (potentially
unreliable around violet costumes, hair, collars, and shoulders), and independently
reviewed production acceptance. `search_regions.review_status=owner_confirmed`
alone cannot unlock the queue; synthetic drawings can otherwise accidentally
appear compliant.

To be eligible for a five-of-five PASS, each core-state registry entry must have
unique `original_source_sha256`, `source_kind=independent_standalone_native`,
and `native_canvas=[1536,1920]`. The caller must supply an independently
verified approval ledger using `--owner-approval-ledger path/to/ledger.json`.
Its `states` entries must bind to the actual `image_sha256` and
`original_source_sha256`, and include a genuine nonempty
`approval_reference`, `anatomy_pose_review=completed`, and true
`eye_landmarks_reviewed`, `shoulder_landmarks_reviewed`, and
`distinct_state_reviewed`. Only record these after actual human inspection
of exact source files and output pixels. No approval ledger is present at this
checkpoint. Machine-readable claims alone are not proof of owner consent.

Example command, only **after** authentic review evidence exists:

```bash
python orchestrator/tools/audit_portrait_anchors.py \
  --registry path/to/native_core5_registry.json \
  --search-regions path/to/sha_bound_landmark_regions.json \
  --asset-root path/to/native_standalone_images \
  --owner-approval-ledger path/to/authenticated_owner_review.json \
  --report core5_anchor_audit.json
```

## Current review-only comparison

`python orchestrator/tools/build_core5_review.py` produces a SHA-verified
diagnostic from the four committed **prototype previews** and visibly marks
Pointing absent. The cyan/gold guide lines are desired **target** coordinates,
NOT measured facial or anatomical landmarks. Its JSON report intentionally
contains null measurements and false production acceptance. The original
1122×1402 concept sources (including true Pointing) were not attached to
this repository checkpoint; even if supplied, they remain concept art, not
native 1536×1920 production masters. The GitHub portrait-registry workflow
uploads the diagnostic board and inventory as review artifacts.

The 28-state generation queue must remain blocked until all five real native
masters and approvals have been independently verified.
