# Albedo Static Portrait Ingestion

All animated loops are deferred. The 33-state static release requires original native 1536x1920 PNGs for the 20 expression keys and 13 action keys, plus one independently human-reviewed registration JSON per image and exact SHA-256 owner-approval evidence.

Source folder mirrors the registry paths:
`frames/expressions/<key>.png`, `frames/actions/<key>.png`, `registration/expressions/<key>.json`, `registration/actions/<key>.json`.

Each registration record needs `image_sha256`, `method:human_annotated_from_actual_image`, `human_review:completed`, `owner_confirmation_reference`, and `points_px` with seven measured landmarks. The separate approval ledger schema is `exodia.portrait-static-approval-ledger/v1`, with a `states` object containing all 33 keys, each with matching `image_sha256`, `registration_sha256`, `approved_by:owner`, `owner_confirmation_reference`, `reviewed_by`; include a top-level `owner_static_release_reference`. Do not fabricate or auto-author approvals.

Run after assets are obtained:
```
cd orchestrator
python tools/ingest_static_portraits.py --source /path/to/approved_native_static --registry-root frontend/companions/production/kiko --approval-ledger /path/to/owner_approvals.json --report static_preflight.json
```
Only after a clean report and actual owner approval add `--commit`. This stages through an isolated directory, preserves a backup and leaves the active client unchanged on any failure. Automated metadata checks alone cannot authenticate approval.


## EXODIA_STANDALONE_ASSET_ONLY — PERMANENT RULE (2026-11-02)

The owner rejects all auto-sliced production character artwork. Never crop portraits or sprites from composite summary boards, contact sheets, UI grids, thumbnail atlases, collage montages, or compressed review sheets. Never promote such crops by padding, upscaling, or changing their filename. Approved source boards remain style references only. The retired grid slicer and its CI are banned.

Each of the 33 production portraits must originate as a truly independent, standalone, native 1536×1920 PNG, with an image SHA-256, image-bound human-annotated facial landmarks, and direct owner approval. Every registration record and matching owner approval ledger row must include the same independently reviewed provenance record: schema exodia.independent-portrait-source/v1, source_kind independent_standalone_native, derived_from_composite false, native_canvas [1536,1920], original_sha256 matching the actual file, original_filename, source_method independent_image_render or standalone_artist_export, human_source_review completed.

Metadata alone does not prove source authenticity or owner consent; reviewers must inspect the original standalone file and the actual approval evidence. Missing or suspicious provenance MUST fail the importer and independent registry audit. No live promotion until all 33 pass. Deferred animation loops and Operations Deck sprites remain separate. Preserve live provider workflows.

See docs/EXODIA_STANDALONE_ASSET_ONLY.md.

Registration JSON source_provenance and owner ledger source_provenance must be identical and must bind to the actual PNG SHA-256.
