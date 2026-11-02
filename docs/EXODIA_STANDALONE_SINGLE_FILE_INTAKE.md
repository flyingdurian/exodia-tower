# EXODIA standalone single-state portrait intake

The original source must be a standalone native 1536×1920 PNG, not a resized or cropped summary board. The exact 33-key manifest in assets/staging_intake/manifest_template.json references the canonical portrait_registry.json state names.

For each state provide a matching PNG, seven human-measured landmark coordinates in SHA-bound registration JSON, and an authentic owner approval record with matching source provenance, image SHA and registration SHA. The importer emits console preflight logs and final JSON; its default is dry run. --commit performs an atomic one-state production-directory update only if all per-state checks pass. The original remains in intake for evidence. Full global portrait activation remains off, because 33 completed independently approved assets and a separate all-state gate are required.

The utility **does not automatically locate eye features**. It calculates eye midpoint and head width from reviewed image-landmark coordinates; independent visual inspection of the actual PNG remains essential. Metadata correctness is not evidence of real owner approval or independent native authorship.

Example: python orchestrator/tools/ingest_standalone_portrait.py --state idle --source assets/staging_intake/incoming/idle.png --report intake_idle.json
