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



# Explicitly approved postprocessing adapter: normalized 4:5 VISUAL masters only.
# This is not a proof of native detail, independent authorship, or image landmarks.
def _canonical_sha256(record: dict) -> str:
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def _soft_edge_pad(image: Image.Image, offset: tuple[int,int], size=(WIDTH,HEIGHT)) -> Image.Image:
    """Pad by extending nearest boundary colours and feathering the join, no crop."""
    x,y=offset
    w,h=image.size
    if x<0 or y<0 or x+w>size[0] or y+h>size[1]:
        raise ValueError('Cannot satisfy mapping without cropping; HALTED')
    out=Image.new('RGB',size)
    out.paste(image,(x,y))
    if y:
        out.paste(image.crop((0,0,w,1)).resize((w,y)),(x,0))
    bottom=size[1]-(y+h)
    if bottom:
        out.paste(image.crop((0,h-1,w,h)).resize((w,bottom)),(x,y+h))
    if x:
        out.paste(out.crop((x,0,x+1,size[1])).resize((x,size[1])),(0,0))
    right=size[0]-(x+w)
    if right:
        out.paste(out.crop((x+w-1,0,x+w,size[1])).resize((right,size[1])),(x+w,0))
    backdrop=out.filter(ImageFilter.GaussianBlur(65))
    from PIL import ImageDraw
    alpha=Image.new('L',size,0)
    ImageDraw.Draw(alpha).rectangle((x+18,y+18,x+w-18,y+h-18),fill=255)
    alpha=alpha.filter(ImageFilter.GaussianBlur(14))
    backdrop.paste(out,(0,0),alpha)
    return backdrop


def normalize_generated(source: Path, destination: Path, landmarks: dict, metadata_path: Path) -> dict:
    """High-quality 4:5 generator normalization with honest source provenance.

    Numeric eye/head PASS checks evaluate a transform of user/artist measurements,
    NOT automatic feature detection. The normalized image is for visual review
    and does not authorize animation sequences or production rollout.
    """
    with Image.open(source) as original:
        original.load()
        if original.format != 'PNG':
            raise ValueError('Generated source must be PNG')
        sw,sh=original.size
        im=ImageOps.exif_transpose(original).convert('RGB')
    if not (600<=sw<=WIDTH and 750<=sh<=HEIGHT):
        raise ValueError('Source dimensions outside normalization window')
    if abs(sw/sh-RATIO)>0.001:
        raise ValueError('Generator aspect deviates from 4:5; HALTED')
    if landmarks.get('method')!='manual_visual_estimate':
        raise ValueError('Landmark provenance must say manual_visual_estimate')
    for key in ('eye_midpoint_source_px','head_bounds_x_source_px'):
        value=landmarks.get(key)
        if not (isinstance(value,list) and len(value)==2 and all(type(z) in (int,float) for z in value)):
            raise ValueError('Missing source landmarks: '+key)
    ex,ey=landmarks['eye_midpoint_source_px']
    left,right=landmarks['head_bounds_x_source_px']
    if not (0<ex<sw and 0<ey<sh and 0<=left<right<=sw):
        raise ValueError('Landmark values outside original image')
    desired_eye_x,desired_eye_y=WIDTH*EYE_TARGET[0],HEIGHT*EYE_TARGET[1]
    desired_head=WIDTH*HEAD_WIDTH_TARGET
    ideal_scale=desired_head/(right-left)
    ow,oh=round(sw*ideal_scale),round(sh*ideal_scale)
    sx,sy=ow/sw,oh/sh
    x=round(desired_eye_x-ex*sx)
    y=round(desired_eye_y-ey*sy)
    if x<0 or y<0 or x+ow>WIDTH or y+oh>HEIGHT:
        raise ValueError('Cannot simultaneously satisfy anchors without cropping; HALTED')
    if abs(sx-sy)>0.001:
        raise ValueError('Anisotropic stretching forbidden')
    mapped_x,mapped_y=x+ex*sx,y+ey*sy
    mapped_head=(right-left)*sx
    if abs(mapped_x-desired_eye_x)>1.0 or abs(mapped_y-desired_eye_y)>1.0 or abs(mapped_head-desired_head)>1.0:
        raise ValueError('Mapped eye/head targets not within one pixel')
    content=im.resize((ow,oh),Image.Resampling.LANCZOS)
    final=_soft_edge_pad(content,(x,y))
    destination.parent.mkdir(parents=True,exist_ok=True)
    final.save(destination,format='PNG',optimize=True)
    registration={
        'source_landmarks':landmarks,'source_sha256':fingerprint(source),
        'output_sha256':fingerprint(destination),
        'interpolation':'Pillow Lanczos',
        'transform':{'scale_x':sx,'scale_y':sy,'offset_x':x,'offset_y':y},
        'mapped':{'eye_x_px':mapped_x,'eye_y_px':mapped_y,'head_width_px':mapped_head},
        'source_method':'upsampled_from_generated_4x5',
        'landmark_verified_from_pixels':False}
    meta={'standard':STANDARD_ID,'kind':'emotion','character_id':'kiko',
          'status':'candidate_pending_review','human_visual_review':'pending',
          'registration':{'eye_x':mapped_x/WIDTH,'eye_y':mapped_y/HEIGHT,
                          'head_width':mapped_head/WIDTH},
          'legacy_reframe':False,'provenance':'normalized_generated_4x5',
          'source_is_native_render':False,
          'registration_sha256':_canonical_sha256(registration)}
    checked=validate_master(destination,meta)
    passed=not checked['errors']
    report={'rule':'EXODIA_STRICT_INSTRUCTION_COMPLIANCE',
            'scope':'normalized_visual_master_only',
            'status':'PASSED' if passed else 'FAILED',
            'source_px':[sw,sh],'output_px':[WIDTH,HEIGHT],
            'original_sha256':registration['source_sha256'],
            'normalized_sha256':registration['output_sha256'],
            'requested_eye_line_px':desired_eye_y,'mapped_eye_line_px':mapped_y,
            'requested_head_width_px':desired_head,'mapped_head_width_px':mapped_head,
            'registration_sha256':meta['registration_sha256'],
            'registration_verified_from_image':False,
            'source_native_resolution':False,
            'visual_approval_pending':True,
            'sequence_generation_authorized':False,
            'technical_check':checked,
            'transform':registration['transform'],
            'errors':checked['errors'],
            'note':'Only output dimensions and mapping of provisional manually annotated landmarks pass. Resampling adds no native detail or proof of actual eye/head locations.'}
    metadata_path.parent.mkdir(parents=True,exist_ok=True)
    metadata_path.write_text(json.dumps({'metadata':meta,'registration':registration,'telemetry':report},indent=2)+'\n',encoding='utf-8')
    return report

def main():
    parser = argparse.ArgumentParser(description='Exodia fixed portrait canvas gate')
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('check')
    check.add_argument('image', type=Path)
    check.add_argument('metadata', type=Path)
    legacy = sub.add_parser('reframe-review')
    legacy.add_argument('image', type=Path)
    legacy.add_argument('output', type=Path)
    normal=sub.add_parser('normalize-generated')
    normal.add_argument('source_png', type=Path)
    normal.add_argument('output_png', type=Path)
    normal.add_argument('source_landmarks', type=Path)
    normal.add_argument('metadata_output', type=Path)
    args = parser.parse_args()
    if args.command == 'normalize-generated':
        report=normalize_generated(args.source_png,args.output_png,
            json.loads(args.source_landmarks.read_text(encoding='utf-8')),
            args.metadata_output)
        print(json.dumps(report,indent=2))
        if report['status']!='PASSED':
            raise SystemExit(1)
        return
    if args.command == 'check':
        report = validate_master(args.image, json.loads(args.metadata.read_text(encoding='utf8')))
    else:
        report = reframe_legacy_review(args.image, args.output)
    print(json.dumps(report, indent=2))
    if args.command == 'check' and report['errors']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()