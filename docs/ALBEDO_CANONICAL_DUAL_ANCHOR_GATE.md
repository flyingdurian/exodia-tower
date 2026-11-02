# Albedo immutable dual-anchor gate — 2026-11-02

Canvas **1536×1920** (4:5). Eye-line **y=633.6 ±2 px**; upper-shoulder baseline **y=980 ±2 px**; horizontal midpoint x=768. Working, Explaining, Monitoring remain **visual style references**, not silently certified geometrical anchors. The existing gold previews currently fail the numerical audit, so the 28-state batch is locked.

`orchestrator/tools/audit_portrait_anchors.py` reads actual iris pigment and shoulder-edge pixels within image-bound search regions, rejects absent/ambiguous signals and checks distinct source hashes. It explicitly requires owner-reviewed search regions. This is *not* a general-purpose facial landmark detector; automated numeric output is not sufficient proof of a physically correct shoulder or anatomy.

`orchestrator/tools/reanchor_core5_preview.py` generates provisional rigid whole-image scale/translation previews for Idle and true Pointing, without changing production assets. The script never sets approval flags. Local inspection measured Idle/Pointing near target after transform, but all five lack reviewed image-bound landmarks; gold Working/Explaining/Monitoring fail the new strict geometry, so the full 28-state batch must not start.

Run locally (with original core-five review PNGs and hash-bound search-region JSON):
```bash
python orchestrator/tools/audit_portrait_anchors.py --registry path/to/core5_registry.json --search-regions path/to/search_regions.json --asset-root path/to/core5_images --report core5_audit_report.json
```
A nonzero result is an expected hard gate, **not** permission to clone or fabricate states. The actual review package includes proof and hashes for two provisional reanchored images.
