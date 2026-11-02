/** Workbench-only controller. Cannot load or modify the signed production registry. */
export const PROTOTYPE_SCHEMA = 'exodia.albedo-prototype-preview/v1';
export const PROTOTYPE_STATES = Object.freeze(['idle', 'working', 'explaining', 'monitoring', 'pointing']);

export function validPrototypeRegistry(registry) {
  if (registry?.schema !== PROTOTYPE_SCHEMA || registry?.production_release_enabled !== false ||
      registry?.canvas?.width !== 1536 || registry?.canvas?.height !== 1920) return false;
  return PROTOTYPE_STATES.every(k =>
    registry.states?.[k]?.approval === 'UNAPPROVED_PROTOTYPE' &&
    registry.states?.[k]?.canvas?.[0] === 1536 &&
    registry.states?.[k]?.canvas?.[1] === 1920 &&
    /^[a-f0-9]{64}$/i.test(registry.states[k].sha256) &&
    registry.states[k].path === `${k}.png`);
}

export class PrototypePortraitStateManager {
  constructor({manifestUrl = './prototype_assets/albedo/prototype_registry.json',
               fetcher = globalThis.fetch?.bind(globalThis),
               container, duration = 240} = {}) {
    this.url = manifestUrl;
    this.fetcher = fetcher;
    this.container = container;
    this.duration = duration;
    this.registry = null;
    this.layers = [];
    this.current = null;
    this.active = 0;
    this.token = 0;
    this.cache = new Map();
    this.events = [];
  }

  async initialize() {
    if (!this.fetcher || !this.container) throw new Error('Preview mount or fetch unavailable');
    const response = await this.fetcher(this.url, {cache: 'no-store'});
    if (!response.ok) throw new Error(`Manifest unavailable: HTTP ${response.status}`);
    const json = await response.json();
    if (!validPrototypeRegistry(json)) throw new Error('Invalid or production-linked prototype registry');
    this.registry = json;
    this.container.classList.add('portrait-preview-surface');
    for (let i = 0; i < 2; i++) {
      const img = document.createElement('img');
      img.className = 'portrait-preview-layer';
      img.alt = '';
      img.draggable = false;
      img.setAttribute('aria-hidden', 'true');
      img.style.opacity = '0';
      this.container.appendChild(img);
      this.layers.push(img);
    }
    return json;
  }

  async load(state) {
    const entry = this.registry?.states?.[state];
    if (!entry || !PROTOTYPE_STATES.includes(state)) throw new Error(`Unknown preview state: ${state}`);
    if (this.cache.has(state)) return this.cache.get(state);
    const imageUrl = new URL(entry.path, new URL(this.url, location.href)).href;
    const res = await this.fetcher(imageUrl, {cache: 'no-store'});
    if (!res.ok) throw new Error(`${state}: PNG HTTP ${res.status}`);
    const blob = await res.blob();
    const bytes = await blob.arrayBuffer();
    const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),
      b => b.toString(16).padStart(2, '0')).join('');
    if (hash !== entry.sha256) throw new Error(`${state}: SHA-256 mismatch`);
    const objectUrl = URL.createObjectURL(blob);
    const image = new Image();
    image.src = objectUrl;
    try { await image.decode(); } catch (err) { URL.revokeObjectURL(objectUrl); throw err; }
    if (image.naturalWidth !== 1536 || image.naturalHeight !== 1920) {
      URL.revokeObjectURL(objectUrl);
      throw new Error(`${state}: invalid canvas`);
    }
    this.cache.set(state, objectUrl);
    return objectUrl;
  }

  async setState(state) {
    if (!this.registry) throw new Error('Call initialize() first');
    if (!PROTOTYPE_STATES.includes(state)) throw new Error(`Unknown prototype state ${state}`);
    const token = ++this.token;
    const source = await this.load(state);
    if (token !== this.token) return false;
    if (state === this.current) return true;
    const next = this.current === null ? this.active : 1 - this.active;
    const front = this.layers[next];
    const back = this.layers[1-next];
    front.style.transition = 'none';
    front.style.opacity = '0';
    front.src = source;
    void front.offsetWidth;
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
    const duration = reduced ? 0 : this.duration;
    front.style.transition = `opacity ${duration}ms ease-in-out`;
    back.style.transition = `opacity ${duration}ms ease-in-out`;
    front.style.opacity = '1';
    back.style.opacity = '0';
    this.active = next;
    this.current = state;
    this.events.push({state, at: new Date().toISOString(), duration});
    if (this.events.length > 20) this.events.shift();
    this.container.setAttribute('aria-label', `Albedo ${this.registry.states[state].label} — prototype preview`);
    this.container.dispatchEvent(new CustomEvent('albedo:preview-state', {detail: {state, entry:this.registry.states[state], duration}}));
    return true;
  }

  clear() {
    ++this.token;
    for (const url of this.cache.values()) URL.revokeObjectURL(url);
    this.cache.clear();
    this.layers.forEach(el => el.remove());
    this.layers = [];
  }
}
