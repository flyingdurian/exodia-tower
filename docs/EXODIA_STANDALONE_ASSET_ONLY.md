# EXODIA_STANDALONE_ASSET_ONLY — permanent ban on board slicing

## EXODIA_STANDALONE_ASSET_ONLY — PERMANENT RULE (2026-11-02)

The owner rejects all auto-sliced production character artwork. Never crop portraits or sprites from composite summary boards, contact sheets, UI grids, thumbnail atlases, collage montages, or compressed review sheets. Never promote such crops by padding, upscaling, or changing their filename. Approved source boards remain style references only. The retired grid slicer and its CI are banned.

Each of the 33 production portraits must originate as a truly independent, standalone, native 1536×1920 PNG, with an image SHA-256, image-bound human-annotated facial landmarks, and direct owner approval. Every registration record and matching owner approval ledger row must include the same independently reviewed provenance record: schema exodia.independent-portrait-source/v1, source_kind independent_standalone_native, derived_from_composite false, native_canvas [1536,1920], original_sha256 matching the actual file, original_filename, source_method independent_image_render or standalone_artist_export, human_source_review completed.

Metadata alone does not prove source authenticity or owner consent; reviewers must inspect the original standalone file and the actual approval evidence. Missing or suspicious provenance MUST fail the importer and independent registry audit. No live promotion until all 33 pass. Deferred animation loops and Operations Deck sprites remain separate. Preserve live provider workflows.

See docs/EXODIA_STANDALONE_ASSET_ONLY.md.

The approved composite boards are reference-only and must not be repackaged as production source PNGs. No auto-slicing, reframe, upscaling, crop, or padding waiver. Technical source declarations need separate human review; do not invent consent.
