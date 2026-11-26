/**
 * Hash-based router with Back / Forward navigation history across views & entities.
 * Routes:
 *   #/
 *   #/game/<slug>
 *   #/game/<slug>/<view>
 *   #/game/<slug>/<view>/<id>
 */
export class Router {
  constructor() {
    this.history = [];
    this.index = -1;
    this.listeners = new Set();
    this._suppressPush = false;

    window.addEventListener('hashchange', () => {
      const hash = this.currentHash();
      if (this._suppressPush) {
        this._suppressPush = false;
      } else if (this.history[this.index] !== hash) {
        this.history = this.history.slice(0, this.index + 1);
        this.history.push(hash);
        this.index = this.history.length - 1;
      }
      this._emit();
    });
  }

  init() {
    const hash = this.currentHash();
    this.history = [hash];
    this.index = 0;
    this._emit();
  }

  currentHash() {
    const raw = window.location.hash || '#/';
    return raw.startsWith('#') ? raw : `#${raw}`;
  }

  parse(hash = this.currentHash()) {
    const clean = hash.replace(/^#\/?/, '');
    if (!clean) {
      return { type: 'hub', hash: '#/' };
    }
    const parts = clean.split('/').filter(Boolean).map((p) => decodeURIComponent(p));
    if (parts[0] === 'game' && parts[1]) {
      return {
        type: 'game',
        slug: parts[1],
        view: parts[2] || null,
        entityId: parts.slice(3).join('/') || null,
        hash
      };
    }
    return { type: 'hub', hash: '#/' };
  }

  navigate(hash) {
    const normalized = hash.startsWith('#') ? hash : `#${hash}`;
    if (normalized === this.currentHash()) {
      this._emit();
      return;
    }
    window.location.hash = normalized;
  }

  canGoBack() {
    return this.index > 0;
  }

  canGoForward() {
    return this.index >= 0 && this.index < this.history.length - 1;
  }

  back() {
    if (!this.canGoBack()) return;
    this.index -= 1;
    this._suppressPush = true;
    window.location.hash = this.history[this.index];
  }

  forward() {
    if (!this.canGoForward()) return;
    this.index += 1;
    this._suppressPush = true;
    window.location.hash = this.history[this.index];
  }

  onChange(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  _emit() {
    const route = this.parse();
    for (const fn of this.listeners) {
      fn(route, {
        canGoBack: this.canGoBack(),
        canGoForward: this.canGoForward()
      });
    }
  }
}
