# EXODIA TOWER — Albedo A3 fidelity-first production gate

**Gate status: BLOCKED / NO APPROVED 3D MODEL.** This package is a concrete rejection test and modeling reference set, **not** a completed 3D character, rig, or a reason to accept the A1 proxy.

The owner-approved silver-lavender adult anime Albedo design remains authoritative. This bundle preserves the exact source bytes and SHA-256 values, the real A1 mannequin frame, and an objective *negative-only* detail check. Source images include a standalone front full-body illustration, front/side/back concept sheet, and prior mission-complete workstation artwork. They are concept references, not texture-sliced movement sprites or complete five-view geometry.

## Implemented
- Seven region-level checks anchored to the actual approved full-body illustration: face, hair, collar crystal, bodice, waist ornament, draped panels, boots. A low-detail region can reject; a high score never approves likeness.
- Source fingerprint check (rejects substitute concept images), candidate bounding-box input, JSON evidence report, and a visual comparison board using only the real locked artwork and rejected A1 render.
- Six local regression tests: original fingerprint, known mannequin rejection, correct-source cannot self-approve, tampered reference rejection, unsafe body bounds rejection, low-detail false model rejection.
- Original art image bytes are included for the user's local fidelity modeler; no images were AI-repainted or cut into reusable animation layers.

### Measured A1 result
The original A1 skinned GLB is real technical engineering geometry, but its *appearance* was rejected. `reports/rejected_a1.json` records the rejection zones and the `reports/albedo_a3_fidelity_rejection_board.png` is a side-by-side evidence board. At this gate, the existing A2 GLB validator also rejects the model because it is marked as an engineering proxy and has **zero textures and zero facial morph targets**.

### Run visual preflight after producing a candidate **GLB render**
Install optional QA dependencies in a local virtual environment:

```powershell
py -m pip install -r requirements-visual-qa.txt
py tools/albedo_visual_preflight.py --reference references/approved_full_body.png --render C:\path\to\new-model\front.png --bounds 100,60,920,970 --output C:\path\to\new-model\visual_preflight.json
py -m pytest tests -q
```

`--bounds` is the x1,y1,x2,y2 rectangle tightly enclosing the **rendered character**, measured from the actual candidate screenshot, not the reference source. The values shown are illustrative only and must be replaced with actual coordinates. For the rejected A1 example:

```powershell
py tools/albedo_visual_preflight.py --reference references/approved_full_body.png --render reports/rejected_a1_idle.png --bounds 81,75,390,592 --output reports/rejected_a1.json
```

**The only success status is `MANUAL_REVIEW_REQUIRED`.** It never means the candidate is approved. Render all five genuinely different camera angles, inspect facial likeness and costume under an agreed neutral studio light, rotate the model live, check UV seams and depth, and obtain direct owner approval before resuming production rigging.

## What remains to complete the gate
- A dedicated **authored high-fidelity full-body 3D sculpt** (Blender editable master) matching the face, silver-lavender strand hair, floral metallic ornament, violet crystal, embroidered white/lilac/black/gold bodice, draped cloth, correct knees, hands and decorated boots.
- Three fully modeled views including unseen back surfaces. The concept sheet is not a working mesh; interpolate its details carefully without inventing identities.
- Five independent 3D camera renders from one model plus an actual live orbit demo, UV/geometry inspection and face close-up. Preserve original mesh file, textures and mesh topology for further review.
- Explicit owner acceptance of **model appearance first**, then binding to the existing skeleton, reweighting cloth/hair, blendshapes, and testing action clips. Do not apply the approved illustration as a flat poster texture to pass the front view.

## Provider feasibility checked 2026-11-01
Connected Higgsfield workspace reports free plan / **6 credits**. Tripo H3.1 multiview is **18 credits**, H3.1 single-view **18 credits**, other full-textured options at least **11 credits**. A 1-credit body-shape-only extractor omits the character-specific hair/costume/face and is not an appropriate substitute. No paid generation was submitted, and no high-fidelity 3D model was produced in this checkpoint. Blender is also not available in the execution environment used to build this QA package.

## GitHub integration and scope
See `docs/COMPANION_ART_BIBLE.md` and `skills/exodia-companion-art/SKILL.md`. Keep provider, Gemini and ChatGPT actions intact. Leave old A1 proof isolated. No change to the live task-stage rendering until high-fidelity model has been approved.