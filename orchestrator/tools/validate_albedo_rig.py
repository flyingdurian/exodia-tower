"""Strict structural inspection of the Albedo A1 skinned GLB engineering proof.

No external dependency. This does not approve the model's likeness, motion quality,
foot locking, facial expressions, or suitability for live companion rendering.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

REQUIRED_ACTIONS = ('idle', 'walk', 'run', 'jump', 'sit', 'work_computer',
                    'typing_working', 'pointing', 'explaining', 'celebrating',
                    'stretching', 'sleeping', 'waking_up')
TYPES = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
COMPONENTS = {5121: ('B', 1), 5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}


class RigValidationError(ValueError):
    pass


def parse_glb(path: Path):
    raw = Path(path).read_bytes()
    if len(raw) < 28 or raw[:4] != b'glTF' or struct.unpack_from('<I', raw, 4)[0] != 2:
        raise RigValidationError('Not a GLB 2.0 binary file')
    if struct.unpack_from('<I', raw, 8)[0] != len(raw):
        raise RigValidationError('GLB header length mismatch')
    offset, json_data, bin_data = 12, None, None
    while offset < len(raw):
        if offset + 8 > len(raw):
            raise RigValidationError('Truncated GLB chunk header')
        length, kind = struct.unpack_from('<I4s', raw, offset)
        offset += 8
        if length % 4 or offset + length > len(raw):
            raise RigValidationError('Invalid GLB chunk bounds')
        payload = raw[offset:offset + length]
        offset += length
        if kind == b'JSON':
            if json_data is not None:
                raise RigValidationError('Duplicate JSON chunk')
            json_data = json.loads(payload)
        elif kind == b'BIN\0':
            if bin_data is not None:
                raise RigValidationError('Duplicate BIN chunk')
            bin_data = payload
    if json_data is None or bin_data is None:
        raise RigValidationError('Missing JSON or BIN chunk')
    if len(json_data['buffers']) != 1 or json_data['buffers'][0]['byteLength'] > len(bin_data):
        raise RigValidationError('Invalid binary buffer length')
    return json_data, bin_data


def inspect(path: Path):
    doc, binary = parse_glb(path)
    errors = []
    joints = doc.get('skins', [{}])[0].get('joints', [])
    if len(joints) != 35 or len(set(joints)) != 35:
        errors.append('Expected 35 unique weighted skeleton joints')
    nodes = doc.get('nodes', [])
    if any(not isinstance(i, int) or i >= len(nodes) or i < 0 for i in joints):
        errors.append('Joint index exceeds node table')
    node_names = [n.get('name') for n in nodes]
    for node in ('root', 'hips', 'head', 'shoulder_L', 'shoulder_R', 'thigh_L', 'thigh_R', 'foot_L', 'foot_R'):
        if node not in node_names:
            errors.append('Required joint missing: ' + node)

    def accessor(index):
        a = doc['accessors'][index]
        view = doc['bufferViews'][a['bufferView']]
        typ = a['type']; kind = a['componentType']
        if typ not in TYPES or kind not in COMPONENTS:
            raise RigValidationError('Unsupported accessor format')
        fmt, size = COMPONENTS[kind]
        stride = size * TYPES[typ]
        if view.get('byteStride', stride) != stride:
            raise RigValidationError('Unsupported interleaved accessor')
        start = view.get('byteOffset', 0) + a.get('byteOffset', 0)
        end = start + a['count'] * stride
        if start < 0 or end > view.get('byteOffset', 0) + view['byteLength'] or end > len(binary):
            raise RigValidationError('Accessor exceeds GLB binary bounds')
        return struct.unpack_from('<' + fmt * (a['count'] * TYPES[typ]), binary, start), a['count']

    total_vertices = 0
    tris = 0
    nontrivial_weights = 0
    if not doc.get('meshes'):
        errors.append('No skinned mesh available')
    else:
        for primitive in doc['meshes'][0].get('primitives', []):
            attrs = primitive.get('attributes', {})
            if not {'POSITION', 'NORMAL', 'JOINTS_0', 'WEIGHTS_0'} <= set(attrs):
                errors.append('Primitive missing required skinning streams')
                continue
            vertices, count = accessor(attrs['POSITION'])
            weights, wc = accessor(attrs['WEIGHTS_0'])
            indices, ic = accessor(attrs['JOINTS_0'])
            faces, fc = accessor(primitive['indices'])
            if not (count == wc == ic):
                errors.append('Vertex weight and joint stream counts differ')
            # All parts in this engineering proof reference the same global vertex buffer.
            total_vertices = max(total_vertices, count)
            tris += fc // 3
            if any(not math.isfinite(w) for w in weights):
                errors.append('Nonfinite skinning weight')
            if any(abs(sum(weights[k:k+4]) - 1) > 0.0002 for k in range(0, len(weights), 4)):
                errors.append('Vertex skinning weights must sum to 1')
            nontrivial_weights = sum(1 for k in range(0, len(weights), 4) if 0 < weights[k + 1] < 1)
            if any(i >= len(joints) for i in indices):
                errors.append('Vertex references nonexistent joint')
            if any(idx >= count for idx in faces):
                errors.append('Mesh index exceeds vertex count')
    if nontrivial_weights < 100:
        errors.append('No evidence of smooth two-joint skinning')
    names = [x.get('name') for x in doc.get('animations', [])]
    if len(names) != len(set(names)) or set(names) != set(REQUIRED_ACTIONS):
        errors.append('Required 13 named rig animation clips not present')
    for clip in doc.get('animations', []):
        if not clip.get('channels'):
            errors.append('Animation has no channels: ' + str(clip.get('name')))
        for channel in clip.get('channels', []):
            sampler = clip['samplers'][channel['sampler']]
            ts, n = accessor(sampler['input'])
            val, out_n = accessor(sampler['output'])
            if n < 2 or n != out_n or ts[0] != 0 or not all(a < b for a, b in zip(ts, ts[1:])):
                errors.append('Invalid time samples: ' + str(clip.get('name')))
            if channel['target']['node'] >= len(nodes) or channel['target']['path'] not in ('rotation', 'translation'):
                errors.append('Unsupported channel target')
            if channel['target']['path'] == 'rotation':
                if any(abs(math.sqrt(sum(x*x for x in val[k:k+4])) - 1) > .001 for k in range(0, len(val), 4)):
                    errors.append('Quaternion not normalized in ' + str(clip.get('name')))
    if doc.get('extras', {}).get('owner_approved_art') is not False or doc.get('extras', {}).get('production_ready') is not False:
        errors.append('Engineering proxy must be labelled unapproved')
    # None of the contact-sheet imagery can be a texture on this engineering proof.
    if doc.get('images') or doc.get('textures'):
        errors.append('Engineering proxy unexpectedly includes source-art textures')
    return {'valid': not errors, 'errors': list(dict.fromkeys(errors)),
            'joints': len(joints), 'vertices': total_vertices,
            'triangles': tris, 'smooth_weight_vertices': nontrivial_weights,
            'actions': names, 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            'production_ready': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('glb', type=Path)
    arguments = parser.parse_args()
    report = inspect(arguments.glb)
    print(json.dumps(report, indent=2))
    return 0 if report['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
