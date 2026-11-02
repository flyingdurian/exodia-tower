# EXODIA_STRICT_INSTRUCTION_COMPLIANCE

## Scope and priority
Superseding owner directive, 2026-11-01. Applies to all 10 AI companions, all technical constraints, architectural sequences and validation checkpoints. Explicit owner-defined sequencing overrides tool convenience, model defaults and assistant plans.

## Mandatory execution order
1. Inspect latest project source, owner-approved benchmark, required coordinates and constraints. Verify availability and SHA-256 of any required source; do not invent inputs.
2. Run a pre-generation preflight validating exact effective model parameters and prerequisite checks, and record a successful verification. No artwork is generated before this pass.
3. Generate ONLY the requested standalone master keyframe for the named state, at native 1536×1920 (4:5), after preflight. Do NOT generate sequences, variants, storyboards or unrelated art.
4. Independently inspect the master file's real dimensions, aspect, identity, anatomy, pixel registration and fixed camera. Record the exact file SHA-256 and master anchor positions: outer eye corners, face center, ornament attachment and both shoulders.
5. Present the master to the owner for direct visual sign-off. An assistant-authored approval flag does not count. Preserve a verifiable owner confirmation tied to that exact master and state; do not guess approval from related concept-board acceptance.
6. Only after explicit owner approval of that specific master, authorize independent HD animation frames for that state. Idle requires at least 72 frames, Working and Explaining at least 48 frames, at 24–30 fps, each native 1536×1920.
7. Validate every frame against the approved master and locked anchor grid: zero camera translation, pan, zoom, rotation or crop; no changes to hard-anchor pixels; only localized natural microgestures. Audit adjacent frame fluidity and last-to-first loop seam. No duplicated frames presented as interpolation.
8. Request visual animation acceptance and run local + GitHub CI gates. Production client integration and fleet rollout are forbidden until both technical validation and owner approval pass.

## Immediate failure cases
- Effective generator ratio differs from requested 4:5 (including silent 3:4 substitution), or output size is not native 1536×1920: STOP.
- Missing/invalid benchmark reference, unverifiable source, missing metadata, failed anchor checks or lack of owner approval: STOP.
- Existing compressed concept-board cells, re-encoded upscales, wobbled cutouts or interpolated slideshows: REJECT.
- Tool result claims success but artifact is unverified: report unverified status, not success.
- User requested master first: no sequence work, even if sequence generation might seem convenient, until the user approves the inspected master.

## Enforcement and accountability
Before each stage, record the required input, actual evidence, pass/fail result and exact SHA-256 where applicable. No fabricated test reports, evidence or approval records. Technical metadata cannot independently authenticate user consent; verify it against an actual user message or authorized approval record. A generated image does not prove pixel-locked anchoring by itself.

Production animation specifications are in docs/ALBEDO_PORTRAIT_STANDARD.md and docs/ALBEDO_NATIVE_MOTION_GATE_V2.md. Current master-generation/sequence gate remains BLOCKED pending verified source, exact-output generator settings, and explicit master approval. No live artwork replacement is authorized. This rule is not a claim that an external image generator is technically incapable of bypassing these steps; all app entrypoints must enforce it.

Keep main unchanged, PR #1 draft, and Operations Deck sprites independent of 4:5 portrait art.
