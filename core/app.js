import { Router } from './router.js';
import { OmniSearch } from './search.js';
import { makeGameStorage } from './storage.js';
import { applyTheme, escapeHtml, showToast } from './ui.js';
import { renderHub } from './hub.js';

const appEl = document.getElementById('app');
const router = new Router();
const omniSearch = new OmniSearch();

const state = {
  registry: null,
  versionInfo: null,
  loadedModules: new Map(),
  activeSlug: null,
  drawerOpen: false
};

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} loading ${url}`);
  return res.json();
}

async function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return;
  try {
    const reg = await navigator.serviceWorker.register('./sw.js');
    navigator.serviceWorker.addEventListener('message', (event) => {
      if (event.data?.type === 'RELOAD_NOW') {
        window.location.reload();
      }
    });
    if (reg.waiting) {
      reg.waiting.postMessage({ type: 'SKIP_WAITING' });
    }
  } catch {
    // SW registration is optional in non-HTTPS/file contexts
  }
}

async function handleSyncUpdates() {
  try {
    const latest = await fetch(`./version.json?t=${Date.now()}`, { cache: 'no-store' }).then((r) => r.json());
    const currentVer = state.versionInfo?.version;
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({ type: 'PURGE_AND_RELOAD' });
      showToast(`Syncing latest repo data (v${latest.version})...`);
      setTimeout(() => window.location.reload(), 1200);
      return;
    }
    if (currentVer && latest.version !== currentVer) {
      showToast(`New version v${latest.version} found! Reloading...`);
      setTimeout(() => window.location.reload(), 600);
    } else {
      showToast(`Up to date (v${latest.version}). Reloading fresh JSON...`);
      setTimeout(() => window.location.reload(), 500);
    }
  } catch {
    showToast('Offline or unable to reach server right now.', 'warn');
  }
}

function openSearchModal() {
  const existing = document.getElementById('omni-search-modal');
  if (existing) {
    existing.remove();
    return;
  }

  const modal = document.createElement('div');
  modal.id = 'omni-search-modal';
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="search-modal" role="dialog" aria-modal="true">
      <div class="modal-head">
        <input id="omni-input" class="input" style="flex:1;" type="search" placeholder="Search ${escapeHtml(omniSearch.scopeLabel)}: items, enemies, M6-6-3, Minerva, guides..." autofocus />
        <button class="btn btn-ghost btn-sm" id="omni-close">Esc</button>
      </div>
      <div id="omni-results" class="search-results">
        <div class="small muted" style="padding:12px;">Type to search indexed entries across the active wiki...</div>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  const input = modal.querySelector('#omni-input');
  const resultsEl = modal.querySelector('#omni-results');

  const close = () => modal.remove();
  modal.addEventListener('click', (e) => {
    if (e.target === modal || e.target.id === 'omni-close') close();
  });

  function renderHits(term) {
    if (!term.trim()) {
      resultsEl.innerHTML = `<div class="small muted" style="padding:12px;">${omniSearch.entities.length.toLocaleString()} entries indexed. Try "Dark Matter", "Minerva", "M6-6-3", or "Costly Punch".</div>`;
      return;
    }
    const hits = omniSearch.query(term, 40);
    if (!hits.length) {
      resultsEl.innerHTML = `<div class="empty-state">No results for "${escapeHtml(term)}".</div>`;
      return;
    }
    resultsEl.innerHTML = hits
      .map(
        (h, idx) => `
        <button class="search-hit" data-hit-idx="${idx}">
          <div style="min-width:0;">
            <div style="font-weight:600;color:var(--text-primary);">${escapeHtml(h.title)}</div>
            <div class="small muted" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(h.subtitle || '')}</div>
          </div>
          <span class="pill pill-cyan">${escapeHtml(h.typeLabel || h.type)}</span>
        </button>
      `
      )
      .join('');

    resultsEl.querySelectorAll('.search-hit').forEach((btn) => {
      btn.addEventListener('click', () => {
        const hit = hits[Number(btn.dataset.hitIdx)];
        close();
        router.navigate(hit.route);
      });
    });
  }

  renderHits('');
  input.addEventListener('input', () => renderHits(input.value));
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') close();
    if (e.key === 'Enter') {
      const first = resultsEl.querySelector('.search-hit');
      if (first) first.click();
    }
  });
  setTimeout(() => input.focus(), 20);
}

async function loadGameModule(gameMeta) {
  if (state.loadedModules.has(gameMeta.slug)) {
    return state.loadedModules.get(gameMeta.slug);
  }
  const [config, mod] = await Promise.all([
    fetchJson(`./${gameMeta.configPath}`),
    import(`../${gameMeta.modulePath}`)
  ]);
  const storage = makeGameStorage(gameMeta.slug);
  const instance = await mod.createGameModule({
    meta: gameMeta,
    config,
    storage,
    router
  });
  state.loadedModules.set(gameMeta.slug, instance);
  return instance;
}

function renderShell({ route, navInfo, gameInstance }) {
  const isGame = Boolean(gameInstance);
  const title = isGame ? gameInstance.config.title : state.registry.hubTitle;
  const sub = isGame ? gameInstance.config.subtitle : 'Multi-Game Hub';
  const tabs = isGame ? gameInstance.config.tabs || [] : [];
  const activeView = isGame ? route.view || gameInstance.config.defaultView : 'hub';

  const navItemsHtml = isGame
    ? `
      <button class="nav-item" data-nav="#/">
        <span class="nav-left"><span>🏠</span><span>All Games</span></span>
        <span class="nav-badge">Hub</span>
      </button>
      <div style="height:1px;background:var(--border-subtle);margin:6px 4px;"></div>
      ${tabs
        .map(
          (t) => `
          <button class="nav-item ${activeView === t.id ? 'active' : ''}" data-nav="#/game/${escapeHtml(gameInstance.meta.slug)}/${escapeHtml(t.id)}">
            <span class="nav-left"><span>${escapeHtml(t.icon || '•')}</span><span>${escapeHtml(t.label)}</span></span>
            ${t.badge ? `<span class="nav-badge">${escapeHtml(t.badge)}</span>` : ''}
          </button>
        `
        )
        .join('')}
    `
    : `
      <button class="nav-item active" data-nav="#/">
        <span class="nav-left"><span>🎮</span><span>Game Library</span></span>
        <span class="nav-badge">${state.registry.games.length}</span>
      </button>
      ${state.registry.games
        .map(
          (g) => `
          <button class="nav-item" data-nav="#/game/${escapeHtml(g.slug)}">
            <span class="nav-left"><span>⚡</span><span>${escapeHtml(g.title)}</span></span>
          </button>
        `
        )
        .join('')}
    `;

  appEl.innerHTML = `
    <div class="layout">
      <div class="drawer-backdrop ${state.drawerOpen ? 'open' : ''}" id="drawer-backdrop"></div>
      <aside class="sidebar ${state.drawerOpen ? 'open' : ''}" id="sidebar">
        <div class="sidebar-brand">
          <div>
            <div class="brand-sub">${escapeHtml(sub)}</div>
            <div class="brand-title">${escapeHtml(title)}</div>
          </div>
          <button class="btn btn-ghost btn-sm mobile-menu-btn" id="drawer-close" aria-label="Close Menu">✕</button>
        </div>
        <nav class="sidebar-nav">${navItemsHtml}</nav>
        <div class="sidebar-footer">
          <button class="btn btn-sm" id="sidebar-sync-btn" style="width:100%;">⟳ Sync GitHub Updates</button>
          <div style="display:flex;justify-content:space-between;">
            <span>v${escapeHtml(state.versionInfo?.version || '1.0.0')}</span>
            <span>Offline PWA</span>
          </div>
        </div>
      </aside>

      <div class="main-area">
        <header class="topbar">
          <div class="topbar-left">
            <button class="btn btn-icon mobile-menu-btn" id="drawer-open" aria-label="Open Menu">☰</button>
            <button class="btn btn-icon" id="nav-back" ${navInfo.canGoBack ? '' : 'disabled'} title="Back">←</button>
            <button class="btn btn-icon" id="nav-fwd" ${navInfo.canGoForward ? '' : 'disabled'} title="Forward">→</button>
            <span class="small muted" id="crumb-label" style="margin-left:4px;display:none;"></span>
          </div>
          <div class="topbar-right">
            <button class="search-trigger" id="omni-btn">
              <span>🔍 Search ${isGame ? 'wiki...' : 'hub...'}</span>
              <span class="kbd">Ctrl K</span>
            </button>
          </div>
        </header>
        <main class="page-content" id="page-content"></main>
      </div>
    </div>
  `;

  const setDrawer = (open) => {
    state.drawerOpen = open;
    appEl.querySelector('#sidebar')?.classList.toggle('open', open);
    appEl.querySelector('#drawer-backdrop')?.classList.toggle('open', open);
  };

  appEl.querySelector('#drawer-open')?.addEventListener('click', () => setDrawer(true));
  appEl.querySelector('#drawer-close')?.addEventListener('click', () => setDrawer(false));
  appEl.querySelector('#drawer-backdrop')?.addEventListener('click', () => setDrawer(false));
  appEl.querySelector('#nav-back')?.addEventListener('click', () => router.back());
  appEl.querySelector('#nav-fwd')?.addEventListener('click', () => router.forward());
  appEl.querySelector('#omni-btn')?.addEventListener('click', openSearchModal);
  appEl.querySelector('#sidebar-sync-btn')?.addEventListener('click', handleSyncUpdates);

  appEl.querySelectorAll('[data-nav]').forEach((btn) => {
    btn.addEventListener('click', () => {
      state.drawerOpen = false;
      router.navigate(btn.dataset.nav);
    });
  });

  return appEl.querySelector('#page-content');
}

async function handleRoute(route, navInfo) {
  try {
    if (route.type === 'hub') {
      state.activeSlug = null;
      applyTheme();
      omniSearch.clear('Hub');
      omniSearch.registerEntities(
        state.registry.games.map((g) => ({
          id: g.id,
          type: 'game',
          typeLabel: 'Game',
          title: g.title,
          subtitle: g.subtitle,
          keywords: (g.tags || []).join(' '),
          route: `#/game/${g.slug}`
        }))
      );
      const container = renderShell({ route, navInfo, gameInstance: null });
      await renderHub({
        container,
        registry: state.registry,
        router,
        versionInfo: state.versionInfo,
        onSyncUpdates: handleSyncUpdates
      });
      return;
    }

    const gameMeta = state.registry.games.find((g) => g.slug === route.slug);
    if (!gameMeta) {
      router.navigate('#/');
      return;
    }

    const gameInstance = await loadGameModule(gameMeta);
    applyTheme(gameInstance.config.theme);

    if (state.activeSlug !== gameMeta.slug) {
      state.activeSlug = gameMeta.slug;
      omniSearch.clear(gameInstance.config.title);
      omniSearch.registerEntities(gameInstance.getSearchEntities());
    }

    const viewId = route.view || gameInstance.config.defaultView;
    const container = renderShell({ route: { ...route, view: viewId }, navInfo, gameInstance });
    await gameInstance.renderView({
      container,
      viewId,
      entityId: route.entityId
    });
  } catch (err) {
    console.error(err);
    appEl.innerHTML = `
      <div class="page-content">
        <div class="alert alert-danger">
          <strong>Error loading route:</strong> ${escapeHtml(err.message)}
          <div style="margin-top:10px;"><a href="#/" class="btn btn-sm">Return to Game Hub</a></div>
        </div>
      </div>
    `;
  }
}

async function boot() {
  await registerServiceWorker();
  const [registry, versionInfo] = await Promise.all([
    fetchJson('./games/registry.json'),
    fetchJson('./version.json').catch(() => ({ version: '1.0.0' }))
  ]);
  state.registry = registry;
  state.versionInfo = versionInfo;

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      openSearchModal();
    } else if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
      e.preventDefault();
      openSearchModal();
    }
  });

  router.onChange(handleRoute);
  router.init();
}

boot();
