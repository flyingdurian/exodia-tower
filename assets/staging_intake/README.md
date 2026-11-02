# Albedo standalone portrait intake (no board slicing)

Place one original, independently authored native **1536×1920 4:5 PNG** in \`incoming/<state>.png\`. Follow the 33-key \`manifest_template.json\` exactly. Collage crops, panel extractions, resized summaries and contact sheets are prohibited.

Provide \`registration/<state>.json\` with SHA-bound human-reviewed landmarks: \`left_outer_eye\`, \`right_outer_eye\`, \`head_left_edge\`, \`head_right_edge\`, \`ornament_attachment\`, \`left_shoulder\`, \`right_shoulder\`; include the required \`source_provenance\` per \`docs/EXODIA_STANDALONE_ASSET_ONLY.md\`, \`image_sha256\`, \`method=human_annotated_from_actual_image\`, \`human_review=completed\`, and a real \`owner_confirmation_reference\`.

Provide \`approvals/<state>.json\` with schema \`exodia.portrait-static-approval-record/v1\`, exact \`state_key\`, \`category\`, \`image_sha256\`, \`registration_sha256\`, matching \`source_provenance\`, \`approved_by=owner\`, identical \`owner_confirmation_reference\`, and \`reviewed_by\`. The actual owner's confirmation must be independently checked; a JSON declaration is not authentication.

From repository root:

\`\`\`bash
python orchestrator/tools/ingest_standalone_portrait.py --state idle --source assets/staging_intake/incoming/idle.png --report intake_idle.json
python orchestrator/tools/ingest_standalone_portrait.py --state idle --source assets/staging_intake/incoming/idle.png --commit
\`\`\`

Default dry-run prints \`[PASS]\`/\`[FAIL]\` messages and JSON telemetry. The CLI computes eye midpoint y and head width from reviewed coordinates (target eye-line **633.6±2px**, eye midpoint x **768±8px**, head width **614.4±4px**). It does **not** automatically detect faces or prove artistic origin. The importer copies an individually verified PNG and registration atomically, records its hashes in the existing registry, retains original source files, and leaves \`release.enabled=false\` until all 33 pass a separate audit and global owner approval.

These directories contain no approved art at initialization; empty directories are represented with .gitkeep. Incoming image and human-approval files are intentionally excluded from source control.


## Authorized high-resolution normalization exception
See `docs/EXODIA_AUTHORIZED_NORMALIZATION.md`. `--normalize` accepts only reviewed, independent higher-resolution originals; never collage crops, upscaled images, or self-declared landmark targets. Preserve original SHA-256 and commit source original plus normalized derivative.
