# EXODIA Tower · Albedo Visual Test Workbench

This is a **prototype-only** interactive 5-state preview. It does not change the signed 33-state production registry, record owner approval, or alter game workflows. All portrait PNGs occupy a 1536×1920 canvas. Low-resolution standalone concept references are padded and upscaled **for preview only** using Lanczos; this is not a production-resolution claim. The Pointing state is a **representative non-pointing pose** until the dedicated original exists.

## Run locally

From the unpacked archive root:

```powershell
python -m http.server 8765 --directory orchestrator/frontend
```

Then open `http://localhost:8765/test_workbench.html` in Chrome, Edge or Firefox. Do **not** open the HTML using `file://` because the preview registry and SHA verification use HTTP requests. Click each state or use Left/Right arrows. Toggle Auto-demo, change cross-fade duration, toggle cosmic background movement, and copy diagnostic telemetry. Original portrait layers stay stationary; only opacity changes.

## Refresh artwork when working in the GitHub repository

From the repository root, where the original individual art files exist:

```powershell
python orchestrator/tools/ingest_core_action_batch.py --prototype --prototype-source-root assets/prototype_sources
python -m http.server 8765 --directory orchestrator/frontend
```

The prototype flag invokes `build_albedo_prototype_assets.py` and writes only to `orchestrator/frontend/prototype_assets/albedo/`. That folder is deliberately separate from `orchestrator/frontend/companions/production/kiko/`. For a better image, replace its standalone source and rerun the command. No collage-board slicing is used.

## Test controls

- Idle: quiet standby portrait
- Working: holographic keyboard portrait
- Explaining: hand-gesture teaching portrait
- Monitoring: attentive observation portrait
- Pointing: representative static proxy with focus-target graphic, **not** a true pointing-finger illustration

`prototype_registry.json` includes the exact SHA-256 of every output. The browser verifies the hash and dimensions before displaying each image. The manager cross-fades complete PNG layers, with no rubber-sheet warp, hard-edged eye overlay, or sliding camera.

## Production guard

The standalone-only production rules remain untouched. The prototype runner does not set any `approved_by`, `status: verified` or `release.enabled` values, and cannot be used as a substitute for the normal `--normalize --commit` production intake.
