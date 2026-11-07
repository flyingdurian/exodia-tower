/** Source-registered RGBA layer compositor. The registered images are *cutouts*, not a complete rig. */
export const ART_PRODUCTION_STATUS = 'artist-repaint-required';
export const ART_RENDER_MODES = Object.freeze(['registered','source-masks']);
export function layerOrder(manifest){
 return Object.entries(manifest.layers || {}).filter(([,m])=>Array.isArray(m.polygons)&&m.polygons.length).sort((a,b)=>(a[1].z||0)-(b[1].z||0));
}
export function validateRegistration(manifest,images){
 if(!Array.isArray(manifest.source_size)||manifest.source_size.length!==2)throw Error('Missing source art registration');
 const [w,h]=manifest.source_size;const rejected=[],ready=[];
 for(const [name,m] of layerOrder(manifest)){
  const [x0,y0,x1,y1]=m.box||[];
  const bboxOK=[x0,y0,x1,y1].every(Number.isFinite)&&x0>=0&&y0>=0&&x1<=w&&y1<=h&&x1>x0&&y1>y0;
  const pivotOK=Array.isArray(m.pivot)&&m.pivot.length===2&&m.pivot.every(Number.isFinite);
  const image=images.get(name);
  const sizeOK=image&&image.naturalWidth>0&&image.naturalHeight>0;
  if(!bboxOK||!pivotOK||!sizeOK)rejected.push({name,reason:!bboxOK?'invalid box':!pivotOK?'invalid pivot':'image unavailable'});
  else ready.push(name);
 }
 return {ready,rejected,production_ready:false,quality_gate:ART_PRODUCTION_STATUS};
}
export function paintRegisteredLayers(ctx,manifest,images,angles,transform,{showBounds=false}={}){
 const drawn=[],missing=[];
 for(const [name,m] of layerOrder(manifest)){
  const image=images.get(name);if(!image?.naturalWidth){missing.push(name);continue;}
  const [x0,y0,x1,y1]=m.box;ctx.save();transform(ctx,name,angles);
  ctx.drawImage(image,x0,y0,x1-x0,y1-y0);
  if(showBounds){ctx.strokeStyle='rgba(255,205,106,.95)';ctx.lineWidth=2;ctx.strokeRect(x0,y0,x1-x0,y1-y0);}
  ctx.restore();drawn.push(name);
 }
 return {drawn,missing};
}
