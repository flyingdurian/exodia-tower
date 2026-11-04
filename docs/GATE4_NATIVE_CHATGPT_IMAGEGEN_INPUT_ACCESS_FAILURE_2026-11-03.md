# EXODIA Tower — Gate 4 Native ChatGPT ImageGen Input Recovery Audit
Date: 2026-11-03 (America/Vancouver). **No image has been promoted.**

## Verified input
The authoritative positive Idle reference was loaded as actual image bytes from `POSITIVE_STYLE_REFERENCE_idle.jpg`, image size **1536×1920 JPEG**, SHA-256 `202d6b0a0b0dd7d6970f0a6897561d8727c87eb4cdbbdb605bfd8d3c472afde1`. The image was displayed/inspected inside the current conversation with an active image file ID `file_0000000039008230b12c65750cc35022`. This resolves the earlier "filename without accessible image data" problem.

## Native generation trials
Each invocation used **ChatGPT's actual built-in image generation tool** (`image_gen.text2im`). The owner prohibited Runway and Higgsfield, and neither was used. The intended deliverable was one independently rendered, image-specific Albedo original, particularly `angered`. The tool's generated instructions nevertheless requested/displayed four-state composites each time.

| Distinct trial | Actual PNG | Canvas | Output SHA-256 | Verdict |
|---|---|---|---|---|
| Text-to-image without direct image | `a_high_detail_polished_anime_illustration_strip.png` | 2172×724 | `742d9d4262611b61e7109bdcda4cfbc5f47ab67bdc75461e48540e044643372e` | REJECTED FOUR-PANEL |
| One-state request, no image | `a_wide_cinematic_high_detail_anime_illustration.png` | 2172×724 | `8b8bd72ddd84e0ab9e146081274836bca5909e3dd2fb86200c1f52312f7e6289` | REJECTED FOUR-PANEL |
| Approved JPEG bytes brought into model context | `a_wide_high_detail_anime_illustration_composite.png` | 2172×724 | `b6eb9838d43f9e70a2d4dfc1e6e082d1493bc0906607d9ca1f7b44da12cc4069` | REJECTED FOUR-PANEL |
| Controllable portrait-size and explicit reference binding attempted | `a_detailed_high_quality_anime_illustration_collag.png` | 2172×724 | `eaea2008d36e8facbf03042ea248b4b5046e031f46b731be814eb1622d26138e` | REJECTED FOUR-PANEL |

The tool returned rendered image files, **not an exception**. The verified failure is that each returned image depicts four labeled states on one wide canvas. The current image-generation invocation auto-resolves the entire four-state conversation into a four-panel board even when the assistant requests one specific standalone image. **No native individual state PNG results.**

## Why the prior successful 33-state flow is different
`assets/review/albedo_core5/gate4_runway_verified_sources.json` records the original independent image outputs as `nano-banana-2` jobs delivered by a **Runway-hosted Nano Banana 2** workflow (the stored URLs use `runway-task-artifacts`), not the same ChatGPT built-in image-generation invocation available to this chat. Earlier work also used the separately connected Higgsfield renderer for a Celebrating portrait. Both Runway and Higgsfield are explicitly disallowed for this correction.

## Mandatory preservation
- Approved for continued development: **29/33 image source/output SHA pairs unchanged**.
- Targeted replacements: Angered, Awaiting Command, Neutral and Tantrum **0/4 produced**.
- All four existing images retained for live demonstration. Neither cropped multi-state board nor proxy art is acceptable.
- The dedicated four-source protected importer remains ready. No production approvals, no release, no merge.
- This is **an interface control limitation, not evidence that the underlying image model is incapable of rendering solo images**. A controllable native per-image prompt path returning genuine standalone originals is required to move forward.

All four unsuccessful full-size composites are kept as rejected evidence in the conversation environment and are intentionally excluded from GitHub production/review asset directories.
