# EXODIA / ALBEDO — Core Five real-source alignment checkpoint (2026-11-02)

## Source verification is complete; production release remains blocked

The user-supplied, directly readable archive
`EXODIA_TOWER_HANDOFF_WITH_CORE5_SOURCES_2026-11-02(1).zip`
was verified byte-for-byte (SHA-256
`24553003a69c133d1c9036c36abada89dd15a608a78f2bd63f265923c8d60c21`).
All five original `1122×1402` PNGs matched the exact SHA-256 values in the
archive's `EXODIA_CORE5_SOURCE_MANIFEST_2026-11-02.json` (manifest SHA
`081bb91bf3a23f7bb395ee047a8bc4d7d66647df902851364de5b8de2db4f966`).

The revised Idle and the **true extended-index-finger Pointing** original
matched their hashes. The prior GitHub staging previews are not suitable
substitutes. The companion style benchmark is an independent `1448×1086`
reference and was **not** substituted for a Core-Five state.

The actual portrait originals and large binary review PNGs were produced in
the conversation workspace, not uploaded into GitHub through the
text-only contents connector. The immutable checksums and audit measurements
are committed at
`assets/review/albedo_core5/verified_concept_pixel_telemetry_2026-11-02.json`.
The downloadable full-resolution review package and five-state contact sheet
are available in the originating ChatGPT conversation. **Do not imply that
these exact PNGs are in the Git repository.**

## Actual eye and shoulder pixel scan (resampled review only)

All outputs are 1536×1920 PNGs generated with one **uniform scale and
translation** applied to an independently verified 1122×1402 original. A
bounded two-pass feedback step corrects the source-space transform based on
real CV landmark detection from the output PNG; it never warps a previous
preview. Eye target `y=633.6±2px`, shoulder midline target
`y=980±2px`. The registered output hashes permit independent checking.

| State | Eye y | Eye delta | Shoulder y | Shoulder delta | Approx. head width | Provisional numeric |
|---|---:|---:|---:|---:|---:|---|
| Idle | 633.672 | +0.072 | 980.5 | +0.5 | 587.93 | PASS |
| Working | 633.659 | +0.059 | 980.0 | 0 | **692.98** | PASS |
| Explaining | 633.613 | +0.013 | 979.5 | −0.5 | 649.28 | PASS |
| Monitoring | 633.642 | +0.042 | 980.0 | 0 | 635.65 | PASS |
| Pointing | 633.676 | +0.076 | 980.0 | 0 | 592.25 | PASS |

**Risk:** Working's estimated head width of 692.98 is ~12.79% over the
614.4px target; calibrated Working loses more peripheral composition
because its source facial/shoulder spacing differs. Shoulders are naturally
asymmetric: the current audit uses the **mean** of two gradient picks and
does not prove each shoulder separately falls within ±2px.
Visual confirmation must ensure gradients correspond to actual upper shoulder
contours rather than hair, collar or costume details. Iris center and shoulder
input coordinates were selected through assistant visual inspection and are
**not** owner-reviewed or clinical-grade anatomy labels.

The precise CLI `audit_portrait_anchors.py` run against all five review
previews returned exit code **1**: **0/5 production PASS**,
`full_batch_unlocked=false`. For every state the explicit blocking errors
were `search_regions_not_owner_reviewed`,
`native_standalone_source_not_verified`, and
`owner_hash_bound_approval_missing`. This is correct behavior.

## Next owner visual approval boundary

Owner must inspect the full-resolution review package and either accept the
**visual framing target for future independently generated native masters**
or request specific composition revisions. No owner-approval ledger has
been written and the synthetic numerical green labels are **not** an art
release. The 5 concept previews are resamples, not independently generated
native 1536×1920 art.

All five production masters still require genuine native 1536×1920
independently authored artwork (or another owner-approved provenance
solution that satisfies the native-source audit), further hash-bound
anatomical review, owner sign-off on exact binary hashes and a new production
registry audit. Then Gate 2 may be unlocked. The remaining 28-state generation
must stay at zero until the **full five-state prerequisite** is genuinely met.
`release.enabled` remains false for all 33 states.

The Gemini/browser, manual ChatGPT handoff and Ollama workflows are not
modified by this art checkpoint.

## Engineer commands

```powershell
python orchestrator/tools/recover_core5_sources.py --bundle "<direct ZIP path>" --out-dir review_art/original_core5 --report review_art/source_recovery.json
# Start with the source-SHA-bound, visually inspected annotations in this
# checkpoint, NOT with fabricated target-derived coordinates.
python orchestrator/tools/calibrate_core5_concepts.py --originals review_art/original_core5 --annotations review_art/annotations.json --output-dir review_art/concept_previews --report review_art/review_telemetry.json --board review_art/five_state_comparison.png
# The audited preview must still fail production gate (exit 1).
python orchestrator/tools/audit_portrait_anchors.py --registry review_art/concept_previews/core5_audit_input_registry.json --search-regions review_art/concept_previews/core5_audit_search_regions.json --asset-root review_art/concept_previews --report review_art/production_audit.json
```
