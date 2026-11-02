# Exodia state-driven portrait registry · 2026-11-02
Development architecture: 20 expressions, 13 actions/statuses, and Idle/Working/Explaining loop hooks.
The registry is COMPLETE AS A STATE MAP but not as a set of production artwork. Legacy source audit (docs/albedo_portrait_phase2_registry.json) reports zero independently accepted 1536×1920 masters and zero accepted native loops. Prior expression boards and procedural keyframe proofs remain references only.
Run the strict scanner:
\`\`\`
python orchestrator/tools/portrait_registry_audit.py orchestrator/frontend/companions/production/kiko/portrait_registry.json --report portrait_registry_report.json
\`\`\`
Expected until native art exists: exit code 1, 0/33 portraits, 0/3 loops, release flag false. A frame needs native PNG, correct SHA-256, registration JSON bound to that source hash and its own SHA-256, human landmarks (outer eyes, head edges, ornament/shoulders), explicit owner approval, and reviewer metadata. Eye midline target 633.6px and head width 614.4px; tolerance and 768px eye X in registry. Automatic verification of whether annotations match the pixels is not claimed. An actual human visual inspection remains mandatory.
Client: \`portrait_state_manager.mjs\` and \`portrait_state_boot.mjs\` are opt-in modules on the existing workstation; release.enabled=false retains the previous avatar and doesn't alter browser providers, task scheduling, or Operations Deck navigation. After explicit registry signoff, the manager verifies each PNG hash and canvas before rendering. Transitions crossfade entire static portraits in a constant 4:5 container without resizing or motion effects. Animation loops require separate pixel-lock and seam audits and are not auto-enabled.
