"""Gemini generated-media handling for an operator's local browser session.

Never treat old thumbnails as the new result. A large new image counts even
when Gemini moves it outside the old model-response element. Browser fetch works for authenticated/blob sources; media
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
  const result=[];
  const seen=new Set();
  const SELECTOR='model-response, .model-response, [data-message-author-role="model"], generated-image, image-generation, generated-video, [data-test-id*="generated-image"], [data-test-id*="generated-video"]';
  function walk(root,inside){
    if(!root)return;
    // Shadow DOM is used by some Gemini components. document.querySelectorAll
    // alone misses generated content living inside open shadow roots.
    const nodes=root.querySelectorAll('*');
    for(const el of nodes){
      const inMessage=inside || (el.matches&&el.matches(SELECTOR)) || (el.closest&&el.closest(SELECTOR));
      if(el.tagName==='IMG'||el.tagName==='VIDEO'){
        const bounds=el.getBoundingClientRect();
        const width=el.naturalWidth||el.videoWidth||bounds.width;
        const height=el.naturalHeight||el.videoHeight||bounds.height;
        const src=el.currentSrc||el.getAttribute('src')||'';
        const large=width>=180&&height>=180;
        if((inMessage||large)&&width>=100&&height>=70&&src&&!seen.has(src)&&!src.startsWith('javascript:')&&!/avatar|logo|icon/i.test(src)){
          seen.add(src);
          result.push({kind:el.tagName==='VIDEO'?'video':'image',src,
            poster:el.getAttribute('poster')||'',width,height});
        }
      }
      if(el.shadowRoot)walk(el.shadowRoot,inMessage);
    }
  }
  walk(document,false);
  return result;
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
    if re.search(r'\b(generate|create|draw|make|design|render|produce|illustrate|animate)\b'
                 r'.{0,100}\b(image|picture|photo|artwork|illustration|video|clip|animation)\b'
                 r'|\b(image|video)\b.{0,50}\b(generate|creation)\b',
                 prompt,re.I|re.S):
        return True
    if re.search(r'\b(draw|illustrate|paint|render)\s+(?:me\s+)?(?:a|an|the)\b',
                 prompt,re.I):
        return True
    # Gemini also treats concise requests such as "Generate me a pineapple" as
    # image generation even though they omit the word "image". Keep common
    # writing/code requests on the text watcher.
    implicit=re.search(
        r'\b(generate|create|make|design)\s+(?:me\s+)?(?:a|an|the)\s+(.+)',
        prompt,re.I|re.S)
    if not implicit:
        return False
    requested=implicit.group(2).strip()
    text_output=re.search(
        r'\b(summary|text|story|poem|code|script|list|report|answer|response|'
        r'plan|description|caption|email|message|article|document|table)\b',
        requested,re.I)
    return bool(requested) and not text_output

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
                             timeout:float=240.0,poll:float=.5,stable:float=1.5,
                             confirmed_stable:float|None=None)->MediaResult:
    if timeout<=0 or poll<=0 or stable<=0:raise ValueError('Invalid timing')
    if confirmed_stable is not None and not 0<confirmed_stable<=stable:
        raise ValueError('Invalid timing')
    baseline_urls={m['src'] for m in baseline}
    started=monotonic();last_change=started;last_signature=None;saw_stop=False
    while monotonic()-started<timeout:
        media=await snapshot_media(page)
        new=[m for m in media if m.get('src') not in baseline_urls]
        matches=page.locator(text_selector)
        count=await matches.count()
        text=(await matches.last.inner_text(timeout=5000)).strip() if count else ''
        fresh_text=text if text and (count>baseline_count or text!=baseline_text) else ''
        generating=await page.locator(stop_selector).is_visible() if stop_selector else False
        if generating:saw_stop=True
        signature=([m.get('src') for m in new],fresh_text)
        if signature!=last_signature:
            last_signature=signature;last_change=monotonic()
        # Generated media may arrive long after Gemini emits a short introductory sentence.
        # Never treat that sentence as successful image/video completion.
        final_text_only=bool(re.search(
          r"(can(?:not|'t) (?:generate|create|make)|unable to (?:generate|create)|"
          r"couldn(?:'t|ot) (?:generate|create)|sorry.{0,70}(?:image|video))",
          fresh_text,re.I|re.S))
        hold=confirmed_stable if saw_stop and not generating and confirmed_stable is not None else stable
        if (new or final_text_only) and not generating and monotonic()-last_change>=hold:
            return MediaResult(fresh_text,new[:4])
        await asyncio.sleep(poll)
    raise MediaCaptureError('No completed new generated image/video or text detected before timeout')

async def store_media(page,candidates:list[dict],destination:Path,*,max_bytes:int=50*1024*1024)->list[dict]:
    destination.mkdir(parents=True,exist_ok=True)
    records=[]
    seen_sources=set()
    seen_hashes=set()
    for candidate in candidates[:4]:
        if candidate.get('src') in seen_sources:continue
        seen_sources.add(candidate.get('src'))
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
            digest=hashlib.sha256(data).hexdigest()
            # Distinct Gemini media URLs can resolve to identical file bytes.
            if digest in seen_hashes:continue
            name=secrets.token_hex(16)+ext
            target=destination/name
            target.write_bytes(data)
            seen_hashes.add(digest)
            records.append({'kind':kind,'url':'/artifacts/'+name,
                            'bytes':len(data),
                            'sha256':digest,
                            'width':candidate.get('width') or None,
                            'height':candidate.get('height') or None})
        except Exception as exc:
            # Signed Gemini media can use cross-origin URLs that are viewable by the
            # page but cannot be fetched as bytes because of CORS. Preserve at
            # least the visible image as a marked preview, without inventing a
            # full-quality download.
            if kind=='image':
                # The last page image is not necessarily the generated result.
                # Locator queries also traverse Playwright's open shadow roots.
                target=destination/(secrets.token_hex(16)+'.png')
                try:
                    images=page.locator('img')
                    index=await images.evaluate_all(
                        """(elements, source) => elements.findIndex(el =>
                          el.currentSrc === source || el.getAttribute('src') === source)""",
                        src)
                    if index<0:
                        raise MediaCaptureError('Generated image missing from task tab')
                    await images.nth(index).screenshot(path=str(target),timeout=8000)
                    raw=target.read_bytes()
                    if len(raw)>max_bytes:
                        raise MediaCaptureError('Media preview too large')
                    validate_bytes(raw,'image')
                    digest=hashlib.sha256(raw).hexdigest()
                    if digest in seen_hashes:
                        target.unlink(missing_ok=True)
                        continue
                    seen_hashes.add(digest)
                    records.append({'kind':'image','url':'/artifacts/'+target.name,
                                    'bytes':len(raw),'sha256':digest,
                                    'quality':'preview',
                                    'reason':type(exc).__name__})
                    continue
                except Exception:
                    target.unlink(missing_ok=True)
            records.append({'kind':kind,'status':'capture_failed',
                            'reason':type(exc).__name__})
    return records
