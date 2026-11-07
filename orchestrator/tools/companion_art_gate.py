"""Fail-closed art asset acceptance gate for Exodia's companion production.

This checks file integrity, dimensions, transparency, paths, hash and human
sign-off metadata. It cannot judge whether a face matches approved artwork;
that comparison remains a mandatory human approval step.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

PNG_SIG = b'\x89PNG\r\n\x1a\n'
EMOTIONS = ('happy','excited','laugh','smile','thinking','curious','surprised',
            'confused','determined','serious','sad','disappointed','pouting',
            'angry','hurt','bored','sleepy','dizzy','pain','cheerful_wink')


def inspect_image(path: Path) -> dict:
    """Inspect PNG and common WebP headers without introducing a PIL dependency."""
    data = path.read_bytes()
    if data.startswith(PNG_SIG) and len(data) >= 33:
        if data[12:16] != b'IHDR':
            raise ValueError('PNG has no valid IHDR')
        width, height = struct.unpack('>II', data[16:24])
        bitdepth, colour = data[24], data[25]
        if not (width and height and bitdepth == 8 and b'IEND' in data[-32:]):
            raise ValueError('Invalid/incomplete PNG')
        alpha = colour in (4, 6) or b'tRNS' in data
        kind = 'png'
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP' and len(data) >= 30:
        chunk = data[12:16]
        if chunk == b'VP8X':
            alpha = bool(data[20] & 0x10)
            width = int.from_bytes(data[24:27], 'little') + 1
            height = int.from_bytes(data[27:30], 'little') + 1
        elif chunk == b'VP8 ' and len(data) >= 30:
            alpha = False
            width, height = struct.unpack('<HH', data[26:30]); width &= 0x3fff; height &= 0x3fff
        elif chunk == b'VP8L' and len(data) >= 25 and data[20] == 0x2f:
            v = int.from_bytes(data[21:25], 'little')
            width = (v & 0x3fff) + 1
            height = ((v >> 14) & 0x3fff) + 1
            alpha = bool((v >> 28) & 1)
        else:
            raise ValueError('Unsupported WebP header')
        kind = 'webp'
    else:
        raise ValueError('Only actual PNG/WebP files are accepted')
    if width > 16384 or height > 16384 or width <= 0 or height <= 0:
        raise ValueError('Unreasonable image dimensions')
    return {'width':width,'height':height,'alpha':alpha,'format':kind,
            'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}


def audit(manifest: dict, directory: Path, contract: dict) -> dict:
    """Perform A0 technical checks; never imply automatic visual approval."""
    directory = directory.resolve()
    errors = []
    results = {}
    agents = {a['id'] for a in contract['fleet']}
    agent = manifest.get('companion_id')
    if agent not in agents:
        errors.append('Unknown companion ID')
    if manifest.get('schema') != 'exodia.companion-master/v1':
        errors.append('Unknown asset-manifest schema')
    approved_hash = contract['benchmark']['sha256']
    if manifest.get('approved_reference_sha256') != approved_hash:
        errors.append('Wrong or missing benchmark identity fingerprint')
    if manifest.get('source_method') != 'independently_authored':
        errors.append('Source must be independently authored, not a cropped concept poster')
    assets = manifest.get('assets',{})
    for key,min_height in [('front_master',2048),('face_master',1024)]:
        relative = assets.get(key)
        if not isinstance(relative,str) or not relative:
            errors.append(f'{key}: file not declared')
            continue
        full_path = (directory / relative).resolve()
        if not full_path.is_relative_to(directory) or full_path.suffix.lower() not in ('.png','.webp'):
            errors.append(f'{key}: unsafe path or extension')
            continue
        if not full_path.is_file():
            errors.append(f'{key}: file missing')
            continue
        try:
            info = inspect_image(full_path)
            results[key] = info
            if info['height'] < min_height:
                errors.append(f'{key}: requires at least {min_height}px height')
            if not info['alpha']:
                errors.append(f'{key}: needs transparency for production sprite registration')
            if info['width'] < 512:
                errors.append(f'{key}: too narrow for high-definition production')
        except (OSError, ValueError) as exc:
            errors.append(f'{key}: {exc}')
    if manifest.get('visual_identity_review') != 'owner_approved':
        errors.append('Visual identity requires explicit owner approval')
    if manifest.get('rig_status') == 'production_ready' and not manifest.get('rig_proof'):
        errors.append('No rig proof; static images cannot certify articulated motion')
    return {'companion_id':agent,'gate':'A0','passed':not errors,
            'production_rig_ready':False,'assets':results,'errors':errors,
            'note':'Technical checks do not establish visual likeness or working animation.'}


def main() -> int:
    parser=argparse.ArgumentParser(description='Exodia companion master asset gate')
    parser.add_argument('asset_directory',type=Path)
    parser.add_argument('--contract',type=Path,default=Path(__file__).resolve().parents[2]/'docs'/'companion_art_contract.json')
    args=parser.parse_args()
    directory=args.asset_directory.resolve()
    manifest=json.loads((directory/'asset_manifest.json').read_text(encoding='utf8'))
    contract=json.loads(args.contract.read_text(encoding='utf8'))
    result=audit(manifest,directory,contract)
    print(json.dumps(result,indent=2))
    return 0 if result['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())