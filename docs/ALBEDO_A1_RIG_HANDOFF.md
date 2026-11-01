# Exodia Tower · Albedo A1 skeletal rig engineering handoff

**Checkpoint:** A1 skinned geometry and 13 skeletal animation curves. **NOT final artwork, facial rigging or owner-accepted locomotion.** Current development branch checked Nov 1 2026; no modifications to the main live task UI or AI providers.

## Assets

- `references/ALBEDO_APPROVED_STAGE_BENCHMARK.png` — original owner-approved command center design. SHA-256 `bfc233740851980021ea0b479a1b4254574f6ca614e3a1e9cbb7bd66c03dc409`.
- `references/ALBEDO_APPROVED_FULL_BODY_VISUAL.png` — full-body silver-lavender character drawing, accepted **visual style**. Concept, not a clean high-resolution transparent rig skin.
- `references/ALBEDO_TURNAROUND_CONCEPT.png` — front/side/back + skeletal annotation **concept**. Not mesh, editable skeleton or five independently approved modeling views.
- `orchestrator/frontend/companions/production/kiko/albedo_rig_proof.glb` — 35-skin-joint weighted original 3D proxy with 13 glTF animation clips, 6,972 vertices and 12,800 triangles. No cropped still-frame body cutouts. The geometry IS NOT faithful final Albedo character art and is not production-ready.
- `orchestrator/tools/build_albedo_rig_proof.py` — source generator, Python 3.10+, stdlib only.
- `orchestrator/tools/validate_albedo_rig.py` — strict structural validation of weights, joints, channel samples and release flags.
- `orchestrator/tests/test_albedo_a1_rig.py` — deterministic proof tests, malformed GLB and falsified release flag checks.
- `orchestrator/frontend/albedo_rig_a1.html` — WebGL2 rig evaluation, 13 actions, camera turn, joint overlays, reference comparison, pause and speed; developer-only.
- `previews/` — pre-rendered actual weighted-mesh frames/GIFs and contact sheet. **Preview GIFs are offline proof, not authorization to ship to live stage**.

## Windows installation and review

1. Extract this ZIP into your existing `C:\Users\TFBOSS\Documents\GitHub\exodia-tower` directory, preserving all relative folders. No existing task/AI source files are overwritten.
2. Run in PowerShell:

```powershell
cd C:\Users\TFBOSS\Documents\GitHub\exodia-tower
py -3 orchestrator\tools\build_albedo_rig_proof.py
py -3 orchestrator\tools\validate_albedo_rig.py orchestrator\frontend\companions\production\kiko\albedo_rig_proof.glb
py -3 -m pytest orchestrator\tests\test_albedo_a1_rig.py -q
cd orchestrator
.\.venv\Scripts\python.exe main.py
```

3. Open **`http://127.0.0.1:8765/assets/albedo_rig_a1.html`** in your installed Chrome. The model is **served through the existing `/assets` mount**, so no new FastAPI route is necessary. The viewer fetches `/assets/companions/production/kiko/albedo_rig_proof.glb`.
4. Change between Walk, Run, Sit, Typing, Pointing, Explaining, Celebrating and other modes. Rotate front/side/back, toggle joints and compare against the original art. If WebGL2 fails, check browser GPU support; keep the offline GIFs as limited proof only.

## Acceptance / next stage

**Structural gate PASS:** 35 joints, normalized weights, inverse binding, 13 clips, rig not marked production-ready. Four new tests passed locally on Python 3.13. Model import passed with `trimesh`.

**Browser runtime gate UNVERIFIED:** headless Chromium installation exists but the execution environment blocks local URL navigation (`ERR_BLOCKED_BY_ADMINISTRATOR`). No claim of end-to-end interactive WebGL acceptance.

**Visual quality gate BLOCKED:** engineering proxy is simplified. Next production pass requires topology/repaint matching approved silver-lavender full-body master, appropriate fully modeled rear costume/boots, clean weight painting, facial blendshapes/eyelids/visemes, foot IK without sliding, sitting/standing transitions and compliant hair/cloth physics. Screen-record full live 13-action proof before deployment. Do not substitute the previous pasted cutout figures or tiny expression atlas.

**Git integration:** this package is a standalone handoff of generated binaries and source. Merge only after checking main development branch and CI. A GitHub metadata checkpoint may reference this ZIP; the private repository does not automatically contain these binaries merely because the ZIP exists.
