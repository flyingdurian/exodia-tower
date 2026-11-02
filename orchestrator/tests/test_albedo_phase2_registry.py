"""Review-only contract tests: no identity or animation approval is implied."""
import json,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def test_manifest_covers_every_state():
 m=json.loads((ROOT/'docs/albedo_portrait_phase2_registry.json').read_text())
 assert m['master']['width']==1536 and m['master']['height']==1920
 assert len(m['emotions'])==20 and len(set(m['emotions']))==20
 assert len(m['actions'])==13 and len(set(m['actions']))==13
 assert set(m['loops'])=={'idle','working','explaining'}
 assert m['accepted_native_portraits']==0 and m['accepted_native_loops']==0
 assert not m['release_ready']
def test_bad_import_refused(tmp_path):
 spec=importlib.util.spec_from_file_location('phase2',ROOT/'orchestrator/tools/import_albedo_phase2.py')
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 invalid=tmp_path/'bad.zip';invalid.write_bytes(b'not-zip')
 try:mod.inspect(invalid)
 except Exception:pass
 else:raise AssertionError('accepted invalid zip')
