"""Compose modeler QA board from real locked reference and actual rejected A1 render.

This tool never fabricates or edits visual identity and never represents a still as a rig.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import json
BASE=Path(__file__).resolve().parents[1]
REF=BASE/'references/approved_full_body.png'
BAD=BASE/'reports/rejected_a1_idle.png'
REPORT=json.loads((BASE/'reports/rejected_a1.json').read_text())
fontroot=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
FONT=lambda size:ImageFont.truetype(str(fontroot),size) if fontroot.exists() else ImageFont.load_default()
CANVAS=Image.new('RGB',(1800,1320),(8,13,36))
d=ImageDraw.Draw(CANVAS)
d.text((44,20),'EXODIA TOWER  /  ALBEDO A3  /  IDENTITY FIDELITY GATE',font=FONT(29),fill=(237,238,255))
d.text((44,66),'Approved concept is authoritative. A1 model remains rejected. Nothing below is a finished 3D character.',font=FONT(17),fill=(178,188,230))
ref=Image.open(REF).convert('RGB');bad=Image.open(BAD).convert('RGB')
# Fit complete art to a bounded comparison area, with no character masking or invented repaint.
def image_at(source,box):
 x,y,w,h=box
 thumb=ImageOps.contain(source,(w,h),Image.Resampling.LANCZOS)
 CANVAS.paste(thumb,(x+(w-thumb.width)//2,y+(h-thumb.height)//2))
 return (x+(w-thumb.width)//2,y+(h-thumb.height)//2,thumb.width,thumb.height)
image_at(ref,(35,125,580,870));image_at(bad,(635,200,500,730))
d.text((55,1000),'APPROVED FULL-BODY SOURCE',font=FONT(21),fill=(114,246,204))
d.text((700,1000),'REJECTED ENGINEERING PROXY',font=FONT(21),fill=(255,174,155))
d.text((1145,125),'DETAIL RETENTION / NEGATIVE QA',font=FONT(19),fill=(232,226,255))
labels=[('Face', 'face'),('Collar crystal','collar_crystal'),('Bodice','bodice'),('Waist ornament','waist_ornament'),('Draped panels','draped_panels'),('Hair','hair'),('Boots','boots')]
for i,(name,key) in enumerate(labels):
 t=REPORT['zones'][key];ratio=t['relative_edge_detail'];v=t['low_detail_blocker']
 yy=180+100*i;d.text((1145,yy),name,font=FONT(21),fill=(229,232,255))
 d.text((1145,yy+35),f'Visual edge retention: {ratio:.2f}x',font=FONT(16),fill=(170,185,223))
 d.rounded_rectangle((1510,yy+15,1745,yy+49),radius=10,fill=(102,36,61) if v else (37,60,82))
 d.text((1530,yy+19),'REJECTED' if v else 'Still review',font=FONT(15),fill=(255,218,221) if v else (205,226,238))
d.text((1145,960),f'{sum(x["low_detail_blocker"] for x in REPORT["zones"].values())} of 7 critical zones failed',font=FONT(23),fill=(255,162,162))
d.multiline_text((1145,1015),'This metric is for early REJECTION only.\nA passing score cannot approve a 3D model.\nNo five-view, topology, or likeness proof\nexists for the rejected A1 candidate.',font=FONT(18),spacing=12,fill=(185,201,224))
d.text((35,1252),'Locked source SHA-256: '+REPORT['reference_sha256'],font=FONT(15),fill=(143,166,208))
CANVAS.save(BASE/'reports/albedo_a3_fidelity_rejection_board.png')
print(BASE/'reports/albedo_a3_fidelity_rejection_board.png')