# Albedo — Review-only 4:5 generator normalization

The generator produced 1122×1402, approximately 4:5, and the owner authorized resampling and padding for the master **review stage only**. This is a conscious relaxation of the *master preview source resolution*, not of animation frame origin or approval sequencing.

- Command: `python orchestrator/tools/portrait_standard.py normalize-generated ORIGINAL.png NORMALIZED.png SOURCE_LANDMARKS.json METADATA.json`.
- Landmark JSON: `{"method":"manual_visual_estimate","eye_midpoint_source_px":[554,377],"head_bounds_x_source_px":[294,814]}` — example coordinates for the specific November 1 Idle illustration; they are visually estimated, not automatically detected.
- Image adapter uses one near-uniform Lanczos scale, then extrapolates and feathers outside the original image footprint to avoid destructive cropping.
- Mapping target is y=633.6px, head width=614.4px. Unfeasible margins or wrong aspect ratio HALT rather than crop or distort.
- Telemetry records original/generated pixel size, normalized image size, original and output SHA-256, mapping SHA-256 and the mathematical transform.
- A **PASSED** result and exit code zero signify only the numeric output-canvas/transform checks. `registration_verified_from_image=false`, `source_native_resolution=false`, and `sequence_generation_authorized=false` are permanent truthful metadata fields.
- Do not turn a technically normalized still into frame sequences before separately confirming its visual acceptability and revalidating hard anchor regions. The prior native-frame/zero-drift strict gate remains in force.

Do not overwrite prior original PNGs or alter Gemini/ChatGPT/Operations Deck code.
