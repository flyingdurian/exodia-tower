"""Read-only, fail-closed A0 identity intake for Riven.

A technical pass is NEVER evidence of an independently authored source, actual
facial landmarks, a stable character identity, or owner production approval.
The historical poster is a style reference only and may not become a master.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
PILOT_MANIFEST = ROOT.parent / "assets/review/riven_pilot/pilot_manifest.json"
LOCKED = (1536, 1920)
SHA_RE = re.compile(r"^[a-f0-9]{64}$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_reference(manifest: dict, source_root: Path) -> dict:
    """Pin the real historical Riven image, not an invented replacement."""
    reference = manifest["identity_reference"]
    source_root = source_root.resolve()
    file = (source_root / reference["path"]).resolve()
    if not file.is_relative_to(source_root) or not file.is_file():
        raise ValueError("reference_missing_or_unsafe")
    if manifest.get("character_id") != "router" or manifest.get("name") != "Riven":
        raise ValueError("riven_identity_id_drift")
    if manifest.get("production_release_enabled") is not False:
        raise ValueError("production_lock_changed")
    if manifest.get("native_canvas") != list(LOCKED):
        raise ValueError("native_canvas_contract_changed")
    if reference.get("classification") != "nonproduction_composite_poster_style_reference_only":
        raise ValueError("historical_poster_promoted")
    if reference.get("native_identity_owner_approved") is not False:
        raise ValueError("unauthorized_identity_approval")
    if not SHA_RE.fullmatch(reference.get("sha256", "")):
        raise ValueError("reference_hash_missing")
    actual_hash = sha256(file)
    if actual_hash != reference["sha256"]:
        raise ValueError("reference_sha_mismatch")
    with Image.open(file) as image:
        size = list(image.size)
        if image.format != "PNG":
            raise ValueError("reference_not_png")
    if size != reference["dimensions"] or size == list(LOCKED):
        raise ValueError("reference_dimensions_or_classification_drift")
    return {"path": reference["path"], "sha256": actual_hash, "dimensions": size,
            "status": "verified_composite_reference_only"}


def audit_identity(manifest: dict, source_root: Path, candidate: Path | None = None,
                   expected_sha256: str | None = None) -> dict:
    """Never assert source independence or owner signoff based on file metadata."""
    verified = verify_reference(manifest, source_root)
    result = {
        "schema": "exodia.riven-a0-native-identity-review/v1",
        "character_id": "router",
        "reference": verified,
        "canonical_canvas": list(LOCKED),
        "identity_candidate": "awaiting_independent_native_artwork",
        "technical_source_pass": False,
        "source_authenticity_verified": False,
        "image_bound_landmark_review": "pending",
        "owner_identity_approval": "pending",
        "five_state_pilot": "blocked_until_identity_approval",
        "production_release_enabled": False,
        "errors": [],
    }
    if candidate is None:
        if expected_sha256 is not None:
            result["errors"].append("hash_provided_without_candidate")
        return result

    if not expected_sha256 or not SHA_RE.fullmatch(expected_sha256):
        result["errors"].append("expected_sha_required")
        return result
    source_root = source_root.resolve()
    file = (source_root / candidate).resolve()
    if not file.is_relative_to(source_root) or not file.is_file():
        result["errors"].append("candidate_missing_or_unsafe")
        return result
    if file.suffix.lower() != ".png":
        result["errors"].append("candidate_must_be_png")
        return result
    try:
        with Image.open(file) as im:
            dim, fmt, mode = im.size, im.format, im.mode
            # Guard obvious blanks, not a surrogate for visual authenticity.
            sampling = im.convert("RGB").resize((64, 64)).getcolors(maxcolors=4097)
            unique = len(sampling) if sampling is not None else 4097
    except (UnidentifiedImageError, OSError, ValueError):
        result["errors"].append("unreadable_image")
        return result
    actual_sha = sha256(file)
    result["identity_candidate"] = {
        "filename": str(file.relative_to(source_root)),
        "sha256": actual_sha, "dimensions": list(dim), "pixel_format": mode,
        "sampled_unique_colors": unique,
    }
    if dim != LOCKED or fmt != "PNG":
        result["errors"].append("not_native_1536x1920_png")
    if actual_sha != expected_sha256:
        result["errors"].append("candidate_sha_mismatch")
    if actual_sha == verified["sha256"]:
        result["errors"].append("historical_poster_cannot_be_master")
    if unique < 64:
        result["errors"].append("flat_or_placeholder_image")
    result["technical_source_pass"] = not result["errors"]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=PILOT_MANIFEST)
    parser.add_argument("--candidate", type=Path, help="Relative path to a new standalone identity PNG")
    parser.add_argument("--expected-sha256", help="Owner-supplied exact original SHA-256")
    parser.add_argument("--require-native-candidate", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = audit_identity(json.loads(args.manifest.read_text(encoding="utf-8")), args.root,
                                args.candidate, args.expected_sha256)
    except (ValueError, FileNotFoundError, KeyError, json.JSONDecodeError) as error:
        print(json.dumps({"schema": "exodia.riven-a0-native-identity-review/v1", "technical_source_pass": False,
                          "errors": [str(error)], "production_release_enabled": False}, indent=2))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["errors"] or args.require_native_candidate and not result["technical_source_pass"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
