"""Build NON-PRODUCTION standalone Albedo 4:5 previews, never touches the audited registry.

Intentionally allows contain-and-pad + Lanczos upscaling in --prototype mode only.
Never creates review metadata or owner approvals. Never slices boards or summary collages.
The five states are testable; Pointing is an explicitly marked explanatory-gesture proxy.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageOps

CANVAS = (1536, 1920)
STATE_SOURCES = {
    "idle": ["albedo_s_serene_cosmic_idle_pose.png", "orchestrator/frontend/companions/portraits/kiko.webp"],
    "working": ["albedo_s_celestial_holographic_workstation.png", "orchestrator/frontend/companions/review/kiko_wave1/assets/hd/typing_working.webp"],
    "explaining": ["albedo_s_luminous_arcane_explanation.png", "orchestrator/frontend/companions/review/kiko_wave1/assets/hd/happy.webp"],
    "monitoring": ["albedo_in_a_celestial_command_halo.png", "orchestrator/frontend/companions/review/kiko_wave1/assets/hd/thinking.webp"],
    "pointing": ["celestial_albedo_in_radiant_regalia.png", "orchestrator/frontend/companions/review/kiko_wave1/assets/hd/serious.webp"],
}
STATE_LABELS = {
    "idle": ("Awaiting command", "Available for a new mission", "STANDBY"),
    "working": ("Working", "Typing at the command console", "PROCESSING"),
    "explaining": ("Explaining", "Presenting mission guidance", "COMMUNICATING"),
    "monitoring": ("Monitoring", "Observing the Operations Deck", "OBSERVING"),
    "pointing": ("Pointing", "Directing attention to a target", "DIRECTING"),
}


def find_source(state: str, source_root: Path, project_root: Path) -> Path | None:
    for rel in STATE_SOURCES[state]:
        for root in (source_root, project_root):
            p = root / rel
            if p.is_file():
                return p
    return None


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(source_root: Path, project_root: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    entries = {}
    for state, names in STATE_SOURCES.items():
        source = find_source(state, source_root, project_root)
        if source is None:
            raise FileNotFoundError(f"No individual source artwork for {state}; searched: {names}")
        with Image.open(source) as im:
            if im.format not in ("PNG", "WEBP", "JPEG"):
                raise ValueError(f"Unsupported individual-art format for {state}: {im.format}")
            size = list(im.size)
            # Only presentation-size normalization. Preserve entire source, never crop a collage.
            base = ImageOps.pad(im.convert("RGB"), CANVAS, method=Image.Resampling.LANCZOS,
                                color=(19, 16, 42), centering=(0.5, 0.5))
        out = output_dir / (state + ".png")
        base.save(out, format="PNG", optimize=True)
        label, description, activity = STATE_LABELS[state]
        entries[state] = {
            "label": label, "description": description, "activity": activity,
            "path": state + ".png", "sha256": file_hash(out),
            "canvas": list(CANVAS), "source_canvas": size,
            "original_source": source.name, "source_sha256": file_hash(source),
            "asset_family": "prototype_only", "approval": "UNAPPROVED_PROTOTYPE",
            "normalization": "contain_lanczos_pad_scaled_as_needed",
            "is_action_accurate": state != "pointing",
            "caveat": "Gesture representative only; dedicated pointing-finger master still needed" if state == "pointing" else
                      "Concept-state preview, not signed production artwork",
        }
        print(f"[PROTOTYPE] {state:12s} {size[0]}x{size[1]} -> 1536x1920; sha256={entries[state]['sha256'][:16]}…")
    # Explicit independence from verified production registry
    registry = {
        "schema": "exodia.albedo-prototype-preview/v1", "character_id": "kiko",
        "canvas": {"width": CANVAS[0], "height": CANVAS[1], "aspect_ratio": "4:5"},
        "mode": "visual_workbench_only", "production_release_enabled": False,
        "states": entries,
        "order": list(STATE_SOURCES),
        "notice": "PROTOTYPE ONLY — includes low-resolution source scaling and a representative Pointing gesture; no owner approval is asserted.",
    }
    (output_dir / "prototype_registry.json").write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    return registry


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root", type=Path, default=Path.cwd())
    p.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument("--output-dir", type=Path,
                   default=Path(__file__).resolve().parents[1] / "frontend/prototype_assets/albedo")
    args = p.parse_args()
    try:
        registry = build(args.source_root, args.project_root, args.output_dir)
    except (OSError, ValueError) as e:
        print(f"[FAIL] {e}")
        return 1
    print(f"[PASS] {len(registry['states'])} prototype-only states generated; production registry untouched")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
