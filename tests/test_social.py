from backend.social.models import ContentJob, Platform, Stage
from backend.social.planner import create_brief
import pytest

def test_brief_is_draft_not_posted():
    result=create_brief('My first series',{Platform.YOUTUBE,Platform.TIKTOK})
    assert result['stage']=='idea'
    assert result['publication_status']=='not_published'
    assert result['review_required']

def test_no_skipping():
    job=ContentJob('Title',{Platform.YOUTUBE})
    with pytest.raises(ValueError):job.advance(Stage.PUBLISHED)
    job.advance(Stage.RESEARCH)
    assert job.stage==Stage.RESEARCH

def test_approval_gate():
    job=ContentJob('Title',{Platform.INSTAGRAM},stage=Stage.REVIEW)
    with pytest.raises(PermissionError):job.advance(Stage.APPROVED)
