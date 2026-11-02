# Exodia Tower — Albedo 2D HD Wave 1 (2026-11-01)

Owner approved the original Operations Deck prototype and authorized the next 2D development gate. This wave is a **review of newly independently rendered high-resolution artwork**, NOT an approval of those images.

Four native-resolution candidate images were authored: Happy 1199×1312, Thinking 1312×1199, Serious 1312×1199, Typing/Working 1536×1024. The downloadable package contains PNG originals and optimized WebPs; none derive from the old 100px contact-sheet atlas.

Four earlier 128×196 directional standing sprites are retained for the previously accepted small-scale navigation prototype. Right is mirrored from left. Position tweening of a still image does **not** constitute authored walking, running, or idle animation frames.

## Import for review only

Download Exodia_Albedo_2D_HD_Wave1.zip from the conversation. After pulling development/exodia-foundation, from the repository root run:

    py -3 orchestrator\tools\import_albedo_wave1.py C:\path\to\Exodia_Albedo_2D_HD_Wave1.zip

Start the existing local Exodia server and open:

    http://127.0.0.1:8765/assets/companions/review/kiko_wave1/albedo_hd_wave1_review.html

The importer validates the exact four image paths, SHA-256 of original and display files, native image dimensions, and safe ZIP member names. It installs ONLY into frontend/companions/review/kiko_wave1; there is no live workstation modification.

## Remaining gates

Three of twenty expression illustrations and one of thirteen action illustrations are HD candidates; seventeen emotions and twelve action illustrations remain to be independently authored. Genuine frame-by-frame walk and idle cycles, true right-facing sprite art, and task-driven behavior must also be produced and accepted. No fleet-wide rollout before owner visual acceptance. 3D remains deferred.
