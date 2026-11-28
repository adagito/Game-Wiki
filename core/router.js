/**
 * Hash-based router synchronized with native browser history, human-readable trail labels,
 * and automatic per-entry scroll position restoration.
 * Routes:
 *   #/
 *   #/game/<slug>
 *   #/game/<slug>/<view>
 *   #/game/<slug>/<view>/<id>
 */
export class Router {
  constructor() {
    this.trail = [];
    this.index = -1;
    this._seq = 0;
    this._historyStateSupported = true;
    this._transitioning = false;
    this.listeners = new Set();
    this.metaListeners = new Set();

    window.addEventListener(
      'scroll',
      () => {
        if (this._transitioning || this.index < 0 || !this.trail[this.index]) return;
        this.trail[this.index].scrollY = window.scrollY || 0;
      },
      { passive: true }
    );

    window.addEventListener('hashchange', () => {
      this._transitioning = true;
      const hash = this.currentHash();
      const navId = window.history.state?.wikiNavId;
      let foundIdx = -1;

      if (typeof navId === 'number') {
        foundIdx = this.trail.findIndex((e) => e.id === navId);
      }

      if (foundIdx === -1 && !this._historyStateSupported) {
        if (this.index > 0 && this.trail[this.index - 1]?.hash === hash) {
          foundIdx = this.index - 1;
        } else if (this.index >= 0 && this.trail[this.index + 1]?.hash === hash) {
          foundIdx = this.index + 1;
        }
      }

      let isRestoring = false;
      let restoreScrollY = 0;

      if (foundIdx >= 0) {
        this.index = foundIdx;
        isRestoring = true;
        restoreScrollY = this.trail[this.index]?.scrollY || 0;
      } else {
        this.trail = this.trail.slice(0, this.index + 1);
        const newId = ++this._seq;
        this.trail.push({ id: newId, hash, label: '', typeLabel: '', breadcrumbs: null, scrollY: 0 });
        this.index = this.trail.length - 1;
        this._tryReplaceState({ ...(window.history.state || {}), wikiNavId: newId }, window.location.href);
      }

      this._emit(isRestoring, restoreScrollY);
      requestAnimationFrame(() => {
        this._transitioning = false;
      });
    });
  }

  _tryReplaceState(stateObj, url) {
    if (!this._historyStateSupported) return;
    try {
      window.history.replaceState(stateObj, '', url);
    } catch {
      this._historyStateSupported = false;
    }
  }

  init() {
    const hash = this.currentHash();
    this._seq = 1;
    this.trail = [{ id: 1, hash, label: '', typeLabel: '', breadcrumbs: null, scrollY: 0 }];
    this.index = 0;
    this._tryReplaceState({ ...(window.history.state || {}), wikiNavId: 1 }, window.location.href);
    this._emit(false, 0);
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
    if (this.index >= 0 && this.trail[this.index]) {
      this.trail[this.index].scrollY = window.scrollY || 0;
    }
    if (normalized === this.currentHash()) {
      this._emit(false, window.scrollY || 0);
      return;
    }
    window.location.hash = normalized;
  }

  setCurrentMeta(meta = {}) {
    if (this.index < 0 || !this.trail[this.index]) return;
    const entry = this.trail[this.index];
    if (meta.label !== undefined) entry.label = meta.label;
    if (meta.typeLabel !== undefined) entry.typeLabel = meta.typeLabel;
    if (meta.breadcrumbs !== undefined) entry.breadcrumbs = meta.breadcrumbs;
    this._emitMeta();
  }

  replaceCurrent(hash, meta = null) {
    const normalized = hash.startsWith('#') ? hash : `#${hash}`;
    if (this.index < 0 || !this.trail[this.index]) return;
    const entry = this.trail[this.index];
    entry.hash = normalized;
    if (meta) {
      if (meta.label !== undefined) entry.label = meta.label;
      if (meta.typeLabel !== undefined) entry.typeLabel = meta.typeLabel;
      if (meta.breadcrumbs !== undefined) entry.breadcrumbs = meta.breadcrumbs;
    }
    if (this._historyStateSupported) {
      this._tryReplaceState({ ...(window.history.state || {}), wikiNavId: entry.id }, normalized);
    }
    this._emitMeta();
  }

  getPreviousEntry() {
    return this.index > 0 ? this.trail[this.index - 1] : null;
  }

  getNextEntry() {
    return this.index >= 0 && this.index < this.trail.length - 1 ? this.trail[this.index + 1] : null;
  }

  getTrailEntries() {
    return this.trail.map((e, i) => ({
      ...e,
      historyIndex: i,
      isCurrent: i === this.index
    }));
  }

  canGoBack() {
    return this.index > 0;
  }

  canGoForward() {
    return this.index >= 0 && this.index < this.trail.length - 1;
  }

  back() {
    if (!this.canGoBack()) return;
    if (this.trail[this.index]) {
      this.trail[this.index].scrollY = window.scrollY || 0;
    }
    if (this._historyStateSupported) {
      window.history.back();
    } else {
      this.index -= 1;
      window.location.hash = this.trail[this.index].hash;
    }
  }

  forward() {
    if (!this.canGoForward()) return;
    if (this.trail[this.index]) {
      this.trail[this.index].scrollY = window.scrollY || 0;
    }
    if (this._historyStateSupported) {
      window.history.forward();
    } else {
      this.index += 1;
      window.location.hash = this.trail[this.index].hash;
    }
  }

  goToIndex(targetIdx) {
    if (targetIdx < 0 || targetIdx >= this.trail.length || targetIdx === this.index) return;
    if (this.trail[this.index]) {
      this.trail[this.index].scrollY = window.scrollY || 0;
    }
    const delta = targetIdx - this.index;
    if (this._historyStateSupported) {
      window.history.go(delta);
    } else {
      this.index = targetIdx;
      window.location.hash = this.trail[targetIdx].hash;
    }
  }

  onChange(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  onMetaChange(fn) {
    this.metaListeners.add(fn);
    return () => this.metaListeners.delete(fn);
  }

  _buildNavInfo(isRestoring = false, restoreScrollY = 0) {
    return {
      canGoBack: this.canGoBack(),
      canGoForward: this.canGoForward(),
      previousEntry: this.getPreviousEntry(),
      nextEntry: this.getNextEntry(),
      trail: this.getTrailEntries(),
      currentIndex: this.index,
      isRestoring,
      restoreScrollY
    };
  }

  _emitMeta() {
    const entry = this.index >= 0 ? this.trail[this.index] : null;
    const navInfo = this._buildNavInfo(false, 0);
    for (const fn of this.metaListeners) {
      fn(entry, navInfo);
    }
  }

  _emit(isRestoring = false, restoreScrollY = 0) {
    const route = this.parse();
    const navInfo = this._buildNavInfo(isRestoring, restoreScrollY);
    for (const fn of this.listeners) {
      fn(route, navInfo);
    }
  }
}
