const CACHE_NAME = 'game-wiki-hub-v2-1';
const STATIC_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './version.json',
  './core/core.css',
  './core/app.js',
  './core/hub.js',
  './core/router.js',
  './core/search.js',
  './core/storage.js',
  './core/ui.js',
  './core/icons/icon.svg',
  './core/icons/icon-192.png',
  './core/icons/icon-512.png',
  './games/registry.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('message', (event) => {
  const msg = event.data;
  if (!msg || !msg.type) return;
  if (msg.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  if (msg.type === 'PURGE_AND_RELOAD') {
    event.waitUntil(
      caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k)))).then(async () => {
        const cache = await caches.open(CACHE_NAME);
        await cache.addAll(STATIC_ASSETS).catch(() => {});
        const clients = await self.clients.matchAll({ type: 'window' });
        clients.forEach((client) => client.postMessage({ type: 'RELOAD_NOW' }));
      })
    );
  }
});

function isStaticImage(url) {
  return /\.(svg|png|jpg|jpeg|webp|gif|ico)(\?.*)?$/i.test(url.pathname);
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) {
    // External images (e.g. wiki renders): network first, optional cache fallback
    event.respondWith(
      fetch(req).catch(() => caches.match(req))
    );
    return;
  }

  // Static local icons/portraits: cache-first, falling back to network & caching
  if (isStaticImage(url)) {
    event.respondWith(
      caches.match(req).then((cached) => {
        if (cached) return cached;
        return fetch(req).then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(CACHE_NAME).then((c) => c.put(req, copy));
          }
          return res;
        });
      })
    );
    return;
  }

  // HTML, JS, CSS, JSON databases: network-first so GitHub updates always show immediately when online
  event.respondWith(
    fetch(req, { cache: 'no-cache' })
      .then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req))
  );
});
