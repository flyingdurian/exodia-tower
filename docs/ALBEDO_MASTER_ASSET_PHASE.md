# Exodia Tower — Albedo Phase A0 Production Asset Gate

Owner-approved visual identity reference: `albedo_s_mission_complete_command_center.png`, 1448×1086 PNG, SHA-256 `bfc233740851980021ea0b479a1b4254574f6ca614e3a1e9cbb7bd66c03dc409`.

## Implemented now
- Real in-app local visual reviewer: `http://127.0.0.1:8765/companion-art-qa`. Select the original approved reference from the downloaded archive, then select candidate transparent images and real motion video clips. File content remains local in the browser. Twenty expressions, thirteen actions, five turnarounds and four close-up groups are enumerated.
- Standalone `orchestrator/tools/companion_art_gate.py` requires two transparent high-resolution independently authored masters (>=2048px full body; >=1024px face), verifies PNG/WebP headers, hashes, paths and explicit human identity review. It ALWAYS marks rig readiness false.
- Regression tests use synthetic PNGs only; no synthetic test image is a companion asset.

## How to review
Open `/companion-art-qa` in the running local Exodia application. Load `albedo_mission_complete_v1.png` from the owner-approved benchmark package, then candidate files using the naming `kiko__happy.png` or `kiko__walk.mp4`.

After real production art and actual owner approval, copy `docs/albedo_master_manifest.template.json` to `asset_manifest.json` in the asset folder, point it at the images, and adjust the declared status truthfully. Run from repository root:

```powershell
python orchestrator/tools/companion_art_gate.py C:\path\to\albedo-master
```

## Acceptance status
**Only the original cinematic design is approved.** Independent full-body master, transparent face master, five-view turnaround, twenty independently painted expressions, and skinned/deforming action rig are NOT YET PRODUCED. The old cropped face atlas and pink-haired concept boards must not be promoted into the live stage. File format checks do not establish visual likeness or animation. An external reference-unavailable generation attempt requiring a paid tier was not submitted; do not claim any replacement master exists. The current task UI and provider implementations are intentionally unchanged.
