/**
 * Namespaced localStorage manager: `wiki:<game-slug>:<key>`
 * Keeps each game module's checklists, mission completions, builds, and notes isolated.
 */
const PREFIX = 'wiki';

export function makeGameStorage(slug) {
  const ns = `${PREFIX}:${slug}:`;
  return {
    get(key, fallback = null) {
      try {
        const raw = window.localStorage.getItem(ns + key);
        return raw === null ? fallback : JSON.parse(raw);
      } catch {
        return fallback;
      }
    },
    set(key, value) {
      try {
        window.localStorage.setItem(ns + key, JSON.stringify(value));
        return true;
      } catch {
        return false;
      }
    },
    remove(key) {
      try {
        window.localStorage.removeItem(ns + key);
      } catch {
        // ignore storage quota/privacy errors
      }
    },
    keys() {
      const out = [];
      for (let i = 0; i < window.localStorage.length; i++) {
        const k = window.localStorage.key(i);
        if (k && k.startsWith(ns)) out.push(k.slice(ns.length));
      }
      return out;
    }
  };
}

export function exportAllWikiData() {
  const dump = { exportedAt: new Date().toISOString(), prefix: PREFIX, entries: {} };
  for (let i = 0; i < window.localStorage.length; i++) {
    const k = window.localStorage.key(i);
    if (k && k.startsWith(`${PREFIX}:`)) {
      try {
        dump.entries[k] = JSON.parse(window.localStorage.getItem(k));
      } catch {
        dump.entries[k] = window.localStorage.getItem(k);
      }
    }
  }
  return dump;
}

export function importAllWikiData(dump) {
  if (!dump || typeof dump !== 'object' || !dump.entries || typeof dump.entries !== 'object') {
    throw new Error('Invalid backup JSON format');
  }
  let count = 0;
  for (const [k, v] of Object.entries(dump.entries)) {
    if (k.startsWith(`${PREFIX}:`)) {
      window.localStorage.setItem(k, JSON.stringify(v));
      count++;
    }
  }
  return count;
}
