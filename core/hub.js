import { escapeHtml, showToast } from './ui.js';
import { makeGameStorage, exportAllWikiData, importAllWikiData } from './storage.js';

/**
 * Renders the Game Library Hub (#/) displaying all games in games/registry.json,
 * live localStorage progress, Phone PWA Install & GitHub Sync controls, and Add-Game reference.
 */
export async function renderHub({ container, registry, router, versionInfo, onSyncUpdates }) {
  const games = registry.games || [];

  const cardsHtml = await Promise.all(
    games.map(async (g) => {
      const store = makeGameStorage(g.slug);
      let cfg = null;
      let statsSummary = { indexed: '—', completedCount: 0, totalChecklist: 0, missionsDone: 0, missionsTotal: 300 };
      try {
        const res = await fetch(`./${g.configPath}`);
        if (res.ok) cfg = await res.json();
      } catch {
        // ignore config preview failure
      }

      const checklistState = store.get('checklist', {});
      const completedMissions = store.get('completedMissions', {});
      const checklistItems = cfg?.checklistItems || [];
      const chkDone = checklistItems.filter((item) => checklistState[item.id]).length;
      const mDone = Object.values(completedMissions).filter(Boolean).length;
      const zackLevel = store.get('zackLevel', 1);

      statsSummary = {
        chkDone,
        chkTotal: checklistItems.length,
        mDone,
        zackLevel
      };

      const pct = statsSummary.chkTotal
        ? Math.round((statsSummary.chkDone / statsSummary.chkTotal) * 100)
        : 0;

      const tagsHtml = (g.tags || [])
        .map((t) => `<span class="pill pill-cyan">${escapeHtml(t)}</span>`)
        .join('');

      return `
        <article class="game-card card-glow">
          <img class="game-cover" src="./${escapeHtml(g.coverArt)}" alt="${escapeHtml(g.title)}" />
          <div class="game-card-body">
            <div>
              <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:4px;">
                <span class="pill pill-mako">${escapeHtml(g.edition || 'Wiki Module')}</span>
                <span class="small muted mono">${escapeHtml(g.theme?.name || 'Custom Theme')}</span>
              </div>
              <h2 style="margin:4px 0 2px;font-size:1.18rem;">${escapeHtml(g.title)}</h2>
              <div class="small muted">${escapeHtml(g.subtitle || '')}</div>
            </div>

            <div class="chip-row" style="margin:0;">${tagsHtml}</div>

            <div class="card" style="background:var(--bg-secondary);padding:10px 12px;">
              <div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:6px;">
                <span>Checklist Progress</span>
                <strong class="mono">${statsSummary.chkDone}/${statsSummary.chkTotal} (${pct}%)</strong>
              </div>
              <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
              <div style="display:flex;justify-content:space-between;font-size:0.78rem;margin-top:8px;" class="muted">
                <span>Missions Cleared: <strong style="color:var(--text-primary)">${statsSummary.mDone}/300</strong></span>
                <span>Tracked Lv: <strong style="color:var(--accent)">${statsSummary.zackLevel}</strong></span>
              </div>
            </div>

            <div style="display:flex;gap:8px;margin-top:auto;">
              <button class="btn btn-primary" style="flex:1;" data-launch-slug="${escapeHtml(g.slug)}">
                Launch Compendium →
              </button>
            </div>
          </div>
        </article>
      `;
    })
  );

  container.innerHTML = `
    <div class="section-header">
      <div>
        <div class="brand-sub">Modular Offline-Ready Library</div>
        <h1>${escapeHtml(registry.hubTitle || 'Personal Game Wiki Hub')}</h1>
        <p class="muted" style="margin:4px 0 0;">${escapeHtml(registry.hubSubtitle || 'Self-contained interactive wikis powered by static JSON & localStorage.')}</p>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
        <span class="pill pill-mako mono">v${escapeHtml(versionInfo?.version || '1.0.0')}</span>
        <button class="btn btn-primary btn-sm" id="hub-sync-btn">⟳ Check GitHub Updates</button>
        <button class="btn btn-sm" id="hub-export-btn">⬇ Backup Saves</button>
        <label class="btn btn-sm" style="cursor:pointer;">
          ⬆ Restore Saves
          <input type="file" id="hub-import-input" accept="application/json" hidden />
        </label>
      </div>
    </div>

    <div class="grid-auto" style="margin-bottom:24px;">
      ${cardsHtml.join('')}
    </div>

    <div class="grid-2">
      <section class="card">
        <h3 style="margin-top:0;">📱 Install & Update on Your Phone</h3>
        <p class="small muted">This hub is a Progressive Web App (PWA) designed to run directly from GitHub Pages. Your checklists, Zack level, and 6+4 builds stay safely in your phone's <code>localStorage</code>.</p>
        <ul class="small" style="padding-left:18px;margin:8px 0;">
          <li><strong>iPhone / iPad (Safari):</strong> Open the GitHub Pages URL → tap <strong>Share</strong> → <strong>Add to Home Screen</strong>.</li>
          <li><strong>Android (Chrome):</strong> Open the GitHub Pages URL → tap <strong>⋮ Menu</strong> → <strong>Install App / Add to Home Screen</strong>.</li>
          <li><strong>Easy Updates:</strong> Edit any HTML or <code>data/*.json</code> file in the GitHub repo and push. When online, tapping <strong>Check GitHub Updates</strong> pulls the latest databases immediately.</li>
        </ul>
      </section>

      <section class="card">
        <h3 style="margin-top:0;">🧩 How to Add a New Game</h3>
        <p class="small muted">Adding a new game never touches the core engine. Drop a folder and register it:</p>
        <pre class="small mono" style="background:var(--bg-secondary);padding:10px;border-radius:8px;overflow-x:auto;border:1px solid var(--border-subtle);margin:0;">1. Create folder: games/&lt;game-slug&gt;/
   ├── config.json   (theme + tabs)
   ├── module.js     (registers search + views)
   ├── data/*.json   (normalized tables)
   └── views/*.js    (custom views)
2. Add entry in: games/registry.json
3. Push to GitHub → live on your phone!</pre>
      </section>
    </div>
  `;

  container.querySelectorAll('[data-launch-slug]').forEach((btn) => {
    btn.addEventListener('click', () => {
      router.navigate(`#/game/${btn.dataset.launchSlug}`);
    });
  });

  container.querySelector('#hub-sync-btn')?.addEventListener('click', onSyncUpdates);

  container.querySelector('#hub-export-btn')?.addEventListener('click', () => {
    const dump = exportAllWikiData();
    const blob = new Blob([JSON.stringify(dump, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `game-wiki-backup-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Exported all saved checklists & builds!');
  });

  container.querySelector('#hub-import-input')?.addEventListener('change', async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const count = importAllWikiData(JSON.parse(text));
      showToast(`Restored ${count} saved storage entries!`);
      renderHub({ container, registry, router, versionInfo, onSyncUpdates });
    } catch (err) {
      showToast(`Restore failed: ${err.message}`, 'danger');
    }
  });
}
