"""Owner-accepted Albedo four-state DEVELOPMENT-only review import.

Preserves four original 1122x1402 PNGs byte-for-byte, installs four
SHA-pinned presentation-resampled 1536x1920 PNGs, protects the other 29
original/output hashes, and creates a verified on-disk rollback snapshot.

This is NOT the native production-art importer. Never sets owner_approved,
native_production_certified or release.enabled. No portrait is generated here.

Input: EXODIA_GATE4_FOUR_REVIEW_ONLY_IMPORT_2026-11-04.zip
(9 members: review_only_manifest.json, 4 sources/*.png, 4 images/*.png).
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import sys
from zipfile import ZipFile, BadZipFile
from PIL import Image, ImageChops
# The module is called both by the live FastAPI app and as a standalone
# repository-root CLI. Keep the same import contract in both environments.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.apply_gate4_four_corrections import verify_locked_29, TARGETS, sha

ROOT = Path(__file__).resolve().parents[2]
STORE = Path("orchestrator/app_data/albedo_33_review")
LOCK = Path("assets/review/albedo_core5/gate4_four_state_correction_lock.json")
QUEUE = Path("assets/review/albedo_core5/authorized_28_state_art_queue.json")
LEDGER = Path("assets/review/albedo_core5/gate4_four_accepted_development_review_only.json")
NORMALIZATION = "REVIEW_ONLY_SYMMETRIC_CROP_THEN_UNIFORM_LANCZOS_UPSCALE"
SCHEMA = "exodia.gate4-four-resampled-development-intake/v1"
BACKUP = Path("orchestrator/app_data/albedo_33_review/rollback/gate4_before_resampled")
MAX_ARCHIVE_BYTES = 48 * 1024 * 1024
MAX_MEMBER_BYTES = 11 * 1024 * 1024

def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def jbytes(obj: dict) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")

def expected_paths() -> set[str]:
    return {"review_only_manifest.json"} | {
        f"{kind}/{state}{'_original' if kind=='sources' else ''}.png"
        for kind in ("sources", "images") for state in TARGETS
    }

def require_source_and_review(original: bytes, review: bytes, state: str) -> str:
    if not original or not review or len(original)>MAX_MEMBER_BYTES or len(review)>MAX_MEMBER_BYTES:
        raise ValueError("image_empty_or_over_maximum_size:"+state)
    with Image.open(BytesIO(original)) as im:
        if im.format != "PNG" or im.size != (1122, 1402):
            raise ValueError("non_compliant_review_source_canvas:"+state)
        source = im.convert("RGB")
    with Image.open(BytesIO(review)) as im:
        if im.format != "PNG" or im.size != (1536, 1920):
            raise ValueError("presentation_review_png_canvas_invalid:"+state)
        candidate = im.convert("RGB")
    # Exact 4:5 proportional geometry: remove 1 px evenly from every edge,
    # then uniform 1.371428571 scale (pure presentation upscale, never native).
    computed = source.crop((1, 1, 1121, 1401)).resize(
        (1536, 1920), Image.Resampling.LANCZOS
    )
    if ImageChops.difference(candidate, computed).getbbox() is not None:
        raise ValueError("presentation_pixels_not_proven_from_original:"+state)
    return sha(computed.tobytes())

def preflight(repo: Path, archive: bytes) -> tuple[dict, dict, dict]:
    if not isinstance(archive, bytes) or not archive or len(archive)>MAX_ARCHIVE_BYTES:
        raise ValueError("review_zip_missing_or_oversized")
    ledger = load(repo / LEDGER)
    if (ledger.get("schema")!="exodia.gate4-owner-accepted-four-lowres-review-only/v1"
            or set(ledger.get("states",{}))!=set(TARGETS)
            or ledger.get("release_enabled") is not False):
        raise ValueError("authoritative_approved_four_ledger_invalid")
    with ZipFile(BytesIO(archive)) as z:
        infos = z.infolist()
        if (set(z.namelist()) != expected_paths()
                or len(infos) != len(expected_paths())
                or any(info.file_size>MAX_MEMBER_BYTES for info in infos)
                or sum(info.file_size for info in infos)>MAX_ARCHIVE_BYTES):
            raise ValueError("review_zip_not_exactly_four_source_and_four_review_files")
        document = json.loads(z.read("review_only_manifest.json"))
        if (document.get("schema")!=SCHEMA
                or document.get("owner_final_production_approved",True) is not False
                or document.get("release_enabled",True) is not False
                or document.get("protected_existing_accepted_count")!=29
                or set(document.get("states",{}))!=set(TARGETS)):
            raise ValueError("review_manifest_schema_or_production_lock_invalid")
        verified={}
        source_hashes=set()
        image_hashes=set()
        for state in TARGETS:
            row = document["states"][state]
            approved = ledger["states"][state]
            source = z.read(f"sources/{state}_original.png")
            output = z.read(f"images/{state}.png")
            src_hash, out_hash = sha(source), sha(output)
            if (src_hash!=row["source_sha256"]
                    or src_hash!=approved["original_sha256"]
                    or out_hash!=row["review_sha256"]
                    or out_hash!=approved["expected_resampled_png_sha256"]
                    or len(source)!=approved["original_bytes"]
                    or row.get("source_dimensions")!=[1122,1402]
                    or row.get("review_dimensions")!=[1536,1920]
                    or row.get("normalization",{}).get("kind")!=NORMALIZATION
                    or row["normalization"].get("crop_xyxy")!=[1,1,1121,1401]
                    or row["normalization"].get("resampled_not_native") is not True):
                raise ValueError("source_or_resampled_hash_provenance_mismatch:"+state)
            px_sha=require_source_and_review(source,output,state)
            if px_sha!=row.get("normalized_pixel_sha256"):
                raise ValueError("resampled_RGB_pixels_sha_mismatch:"+state)
            source_hashes.add(src_hash)
            image_hashes.add(out_hash)
            verified[state]={"source":source,"review":output,"source_sha":src_hash,
                             "review_sha":out_hash,"pixel_sha":px_sha,
                             "review_metadata":row}
        if len(source_hashes)!=4 or len(image_hashes)!=4:
            raise ValueError("duplicate_input_originals_or_review_files")
    return verified, document, ledger

def _snapshot_paths(root: Path) -> list[Path]:
    p=[root/STORE/"review_index.json",root/LOCK,root/QUEUE]
    for key in TARGETS:
        p.extend([root/STORE/"sources"/f"{key}_original.png",
                  root/STORE/"images"/f"{key}.png"])
    return p

def _snapshot_before_mutation(root: Path, snapshot: Path):
    if snapshot.exists():
        raise ValueError("existing_rollback_snapshot_must_be_handled_before_new_import")
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=snapshot.parent,prefix="snapshot_stage_") as tmp:
        stage=Path(tmp)
        for j,path in enumerate(_snapshot_paths(root)):
            if not path.is_file():
                raise ValueError("missing_preexisting_replacement_file:"+str(path))
            (stage/f"{j:02d}.bak").write_bytes(path.read_bytes())
        metadata={
            "schema":"exodia.gate4-four-review-only-rollback/v1",
            "paths":[str(p.relative_to(root)) for p in _snapshot_paths(root)],
            "sha256":[sha(p.read_bytes()) for p in _snapshot_paths(root)],
        }
        (stage/"metadata.json").write_bytes(jbytes(metadata))
        os.replace(stage,snapshot)
        # TemporaryDirectory cleanup would try to delete the renamed path,
        # but that path is no longer at its original staging location.

def _restore(root: Path, backup: Path):
    if not backup.is_dir():
        raise ValueError("rollback_backup_missing")
    meta=load(backup/"metadata.json")
    if meta.get("schema")!="exodia.gate4-four-review-only-rollback/v1":
        raise ValueError("rollback_metadata_invalid")
    for j,p in enumerate(meta["paths"]):
        raw=(backup/f"{j:02d}.bak").read_bytes()
        if sha(raw)!=meta["sha256"][j]:
            raise ValueError("rollback_backup_corrupted")
    for j,p in enumerate(meta["paths"]):
        target=root/p
        tmp=target.with_name(target.name+".review_restore")
        tmp.write_bytes((backup/f"{j:02d}.bak").read_bytes())
        os.replace(tmp,target)

def apply(root: Path, archive: bytes, *, dry_run=False) -> dict:
    # Image integrity verified before touching ANY protected files.
    images, document, ledger = preflight(root, archive)
    baseline = verify_locked_29(root)
    lock=baseline["contract"]
    idx=baseline["index"]
    already=lock.get("review_only_correction_completed",0)
    if already==4:
        for state,info in images.items():
            row=idx["states"][state]
            if (row["source_sha256"]!=info["source_sha"]
                    or row["image_sha256"]!=info["review_sha"]
                    or row.get("native_production_certified") is not False):
                raise ValueError("inconsistent_already_imported_four_state_library")
        return {"status":"ALREADY_APPLIED","review_only_artwork_count":4,
                "owner_development_accepted_total":33,"production_approved":0,
                "release_enabled":False,"protected_29_verified":29}
    if already!=0 or any(
        lock["correction_briefs"][name]["status"]!="PENDING_NEW_STANDALONE_ARTWORK"
        for name in TARGETS
    ):
        raise ValueError("unexpected_intermediate_four_state_status")
    # Ensure all 29 declared owner-protected source and review SHA pairs
    # match the actual physically stored bytes, not only the registry index.
    protected=document.get("protected_29_sha256",{})
    if len(protected)!=29 or set(protected)!=set(idx["states"])-set(TARGETS):
        raise ValueError("missing_protected_29_exact_sha_declarations")
    for state,claim in protected.items():
        rec=lock["frozen_review_hashes"][state]
        if claim["original_sha256"]!=rec["original_sha256"] or claim["review_sha256"]!=rec["review_sha256"]:
            raise ValueError("protected_29_baseline_mismatch:"+state)
    if dry_run:
        return {"status":"PREFLIGHT_PASS","review_only_artwork_count":4,
                "owner_development_accepted_total":33,"production_approved":0,
                "release_enabled":False,"protected_29_verified":29}

    # Backup ALL old four original sources and old four preview images, plus
    # index and lock. Preserve them exactly for deterministic rollback.
    backup=root/BACKUP
    _snapshot_before_mutation(root,backup)
    try:
        for state,info in images.items():
            old=idx["states"][state]
            old_source=old["source_sha256"]
            old_review=old["image_sha256"]
            if (lock["correction_briefs"][state]["old_original_sha256"]!=old_source
                    or lock["correction_briefs"][state]["old_review_sha256"]!=old_review):
                raise ValueError("previous_four_originals_not_expected:"+state)
            old.update({
                "source_filename":state+"_original.png",
                "source_sha256":info["source_sha"],
                "image_sha256":info["review_sha"],
                "source_dimensions":[1122,1402],
                "normalization":{
                    "kind":NORMALIZATION,
                    "crop_xyxy":[1,1,1121,1401],
                    "cropped_size":[1120,1400],
                    "output_size":[1536,1920],
                    "uniform_scale_factor":1536/1120,
                    "source_pixel_sha256":info["pixel_sha"],
                    "resampled_not_native":True,
                },
                "independent_source_kind":"standalone_original_lowres_review_only",
                "source_generation_handoff":ledger["handoff_archive_name"],
                "generator_model":"ChatGPT built-in image generation (verified handoff provenance)",
                "generator_job_id":None,
                "generation_input_manifest_sha256":None,
                "review_status":"OWNER_ACCEPTED_FOR_DEVELOPMENT_RESAMPLED_NON_NATIVE",
                "owner_development_design_accepted":True,
                "native_production_certified":False,
                "owner_approved":False,
                "geometry_status":"NON_NATIVE_SOURCE_REAL_PIXEL_GEOMETRY_PENDING",
                "production_status":"pending_production_art",
            })
            frozen=lock["frozen_review_hashes"][state]
            frozen["original_sha256"]=info["source_sha"]
            frozen["review_sha256"]=info["review_sha"]
            frozen["development_review_status"]="REVIEW_ONLY_OWNER_ACCEPTED_NON_NATIVE"
            brief=lock["correction_briefs"][state]
            brief["status"]="REVIEW_ONLY_OWNER_ACCEPTED_NON_NATIVE"
            brief["new_original_sha256"]=info["source_sha"]
            brief["new_review_sha256"]=info["review_sha"]
            brief["review_only_source_dimensions"]=[1122,1402]
            brief["review_only_presentation_dimensions"]=[1536,1920]
            brief["native_production_certified"]=False
            brief["owner_final_visual_review"]="DEVELOPMENT_APPROVED_ONLY"
        lock["review_only_correction_completed"]=4
        lock["correction_completed"]=0  # Native production masters still absent.
        lock["owner_final_production_approval"]=False
        if lock["release_enabled"] is not False:
            raise ValueError("release_safety_lock_mutated")
        # Keep the authoritative 28-state source/output ledger consistent
        # with the ACTUAL displayed development originals. These four are
        # deliberately NOT native production candidates.
        queue=load(root/QUEUE)
        queued={r["state_key"]:r for r in queue["states"]}
        if len(queued)!=28 or queue["generated_count"]!=28:
            raise ValueError("invalid_existing_28_state_queue")
        for state,info in images.items():
            row=queued[state]
            row.update({
                "generation_status":"generated_owner_development_review_only",
                "source_sha256":info["source_sha"],
                "output_sha256":info["review_sha"],
                "original_canvas":[1122,1402],
                "output_canvas":[1536,1920],
                "normalization":"REVIEW_ONLY_SYMMETRIC_CROP_THEN_UNIFORM_LANCZOS_UPSCALE",
                "source_native_resolution_eligible":False,
                "native_production_certified":False,
                "generation_job_id":None,
                "generation_job_id_status":"not_present_in_original_handoff",
                "human_pose_review":"owner_accepted_development_only",
                "owner_hash_bound_approval":None,
                "production_status":"pending_production_art",
            })
        queue["review_only_resampled_count"]=4
        queue["native_original_candidate_count"]=24
        # 28 genuine distinct source renders exist, but only 24 are currently
        # native/larger candidates; four lowres originals are preserved.
        queue["generated_count"]=28
        files={}
        for state,info in images.items():
            files[root/STORE/"sources"/f"{state}_original.png"]=info["source"]
            files[root/STORE/"images"/f"{state}.png"]=info["review"]
        files[root/STORE/"review_index.json"]=jbytes(idx)
        files[root/LOCK]=jbytes(lock)
        files[root/QUEUE]=jbytes(queue)
        files[root/STORE/"four_owner_dev_review_only_provenance.json"]=jbytes(document)
        # Atomic replacement per path; any error restores the preflight-tested
        # prior state from byte-verified rollback copies.
        for target,blob in files.items():
            target.parent.mkdir(parents=True,exist_ok=True)
            tmp=target.with_name(target.name+".gate4_review_stage")
            tmp.write_bytes(blob)
            os.replace(tmp,target)
        check=verify_locked_29(root)
        assert check["locked_29_verified"]==29
        for state,info in images.items():
            assert sha((root/STORE/"sources"/f"{state}_original.png").read_bytes())==info["source_sha"]
            assert sha((root/STORE/"images"/f"{state}.png").read_bytes())==info["review_sha"]
    except BaseException:
        _restore(root,backup)
        (root/STORE/"four_owner_dev_review_only_provenance.json").unlink(missing_ok=True)
        raise
    return {"status":"REVIEW_ONLY_INSTALLED","review_only_artwork_count":4,
            "owner_development_accepted_total":33,"production_approved":0,
            "release_enabled":False,"protected_29_verified":29,
            "native_production_certified_count":0,
            "rollback_snapshot":str(BACKUP)}

def rollback(root: Path):
    # Never undo the four without checking that the accepted 29 remain intact.
    verify_locked_29(root)
    lock=load(root/LOCK)
    if lock.get("review_only_correction_completed")!=4:
        raise ValueError("no_review_only_four_installation_to_roll_back")
    _restore(root,root/BACKUP)
    (root/STORE/"four_owner_dev_review_only_provenance.json").unlink(missing_ok=True)
    check=verify_locked_29(root)
    return {"status":"ROLLED_BACK_FOUR_REVIEW_IMAGES",
            "protected_29_verified":check["locked_29_verified"],
            "production_approved":0,"release_enabled":False}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root",type=Path,default=ROOT)
    ap.add_argument("--archive",type=Path)
    ap.add_argument("--dry-run",action="store_true")
    ap.add_argument("--rollback",action="store_true")
    args=ap.parse_args()
    root=args.repo_root.resolve()
    if args.rollback:
        print(json.dumps(rollback(root),indent=2))
    elif args.archive is not None:
        print(json.dumps(apply(root,args.archive.read_bytes(),
                               dry_run=args.dry_run),indent=2))
    else:
        ap.error("Use --archive <file> or --rollback")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
