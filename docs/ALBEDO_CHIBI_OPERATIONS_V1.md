# EXODIA Tower — Albedo Operations Chibi Runtime V1

**Milestones:** A (sprite contract) and C scaffold (real command-center integration); frontshell status stream runs in parallel.  
**Feature branch:** `feature/lead/albedo-chibi-runtime-status-v1`, based on merged integration commit `e2398b7ef74bc183ad9f747f836d11b921bc041e`.  
**Artwork:** **40 slots intentionally pending. No 8-direction chibi frame is claimed to exist yet.**  
**Scope:** Albedo only (`kiko`). Liu Bei, Mira, Lyra, Pip, Aurelia, Nyx, Mochi, Orion and Nova art production is frozen by owner instruction.

## Identity / art contract

- The owner-provided eight-view Albedo turnaround is **design reference**, not production sprites. Do not crop eight figures from its composite background or invent missing walk cycles from still images.
- Asset manifest `orchestrator/frontend/albedo_chibi_manifest.json`, schema `exodia.albedo-chibi/v1`. Locked direction keys: `n, ne, e, se, s, sw, w, nw`. Screen X increases right; screen Y increases down; `n` faces toward decreasing Y.
- Art **per direction**: `idle_<direction>` (one independent idle frame), `walk_<direction>_00..03` (four separately authored walk frames). Total **8 idle + 32 walk = 40**. No mirror shortcuts. Character identity, crown/flower/headpiece, lavender hair mass, lilac-and-white dress with gold trim, limb continuity, back hair shape and footwear must read consistently under all rotations.
- Proposed nominal source frame canvas **192×256 transparent PNG** for chibi operations (separate from the immutable portrait canvas 1536×1920). Every production frame needs independent provenance, exact SHA-256, native pixel dimensions, owner frame/atlas approval, coherent foot pivot, side-by-side identity review and animation inspection. No approval, no release; no inferred sign-off from an uploaded composite.
- Anchor metadata normalized to each frame: foot `[.5,.94]`, shadow `[.5,.96]`; collision footprint radius `.022` in normalized operations-floor width. Anchors must coincide with the same real-world floor location across all frames. Scale is 80 px display height desktop and 66 px mobile; center-based X / foot-based Y transforms. These are prototype values subject to **measured** sprite QA before production.
- The manifest is **fail-closed**: `asset_status=pending_production_frames`, all 40 frames `src=null`, `sha256=null`, `approval_sha256=null`, `source_provenance=null`, and `production_release_enabled=false`. An approved-art mode is only accepted when every frame has a distinct, independently sourced exact hash and SHA-specific approval. The renderer hashes PNG bytes with the browser crypto API before showing a frame; missing or corrupt art falls back to a clearly labeled non-art technical marker.

## Runtime architecture

| Module | Role | External impact |
|---|---|---|
| `albedo_chibi_controller.mjs` | Pure deterministic heading, normalized floor stepping, distance-registered stride frames, task-zone routing, idle/walk transitions, clamped max delta | No provider code or API calls |
| `albedo_chibi_renderer.mjs` | Foot-anchored DOM sprite layer with technical marker before art approval; SHA-check each approved PNG before display | No portrait production flag modifications |
| `albedo_chibi_boot.mjs` | Connect `exodia:command-task` public events and selected companion to main command-center operations floor | No prompt/instruction leakage |
| `command_status.mjs` | At-a-glance selected companion, task owner, provider, task state, result, latency, background task count | Reads only already-visible public task records |
| `albedo_command.html/css/js` | Live `/` frontshell status strip and operations floor; development-only test controls inside a collapsed details element | Keeps existing portrait/command controls intact |

The five named, normalized destinations are Home `(0.17,.77)`, Terminal `(.79,.30)`, Waiting `(.50,.76)`, Results `(.82,.76)`, and Recovery `(.20,.31)`. Task mappings use **only public task phase + companion ID**, never a prompt body or private custom instructions:

- `queued/opening/researching/typing/submitting/running/rendering_media` → Terminal
- `waiting_for_reply/awaiting_operator` → Waiting
- `answered` → Results; `failed` → Recovery; `cancelled/draft/idle` → Home.

Chibi movement is suppressed when the currently selected task/companion is **not Albedo**. A non-Albedo selection never displays the Albedo actor. Repeated 650 ms task polling does not restart motion or walk frames. `requestAnimationFrame()` drives movement; speed is expressed in floor-normalized units per second, delta is clamped for tab suspension, direction follows the vector to the destination, and stride frames advance by physical distance rather than wall-clock time to reduce foot-slide. Reduced-motion preference snaps to destination.

**Temporary marker restriction:** the technical `A` position/orientation glyph is deliberately **not** an illustrated Albedo sprite; it exists only for real browser movement and zone validation. It must not be substituted for any missing production frame or represented as completed Milestone B.

## Frontshell / integration acceptance

- The actual `GET /` command page displays version, channel and 12-char SHA returned by `GET /api/build-info`, with `unknown` when the server cannot verify a Git commit. No hardcoded release SHA.
- Header distinguishes selected companion from selected task's companion owner; selected task, provider, task state, response status and observed latency; background task count is visible. Not-opened browser sessions are **not** presented as authenticated or ready; API transport options remain honestly unconfigured.
- Node and Python tests validate heading quadrants, 40-slot contract, no art promotion, floor registration, exact arrival, duplicate-poll behavior, lifecycle mapping, XSS-safe text rendering, build identity and preserved 33-portrait release lock.
- Real FastAPI/Chromium desktop+390px mobile test checks frame/status visibility, movement between actual floor zones, cancellation/result state routing and suppression when switching companions. CI artifacts include screenshots. This is a **frontend simulation plus real Chromium**, not authenticated ChatGPT/Gemini/DeepSeek/Ollama evidence.

## Milestone and platform sequencing

1. **A/C scaffold — in this PR:** manifest, controller, technical marker renderer, boot wiring, actual frontshell strip and UI/browser tests. No production sprite animation claim.
2. **B — gated art production:** 40 individually authored, visually consistent frames and SHA-verified owner-approved asset manifest. Owner art review required for native sprite sources and movement appearance; no composite cutouts.
3. **C/D completion:** swap the approved frame set, inspect true gait and transitions in all eight directions, measure foot drift, resolve occlusion/path collisions, and certify desktop/mobile fluidity before calling the chibi sprite done.
4. **Platform Milestones 1–4:** provider E2E verification (Cursor-owned transports), frontshell usability, task-driven companion behaviors, and persistence/retry/cancellation hardening continue in separate reviewed feature PRs. Fleet art remains frozen.

### Source / isolation safeguards

The original 33 Albedo review portraits and 29 protected pairs are untouched; `orchestrator/frontend/companions/production/kiko/portrait_registry.json` retains `release.enabled=false`; PR #1 remains draft. No backend provider implementations, stored task IDs, SQLite migrations, keys, cookies, or authenticated Chromium sessions are changed by this feature. The permanent owner checkout is not modified; run the preview in its own worktree and port 8767 with local-only data.

## Phase 2 gait/path and 40-frame source checkpoint

- 8×(idle + four walk poses) remain pinned to unique `idle_<dir>` and `walk_<dir>_00..03` source filenames under `orchestrator/frontend/albedo_chibi/frames/`. The directory is a **reserved destination**; no claimed PNGs are present yet.
- Movement uses physical floor-pixel aspect ratio to keep walk speed and frame progression constant in desktop/mobile views. Stride phase is continuous when a command changes the target; only a full arrived idle resets to frame zero.
- Optional registered floor-only obstacle rectangles are supported by a visibility-graph route planner using the character's collision radius. No furniture geometry is invented in the current uncluttered technical test floor; register measured geometry before enabling an obstacle.
- Shadow/floor CSS positioning comes from the same manifest anchor, not a separately guessed percentage. The renderer rejects a PNG if either its SHA-256 **or native 192×256 dimensions** differ.
- `python orchestrator/tools/audit_chibi_frames.py` checks all 40 source slots without accepting a cropped turnaround board. Pending status returns `PENDING_INDEPENDENT_ART_AND_OWNER_APPROVAL`; an approved manifest must include exact unique frame hashes, actual standalone source files, transparency, image size, an image-bound human-reviewed foot anchor, and SHA-specific approval. Automated checks alone do **not** certify anatomy or owner consent.
- Gate remains `production_release_enabled=false`. Final foot contact quality requires comparing *actual independently authored* frames on floor paths in all eight directions. **No claim of eliminated visual foot slide until those images exist.**
