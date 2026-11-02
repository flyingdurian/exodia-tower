# Exodia Tower project skills

## EXODIA_STRICT_INSTRUCTION_COMPLIANCE — highest-priority production directive (2026-11-01)

For any engineering directive with explicit steps, technical constraints, or sign-off gates, obey the steps in the specified order. Never generate raw image assets, animation frames, storyboards or speculative substitutes before ALL prerequisites for that stage are verified passing. Never claim approval, animation, deployment, or validation that has not actually occurred.

Before any Albedo or fleet portrait work, follow docs/EXODIA_STRICT_INSTRUCTION_COMPLIANCE.md, then skills/exodia-companion-art/SKILL.md. Exact approved native portrait canvas: 1536 × 1920 (4:5); static camera, pixel-locked anchors and separately authored frames. If the image model reports a changed ratio (such as 3:4), missing settings or other deviation, HALT before the next creative action; do not pad/upscale the result to conceal it. Each master keyframe requires explicit owner visual sign-off tied to its SHA-256 before sequence generation. CI and owner motion review precede production promotion.

Existing contact sheets, A2/A3 GIFs and proxy rigs are nonproduction concepts. Operations Deck sprites are a separate family. Preserve current provider workflows, main and draft PR #1.

Explicit owner override (2026-11-01): normalization of near-4:5 generated master candidates is allowed for **review only** using `portrait_standard.py normalize-generated`. A technical `PASSED` of the normalized canvas does not certify native source detail, actually detected facial anchors, owner approval, or sequence release. The original native-sequence restriction remains.
