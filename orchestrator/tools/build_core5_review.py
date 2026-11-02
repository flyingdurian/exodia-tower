"""Review-only Core-Five comparison. Never produces production portrait assets.

Verifies the four currently registered prototype previews and marks the true
Pointing slot unavailable. Cyan/gold guides are targets, NOT detected landmarks.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

CORE = ('idle', 'working', 'explaining', 'monitoring', 'pointing')
TARGET = (1536, 1920)
EYE_Y, SHOULDER_Y = 633.6, 980
CARD = (416, 520)

def _font(size):
    for name in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                 'C:/Windows/Fonts/arial.ttf'):
        if Path(name).is_file():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()

def build(registry_path, asset_dir, out_png, out_json):
    registry_path = Path(registry_path)
    asset_dir = Path(asset_dir).resolve()
    reg = json.loads(registry_path.read_text(encoding='utf-8'))
    board = Image.new('RGB', (5 * (CARD[0] + 16) + 32, 716), '#0d1725')
    d = ImageDraw.Draw(board)
    d.text((24, 12), 'EXODIA / ALBEDO — CORE FIVE PREVIEW INSPECTION',
           font=_font(24), fill='#e9f8ff')
    d.text((24, 50), 'CYAN: eye y=633.6px | GOLD: shoulder y=980px | guides are TARGETS, not measurements',
           font=_font(14), fill='#c8dce9')
    d.text((24, 74), 'NOT A PRODUCTION AUDIT · Source images and true pointing pose require separate review',
           font=_font(14), fill='#ffbd8b')
    results = {}
    for index, state in enumerate(CORE):
        info = reg.get('states', {}).get(state, {})
        x, y = 24 + index * (CARD[0] + 16), 136
        d.text((x, 106), state.upper(), font=_font(20), fill='#ffffff')
        path = info.get('path')
        report = dict(state=state, original_source=info.get('original_source'),
                      original_source_sha256=info.get('source_sha256'),
                      native_source_available=False, owner_reviewed=False,
                      measured_eye_y_px=None, measured_shoulder_y_px=None,
                      production_pass=False)
        d.rectangle([x, y, x + CARD[0] - 1, y + CARD[1] - 1],
                    outline='#3b5368', width=2)
        if path is None:
            d.text((x + 40, y + 220), 'TRUE POINTING', font=_font(22), fill='#ffcd91')
            d.text((x + 40, y + 252), 'SOURCE MISSING', font=_font(22), fill='#ffcd91')
            report.update(availability='MISSING', preview_sha256=None)
        else:
            if Path(path).name != path or Path(path).suffix.lower() != '.png':
                raise ValueError(f'Unsafe preview filename for {state}')
            source = (asset_dir / path).resolve()
            if not source.is_relative_to(asset_dir) or not source.is_file():
                raise ValueError(f'Missing listed preview for {state}: {source}')
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if digest != info.get('sha256'):
                raise ValueError(f'Preview SHA-256 mismatch for {state}: {digest}')
            with Image.open(source) as im:
                im.load()
                if im.size != TARGET or im.format != 'PNG':
                    raise ValueError(f'Unexpected canvas/format for {state}: {im.size}, {im.format}')
                scaled = im.convert('RGB').resize(CARD, Image.Resampling.LANCZOS)
            board.paste(scaled, (x, y))
            report.update(availability='PROTOTYPE_ONLY', preview_sha256=digest,
                          preview_canvas=list(TARGET))
        d.line([(x, y + round(EYE_Y * CARD[1] / TARGET[1])),
                (x + CARD[0] - 1, y + round(EYE_Y * CARD[1] / TARGET[1]))],
               fill='#26edee', width=2)
        d.line([(x, y + round(SHOULDER_Y * CARD[1] / TARGET[1])),
                (x + CARD[0] - 1, y + round(SHOULDER_Y * CARD[1] / TARGET[1]))],
               fill='#f9d36a', width=2)
        d.rectangle((x, y, x + CARD[0] - 1, y + CARD[1] - 1),
                    outline='#87a8bd', width=2)
        d.rectangle((x, y + CARD[1] - 49, x + CARD[0] - 1, y + CARD[1] - 1),
                    fill='#0d1725')
        d.text((x + 9, y + CARD[1] - 42), report['availability'],
               font=_font(17), fill='#fff6e2')
        d.text((x + 9, y + CARD[1] - 20),
               'landmarks: UNREVIEWED / NO PIXEL CERTIFICATION',
               font=_font(11), fill='#ffad92')
        results[state] = report
    board.save(out_png, 'PNG')
    report = dict(schema='exodia.core5-preview-diagnostic/v1',
                  status='BLOCKED_MISSING_NATIVE_SOURCES_AND_OWNER_REVIEW',
                  five_of_five_production_pass=False, released_28_states=False,
                  guide_targets=dict(canvas=list(TARGET), eye_y=EYE_Y,
                                     shoulder_y=SHOULDER_Y),
                  preview_only_count=sum(x['availability'] == 'PROTOTYPE_ONLY' for x in results.values()),
                  unavailable_count=sum(x['availability'] == 'MISSING' for x in results.values()),
                  states=results)
    Path(out_json).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'states'}, indent=2))
    return report

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--registry', type=Path,
                   default=Path('orchestrator/frontend/prototype_assets/albedo/prototype_registry.json'))
    p.add_argument('--asset-dir', type=Path,
                   default=Path('orchestrator/frontend/prototype_assets/albedo'))
    p.add_argument('--out-png', type=Path, default=Path('core5_preview_review.png'))
    p.add_argument('--out-json', type=Path, default=Path('core5_preview_diagnostic.json'))
    a = p.parse_args()
    a.out_png.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    build(a.registry, a.asset_dir, a.out_png, a.out_json)

if __name__ == '__main__':
    main()
