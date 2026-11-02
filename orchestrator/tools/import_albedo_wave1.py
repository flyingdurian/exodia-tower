"""Safely import user-reviewed Albedo HD 2D candidates into a PREPRODUCTION path."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile

SCHEMA = 'exodia.albedo-hd-2d-wave/v1'
STATES = ('happy', 'thinking', 'serious', 'typing_working')
DIRECTIONS = ('front', 'back', 'left', 'right')
PNG_SIG = bytes.fromhex('89504e470d0a1a0a')
REVIEW_PATH = Path('frontend/companions/review/kiko_wave1')


class AssetImportError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_name(name: str) -> bool:
    parts = PurePosixPath(name).parts
    return bool(parts) and not name.startswith('/') and '\\' not in name and '..' not in parts


def validated_sources(archive_path: Path) -> dict[str, bytes]:
    """Whitelist only required media. Never extract arbitrary paths from a ZIP."""
    with zipfile.ZipFile(archive_path) as archive:
        entries = [info for info in archive.infolist() if not info.is_dir()]
        names = [info.filename for info in entries]
        if len(set(names)) != len(names) or any(not safe_name(n) for n in names):
            raise AssetImportError('Duplicate or unsafe archive path')
        if any(info.file_size > 25_000_000 or
               ((info.external_attr >> 16) & 0o170000) == 0o120000 for info in entries):
            raise AssetImportError('Oversize or symlink archive member')
        if sum(info.file_size for info in entries) > 100_000_000:
            raise AssetImportError('Archive exceeds safe size limit')
        if 'manifest.json' not in names:
            raise AssetImportError('Missing manifest')
        spec = json.loads(archive.read('manifest.json'))
        if spec.get('schema') != SCHEMA or spec.get('agent_id') != 'kiko':
            raise AssetImportError('Unexpected character or format')
        if spec.get('stage') != 'art_review_only' or spec.get('owner_acceptance', {}).get('fleet_rollout_allowed') is not False:
            raise AssetImportError('Unreviewed art cannot authorize release')
        if set(spec.get('artwork', {})) != set(STATES):
            raise AssetImportError('Missing independently authored images')

        allowed = {'manifest.json', 'albedo_hd_wave1_review.html',
                   'source_png/approved_full_body.png'}
        for state in STATES:
            info = spec['artwork'][state]
            original = f'source_png/{state}.png'
            display = f'assets/hd/{state}.webp'
            if info.get('source') != original or info.get('display') != display:
                raise AssetImportError('Unexpected source path')
            if original not in names or display not in names:
                raise AssetImportError('Source or display art missing')
            raw, webp = archive.read(original), archive.read(display)
            if len(raw) < 30 or not raw.startswith(PNG_SIG):
                raise AssetImportError('Invalid source PNG')
            if not (webp[:4] == b'RIFF' and webp[8:12] == b'WEBP'):
                raise AssetImportError('Invalid WebP')
            if info.get('sha256') != sha256(raw) or info.get('display_sha256') != sha256(webp):
                raise AssetImportError(f'{state}: hash mismatch')
            size = (int.from_bytes(raw[16:20],'big'), int.from_bytes(raw[20:24],'big'))
            if size != (info.get('width'),info.get('height')) or min(size) < 1024:
                raise AssetImportError(f'{state}: HD dimensions insufficient')
            allowed.add(display)
        for direction in DIRECTIONS:
            path = f'assets/deck/{direction}.png'
            if path not in names or not archive.read(path).startswith(PNG_SIG):
                raise AssetImportError('Missing deck directional still')
            allowed.add(path)
        if not allowed.issubset(names):
            raise AssetImportError('Missing review document or full-body reference')
        return {name:archive.read(name) for name in sorted(allowed)}


def import_wave(archive_path: Path, app_root: Path, replace=False) -> Path:
    art = validated_sources(archive_path)
    target = (app_root / REVIEW_PATH).resolve()
    if target.exists() and not replace:
        raise AssetImportError('Review art already installed; use --replace explicitly')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='albedo-hd-', dir=target.parent) as directory:
        staging = Path(directory)
        for name, data in art.items():
            path = staging / name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(staging),str(target))
    return target


def main():
    parser = argparse.ArgumentParser(description='Install Albedo HD 2D for isolated review')
    parser.add_argument('zipfile',type=Path)
    parser.add_argument('--app-root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--replace',action='store_true')
    args = parser.parse_args()
    dest = import_wave(args.zipfile,args.app_root,replace=args.replace)
    print('Review-only art installed:',dest)
    print('Open /assets/companions/review/kiko_wave1/albedo_hd_wave1_review.html')


if __name__ == '__main__':
    main()
