# Exodia Tower — Gate A1.3: Kiko Prime artistic production
## Source and assets
- Approved identity: the SILVER-haired Kiko Prime, source `orchestrator/frontend/companions/source_masters/kiko.png`. Do not substitute the exploratory pink-haired concept.
- `artwork/kiko_prime/`: 13 independently source-extracted movement cutouts, 3 feature regions, two draft closed-eye images, plus registration/matte coordinates in the editable JSON manifest.
- `kiko_art_engine.mjs` and `/art-studio`: interactive source-pixel puppet preview, IK reach, pose states, blink/speech engineering approximation, mask inspection.
- The master is 1122×1402 pixels. Original rendering, costume and face retained from the approved illustration.

## Quality status: NOT PRODUCTION READY
The source was originally a finished cinematic scene, not a layered rig. Foreground extraction retains some scenery especially around hair and lower body. Limb back surfaces, lower-body garment geometry, and complete closed-eye/viseme paintings do not exist. No artist has accepted the seam quality. Current blink and speech retouch is a controller proof, not premium facial animation.

## Required artist work
1. Repaint contaminated hair, clothing and lower-body edges without background artifacts.
2. Create hidden rear arm/leg artwork plus feet and fully visible standing turnaround.
3. Paint coherent aligned eye/brow/mouth viseme plates and hair strand chains.
4. Integrate approved parts in the 22-bone runtime with planted-foot IK, body expressions and audio timing.
5. Record multi-action, cross-transition QC proof before owner approval; only then propagate rigging to the rest of the cast.

## Validation
`cd orchestrator && python -m pytest tests -q`
`node --test orchestrator/tests/*.test.mjs`
`python main.py` → `http://127.0.0.1:8765/art-studio`
