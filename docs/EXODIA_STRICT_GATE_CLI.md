# EXODIA strict sequential gate — executable implementation

The supreme rule is in docs/EXODIA_STRICT_INSTRUCTION_COMPLIANCE.md and SKILL.md.

Run preflight BEFORE contacting any image-generation service. The JSON spec for a single Albedo state requires schema exodia.strict-instruction/v1, exact requested/effective canvas_px [1536,1920] and aspect 4:5, empty model_adjustments, camera transform exactly zero, and an owner-approved reference file with verified SHA-256. If effective model parameters cannot be verified or a model coerces 4:5 to 3:4, the preflight MUST fail.

Commands (replace paths with local files):
- python orchestrator/tools/strict_instruction_gate.py preflight SPEC.json --out PREFLIGHT.json
- python orchestrator/tools/strict_instruction_gate.py master-check SPEC.json PREFLIGHT.json MASTER.png ANCHORS.json --out MASTER_RECEIPT.json
- python orchestrator/tools/strict_instruction_gate.py authorize-sequence SPEC.json PREFLIGHT.json MASTER_RECEIPT.json MASTER.png ANCHORS.json OWNER_DECISION.json --out SEQUENCE_PERMIT.json

MASTER_RECEIPT is ALWAYS pending visual approval, even if all technical checks pass. The coder must cross-check OWNER_DECISION with a real explicit user approval message. No self-generated approval is valid. The permit never authorizes production release. Run native motion audits and obtain visual acceptance separately after authorized frame generation. These checks cannot physically prevent an unrelated external image-generation tool from running; make the preflight and permit mandatory in all generation entrypoints.

No master receipt or user approval exists yet for Idle, Working or Explaining. Current sequence status is blocked, and no image files were created in this policy update.
