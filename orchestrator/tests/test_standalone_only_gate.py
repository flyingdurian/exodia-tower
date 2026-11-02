"""Prohibit composite-derived Albedo production art; synthetic fixtures only."""
import json,sys
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from portrait_registry_audit import standalone_provenance,asset,digest,image_audit,audit
ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/"orchestrator/frontend/companions/production/kiko/portrait_registry.json"
def approved(sha):
    return dict(schema="exodia.independent-portrait-source/v1",source_kind="independent_standalone_native",
                derived_from_composite=False,native_canvas=[1536,1920],original_sha256=sha,
                original_filename="albedo_neutral_individual.png",
                source_method="independent_image_render",human_source_review="completed")
def test_valid_metadata_format_not_proof_of_authenticity():
    assert standalone_provenance(approved("a"*64),"a"*64)==[]
def test_slices_and_unreviewed_files_rejected():
    assert "standalone_provenance_missing" in standalone_provenance(None,"a"*64)
    for variant in ("grid_slice","collage_crop","upscaled_sheet"):
        p=approved("a"*64);p["source_kind"]=variant
        assert "source_not_independent_standalone" in standalone_provenance(p,"a"*64)
    p=approved("a"*64);p["derived_from_composite"]=True
    assert "composite_source_prohibited" in standalone_provenance(p,"a"*64)
def test_source_filename_dimensions_and_sha_validation():
    for name in ("albedo_board.png","contact_sheet.png","cropped_face.png","grid_atlas.png"):
        p=approved("a"*64);p["original_filename"]=name
        assert "derived_composite_filename_disallowed" in standalone_provenance(p,"a"*64)
    p=approved("b"*64);p["native_canvas"]=[1122,1402];p["human_source_review"]="pending"
    errors=standalone_provenance(p,"a"*64)
    assert "source_not_native_1536x1920" in errors
    assert "original_image_sha_mismatch" in errors
    assert "independent_source_review_missing" in errors
def test_asset_audit_refuses_synthetic_native_png_without_source_review(tmp_path):
    p=tmp_path/"frames/expressions/neutral.png";p.parent.mkdir(parents=True)
    Image.new("RGB",(1536,1920)).save(p);sha=digest(p)
    assert image_audit(p,sha)==[]
    meta={"image_sha256":sha,"method":"human_annotated_from_actual_image",
          "human_review":"completed","owner_confirmation_reference":"TEST-NOT-REAL-APPROVAL",
          "points_px":{"left_outer_eye":[610,633.6],"right_outer_eye":[926,633.6],
                       "head_left_edge":[460,410],"head_right_edge":[1074.4,410],
                       "ornament_attachment":[1040,280],"left_shoulder":[430,960],
                       "right_shoulder":[1100,960]}}
    rp=tmp_path/"registration/expressions/neutral.json";rp.parent.mkdir(parents=True)
    rp.write_text(json.dumps(meta))
    entry=dict(status="verified",path="frames/expressions/neutral.png",sha256=sha,
               registration_path="registration/expressions/neutral.json",
               registration_sha256=digest(rp),owner_approval_reference="TEST-NOT-REAL",
               verified_by="synthetic")
    assert "standalone_provenance_missing" in asset(tmp_path,entry,{})
    meta["source_provenance"]=approved(sha)
    meta["source_provenance"]["derived_from_composite"]=True
    rp.write_text(json.dumps(meta));entry["registration_sha256"]=digest(rp)
    assert "composite_source_prohibited" in asset(tmp_path,entry,{})
def test_banned_slicer_files_are_gone_and_live_gate_stays_closed():
    assert not (ROOT/"orchestrator/tools/slice_master_boards.py").exists()
    assert not (ROOT/"orchestrator/tests/test_slice_master_boards.py").exists()
    assert not (ROOT/".github/workflows/exodia-grid-slicer.yml").exists()
    assert not (ROOT/"docs/ALBEDO_APPROVED_BOARD_EXTRACTION.md").exists()
    assert audit(REG)["production_ready"] is False
