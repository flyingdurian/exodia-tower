"""Fail-closed standalone intake regression tests; synthetic fixtures only."""
import json,sys
from pathlib import Path
import pytest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from ingest_standalone_portrait import ingest,validate_manifest,IntakeRejected
from portrait_registry_audit import digest,asset,audit
ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"assets/staging_intake/manifest_template.json"

@pytest.fixture
def setup(tmp_path):
    intake=tmp_path/"assets/staging_intake";intake.mkdir(parents=True)
    dst=tmp_path/"orchestrator/frontend/companions/production/kiko";dst.mkdir(parents=True)
    template=json.loads(MANIFEST.read_text())
    (intake/"manifest_template.json").write_text(json.dumps(template))
    states={}
    for key,meta in template["entries"].items():
        family="expressions" if meta["category"]=="expression" else "actions"
        states[key]=dict(label=meta["label"],category=meta["category"],status="missing",
                         path=f"frames/{family}/{key}.png",
                         registration_path=f"registration/{family}/{key}.json",
                         sha256=None,registration_sha256=None,
                         verified_by=None,owner_approval_reference=None)
    registry=dict(schema="exodia.portrait-state-registry/v1",character_id="kiko",
        states=states,loops={
            "idle_breathing":dict(status="deferred"),
            "working_computer":dict(status="deferred"),
            "explaining_talk_gesture":dict(status="deferred")},
        canvas=dict(width=1536,height=1920,aspect_ratio="4:5",
                    eye_line_target_px=633.6,eye_midpoint_target_x_px=768,
                    head_width_target_px=614.4),
        release=dict(enabled=False,mode="static_portraits"))
    (dst/"portrait_registry.json").write_text(json.dumps(registry))
    return intake,dst,registry

def make_files(intake,size=(1536,1920)):
    image=intake/"incoming/idle.png";image.parent.mkdir(parents=True)
    Image.new("RGB",size,(23,46,70)).save(image);sha=digest(image)
    provenance=dict(schema="exodia.independent-portrait-source/v1",
        source_kind="independent_standalone_native",derived_from_composite=False,
        native_canvas=[1536,1920],original_sha256=sha,
        original_filename="idle.png",source_method="standalone_artist_export",
        human_source_review="completed")
    reference="SYNTHETIC-TEST-NOT-REAL-APPROVAL"
    annot=dict(image_sha256=sha,source_provenance=provenance,
        method="human_annotated_from_actual_image",human_review="completed",
        owner_confirmation_reference=reference,
        points_px={"left_outer_eye":[612,633.6],"right_outer_eye":[924,633.6],
        "head_left_edge":[460,415],"head_right_edge":[1074.4,415],
        "ornament_attachment":[1050,265],
        "left_shoulder":[415,960],"right_shoulder":[1120,960]})
    reg=intake/"registration/idle.json";reg.parent.mkdir(parents=True)
    reg.write_text(json.dumps(annot))
    approval=dict(schema="exodia.portrait-static-approval-record/v1",state_key="idle",
        category="action",image_sha256=sha,registration_sha256=digest(reg),
        source_provenance=provenance,approved_by="owner",
        owner_confirmation_reference=reference,reviewed_by="synthetic_fixture")
    approve=intake/"approvals/idle.json";approve.parent.mkdir(parents=True)
    approve.write_text(json.dumps(approval))
    return image,reg,approve

def test_template_all_33_keys(setup):
    src,dst,reg=setup
    template=json.loads((src/"manifest_template.json").read_text())
    assert len(template["entries"])==33
    validate_manifest(template,reg)

def test_manifest_wrong_state_rejected(setup):
    src,dst,reg=setup
    template=json.loads((src/"manifest_template.json").read_text())
    template["entries"]["idle"]["filename"]="incoming/working.png"
    with pytest.raises(IntakeRejected,match="filename_key_mismatch"):
        validate_manifest(template,reg)

def test_dry_run_measurement_and_no_file_modification(setup):
    src,dst,_=setup;image,_,_=make_files(src)
    logs=[]
    output=ingest(image,"idle",src,dst,emit=lambda k,m:logs.append(m))
    assert output["status"]=="PASSED" and not output["committed"]
    assert output["geometry"]["eye_line_percent"]==33.0
    assert abs(output["geometry"]["head_width_percent"]-40)<.00001
    assert not (dst/"frames").exists()

def test_atomic_single_file_commit_does_not_unlock_release(setup):
    src,dst,_=setup;image,_,_=make_files(src)
    outcome=ingest(image,"idle",src,dst,commit=True)
    assert outcome["committed"]
    assert image.exists() and (dst/"frames/actions/idle.png").is_file()
    registry=json.loads((dst/"portrait_registry.json").read_text())
    assert registry["release"]["enabled"] is False
    assert asset(dst,registry["states"]["idle"],registry["canvas"])==[]
    assert audit(dst/"portrait_registry.json")["production_ready"] is False
    with pytest.raises(IntakeRejected,match="state_already_verified"):
        ingest(image,"idle",src,dst,commit=True)

def test_wrong_dimensions_fail_before_commit(setup):
    src,dst,_=setup;image,_,_=make_files(src,size=(1122,1402))
    with pytest.raises(IntakeRejected,match="native_png_gate_failed"):
        ingest(image,"idle",src,dst,commit=True)
    assert not (dst/"frames").exists()

def test_wrong_key_and_missing_owner_approval_fail(setup):
    src,dst,_=setup;image,_,ap=make_files(src)
    with pytest.raises(IntakeRejected,match="source_does_not_match_state_key"):
        ingest(image,"working",src,dst)
    ap.unlink()
    with pytest.raises(IntakeRejected,match="file_missing"):
        ingest(image,"idle",src,dst,commit=True)

def test_bad_landmark_and_composite_rejected(setup):
    src,dst,_=setup;image,reg,approval_file=make_files(src)
    info=json.loads(reg.read_text())
    info["points_px"]["left_outer_eye"][1]=720
    info["points_px"]["right_outer_eye"][1]=720
    reg.write_text(json.dumps(info))
    ap=json.loads(approval_file.read_text())
    ap["registration_sha256"]=digest(reg)
    approval_file.write_text(json.dumps(ap))
    with pytest.raises(IntakeRejected,match="landmark_gate_failed"):
        ingest(image,"idle",src,dst)
    info["points_px"]["left_outer_eye"][1]=633.6
    info["points_px"]["right_outer_eye"][1]=633.6
    info["source_provenance"]["derived_from_composite"]=True
    reg.write_text(json.dumps(info))
    ap["source_provenance"]=info["source_provenance"]
    ap["registration_sha256"]=digest(reg)
    approval_file.write_text(json.dumps(ap))
    with pytest.raises(IntakeRejected,match="composite_source_prohibited"):
        ingest(image,"idle",src,dst)
