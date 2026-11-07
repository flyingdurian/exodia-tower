"""Tests for technical sprite gates. Synthetic PNGs here are not art assets."""
import hashlib, json, struct, sys, zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'orchestrator'))
from tools.companion_art_gate import inspect_image, audit

CONTRACT={"fleet":[{"id":"kiko"}],"benchmark":{"sha256":"ab"*32}}


def png(path,w,h,colour=6):
    # Valid highly compressible transparent RGBA sprite, for automated format tests only.
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    sig=bytes.fromhex('89504e470d0a1a0a')
    row=b'\x00'+(b'\0'*(4 if colour==6 else 3))*w
    b=sig+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,colour,0,0,0))
    b+=chunk(b'IDAT',zlib.compress(row*h,9))+chunk(b'IEND',b'')
    path.write_bytes(b)


def manifest(**overrides):
    basic={"schema":"exodia.companion-master/v1","companion_id":"kiko",
           "approved_reference_sha256":"ab"*32,
           "source_method":"independently_authored",
           "visual_identity_review":"owner_approved","rig_status":"not_started",
           "assets":{"front_master":"front.png","face_master":"face.png"}}
    return dict(basic,**overrides)


def test_a0_accepts_valid_transparent_registered_masters(tmp_path):
    png(tmp_path/'front.png',1024,2048)
    png(tmp_path/'face.png',1024,1024)
    result=audit(manifest(),tmp_path,CONTRACT)
    assert result['passed'] and not result['production_rig_ready']
    assert result['assets']['front_master']['width']==1024
    assert result['assets']['face_master']['sha256']==hashlib.sha256((tmp_path/'face.png').read_bytes()).hexdigest()


def test_a0_rejects_unapproved_crop_and_small_rgb(tmp_path):
    png(tmp_path/'front.png',512,256,2)
    png(tmp_path/'face.png',512,512,2)
    result=audit(manifest(source_method='cropped_concept_poster',visual_identity_review='pending'),tmp_path,CONTRACT)
    assert not result['passed']
    assert 'source must be independently authored' in ' '.join(result['errors']).lower()
    assert any('transparency' in err for err in result['errors'])
    assert any('owner approval' in err for err in result['errors'])


def test_a0_rejects_path_traversal_and_forged_rig_status(tmp_path):
    png(tmp_path/'face.png',1024,1024)
    data=manifest(rig_status='production_ready',assets={'front_master':'../elsewhere.png','face_master':'face.png'})
    r=audit(data,tmp_path,CONTRACT)
    assert not r['passed']
    assert any('unsafe path' in err for err in r['errors'])
    assert any('No rig proof' in err for err in r['errors'])


def test_broken_asset_is_rejected(tmp_path):
    (tmp_path/'bad.png').write_bytes(b'not a png')
    try:
        inspect_image(tmp_path/'bad.png')
    except ValueError as exc:
        assert 'PNG/WebP' in str(exc)
    else: assert False


def test_png_hash_content_readable(tmp_path):
    png(tmp_path/'front.png',1024,2048)
    assert inspect_image(tmp_path/'front.png')['alpha'] is True