"""Albedo Phase 3: stationary-camera storyboard comparison, not HD animation."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

NATIVE=(1536,1920)
PREVIEW=(256,320)
STATES=('idle','working','explaining')
# Floral headpiece offsets in the existing Phase 2 concept-board crops.
OFFSETS={
 'idle':((0,0),(20,0),(27,0),(28,0)),
 'working':((0,0),(16,1),(20,-3),(26,-2)),
 'explaining':((0,0),(15,1),(22,0),(26,1)),
}
ORDER=(0,1,2,3,2,1)
DURATIONS={
 'idle':(720,690,210,780,690,720),
 'working':(340,360,380,360,340,370),
 'explaining':(400,400,430,390,400,440),
}

def digest(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def static_matte()->Image.Image:
    im=Image.new('RGB',PREVIEW);pix=im.load()
    for y in range(PREVIEW[1]):
        for x in range(PREVIEW[0]):
            t=max(0,1-((x-127)/200)**2-((y-136)/260)**2)
            pix[x,y]=(round(12+20*t),round(13+14*t),round(43+45*t))
    return im

def soft_mask(size)->Image.Image:
    w,h=size
    mask=Image.new('L',(w,h),0)
    ImageDraw.Draw(mask).ellipse((23,6,w-7,h+54),fill=255)
    return mask.filter(ImageFilter.GaussianBlur(14))

def render_frames(source:Path,state:str)->list[Image.Image]:
    if state not in STATES: raise ValueError('Unknown storyboard action')
    result=[]
    for i,(dx,dy) in enumerate(OFFSETS[state],1):
        with Image.open(source/(state+f'_storyboard_{i:02d}.png')) as src:
            picture=src.convert('RGB')
        if not (170<=picture.width<=235 and 210<=picture.height<=290):
            raise ValueError('Unexpected storyboard cell; do not use HD originals as a crop')
        canvas=static_matte()
        canvas.paste(picture,(37-dx,38-dy),soft_mask(picture.size))
        result.append(canvas)
    return result

def build(source:Path,out:Path)->dict:
    out.mkdir(parents=True,exist_ok=True)
    report={'schema':'exodia.albedo.storyboard-camera-lock/v1',
            'status':'review_only_not_hd_motion','canvas_px':list(PREVIEW),
            'production_canvas_px':list(NATIVE),
            'camera_translation_px':[0,0],'camera_scale':1,'camera_rotation':0,
            'loops':{}}
    for state in STATES:
        images=render_frames(source,state)
        files=[]
        for n,img in enumerate(images,1):
            p=out/f'{state}_locked_{n:02}.png';img.save(p)
            files.append({'file':p.name,'sha256':digest(p)})
        gif=out/(state+'_CAMERA_LOCK_STORYBOARD_ONLY.gif')
        seq=[images[i] for i in ORDER]
        seq[0].save(gif,save_all=True,append_images=seq[1:],
                    duration=DURATIONS[state],loop=0,optimize=False,disposal=2)
        report['loops'][state]={
            'gif':gif.name,'sha256':digest(gif),'frames':files,
            'display_order':[i+1 for i in ORDER],
            'source_offsets_px':[list(p) for p in OFFSETS[state]],
            'approved_as_full_hd':False,
            'source_cells_are_small':True,
            'character_frame_transformed_between_frames':False,
        }
    (out/'camera_lock_report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def validate_native(paths:list[Path],registration:list[dict])->list[str]:
    """Technical validation; no automatic artistic or release approval."""
    errors=[]
    if len(paths)<4 or len(paths)!=len(registration):
        errors.append('requires_four_frames_and_equal_registration_metadata')
    hashes=[]
    for n,p in enumerate(paths):
        if not p.is_file():
            errors.append(f'frame_{n}_missing');continue
        with Image.open(p) as im:
            if im.size!=NATIVE:errors.append(f'frame_{n}_not_native_4x5')
        hashes.append(digest(p))
    if len(set(hashes))!=len(hashes):errors.append('duplicate_frames')
    if len(registration)==len(paths) and registration:
        for key,tolerance in (('eye_x',.008),('eye_y',.008),('head_width',.012)):
            try: vals=[float(x[key]) for x in registration]
            except (KeyError,TypeError,ValueError):
                errors.append('missing_landmark_'+key);continue
            if max(vals)-min(vals)>tolerance:errors.append('camera_drift_'+key)
    return errors

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--storyboard-source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=build(args.storyboard_source,args.output)
    print(json.dumps({'stage':report['status'],'loops':list(report['loops']),
                      'production_ready':False}))

if __name__=='__main__':main()
