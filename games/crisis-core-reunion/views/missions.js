import {
  escapeHtml,
  formatNum,
  icon,
  openLightbox,
  renderDossierNavBar,
  renderSortableTable,
  wireDossierNavBar
} from '../../../core/ui.js';

export function renderMissionsView(container, ctx, selectedMissionId = null) {
  if (selectedMissionId && ctx.indexes.missionById.has(selectedMissionId)) {
    renderMissionDossier(container, ctx, ctx.indexes.missionById.get(selectedMissionId));
    return;
  }

  const zack = ctx.getZackState();
  const branches = ['ALL', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'M10'];

  if (!ctx.viewState.missions) {
    ctx.viewState.missions = {
      activeBranch: 'ALL',
      starFilter: 'all',
      chapterFilter: 'all',
      readinessFilter: 'all',
      statusFilter: 'all',
      search: '',
      filtersOpen: false,
      sortKey: null,
      sortDir: 'asc'
    };
  }
  const vs = ctx.viewState.missions;

  const doneCount = Object.values(zack.completedMissions).filter(Boolean).length;

  container.innerHTML = `
    <div class="section-header">
      <div>
        <div class="brand-sub">Hard Mode Tactical Index</div>
        <h1>Missions Explorer (All 300)</h1>
        <p class="muted small" style="margin:4px 0 0;">Readiness badges evaluate against Zack Lv. <strong>${zack.level}</strong> · Ch. <strong>${zack.chapter}</strong> (use "Unlockable Now" to see next playable chains).</p>
      </div>
      <div style="display:flex;gap:8px;align-items:center;">
        <span class="pill pill-mako mono" id="missions-progress-pill">${doneCount} / ${ctx.data.missions.length} Cleared</span>
      </div>
    </div>

    <div class="chip-row" id="mission-branches">
      ${branches.map((b) => `<button class="chip ${b === vs.activeBranch ? 'active' : ''}" data-branch="${b}">${b === 'ALL' ? 'All (300)' : b}</button>`).join('')}
    </div>

    <div class="filter-bar ${vs.filtersOpen ? 'filters-open' : ''}" id="mission-filter-bar">
      <div class="filter-main-row">
        <input type="search" id="mission-search" class="input" style="flex:1;min-width:140px;" value="${escapeHtml(vs.search)}" placeholder="Search M6-6-3, boss, reward..." />
        <button type="button" class="btn btn-sm filter-toggle-btn ${vs.filtersOpen ? 'btn-primary' : ''}" id="mission-filter-toggle">
          ${icon('sliders', 14)}
          <span>Filters</span>
          <span class="pill pill-mako mono" id="mission-filter-badge" style="padding:0 6px;font-size:0.7rem;" hidden>0</span>
        </button>
        <span class="small muted mono" id="mission-count"></span>
      </div>
      <div class="filter-extras">
        <select id="mission-stars" class="select">
          <option value="all" ${vs.starFilter === 'all' ? 'selected' : ''}>All Stars (1–10★)</option>
          ${Array.from({ length: 10 }, (_, i) => `<option value="${i + 1}" ${String(i + 1) === vs.starFilter ? 'selected' : ''}>${i + 1}★</option>`).join('')}
        </select>
        <select id="mission-chapter" class="select">
          <option value="all" ${vs.chapterFilter === 'all' ? 'selected' : ''}>Any Chapter</option>
          ${Array.from({ length: 10 }, (_, i) => `<option value="${i + 1}" ${String(i + 1) === vs.chapterFilter ? 'selected' : ''}>Ch. ${i + 1}+</option>`).join('')}
        </select>
        <select id="mission-readiness" class="select">
          <option value="all" ${vs.readinessFilter === 'all' ? 'selected' : ''}>All Readiness</option>
          <option value="ready" ${vs.readinessFilter === 'ready' ? 'selected' : ''}>Ready Now</option>
          <option value="stretch" ${vs.readinessFilter === 'stretch' ? 'selected' : ''}>Stretch</option>
          <option value="danger" ${vs.readinessFilter === 'danger' ? 'selected' : ''}>Danger</option>
        </select>
        <select id="mission-status" class="select">
          <option value="all" ${vs.statusFilter === 'all' ? 'selected' : ''}>All Status</option>
          <option value="unlockable" ${vs.statusFilter === 'unlockable' ? 'selected' : ''}>Unlockable Now</option>
          <option value="todo" ${vs.statusFilter === 'todo' ? 'selected' : ''}>Incomplete Only</option>
          <option value="done" ${vs.statusFilter === 'done' ? 'selected' : ''}>Cleared Only</option>
        </select>
        <button type="button" class="btn btn-ghost btn-sm" id="mission-reset" hidden>${icon('filter-x', 14)} Reset</button>
      </div>
    </div>

    <div class="desktop-table-wrap" id="missions-table-host"></div>
    <div class="mobile-card-list" id="missions-mobile-host"></div>
  `;

  const host = container.querySelector('#missions-table-host');
  const mobileHost = container.querySelector('#missions-mobile-host');
  const countEl = container.querySelector('#mission-count');
  const progressPill = container.querySelector('#missions-progress-pill');
  const resetBtn = container.querySelector('#mission-reset');
  const filterBar = container.querySelector('#mission-filter-bar');
  const filterToggle = container.querySelector('#mission-filter-toggle');
  const filterBadge = container.querySelector('#mission-filter-badge');

  function updateResetVisibility() {
    const activeExtrasCount = [
      vs.starFilter !== 'all',
      vs.chapterFilter !== 'all',
      vs.readinessFilter !== 'all',
      vs.statusFilter !== 'all'
    ].filter(Boolean).length;
    if (filterBadge) {
      filterBadge.textContent = String(activeExtrasCount);
      filterBadge.hidden = activeExtrasCount === 0;
    }
    const dirty = vs.activeBranch !== 'ALL' || activeExtrasCount > 0 || Boolean(vs.search.trim());
    if (resetBtn) resetBtn.hidden = !dirty;
  }

  function update() {
    updateResetVisibility();
    const completed = ctx.storage.get('completedMissions', {});
    const q = vs.search.trim().toLowerCase();

    const filtered = ctx.data.missions.filter((m) => {
      if (vs.activeBranch !== 'ALL' && m.branch !== vs.activeBranch) return false;
      if (vs.starFilter !== 'all' && m.stars !== Number(vs.starFilter)) return false;
      if (vs.chapterFilter !== 'all' && m.chapterAvailable > Number(vs.chapterFilter)) return false;
      const ready = ctx.evaluateHardModeReadiness(m, zack.level);
      if (vs.readinessFilter !== 'all' && ready.key !== vs.readinessFilter) return false;
      const isDone = Boolean(completed[m.id]);
      if (vs.statusFilter === 'todo' && isDone) return false;
      if (vs.statusFilter === 'done' && !isDone) return false;
      if (vs.statusFilter === 'unlockable') {
        if (isDone || m.chapterAvailable > zack.chapter) return false;
        const prereqs = m.prerequisiteMissionIds || [];
        if (!prereqs.every((pid) => completed[pid])) return false;
      }
      if (!q) return true;
      const enemiesStr = [...m.bossEnemyIds, ...m.randomEnemyIds]
        .map((eid) => ctx.indexes.enemyById.get(eid)?.name || '')
        .join(' ');
      const bg = m.bossGuide;
      const bossGuideStr = bg
        ? `${bg.targetName} ${bg.encounterType} ${bg.threatRating} ${bg.summary} ${(bg.keyAttacksToWatch || []).join(' ')}`
        : '';
      const hay = `${m.id} ${m.title} ${m.unlockCondition} ${m.clearReward?.rawLabel || ''} ${(m.treasures || []).map((t) => t.rawLabel).join(' ')} ${enemiesStr} ${bossGuideStr}`.toLowerCase();
      return hay.includes(q);
    });

    countEl.textContent = `${filtered.length} shown`;

    renderSortableTable({
      container: host,
      rows: filtered,
      initialSortKey: vs.sortKey,
      initialSortDir: vs.sortDir,
      onSortChange: (k, d) => {
        vs.sortKey = k;
        vs.sortDir = d;
      },
      onRowClick: (row) => ctx.router.navigate(`#/game/${ctx.meta.slug}/missions/${encodeURIComponent(row.id)}`),
      columns: [
        {
          key: 'done',
          label: '✓',
          sortable: false,
          render: (m) => `<input type="checkbox" data-toggle-mid="${escapeHtml(m.id)}" ${completed[m.id] ? 'checked' : ''} aria-label="Mark ${escapeHtml(m.id)} complete" />`
        },
        {
          key: 'id',
          label: 'Mission',
          render: (m) => `<strong class="mono">${escapeHtml(m.id)}</strong><div class="small">${escapeHtml(m.title)}</div>`
        },
        {
          key: 'boss',
          label: 'Boss / Kill Guide',
          sortValue: (m) => m.bossGuide?.targetName || 'zzz',
          render: (m) => {
            const bg = m.bossGuide;
            if (!bg) return '<span class="muted">—</span>';
            const threatCls = {
              Low: 'pill-mako',
              Moderate: 'pill-cyan',
              High: 'pill-warn',
              Extreme: 'pill-danger'
            }[bg.threatRating] || 'pill-cyan';
            return `
              <div style="font-weight:600;">${escapeHtml(bg.targetName)}</div>
              <div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:3px;">
                <span class="pill ${threatCls}">${escapeHtml(bg.encounterType)}</span>
                <span class="small muted">Kill Guide</span>
              </div>
            `;
          }
        },
        {
          key: 'stars',
          label: 'Difficulty',
          numeric: true,
          render: (m) => {
            const ready = ctx.evaluateHardModeReadiness(m, zack.level);
            return `<span class="pill ${ready.tone}">${m.stars}★ · ${ready.label}</span><div class="small muted">Rec Lv.${m.hardModeBenchmarks?.recommendedLevel}</div>`;
          }
        },
        {
          key: 'chapterAvailable',
          label: 'Ch.',
          numeric: true,
          render: (m) => `<span class="mono">Ch.${m.chapterAvailable}</span>`
        },
        {
          key: 'clearReward',
          label: 'Clear Reward',
          sortValue: (m) => m.clearReward?.rawLabel || 'zzz',
          render: (m) => {
            if (!m.clearReward) return '<span class="muted">—</span>';
            const it = ctx.indexes.itemById.get(m.clearReward.itemId);
            return it
              ? `<a class="pill pill-link pill-mako" href="#/game/${escapeHtml(ctx.meta.slug)}/items/${encodeURIComponent(it.id)}">${escapeHtml(m.clearReward.rawLabel || it.name)}</a>`
              : escapeHtml(m.clearReward.rawLabel);
          }
        },
        {
          key: 'treasures',
          label: 'Chests',
          numeric: true,
          sortValue: (m) => (m.treasures || []).length,
          render: (m) => `<span class="small mono">${(m.treasures || []).length} chest(s)</span>`
        }
      ]
    });

    host.querySelectorAll('[data-toggle-mid]').forEach((chk) => {
      chk.addEventListener('change', () => {
        const mid = chk.dataset.toggleMid;
        const now = ctx.toggleMissionComplete(mid);
        container.querySelectorAll(`[data-toggle-mid="${CSS.escape(mid)}"]`).forEach((peer) => {
          peer.checked = now;
        });
        chk.closest('.m-card')?.classList.toggle('is-done', now);
        const nowDone = Object.values(ctx.storage.get('completedMissions', {})).filter(Boolean).length;
        progressPill.textContent = `${nowDone} / ${ctx.data.missions.length} Cleared`;
      });
    });

    if (mobileHost) {
      if (!filtered.length) {
        mobileHost.innerHTML = `<div class="empty-state">No matching missions found.</div>`;
      } else {
        mobileHost.innerHTML = filtered
          .map((m) => {
            const isDone = Boolean(completed[m.id]);
            const ready = ctx.evaluateHardModeReadiness(m, zack.level);
            const bg = m.bossGuide;
            const rewItem = m.clearReward ? ctx.indexes.itemById.get(m.clearReward.itemId) : null;
            const chestCount = (m.treasures || []).length;
            const rewardHtml = m.clearReward
              ? rewItem
                ? `<a class="pill pill-link pill-mako" href="#/game/${escapeHtml(ctx.meta.slug)}/items/${encodeURIComponent(rewItem.id)}">${escapeHtml(m.clearReward.rawLabel || rewItem.name)}</a>`
                : `<span class="pill">${escapeHtml(m.clearReward.rawLabel)}</span>`
              : '';

            return `
              <article class="m-card ${isDone ? 'is-done' : ''}" data-mission-route="#/game/${escapeHtml(ctx.meta.slug)}/missions/${encodeURIComponent(m.id)}">
                <div class="m-card-top">
                  <div class="m-card-check">
                    <input type="checkbox" data-toggle-mid="${escapeHtml(m.id)}" ${isDone ? 'checked' : ''} aria-label="Mark ${escapeHtml(m.id)} complete" />
                  </div>
                  <div class="m-card-body">
                    <div class="m-card-head">
                      <span class="m-card-id mono">${escapeHtml(m.id)}</span>
                      <span class="pill ${ready.tone}">${m.stars}★ · ${ready.label}</span>
                    </div>
                    <div class="m-card-title">${escapeHtml(m.title)}</div>
                    <div class="m-card-meta" style="margin-top:4px;">
                      ${bg ? `<span>Boss: <strong style="color:var(--text-secondary);">${escapeHtml(bg.targetName)}</strong></span><span>·</span>` : ''}
                      <span class="mono">Ch.${m.chapterAvailable}</span>
                      <span>·</span>
                      <span class="mono">Rec Lv.${m.hardModeBenchmarks?.recommendedLevel ?? '?'}</span>
                      ${chestCount ? `<span>·</span><span class="mono">${chestCount} chest${chestCount > 1 ? 's' : ''}</span>` : ''}
                    </div>
                  </div>
                  <span class="m-card-chevron">${icon('chevron-right', 16)}</span>
                </div>
                ${
                  rewardHtml
                    ? `<div class="m-card-footer">
                        <span class="small muted">Reward</span>
                        ${rewardHtml}
                      </div>`
                    : ''
                }
              </article>
            `;
          })
          .join('');

        mobileHost.querySelectorAll('[data-toggle-mid]').forEach((chk) => {
          chk.addEventListener('change', () => {
            const mid = chk.dataset.toggleMid;
            const now = ctx.toggleMissionComplete(mid);
            container.querySelectorAll(`[data-toggle-mid="${CSS.escape(mid)}"]`).forEach((peer) => {
              peer.checked = now;
            });
            chk.closest('.m-card')?.classList.toggle('is-done', now);
            const nowDone = Object.values(ctx.storage.get('completedMissions', {})).filter(Boolean).length;
            progressPill.textContent = `${nowDone} / ${ctx.data.missions.length} Cleared`;
          });
        });

        mobileHost.querySelectorAll('.m-card[data-mission-route]').forEach((card) => {
          card.addEventListener('click', (e) => {
            if (e.target.closest('a, button, input, label')) return;
            ctx.router.navigate(card.dataset.missionRoute);
          });
        });
      }
    }
  }

  filterToggle?.addEventListener('click', () => {
    vs.filtersOpen = !vs.filtersOpen;
    filterBar?.classList.toggle('filters-open', vs.filtersOpen);
    filterToggle.classList.toggle('btn-primary', vs.filtersOpen);
  });

  container.querySelectorAll('#mission-branches .chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      vs.activeBranch = btn.dataset.branch;
      container.querySelectorAll('#mission-branches .chip').forEach((b) => b.classList.toggle('active', b === btn));
      update();
    });
  });
  container.querySelector('#mission-search').addEventListener('input', (e) => {
    vs.search = e.target.value;
    update();
  });
  container.querySelector('#mission-stars').addEventListener('change', (e) => {
    vs.starFilter = e.target.value;
    update();
  });
  container.querySelector('#mission-chapter').addEventListener('change', (e) => {
    vs.chapterFilter = e.target.value;
    update();
  });
  container.querySelector('#mission-readiness').addEventListener('change', (e) => {
    vs.readinessFilter = e.target.value;
    update();
  });
  container.querySelector('#mission-status').addEventListener('change', (e) => {
    vs.statusFilter = e.target.value;
    update();
  });
  resetBtn?.addEventListener('click', () => {
    vs.activeBranch = 'ALL';
    vs.starFilter = 'all';
    vs.chapterFilter = 'all';
    vs.readinessFilter = 'all';
    vs.statusFilter = 'all';
    vs.search = '';
    container.querySelector('#mission-search').value = '';
    container.querySelector('#mission-stars').value = 'all';
    container.querySelector('#mission-chapter').value = 'all';
    container.querySelector('#mission-readiness').value = 'all';
    container.querySelector('#mission-status').value = 'all';
    container.querySelectorAll('#mission-branches .chip').forEach((b) => b.classList.toggle('active', b.dataset.branch === 'ALL'));
    update();
  });

  update();
}

function getUpstreamChain(mission, missionById, maxDepth = 6) {
  const chain = [];
  const visited = new Set([mission.id]);
  let frontier = [...(mission.prerequisiteMissionIds || [])];
  let depth = 0;
  while (frontier.length && depth < maxDepth) {
    const next = [];
    for (const pid of frontier) {
      if (visited.has(pid)) continue;
      visited.add(pid);
      const pm = missionById.get(pid);
      if (pm) {
        chain.unshift(pm);
        for (const gp of pm.prerequisiteMissionIds || []) {
          if (!visited.has(gp)) next.push(gp);
        }
      }
    }
    frontier = next;
    depth++;
  }
  return chain;
}

function renderMissionDossier(container, ctx, mission) {
  const slug = ctx.meta.slug;
  const zack = ctx.getZackState();
  const ready = ctx.evaluateHardModeReadiness(mission, zack.level);
  const isDone = Boolean(zack.completedMissions[mission.id]);

  const branchMissions = ctx.data.missions.filter((m) => m.branch === mission.branch);
  const branchIdx = branchMissions.findIndex((m) => m.id === mission.id);
  const prevMission = branchIdx > 0 ? branchMissions[branchIdx - 1] : null;
  const nextMission = branchIdx >= 0 && branchIdx < branchMissions.length - 1 ? branchMissions[branchIdx + 1] : null;

  const renderEnemyCards = (eids, badgeLabel, tone) => {
    if (!eids.length) return '<div class="small muted">None listed.</div>';
    const slots = [
      { key: 'commonDrop', label: 'Common Drop', cls: 'loot-common-drop' },
      { key: 'rareDrop', label: 'Rare Drop', cls: 'loot-rare-drop' },
      { key: 'commonSteal', label: 'Common Steal', cls: 'loot-common-steal' },
      { key: 'rareSteal', label: 'Rare Steal', cls: 'loot-rare-steal' }
    ];
    return eids
      .map((eid) => {
        const en = ctx.indexes.enemyById.get(eid);
        if (!en) return '';
        const port = ctx.resolvePortrait(en);
        const weakText = (en.affinities?.weak || []).length ? `Weak: ${en.affinities.weak.join(', ')}` : '';
        return `
          <div class="enemy-hunt-card">
            <div class="enemy-hunt-head">
              <div class="enemy-thumb" data-zoom-eid="${escapeHtml(en.id)}" title="Tap to zoom ${escapeHtml(en.name)}">
                <img referrerpolicy="no-referrer" src="${escapeHtml(port.primary)}" alt="${escapeHtml(en.name)}" loading="lazy" onerror="if(this.dataset.step!=='1'){this.dataset.step='1';this.src='${escapeHtml(port.secondary)}';}else{this.onerror=null;this.src='${escapeHtml(port.fallback)}';}" />
              </div>
              <div style="flex:1;min-width:0;">
                <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;flex-wrap:wrap;">
                  <a href="#/game/${escapeHtml(slug)}/enemies/${encodeURIComponent(en.id)}" style="font-weight:700;font-size:1rem;">${escapeHtml(en.name)}</a>
                  <span class="pill ${tone}">${escapeHtml(badgeLabel)} · Lv.${en.stats?.level ?? '?'}</span>
                </div>
                <div class="small muted mono" style="margin-top:3px;">
                  Hard HP: ${formatNum(en.stats?.hpHard)} · EXP ${formatNum(en.stats?.exp)} · SP ${formatNum(en.stats?.sp)}${weakText ? ` · <span style="color:var(--accent-secondary)">${escapeHtml(weakText)}</span>` : ''}
                </div>
              </div>
            </div>
            <div class="loot-grid">
              ${slots
                .map((s) => {
                  const iid = en.loot?.[s.key];
                  const it = iid ? ctx.indexes.itemById.get(iid) : null;
                  return `
                    <div class="loot-cell ${s.cls} ${it ? '' : 'loot-cell-empty'}">
                      <span class="loot-cell-label">${escapeHtml(s.label)}</span>
                      <span class="loot-cell-val">
                        ${it ? `<a href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(it.id)}">${escapeHtml(it.name)}</a>` : '<span class="muted">—</span>'}
                      </span>
                    </div>
                  `;
                })
                .join('')}
            </div>
          </div>
        `;
      })
      .join('');
  };

  const rewardItem = mission.clearReward ? ctx.indexes.itemById.get(mission.clearReward.itemId) : null;

  const itemByLowerName = new Map(ctx.data.items.map((it) => [it.name.toLowerCase(), it]));
  const linkItemChip = (label, tone = 'pill-cyan') => {
    const clean = String(label || '').trim();
    const candidates = [clean, clean.replace(/\s*\(.*?\)\s*/g, '').trim(), clean.split('/')[0].trim()];
    let found = null;
    for (const c of candidates) {
      if (itemByLowerName.has(c.toLowerCase())) {
        found = itemByLowerName.get(c.toLowerCase());
        break;
      }
    }
    if (found) {
      return `<a class="pill pill-link ${tone}" href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(found.id)}" title="${escapeHtml(found.description || found.name)}">${escapeHtml(clean)}</a>`;
    }
    return `<span class="pill ${tone}">${escapeHtml(clean)}</span>`;
  };

  const renderBossGuideSection = () => {
    const bg = mission.bossGuide;
    if (!bg) return '';
    const threatClassMap = { Low: 'boss-threat-low', Moderate: 'boss-threat-moderate', High: 'boss-threat-high', Extreme: 'boss-threat-extreme' };
    const threatPillMap = { Low: 'pill-mako', Moderate: 'pill-cyan', High: 'pill-warn', Extreme: 'pill-danger' };
    const threatCls = threatClassMap[bg.threatRating] || 'boss-threat-moderate';
    const threatPill = threatPillMap[bg.threatRating] || 'pill-cyan';

    const targetEnemies = (bg.targetEnemyIds || []).map((eid) => ctx.indexes.enemyById.get(eid)).filter(Boolean);
    const primaryTarget = targetEnemies[0] || null;
    const thumbsHtml = targetEnemies
      .slice(0, 3)
      .map((en) => {
        const port = ctx.resolvePortrait(en);
        return `
        <div class="enemy-thumb" data-zoom-eid="${escapeHtml(en.id)}" title="Tap to zoom ${escapeHtml(en.name)}">
          <img referrerpolicy="no-referrer" src="${escapeHtml(port.primary)}" alt="${escapeHtml(en.name)}" loading="lazy" onerror="if(this.dataset.step!=='1'){this.dataset.step='1';this.src='${escapeHtml(port.secondary)}';}else{this.onerror=null;this.src='${escapeHtml(port.fallback)}';}" />
        </div>
      `;
      })
      .join('');

    const targetLinksHtml = targetEnemies.length
      ? targetEnemies
          .map((en) => `<a class="pill pill-link pill-danger" href="#/game/${escapeHtml(slug)}/enemies/${encodeURIComponent(en.id)}">${escapeHtml(en.name)} · Hard HP ${formatNum(en.stats?.hpHard)}</a>`)
          .join('')
      : '';

    return `
      <section class="card card-glow boss-guide-card" style="margin-bottom:16px;">
        <div class="boss-guide-head">
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;min-width:0;">
            ${thumbsHtml}
            <div style="min-width:0;">
              <div class="brand-sub">Hard Mode Tactical Kill Guide</div>
              <h2 style="margin:2px 0 4px;">How to Kill: ${escapeHtml(bg.targetName)}</h2>
              <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;">
                <span class="pill ${threatPill}">${escapeHtml(bg.encounterType)}</span>
                <span class="pill ${threatCls}">Threat: ${escapeHtml(bg.threatRating)}</span>
                ${primaryTarget ? `<span class="pill mono">Lv.${primaryTarget.stats?.level ?? '?'} · Hard HP ${formatNum(primaryTarget.stats?.hpHard)}</span>` : ''}
              </div>
            </div>
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;">
            ${targetLinksHtml}
          </div>
        </div>

        <p class="prose" style="margin:10px 0 14px;">${escapeHtml(bg.summary)}</p>

        <div class="grid-2" style="margin-bottom:14px;">
          <div class="sub-panel">
            <h4 style="margin:0 0 8px;color:var(--accent);">Recommended Hard Mode Loadout</h4>
            <div class="small mono muted" style="margin-bottom:8px;">${escapeHtml(bg.recommendedLoadout?.statTargets || '')}</div>
            <div class="small muted" style="margin-bottom:4px;">Materia</div>
            <div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:10px;">
              ${(bg.recommendedLoadout?.materia || []).map((mName) => linkItemChip(mName, 'pill-mako')).join('')}
            </div>
            <div class="small muted" style="margin-bottom:4px;">Accessories</div>
            <div style="display:flex;flex-wrap:wrap;gap:5px;">
              ${(bg.recommendedLoadout?.accessories || []).map((aName) => linkItemChip(aName, 'pill-cyan')).join('')}
            </div>
          </div>

          <div class="sub-panel">
            <h4 style="margin:0 0 8px;color:var(--accent-secondary);">Weaknesses, Immunities & Counters</h4>
            <ul class="boss-bullet-list small">
              ${(bg.weaknessesAndCounters || []).map((w) => `<li>${escapeHtml(w)}</li>`).join('')}
            </ul>
          </div>
        </div>

        <div style="margin-bottom:14px;">
          <h4 style="margin:0 0 8px;color:var(--accent-warn);">Key Attacks to Watch</h4>
          <div class="boss-attack-list">
            ${(bg.keyAttacksToWatch || []).map((atk) => `<div class="boss-attack-item small">${escapeHtml(atk)}</div>`).join('')}
          </div>
        </div>

        <div style="margin-bottom:14px;">
          <h4 style="margin:0 0 8px;">Step-by-Step Kill Strategy</h4>
          <div class="step-timeline">
            ${(bg.killSteps || [])
              .map(
                (step, idx) => `
                <div class="step-item">
                  <div class="step-item-head">
                    <strong style="color:var(--accent);">Step ${idx + 1}</strong>
                  </div>
                  <div class="prose small">${escapeHtml(step)}</div>
                </div>
              `
              )
              .join('')}
          </div>
        </div>

        <div class="alert alert-mako small"><strong>Reunion Hard Mode Pro Tip:</strong> ${escapeHtml(bg.proTip)}</div>
      </section>
    `;
  };

  const upstreamChain = getUpstreamChain(mission, ctx.indexes.missionById);
  const downstreamList = ctx.indexes.unlocksByMission?.get(mission.id) || [];

  const pagerHtml = `
    ${prevMission ? `<a class="btn btn-sm" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(prevMission.id)}" title="${escapeHtml(prevMission.title)}">${icon('chevron-left', 14)} <span class="mono">${escapeHtml(prevMission.id)}</span></a>` : ''}
    ${nextMission ? `<a class="btn btn-sm" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(nextMission.id)}" title="${escapeHtml(nextMission.title)}"><span class="mono">${escapeHtml(nextMission.id)}</span> ${icon('chevron-right', 14)}</a>` : ''}
  `;

  const navRightHtml = `
    ${pagerHtml}
    <button class="btn btn-sm ${isDone ? 'btn-primary' : ''}" id="dossier-toggle-done">
      ${isDone ? `${icon('check', 14)} Cleared (Undo)` : 'Mark Cleared'}
    </button>
  `;

  container.innerHTML = `
    ${renderDossierNavBar({
      router: ctx.router,
      listRoute: `#/game/${escapeHtml(slug)}/missions`,
      listLabel: 'All 300 Missions',
      rightHtml: navRightHtml
    })}

    <div class="dossier-header">
      <div style="flex:1;min-width:240px;">
        <div class="brand-sub">${escapeHtml(mission.branch)} · ${escapeHtml(mission.branchName)}</div>
        <h1 style="margin:4px 0;" class="mono">${escapeHtml(mission.id)}: <span style="font-family:var(--font-sans);">${escapeHtml(mission.title)}</span></h1>
        <p class="muted" style="margin:4px 0 8px;">${escapeHtml(mission.description || '')}</p>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">
          <span class="pill ${ready.tone}">${mission.stars}★ · ${ready.label} (Zack Lv.${zack.level})</span>
          <span class="pill pill-cyan">Ch. ${mission.chapterAvailable}+</span>
          <span class="pill">Unlock: ${escapeHtml(mission.unlockCondition || 'Story progression')}</span>
        </div>
      </div>

      <div class="card" style="min-width:250px;background:var(--bg-primary);">
        <div class="small muted" style="margin-bottom:6px;">Hard Mode Stat Benchmarks</div>
        <div class="grid-2 small mono" style="gap:6px;">
          <div>Rec Lv: <strong>${mission.hardModeBenchmarks?.recommendedLevel}</strong></div>
          <div>HP: <strong>${formatNum(mission.hardModeBenchmarks?.hp)}</strong></div>
          <div>VIT: <strong>${mission.hardModeBenchmarks?.vit}</strong></div>
          <div>SPR: <strong>${mission.hardModeBenchmarks?.spr}</strong></div>
        </div>
        <div class="small muted" style="margin-top:8px;">${escapeHtml(mission.hardModeBenchmarks?.notes || '')}</div>
      </div>
    </div>

    ${
      mission.routeNotes
        ? `<div class="alert alert-mako small" style="margin-bottom:14px;"><strong>Chest & Route Notes:</strong> ${escapeHtml(mission.routeNotes)}</div>`
        : ''
    }

    ${
      upstreamChain.length || downstreamList.length
        ? `
      <section class="card" style="margin-bottom:16px;">
        <h3 style="margin-top:0;">Mission Unlock Chain</h3>
        <div class="grid-2">
          <div class="sub-panel">
            <div class="small muted" style="margin-bottom:6px;">Prerequisites to Reach ${escapeHtml(mission.id)}</div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;">
              ${
                upstreamChain.length
                  ? upstreamChain
                      .map((pm) => {
                        const done = Boolean(zack.completedMissions[pm.id]);
                        return `<a class="pill pill-link ${done ? 'pill-mako' : 'pill-warn'} mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(pm.id)}">${done ? '✓ ' : ''}${escapeHtml(pm.id)}</a>`;
                      })
                      .join('<span class="muted">→</span>') + `<span class="muted">→</span><span class="pill pill-cyan mono">${escapeHtml(mission.id)}</span>`
                  : `<span class="small muted">${escapeHtml(mission.unlockCondition || 'Story / NPC Unlock')}</span>`
              }
            </div>
          </div>
          <div class="sub-panel">
            <div class="small muted" style="margin-bottom:6px;">Unlocks Next</div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;">
              ${
                downstreamList.length
                  ? downstreamList
                      .map((dm) => {
                        const done = Boolean(zack.completedMissions[dm.id]);
                        return `<a class="pill pill-link ${done ? 'pill-mako' : 'pill-cyan'} mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(dm.id)}">${done ? '✓ ' : ''}${escapeHtml(dm.id)} · ${escapeHtml(dm.title)}</a>`;
                      })
                      .join('')
                  : '<span class="small muted">End of branch chain.</span>'
              }
            </div>
          </div>
        </div>
      </section>
    `
        : ''
    }

    <div class="grid-2" style="margin-bottom:16px;">
      <section class="card">
        <h3 style="margin-top:0;">Clear Reward</h3>
        ${
          rewardItem
            ? `<a class="pill pill-link pill-mako" href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(rewardItem.id)}">${escapeHtml(mission.clearReward.rawLabel || rewardItem.name)}</a>`
            : `<span class="small muted">${escapeHtml(mission.clearReward?.rawLabel || 'None')}</span>`
        }
      </section>
      <section class="card">
        <h3 style="margin-top:0;">Treasure Chests</h3>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">
          ${
            (mission.treasures || []).length
              ? mission.treasures
                  .map((t) => {
                    const it = ctx.indexes.itemById.get(t.itemId);
                    return it
                      ? `<a class="pill pill-link pill-cyan" href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(it.id)}">${escapeHtml(t.rawLabel || it.name)}</a>`
                      : `<span class="pill">${escapeHtml(t.rawLabel)}</span>`;
                  })
                  .join(' ')
              : '<span class="small muted">No treasure chests in this mission.</span>'
          }
        </div>
      </section>
    </div>

    ${renderBossGuideSection()}

    <div class="grid-2">
      <section class="card">
        <h3 style="margin-top:0;">Boss Encounters</h3>
        ${renderEnemyCards(mission.bossEnemyIds || [], 'Boss', 'pill-danger')}
      </section>
      <section class="card">
        <h3 style="margin-top:0;">Random Encounters</h3>
        ${renderEnemyCards(mission.randomEnemyIds || [], 'Random', 'pill-cyan')}
      </section>
    </div>

    ${
      prevMission || nextMission
        ? `
      <div class="dossier-pager">
        <div>${prevMission ? `<a class="btn btn-sm" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(prevMission.id)}">${icon('chevron-left', 14)} <span class="mono">${escapeHtml(prevMission.id)}</span> · ${escapeHtml(prevMission.title)}</a>` : ''}</div>
        <div>${nextMission ? `<a class="btn btn-sm" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(nextMission.id)}"><span class="mono">${escapeHtml(nextMission.id)}</span> · ${escapeHtml(nextMission.title)} ${icon('chevron-right', 14)}</a>` : ''}</div>
      </div>
    `
        : ''
    }
  `;

  wireDossierNavBar(container, ctx.router);

  container.querySelector('#dossier-toggle-done')?.addEventListener('click', (e) => {
    const now = ctx.toggleMissionComplete(mission.id);
    e.currentTarget.classList.toggle('btn-primary', now);
    e.currentTarget.innerHTML = now ? `${icon('check', 14)} Cleared (Undo)` : 'Mark Cleared';
  });

  container.querySelectorAll('[data-zoom-eid]').forEach((el) => {
    el.addEventListener('click', () => {
      const en = ctx.indexes.enemyById.get(el.dataset.zoomEid);
      if (!en) return;
      const port = ctx.resolvePortrait(en);
      openLightbox({
        src: port.primary,
        fallbackSrc: port.fallback,
        title: en.name,
        subtitle: `${en.family} · Lv.${en.stats?.level ?? '?'} · Hard HP ${formatNum(en.stats?.hpHard)}`
      });
    });
  });
}
