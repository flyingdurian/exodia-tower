"""Four-state Albedo review artwork correction gate.

This tool can replace ONLY angered, awaiting_command, neutral, and tantrum,
and ONLY with four real, individual, independently rendered original PNGs.
29 owner-accepted DEVELOPMENT references remain immutable byte-for-byte.

Command: python orchestrator/tools/apply_gate4_four_corrections.py --verify-baseline
     or  python orchestrator/tools/apply_gate4_four_corrections.py --archive <zip>

Archive format:
  correction_manifest.json: schema exodia.gate4-corrections-input/v1,
      states = { state: {source_sha256,source_dimensions,generator_model,
        generator_job_id,generation_input_manifest_sha256,
        pose_evidence_description,derived_from_composite:false,
        owner_approved:false,production_release_enabled:false} }
  sources/<state>_original.png (four INDIVIDUAL originals)

Never creates portraits, never crops from boards or reuses frozen 29 sources.
Never changes final owner approvals or production release metadata.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
from zipfile import ZipFile
from PIL import Image, ImageOps
ROOT = Path(__file__).resolve().parents[2]
STORE = Path("orchestrator/app_data/albedo_33_review")
CONTRACT = Path("assets/review/albedo_core5/gate4_four_state_correction_lock.json")
QUEUE = Path("assets/review/albedo_core5/authorized_28_state_art_queue.json")
REPORT = Path("assets/review/albedo_core5/gate4_all_real_33_state_byte_audit.json")
PROD = Path("orchestrator/frontend/companions/production/kiko/portrait_registry.json")
SCHEMA = "exodia.gate4-corrections-input/v1"
SIZE = (1536, 1920)
MAX_SOURCE_BYTES = 26_000_000
MAX_ARCHIVE_BYTES = 130_000_000
TARGETS = ("angered", "awaiting_command", "neutral", "tantrum")


def sha(blob: bytes) -> str:
    return sha256(blob).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_original_png(original: bytes, state: str, expected_dims: list[int]):
    if len(original) < 100_000 or len(original) > MAX_SOURCE_BYTES:
        raise ValueError("invalid_individual_source_size:" + state)
    with Image.open(BytesIO(original)) as im:
        if im.format != "PNG" or list(im.size) != expected_dims:
            raise ValueError("original_canvas_or_format_incorrect:" + state)
        if im.width < SIZE[0] or im.height < SIZE[1]:
            raise ValueError("low_resolution_original_cannot_be_upscaled:" + state)
        if im.width > 6144 or im.height > 7680:
            raise ValueError("source_dimensions_unreasonable:" + state)
        if im.width == 1536 and im.height == 1920:
            box = (0, 0, 1536, 1920)
        else:
            # Max 2% symmetric crop allowed before a UNIFORM resampling.
            k = min(im.width // 4, im.height // 5)
            w, h = 4 * k, 5 * k
            left = (im.width - w) // 2
            top = (im.height - h) // 2
            box = (left, top, left + w, top + h)
            if w < 1536 or h < 1920:
                raise ValueError("cropped_source_below_native:" + state)
            if max(im.width-w, im.height-h) / max(im.width, im.height) > 0.02:
                raise ValueError("material_cropping_not_allowed:" + state)
        normalized = im.convert("RGB").crop(box).resize(SIZE, Image.Resampling.LANCZOS)
        stream = BytesIO()
        normalized.save(stream, format="PNG", optimize=True)
        return stream.getvalue(), {
            "kind": "identity_rgb" if im.size == SIZE else "symmetric_center_crop_then_uniform_lanczos",
            "crop_xyxy": list(box),
            "cropped_size": [box[2] - box[0], box[3] - box[1]],
            "output_size": list(SIZE),
            "source_pixel_sha256": sha(normalized.tobytes()),
        }


def perceptual_hash(image: bytes, *, face=False) -> int:
    with Image.open(BytesIO(image)) as im:
        gray = ImageOps.grayscale(im)
        if face:
            w, h = gray.size
            gray = gray.crop((int(w * 0.15), int(h * 0.06),
                              int(w * 0.85), int(h * 0.63)))
        pixels = list(gray.resize((9, 8), Image.Resampling.LANCZOS).getdata())
    result = 0
    for y in range(8):
        for x in range(8):
            result = (result << 1) | int(pixels[y*9+x] > pixels[y*9+x+1])
    return result


def verify_locked_29(root: Path) -> dict:
    contract = read(root / CONTRACT)
    index = read(root / STORE / "review_index.json")
    production = read(root / PROD)
    if (contract.get("schema") != "exodia.gate4-four-state-owner-correction-lock/v1"
            or set(contract.get("target_states", [])) != set(TARGETS)
            or contract.get("protected_count") != 29
            or production.get("release", {}).get("enabled") is not False):
        raise ValueError("invalid_owner_lock_or_release")
    if (len(index.get("states", {})) != 33
            or set(index["states"]) != set(contract["frozen_review_hashes"])):
        raise ValueError("33_state_index_does_not_match_owner_lock")
    if any(x.get("status") != "pending_production_art"
           for x in production.get("states", {}).values()):
        raise ValueError("production_release_gate_corrupted")
    frozen_hashes = set()
    for key, rec in contract["frozen_review_hashes"].items():
        actual = index["states"][key]
        old = key not in TARGETS
        if old and rec["development_review_status"] != "OWNER_ACCEPTED_FOR_CONTINUED_DEVELOPMENT":
            raise ValueError("29_development_approval_status_corrupted:" + key)
        if not old and rec["development_review_status"] not in (
                "CORRECTION_REQUIRED", "CORRECTION_RENDERED_OWNER_REVIEW_PENDING"):
            raise ValueError("four_target_status_corrupted:" + key)
        if old and (actual["source_sha256"] != rec["original_sha256"]
                    or actual["image_sha256"] != rec["review_sha256"]):
            raise ValueError("protected_29_hashes_changed:" + key)
        for sub, field in (("sources", "source_sha256"), ("images", "image_sha256")):
            file = root / STORE / sub / (key + "_original.png" if sub == "sources"
                                          else key + ".png")
            if not file.is_file() or sha(file.read_bytes()) != actual[field]:
                raise ValueError("original_or_review_bytes_do_not_match_index:" + key)
        if old:
            frozen_hashes.add(actual["source_sha256"])
            frozen_hashes.add(actual["image_sha256"])
    return {
        "locked_29_verified": 29, "unapproved_replacements": sum(
            contract["correction_briefs"][k].get("status") == "RENDERED_PENDING_OWNER"
            for k in TARGETS),
        "frozen_hashes": frozen_hashes, "contract": contract, "index": index,
    }


def check_metadata(state: str, info: dict):
    if state not in TARGETS or not isinstance(info, dict):
        raise ValueError("unauthorized_replacement_state")
    if (info.get("approved_by") or info.get("owner_approved") is not False
            or info.get("production_release_enabled") is not False):
        raise ValueError("fake_owner_or_release_approval_forbidden:" + state)
    model = str(info.get("generator_model", ""))
    if not model or "runway" in model.lower():
        raise ValueError("runway_prohibited_for_targeted_correction:" + state)
    if (not isinstance(info.get("generator_job_id"), str)
            or len(info["generator_job_id"]) < 8):
        raise ValueError("independent_generation_job_required:" + state)
    if not isinstance(info.get("source_dimensions"), list):
        raise ValueError("source_dimensions_missing:" + state)
    if (not isinstance(info.get("source_sha256"), str)
            or len(info["source_sha256"]) != 64):
        raise ValueError("source_sha256_missing:" + state)
    if (not isinstance(info.get("generation_input_manifest_sha256"), str)
            or len(info["generation_input_manifest_sha256"]) != 64):
        raise ValueError("generation_request_provenance_missing:" + state)
    if info.get("derived_from_composite") is not False:
        raise ValueError("contact_sheet_or_composite_forbidden:" + state)
    if not isinstance(info.get("pose_evidence_description"), str) or len(
            info["pose_evidence_description"].strip()) < 45:
        raise ValueError("original_pose_evidence_missing:" + state)


def preflight(root: Path, archive: Path) -> tuple[list, dict]:
    status = verify_locked_29(root)
    if not archive.is_file() or archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("missing_or_oversized_correction_zip")
    with ZipFile(archive) as zipped:
        permitted = {"correction_manifest.json"} | {
            "sources/" + key + "_original.png" for key in TARGETS}
        all_names = zipped.namelist()
        if (len(all_names) != len(set(all_names))
                or set(all_names) != permitted
                or any(".." in Path(name).parts or name.startswith("/")
                       for name in all_names)):
            raise ValueError("unsafe_or_duplicate_zip_entry")
        if any(entry.file_size > (MAX_SOURCE_BYTES if entry.filename !=
                "correction_manifest.json" else 65_536)
                for entry in zipped.infolist()):
            raise ValueError("zip_member_exceeds_individual_image_limit")
        if sum(entry.file_size for entry in zipped.infolist()) > MAX_ARCHIVE_BYTES:
            raise ValueError("zip_uncompressed_size_exceeds_limit")
        m = json.loads(zipped.read("correction_manifest.json"))
        if (m.get("schema") != SCHEMA or not isinstance(m.get("states"), dict)
                or set(m["states"]) != set(TARGETS)):
            raise ValueError("must_supply_exactly_four_independent_sources")
        originals = []
        for state in TARGETS:
            info = m["states"][state]
            check_metadata(state, info)
            data = zipped.read("sources/" + state + "_original.png")
            if sha(data) != info["source_sha256"]:
                raise ValueError("source_hash_mismatch:" + state)
            output, transform = validate_original_png(
                data, state, info["source_dimensions"])
            old = status["index"]["states"][state]
            if (sha(data) == old["source_sha256"] or
                    sha(output) == old["image_sha256"]):
                raise ValueError("source_is_unchanged_old_portrait:" + state)
            originals.append((state, info, data, output, transform))
    # Compare actual images, not merely labels or declared generation IDs.
    if len(set(i[1]["generator_job_id"] for i in originals)) != 4:
        raise ValueError("reused_generation_job")
    if len(set(sha(i[2]) for i in originals)) != 4:
        raise ValueError("identical_source_pixels")
    if len(set(sha(i[3]) for i in originals)) != 4:
        raise ValueError("identical_review_pixels")
    frozen = []
    for state in status["index"]["states"]:
        if state not in TARGETS:
            image = (root / STORE / "images" / (state + ".png")).read_bytes()
            frozen.append((state, perceptual_hash(image), perceptual_hash(image, face=True)))
    for i, (state, info, original, output, transform) in enumerate(originals):
        ph = perceptual_hash(output)
        fh = perceptual_hash(output, face=True)
        candidates = frozen + [(s, perceptual_hash(b), perceptual_hash(b,face=True))
                                for s, _, _, b, _ in originals[:i]]
        for other, o_ph, o_fh in candidates:
            if (ph ^ o_ph).bit_count() <= 3 and (fh ^ o_fh).bit_count() <= 3:
                raise ValueError("visually_reused_pose_or_face:" + state + ":" + other)
        old_art = (root / STORE / "images" / (state + ".png")).read_bytes()
        if ((ph ^ perceptual_hash(old_art)).bit_count() <= 4 and
                (fh ^ perceptual_hash(old_art, face=True)).bit_count() <= 4):
            raise ValueError("correction_still_near_identical_to_old:" + state)
    return originals, status


def apply(root: Path, archive: Path, *, dry_run=False):
    originals, pre = preflight(root, archive)
    if dry_run:
        return {"valid_new_images": 4, "locked_29_verified": 29,
                "replacement_files_written": 0, "owner_approved": 0,
                "production_release_enabled": False}
    index = pre["index"]
    contract = pre["contract"]
    queue = read(root / QUEUE)
    audit = read(root / REPORT)
    queue_by_key = {s["state_key"]: s for s in queue["states"]}
    # All four unique originals are genuine and checked BEFORE any mutation.
    staged = []
    for state, info, original, output, transform in originals:
        item = index["states"][state]
        staged.append((state, original, output))
        item.update({
            "source_filename": state + "_original.png",
            "source_sha256": sha(original), "image_sha256": sha(output),
            "generator_job_id": info["generator_job_id"],
            "generator_model": info["generator_model"],
            "generation_input_manifest_sha256": info["generation_input_manifest_sha256"],
            "source_dimensions": info["source_dimensions"], "normalization": transform,
            "pose_evidence_description": info["pose_evidence_description"],
            "review_status": "GENERATED_UNAPPROVED",
            "geometry_status": "PENDING_INDEPENDENT_PIXEL_AND_HUMAN_AUDIT",
            "owner_approved": False, "production_status": "pending_production_art",
            "independent_source_kind": "independent_native_or_larger_render",
        })
        b = contract["correction_briefs"][state]
        b["status"] = "RENDERED_PENDING_OWNER"
        b["new_original_sha256"] = sha(original)
        b["new_review_sha256"] = sha(output)
        b["owner_final_visual_review"] = "PENDING"
        contract["frozen_review_hashes"][state].update({
            "original_sha256": sha(original), "review_sha256": sha(output),
            "development_review_status": "CORRECTION_RENDERED_OWNER_REVIEW_PENDING",
        })
        q = queue_by_key[state]
        q.update({
            "generation_status": "generated_unapproved_native_candidate",
            "source_sha256": sha(original), "output_sha256": sha(output),
            "original_canvas": info["source_dimensions"],
            "output_canvas": list(SIZE), "generation_job_id": info["generator_job_id"],
            "human_pose_review": "pending", "owner_hash_bound_approval": None,
            "production_status": "pending_production_art",
        })
        audit["states"][state] = {
            "source_sha256": sha(original), "image_sha256": sha(output),
            "source_dimensions": info["source_dimensions"],
            "native_review_dimensions": list(SIZE),
            "task_id": info["generator_job_id"],
            "status": "NEW_CORRECTED_ORIGINAL_BYTES_VERIFIED_OWNER_UNREVIEWED",
            "geometry": "PENDING_MEASUREMENT",
            "owner_approved": False,
        }
    contract["correction_completed"] = 4
    # Save originals before mutating in-place index/queue metadata.
    updates = {
        root / STORE / "review_index.json": json.dumps(index, indent=2, sort_keys=True) + "\n",
        root / CONTRACT: json.dumps(contract, indent=2, sort_keys=True) + "\n",
        root / QUEUE: json.dumps(queue, indent=2, ensure_ascii=False) + "\n",
        root / REPORT: json.dumps(audit, indent=2, sort_keys=True) + "\n",
    }
    with tempfile.TemporaryDirectory(dir=root / STORE, prefix="gate4_four_") as temp:
        temp = Path(temp)
        originals_before = {}
        try:
            for state, original, output in staged:
                for sub, blob, filename in (
                        ("sources", original, state + "_original.png"),
                        ("images", output, state + ".png")):
                    path = root / STORE / sub / filename
                    originals_before[path] = path.read_bytes()
                    (temp / filename.replace(".png", "_" + sub + ".png")).write_bytes(blob)
            for path in updates:
                originals_before[path] = path.read_bytes()
            for state, _, _ in staged:
                for sub, filename in (("sources", state + "_original.png"),
                                      ("images", state + ".png")):
                    os.replace(temp / filename.replace(".png", "_" + sub + ".png"),
                               root / STORE / sub / filename)
            for path, content in updates.items():
                swap = temp / (path.name + "_updated")
                swap.write_text(content, encoding="utf-8")
                os.replace(swap, path)
            result = verify_locked_29(root)
            if result["unapproved_replacements"] != 4:
                raise ValueError("four_replacement_postcommit_validation_failed")
        except Exception:
            for path, data in originals_before.items():
                path.write_bytes(data)
            raise
    return {"valid_new_images": 4, "locked_29_verified": 29,
            "replacement_files_written": 8, "owner_approved": 0,
            "production_release_enabled": False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",type=Path,default=ROOT)
    p.add_argument("--verify-baseline",action="store_true")
    p.add_argument("--archive",type=Path)
    p.add_argument("--dry-run",action="store_true")
    args=p.parse_args()
    root=args.repo_root.resolve()
    if args.verify_baseline:
        result=verify_locked_29(root)
        print(json.dumps({"locked_29_verified":result["locked_29_verified"],
                          "corrections_completed":result["unapproved_replacements"],
                          "owner_approved":0,"release_enabled":False}))
        return 0
    if not args.archive:
        p.error("Provide --verify-baseline or --archive pointing to genuine four-source ZIP.")
    print(json.dumps(apply(root,args.archive,dry_run=args.dry_run),indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
