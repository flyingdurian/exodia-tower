# EXODIA Tower / Gate 4 targeted Albedo corrections

Owner directive dated **2026-11-03**. All output remains **development review art** until explicit image-hash-specific owner final visual approval. No production release or main-branch merge authorized.

## Owner source of truth

The authoritative illustration review is **`EXODIA TOWER / ALBEDO — ACTUAL STANDALONE ARTWORK REVIEW`**, the complete 33-portrait board. Board SHA-256: `f1b9e71ab0d2410f229918bdbef20e0f8bb1b9cf46b30354c742be5cb6b3be4d`.

All **29 non-target states are accepted for continued development and exact source/image SHA-256 locked** in `assets/review/albedo_core5/gate4_four_state_correction_lock.json`. Only four replacements are permitted:

| Board ID | State | Old review SHA-256 | Correction |
|---|---|---|---|
| 07 | `angered` | `a077efef47a94e371ae59c3475457ca68455737fe68e1945de540ed2854f02e3` | Read unmistakably irritated / upset, controlled anger; changed connected gesture |
| 08 | `awaiting_command` | `5f495c8ab760d598aaaff2980d29fbe095cb182e5445a87832784317ef91b4da` | Poised, calm, receptive and visibly listening/ready; not generic raised palm |
| 22 | `neutral` | `c5e06e112eccf607a98c18cd93c58a27f88c48c8443f7c3c9f757c427a680a86` | Balanced emotional rest, neither happy, sad nor intense |
| 29 | `tantrum` | `2212dd4cea7724affa66e6441bf2d76d958c14399c420a087250ad4411e7ea13` | Stronger frustrated outburst, active plausible limbs and distinct silhouette from Angered |

The old images remain in the live review app for comparison; none was replaced by a dashboard or proxy. All four new SHA fields remain null until actual original pixels are supplied.

## Correction asset creation and provenance

Use a rendering workflow that produces **four separate native or larger original character PNGs**, each genuinely reillustrated and independently posed. **Do not use Runway**. Do not extract from a contact sheet or introduce cloned bases. Preserve Albedo's approved identity and perspective.

In `correction_manifest.json` provide:
```json
{
  "schema": "exodia.gate4-corrections-input/v1",
  "states": {
    "angered": {
      "source_sha256": "<64-character hex of sources/angered_original.png>",
      "source_dimensions": [1856, 2304],
      "generator_model": "<the actual non-Runway model>",
      "generator_job_id": "<actual unique completed rendering job ID>",
      "generation_input_manifest_sha256": "<SHA-256 of actual generation request>",
      "pose_evidence_description": "<original, genuinely distinguishable acting and connected anatomy>",
      "derived_from_composite": false,
      "owner_approved": false,
      "production_release_enabled": false
    }
  }
}
```
Complete the same fields for `awaiting_command`, `neutral`, and `tantrum`. The example deliberately abbreviates the manifest: the intake requires **all four states at once**.

The archive must contain exactly `correction_manifest.json` and four separate `sources/<state>_original.png` files. Its originals must have at least 1536×1920 pixels; a source 1856×2304 is permitted through a symmetric 8-pixel left/right, 2-pixel top/bottom crop and **uniform** Lanczos downsample. Native-size originals are preferred.

### Fail-closed verification and integration

From repository root:
```bash
python orchestrator/tools/apply_gate4_four_corrections.py --verify-baseline
python orchestrator/tools/apply_gate4_four_corrections.py --archive four_independent_originals.zip --dry-run
python orchestrator/tools/apply_gate4_four_corrections.py --archive four_independent_originals.zip
```

Alternatively, start the **existing** FastAPI application and use the `/test-workbench` four-state correction upload, which calls `POST /api/albedo/state33/gate4-four-correction-import`. The former generic intake is closed to overwriting the 33-image owner-reviewed library.

The preflight checks: immutable 29 SHA pairs; all 33 baseline original/output bytes; exactly four original standalone PNGs; original generation job IDs and source hashes; native resolution with only controlled uniform normalization; no reused full or facial perceptual hash within the 33; no unchanged four-state image; no Runway; no fake owner approval. If any check fails, none of the four review images is replaced.

A successful import updates the four originals, review images, index entries and SHA-bound 28-state queue. It **does not** update the signed production registry or mark geometry/owner approval PASS. Run the independent landmark detector and full browser/CI tests afterward, then visually inspect all four original full-resolution images.

## Present blocker and exact status

The built-in LLM/image-generation attempt made another **dashboard collage with unverified PASS labels** rather than independent PNG originals. It was rejected. Higgsfield balance is **0 credits** with an eligible but inactive trial; Runway is explicitly prohibited. No four usable corrected standalone image files were generated in this pass.

**29 unchanged/locked + 4 previous originals still visible, replacements 0/4, production approved 0/33, release disabled.** The four-source rendering dependency requires a capable standalone generator or the four independent image files from the Art Director, not an additional engineering approval.
