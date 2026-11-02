# Exodia Tower project skills

## EXODIA_STRICT_INSTRUCTION_COMPLIANCE — highest-priority production directive (2026-11-01)

For any engineering directive with explicit steps, technical constraints, or sign-off gates, obey the steps in the specified order. Never generate raw image assets, animation frames, storyboards or speculative substitutes before ALL prerequisites for that stage are verified passing. Never claim approval, animation, deployment, or validation that has not actually occurred.

Before any Albedo or fleet portrait work, follow docs/EXODIA_STRICT_INSTRUCTION_COMPLIANCE.md, then skills/exodia-companion-art/SKILL.md. Exact approved native portrait canvas: 1536 × 1920 (4:5); static camera, pixel-locked anchors and separately authored frames. If the image model reports a changed ratio (such as 3:4), missing settings or other deviation, HALT before the next creative action; do not pad/upscale the result to conceal it. Each master keyframe requires explicit owner visual sign-off tied to its SHA-256 before sequence generation. CI and owner motion review precede production promotion.

Existing contact sheets, A2/A3 GIFs and proxy rigs are nonproduction concepts. Operations Deck sprites are a separate family. Preserve current provider workflows, main and draft PR #1.

Explicit owner override (2026-11-01): normalization of near-4:5 generated master candidates is allowed for **review only** using `portrait_standard.py normalize-generated`. A technical `PASSED` of the normalized canvas does not certify native source detail, actually detected facial anchors, owner approval, or sequence release. The original native-sequence restriction remains.


## EXODIA_STANDALONE_ASSET_ONLY — PERMANENT RULE (2026-11-02)

The owner rejects all auto-sliced production character artwork. Never crop portraits or sprites from composite summary boards, contact sheets, UI grids, thumbnail atlases, collage montages, or compressed review sheets. Never promote such crops by padding, upscaling, or changing their filename. Approved source boards remain style references only. The retired grid slicer and its CI are banned.

Each of the 33 production portraits must originate as a truly independent, standalone, native 1536×1920 PNG, with an image SHA-256, image-bound human-annotated facial landmarks, and direct owner approval. Every registration record and matching owner approval ledger row must include the same independently reviewed provenance record: schema exodia.independent-portrait-source/v1, source_kind independent_standalone_native, derived_from_composite false, native_canvas [1536,1920], original_sha256 matching the actual file, original_filename, source_method independent_image_render or standalone_artist_export, human_source_review completed.

Metadata alone does not prove source authenticity or owner consent; reviewers must inspect the original standalone file and the actual approval evidence. Missing or suspicious provenance MUST fail the importer and independent registry audit. No live promotion until all 33 pass. Deferred animation loops and Operations Deck sprites remain separate. Preserve live provider workflows.

See docs/EXODIA_STANDALONE_ASSET_ONLY.md.

## EXODIA_UNIQUE_STATE_ART_ONLY — permanent 2026-11-02
The 33-state proxy contact sheet and cloned/relabelled 28 portrait assets are rejected. Ban reuse of any base portrait image for another state with just changed captions, palettes, overlay effects or minor edits. No collage board slicing or source extraction.
A state without a genuinely independently authored expression or action pose, measured dual anchors (eyes and shoulders), verified original source identity, and owner sign-off MUST be `pending_production_art` with null approved hashes. Every verified original SHA-256 must be unique and each registration requires independent state_specific_visual_review='completed' based on real inspection. Do not fabricate approval or measure against target numbers alone.
Restrict the workbench to Idle, Working, Explaining, Monitoring, and true pointing-hand Pointing. If genuine Pointing art is not present in that runtime, show an unavailable slot; never display the old inaccurate proxy. Production release remains blocked.
