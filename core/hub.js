import { escapeHtml, formatNum, icon, showToast } from './ui.js';
import { makeGameStorage, exportAllWikiData, importAllWikiData } from './storage.js';

function evaluateReadiness(mission, zackLevel) {
  const rec = mission?.hardModeBenchmarks?.recommendedLevel || 1;
  const diff = zackLevel - rec;
  if (diff >= 0) return { key: 'ready', label: 'Ready', tone: 'pill-mako' };
  if (diff >= -8) return { key: 'stretch', label: 'Stretch', tone: 'pill-warn' };
  return { key: 'danger', label: 'Danger', tone: 'pill-danger' };
}

function getStorageTelemetry() {
  let wikiKeys = 0;
  let totalBytes = 0;
  try {
    for (let i = 0; i < window.localStorage.length; i++) {
      const k = window.localStorage.key(i);
      if (k && k.startsWith('wiki:')) {
        wikiKeys++;
        const v = window.localStorage.getItem(k) || '';
        totalBytes += k.length + v.length;
      }
    }
  } catch {
    // ignore storage access issues
  }
  return { wikiKeys, kb: (totalBytes / 1024).toFixed(1) };
}

async function fetchOptionalJson(url, fallback) {
  try {
    const res = await fetch(url);
    return res.ok ? await res.json() : fallback;
  } catch {
    return fallback;
  }
}

/**
 * Renders the Game Library Hub (#/) displaying all games in games/registry.json,
 * live aggregated database telemetry, boss-hunt readiness, missables/milestones,
 * Phone PWA Install & GitHub Sync controls, and Add-Game reference.
 */
export async function renderHub({ container, registry, router, versionInfo, onSyncUpdates }) {
  const games = registry.games || [];

  const enrichedGames = await Promise.all(
    games.map(async (g) => {
      const store = makeGameStorage(g.slug);
      const dataBase = g.dataPath ? `./${g.dataPath}` : null;

      const [cfg, missions, enemies, items, shops, guides, extra] = await Promise.all([
        fetchOptionalJson(`./${g.configPath}`, null),
        dataBase ? fetchOptionalJson(`${dataBase}/missions.json`, []) : Promise.resolve([]),
        dataBase ? fetchOptionalJson(`${dataBase}/enemies.json`, []) : Promise.resolve([]),
        dataBase ? fetchOptionalJson(`${dataBase}/items.json`, []) : Promise.resolve([]),
        dataBase ? fetchOptionalJson(`${dataBase}/shops.json`, []) : Promise.resolve([]),
        dataBase ? fetchOptionalJson(`${dataBase}/guides.json`, {}) : Promise.resolve({}),
        dataBase ? fetchOptionalJson(`${dataBase}/compendium-extra.json`, {}) : Promise.resolve({})
      ]);

      const checklistState = store.get('checklist', {});
      const completedMissions = store.get('completedMissions', {});
      const unlockedShops = store.get('unlockedShops', { shop_shinra_shop: true });
      const dmwDone = store.get('dmwDone', {});
      const missablesDone = store.get('missablesDone', {});
      const trophiesDone = store.get('trophiesDone', {});
      const mailDone = store.get('mailDone', {});
      const storyDone = store.get('storyDone', {});
      const zackLevel = Number(store.get('zackLevel', 25)) || 25;
      const zackChapter = Number(store.get('zackChapter', 4)) || 4;
      const bs = store.get('busterProficiency', { guard: 0, strong: 0, command: 0, barrier: 0 });
      const bsTotal = Math.min(
        100,
        (Number(bs.guard) || 0) + (Number(bs.strong) || 0) + (Number(bs.command) || 0) + (Number(bs.barrier) || 0)
      );

      const checklistItems = cfg?.checklistItems || [];
      const chkDone = checklistItems.filter((item) => checklistState[item.id]).length;
      const mTotal = missions.length || 300;
      const mDone = missions.length
        ? missions.filter((m) => completedMissions[m.id]).length
        : Object.values(completedMissions).filter(Boolean).length;
      const bossGuideCount = missions.filter((m) => Boolean(m.bossGuide)).length;

      const dmwImages = guides?.dmwImages || [];
      const missables = guides?.missablesByChapter || [];
      const playbooks = guides?.farmingPlaybooks || [];
      const statGuides = guides?.statLevelingGuides || [];
      const guideSections = guides?.sections || [];
      const trophies = extra?.trophies || [];
      const mailSenders = extra?.mailSenders || [];
      const storyChapters = extra?.storyChapters || [];
      const minigames = extra?.minigames || [];

      const shopsDone = shops.filter((s) => unlockedShops[s.id]).length;
      const dmwCount = dmwImages.filter((d) => dmwDone[d.id]).length;
      const missCount = missables.filter((m) => missablesDone[m.id]).length;
      const trophyCount = trophies.filter((t) => trophiesDone[t.id]).length;
      const mailCount = mailSenders.filter((ms) => mailDone[ms.id]).length;
      const storyCount = storyChapters.filter((sc) => storyDone[sc.id]).length;

      const starTiers = [
        { label: '1–3★', min: 1, max: 3 },
        { label: '4–6★', min: 4, max: 6 },
        { label: '7–8★', min: 7, max: 8 },
        { label: '9–10★', min: 9, max: 10 }
      ].map((t) => {
        const subset = missions.filter((m) => m.stars >= t.min && m.stars <= t.max);
        const cleared = subset.filter((m) => completedMissions[m.id]).length;
        return { label: t.label, cleared, total: subset.length };
      });

      const indexedTotal =
        missions.length +
        enemies.length +
        items.length +
        shops.length +
        dmwImages.length +
        playbooks.length +
        statGuides.length +
        guideSections.length +
        trophies.length +
        mailSenders.length +
        storyChapters.length +
        minigames.length;

      return {
        meta: g,
        cfg,
        missions,
        enemies,
        items,
        shops,
        guides,
        extra,
        progress: {
          chkDone,
          chkTotal: checklistItems.length,
          mDone,
          mTotal,
          bossGuideCount,
          zackLevel,
          zackChapter,
          bsTotal,
          shopsDone,
          shopsTotal: shops.length,
          dmwCount,
          dmwTotal: dmwImages.length,
          missCount,
          missTotal: missables.length,
          trophyCount,
          trophyTotal: trophies.length,
          mailCount,
          mailTotal: mailSenders.length,
          storyCount,
          storyTotal: storyChapters.length,
          starTiers,
          checklistState,
          completedMissions,
          missablesDone
        },
        indexedTotal
      };
    })
  );

  const totalIndexedAll = enrichedGames.reduce((acc, g) => acc + g.indexedTotal, 0);
  const totalBossGuidesAll = enrichedGames.reduce((acc, g) => acc + g.progress.bossGuideCount, 0);
  const totalMissionsAll = enrichedGames.reduce((acc, g) => acc + g.progress.mTotal, 0);
  const primaryGame = enrichedGames[0] || null;
  const primaryPct = primaryGame
    ? Math.round(
        ((primaryGame.progress.mDone + primaryGame.progress.chkDone) /
          Math.max(1, primaryGame.progress.mTotal + primaryGame.progress.chkTotal)) *
          100
      )
    : 0;
  const storageTel = getStorageTelemetry();

  const cardsHtml = enrichedGames
    .map(({ meta: g, cfg, enemies, items, shops, guides, progress }) => {
      const mPct = progress.mTotal ? Math.round((progress.mDone / progress.mTotal) * 100) : 0;
      const chkPct = progress.chkTotal ? Math.round((progress.chkDone / progress.chkTotal) * 100) : 0;
      const tagsHtml = (g.tags || [])
        .map((t) => `<span class="pill pill-cyan">${escapeHtml(t)}</span>`)
        .join('');
      const tabs = cfg?.tabs || [];

      const dbCounts = [
        `${progress.mTotal} Missions`,
        `${progress.bossGuideCount} Boss Guides`,
        `${enemies.length} Enemies`,
        `${items.length} Items`,
        `${shops.length} Shops`,
        `${(guides?.dmwImages || []).length} DMW`,
        `${(guides?.farmingPlaybooks || []).length} Playbooks`,
        `${(guides?.statLevelingGuides || []).length} Stat Guides`
      ];

      return `
        <article class="game-card card-glow">
          <img class="game-cover" src="./${escapeHtml(g.coverArt)}" alt="${escapeHtml(g.title)}" />
          <div class="game-card-body">
            <div>
              <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:4px;flex-wrap:wrap;">
                <span class="pill pill-mako">${escapeHtml(g.edition || 'Wiki Module')}</span>
                <span class="small muted mono">${escapeHtml(g.theme?.name || 'Custom Theme')}</span>
              </div>
              <h2 style="margin:4px 0 2px;font-size:1.22rem;">${escapeHtml(g.title)}</h2>
              <div class="small muted">${escapeHtml(g.subtitle || '')}</div>
              ${g.description ? `<p class="small muted" style="margin:8px 0 0;">${escapeHtml(g.description)}</p>` : ''}
            </div>

            <div class="chip-row" style="margin:0;">${tagsHtml}</div>

            <div class="sub-panel" style="padding:10px 12px;">
              <div class="small muted" style="margin-bottom:6px;font-weight:600;">Indexed Compendium Datasets</div>
              <div style="display:flex;flex-wrap:wrap;gap:5px;">
                ${dbCounts.map((c) => `<span class="pill mono">${escapeHtml(c)}</span>`).join('')}
              </div>
            </div>

            <div class="card" style="background:var(--bg-secondary);padding:12px;">
              <div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:5px;">
                <span>Missions & Boss Guides Cleared</span>
                <strong class="mono">${progress.mDone}/${progress.mTotal} (${mPct}%)</strong>
              </div>
              <div class="progress-track" style="margin-bottom:10px;"><div class="progress-fill" style="width:${mPct}%"></div></div>

              <div class="hub-tier-row" style="margin-bottom:10px;">
                ${progress.starTiers
                  .map(
                    (t) => `<span class="pill mono" style="font-size:0.72rem;">${escapeHtml(t.label)}: ${t.cleared}/${t.total}</span>`
                  )
                  .join('')}
              </div>

              <div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:5px;">
                <span>Key Milestones Checklist</span>
                <strong class="mono">${progress.chkDone}/${progress.chkTotal} (${chkPct}%)</strong>
              </div>
              <div class="progress-track"><div class="progress-fill" style="width:${chkPct}%"></div></div>

              <div style="display:flex;flex-wrap:wrap;gap:10px;justify-content:space-between;font-size:0.78rem;margin-top:10px;" class="muted">
                ${progress.trophyTotal ? `<span>Trophies: <strong style="color:var(--text-primary)">${progress.trophyCount}/${progress.trophyTotal}</strong></span>` : ''}
                ${progress.storyTotal ? `<span>Story: <strong style="color:var(--text-primary)">${progress.storyCount}/${progress.storyTotal}</strong></span>` : ''}
                ${progress.mailTotal ? `<span>Mail: <strong style="color:var(--text-primary)">${progress.mailCount}/${progress.mailTotal}</strong></span>` : ''}
                <span>Shops: <strong style="color:var(--text-primary)">${progress.shopsDone}/${progress.shopsTotal}</strong></span>
                <span>DMW: <strong style="color:var(--text-primary)">${progress.dmwCount}/${progress.dmwTotal}</strong></span>
                <span>Missables: <strong style="color:var(--text-primary)">${progress.missCount}/${progress.missTotal}</strong></span>
                <span>Buster Sword: <strong style="color:var(--accent-secondary)">${progress.bsTotal}%</strong></span>
                <span>Tracked: <strong style="color:var(--accent)">Lv.${progress.zackLevel} · Ch.${progress.zackChapter}</strong></span>
              </div>
            </div>

            ${
              tabs.length
                ? `
              <div>
                <div class="small muted" style="margin-bottom:6px;">Quick Jump to Compendium Sections</div>
                <div class="hub-quick-grid">
                  ${tabs
                    .map(
                      (t) => `
                    <a class="pill pill-link" href="#/game/${escapeHtml(g.slug)}/${escapeHtml(t.id)}">
                      ${icon(t.iconName || 'layers', 13)}
                      <span>${escapeHtml(t.label)}</span>
                    </a>
                  `
                    )
                    .join('')}
                </div>
              </div>
            `
                : ''
            }

            <div style="display:flex;gap:8px;margin-top:auto;">
              <button class="btn btn-primary" style="flex:1;" data-launch-slug="${escapeHtml(g.slug)}">
                Launch Compendium →
              </button>
            </div>
          </div>
        </article>
      `;
    })
    .join('');

  // Build Live Command Dashboard for the primary game
  let commandDashboardHtml = '';
  if (primaryGame && primaryGame.missions.length) {
    const slug = primaryGame.meta.slug;
    const { zackLevel, zackChapter, completedMissions, checklistState, missablesDone } = primaryGame.progress;
    const missionById = new Map(primaryGame.missions.map((m) => [m.id, m]));
    const enemyById = new Map(primaryGame.enemies.map((e) => [e.id, e]));

    // 1. Recommended Next Missions & Boss Previews
    const nextMissions = primaryGame.missions
      .filter((m) => !completedMissions[m.id] && m.chapterAvailable <= zackChapter)
      .map((m) => ({
        mission: m,
        ready: evaluateReadiness(m, zackLevel),
        delta: Math.abs((m.hardModeBenchmarks?.recommendedLevel || 1) - zackLevel)
      }))
      .filter((x) => x.ready.key !== 'danger')
      .sort((a, b) => a.delta - b.delta || a.mission.stars - b.mission.stars)
      .slice(0, 4);

    // 2. Iconic Boss Hunts & Hard Mode Readiness
    const landmarkBossIds = ['M5-1-1', 'M5-1-2', 'M3-2-6', 'M5-2-1', 'M5-1-4', 'M9-6-5', 'M9-6-6'];
    const landmarkRows = landmarkBossIds
      .map((mid) => missionById.get(mid))
      .filter(Boolean)
      .map((m) => {
        const bg = m.bossGuide;
        const primaryEid = bg?.targetEnemyIds?.[0];
        const en = primaryEid ? enemyById.get(primaryEid) : null;
        const ready = evaluateReadiness(m, zackLevel);
        const done = Boolean(completedMissions[m.id]);
        return { m, bg, en, ready, done };
      });

    // 3. Missables Watch
    const allMissables = primaryGame.guides?.missablesByChapter || [];
    const pendingMissables = allMissables
      .filter((ms) => !missablesDone[ms.id])
      .slice(0, 6);

    // 4. Next Unchecked Milestones
    const pendingMilestones = (primaryGame.cfg?.checklistItems || [])
      .filter((it) => !checklistState[it.id])
      .slice(0, 6);

    commandDashboardHtml = `
      <div class="grid-2" style="margin-bottom:20px;">
        <section class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap;">
            <div>
              <div class="brand-sub">Live For Zack Lv.${zackLevel} · Ch.${zackChapter}</div>
              <h3 style="margin:2px 0 0;">Next Missions & Boss Previews</h3>
            </div>
            <a class="btn btn-sm" href="#/game/${escapeHtml(slug)}/suggester">Full Planner →</a>
          </div>
          <div style="display:flex;flex-direction:column;gap:8px;">
            ${
              nextMissions.length
                ? nextMissions
                    .map(
                      ({ mission: m, ready }) => `
                  <a class="hub-mission-card" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(m.id)}">
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">
                      <strong class="mono" style="color:var(--accent);">${escapeHtml(m.id)} · ${escapeHtml(m.title)}</strong>
                      <span class="pill ${ready.tone}">${m.stars}★ · ${ready.label}</span>
                    </div>
                    <div class="small" style="color:var(--text-primary);margin-top:3px;">
                      <strong>Boss:</strong> ${escapeHtml(m.bossGuide?.targetName || 'Target')} · <span class="muted">${escapeHtml(m.bossGuide?.encounterType || '')}</span>
                    </div>
                    <div class="small muted" style="margin-top:2px;">${escapeHtml(m.bossGuide?.summary || '')}</div>
                  </a>
                `
                    )
                    .join('')
                : `<div class="empty-state small">All Ready/Stretch missions up to Chapter ${zackChapter} are cleared! Advance story chapter in Route Suggester.</div>`
            }
          </div>
        </section>

        <section class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap;">
            <div>
              <div class="brand-sub">Hard Mode Benchmark Radar</div>
              <h3 style="margin:2px 0 0;">Major Boss Hunts (${primaryGame.progress.bossGuideCount} Guides)</h3>
            </div>
            <a class="btn btn-sm" href="#/game/${escapeHtml(slug)}/missions">All 300 Missions →</a>
          </div>
          <div class="hub-boss-list">
            ${landmarkRows
              .map(
                ({ m, bg, en, ready, done }) => `
              <a class="hub-boss-row" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(m.id)}">
                <div style="min-width:0;">
                  <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                    <span class="mono small" style="color:var(--accent-secondary);font-weight:700;">${escapeHtml(m.id)}</span>
                    <strong style="color:var(--text-primary);">${escapeHtml(bg?.targetName || m.title)}</strong>
                    ${done ? '<span class="pill pill-mako">✓ Cleared</span>' : ''}
                  </div>
                  <div class="small muted mono">
                    Rec Lv.${m.hardModeBenchmarks?.recommendedLevel} · Hard HP ${formatNum(en?.stats?.hpHard)}
                  </div>
                </div>
                <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
                  <span class="pill ${ready.tone}">${m.stars}★ · ${ready.label}</span>
                  <span class="small" style="color:var(--accent);">Kill Guide →</span>
                </div>
              </a>
            `
              )
              .join('')}
          </div>
        </section>
      </div>

      <div class="grid-2" style="margin-bottom:20px;">
        <section class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap;">
            <h3 style="margin:0;">Missables Watch (${primaryGame.progress.missCount}/${primaryGame.progress.missTotal} Done)</h3>
            <a class="btn btn-sm" href="#/game/${escapeHtml(slug)}/compendium/missables">All Missables →</a>
          </div>
          ${
            zackChapter <= 7
              ? `<div class="alert alert-danger small" style="margin-bottom:10px;"><strong>Point of No Return:</strong> Leaving Midgar at the end of <strong>Chapter 7</strong> permanently locks Midgar NPC missions, Fan Clubs & mail!</div>`
              : ''
          }
          <div style="display:flex;flex-direction:column;gap:7px;">
            ${
              pendingMissables.length
                ? pendingMissables
                    .map(
                      (ms) => `
                  <div class="sub-panel" style="padding:9px 11px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:3px;">
                      <strong class="small">${escapeHtml(ms.title)}</strong>
                      <span class="pill pill-warn mono">${escapeHtml(ms.chapter)}</span>
                    </div>
                    <div class="small muted">${escapeHtml(ms.detail)}</div>
                  </div>
                `
                    )
                    .join('')
                : '<div class="alert alert-mako small">All tracked missables checked off!</div>'
            }
          </div>
        </section>

        <section class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap;">
            <h3 style="margin:0;">Next Key Milestones (${primaryGame.progress.chkDone}/${primaryGame.progress.chkTotal})</h3>
            <a class="btn btn-sm" href="#/game/${escapeHtml(slug)}/fusion-tracker">Full Tracker →</a>
          </div>
          <div style="display:flex;flex-direction:column;gap:7px;">
            ${
              pendingMilestones.length
                ? pendingMilestones
                    .map(
                      (it) => `
                  <div class="sub-panel" style="padding:9px 11px;display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">
                    <div style="min-width:0;flex:1;">
                      <div class="small muted">${escapeHtml(it.group)}</div>
                      <div class="small" style="font-weight:600;">${escapeHtml(it.label)}</div>
                    </div>
                    ${
                      it.missionId
                        ? `<a class="pill pill-link pill-mako mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(it.missionId)}">${escapeHtml(it.missionId)} →</a>`
                        : `<a class="pill pill-link pill-cyan" href="#/game/${escapeHtml(slug)}/compendium/missables">Story / DMW</a>`
                    }
                  </div>
                `
                    )
                    .join('')
                : '<div class="alert alert-mako small">All key Hard Mode milestones completed!</div>'
            }
          </div>
        </section>
      </div>
    `;
  }

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

    <div class="grid-4" style="margin-bottom:20px;">
      <div class="stat-tile">
        <div class="stat-tile-label">Active Compendiums</div>
        <div class="stat-tile-val mono" style="color:var(--accent);">${enrichedGames.length} Game · v${escapeHtml(versionInfo?.version || '1.0.0')}</div>
        <div class="small muted">Offline-first PWA ready</div>
      </div>
      <div class="stat-tile">
        <div class="stat-tile-label">Indexed Knowledge Base</div>
        <div class="stat-tile-val mono" style="color:var(--accent-secondary);">${totalIndexedAll.toLocaleString()} Entries</div>
        <div class="small muted">Missions, Bestiary, Items, Shops, Guides</div>
      </div>
      <div class="stat-tile">
        <div class="stat-tile-label">Mission Boss Kill Guides</div>
        <div class="stat-tile-val mono" style="color:var(--accent);">${totalBossGuidesAll} / ${totalMissionsAll}</div>
        <div class="small muted">100% mission boss tactics covered</div>
      </div>
      <div class="stat-tile">
        <div class="stat-tile-label">Your Saved Progress</div>
        <div class="stat-tile-val mono">${primaryPct}% Overall</div>
        <div class="small muted">${primaryGame ? `Lv.${primaryGame.progress.zackLevel} · Ch.${primaryGame.progress.zackChapter} · ${storageTel.wikiKeys} keys (${storageTel.kb} KB)` : 'No local data yet'}</div>
      </div>
    </div>

    <div class="grid-auto" style="margin-bottom:20px;">
      ${cardsHtml}
    </div>

    ${commandDashboardHtml}

    <div class="grid-3">
      <section class="card">
        <h3 style="margin-top:0;">📦 Hub Build & Release Info</h3>
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;">
          <span class="pill pill-mako mono">Version v${escapeHtml(versionInfo?.version || '1.0.0')}</span>
          ${versionInfo?.buildDate ? `<span class="pill mono">${escapeHtml(versionInfo.buildDate.slice(0, 10))}</span>` : ''}
        </div>
        <p class="small muted" style="margin:0 0 8px;">${escapeHtml(versionInfo?.notes || 'Latest static compendium build.')}</p>
        <div class="sub-panel small">
          <strong>Local Save Health:</strong> <span class="mono">${storageTel.wikiKeys}</span> saved keys (<span class="mono">${storageTel.kb} KB</span> in browser <code>localStorage</code>). Use <strong>Backup Saves</strong> above to export JSON anytime.
        </div>
      </section>

      <section class="card">
        <h3 style="margin-top:0;">📱 Install & Update on Your Phone</h3>
        <p class="small muted">This hub is a Progressive Web App (PWA) designed to run directly from GitHub Pages. Your checklists, Zack level, and 6+4 builds stay safely in your phone's <code>localStorage</code>.</p>
        <ul class="small" style="padding-left:18px;margin:8px 0 0;">
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
