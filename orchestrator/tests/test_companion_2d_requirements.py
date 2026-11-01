"""Assert that the 2D pivot does not silently erode the owner-approved contract."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def test_2d_scope_and_release_gate():
    c=json.loads((ROOT/'docs/companion_2d_requirements.json').read_text())
    prior=json.loads((ROOT/'docs/companion_art_contract.json').read_text())
    assert c['schema']=='exodia.companion-2d/v1'
    assert c['identity']['agent_id']=='kiko'
    assert c['workstation']['required_emotions']==[x['id'] for x in prior['emotions']]
    assert c['actions']['ids']==[x['id'] for x in prior['actions']]
    assert len(c['workstation']['required_emotions'])==20
    assert len(c['actions']['ids'])==13
    assert c['quality_acceptance']['no_fleet_rollout_until_Albedo_accepted']
    assert not c['review_snapshot']['release_ready']
    assert c['review_snapshot']['independent_emotion_masters_approved']==0
    assert c['review_snapshot']['individual_action_masters_approved']==0

def test_2d_deck_contract_requires_real_frames():
    c=json.loads((ROOT/'docs/companion_2d_requirements.json').read_text())
    d=c['deck']
    assert d['base_frame_px']==[128,196]
    assert set(d['directional_stills'])=={'front','left','right','back'}
    assert next(a for a in d['required_frame_sets'] if a['action']=='walk')['frames_per_direction']>=8
    assert c['quality_acceptance']['past_low_quality_cutout_wobble_rejected']
    assert c['quality_acceptance']['owner_signoff_required']
    assert c['workstation']['large_circle_from_low_resolution_atlas']=='forbidden'
