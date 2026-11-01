import importlib.util
from pathlib import Path
import pytest
np=pytest.importorskip("numpy", reason="A3 optional visual QA requires numpy")
cv2=pytest.importorskip("cv2", reason="A3 optional visual QA requires opencv-python-headless")

BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('vis',BASE/'tools/albedo_visual_preflight.py')
vis=importlib.util.module_from_spec(spec);spec.loader.exec_module(vis)
REF=BASE/'references/approved_full_body.png'
BAD=BASE/'reports/rejected_a1_idle.png'
pytestmark=pytest.mark.skipif(not REF.is_file() or not BAD.is_file(),
    reason='A3 source images are distributed in the approved local reference archive, not embedded in GitHub')

def test_reference_is_exact_approved_asset():
    assert vis.digest(REF)==vis.EXPECTED['front']


def test_known_rejected_primitive_model_is_rejected():
    r=vis.evaluate(REF,BAD,vis.REF_BODY_BOUNDS,(81,75,390,592))
    assert r['status']=='REJECTED_PREVIEW'
    assert r['production_ready'] is False
    assert r['owner_visual_approval'] is False
    assert {'face','collar_crystal','draped_panels'} <= {x.split(' detail')[0] for x in r['technical_nonlikeness_blockers']}


def test_exact_source_cannot_auto_approve_model():
    r=vis.evaluate(REF,REF,vis.REF_BODY_BOUNDS,vis.REF_BODY_BOUNDS)
    assert r['status']=='MANUAL_REVIEW_REQUIRED'
    assert r['production_ready'] is False and r['owner_visual_approval'] is False
    assert not r['technical_nonlikeness_blockers']


def test_wrong_reference_fingerprint_fails_closed(tmp_path):
    a=cv2.imread(str(REF));a[20,20]=0
    tampered=tmp_path/'altered.png';cv2.imwrite(str(tampered),a)
    with pytest.raises(ValueError,match='fingerprint'):
        vis.evaluate(tampered,BAD,vis.REF_BODY_BOUNDS,(81,75,390,592))


def test_invalid_body_bounds_not_accepted():
    with pytest.raises(ValueError,match='bounds'):
        vis.evaluate(REF,BAD,vis.REF_BODY_BOUNDS,(-1,1,360,500))


def test_flat_inaccurate_preview_is_rejected(tmp_path):
    fake=np.full((700,500,3),(200,200,235),dtype=np.uint8)
    path=tmp_path/'flat.png';cv2.imwrite(str(path),fake)
    r=vis.evaluate(REF,path,vis.REF_BODY_BOUNDS,(15,20,485,690))
    assert r['status']=='REJECTED_PREVIEW'
    assert len(r['technical_nonlikeness_blockers'])>=5