import { Router } from './router.js';
import { OmniSearch } from './search.js';
import { makeGameStorage } from './storage.js';
import { applyTheme, escapeHtml, icon, showToast } from './ui.js';
import { renderHub } from './hub.js';

const appEl = document.getElementById('app');
const router = new Router();
const omniSearch = new OmniSearch();

const state = {
  registry: null,
  versionInfo: null,
  loadedModules: new Map(),
  activeSlug: null,
  activeGameInstance: null,
  activeRoute: null,
  drawerOpen: false,
  trailOpen: false,
  shellMounted: false
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

  const recentEntries = router
    .getTrailEntries()
    .filter((e) => !e.isCurrent && e.label && e.hash)
    .reverse()
    .slice(0, 6);

  const modal = document.createElement('div');
  modal.id = 'omni-search-modal';
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="search-modal" role="dialog" aria-modal="true" aria-label="Command Palette">
      <div class="modal-head">
        <span class="muted" style="display:inline-flex;">${icon('search', 16)}</span>
        <input id="omni-input" class="input" style="flex:1;border:none;background:transparent;box-shadow:none;padding:4px 6px;" type="search" placeholder="Search ${escapeHtml(omniSearch.scopeLabel)}: items, enemies, M6-6-3, Minerva, guides..." autofocus />
        <button class="btn btn-ghost btn-sm" id="omni-close">Esc</button>
      </div>
      <div id="omni-results" class="search-results"></div>
      <div class="search-footer">
        <span>↑↓ Navigate · Enter Open · Esc Close</span>
        <span class="mono">${omniSearch.entities.length.toLocaleString()} indexed</span>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  const input = modal.querySelector('#omni-input');
  const resultsEl = modal.querySelector('#omni-results');
  let activeHits = [];
  let selectedIdx = 0;

  const close = () => modal.remove();
  modal.addEventListener('click', (e) => {
    if (e.target === modal || e.target.closest('#omni-close')) close();
  });

  function updateSelectionHighlight() {
    resultsEl.querySelectorAll('.search-hit').forEach((btn, idx) => {
      const isSel = idx === selectedIdx;
      btn.classList.toggle('is-selected', isSel);
      if (isSel) btn.scrollIntoView({ block: 'nearest' });
    });
  }

  function renderHits(term) {
    const clean = term.trim();
    if (!clean) {
      activeHits = recentEntries.map((e) => ({
        title: e.label,
        subtitle: e.hash,
        typeLabel: e.typeLabel || 'Recent',
        route: e.hash
      }));
      selectedIdx = 0;

      if (!activeHits.length) {
        resultsEl.innerHTML = `<div class="small muted" style="padding:14px;">${omniSearch.entities.length.toLocaleString()} entries indexed. Try "Dark Matter", "Minerva", "M6-6-3", or "Costly Punch".</div>`;
        return;
      }

      resultsEl.innerHTML = `
        <div class="search-section-label">Recently Visited</div>
        ${activeHits
          .map(
            (h, idx) => `
            <button class="search-hit ${idx === 0 ? 'is-selected' : ''}" data-hit-idx="${idx}">
              <div style="min-width:0;">
                <div style="font-weight:600;color:var(--text-primary);">${escapeHtml(h.title)}</div>
                <div class="small muted mono" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(h.subtitle)}</div>
              </div>
              <span class="pill pill-cyan">${escapeHtml(h.typeLabel)}</span>
            </button>
          `
          )
          .join('')}
      `;
    } else {
      activeHits = omniSearch.query(clean, 40);
      selectedIdx = 0;
      if (!activeHits.length) {
        resultsEl.innerHTML = `<div class="empty-state">No results for "${escapeHtml(term)}".</div>`;
        return;
      }
      resultsEl.innerHTML = activeHits
        .map(
          (h, idx) => `
          <button class="search-hit ${idx === 0 ? 'is-selected' : ''}" data-hit-idx="${idx}">
            <div style="min-width:0;">
              <div style="font-weight:600;color:var(--text-primary);">${escapeHtml(h.title)}</div>
              <div class="small muted" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(h.subtitle || '')}</div>
            </div>
            <span class="pill pill-cyan">${escapeHtml(h.typeLabel || h.type)}</span>
          </button>
        `
        )
        .join('');
    }

    resultsEl.querySelectorAll('.search-hit').forEach((btn) => {
      btn.addEventListener('click', () => {
        const hit = activeHits[Number(btn.dataset.hitIdx)];
        if (!hit) return;
        close();
        router.navigate(hit.route);
      });
    });
  }

  renderHits('');
  input.addEventListener('input', () => renderHits(input.value));
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      close();
      return;
    }
    if (e.key === 'ArrowDown' && activeHits.length) {
      e.preventDefault();
      selectedIdx = (selectedIdx + 1) % activeHits.length;
      updateSelectionHighlight();
    } else if (e.key === 'ArrowUp' && activeHits.length) {
      e.preventDefault();
      selectedIdx = (selectedIdx - 1 + activeHits.length) % activeHits.length;
      updateSelectionHighlight();
    } else if (e.key === 'Enter' && activeHits.length) {
      e.preventDefault();
      const hit = activeHits[selectedIdx] || activeHits[0];
      if (hit) {
        close();
        router.navigate(hit.route);
      }
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

function setDrawer(open) {
  state.drawerOpen = open;
  appEl.querySelector('#sidebar')?.classList.toggle('open', open);
  appEl.querySelector('#drawer-backdrop')?.classList.toggle('open', open);
}

function setTrailOpen(open) {
  state.trailOpen = open;
  appEl.querySelector('#trail-popover')?.classList.toggle('open', open);
}

function ensureShellMounted() {
  if (state.shellMounted && appEl.querySelector('#page-content')) return;

  appEl.innerHTML = `
    <div class="layout">
      <div class="drawer-backdrop" id="drawer-backdrop"></div>
      <aside class="sidebar" id="sidebar">
        <div class="sidebar-brand" id="sidebar-brand"></div>
        <div class="sidebar-zack-wrap" id="sidebar-zack" hidden></div>
        <nav class="sidebar-nav" id="sidebar-nav"></nav>
        <div class="sidebar-footer">
          <button class="btn btn-sm" id="sidebar-sync-btn" style="width:100%;">
            ${icon('refresh', 14)}
            <span>Sync GitHub Updates</span>
          </button>
          <div style="display:flex;justify-content:space-between;">
            <span id="sidebar-version" class="mono">v1.0.0</span>
            <span>Offline PWA</span>
          </div>
        </div>
      </aside>

      <div class="main-area">
        <header class="topbar">
          <div class="topbar-left">
            <button class="btn btn-icon mobile-menu-btn" id="drawer-open" aria-label="Open Menu">${icon('menu', 17)}</button>
            <div class="nav-history-group">
              <button class="btn btn-icon" id="nav-back" title="Back" aria-label="Back">${icon('chevron-left', 16)}</button>
              <button class="btn btn-icon" id="nav-fwd" title="Forward" aria-label="Forward">${icon('chevron-right', 16)}</button>
              <div class="trail-popover-wrap">
                <button class="btn btn-icon" id="nav-trail-btn" title="Recent History Trail" aria-label="History Trail">${icon('clock', 15)}</button>
                <div class="trail-popover" id="trail-popover" role="menu"></div>
              </div>
            </div>
            <nav class="breadcrumbs" id="breadcrumbs" aria-label="Breadcrumb"></nav>
          </div>
          <div class="topbar-right">
            <button class="search-trigger" id="omni-btn">
              <span class="search-trigger-left">
                ${icon('search', 14)}
                <span class="search-trigger-text" id="omni-btn-label">Search wiki...</span>
              </span>
              <span class="kbd">Ctrl K</span>
            </button>
          </div>
        </header>
        <main class="page-content" id="page-content"></main>
        <div id="mobile-bottom-nav-slot"></div>
      </div>
    </div>
  `;

  appEl.querySelector('#drawer-open')?.addEventListener('click', () => setDrawer(true));
  appEl.querySelector('#drawer-backdrop')?.addEventListener('click', () => setDrawer(false));
  appEl.querySelector('#nav-back')?.addEventListener('click', () => router.back());
  appEl.querySelector('#nav-fwd')?.addEventListener('click', () => router.forward());
  appEl.querySelector('#omni-btn')?.addEventListener('click', openSearchModal);
  appEl.querySelector('#sidebar-sync-btn')?.addEventListener('click', handleSyncUpdates);

  appEl.querySelector('#nav-trail-btn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    setTrailOpen(!state.trailOpen);
  });

  appEl.addEventListener('click', (e) => {
    const navBtn = e.target.closest('[data-nav]');
    if (navBtn) {
      setDrawer(false);
      setTrailOpen(false);
      router.navigate(navBtn.dataset.nav);
      return;
    }
    const trailBtn = e.target.closest('[data-trail-idx]');
    if (trailBtn) {
      const idx = Number(trailBtn.dataset.trailIdx);
      setTrailOpen(false);
      router.goToIndex(idx);
      return;
    }
    if (e.target.closest('#drawer-close')) {
      setDrawer(false);
      return;
    }
    if (e.target.closest('#mbn-more')) {
      setDrawer(true);
    }
  });

  document.addEventListener('click', (e) => {
    if (state.trailOpen && !e.target.closest('.trail-popover-wrap')) {
      setTrailOpen(false);
    }
  });

  state.shellMounted = true;
}

function renderSidebarZackStatus(gameInstance) {
  const zackWrap = appEl.querySelector('#sidebar-zack');
  if (!zackWrap) return;
  if (!gameInstance || typeof gameInstance.getSidebarStatus !== 'function') {
    zackWrap.hidden = true;
    zackWrap.innerHTML = '';
    return;
  }
  const st = gameInstance.getSidebarStatus();
  const pct = st.missionsTotal ? Math.round((st.missionsDone / st.missionsTotal) * 100) : 0;
  zackWrap.hidden = false;
  zackWrap.innerHTML = `
    <a class="sidebar-zack-card" href="#/game/${escapeHtml(gameInstance.meta.slug)}/suggester" title="Adjust Zack Level & Chapter">
      <div class="sidebar-zack-top">
        <span>Zack Fair</span>
        <span class="mono" style="color:var(--accent);">Lv.${st.level} · Ch.${st.chapter}</span>
      </div>
      <div class="progress-track" style="height:5px;">
        <div class="progress-fill" style="width:${pct}%"></div>
      </div>
      <div class="sidebar-zack-meta">
        <span>Missions Cleared</span>
        <span class="mono">${st.missionsDone}/${st.missionsTotal}</span>
      </div>
    </a>
  `;
}

function renderBreadcrumbs(breadcrumbs, fallbackTitle) {
  const crumbsEl = appEl.querySelector('#breadcrumbs');
  if (!crumbsEl) return;
  const list = Array.isArray(breadcrumbs) && breadcrumbs.length
    ? breadcrumbs
    : [{ label: fallbackTitle || 'Wiki', route: null }];

  crumbsEl.innerHTML = list
    .map((c, idx) => {
      const isLast = idx === list.length - 1;
      const sep = idx > 0 ? `<span class="crumb-sep">${icon('chevron-right', 13)}</span>` : '';
      if (isLast || !c.route) {
        return `${sep}<span class="crumb-current" title="${escapeHtml(c.label)}">${escapeHtml(c.label)}</span>`;
      }
      return `${sep}<a class="crumb-link" href="${escapeHtml(c.route)}" title="${escapeHtml(c.label)}">${escapeHtml(c.label)}</a>`;
    })
    .join('');
}

function renderTrailPopover(navInfo) {
  const pop = appEl.querySelector('#trail-popover');
  const trailBtn = appEl.querySelector('#nav-trail-btn');
  if (!pop || !trailBtn) return;

  const entries = (navInfo?.trail || []).slice().reverse().slice(0, 12);
  trailBtn.disabled = entries.length <= 1;

  if (!entries.length) {
    pop.innerHTML = '<div class="small muted" style="padding:8px;">No navigation history yet.</div>';
    return;
  }

  pop.innerHTML = `
    <div class="trail-popover-head">Recent Trail (${entries.length})</div>
    ${entries
      .map(
        (e) => `
        <button type="button" class="trail-item ${e.isCurrent ? 'current' : ''}" data-trail-idx="${e.historyIndex}">
          <span class="trail-item-title">${escapeHtml(e.label || e.hash)}</span>
          ${e.typeLabel ? `<span class="pill" style="font-size:0.68rem;padding:1px 6px;">${escapeHtml(e.typeLabel)}</span>` : ''}
        </button>
      `
      )
      .join('')}
  `;
}

function updateTopbarMeta({ routeMeta, navInfo, gameInstance }) {
  const backBtn = appEl.querySelector('#nav-back');
  const fwdBtn = appEl.querySelector('#nav-fwd');
  if (backBtn) {
    backBtn.disabled = !navInfo.canGoBack;
    backBtn.title = navInfo.previousEntry?.label ? `Back to ${navInfo.previousEntry.label}` : 'Back';
  }
  if (fwdBtn) {
    fwdBtn.disabled = !navInfo.canGoForward;
    fwdBtn.title = navInfo.nextEntry?.label ? `Forward to ${navInfo.nextEntry.label}` : 'Forward';
  }

  renderBreadcrumbs(routeMeta?.breadcrumbs, routeMeta?.title);
  renderTrailPopover(navInfo);

  const siteTitle = gameInstance ? gameInstance.config.title : (state.registry?.hubTitle || 'Game Wiki Hub');
  if (routeMeta?.title) {
    document.title = `${routeMeta.title} · ${siteTitle}`;
  } else {
    document.title = siteTitle;
  }
}

function updateShell({ route, navInfo, gameInstance, routeMeta }) {
  ensureShellMounted();

  const isGame = Boolean(gameInstance);
  const title = isGame ? gameInstance.config.title : state.registry.hubTitle;
  const sub = isGame ? gameInstance.config.subtitle : 'Multi-Game Hub';
  const tabs = isGame ? gameInstance.config.tabs || [] : [];
  const activeView = isGame ? route.view || gameInstance.config.defaultView : 'hub';

  const brandEl = appEl.querySelector('#sidebar-brand');
  if (brandEl) {
    brandEl.innerHTML = `
      <div style="min-width:0;">
        <div class="brand-sub">${escapeHtml(sub)}</div>
        <div class="brand-title">${escapeHtml(title)}</div>
      </div>
      <button class="btn btn-ghost btn-sm mobile-menu-btn" id="drawer-close" aria-label="Close Menu">${icon('x', 16)}</button>
    `;
  }

  renderSidebarZackStatus(gameInstance);

  const navEl = appEl.querySelector('#sidebar-nav');
  if (navEl) {
    if (isGame) {
      let groupsHtml = '';
      const hasGroups = tabs.some((t) => Boolean(t.group));
      if (hasGroups) {
        const grouped = new Map();
        for (const t of tabs) {
          const gName = t.group || 'Sections';
          if (!grouped.has(gName)) grouped.set(gName, []);
          grouped.get(gName).push(t);
        }
        for (const [gName, gTabs] of grouped.entries()) {
          groupsHtml += `<div class="nav-group-label">${escapeHtml(gName)}</div>`;
          groupsHtml += gTabs
            .map(
              (t) => `
              <button class="nav-item ${activeView === t.id ? 'active' : ''}" data-nav="#/game/${escapeHtml(gameInstance.meta.slug)}/${escapeHtml(t.id)}">
                <span class="nav-left">${icon(t.iconName || 'layers', 15)}<span>${escapeHtml(t.label)}</span></span>
                ${t.badge ? `<span class="nav-badge">${escapeHtml(t.badge)}</span>` : ''}
              </button>
            `
            )
            .join('');
        }
      } else {
        groupsHtml = tabs
          .map(
            (t) => `
            <button class="nav-item ${activeView === t.id ? 'active' : ''}" data-nav="#/game/${escapeHtml(gameInstance.meta.slug)}/${escapeHtml(t.id)}">
              <span class="nav-left">${icon(t.iconName || 'layers', 15)}<span>${escapeHtml(t.label)}</span></span>
              ${t.badge ? `<span class="nav-badge">${escapeHtml(t.badge)}</span>` : ''}
            </button>
          `
          )
          .join('');
      }

      navEl.innerHTML = `
        <button class="nav-item" data-nav="#/">
          <span class="nav-left">${icon('home', 15)}<span>All Games</span></span>
          <span class="nav-badge">Hub</span>
        </button>
        <div class="nav-divider"></div>
        ${groupsHtml}
      `;
    } else {
      navEl.innerHTML = `
        <div class="nav-group-label">Library</div>
        <button class="nav-item active" data-nav="#/">
          <span class="nav-left">${icon('gamepad', 15)}<span>Game Library</span></span>
          <span class="nav-badge">${state.registry.games.length}</span>
        </button>
        <div class="nav-group-label">Installed Wikis</div>
        ${state.registry.games
          .map(
            (g) => `
            <button class="nav-item" data-nav="#/game/${escapeHtml(g.slug)}">
              <span class="nav-left">${icon('book-open', 15)}<span>${escapeHtml(g.title)}</span></span>
            </button>
          `
          )
          .join('')}
      `;
    }
  }

  const verEl = appEl.querySelector('#sidebar-version');
  if (verEl) verEl.textContent = `v${state.versionInfo?.version || '1.0.0'}`;

  const searchLabel = appEl.querySelector('#omni-btn-label');
  if (searchLabel) searchLabel.textContent = isGame ? 'Search wiki...' : 'Search hub...';

  const mbnSlot = appEl.querySelector('#mobile-bottom-nav-slot');
  if (mbnSlot) {
    mbnSlot.innerHTML = isGame
      ? `
        <nav class="mobile-bottom-nav" aria-label="Quick Navigation">
          <button class="mbn-btn ${activeView === 'missions' ? 'active' : ''}" data-nav="#/game/${escapeHtml(gameInstance.meta.slug)}/missions">${icon('target', 18)}<span>Missions</span></button>
          <button class="mbn-btn ${activeView === 'items' ? 'active' : ''}" data-nav="#/game/${escapeHtml(gameInstance.meta.slug)}/items">${icon('flask', 18)}<span>Items</span></button>
          <button class="mbn-btn ${activeView === 'enemies' ? 'active' : ''}" data-nav="#/game/${escapeHtml(gameInstance.meta.slug)}/enemies">${icon('skull', 18)}<span>Bestiary</span></button>
          <button class="mbn-btn ${activeView === 'guides' ? 'active' : ''}" data-nav="#/game/${escapeHtml(gameInstance.meta.slug)}/guides">${icon('book-open', 18)}<span>Guides</span></button>
          <button class="mbn-btn" id="mbn-more">${icon('menu', 18)}<span>More</span></button>
        </nav>
      `
      : '';
  }

  updateTopbarMeta({ routeMeta, navInfo, gameInstance });
  setDrawer(false);
  setTrailOpen(false);
  return appEl.querySelector('#page-content');
}

async function handleRoute(route, navInfo) {
  try {
    state.activeRoute = route;

    if (route.type === 'hub') {
      state.activeSlug = null;
      state.activeGameInstance = null;
      applyTheme();
      omniSearch.clear('Hub');
      omniSearch.registerEntities([
        ...state.registry.games.map((g) => ({
          id: g.id,
          type: 'game',
          typeLabel: 'Game',
          title: g.title,
          subtitle: g.subtitle,
          keywords: `${(g.tags || []).join(' ')} ${g.description || ''}`,
          route: `#/game/${g.slug}`
        })),
        ...state.registry.games.flatMap((g) => [
          {
            id: `${g.id}_missions`,
            type: 'shortcut',
            typeLabel: 'Missions + Boss Guides',
            title: `${g.title}: Missions & Boss Kill Guides`,
            subtitle: 'All 300 missions with Hard Mode boss kill strategies',
            keywords: 'missions boss kill guide how to kill minerva',
            route: `#/game/${g.slug}/missions`
          },
          {
            id: `${g.id}_enemies`,
            type: 'shortcut',
            typeLabel: 'Bestiary',
            title: `${g.title}: Enemy Bestiary`,
            subtitle: '365 enemies, weaknesses, stats, and 4-slot loot tables',
            keywords: 'enemies bestiary bosses drops steals',
            route: `#/game/${g.slug}/enemies`
          },
          {
            id: `${g.id}_items`,
            type: 'shortcut',
            typeLabel: 'Items',
            title: `${g.title}: Item & Materia Database`,
            subtitle: 'Items, accessories, materia, shops & live drop matrix',
            keywords: 'items materia accessories fusion shops',
            route: `#/game/${g.slug}/items`
          },
          {
            id: `${g.id}_guides`,
            type: 'shortcut',
            typeLabel: 'Guides',
            title: `${g.title}: Farming & Stat-Leveling Guides`,
            subtitle: 'Playbooks, all 8 stat-leveling pipelines, and meta builds',
            keywords: 'farming exp sp gil dmw stat leveling guides',
            route: `#/game/${g.slug}/guides`
          }
        ])
      ]);

      const routeMeta = {
        title: 'Game Library',
        typeLabel: 'Hub',
        breadcrumbs: [{ label: 'Game Library', route: '#/' }]
      };
      router.setCurrentMeta({ label: routeMeta.title, typeLabel: routeMeta.typeLabel, breadcrumbs: routeMeta.breadcrumbs });
      const latestNav = { ...navInfo, trail: router.getTrailEntries() };
      const container = updateShell({ route, navInfo: latestNav, gameInstance: null, routeMeta });

      container.classList.remove('page-enter');
      void container.offsetWidth;
      container.classList.add('page-enter');

      await renderHub({
        container,
        registry: state.registry,
        router,
        versionInfo: state.versionInfo,
        onSyncUpdates: handleSyncUpdates
      });

      if (navInfo.isRestoring) {
        requestAnimationFrame(() => window.scrollTo({ top: navInfo.restoreScrollY || 0, behavior: 'instant' }));
      } else {
        window.scrollTo({ top: 0, behavior: 'instant' });
      }
      return;
    }

    const gameMeta = state.registry.games.find((g) => g.slug === route.slug);
    if (!gameMeta) {
      router.navigate('#/');
      return;
    }

    const gameInstance = await loadGameModule(gameMeta);
    state.activeGameInstance = gameInstance;
    applyTheme(gameInstance.config.theme);

    if (state.activeSlug !== gameMeta.slug) {
      state.activeSlug = gameMeta.slug;
      omniSearch.clear(gameInstance.config.title);
      omniSearch.registerEntities(gameInstance.getSearchEntities());
    }

    const viewId = route.view || gameInstance.config.defaultView;
    const routeMeta = typeof gameInstance.resolveRouteMeta === 'function'
      ? gameInstance.resolveRouteMeta(viewId, route.entityId)
      : {
          title: gameInstance.config.tabs?.find((t) => t.id === viewId)?.label || viewId,
          typeLabel: 'Page',
          breadcrumbs: [
            { label: gameInstance.config.title, route: `#/game/${gameMeta.slug}` },
            { label: viewId, route: null }
          ]
        };

    router.setCurrentMeta({
      label: routeMeta.title,
      typeLabel: routeMeta.typeLabel,
      breadcrumbs: routeMeta.breadcrumbs
    });

    const latestNav = { ...navInfo, trail: router.getTrailEntries() };
    const container = updateShell({
      route: { ...route, view: viewId },
      navInfo: latestNav,
      gameInstance,
      routeMeta
    });

    container.classList.remove('page-enter');
    void container.offsetWidth;
    container.classList.add('page-enter');

    await gameInstance.renderView({
      container,
      viewId,
      entityId: route.entityId
    });

    if (navInfo.isRestoring) {
      requestAnimationFrame(() => window.scrollTo({ top: navInfo.restoreScrollY || 0, behavior: 'instant' }));
    } else {
      window.scrollTo({ top: 0, behavior: 'instant' });
    }
  } catch (err) {
    console.error(err);
    state.shellMounted = false;
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

  router.onMetaChange((entry, navInfo) => {
    if (!state.shellMounted) return;
    updateTopbarMeta({
      routeMeta: {
        title: entry?.label || '',
        breadcrumbs: entry?.breadcrumbs || null
      },
      navInfo,
      gameInstance: state.activeGameInstance
    });
  });

  window.addEventListener('wiki:zack-updated', () => {
    if (state.shellMounted && state.activeGameInstance) {
      renderSidebarZackStatus(state.activeGameInstance);
    }
  });

  router.onChange(handleRoute);
  router.init();
}

boot();
