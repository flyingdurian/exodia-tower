"""Fail-closed EXODIA native portrait-motion intake.

Verifies native PNGs, immutable anchor regions, a static camera, localized
pixel motion and loop continuity. No automatic artistic or production approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any
import numpy as np
from PIL import Image, UnidentifiedImageError

SCHEMA="exodia.portrait-motion/v2"
CANVAS=(1536,1920)
AGENTS={"kiko","router","memory","archives","inventory","vault","ninja","cache","strategy","nova"}
REQUIRED_ANCHORS={"left_eye_corner","right_eye_corner","hair_ornament","left_shoulder","right_shoulder"}
MOTION_PROFILES={
    "idle":{"min_frames":72,"min_seconds":3.0,"max_changed":0.055},
    "working":{"min_frames":48,"min_seconds":2.0,"max_changed":0.085},
    "explaining":{"min_frames":48,"min_seconds":2.0,"max_changed":0.085},
}

def sha256(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def relative_asset_path(value:Any)->bool:
    if not isinstance(value,str) or not value or "\\" in value or ":" in value:
        return False
    p=PurePosixPath(value)
    return not p.is_absolute() and all(part not in ("..",".","") for part in p.parts)

def image_rgb(path:Path)->tuple[np.ndarray,str,str]:
    with Image.open(path) as im:
        if im.format!="PNG" or im.size!=CANVAS or im.mode not in ("RGB","RGBA"):
            raise ValueError(f"native 1536x1920 RGB/RGBA PNG required: {path.name} (got {im.size} {im.mode} {im.format})")
        im.load()
        return np.array(im),sha256(path.read_bytes()),im.mode

def mask_array(path:Path)->np.ndarray:
    with Image.open(path) as im:
        if im.format!="PNG" or im.size!=CANVAS or im.mode not in ("L","1"):
            raise ValueError("motion mask must be 1536x1920 grayscale PNG")
        mask=np.asarray(im.convert("L"))
    if np.any((mask!=0)&(mask!=255)):
        raise ValueError("motion mask must contain only 0/255 values")
    allowed=mask==255
    fraction=float(np.count_nonzero(allowed))/allowed.size
    if not 0.001<=fraction<=0.38:
        raise ValueError("motion mask coverage must be between 0.1% and 38%")
    mx,my=84,106
    if allowed[:my].any() or allowed[-my:].any() or allowed[:,:mx].any() or allowed[:,-mx:].any():
        raise ValueError("motion mask must preserve the 5.5% canvas border")
    return allowed

def anchor_boxes(spec:Any,allowed:np.ndarray)->dict[str,tuple[int,int,int,int]]:
    if not isinstance(spec,dict) or set(spec)!=REQUIRED_ANCHORS:
        raise ValueError("five named pixel-locked anchor rectangles are mandatory")
    boxes={}
    for name,box in spec.items():
        if not isinstance(box,list) or len(box)!=4 or any(type(v) is not int for v in box):
            raise ValueError(f"{name}: [x,y,width,height] integer rectangle required")
        x,y,w,h=box
        if not (0<=x<CANVAS[0] and 0<=y<CANVAS[1] and 12<=w<=120 and 12<=h<=120 and x+w<=CANVAS[0] and y+h<=CANVAS[1]):
            raise ValueError(f"{name}: anchor box out of bounds or too small/large")
        if allowed[y:y+h,x:x+w].any():
            raise ValueError(f"{name}: a locked anchor cannot overlap the motion mask")
        boxes[name]=tuple(box)
    return boxes

def changed_mask(a:np.ndarray,b:np.ndarray)->np.ndarray:
    return np.any(a!=b,axis=2)

def audit(manifest:dict,directory:Path)->dict:
    directory=directory.resolve()
    errors:list[str]=[]
    report:dict[str,Any]={
        "schema":SCHEMA,"agent_id":manifest.get("agent_id"),"state":manifest.get("state"),
        "technical_pass":False,"production_ready":False,
        "human_visual_review":"required","frame_count":0,"errors":errors,"transitions":[]
    }
    if manifest.get("schema")!=SCHEMA:errors.append("wrong_schema")
    if manifest.get("agent_id") not in AGENTS:errors.append("unknown_agent")
    state=manifest.get("state")
    if state not in MOTION_PROFILES:
        errors.append("unsupported_loop_state")
        return report
    profile=MOTION_PROFILES[state]
    if manifest.get("asset_stage")!="candidate_review_only":
        errors.append("no_live_or_production_assets_allowed")
    if manifest.get("source_art_type")!="independently_authored_native_frames":
        errors.append("upscaled_or_storyboard_source_not_eligible")
    if manifest.get("camera")!={"translate_px":[0,0],"zoom":1,"rotation_deg":0,"crop":None}:
        errors.append("camera_transform_must_be_exactly_fixed")
    fps=manifest.get("fps")
    if type(fps) not in (float,int) or not 24<=fps<=30:
        errors.append("fps_must_be_24_to_30")
        fps=0
    if errors:return report
    frames=manifest.get("frames")
    if not isinstance(frames,list) or len(frames)<profile["min_frames"]:
        errors.append(f"minimum_{profile['min_frames']}_independent_frames")
        return report
    if fps and len(frames)/fps<profile["min_seconds"]:
        errors.append("loop_duration_too_short")
    report["frame_count"]=len(frames)
    if len(frames)>240:
        errors.append("too_many_frames_for_intake")
        return report
    mask_name=manifest.get("motion_mask")
    if not relative_asset_path(mask_name):
        errors.append("unsafe_motion_mask_path")
        return report
    try:
        allowed=mask_array(directory/mask_name)
        boxes=anchor_boxes(manifest.get("locked_anchor_boxes"),allowed)
    except (OSError,ValueError,UnidentifiedImageError) as exc:
        errors.append("invalid_motion_mask_or_anchors: "+str(exc))
        return report
    hashes=[]
    first=None
    prev=None
    first_mode=None
    changed_fractions=[]
    total_pixels=CANVAS[0]*CANVAS[1]
    for i,item in enumerate(frames):
        if not isinstance(item,dict) or not relative_asset_path(item.get("path")):
            errors.append(f"frame_{i}_unsafe_path")
            return report
        if "STORYBOARD" in item["path"].upper() or "reframe" in item["path"].lower():
            errors.append(f"frame_{i}_legacy_storyboard_or_reframe")
            return report
        path=(directory/item["path"]).resolve()
        if not path.is_relative_to(directory):
            errors.append(f"frame_{i}_path_escape")
            return report
        try:
            current,digest,mode=image_rgb(path)
        except (OSError,ValueError,UnidentifiedImageError) as exc:
            errors.append(f"frame_{i}_invalid_native_png: {exc}")
            return report
        if item.get("sha256")!=digest:errors.append(f"frame_{i}_fingerprint_mismatch")
        if item.get("source_dimensions")!=list(CANVAS):
            errors.append(f"frame_{i}_native_source_provenance_missing")
        if item.get("render_method")!="artist_native_master":
            errors.append(f"frame_{i}_not_original_master")
        if first_mode is not None and mode!=first_mode:
            errors.append(f"frame_{i}_pixel_mode_changed")
        hashes.append(digest)
        if first is None:
            first,first_mode=current,mode
            prev=current
            continue
        diff_from_start=changed_mask(first,current)
        if np.any(diff_from_start&~allowed):
            errors.append(f"frame_{i}_modified_static_or_anchor_pixels")
        for name,(x,y,w,h) in boxes.items():
            if np.any(diff_from_start[y:y+h,x:x+w]):
                errors.append(f"frame_{i}_locked_anchor_modified_{name}")
        diff_adj=changed_mask(prev,current)
        ratio=float(np.count_nonzero(diff_adj))/total_pixels
        changed_fractions.append(ratio)
        report["transitions"].append(round(ratio,7))
        if ratio>profile["max_changed"]:
            errors.append(f"frame_{i}_abrupt_motion_ratio_{ratio:.5f}")
        if ratio<0.00001:
            errors.append(f"frame_{i}_duplicate_or_frozen_neighbor")
        prev=current
    if first is not None and prev is not None:
        seam=changed_mask(prev,first)
        seam_ratio=float(np.count_nonzero(seam))/total_pixels
        report["loop_seam_fraction"]=round(seam_ratio,7)
        if seam_ratio>profile["max_changed"]:
            errors.append("loop_seam_abrupt_jump")
        if seam_ratio<0.00001:
            errors.append("loop_seam_frozen_or_duplicate")
        nonzero=[x for x in changed_fractions if x>0.00001]
        if nonzero:
            typical=float(np.median(nonzero))
            if max([seam_ratio]+changed_fractions)>typical*4.0+0.001:
                errors.append("frame_to_frame_velocity_outlier")
        if len(set(hashes))!=len(hashes):
            errors.append("duplicate_frame_bytes")
    report["technical_pass"]=not errors
    report["source_authorship_verified"]=False
    report["fluidity_visually_verified"]=False
    report["warning"]="Technical acceptance is not visual, provenance, or release acceptance."
    return report

def main()->int:
    parser=argparse.ArgumentParser(description="Native HD portrait loop gate; NEVER auto-releases artwork")
    parser.add_argument("manifest",type=Path)
    parser.add_argument("--report",type=Path)
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text(encoding="utf-8"))
    result=audit(manifest,args.manifest.parent)
    out=json.dumps(result,indent=2)
    print(out)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(out+"\n",encoding="utf-8")
    return 0 if result["technical_pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
