"""A2 safeguards. Mock inputs are NOT actual Albedo art."""
import importlib.util, json, struct
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('a2',root/'tools'/'validate_albedo_lookdev.py')
a2=importlib.util.module_from_spec(s);s.loader.exec_module(a2)
def test_missing_model_blocks_approval(tmp_path):
    assert a2.review(tmp_path)['production_ready'] is False
    spec={'schema':'exodia.albedo-lookdev/v1','character_id':'kiko',
        'reference_sha256':a2.REF,'candidate_kind':'full_body_3d',
        'visual_review_state':'approved','model':'../bad.glb','review_views':{},
        'art_review':{k:'pending' for k in a2.CHECKS}}
    (tmp_path/'model_submission.json').write_text(json.dumps(spec))
    r=a2.review(tmp_path)
    assert not r['passed'] and not r['visual_identity_approved']
    assert any('Self-reported approval' in x for x in r['errors'])
def test_proxy_is_detected(tmp_path):
    j=json.dumps({'asset':{'version':'2.0','extras':{'production_ready':False}},
      'meshes':[{'primitives':[{}]}], 'materials':[{} for i in range(4)], 'textures':[{}]})
    raw=j.encode();raw+=b' '*((-len(raw))%4)
    p=tmp_path/'proxy.glb'
    p.write_bytes(b'glTF'+struct.pack('<I',2)+struct.pack('<I',20+len(raw))+
        struct.pack('<II',len(raw),0x4e4f534a)+raw)
    assert a2.inspect_glb(p)['engineering_proxy']
def test_reference_and_angles_fixed():
    assert len(a2.VIEWS)==5 and len(a2.CHECKS)==12
    assert len(set(a2.REF.values()))==3
def test_path_escape_rejected(tmp_path):
    try:a2.resolve(tmp_path,'../albedo.glb')
    except ValueError:pass
    else:raise AssertionError('Unsafe model path accepted')
