"""Portable fail-closed tests; fixture images here are NOT production art."""
from pathlib import Path
import importlib.util
import json
import struct
import zlib
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('albedo_hd_import', ROOT/'tools'/'import_albedo_wave1.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def mock_png():
    def chunk(kind, data):
        return struct.pack('>I',len(data)) + kind+data + struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    row = b'\0'+bytes(1024*4)
    return (tool.PNG_SIG + chunk(b'IHDR',struct.pack('>IIBBBBB',1024,1024,8,6,0,0,0))
            + chunk(b'IDAT',zlib.compress(row*1024)) + chunk(b'IEND',b''))


def archive(tmp_path, mutate=None):
    raw = mock_png()
    riff = b'RIFF' + struct.pack('<I',16) + b'WEBPVP8X' + struct.pack('<I',4) + bytes(4)
    items = {'albedo_hd_wave1_review.html':b'<html>review</html>',
             'source_png/approved_full_body.png':raw}
    art = {}
    for state in tool.STATES:
        src, dst = f'source_png/{state}.png',f'assets/hd/{state}.webp'
        items[src]=raw; items[dst]=riff
        art[state]={'source':src,'display':dst,'width':1024,'height':1024,
                    'sha256':tool.sha256(raw),'display_sha256':tool.sha256(riff)}
    for d in tool.DIRECTIONS:
        items[f'assets/deck/{d}.png']=raw
    manifest = {'schema':tool.SCHEMA,'agent_id':'kiko','stage':'art_review_only',
                'owner_acceptance':{'fleet_rollout_allowed':False},'artwork':art}
    if mutate:mutate(manifest)
    items['manifest.json']=json.dumps(manifest).encode()
    target=tmp_path/'art.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for name, content in items.items():z.writestr(name,content)
    return target


def test_only_review_path_is_created(tmp_path):
    target=tool.import_wave(archive(tmp_path),tmp_path/'app')
    assert target.name=='kiko_wave1'
    assert (target/'assets/hd/happy.webp').is_file()
    assert not (tmp_path/'app/frontend/companions/production').exists()


def test_refuses_unrequested_overwrite(tmp_path):
    file=archive(tmp_path)
    tool.import_wave(file,tmp_path/'app')
    with pytest.raises(tool.AssetImportError,match='already installed'):
        tool.import_wave(file,tmp_path/'app')


def test_corrupted_hash_is_rejected(tmp_path):
    file=archive(tmp_path, lambda m:m['artwork']['happy'].update(sha256='a'*64))
    with pytest.raises(tool.AssetImportError,match='hash mismatch'):
        tool.validated_sources(file)


def test_false_release_flag_is_rejected(tmp_path):
    file=archive(tmp_path,lambda m:m['owner_acceptance'].update(fleet_rollout_allowed=True))
    with pytest.raises(tool.AssetImportError,match='cannot authorize'):
        tool.validated_sources(file)


def test_malicious_paths_are_rejected():
    for name in ('../x','/absolute','assets\\windows'):
        assert not tool.safe_name(name)
    assert tool.safe_name('assets/hd/happy.webp')
