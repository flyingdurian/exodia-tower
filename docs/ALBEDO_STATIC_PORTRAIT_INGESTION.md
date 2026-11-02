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
