"""Exodia: fail-closed 33-state PNG/geometry/SHA intake; no auto face detection."""
import argparse, hashlib, json, re
from pathlib import Path
from PIL import Image
SCHEMA="exodia.portrait-state-registry/v1"
EXPRESSIONS=("neutral happy joyful excited gentle smiling_closed laughing amused confident serious focused thinking curious surprised concerned worried sad disappointed angered blushing").split()
ACTIONS=("idle working monitoring pointing explaining celebrating defeat stretching sleeping waking_up tantrum thinking_deeper awaiting_command").split()
LOOPS=("idle_breathing working_computer explaining_talk_gesture").split()
SIZE=(1536,1920)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def within(root,rel):
    if not isinstance(rel,str) or not rel or "\\" in rel or ":" in rel:raise ValueError("invalid_path")
    path=(root/rel).resolve()
    if Path(rel).is_absolute() or ".." in Path(rel).parts or not path.is_relative_to(root.resolve()):raise ValueError("unsafe_path")
    return path
def image_audit(path,sha):
    e=[]
    if not path.is_file():return ["file_missing"]
    try:
        with Image.open(path) as im:
            if im.format!="PNG":e.append("not_png")
            if im.size!=SIZE:e.append("wrong_canvas_"+str(im.size))
            im.verify()
    except Exception as ex:return ["invalid_png_"+str(ex)]
    if not isinstance(sha,str) or not re.fullmatch("[0-9a-f]{64}",sha):e.append("missing_sha256")
    elif digest(path)!=sha:e.append("sha256_mismatch")
    return e
def standalone_provenance(source,image_sha):
    if not isinstance(source,dict):return ["standalone_provenance_missing"]
    errors=[]
    if source.get("schema")!="exodia.independent-portrait-source/v1":errors.append("invalid_standalone_source_schema")
    normalized=source.get("source_kind")=="independent_standalone_normalized"
    if source.get("source_kind") not in ("independent_standalone_native","independent_standalone_normalized"):
        errors.append("source_not_independent_standalone")
    if source.get("derived_from_composite") is not False:errors.append("composite_source_prohibited")
    if normalized:
        original=source.get("original_canvas")
        if not isinstance(original,list) or len(original)!=2 or any(type(v)!=int for v in original) or original[0]<1536 or original[1]<1920:
            errors.append("source_not_high_resolution")
        if source.get("normalized_canvas")!=[1536,1920]:errors.append("normalized_canvas_invalid")
        if source.get("normalized_sha256")!=image_sha:errors.append("normalized_sha256_mismatch")
        if source.get("original_sha256")==image_sha:errors.append("normalized_identical_to_source")
        if source.get("normalization_method")!="center_crop_lanczos_downsample":errors.append("normalization_method_invalid")
        if not isinstance(source.get("original_artifact_path"),str):errors.append("original_artifact_path_missing")
        if not isinstance(source.get("normalization_transform"),dict):errors.append("normalization_transform_missing")
        if source.get("normalization_visual_review")!="completed":errors.append("normalized_composition_review_missing")
    else:
        if source.get("native_canvas")!=[1536,1920]:errors.append("source_not_native_1536x1920")
        if source.get("original_sha256")!=image_sha:errors.append("original_image_sha_mismatch")
    if source.get("source_method") not in ("independent_image_render","standalone_artist_export"):errors.append("source_method_not_standalone")
    if source.get("human_source_review")!="completed":errors.append("independent_source_review_missing")
    name=source.get("original_filename")
    if not isinstance(name,str) or not name.lower().endswith(".png") or Path(name).name!=name:
        errors.append("original_filename_invalid")
    elif any(t in name.lower() for t in ("collage","grid","board","atlas","contact","slice","crop","montage","thumbnail","upscale","reframe","normalized")):
        errors.append("derived_composite_filename_disallowed")
    return errors

def normalized_asset_audit(root,provenance,image_sha):
    if not isinstance(provenance,dict) or provenance.get("source_kind")!="independent_standalone_normalized":return []
    from portrait_normalization import normalize_portrait
    try:
        source=within(root,provenance["original_artifact_path"])
        if not source.is_file():return ["normalized_original_missing"]
        if digest(source)!=provenance.get("original_sha256"):return ["normalized_original_sha256_mismatch"]
        import hashlib
        normalized,transform=normalize_portrait(source)
        if hashlib.sha256(normalized).hexdigest()!=image_sha:return ["normalized_reproduction_sha256_mismatch"]
        if transform!=provenance.get("normalization_transform"):return ["normalized_transform_mismatch"]
        return []
    except Exception as exc:return ["normalized_source_validation_failed_"+str(exc)]

def landmarks(meta,sha,spec):
    e=[]
    if meta.get("image_sha256")!=sha:e.append("landmarks_not_bound_to_image")
    if meta.get("method")!="human_annotated_from_actual_image" or meta.get("human_review")!="completed":e.append("human_landmarks_not_verified")
    if not isinstance(meta.get("owner_confirmation_reference"),str) or len(meta["owner_confirmation_reference"])<8:e.append("no_owner_confirmation_reference")
    pts=meta.get("points_px")
    keys=["left_outer_eye","right_outer_eye","head_left_edge","head_right_edge","ornament_attachment","left_shoulder","right_shoulder"]
    if not isinstance(pts,dict) or any(x not in pts for x in keys):return e+["missing_seven_landmarks"]
    for key in keys:
        point=pts[key]
        if not isinstance(point,list) or len(point)!=2 or not all(type(x) in (int,float) for x in point) or not (0<=point[0]<1536 and 0<=point[1]<1920):return e+["invalid_landmark_"+key]
    a,b=pts["left_outer_eye"],pts["right_outer_eye"]
    if a[0]>=b[0]:e.append("eye_order_invalid")
    measured={"eye_y":(a[1]+b[1])/2,"eye_x":(a[0]+b[0])/2,"head_width":pts["head_right_edge"][0]-pts["head_left_edge"][0]}
    for key,target,tol in [("eye_y",633.6,2),("eye_x",768,8),("head_width",614.4,4)]:
        if abs(measured[key]-target)>tol:e.append(key+"_out_of_range_"+str(round(measured[key],2)))
    return e
def asset(root,entry,spec):
    e=[]
    if entry.get("status")!="verified":e.append("not_verified")
    try:p=within(root,entry.get("path"));r=within(root,entry.get("registration_path"))
    except Exception as ex:return ["invalid_path_"+str(ex)]
    e.extend(image_audit(p,entry.get("sha256")))
    if not r.is_file():e.append("registration_missing")
    else:
        if digest(r)!=entry.get("registration_sha256"):e.append("registration_sha256_mismatch")
        try:
            data=json.loads(r.read_text())
            e.extend(landmarks(data,entry.get("sha256"),spec))
            e.extend(standalone_provenance(data.get("source_provenance"),entry.get("sha256")))
            e.extend(normalized_asset_audit(root,data.get("source_provenance"),entry.get("sha256")))
        except Exception as ex:e.append("registration_invalid_"+str(ex))
    if not isinstance(entry.get("owner_approval_reference"),str) or len(entry["owner_approval_reference"])<8:e.append("approval_not_documented")
    if not entry.get("verified_by"):e.append("reviewer_missing")
    return e
def loop(root,entry):
    e=[]
    if entry.get("status")!="verified" or not entry.get("production_ready"):e.append("loop_not_approved")
    try:p=within(root,entry.get("manifest_path"))
    except Exception as ex:return ["loop_path_invalid_"+str(ex)]
    if not p.is_file():return e+["loop_manifest_missing"]
    if digest(p)!=entry.get("manifest_sha256"):e.append("loop_manifest_sha256_mismatch")
    try:data=json.loads(p.read_text());frames=data["frames"]
    except Exception as ex:return e+["invalid_loop_manifest_"+str(ex)]
    if not isinstance(frames,list) or len(frames)<entry["min_frames"]:return e+["insufficient_frames"]
    hashes=set()
    for i,f in enumerate(frames):
        try:
            errors=image_audit(within(root,f.get("path")),f.get("sha256"))
            if f.get("sha256") in hashes:errors.append("duplicate_hash")
            hashes.add(f.get("sha256"))
        except Exception as ex:errors=["invalid_path_"+str(ex)]
        e.extend("frame_"+str(i)+"_"+x for x in errors)
    if data.get("pixel_lock_audit")!="passed" or data.get("seam_audit")!="passed":e.append("motion_validation_required")
    if not entry.get("owner_approval_reference"):e.append("owner_loop_approval_missing")
    return e
def audit(registry):
    d=json.loads(registry.read_text());root=registry.parent
    e=[]
    if d.get("schema")!=SCHEMA or d.get("character_id")!="kiko":e.append("schema_or_agent_wrong")
    if set(d.get("states",{}))!=set(EXPRESSIONS+ACTIONS):e.append("not_exactly_33_states")
    if set(d.get("loops",{}))!=set(LOOPS):e.append("not_exactly_three_loops")
    spec=d.get("canvas",{})
    if (spec.get("width"),spec.get("height"),spec.get("aspect_ratio"))!=(1536,1920,"4:5"):e.append("wrong_master_spec")
    if (spec.get("eye_line_target_px"),spec.get("head_width_target_px"),spec.get("eye_midpoint_target_x_px"))!=(633.6,614.4,768):e.append("wrong_anchor_targets")
    if e:return {"status":"FAILED","production_ready":False,"errors":e}
    states={}
    for name,entry in d["states"].items():
        errors=asset(root,entry,spec)
        if entry.get("category")!=("expression" if name in EXPRESSIONS else "action"):errors.append("wrong_category")
        states[name]={"passed":not errors,"errors":errors}
    # Reject reused original sources even when exported PNGs differ by labels, tint or recompression.
    original_seen={}
    for state_key,state in d['states'].items():
        if state.get('status')!='verified':continue
        try:
            registration=json.loads(within(root,state['registration_path']).read_text())
            src_hash=registration.get('source_provenance',{}).get('original_sha256')
            if not isinstance(src_hash,str) or not re.fullmatch('[0-9a-f]{64}',src_hash):
                states[state_key]['errors'].append('original_source_hash_missing')
                states[state_key]['passed']=False
            elif src_hash in original_seen:
                other=original_seen[src_hash]
                for state_name in (state_key,other):
                    states[state_name]['errors'].append('cloned_original_source_hash')
                    states[state_name]['passed']=False
            else:original_seen[src_hash]=state_key
            if registration.get('state_specific_visual_review')!='completed':
                states[state_key]['errors'].append('distinct_pose_or_expression_review_missing')
                states[state_key]['passed']=False
        except Exception:
            states[state_key]['errors'].append('uniqueness_evidence_unavailable')
            states[state_key]['passed']=False
    # No visual state is allowed to alias another state's PNG hash.
    seen={}
    for key,entry in d["states"].items():
        sha=entry.get("sha256")
        if entry.get("status")=="verified" and isinstance(sha,str) and re.fullmatch("[0-9a-f]{64}",sha):
            if sha in seen:
                states[key]["errors"].append("duplicate_static_image_sha256")
                states[key]["passed"]=False
                states[seen[sha]]["errors"].append("duplicate_static_image_sha256")
                states[seen[sha]]["passed"]=False
            else:seen[sha]=key
    mode=d.get("release",{}).get("mode")
    if mode not in ("static_portraits","static_and_loops"):e.append("unknown_release_mode")
    if mode=="static_and_loops":
        loops={name:{"errors":loop(root,entry)} for name,entry in d["loops"].items()}
    else:
        loops={name:{"status":"DEFERRED","errors":[]} for name in d["loops"]}
    npass=sum(v["passed"] for v in states.values())
    lpass=sum(not v["errors"] for v in loops.values()) if mode=="static_and_loops" else 0
    if d.get("release",{}).get("enabled") is not True:e.append("release_disabled")
    owner_release=d.get("release",{}).get("owner_static_release_reference")
    if not isinstance(owner_release,str) or len(owner_release.strip())<8:e.append("owner_static_release_confirmation_missing")
    if npass!=33:e.append("verified_states_"+str(npass)+"_of_33")
    if mode=="static_and_loops" and lpass!=3:e.append("verified_loops_"+str(lpass)+"_of_3")
    passed=not e
    return {"schema":SCHEMA,"status":"PASSED" if passed else "FAILED",
      "production_ready":passed,"static_release_pass":passed and mode=="static_portraits",
      "release_mode":mode,"canvas":[1536,1920],"eye_y_target_px":633.6,
      "head_width_target_px":614.4,"states_checked":33,"states_verified":npass,
      "loops_checked":3,"loops_verified":lpass,"errors":e,
      "states":states,"loops":loops,
      "warning":"The validator checks human-reviewed image-bound landmarks but cannot detect facial features or authenticate approval."}

def main():
    p=argparse.ArgumentParser();p.add_argument("registry",type=Path);p.add_argument("--report",type=Path)
    args=p.parse_args();result=audit(args.registry)
    output=json.dumps(result,indent=2)
    print(output)
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(output+"\n")
    return 0 if result["production_ready"] else 1
if __name__=="__main__":raise SystemExit(main())
