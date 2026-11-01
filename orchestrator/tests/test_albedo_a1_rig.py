"""A1 GLB engineering QA. No claims of production art acceptance."""
import importlib.util
import os
from pathlib import Path
import struct
import pytest

ROOT = Path(__file__).parent.parent

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

builder = load(ROOT / 'tools' / 'build_albedo_rig_proof.py', 'albedo_a1_builder')
checker = load(ROOT / 'tools' / 'validate_albedo_rig.py', 'albedo_a1_checker')

@pytest.fixture(scope='module')
def model(tmp_path_factory):
    file = tmp_path_factory.mktemp('rig')/'test.glb'
    builder.build(file)
    return file


def test_deterministic_skinned_glb_and_action_set(model, tmp_path):
    output = tmp_path/'clone.glb'
    builder.build(output)
    assert model.read_bytes() == output.read_bytes()
    report = checker.inspect(model)
    assert report['valid'], report
    assert report['joints'] == 35
    assert report['vertices'] == 6972
    assert report['smooth_weight_vertices'] > 1000
    assert report['triangles'] == 12800
    assert report['actions'] == list(checker.REQUIRED_ACTIONS)
    assert not report['production_ready']


def test_animated_rotations_and_locmotion_are_not_static_frames(model):
    doc, raw = checker.parse_glb(model)
    clips = {a['name']: a for a in doc['animations']}
    assert len(clips['walk']['channels']) >= 8
    assert len(clips['typing_working']['channels']) >= 8
    assert len(clips['celebrating']['channels']) >= 8
    for action in ('walk', 'run', 'typing_working', 'celebrating', 'waking_up'):
        values=[]
        for channel in clips[action]['channels']:
            sampler=clips[action]['samplers'][channel['sampler']]
            accessor=doc['accessors'][sampler['output']]
            view=doc['bufferViews'][accessor['bufferView']]
            start=view['byteOffset']
            val=raw[start:start+view['byteLength']]
            # At least one authored joint/position channel changes within each clip.
            if len(val) >= 16:
                values.append(len(set(val[i:i+16] for i in range(0,len(val)-15,16)))>1)
        assert any(values), f'{action} does not animate a joint'


def test_bad_glb_header_fails_closed(tmp_path):
    bad=tmp_path/'bad.glb'
    bad.write_bytes(b'not a glb')
    with pytest.raises(checker.RigValidationError):checker.inspect(bad)


def test_approval_is_not_faked(model, tmp_path):
    original=model.read_bytes()
    assert b'production_ready' in original
    # If a tool flips engineering status to release-ready in the GLB JSON,
    # the structural acceptance gate must refuse it.
    tampered=tmp_path/'tampered.glb'
    tampered.write_bytes(original.replace(b'"production_ready":false',b'"production_ready":true '))
    # Replacements preserve JSON size if both values are length matched (false/true+space).
    report=checker.inspect(tampered)
    assert not report['valid']
    assert any('unapproved' in e for e in report['errors'])


def test_weighted_leg_surface_actually_deforms_under_walk_curve():
    """Evaluate skin transforms numerically; animation tracks alone aren't proof."""
    import math

    def qmul(a, b):
        ax, ay, az, aw = a; bx, by, bz, bw = b
        return (aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx,
                aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz)

    def rot(q, vec):
        v = (vec[0], vec[1], vec[2], 0.0)
        conjugate = (-q[0], -q[1], -q[2], q[3])
        return qmul(qmul(q, v), conjugate)[:3]

    def posed(t):
        angles, offsets = builder.posture('walk', t)
        centers, orient = {}, {}
        identity = (0., 0., 0., 1.)
        for name, parent, delta in builder.BONES:
            pq = orient[parent] if parent else identity
            pc = centers[parent] if parent else (0., 0., 0.)
            off = offsets.get(name, (0, 0, 0))
            local = tuple(delta[i]+off[i] for i in range(3))
            moved = rot(pq, local)
            centers[name] = tuple(pc[i]+moved[i] for i in range(3))
            orient[name] = qmul(pq, angles.get(name, identity))
        return centers, orient

    def skin(vertex_index, frame):
        centers, orientations = posed(frame)
        xyz = builder.V[vertex_index*3:vertex_index*3+3]
        ids = builder.J[vertex_index*4:vertex_index*4+4]
        ws = builder.W[vertex_index*4:vertex_index*4+4]
        out = [0.,0.,0.]
        for jid, weight in zip(ids, ws):
            if weight == 0:continue
            name = builder.BONES[jid][0]
            bound = builder.ABS[name]
            local = [xyz[i]-bound[i] for i in range(3)]
            new_point = rot(orientations[name], local)
            for i in range(3):out[i] += weight*(centers[name][i]+new_point[i])
        return out

    wanted = {builder.INDEX['thigh_L'], builder.INDEX['knee_L']}
    candidates = [i for i in range(len(builder.V)//3)
                  if set(builder.J[i*4:i*4+2]) == wanted
                  and 0.1 < builder.W[i*4+1] < .9]
    assert len(candidates) >= 10
    displacement=max(math.dist(skin(i,0),skin(i,.25)) for i in candidates)
    assert displacement > .1, ('Walk clip does not visibly deform the weighted leg', displacement)
