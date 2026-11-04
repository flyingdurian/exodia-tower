"""Owner approved one exact Angered *design*, not the production master.

Regression locks:
  - 1122x1402 source is below native specification
  - owner approval is SHA-bound and cannot transfer to a future re-render
  - four production replacement states remain pending
  - the other 29 original+review hashes are protected
  - no owner-approved or release.enabled fields are silently promoted
"""
from __future__ import annotations
from pathlib import Path
import json
from hashlib import sha256
from app.config import Settings

ROOT=Path(__file__).resolve().parents[2]
PATH=ROOT/'assets'/'review'/'albedo_core5'/'gate4_angered_owner_visual_design_approval_2026-11-04.json'
LOCK=ROOT/'assets'/'review'/'albedo_core5'/'gate4_four_state_correction_lock.json'
REG=ROOT/'orchestrator'/'frontend'/'companions'/'production'/'kiko'/'portrait_registry.json'
INDEX=ROOT/'orchestrator'/'app_data'/'albedo_33_review'/'review_index.json'
SHA='139d622282f097c618c60ded0d3654ebffd2b18f3360fbdbc2eb8863eaf1ae18'


def test_owner_visually_approved_exact_lowres_angered_only():
    approval=json.loads(PATH.read_text())
    assert approval['schema']=='exodia.gate4-angered-owner-visual-design-approval/v1'
    assert approval['state']=='angered'
    assert approval['original_sha256']==SHA
    assert approval['original_source_dimensions']==[1122,1402]
    assert approval['owner_visual_design_approved'] is True
    assert approval['approval_scope']=='VISUAL_DESIGN_ONLY_EXACT_IMAGE_SHA'
    assert approval['native_source_eligible'] is False
    assert approval['production_approved'] is False
    assert approval['production_release_enabled'] is False
    assert approval['rerender_new_hash_requires_new_visual_evaluation'] is True
    assert approval['approval_not_transferrable_to_other_files'] is True
    assert len(approval['generation_provenance']['independent_generation_operation_id'])>8


def test_correction_lock_preserves_29_and_native_angered_pending():
    approval=json.loads(PATH.read_text())
    lock=json.loads(LOCK.read_text())
    registry=json.loads(REG.read_text())
    review=json.loads(INDEX.read_text())
    assert lock['correction_completed']==0
    assert len(lock['frozen_review_hashes'])==33
    assert lock['protected_count']==29
    assert lock['owner_final_production_approval'] is False
    assert registry['release']['enabled'] is False
    assert all(state['status']=='pending_production_art'
               for state in registry['states'].values())
    assert set(lock['target_states'])=={
        'angered','awaiting_command','neutral','tantrum'}
    assert len([r for r in lock['frozen_review_hashes'].values()
                if r['development_review_status']=='OWNER_ACCEPTED_FOR_CONTINUED_DEVELOPMENT'])==29
    assert len(review['states'])==33
    for key,orig in lock['frozen_review_hashes'].items():
        actual=review['states'][key]
        assert actual['source_sha256']==orig['original_sha256']
        assert actual['image_sha256']==orig['review_sha256']
        if key=='angered':
            assert orig['original_sha256'] != SHA
        assert actual['owner_approved'] is False
        assert actual['production_status']=='pending_production_art'
    brief=lock['correction_briefs']['angered']
    cue=brief['owner_approved_reference_design']
    assert cue['sha256']==approval['original_sha256']==SHA
    assert cue['canvas']==[1122,1402]
    assert cue['native_production_eligible'] is False
    assert cue['future_rerender_inherits_owner_visual_approval'] is False
    assert brief['status']=='PENDING_NEW_STANDALONE_ARTWORK'
    assert brief['new_original_sha256'] is None
    assert brief['new_review_sha256'] is None


def test_live_fastapi_manifest_exposes_lowres_owner_visual_cue_only():
    from app.companions.state33_review_assets import manifest
    data=manifest(Settings().root)
    assert data['count']==33
    assert data['artwork_available_count']==33
    assert data['production_release_enabled'] is False
    assert data['owner_production_approved_count']==0
    anger=data['states']['angered']
    cue=anger['owner_approved_lowres_design_reference']
    assert cue['sha256']==SHA
    assert cue['source_dimensions']==[1122,1402]
    assert cue['visual_design_approved_exact_sha'] is True
    assert cue['native_production_eligible'] is False
    assert cue['future_rerender_needs_owner_review'] is True
    assert cue['preview_asset_available_in_repo'] is False
    assert anger['sha256'] != SHA  # Existing 1536x1920 review image remains intact.
    assert anger['owner_approved'] is False
    assert anger['owner_final_visual_approved'] is False
    assert anger['production_status']=='pending_production_art'
    assert anger['owner_development_status']=='CORRECTION_REQUIRED'
    assert len([item for item in data['states'].values()
                if item['owner_development_status']=='OWNER_ACCEPTED_FOR_CONTINUED_DEVELOPMENT'])==29
