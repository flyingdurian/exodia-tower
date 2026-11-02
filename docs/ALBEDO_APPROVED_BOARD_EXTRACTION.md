# EXODIA — Automated board extraction checkpoint

**Result: REVIEW_ONLY, production preflight FAILED (exit 1).**

Approved reference boards: 20-cell Expressions & Emotions sheet, 6-state Actions A (with four concept idle frames), revised 5-state Actions B. The tool exports 31 crops retaining the source pixels and produces source/crop SHA-256 provenance and ROI coordinates. No crops are upscaled or falsely marked as native masters.

Registry has 33 states. Only 21 have exact or safe label-equivalent matches; 12 are missing: amused, awaiting_command, blushing, concerned, confident, focused, gentle, joyful, neutral, smiling_closed, thinking_deeper, worried.

The 31 source crops are around 200–560 pixels wide, and lack independently reviewed eye/head landmarks. They cannot be native-rendered 1536×1920 production portraits. User-approved concept boards are visual references; they do not supply native individual masters, formal landmark review, or 33 separate approvals.

## Run

python slice_master_boards.py --source-dir /path/to/reference_boards --mode review --output-dir /path/to/review --report review_report.json
python slice_master_boards.py --source-dir /path/to/reference_boards --mode production --output-dir /path/to/production --report production_preflight.json

Production command is intentionally fail-closed on the current sources and does not mutate portrait_registry.json. Do not set release.enabled=true or promote existing atlas/still previews.

Existing production audit: portrait_registry_audit.py, registry latest checked at branch acf8c534d7cb1bc8c40b6b0b8b8354b8eac6fe99, returns exit 1 with zero verified states. For that audit, the local copy of the prior static-gate package was used and is included in the report; production was not activated. All loop animation hooks remain deferred.