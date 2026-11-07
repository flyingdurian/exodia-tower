/** Foot-registered DOM renderer. A movement marker is NEVER a substitute sprite. */
import {validateChibiManifest,DIRECTIONS} from './albedo_chibi_controller.mjs';

export class AlbedoChibiRenderer {
  constructor(root,manifest,{fetcher=fetch,cryptoProvider=globalThis.crypto}={}){
    validateChibiManifest(manifest);
    if(!root)throw Error('Chibi operations floor absent');
    this.root=root;this.manifest=manifest;this.fetcher=fetcher;this.cryptoProvider=cryptoProvider;
    this.actor=root.querySelector('#chibiActor');this.status=root.querySelector('#chibiArtStatus');
    this.marker=root.querySelector('#chibiMarker');this.image=root.querySelector('#chibiFrame');
    this.zoneText=root.querySelector('#chibiZoneState');
    if(!this.actor||!this.status||!this.marker||!this.image||!this.zoneText)throw Error('Chibi floor DOM incomplete');
    this.readyFrames=new Map();this.pendingFrames=new Map();this.assetState=manifest.asset_status;
    this.prefetchedHeadings=new Set();this.disposed=false;
    this.actor.style.setProperty('--foot-x',String(manifest.anchors.foot[0]*100)+'%');
    this.actor.style.setProperty('--foot-y',String(manifest.anchors.foot[1]*100)+'%');
    this.actor.style.setProperty('--shadow-x',String(manifest.anchors.shadow[0]*100)+'%');
    this.actor.style.setProperty('--shadow-y',String(manifest.anchors.shadow[1]*100)+'%');
    this.status.textContent=this.assetState==='approved_40_frame_set'?'40 approved frames · hash check pending':'MOTION PROOF · 40 ART FRAMES PENDING';
  }
  async acquireFrame(key){
    if(this.disposed||this.assetState!=='approved_40_frame_set')return null;
    if(this.readyFrames.has(key))return this.readyFrames.get(key);
    if(this.pendingFrames.has(key))return this.pendingFrames.get(key);
    const record=this.manifest.frames[key];
    if(!record)return null;
    const task=(async()=>{
      try{
        const response=await this.fetcher(record.src,{cache:'no-store'});
        if(!response.ok||!this.cryptoProvider?.subtle)throw Error('Missing frame or cryptographic integrity support');
        const blob=await response.blob();
        if(!blob.type.includes('png'))throw Error('Expected PNG');
        const buffer=await blob.arrayBuffer();
        const digest=await this.cryptoProvider.subtle.digest('SHA-256',buffer);
        const hash=Array.from(new Uint8Array(digest)).map(b=>b.toString(16).padStart(2,'0')).join('');
        if(hash!==record.sha256)throw Error('Sprite frame SHA-256 mismatch');
        // Every approved frame must match the native sprite canvas; a hash alone
        // does not establish the required foot-registered source geometry.
        const canvas=await createImageBitmap(blob);
        const valid=canvas.width===this.manifest.frame_size_px.width&&canvas.height===this.manifest.frame_size_px.height;
        canvas.close();
        if(!valid)throw Error('Sprite frame dimensions mismatch');
        if(this.disposed)return null;
        const objectUrl=URL.createObjectURL(blob);
        if(this.disposed){URL.revokeObjectURL(objectUrl);return null;}
        this.readyFrames.set(key,objectUrl);
        return objectUrl;
      }catch(_){this.status.textContent='FRAME UNAVAILABLE · NO UNVERIFIED ART SHOWN';return null;}
      finally{this.pendingFrames.delete(key);}
    })();
    this.pendingFrames.set(key,task);return task;
  }
  /** Verify all five independently authored frames of the active heading ahead
   * of stride selection. Hashes and dimensions are still checked per frame. */
  prefetchHeading(heading){
    if(this.disposed||this.assetState!=='approved_40_frame_set'||
       !DIRECTIONS.includes(heading)||this.prefetchedHeadings.has(heading))return;
    this.prefetchedHeadings.add(heading);
    for(const key of [
      'idle_'+heading,...Array.from({length:4},(_,i)=>
        'walk_'+heading+'_'+String(i).padStart(2,'0'))
    ])void this.acquireFrame(key);
  }
  draw(snap){
    this.actor.hidden=!snap.enabled;
    if(!snap.enabled){this.zoneText.textContent='Albedo off stage · another companion selected';return;}
    this.actor.style.left=(snap.x*100).toFixed(3)+'%';
    this.actor.style.top=(snap.y*100).toFixed(3)+'%';
    this.actor.dataset.heading=snap.heading;
    this.actor.dataset.motion=snap.mode;
    this.actor.dataset.frame=snap.frame_key;
    this.zoneText.textContent=`${snap.zone.toUpperCase()} · ${snap.mode==='walk'?'Walking':'Idle'} · ${snap.heading.toUpperCase()}`;
    this.marker.querySelector('.chibi-heading').textContent=snap.heading.toUpperCase();
    this.marker.hidden=false;this.image.hidden=true;
    if(this.assetState==='approved_40_frame_set'){
      const key=snap.frame_key;
      this.prefetchHeading(snap.heading);
      // Hide a stale image immediately; only verified current-frame bytes may render.
      if(this.readyFrames.has(key))this.showImage(this.readyFrames.get(key));
      else this.acquireFrame(key).then(url=>{
        if(url&&this.actor.dataset.frame===key&&!this.actor.hidden)this.showImage(url);
      });
    }
  }
  showImage(url){this.image.src=url;this.image.hidden=false;this.marker.hidden=true;this.status.textContent='SHA-VERIFIED CHIBI · OWNER APPROVED ART';}
  destroy(){this.disposed=true;for(const url of this.readyFrames.values())URL.revokeObjectURL(url);this.readyFrames.clear();this.prefetchedHeadings.clear();}
}
