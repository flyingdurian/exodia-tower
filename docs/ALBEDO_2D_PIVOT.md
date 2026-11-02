# Exodia Tower — Approved pivot to 2D illustrated companions (2026-11-01)

## Decision
The owner explicitly deferred the premium 3D sculpt and skeletal-rig project. The active delivery target is **independent high-resolution 2D still portraits for states and emotions, independently authored action illustrations, plus directional sprites for roaming the Operations Deck**. The finished Albedo design is the fleet-wide **style** reference, not permission to copy her identity to other agents. 3D remains future scope; preserve the A1 experimental proxy only as a developer test and never display it to users.

## Source fidelity
- Owner-approved silver-lavender Albedo full-body source: `elegant_lavender_crystal_fantasy_gown.png`, 1024×1536, SHA-256 `ddf1cc58e770d7cc99ffc3b2bd5a04ec77f720b05b8c96baf214090c899fb082`.
- Approved front/side/back turnaround source: `albedo_rig_development_sheet.png`, 1448×1086, SHA-256 `787fa6009d504083a927c81c97dec1b01f3add6e1a6f5dacd7516f4789abf480`.
- Previously locked command-center layout benchmark SHA-256 `bfc233740851980021ea0b479a1b4254574f6ca614e3a1e9cbb7bd66c03dc409`.
- Maintain violet eyes, pale silver-lavender hair, delicate gold floral halo accessory, amethyst crystal, intricate white/lilac/gold dress and boots. No saturated pink redesigns or face morphology drift.

## Production artifacts
1. **20 separate expression stills** from `docs/companion_art_contract.json`, individually authored at >=1024px native height. The current ~100px expressions from overview boards are for *thumbnail-scale inspection only*; NEVER enlarge them into 400px hero portraits.
2. **13 action illustrations** matching the approved pose list; no sentence or icon relabeling a duplicate photo as a new pose.
3. **Operations Deck directional sprites**: initial proof front, back, left, right at a consistent 128×196 transparent registration; additional angles / poses must be independently painted where the original turnaround does not exist. A horizontal mirror is temporary navigation proof, not a distinct modeled view.
4. **Frame-authored motion loops**: idle, walk, run, interactions, sit, sleep, wake; repeated or globally wobbling whole-body stills do not constitute walk animation.
5. **Living-companion idle behaviors**: glance at mission monitors, holo-analysis, review reports, tea break, stargaze, greet colleagues, react to a real task event. Never invent progress/results.

## Current QA verdict (not production sign-off)
A local review pack was created containing 3 transparent deck orientations from the approved turnaround (+1 mirrored direction), 20 isolated low-resolution thumbnails, 13 action miniatures, and a standalone interactive Operations Deck *demo-only* page. These thumbnails are insufficient for large stage portraits and do not meet the independent-art requirements. Two separately generated 2K image candidates (happy and serious) exist via external image-generation jobs but could not be retrieved for independent pixel-level review in this runtime and must not be accepted on a filename or tool-success message alone. Five expression generation requests were rate-limited and not completed. The old default atlas remains unapproved.

## Integration gate
Until owner visual approval, do not modify `orchestrator/frontend/albedo_command.html`, `albedo_experience.mjs`, provider bridge, or `/api/companions` art readiness. No production-ready mark. The review pack is separate from the GitHub working branch and can be imported in a future authorized step after native-size and consistency checks.

Machine-readable gates: `docs/companion_2d_requirements.json`. Current 3D rigs, tools and approved historical artwork remain preserved; the active strategy has changed, not their historical purpose.
