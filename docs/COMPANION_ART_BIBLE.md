# Exodia Tower — Companion Art Bible (production gate)

## Decision and authority
The owner approved the **Albedo mission complete** cinematic command-center design on November 1, 2026 and requested the same visual finish for the ten-agent fleet. The benchmark's visual consistency and character silhouette take precedence over earlier blurry expression crops. `skills/exodia-companion-art/SKILL.md` is the executable brief and `docs/companion_art_contract.json` is the exact scope.

**Benchmark master:** `albedo_s_mission_complete_command_center.png`, resolution 1448×1086, SHA-256 `bfc233740851980021ea0b479a1b4254574f6ca614e3a1e9cbb7bd66c03dc409`. Master PNG is available in the user's persistent ChatGPT Library at `/Exodia Tower/Benchmarks/Albedo - approved mission-complete benchmark.png` and as a handoff asset, **not presently in the repository**. Import without recompression into `orchestrator/frontend/companions/benchmarks/albedo_mission_complete_v1.png`; verify fingerprint before calling it committed. No need to regenerate the user-approved scene.

### Character identity and consistency
Albedo: refined silver-lavender hair (NOT pink), violet irises, light floral metallic hair ornament, white/lilac black/gold outfit, violet crystal; polished soft-glow anime shading. Only face/upper-body styling is fixed from the approved image. Full boots, back embroidery, exact skirt/panels and articulating reverse surfaces remain design decisions requiring approval.

For 10 agents, share premium material response, scene lighting, type/ornament craftsmanship and UI quality. Different classes need distinct silhouette/props, palette and recognizable faces. Preserve IDs:
- `kiko`: Albedo
- `router`: Riven
- `memory`: Mira
- `archives`: Lyra
- `inventory`: Pip
- `vault`: Aurelia
- `ninja`: Nyx
- `cache`: Mochi
- `strategy`: Orion
- `nova`: Nova

### Production matrix
| Type | Count per companion | Export guidance | Status |
| --- | ---: | --- | --- |
| Emotions | 20 | individual registered high-resolution transparent portraits, neutral/base face | not produced |
| Actions | 13 | genuine rig clips with matching poses and clean hand/foot contacts | not produced |
| Model turnaround | 5 | distinct coherent views, consistent proportions/costume | not produced |
| Detail close-ups | 4 | eyes, ornament, outfit, boots; readable textures | not produced |
| Rig | 1 | authored deformable skinned model, facial blendshapes, physics, clips | not produced |

### Quality acceptance
1. Compare the new Albedo neutral face with the approved original at 100%, 200% and thumbnail scale: fixed nose/eyes, hairline, accessories, colors.
2. Check silhouette/outfit consistency between front, side, back and back angle; if identity drifts, regenerate or repaint before art export.
3. Do not crop a single finished illustration into 20 expressions; paint/rig properly registered face features. Contact-sheet images cannot be sliced and passed off as HD sprites.
4. Action clips must contain real intra-body deformation, independent joints, foot locking and torso weight shift, rather than global sprite transforms.
5. Idle stage must display a readable character at modest scale and use adjacent negative space for responsive holo-workstation, task-linked cards and conversational gestures; no false telemetry.
6. Validate motion and reduced-motion variants in production browser; capture clips, not still screenshots as proof.

### Production filesystem (planned; not fake deliverables)
- `orchestrator/frontend/companions/benchmarks/albedo_mission_complete_v1.png` — approved benchmark, pending import.
- `orchestrator/frontend/companions/production/kiko/master/` — neutral turnaround masters.
- `orchestrator/frontend/companions/production/kiko/expressions/` — twenty registered high-res face renders.
- `orchestrator/frontend/companions/production/kiko/model/` — GLB/VRM or native editable mesh rig (requires license/runtime review).
- `orchestrator/frontend/companions/production/kiko/clips/` — 13 exported motions, viseme/blink idles.
- Replicate by stable internal agent ID for every agent, including `nova`.

### Rigging design decision
Because walking/running/jumping, five angles and boots are all required, **a skinned 3D master is the preferred path**: one coherent model, weighted skeleton, face blendshapes, cloth/hair spring bones, IK and independent animation clips. The 2.5D stage can render it with an orthographic view matching the painted benchmark. An artist-authored Live2D mesh is a valid alternate for high-quality front-view expressions, but not evidence of multi-angle full-body locomotion by itself. Existing puppet-lab cutout engineering remains developer-only.

### Status
Benchmark layout: **approved**. Albedo identity: **approved only to visible extent**. Pink-haired concept contact sheets: **rejected as identity art**, may guide information architecture. New rig/expressions/turnarounds: **not produced or accepted**. No externally generated board's text (“full-body rig ready”) establishes actual rig functionality.
