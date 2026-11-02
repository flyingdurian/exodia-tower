"""Exodia Tower: grid-board extractor with strict production anti-upscale gate.

Board cells are review references, NOT independently authored production masters.
Never supply made-up eye/head coordinates, approvals, or SHA integrity records.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

SIZE = (1536, 1920)
EXPRESSIONS = ("neutral happy joyful excited gentle smiling_closed laughing amused confident serious focused thinking curious surprised concerned worried sad disappointed angered blushing").split()
ACTIONS = ("idle working monitoring pointing explaining celebrating defeat stretching sleeping waking_up tantrum thinking_deeper awaiting_command").split()
EXPR_SHEET = "albedo_s_neon_portrait_review_board.png"
ACTION_A_SHEET = "albedo_s_futuristic_portrait_production_board.png"
ACTION_B_SHEET = "albedo_s_neon_expression_board.png"  # Revised B (Defeat/Waking etc.)
EXPECTED_SHEETS = {EXPR_SHEET: (1122, 1402), ACTION_A_SHEET: (1491, 1055), ACTION_B_SHEET: (1448, 1086)}
# Exact labels on the approved boards, not inferred matches to a different matrix.
EXPR_LABELS = ("happy excited laugh smile thinking curious surprised confused determined serious sad disappointed pouting angry hurt bored sleepy dizzy pain cheerful_wink").split()
ACTION_A_LABELS = ("idle working monitoring pointing explaining celebrating").split()
ACTION_B_LABELS = ("defeat stretching sleeping waking_up tantrum").split()
# Only label-equivalent aliases. 'smile' -> 'smiling_closed' is NOT automatic.
ALIASES = {'laugh': 'laughing', 'angry': 'angered'}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def boxes():
    """Return literal hand-checked panel coordinates in original board pixels.

    Each bbox intentionally excludes the panel label/footer; this is a review
    crop. A future changed board size fails instead of silently cropping elsewhere.
    """
    expr_x = [(17, 226), (235, 441), (450, 654), (664, 867), (879, 1085)]
    expr_y = [(135, 385), (430, 670), (716, 954), (1006, 1249)]
    records = []
    for index, label in enumerate(EXPR_LABELS):
        row, col = divmod(index, 5)
        records.append({'sheet': EXPR_SHEET, 'source_label': label,
                        'category': 'expression', 'rect': [expr_x[col][0], expr_y[row][0], expr_x[col][1], expr_y[row][1]],
                        'canonical_candidate': ALIASES.get(label, label) if ALIASES.get(label, label) in EXPRESSIONS else None})
    # Set A: first four idle-loop poses are one *state*, not four portrait states.
    records.append({'sheet': ACTION_A_SHEET, 'source_label': 'idle', 'category': 'action',
                    'rect': [45, 117, 372, 410], 'canonical_candidate': 'idle',
                    'note': 'First of four concept idle frames; motion cells never qualify as native stills'})
    ax = [(16, 300), (314, 592), (606, 857), (870, 1137), (1149, 1433)]
    for label, (x0, x1) in zip(ACTION_A_LABELS[1:], ax):
        records.append({'sheet': ACTION_A_SHEET, 'source_label': label, 'category': 'action',
                        'rect': [x0, 510, x1, 968], 'canonical_candidate': label})
    bx_top = [(70, 472), (498, 902), (928, 1335)]
    for label, (x0, x1) in zip(ACTION_B_LABELS[:3], bx_top):
        records.append({'sheet': ACTION_B_SHEET, 'source_label': label, 'category': 'action',
                        'rect': [x0, 76, x1, 464], 'canonical_candidate': label})
    bx_bottom = [(128, 695), (714, 1280)]
    for label, (x0, x1) in zip(ACTION_B_LABELS[3:], bx_bottom):
        records.append({'sheet': ACTION_B_SHEET, 'source_label': label, 'category': 'action',
                        'rect': [x0, 526, x1, 909], 'canonical_candidate': label})
    assert len(records) == 31
    return records


def inspect(source_dir: Path, records: list[dict] | None = None) -> dict:
    records = records if records is not None else boxes()
    sources = {}
    problems = []
    for filename, expected in EXPECTED_SHEETS.items():
        p = source_dir / filename
        if not p.is_file():
            problems.append(f'missing_source:{filename}')
            continue
        try:
            with Image.open(p) as im:
                if im.size != expected:
                    problems.append(f'wrong_board_dimensions:{filename}:{im.size}!= {expected}')
                im.verify()
            sources[filename] = {'sha256': sha256(p), 'size': list(expected)}
        except Exception as exc:
            problems.append(f'invalid_board:{filename}:{exc}')
    for record in records:
        filename, bbox = record['sheet'], record['rect']
        expected = EXPECTED_SHEETS.get(filename)
        if expected is None or filename not in sources:
            problems.append(f'unsupported_board:{filename}')
            continue
        x0, y0, x1, y1 = bbox
        if not (0 <= x0 < x1 <= expected[0] and 0 <= y0 < y1 <= expected[1]):
            problems.append(f'invalid_bbox:{record["source_label"]}')
    matched = {v['canonical_candidate'] for v in records if v.get('canonical_candidate')}
    missing = sorted(set(EXPRESSIONS + ACTIONS) - matched)
    undersized = [
        {'label': r['source_label'], 'canonical_candidate': r.get('canonical_candidate'),
         'source_size': [r['rect'][2]-r['rect'][0], r['rect'][3]-r['rect'][1]]}
        for r in records if (r['rect'][2]-r['rect'][0], r['rect'][3]-r['rect'][1]) != SIZE
    ]
    return {'schema': 'exodia.board-slice-preflight/v1', 'board_sources': sources,
            'boards_found': len(sources), 'board_cells_found': len(records),
            'canonical_states': len(EXPRESSIONS + ACTIONS), 'matched_label_candidates': len(matched),
            'missing_canonical_states': missing, 'undersized_or_non_native_cells': undersized,
            'errors': problems, 'source_anchors_measured': False,
            'owner_approval_carries_to_individual_crops': False,
            'production_eligible': not problems and not missing and not undersized,
            'note': 'Concept boards do not prove independent native detail or verified facial registration.'}


def create_review(source_dir: Path, out: Path, report: dict, records: list[dict] | None = None) -> dict:
    records = records if records is not None else boxes()
    if report['errors']:
        raise ValueError('board_preflight_failed:' + ';'.join(report['errors']))
    out.mkdir(parents=True, exist_ok=True)
    result = []
    for r in records:
        src = source_dir / r['sheet']
        dest = out / r['category'] / (r['source_label'] + '.png')
        dest.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as image:
            image.crop(tuple(r['rect'])).save(dest, format='PNG')
        with Image.open(dest) as crop: dimensions = list(crop.size)
        result.append({'file': str(dest.relative_to(out)), 'original_label': r['source_label'],
                       'canonical_candidate': r.get('canonical_candidate'),
                       'source_board': r['sheet'], 'source_sha256': sha256(src),
                       'source_rect_px': r['rect'], 'crop_size_px': dimensions,
                       'crop_sha256': sha256(dest), 'status': 'review_only_not_native',
                       'landmark_verification': 'not_performed'})
    manifest = {'schema': 'exodia.board-slice-review/v1', 'release_enabled': False,
                'count': len(result), 'slices': result,
                'preflight_summary': {k: report[k] for k in ('matched_label_candidates','missing_canonical_states','production_eligible')},
                'warning': 'No review crop can be promoted by upscaling or placeholder registration.'}
    (out/'slice_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def production_preflight(source_dir: Path, report: dict, ledger: Path | None, manifest: Path | None) -> list[str]:
    errors=[]
    if report['errors']: errors.extend(report['errors'])
    if report['missing_canonical_states']: errors.append('incomplete_33_state_mapping')
    if report['undersized_or_non_native_cells']: errors.append('source_cells_not_native_1536x1920')
    if not ledger or not ledger.is_file():errors.append('per_state_approval_ledger_missing')
    if not manifest or not manifest.is_file():errors.append('production_source_manifest_missing')
    if not report['source_anchors_measured']:errors.append('facial_landmarks_not_verified')
    return errors


def run(args) -> tuple[dict,int]:
    report = inspect(args.source_dir)
    report.update({'run_mode': args.mode, 'status': 'FAILED', 'registry_untouched': True,
                   'production_files_written': 0})
    if args.mode == 'review':
        if report['errors']:
            return report, 1
        manifest = create_review(args.source_dir,args.output_dir,report)
        report.update({'status':'REVIEW_ONLY', 'review_slices_written':manifest['count'],
                      'review_directory':str(args.output_dir), 'production_eligible':False})
        return report, 0
    errors = production_preflight(args.source_dir,report,args.approval_ledger,args.production_manifest)
    if errors:
        report['errors']=list(dict.fromkeys(errors))
        report['status']='FAILED'
        return report, 1
    # The mandatory downstream ingestion path is the existing atomic importer.
    # Production board crops also require an independently signed per-state source
    # manifest and human-reviewed landmarks; preflight refuses to claim those.
    report['status']='BLOCKED'
    report['errors']=['production_direct_board_slicing_requires_independent_landmark_approval']
    return report, 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--mode',choices=('review','production'),default='production')
    p.add_argument('--approval-ledger',type=Path)
    p.add_argument('--production-manifest',type=Path)
    p.add_argument('--report',type=Path)
    args=p.parse_args()
    try: report,code=run(args)
    except Exception as exc: report={'status':'FAILED','errors':[str(exc)],'registry_untouched':True};code=1
    rendered=json.dumps(report,indent=2)+'\n'
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(rendered)
    print(rendered)
    return code

if __name__=='__main__':raise SystemExit(main())