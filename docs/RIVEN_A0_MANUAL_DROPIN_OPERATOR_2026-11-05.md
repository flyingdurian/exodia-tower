# EXODIA — Riven A0 manual drop-in operator intake (2026-11-05)

**Scope:** One Riven \`router\` identity candidate only. This augments PR #14's existing fail-closed gate; does not recreate the technical gate, auto-register five states, alter the poster SHA, or set production-release/owner approval flags.

## Isolated Windows workflow

From the Riven-specific feature worktree (never copy into the permanent owner's working directory without checking pending edits):

\`\`\`powershell
cd C:\Users\TFBOSS\Documents\GitHub\exodia-tower\orchestrator
New-Item -Type Directory -Force .\app_data\riven_a0_inbox | Out-Null
# Optional local watch: runs in the foreground; Ctrl+C exits.
python tools\riven_manual_dropin.py --watch
\`\`\`

Drop exactly **ONE** genuinely independently authored **native 1536×1920** PNG in \`orchestrator/app_data/riven_a0_inbox/\`, e.g. \`riven_A0_native.png\`. No side-by-side collage, old 1122×1402 poster crop, resampled preview or non-native source. A watcher started beforehand recognizes stable bytes, calculates actual SHA and invokes PR #14's existing A0 technical gate. Without a running watcher, perform the same one-shot read-only scan:

\`\`\`powershell
python tools\riven_manual_dropin.py
\`\`\`

Both modes return **source byte/dimension/hash proof only** until image-bound measurements exist. They never certify source independence or owner approval.

## Image-bound anatomy coordinates

The eye, shoulder and head landmarks cannot be reliably inferred solely from declared targets or automated image metadata. A human must annotate the actual standalone original pixels, not paste target numbers as measurements. To create a blank sidecar bound to the actual file SHA, run:

\`\`\`powershell
python tools\riven_manual_dropin.py --write-annotation-template
\`\`\`

Edit \`riven_A0_native.landmarks.json\`: fill \`landmarks\` as actual \`[x,y]\` coordinates for both iris centres, anatomical shoulder joints and left/right head silhouette edges. The emitted fields are **null** by default. Once manually located on the real image, attach machine-verifiable 19×19 raw-pixel patch SHA hashes:

\`\`\`powershell
python tools\riven_manual_dropin.py --stamp-patches
python tools\riven_manual_dropin.py
\`\`\`

This verifies the sidecar is bound to the **current original bytes** and measures eye midline y=633.6±2, shoulder midline y=980±2, head width 614.4±4, horizontal head centre x=768±8, and plausible horizontal order. A patch hash validates coordinates against the image's sampled RGB pixels; it **cannot** recognize whether the point is anatomically an iris or shoulder. Thus even an automated \`technical_and_annotated_geometry_ready_for_human_review\` result retains \`automated_iris_detection=false\`, \`source_authenticity_verified=false\`, \`human_anatomy_identity_review=pending\`, \`owner_identity_approval=pending\`, five states blocked and \`production_release_enabled=false\`.

Full-resolution visual QA must verify Riven's own dark long twin tails, red ties/eyes, black-red-gold tactical twin-blade armor, hand anatomy, real landmark placements, native authoring method and exact original SHA. Submit the candidate and SHA to owner for explicit visual identity approval. Only after that exact-image acceptance may five distinct PNGs \`neutral\`, \`confident\`, \`angered\`, \`working\`, \`pointing\` be authored, separately inspected and reviewed. The other eight companions remain frozen.

**All scanned PNG and sidecar files remain in ignored worktree-local \`app_data\`; no secrets or assets get committed by this script.** PR #14's \`riven_native_identity_gate.py\` remains the authoritative unchanged technical gate.
