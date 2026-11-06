# Albedo chibi operations — independently authored frame intake

This directory intentionally contains **no sprite images**. The owner's turnaround sheet is an identity reference, **not** a permitted source atlas for extraction. No images are approved here.

Future exact filenames are the 40 keys in `../albedo_chibi_manifest.json`: `idle_<n|ne|e|se|s|sw|w|nw>.png`, and `walk_<direction>_00.png` through `_03.png` per direction. Each frame is a separate 192×256 RGBA PNG with independently annotated and owner-reviewed foot contact, no mirrored shortcuts, native standalone provenance and exact SHA-256 in the manifest. Do not flip `asset_status` or release flags until all 40 passed the human and technical gates.

Use `python orchestrator/tools/audit_chibi_frames.py` for mechanical preflight; it cannot independently verify anatomy, identity, or owner consent. Source approval and finished gait quality require owner visual review.
