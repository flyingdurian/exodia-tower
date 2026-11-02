"""Exodia Tower companion portrait standard v1.

Validates a true art master against a fixed 4:5 physical canvas and
checks author-reported registration. No automatic identity approval.

The optional `reframe-review` mode only creates REVIEW previews from legacy
incompatible imagery. It never upgrades their quality or qualifies them
as production art.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps

STANDARD_ID = 'exodia.portrait-4x5/v1'
WIDTH, HEIGHT = 1536, 1920
RATIO = WIDTH / HEIGHT
EYE_TARGET = (0.50, 0.33)
EYE_TOL = (0.04, 0.045)
HEAD_WIDTH_TARGET = 0.40
HEAD_WIDTH_TOL = 0.055
SAFE_MARGIN = 0.055
FRAME_TYPES = {'emotion', 'action', 'idle_loop', 'action_loop'}


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_master(path: Path, meta: dict) -> dict:
    errors = []
    try:
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            size = im.size
            typ = im.format
    except (OSError, ValueError) as exc:
        return {'path': str(path), 'status': 'rejected', 'errors': [f'Invalid image: {exc}']}
    if size != (WIDTH, HEIGHT):
        errors.append(f'Expected {WIDTH}x{HEIGHT}, got {size[0]}x{size[1]}; no resize/stretch waiver')
    if typ not in {'PNG', 'WEBP'}:
        errors.append('PNG or WebP required')
    if meta.get('standard') != STANDARD_ID:
        errors.append('Missing canonical portrait standard')
    if meta.get('kind') not in FRAME_TYPES:
        errors.append('Unknown emotion/action/loop category')
    if meta.get('character_id') not in {'kiko'}:
        errors.append('Wrong character identity')
    if meta.get('status') not in {'candidate_pending_review', 'owner_approved'}:
        errors.append('Art status cannot be inferred from presence of a file')
    anchors = meta.get('registration') or {}
    for key in ('eye_x', 'eye_y', 'head_width'):
        value = anchors.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 < value < 1:
            errors.append(f'Required normalized registration: {key}')
    if not any(err.startswith('Required normalized') for err in errors):
        if abs(anchors['eye_x'] - EYE_TARGET[0]) > EYE_TOL[0]:
            errors.append('Horizontal eye anchor inconsistent across portraits')
        if abs(anchors['eye_y'] - EYE_TARGET[1]) > EYE_TOL[1]:
            errors.append('Vertical eye line inconsistent across portraits')
        if abs(anchors['head_width'] - HEAD_WIDTH_TARGET) > HEAD_WIDTH_TOL:
            errors.append('Character/head scale inconsistent across portraits')
    if meta.get('human_visual_review') != 'completed' and meta.get('status') == 'owner_approved':
        errors.append('Cannot assert owner approval without completed visual review')
    if meta.get('legacy_reframe'):
        errors.append('Legacy review reframing is never a production master')
    return {
        'path': str(path), 'size': list(size), 'sha256': fingerprint(path),
        'status': 'format_and_registration_passed_pending_visual_review' if not errors else 'rejected',
        'production_ready': False,
        'errors': errors,
        'warning': 'Registration fields are artist annotations, not automated face detection or identity validation.'
    }


def validate_loop(frame_paths: list[Path], registrations: list[dict], kind='idle_loop') -> dict:
    errors = []
    if len(frame_paths) < 4:
        errors.append('At least four independently painted frames required')
    if len(frame_paths) != len(registrations):
        errors.append('One registration record required per frame')
    checks = [validate_master(p, {'standard': STANDARD_ID, 'kind': kind,
                                  'character_id': 'kiko', 'status': 'candidate_pending_review',
                                  'registration': a})
              for p, a in zip(frame_paths, registrations)]
    for i, result in enumerate(checks):
        errors.extend(f'frame {i}: {err}' for err in result['errors'])
    if len(frame_paths) == len(registrations) and checks and all(not r['errors'] for r in checks):
        for axis, tol in (('eye_x', 0.015), ('eye_y', 0.018), ('head_width', 0.018)):
            vals = [a[axis] for a in registrations]
            if max(vals) - min(vals) > tol:
                errors.append(f'Loop registration jitter too high for {axis}')
        unique_hashes = {result['sha256'] for result in checks}
        if len(unique_hashes) < min(4, len(checks)):
            errors.append('Duplicate frames: no independently authored loop evidence')
    return {'frames': len(frame_paths), 'status': 'technical_pass_pending_visual_motion_review' if not errors else 'rejected',
            'production_ready': False, 'errors': errors}


def reframe_legacy_review(source: Path, destination: Path) -> dict:
    """Reframe on fixed canvas with NO crop or stretch. Quarantine as legacy.

    Aesthetic character-scale matching is impossible for differing compositions;
    the output is strictly a review/prototype adaptation, not production art.
    """
    with Image.open(source) as im:
        im = ImageOps.exif_transpose(im).convert('RGB')
        original = im.size
        # Background generated separately from actual portrait pixels; never
        # misrepresent this as transparent/source-quality reconstruction.
        bg = Image.new('RGB', (WIDTH, HEIGHT), '#141032')
        soft = ImageOps.fit(im, (WIDTH, HEIGHT), method=Image.Resampling.BICUBIC)
        bg = Image.blend(bg, soft.filter(ImageFilter.GaussianBlur(95)), 0.18)
        # The artwork is only contained, never warped or cropped.
        allowed = (int(WIDTH * .96), int(HEIGHT * .96))
        art = ImageOps.contain(im, allowed, Image.Resampling.LANCZOS)
        x, y = (WIDTH - art.width) // 2, (HEIGHT - art.height) // 2
        bg.paste(art, (x, y))
        destination.parent.mkdir(parents=True, exist_ok=True)
        bg.save(destination, format='PNG', optimize=True)
    return {
        'source': str(source), 'output': str(destination), 'original_dimensions': list(original),
        'output_dimensions': [WIDTH, HEIGHT], 'portrait_content_box': [x, y, art.width, art.height],
        'scaling': 'uniform contain; aspect preserved; no crop',
        'native_scale_consistent': False,
        'status': 'legacy_review_only_must_regenerate_for_production',
        'warning': 'Character scale and eye-line registration NOT proven by canvas normalization.'
    }


def main():
    parser = argparse.ArgumentParser(description='Exodia fixed portrait canvas gate')
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('check')
    check.add_argument('image', type=Path)
    check.add_argument('metadata', type=Path)
    legacy = sub.add_parser('reframe-review')
    legacy.add_argument('image', type=Path)
    legacy.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.command == 'check':
        report = validate_master(args.image, json.loads(args.metadata.read_text(encoding='utf8')))
    else:
        report = reframe_legacy_review(args.image, args.output)
    print(json.dumps(report, indent=2))
    if args.command == 'check' and report['errors']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()