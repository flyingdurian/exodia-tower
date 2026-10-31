# Exodia Tower — Owner-directed development roadmap

## Decisions (2026-10-31)
- Canonical remote: `flyingdurian/exodia-tower`.
- Earlier Command Tower dashboard **rejected**; don't republish it as the new design.
- Approved anime character illustrations are reference-only until fully rigged.
- Specialist social agent spans YouTube, TikTok and Instagram.
- Explicit operator approval before publishing, editing live content, or modifying accounts.

## Gate M0 — Migration
Import complete V0.2 source with secrets/cache/session folders excluded. Include all source masters in Git LFS or an artifact release (GitHub API blobs have transport constraints). Preserve tests and history of new changes. Establish tests in CI.

## Gate U1 — Modern control center
Dark, technology-forward operations dashboard with modular floating workstations, realtime task graphs, low visual noise, and accessible responsive layouts. Companions roam on walkable stage lanes and navigate around UI using pathfinding, easing, collision avoidance, click/drag target selection and idle activities. Respect reduced motion. Differentiate live system data from demonstrations. Expose an actual playable browser proof before accepting.

## Gate A1 — True articulated characters
Kiko is the first production rig. Separate foreground/background art and replace occluded anatomical segments through paint-over and consistent pose sheets. Register bones, joints, facial mesh/mouth shapes, eyelid pairs, hair physics, gestures and walk cycles. Animate idle, thinking, processing, working, speaking, bored, sleeping, happy, excited, angry, disappointed, hurt, pain, wonder, panic, success and recovery. Use state machine, blend trees and event-driven lip-sync; don't fake limbs by wobbling flattened artwork. Pass view-at-rest, motion-at-speed, skin deformation, seam, eye alignment and cross-state continuity reviews before cloning rig pipeline to 8 specialists.

## Gate S1 — Social Media Division
One social strategist character; research trends and subjects with provenance; prepare content briefs, shot lists, scripts, captions, hashtags, titles, thumbnails, review notes and schedules; ingest analytics from authorized APIs; compare performance by channel; recommend changes based on evidence. Queue stages: idea -> research -> script -> assets -> edit -> review -> approved -> scheduled -> published -> monitored. Keep per-platform publishing adapters separate.

## Gate S2 — Platform credentials and publishing
OAuth per platform; short-lived tokens; least privilege; refresh/rotation, revocation and audit trail. Validate platform eligibility and quotas. Upload remains disabled until a human explicitly approves exact media, account, metadata and schedule. Use official upload endpoints and polling, no stealth or anti-bot bypass. YouTube, TikTok and Instagram all differ in scopes, review requirements and publishing capabilities; never imply universal automatic posting.

## Acceptance rules
No placeholder portraits disguised as animated rigs. No simulated analytics displayed as actual data. No scheduling claim without a persistent scheduler and authenticated publisher. No auto-publishing before explicit approvals. A tested PR is mandatory for each gate.
