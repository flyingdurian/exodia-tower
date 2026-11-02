"""Synthetic normalization fixtures: cannot be promoted as Albedo artwork."""
import json,sys
from pathlib import Path
from PIL import Image
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from portrait_normalization import normalize_portrait,transform_landmarks,NormalizationRejected
from ingest_standalone_portrait import ingest,IntakeRejected
from portrait_registry_audit import digest,asset
from test_ingest_standalone_portrait import setup

def test_lanczos_crop_4x5(tmp_path):
    p=tmp_path/"source.png"
    Image.new("RGB",(1856,2304),(50,20,80)).save(p)
    png,info=normalize_portrait(p)
    out=tmp_path/"target.png";out.write_bytes(png)
    assert Image.open(out).size==(1536,1920)
    assert info["crop_box"]==[6,0,1849,2304]
    assert info["scale_x"]<=1 and info["scale_y"]<=1
    eyes=transform_landmarks({"eyes":[928,760.32]},info)
    assert abs(eyes["eyes"][1]-633.6)<0.03

def test_never_upscale(tmp_path):
    p=tmp_path/"small.png";Image.new("RGB",(1122,1402)).save(p)
    with pytest.raises(NormalizationRejected,match="downsample_only_source_too_small"):normalize_portrait(p)

def reviewed_source(intake):
    p=intake/"incoming/idle.png";p.parent.mkdir(parents=True,exist_ok=True)
    Image.new("RGB",(1856,2304),(50,70,90)).save(p)
    sha=digest(p);_,t=normalize_portrait(p)
    def inv(x,y):return [round(x/t["scale_x"]+t["crop_box"][0],5),round(y/t["scale_y"]+t["crop_box"][1],5)]
    pts={"left_outer_eye":inv(610,633.6),"right_outer_eye":inv(926,633.6),
        "head_left_edge":inv(460,410),"head_right_edge":inv(1074.4,410),
        "ornament_attachment":inv(1040,280),"left_shoulder":inv(430,960),
        "right_shoulder":inv(1100,960)}
    prov=dict(schema="exodia.independent-portrait-source/v1",
        source_kind="independent_standalone_native",derived_from_composite=False,
        native_canvas=[1856,2304],original_sha256=sha,original_filename="idle.png",
        source_method="independent_image_render",human_source_review="completed")
    ref="SYNTHETIC-TEST-NOT-REAL"
    reg=dict(source_image_sha256=sha,source_provenance=prov,source_points_px=pts,
        method="human_annotated_from_actual_image",human_review="completed",
        owner_confirmation_reference=ref)
    approval=dict(schema="exodia.portrait-static-approval-record/v1",
        state_key="idle",category="action",source_image_sha256=sha,
        source_provenance=prov,allow_normalization=True,
        normalized_visual_review="completed",approved_by="owner",
        owner_confirmation_reference=ref,reviewed_by="synthetic_fixture")
    r=intake/"registration/idle.json";r.parent.mkdir(parents=True,exist_ok=True)
    a=intake/"approvals/idle.json";a.parent.mkdir(parents=True,exist_ok=True)
    r.write_text(json.dumps(reg));a.write_text(json.dumps(approval))
    return p,r,a

def test_dryrun_and_atomic_normalization_commit(setup):
    intake,production,_=setup
    p,_,_=reviewed_source(intake)
    before=ingest(p,"idle",intake,production,normalize=True)
    assert before["status"]=="PASSED" and before["committed"] is False
    assert not (production/"frames/actions/idle.png").exists()
    result=ingest(p,"idle",intake,production,normalize=True,commit=True)
    assert result["committed"] and result["normalized"]
    assert (production/"sources/actions/idle_original.png").is_file()
    registry=json.loads((production/"portrait_registry.json").read_text())
    assert asset(production,registry["states"]["idle"],registry["canvas"])==[]
    assert registry["release"]["enabled"] is False

def test_approval_and_bad_face_anchor_rejected(setup):
    intake,prod,_=setup;p,r,a=reviewed_source(intake)
    approval=json.loads(a.read_text());approval["normalized_visual_review"]="pending"
    a.write_text(json.dumps(approval))
    with pytest.raises(IntakeRejected,match="normalized_visual_approval_required"):
        ingest(p,"idle",intake,prod,normalize=True,commit=True)
    approval["normalized_visual_review"]="completed";a.write_text(json.dumps(approval))
    reg=json.loads(r.read_text())
    for k in ("left_outer_eye","right_outer_eye"):reg["source_points_px"][k][1]+=200
    r.write_text(json.dumps(reg))
    with pytest.raises(IntakeRejected,match="landmark_gate_failed"):
        ingest(p,"idle",intake,prod,normalize=True,commit=True)
    assert not (prod/"frames").exists()
