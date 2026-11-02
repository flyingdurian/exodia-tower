# Exodia Tower — A2 Albedo visual modeling gate
Status: **engineering/model intake implemented; finished high-fidelity 3D character NOT YET PRODUCED OR ACCEPTED**. Owner explicitly rejected the A1 primitive mannequin as visual artwork. It remains isolated as a technical skinning demonstration and is never a live-stage fallback.

## Owner-approved source hierarchy
1. Mission-complete illustration, SHA-256 `bfc233740851980021ea0b479a1b4254574f6ca614e3a1e9cbb7bd66c03dc409` (1448×1086): facial identity and command UI/style.
2. Silver-lavender full-body concept, SHA-256 `ddf1cc58e770d7cc99ffc3b2bd5a04ec77f720b05b8c96baf214090c899fb082` (1024×1536): anatomy, outfit, hair, accessories, boots.
3. Rig-development/turnaround illustration, SHA-256 `787fa6009d504083a927c81c97dec1b01f3add6e1a6f5dacd7516f4789abf480` (1448×1086): **front, side and back** styling; this is not a five-view genuine mesh.
Sources are preserved in the A2 visual modeling kit. The original body painting is not a 2048px transparent animation asset. Do not stretch/crop it into a fake 3D surface.

## Locked visual specifications
- Violet anime eyes, same eye spacing/head silhouette and bangs as approved full-body source; distinct pale silver-lavender volumetric hair, not saturated pink.
- Floral gold/white hair ornament and gold orbital structure; amethyst collar gemstone, black-and-gold collar, white/lilac layered outfit, independent draped sleeves and skirt cloth, slender proportionate hands, boots with visible construction and gemstones.
- Surface must have coherent **real depth** from the sides and back. No sprite planes, cylindrical noodle limbs, single purple cone skirt, untextured primitive face, or uniform-material disguise.
- Visual acceptance first: front, front 45°, true side, back 45°, back, from the **same unanimated 3D model** with consistent lighting and same framing. Include face and footwear closeups. No claim of production status from material count or vertices.
- A1's 35-bone rig is an optional reference for later retargeting; it must not dictate Albedo's face or body volumes.

## Executable files
- `orchestrator/tools/validate_albedo_lookdev.py`: checks a candidate's GLB metadata, five distinct PNG angle captures, source hash contract and review states. Structural intake never grants visual approval.
- `docs/albedo_a2_model_submission.template.json`: status must remain pending until separate owner visual acceptance.
- `orchestrator/frontend/albedo_model_review.html`: local-only browser comparison for camera-matched owner inspection.
- Full downloadable A2 modeling kit additionally includes `blender/albedo_lookdev_setup.py` and the exact source artwork. Its Blender script installs reference images, lights and orthographic cameras and can render five views from an existing candidate GLB. It does NOT fabricate a character.

## Advancement gate
Candidate modeling must pass:
- independently authored multi-material textured GLB with clean anatomy and model identity
- distinct five-angle 1024px owner-review renders
- visual likeness to approved reference (human judgment, with 12 inspection criteria)
- standalone accept/reject by owner before any blendshapes, skeletal retarget, or production app changes.

**Do not claim a production character exists** until actual high-fidelity editable mesh and owner review are present. Keep Gemini/ChatGPT and the currently approved 2D companion UI untouched.

External Tripo H3.1 multiview generation quote was **18 credits**; no job was submitted or charged. Automated image-to-mesh output still needs artist review and cleanup.
