"""EXODIA single-state native-portrait intake. Fail closed: no collage slicing.

Geometry is measured from reviewed image-bound pixel landmarks, not automatically
detected. Individual intake never unlocks the global 33-state live release.
"""
from __future__ import annotations
import argparse, json, shutil, sys, tempfile
from pathlib import Path
from portrait_registry_audit import asset, digest, image_audit, landmarks, standalone_provenance, within

PROJECT = Path(__file__).resolve().parents[2]
STAGING = PROJECT / "assets/staging_intake"
PRODUCTION = PROJECT / "orchestrator/frontend/companions/production/kiko"
MANIFEST_SCHEMA = "exodia.standalone-intake-manifest/v1"
APPROVAL_SCHEMA = "exodia.portrait-static-approval-record/v1"

class IntakeRejected(ValueError):
    pass

def require(condition, reason):
    if not condition:
        raise IntakeRejected(reason)

def read_dict(path):
    require(path.is_file(), "file_missing:" + str(path))
    try:
        obj=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError) as exc:
        raise IntakeRejected("invalid_json:" + str(path)) from exc
    require(isinstance(obj,dict), "json_object_required:" + str(path))
    return obj

def safe_path(root, name):
    require(isinstance(name,str) and bool(name) and
            not Path(name).is_absolute() and "\\" not in name and ":" not in name and
            all(part not in (".","..") for part in Path(name).parts),
            "unsafe_staging_filename")
    path=(root/name).resolve()
    require(path.is_relative_to(root.resolve()), "source_outside_staging")
    return path

def validate_manifest(manifest,registry):
    require(manifest.get("schema")==MANIFEST_SCHEMA, "wrong_intake_schema")
    require(manifest.get("character_id")==registry.get("character_id")=="kiko",
            "incorrect_companion")
    require(manifest.get("native_canvas")==[1536,1920], "wrong_manifest_canvas")
    states=registry.get("states",{})
    entries=manifest.get("entries")
    require(isinstance(entries,dict) and set(entries)==set(states) and len(entries)==33,
            "manifest_must_match_exactly_33_registry_states")
    used=set()
    for key,state in states.items():
        row=entries[key]
        require(isinstance(row,dict), "invalid_manifest_entry:"+key)
        require(row.get("category")==state["category"], "category_mismatch:"+key)
        require(row.get("label")==state["label"], "label_mismatch:"+key)
        for field,expected,reason in (
            ("filename",f"incoming/{key}.png","filename_key_mismatch"),
            ("registration_filename",f"registration/{key}.json","registration_key_mismatch"),
            ("approval_filename",f"approvals/{key}.json","approval_key_mismatch")):
            require(row.get(field)==expected, reason+":"+key)
        require(row["filename"] not in used, "duplicate_intake_filename")
        used.add(row["filename"])

def measure_geometry(annotation,image_sha):
    errors=landmarks(annotation,image_sha,{})
    require(not errors, "landmark_gate_failed:"+",".join(errors))
    pts=annotation["points_px"]
    left,right=pts["left_outer_eye"],pts["right_outer_eye"]
    x=(left[0]+right[0])/2
    y=(left[1]+right[1])/2
    head=pts["head_right_edge"][0]-pts["head_left_edge"][0]
    return {"eye_midpoint_px":[x,y],
            "eye_line_percent":round(y/1920*100,5),
            "head_width_px":head,
            "head_width_percent":round(head/1536*100,5),
            "eye_line_target_px":633.6,"head_width_target_px":614.4,
            "origin":"human_annotated_from_actual_image_not_automatic_face_detection"}

def evaluate(source,state_key,staging_root,registry_root,emit):
    require((registry_root/"portrait_registry.json").is_file(),
            "production_registry_missing")
    registry=read_dict(registry_root/"portrait_registry.json")
    manifest=read_dict(staging_root/"manifest_template.json")
    validate_manifest(manifest,registry)
    emit("PASS","MANIFEST: 33 keys map to the authoritative registry")
    require(state_key in registry["states"], "unknown_state_key:"+state_key)
    state=registry["states"][state_key]
    row=manifest["entries"][state_key]
    expected=safe_path(staging_root,row["filename"])
    require(source.resolve()==expected,"source_does_not_match_state_key:"+state_key)
    require(source.is_file() and not source.is_symlink(),
            "standalone_source_missing_or_symlink")
    require(state["status"] in ("missing","pending_review"),
            "state_already_verified_no_overwrite")
    emit("PASS","STATE: "+state_key+" -> "+state["path"])
    image_sha=digest(source)
    errors=image_audit(source,image_sha)
    require(not errors,"native_png_gate_failed:"+",".join(errors))
    emit("PASS","PNG: 1536x1920 (4:5), SHA-256 "+image_sha)
    reg_source=safe_path(staging_root,row["registration_filename"])
    approval_source=safe_path(staging_root,row["approval_filename"])
    annotation=read_dict(reg_source)
    provenance=annotation.get("source_provenance")
    errors=standalone_provenance(provenance,image_sha)
    require(not errors,"standalone_source_rejected:"+",".join(errors))
    require(provenance["original_filename"]==source.name,
            "source_filename_not_bound_to_actual_png")
    emit("PASS","PROVENANCE: declared independent native original, reviewed")
    geometry=measure_geometry(annotation,image_sha)
    emit("PASS","LANDMARKS: eye y={:.2f}px ({:.3f}%), head width={:.2f}px ({:.3f}%)".format(
        geometry["eye_midpoint_px"][1],geometry["eye_line_percent"],
        geometry["head_width_px"],geometry["head_width_percent"]))
    emit("INFO","Coordinates supplied by human reviewer; no computer-vision face detection")
    registration_sha=digest(reg_source)
    approval=read_dict(approval_source)
    require(approval.get("schema")==APPROVAL_SCHEMA,"approval_record_schema_invalid")
    require(approval.get("state_key")==state_key,"approval_state_mismatch")
    require(approval.get("category")==state["category"],"approval_category_mismatch")
    require(approval.get("image_sha256")==image_sha,"approval_image_hash_mismatch")
    require(approval.get("registration_sha256")==registration_sha,
            "approval_registration_hash_mismatch")
    require(approval.get("source_provenance")==provenance,
            "approval_provenance_mismatch")
    require(approval.get("approved_by")=="owner","owner_approval_required")
    owner_ref=approval.get("owner_confirmation_reference")
    require(isinstance(owner_ref,str) and len(owner_ref.strip())>=8,
            "owner_confirmation_reference_required")
    require(annotation.get("owner_confirmation_reference")==owner_ref,
            "registration_owner_approval_mismatch")
    reviewer=approval.get("reviewed_by")
    require(isinstance(reviewer,str) and bool(reviewer.strip()),"reviewer_missing")
    emit("PASS","APPROVAL RECORD: image/registration hashes and state match")
    emit("INFO","Verify actual owner approval independently before --commit")
    return registry,state,reg_source,{
        "status":"PASSED","state_key":state_key,"category":state["category"],
        "image_sha256":image_sha,"registration_sha256":registration_sha,
        "geometry":geometry,"production_path":state["path"],
        "owner_confirmation_reference":owner_ref,"reviewed_by":reviewer,
        "live_release_enabled":False}

def ingest(source,state_key,staging_root=STAGING,registry_root=PRODUCTION,
           commit=False,emit=lambda level,message:None):
    staging_root=staging_root.resolve()
    registry_root=registry_root.resolve()
    require(not registry_root.is_relative_to(staging_root) and
            not staging_root.is_relative_to(registry_root),
            "staging_and_production_must_be_separate")
    registry,state,reg_source,report=evaluate(
        source,state_key,staging_root,registry_root,emit)
    for other_key,other in registry["states"].items():
        if other_key!=state_key and other.get("status")=="verified":
            require(other.get("sha256")!=report["image_sha256"],
                    "duplicate_image_sha_across_states")
    require(registry.get("release",{}).get("enabled") is False,
            "single_file_intake_must_not_modify_live_release")
    if not commit:
        emit("PASS","DRY RUN: all individual gates passed; no production changes")
        return {**report,"committed":False,"mode":"dry_run"}
    with tempfile.TemporaryDirectory(prefix=".portrait-intake-",
                                     dir=registry_root.parent) as temp:
        tempdir=Path(temp)
        stage=tempdir/"new"
        backup=tempdir/"backup"
        shutil.copytree(registry_root,stage)
        dst=within(stage,state["path"])
        reg_dst=within(stage,state["registration_path"])
        require(not dst.exists() and not reg_dst.exists(),
                "production_file_exists_no_overwrite")
        dst.parent.mkdir(parents=True,exist_ok=True)
        reg_dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,dst)
        shutil.copy2(reg_source,reg_dst)
        require(digest(dst)==report["image_sha256"],"copied_image_hash_mismatch")
        require(digest(reg_dst)==report["registration_sha256"],
                "copied_registration_hash_mismatch")
        row=registry["states"][state_key]
        row.update(status="verified",sha256=report["image_sha256"],
                   registration_sha256=report["registration_sha256"],
                   verified_by=report["reviewed_by"],
                   owner_approval_reference=report["owner_confirmation_reference"])
        registry["release"]["enabled"]=False
        (stage/"portrait_registry.json").write_text(
            json.dumps(registry,indent=2)+"\n",encoding="utf-8")
        errors=asset(stage,row,registry["canvas"])
        require(not errors,"post_copy_asset_audit_failed:"+",".join(errors))
        emit("PASS","STAGED: independent registry audit passed for single asset")
        registry_root.rename(backup)
        try:
            stage.rename(registry_root)
        except Exception:
            backup.rename(registry_root)
            raise
    emit("PASS","COMMITTED: "+state["path"]+" and reviewed registration")
    emit("INFO","Global release remains DISABLED (33-state audit required)")
    return {**report,"committed":True,"mode":"single_state_staged"}

def main(argv=None):
    p=argparse.ArgumentParser(description="Exodia: single original 1536x1920 PNG intake")
    p.add_argument("--state",required=True)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--staging-root",type=Path,default=STAGING)
    p.add_argument("--registry-root",type=Path,default=PRODUCTION)
    p.add_argument("--commit",action="store_true")
    p.add_argument("--report",type=Path)
    opts=p.parse_args(argv)
    def emit(level,message):
        print(f"[{level}] {message}",file=sys.stderr,flush=True)
    try:
        result=ingest(opts.source,opts.state,opts.staging_root,
                      opts.registry_root,commit=opts.commit,emit=emit)
        code=0
    except (IntakeRejected,OSError,ValueError,KeyError) as exc:
        emit("FAIL",str(exc))
        result={"status":"FAILED","state_key":opts.state,
                "errors":[str(exc)],"committed":False,
                "live_release_enabled":False}
        code=1
    if opts.report:
        opts.report.parent.mkdir(parents=True,exist_ok=True)
        opts.report.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    return code
if __name__=="__main__":
    raise SystemExit(main())
