# Albedo core actions: automated queue B01

Order: Working → Explaining → Monitoring → Pointing, from the official 33-state manifest. The accepted 1122×1402 Working and Explaining images are **style references only**; they cannot be upscaled into production masters. No acceptable standalone Monitoring or Pointing master was present when this batch was created.

Run from the repository root:
\`\`\`bash
python orchestrator/tools/ingest_core_action_batch.py --approve --commit --report assets/staging_intake/core_actions_batch_report.json
\`\`\`

For new independent original render PNGs stored outside the repo, first use \`--source-dir /path/to/standalone_originals\`. In that folder each state requires \`<state>.png\` and \`<state>.source.json\` (SHA-bound standalone provenance). The runner checks the original dimensions (at least 1536×1920), stages it to \`incoming/\`, creates a 1536×1920 normalization *preview*, and drafts **pending** registration and approval JSON without inventing measurements or signoff. A snapshot of the generated normalized preview is not itself certified for release.

After actual visual review, populate \`registration/<state>.json\` with measured \`source_points_px\`, human-review completion, and owner confirmation. Record the matching real owner approval and reviewed-by identity in \`approvals/<state>.json\`. Only then does \`--approve --commit\` invoke \`ingest_standalone_portrait.py --normalize --commit\`. The CLI intentionally does not have an unsafe switch to forge approval. It never slices boards or upscales smaller images.

Batch exit code 0 only means the queue inspection completed; look at \`committed_this_run\`, each state's status, and the registry audit to establish production success. Verify GitHub commit separately: a successful local intake does not push the repository. Global \`release.enabled\` remains false until the full 33-state gate is approved.
