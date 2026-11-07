"""Review page remains empty and cannot publish fake animations."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HTML=ROOT/'frontend'/'companions'/'review'/'portrait_motion_inspector.html'

def test_reviewer_rejects_storyboard_and_keeps_fixed_portrait():
    text=HTML.read_text(encoding='utf-8')
    for x in ('aspect-ratio:4/5','object-fit:contain','transform:none',
              'No storyboard images or upscaled cells','1536','1920',
              'if(image.naturalWidth!==1536||image.naturalHeight!==1920)'):
        assert x in text

def test_reviewer_starts_empty_and_cannot_publish():
    text=HTML.read_text(encoding='utf-8')
    assert '<button id="toggle" disabled>Play</button>' in text
    assert 'NO PRODUCTION ASSETS LOADED' in text
    assert 'reduced-motion: reduce' in text
    assert 'fetch(' not in text
