"""Registry tests use synthetic fixtures, never approved user artwork."""
import importlib.util,json
from pathlib import Path
from PIL import Image
SOURCE=Path(__file__).resolve().parents[1]/"tools"/"portrait_registry_audit.py"
spec=importlib.util.spec_from_file_location("portrait_registry_audit",SOURCE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
REG=Path(__file__).resolve().parents[1]/"frontend"/"companions"/"production"/"kiko"/"portrait_registry.json"
def test_state_map_exact():
    data=json.loads(REG.read_text())
    assert len(data["states"])==33 and len(data["loops"])==3
    assert set(data["states"])==set(m.EXPRESSIONS+m.ACTIONS)
def test_missing_assets_fail_closed():
    r=m.audit(REG)
    assert r["status"]=="FAILED" and not r["production_ready"]
    assert r["states_verified"]==0 and r["loops_verified"]==0
def test_traversal_rejected(tmp_path):
    for name in ("../secret.png","/tmp/secret.png","C:\\temp\\s.png"):
        try:m.within(tmp_path,name)
        except ValueError:pass
        else:raise AssertionError("unsafe path accepted")
def test_canvas_and_sha_integrity(tmp_path):
    p=tmp_path/"still.png"
    Image.new("RGB",(1122,1402)).save(p)
    e=m.image_audit(p,"0"*64)
    assert any("wrong_canvas" in x for x in e)
    assert "sha256_mismatch" in e
    Image.new("RGB",(1536,1920),(2,2,3)).save(p)
    assert m.image_audit(p,m.digest(p))==[]
def test_eye_and_head_registration_required():
    record={"image_sha256":"a"*64,"method":"human_annotated_from_actual_image",
      "human_review":"completed","owner_confirmation_reference":"mock-approval-test",
      "points_px":{"left_outer_eye":[610,633.6],"right_outer_eye":[926,633.6],
       "head_left_edge":[460,410],"head_right_edge":[1074.4,410],
       "ornament_attachment":[1040,280],"left_shoulder":[430,960],"right_shoulder":[1100,960]}}
    assert m.landmarks(record,"a"*64,{})==[]
    record["points_px"]["right_outer_eye"][1]=740
    assert any("eye_y_out_of_range" in e for e in m.landmarks(record,"a"*64,{}))
def test_marking_verified_without_image_is_not_enough():
    data=json.loads(REG.read_text());entry=data["states"]["neutral"].copy()
    entry.update(status="verified",verified_by="mock",owner_approval_reference="mock-confirmation")
    assert "file_missing" in m.asset(REG.parent,entry,data["canvas"])
