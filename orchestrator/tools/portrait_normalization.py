"""Deterministic, downsample-only normalization of independently rendered portraits.

Never upsample, stretch an image to a new aspect, or extract panels from boards.
The returned crop/scale transform maps independently reviewed source landmarks.
"""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
from PIL import Image
import hashlib

TARGET = (1536, 1920)

class NormalizationRejected(ValueError):
    pass


def normalize_portrait(path: Path):
    """Return (PNG bytes, transform) using a centered crop + Lanczos reduction."""
    with Image.open(path) as im:
        if im.format != 'PNG':
            raise NormalizationRejected('source_not_png')
        w, h = im.size
        if w < TARGET[0] or h < TARGET[1]:
            raise NormalizationRejected('downsample_only_source_too_small')
        if w * TARGET[1] >= h * TARGET[0]:
            cw, ch = round(h * TARGET[0] / TARGET[1]), h
        else:
            cw, ch = w, round(w * TARGET[1] / TARGET[0])
        if cw < TARGET[0] or ch < TARGET[1]:
            raise NormalizationRejected('crop_would_require_upscaling')
        x0, y0 = (w-cw)//2, (h-ch)//2
        crop = (x0, y0, x0+cw, y0+ch)
        image = im.convert('RGBA' if 'A' in im.getbands() else 'RGB')
        image = image.crop(crop).resize(TARGET, Image.Resampling.LANCZOS)
        out = BytesIO()
        image.save(out, format='PNG', optimize=True, compress_level=9)
        data = out.getvalue()
    transform = {
        'schema': 'exodia.portrait-normalization/v1',
        'method': 'center_crop_lanczos_downsample',
        'source_canvas': [w, h], 'crop_box': list(crop),
        'output_canvas': list(TARGET),
        'scale_x': TARGET[0]/cw, 'scale_y': TARGET[1]/ch,
        'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'output_sha256': hashlib.sha256(data).hexdigest(),
    }
    return data, transform


def transform_landmarks(points, transform):
    if not isinstance(points, dict):
        raise NormalizationRejected('reviewed_source_landmarks_missing')
    x0,y0,x1,y1=transform['crop_box']
    w,h=transform['source_canvas']
    result={}
    for key, xy in points.items():
        if (not isinstance(xy, (list,tuple)) or len(xy)!=2 or
            any(type(v) not in (int,float) for v in xy)):
            raise NormalizationRejected('invalid_source_landmark_'+key)
        x,y=xy
        if not (0<=x<w and 0<=y<h and x0<=x<x1 and y0<=y<y1):
            raise NormalizationRejected('landmark_cropped_or_outside_source_'+key)
        result[key]=[round((x-x0)*transform['scale_x'],5),
                     round((y-y0)*transform['scale_y'],5)]
    return result
