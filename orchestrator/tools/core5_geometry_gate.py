"""Gate 2 strict geometry feasibility. Measurement != approval.

Affine invariants expose concepts that cannot meet head width AND eye/shoulder
spacing with one uniform scale. Coordinates must be annotated on a verified
original; never infer them from final target pixels.
"""
from __future__ import annotations
import math

CANVAS=(1536,1920)
EYE_Y=633.6
SHOULDER_Y=980.
HEAD_W=614.4
HEAD_TOL=4.
ANCHOR_TOL=2.
CENTER_X=768.
CENTER_TOL=2.
MAX_EYE_ASYMMETRY=12.
MAX_SHOULDER_ASYMMETRY=14.
EYE_SEPARATION_TARGET_PX=None # compared across the independently authored batch

def xy(p):
    if (not isinstance(p,(list,tuple)) or len(p)!=2 or
        any(type(v) not in (int,float) or not math.isfinite(v) for v in p)):
        raise ValueError('invalid_landmark_coordinate')
    return float(p[0]),float(p[1])

def feasibility(annotation):
    eyes=[xy(annotation[key]) for key in ('left_eye_xy','right_eye_xy')]
    shoulder=[xy(annotation[key]) for key in ('left_shoulder_xy','right_shoulder_xy')]
    head=annotation.get('head_width_px')
    if type(head) not in (int,float) or not math.isfinite(head) or head<=0:
        raise ValueError('head_width_missing_or_invalid')
    center=(eyes[0][0]+eyes[1][0])/2
    eyes_y=(eyes[0][1]+eyes[1][1])/2
    shoulders_y=(shoulder[0][1]+shoulder[1][1])/2
    distance=shoulders_y-eyes_y
    if distance<=100: raise ValueError('anatomical_separation_invalid')
    # Both independent anchor midpoints allow +/-2 px: their difference +/-4 px.
    anchor_range=((SHOULDER_Y-EYE_Y-2*ANCHOR_TOL)/distance,
                  (SHOULDER_Y-EYE_Y+2*ANCHOR_TOL)/distance)
    head_range=((HEAD_W-HEAD_TOL)/float(head),(HEAD_W+HEAD_TOL)/float(head))
    overlap=(max(anchor_range[0],head_range[0]),
             min(anchor_range[1],head_range[1]))
    nominal=(SHOULDER_Y-EYE_Y)/distance
    return {
      'original_eye_mid_xy':[round(center,3),round(eyes_y,3)],
      'original_shoulder_baseline_y':round(shoulders_y,3),
      'original_eye_to_shoulder_px':round(distance,3),
      'original_head_width_px':float(head),
      'rigid_nominal_scale':round(nominal,8),
      'nominal_head_width_px':round(nominal*head,3),
      'nominal_eye_separation_px':round(abs(eyes[1][0]-eyes[0][0])*nominal,3),
      'nominal_eye_vertical_asymmetry_px':round(abs(eyes[0][1]-eyes[1][1])*nominal,3),
      'nominal_shoulder_vertical_asymmetry_px':round(abs(shoulder[0][1]-shoulder[1][1])*nominal,3),
      'anchor_compatible_scale_range':[round(v,8) for v in anchor_range],
      'head_compatible_scale_range':[round(v,8) for v in head_range],
      'shared_scale_range':[round(v,8) for v in overlap] if overlap[0]<=overlap[1] else None,
      'all_three_geometry_targets_uniformly_feasible':overlap[0]<=overlap[1],
      'requires_native_composition_reauthoring':overlap[0]>overlap[1],
      'anatomical_human_review_required':True
    }

def validate_independent_measurements(measured, *, source_approved=False):
    """Fail closed: pixel evidence and named anatomy each independently checked."""
    errors=[]
    if not measured or not measured.get('pixel_measurement_independent',False):
        errors.append('independent_pixel_measurement_missing')
    if not measured or not measured.get('anatomical_labels_human_verified',False):
        errors.append('anatomical_identity_unverified')
    if not source_approved: errors.append('owner_exact_hash_approval_missing')
    eyes=measured.get('eyes',[]) if measured else []
    shoulders=measured.get('shoulders',[]) if measured else []
    if len(eyes)!=2 or len(shoulders)!=2:
        return {'status':'FAIL','errors':errors+['both_eye_and_shoulder_pairs_required']}
    try:
        e=[xy(k) for k in eyes]
        s=[xy(k) for k in shoulders]
        width=float(measured['head_width_px'])
        center=float(measured['center_x_px'])
        assert math.isfinite(width) and math.isfinite(center)
    except (ValueError,KeyError,TypeError,AssertionError):
        return {'status':'FAIL','errors':errors+['malformed_measurements']}
    eye_mid=sum(v[1] for v in e)/2
    sh_mid=sum(v[1] for v in s)/2
    if abs(eye_mid-EYE_Y)>ANCHOR_TOL:errors.append('eye_midpoint_out_of_range')
    if abs(sh_mid-SHOULDER_Y)>ANCHOR_TOL:errors.append('shoulder_baseline_out_of_range')
    if abs(width-HEAD_W)>HEAD_TOL:errors.append('head_width_out_of_range')
    if abs(center-CENTER_X)>CENTER_TOL:errors.append('horizontal_center_out_of_range')
    if abs(e[0][1]-e[1][1])>MAX_EYE_ASYMMETRY:errors.append('eye_asymmetric_drift')
    if abs(s[0][1]-s[1][1])>MAX_SHOULDER_ASYMMETRY:errors.append('shoulder_asymmetric_drift')
    if e[0][0]>=e[1][0]:errors.append('eyes_reversed_or_overlapping')
    if s[0][0]>=s[1][0]:errors.append('shoulders_reversed_or_overlapping')
    if not(90<=e[1][0]-e[0][0]<=260): errors.append('eye_separation_implausible')
    if not(300<=s[1][0]-s[0][0]<=800): errors.append('shoulder_separation_implausible')
    return {'status':'PASS' if not errors else 'FAIL','errors':errors,
            'measured_eye_mid_y_px':round(eye_mid,3),
            'measured_shoulder_mid_y_px':round(sh_mid,3),
            'eye_separation_px':round(e[1][0]-e[0][0],3),
            'eye_asymmetry_px':round(abs(e[0][1]-e[1][1]),3),
            'shoulder_asymmetry_px':round(abs(s[0][1]-s[1][1]),3),
            'head_width_delta_px':round(width-HEAD_W,3),
            'center_x_delta_px':round(center-CENTER_X,3)}
