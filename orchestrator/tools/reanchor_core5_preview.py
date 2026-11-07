"""Rigid whole-image preview registration; never fakes landmark approval."""
import argparse,json,hashlib
from pathlib import Path
import cv2,numpy as np
from audit_portrait_anchors import measure_png,SIZE,EYE_Y,SHOULDER_Y,CORE
def reanchor(source,output,search):
    m=measure_png(source,search);dy=m['shoulder_y_px']-m['eye_y_px']
    if dy<250:raise ValueError('uncertain_vertical_anchor_separation')
    scale=(SHOULDER_Y-EYE_Y)/dy
    if not .85<=scale<=1.15:raise ValueError('unsafe_scale')
    x=sum(p['x'] for p in m['eyes'])/2
    tx=SIZE[0]/2-scale*x;ty=EYE_Y-scale*m['eye_y_px']
    img=cv2.imread(str(source))
    background=tuple(int(v) for v in img[15,15])
    output.parent.mkdir(parents=True,exist_ok=True)
    final=cv2.warpAffine(img,np.float32([[scale,0,tx],[0,scale,ty]]),SIZE,
        flags=cv2.INTER_LANCZOS4,borderMode=cv2.BORDER_CONSTANT,borderValue=background)
    if not cv2.imwrite(str(output),final):raise OSError('png_write_failed')
    return dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
       output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
       source_pixel_anchors=m,scale=scale,translation_xy=[tx,ty],
       predicted_eye_y=scale*m['eye_y_px']+ty,
       predicted_shoulder_y=scale*m['shoulder_y_px']+ty,
       preview_only=True,owner_reviewed=False,
       warning='Predictions are transform arithmetic; verify resulting pixels separately.')
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--search',type=Path,required=True);p.add_argument('--state',choices=CORE,required=True)
    p.add_argument('--report',type=Path);a=p.parse_args()
    hints=json.loads(a.search.read_text())['states'][a.state]
    result=reanchor(a.source,a.output,hints);print(json.dumps(result,indent=2))
    if a.report:a.report.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
