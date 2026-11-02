# EXODIA TOWER — Albedo 2D Portrait Phase 2

**Status: visual workstation preview and production-art intake implemented, individual 4:5 artwork incomplete.** The original Exodia production UI and provider workflows are untouched.

## What this gate delivers

- Independent 4:5 portrait slot, same layout dimensions regardless of selected emotion or action, and independently animated lilac holographic scenery behind the character.
- 20 mapped emotions, 13 actions and four extra command statuses: Awaiting Command, Monitoring, Defeat and Tantrum.
- A local-only importer for image candidates named `kiko__happy.png`, `kiko__typing_working.png` etc. It rejects non-1536×1920 images. A correct canvas is only **technically eligible**, not approved for likeness, anatomy or landmark registration.
- Production-loop preview intake for 4+ distinct 1536×1920 frames, with duplicate-hash, pixel-size and reduced-motion checks. Still needs proof of matching head position, anatomical changes and visual acceptance.
- Three short animated **storyboard-only** GIFs (Idle, Working, Explaining) cut from an approved **composition board**, at 200×248/256/274 pixels, meant for evaluating animation intent at a small size. These are NOT individual high-resolution production frames. No global-shift or wobble animation was substituted.
- Separate owner-liked reference boards, their exact SHA-256 fingerprints, and four earlier Wave 1 HD source images that **fail** the newly approved source ratio/dimensions. Their 768×960 contained copies are for visual comparison only.

## Open

- `Exodia_Albedo_Portrait_Phase2_STANDALONE.html` opens directly without a local server or unpacking assets.
- Or unzip this folder and open `albedo_portrait_wave2_review.html`.
- `assets/phase2_HAPPY_DESKTOP.png` and `assets/phase2_LOOPS_DESKTOP.png` show verified Chromium captures.

## Quality and authenticity

The reference model that allowed the approved full-body image was observed coercing **4:5 to 3:4**. A model supporting higher-quality output rejected generation because its account requires a paid plan. No coerced or uninspected image has been added to this release, no credits were spent on a large batch, and the visual board's phrase "production ready" does not confer real approval.

Native 1536×1920 portraits must be individually authored for each of the 20 emotions and 13 primary actions, plus the extra statuses. All future 4:5 images must preserve the 50% horizontal / 33% vertical eye landmark, approximately 40% head width, and 5.5% safe margin. Every animation frame must use the same registration. Operations Deck sprites remain an independent source family.

## Tests

```bash
python -m pytest tests/test_albedo_2d_phase2.py -q
python tests/browser_smoke.py
```

The browser smoke test uses system Chromium via `executable_path='/usr/bin/chromium'`, and works without navigating to an external URL by mounting the HTML in a controlled test document. It validates fixed 4:5 display dimensions and 20+13+4 mapping on desktop and mobile; synthetic PNGs are used only in the technical import test, never as character artwork.

## Acceptance

| Gate | Result |
| --- | --- |
| Portrait stage dimensions | Passed locally (desktop and mobile) |
| All task states present | Mapped (20+13+4) |
| Ambient scene effects | Running, separate from portrait |
| Local technical import | Rejects wrong canvas |
| Idle/Working/Explaining GIF | Storyboard previews only |
| Old Wave 1 originals | 0/4 native format passes |
| Independent compliant 4:5 art | Not yet produced |
| Native 4-frame animation loops | Not yet produced |
| Final production art authorization | Blocked pending real art and visual review |

**Do not replace the live task stage or mark the ten-companion fleet as ready.**
## Named reference boards (corrected)

The review ZIP includes all five benchmarks, with verified SHA-256 prefixes: Expressions & Emotions `92bc46363077858bb0df`; Actions Set A `7b489427ca55c9c0d6f1`; Actions Set B Revised `17a3f1308be2293f3cac`; portrait loops `686bbe9fe56f9006cf26`; original command benchmark `bfc233740851980021ea`. They remain visual concept boards, not individually approved 4:5 masters.
