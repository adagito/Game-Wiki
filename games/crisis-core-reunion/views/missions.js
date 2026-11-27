import { escapeHtml, formatNum, openLightbox, renderSortableTable } from '../../../core/ui.js';

export function renderMissionsView(container, ctx, selectedMissionId = null) {
  if (selectedMissionId && ctx.indexes.missionById.has(selectedMissionId)) {
    renderMissionDossier(container, ctx, ctx.indexes.missionById.get(selectedMissionId));
    return;
  }

  const zack = ctx.getZackState();
  const branches = ['ALL', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'M10'];
  let activeBranch = 'ALL';
  let starFilter = 'all';
  let chapterFilter = 'all';
  let readinessFilter = 'all';
  let statusFilter = 'all';
  let search = '';

  const doneCount = Object.values(zack.completedMissions).filter(Boolean).length;

  container.innerHTML = `
    <div class="section-header">
      <div>
        <div class="brand-sub">Hard Mode Tactical Index</div>
        <h1>🎯 Missions Explorer (All 300)</h1>
        <p class="muted small" style="margin:4px 0 0;">Readiness badges evaluate against your tracked Zack Lv. <strong>${zack.level}</strong> (adjust in Hard Mode Suggester).</p>
      </div>
      <div style="display:flex;gap:8px;align-items:center;">
        <span class="pill pill-mako mono" id="missions-progress-pill">${doneCount} / ${ctx.data.missions.length} Cleared</span>
      </div>
    </div>

    <div class="chip-row" id="mission-branches">
      ${branches.map((b) => `<button class="chip ${b === 'ALL' ? 'active' : ''}" data-branch="${b}">${b === 'ALL' ? 'All (300)' : b}</button>`).join('')}
    </div>

    <div class="filter-bar">
      <input type="search" id="mission-search" class="input" style="flex:1;min-width:200px;" placeholder="Search M6-6-3, title, unlock, reward, treasure, or enemy..." />
      <select id="mission-stars" class="select">
        <option value="all">All Stars (1–10★)</option>
        ${Array.from({ length: 10 }, (_, i) => `<option value="${i + 1}">${i + 1}★</option>`).join('')}
      </select>
      <select id="mission-chapter" class="select">
        <option value="all">Any Chapter</option>
        ${Array.from({ length: 10 }, (_, i) => `<option value="${i + 1}">Ch. ${i + 1}+</option>`).join('')}
      </select>
      <select id="mission-readiness" class="select">
        <option value="all">All Readiness</option>
        <option value="ready">Ready Now</option>
        <option value="stretch">Stretch</option>
        <option value="danger">Danger</option>
      </select>
      <select id="mission-status" class="select">
        <option value="all">All Status</option>
        <option value="todo">Incomplete Only</option>
        <option value="done">Cleared Only</option>
      </select>
      <span class="small muted mono" id="mission-count"></span>
    </div>

    <div id="missions-table-host"></div>
  `;

  const host = container.querySelector('#missions-table-host');
  const countEl = container.querySelector('#mission-count');
  const progressPill = container.querySelector('#missions-progress-pill');

  function update() {
    const completed = ctx.storage.get('completedMissions', {});
    const q = search.trim().toLowerCase();

    const filtered = ctx.data.missions.filter((m) => {
      if (activeBranch !== 'ALL' && m.branch !== activeBranch) return false;
      if (starFilter !== 'all' && m.stars !== Number(starFilter)) return false;
      if (chapterFilter !== 'all' && m.chapterAvailable > Number(chapterFilter)) return false;
      const ready = ctx.evaluateHardModeReadiness(m, zack.level);
      if (readinessFilter !== 'all' && ready.key !== readinessFilter) return false;
      const isDone = Boolean(completed[m.id]);
      if (statusFilter === 'todo' && isDone) return false;
      if (statusFilter === 'done' && !isDone) return false;
      if (!q) return true;
      const enemiesStr = [...m.bossEnemyIds, ...m.randomEnemyIds]
        .map((eid) => ctx.indexes.enemyById.get(eid)?.name || '')
        .join(' ');
      const hay = `${m.id} ${m.title} ${m.unlockCondition} ${m.clearReward?.rawLabel || ''} ${(m.treasures || []).map((t) => t.rawLabel).join(' ')} ${enemiesStr}`.toLowerCase();
      return hay.includes(q);
    });

    countEl.textContent = `${filtered.length} shown`;

    renderSortableTable({
      container: host,
      rows: filtered,
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
        ctx.toggleMissionComplete(chk.dataset.toggleMid);
        const nowDone = Object.values(ctx.storage.get('completedMissions', {})).filter(Boolean).length;
        progressPill.textContent = `${nowDone} / ${ctx.data.missions.length} Cleared`;
      });
    });
  }

  container.querySelectorAll('#mission-branches .chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      activeBranch = btn.dataset.branch;
      container.querySelectorAll('#mission-branches .chip').forEach((b) => b.classList.toggle('active', b === btn));
      update();
    });
  });
  container.querySelector('#mission-search').addEventListener('input', (e) => {
    search = e.target.value;
    update();
  });
  container.querySelector('#mission-stars').addEventListener('change', (e) => {
    starFilter = e.target.value;
    update();
  });
  container.querySelector('#mission-chapter').addEventListener('change', (e) => {
    chapterFilter = e.target.value;
    update();
  });
  container.querySelector('#mission-readiness').addEventListener('change', (e) => {
    readinessFilter = e.target.value;
    update();
  });
  container.querySelector('#mission-status').addEventListener('change', (e) => {
    statusFilter = e.target.value;
    update();
  });

  update();
}

function renderMissionDossier(container, ctx, mission) {
  const slug = ctx.meta.slug;
  const zack = ctx.getZackState();
  const ready = ctx.evaluateHardModeReadiness(mission, zack.level);
  const isDone = Boolean(zack.completedMissions[mission.id]);

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
        const src = en.portrait?.imageUrl || `./${en.portrait?.fallbackSvg}`;
        const fb = `./${en.portrait?.fallbackSvg}`;
        const weakText = (en.affinities?.weak || []).length ? `Weak: ${en.affinities.weak.join(', ')}` : '';
        return `
          <div class="enemy-hunt-card">
            <div class="enemy-hunt-head">
              <div class="enemy-thumb" data-zoom-eid="${escapeHtml(en.id)}" title="Tap to zoom ${escapeHtml(en.name)}">
                <img referrerpolicy="no-referrer" src="${escapeHtml(src)}" alt="${escapeHtml(en.name)}" loading="lazy" onerror="this.onerror=null;this.src='${escapeHtml(fb)}';" />
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

  container.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;gap:8px;flex-wrap:wrap;">
      <a class="btn btn-sm" href="#/game/${escapeHtml(slug)}/missions">← All 300 Missions</a>
      <button class="btn btn-sm ${isDone ? 'btn-primary' : ''}" id="dossier-toggle-done">
        ${isDone ? '✓ Cleared (Click to Undo)' : 'Mark Mission Cleared'}
      </button>
    </div>

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

    <div class="grid-2" style="margin-bottom:16px;">
      <section class="card">
        <h3 style="margin-top:0;">🏆 Clear Reward</h3>
        ${
          rewardItem
            ? `<a class="pill pill-link pill-mako" href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(rewardItem.id)}">${escapeHtml(mission.clearReward.rawLabel || rewardItem.name)}</a>`
            : `<span class="small muted">${escapeHtml(mission.clearReward?.rawLabel || 'None')}</span>`
        }
      </section>
      <section class="card">
        <h3 style="margin-top:0;">📦 Treasure Chests</h3>
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

    <div class="grid-2">
      <section class="card">
        <h3 style="margin-top:0;">💀 Boss Encounters</h3>
        ${renderEnemyCards(mission.bossEnemyIds || [], 'Boss', 'pill-danger')}
      </section>
      <section class="card">
        <h3 style="margin-top:0;">⚔️ Random Encounters</h3>
        ${renderEnemyCards(mission.randomEnemyIds || [], 'Random', 'pill-cyan')}
      </section>
    </div>
  `;

  container.querySelector('#dossier-toggle-done')?.addEventListener('click', (e) => {
    const now = ctx.toggleMissionComplete(mission.id);
    e.currentTarget.classList.toggle('btn-primary', now);
    e.currentTarget.textContent = now ? '✓ Cleared (Click to Undo)' : 'Mark Mission Cleared';
  });

  container.querySelectorAll('[data-zoom-eid]').forEach((el) => {
    el.addEventListener('click', () => {
      const en = ctx.indexes.enemyById.get(el.dataset.zoomEid);
      if (!en) return;
      openLightbox({
        src: en.portrait?.imageUrl || `./${en.portrait?.fallbackSvg}`,
        fallbackSrc: `./${en.portrait?.fallbackSvg}`,
        title: en.name,
        subtitle: `${en.family} · Lv.${en.stats?.level ?? '?'} · Hard HP ${formatNum(en.stats?.hpHard)}`
      });
    });
  });
}
