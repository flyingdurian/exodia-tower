/** Phase 6: fail-closed local connection/snapshot release-readiness contract.
 * Presence of WebSocket == ONLY the EXODIA local stream, never provider auth.
 */
export const FRESHNESS=Object.freeze(['fresh','aging','stale','unavailable','offline']);
const LINKS=new Set(['connected','connecting','disconnected']);
export function boundedRetryDelay(attempt){
  if(!Number.isInteger(attempt)||attempt<0||attempt>1000)
    throw RangeError('Invalid local reconnect attempt');
  return Math.min(15000,1500*Math.pow(2,Math.min(4,attempt)));
}
export function canRefresh({visible=true,online=true}={}){
  return visible===true&&online===true;
}
export function observeResilience({
  now,lastSnapshotAt=0,link='disconnected',
  online=true,visible=true,failures=0
}={}){
  if(!Number.isFinite(now)||now<0||!Number.isFinite(lastSnapshotAt)||
    lastSnapshotAt<0||!LINKS.has(link)||typeof online!=='boolean'||
    typeof visible!=='boolean'||!Number.isInteger(failures)||failures<0)
    throw Error('Invalid Frontshell reliability signal');
  const ageMs=lastSnapshotAt>0?Math.max(0,now-lastSnapshotAt):null;
  const freshness=!online?'offline':ageMs===null?'unavailable':
    ageMs>30000?'stale':ageMs>15000?'aging':'fresh';
  const state=!online?'LOCAL NETWORK OFFLINE':
    link==='connected'?'LOCAL EVENT STREAM LIVE':
    link==='connecting'?'LOCAL EVENT STREAM CONNECTING':
    'LOCAL EVENT STREAM DISCONNECTED';
  return Object.freeze({
    ageMs,freshness,
    link:online?link:'disconnected',
    visible,online,failures,
    state,
    snapshotLabel:ageMs===null?'NO VERIFIED SNAPSHOT':
      'LAST LOCAL SNAPSHOT · '+Math.round(ageMs/1000)+'S AGO',
    providerAuthenticationVerified:false,
    providerWebSocketsVerified:false,
    productionArtworkReleased:false,
    windowsOperatorAcceptanceVerified:false
  });
}
