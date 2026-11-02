"""Ensures the locked profile and signal matrix remain explicit without false release."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/'orchestrator/frontend/companions/production/kiko/portrait_registry.json'
QUEUE=ROOT/'assets/staging_intake/albedo_static_33_batch.json'

def test_locked_profile_and_pending_pointing():
    r=json.loads(REG.read_text())
    profile=r['layout_profile']
    assert profile['canvas_px']==[1536,1920]
    assert profile['eye_line_y_px']==633.6
    assert profile['head_width_px']==614.4
    assert profile['benchmark_states']==['working','explaining','monitoring']
    assert r['states']['pointing']['master_regeneration_required'] is True
    assert r['release']['enabled'] is False

def test_all_33_states_are_explicitly_queued():
    r=json.loads(REG.read_text());q=json.loads(QUEUE.read_text())
    assert len(q['states'])==33
    assert {x['state_key'] for x in q['states']}==set(r['states'])
    assert q['auto_owner_approval'] is False
    assert all(x['signal_overlay']==r['states'][x['state_key']]['signal_overlay'] for x in q['states'])
