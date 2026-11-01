"""Gemini generated-media handling for an operator's local browser session.

Never treat old thumbnails as the new result. Read only images/videos inside
Gemini model messages. Browser fetch works for authenticated/blob sources; media
are validated and saved to Exodia's own artifacts directory.
"""
from __future__ import annotations
import asyncio,base64,hashlib,re,secrets
from dataclasses import dataclass
from pathlib import Path
from time import monotonic

class MediaCaptureError(RuntimeError):pass

GENERATOR_SCOPE="model-response, .model-response, [data-message-author-role='model']"
MEDIA_SCRIPT=r"""() => {
  const nodes=[...document.querySelectorAll(
    'model-response img, model-response video, .model-response img, .model-response video, [data-message-author-role="model"] img, [data-message-author-role="model"] video'
  )];
  return nodes.filter(n=>{
    const rect=n.getBoundingClientRect();
    const w=n.naturalWidth||n.videoWidth||rect.width;
    const h=n.naturalHeight||n.videoHeight||rect.height;
    return w>=100&&h>=70;
  }).map(n=>({kind:n.tagName.toLowerCase()==='video'?'video':'image',
    src:n.currentSrc||n.getAttribute('src')||'',
    poster:n.getAttribute('poster')||'',width:n.naturalWidth||n.videoWidth||0,
    height:n.naturalHeight||n.videoHeight||0})).filter(n=>n.src&&!n.src.startsWith('javascript:'));
}"""
BINARY_FETCH_SCRIPT=r"""async ({src,limit})=>{
  const response=await fetch(src,{credentials:'include'});
  if(!response.ok)throw Error('media fetch failed '+response.status);
  const data=await response.arrayBuffer();
  if(data.byteLength>limit)throw Error('media file too large');
  const b=new Uint8Array(data);let encoded='';
  for(let i=0;i<b.length;i+=32768){
    encoded+=String.fromCharCode(...b.subarray(i,i+32768));
  }
  return {base64:btoa(encoded),type:response.headers.get('content-type')||''};
}"""

def media_intent(prompt:str)->bool:
    """Only use the image/video watcher for explicit generation tasks."""
    return bool(re.search(r'\b(generate|create|draw|make|design|render|produce|illustrate|animate)\b'
                          r'.{0,100}\b(image|picture|photo|artwork|illustration|video|clip|animation)\b'
                          r'|\b(image|video)\b.{0,50}\b(generate|creation)\b',
                          prompt,re.I|re.S))

def validate_bytes(binary:bytes,kind:str)->str:
    if kind=="image":
        if binary.startswith(b'\x89PNG\r\n\x1a\n'):return '.png'
        if binary.startswith(b'\xff\xd8\xff'):return '.jpg'
        if binary.startswith(b'RIFF') and binary[8:12]==b'WEBP':return '.webp'
    if kind=="video":
        if len(binary)>12 and binary[4:8]==b'ftyp':return '.mp4'
        if binary.startswith(b'\x1a\x45\xdf\xa3'):return '.webm'
    raise MediaCaptureError('Media bytes did not match a supported image/video signature')

@dataclass
class MediaResult:
    answer:str
    media:list[dict]

async def snapshot_media(page)->list[dict]:
    return await page.evaluate(MEDIA_SCRIPT)

async def await_media_answer(page,*,text_selector:str,stop_selector:str,
                             baseline:list[dict],baseline_count:int,baseline_text:str,
                             timeout:float=240.0,poll:float=.5,stable:float=1.5)->MediaResult:
    if timeout<=0 or poll<=0 or stable<=0:raise ValueError('Invalid timing')
    baseline_urls={m['src'] for m in baseline}
    started=monotonic();last_change=started;last_signature=None
    while monotonic()-started<timeout:
        media=await snapshot_media(page)
        new=[m for m in media if m.get('src') not in baseline_urls]
        matches=page.locator(text_selector)
        count=await matches.count()
        text=(await matches.last.inner_text(timeout=5000)).strip() if count else ''
        fresh_text=text if text and (count>baseline_count or text!=baseline_text) else ''
        generating=await page.locator(stop_selector).is_visible() if stop_selector else False
        signature=([m.get('src') for m in new],fresh_text)
        if signature!=last_signature:
            last_signature=signature;last_change=monotonic()
        if (new or fresh_text) and not generating and monotonic()-last_change>=stable:
            return MediaResult(fresh_text,new[:4])
        await asyncio.sleep(poll)
    raise MediaCaptureError('No completed new generated image/video or text detected before timeout')

async def store_media(page,candidates:list[dict],destination:Path,*,max_bytes:int=50*1024*1024)->list[dict]:
    destination.mkdir(parents=True,exist_ok=True)
    records=[]
    for candidate in candidates[:4]:
        kind=candidate.get('kind')
        src=candidate.get('src','')
        if kind not in ('image','video') or not src.startswith(('https://','blob:','data:')):
            continue
        try:
            # Keep the fetch inside the browser's signed-in origin; no arbitrary
            # server-side URL fetching or network SSRF from untrusted responses.
            response=await page.evaluate(BINARY_FETCH_SCRIPT,
                {'src':src,'limit':max_bytes})
            data=base64.b64decode(response['base64'],validate=True)
            if len(data)>max_bytes:raise MediaCaptureError('Media too large')
            ext=validate_bytes(data,kind)
            name=secrets.token_hex(16)+ext
            target=destination/name
            target.write_bytes(data)
            records.append({'kind':kind,'url':'/artifacts/'+name,
                            'bytes':len(data),
                            'sha256':hashlib.sha256(data).hexdigest(),
                            'width':candidate.get('width') or None,
                            'height':candidate.get('height') or None})
        except Exception as exc:
            records.append({'kind':kind,'status':'capture_failed',
                            'reason':type(exc).__name__})
    return records
