import {
  escapeHtml,
  formatNum,
  icon,
  openLightbox,
  renderDossierNavBar,
  renderSortableTable,
  wireDossierNavBar
} from '../../../core/ui.js';

function renderLootGrid(en, ctx) {
  const slug = ctx.meta.slug;
  const slots = [
    { key: 'commonDrop', label: 'Common Drop', cls: 'loot-common-drop' },
    { key: 'rareDrop', label: 'Rare Drop', cls: 'loot-rare-drop' },
    { key: 'commonSteal', label: 'Common Steal', cls: 'loot-common-steal' },
    { key: 'rareSteal', label: 'Rare Steal', cls: 'loot-rare-steal' }
  ];
  return `
    <div class="loot-grid">
      ${slots
        .map((s) => {
          const iid = en.loot?.[s.key];
          const it = iid ? ctx.indexes.itemById.get(iid) : null;
          return `
            <div class="loot-cell ${s.cls} ${it ? '' : 'loot-cell-empty'}">
              <span class="loot-cell-label">${escapeHtml(s.label)}</span>
              <span class="loot-cell-val">
                ${
                  it
                    ? `<a href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(it.id)}">${escapeHtml(it.name)}</a>`
                    : '<span class="muted">—</span>'
                }
              </span>
            </div>
          `;
        })
        .join('')}
    </div>
  `;
}

function imgAttrHtml(port, alt, loading = 'lazy') {
  return `<img referrerpolicy="no-referrer" src="${escapeHtml(port.primary)}" alt="${escapeHtml(alt)}" loading="${loading}" onerror="if(this.dataset.step!=='1'){this.dataset.step='1';this.src='${escapeHtml(port.secondary)}';}else{this.onerror=null;this.src='${escapeHtml(port.fallback)}';}" />`;
}

export function renderEnemiesView(container, ctx, selectedEnemyId = null) {
  if (selectedEnemyId && ctx.indexes.enemyById.has(selectedEnemyId)) {
    renderEnemyDossier(container, ctx, ctx.indexes.enemyById.get(selectedEnemyId));
    return;
  }

  const families = ['All', ...Array.from(new Set(ctx.data.enemies.map((e) => e.family))).sort()];

  if (!ctx.viewState.enemies) {
    ctx.viewState.enemies = {
      activeFamily: 'All',
      viewMode: ctx.storage.get('bestiaryMode', 'gallery'),
      bossOnly: false,
      search: '',
      sortKey: 'name',
      sortDir: 'asc'
    };
  }
  const vs = ctx.viewState.enemies;

  container.innerHTML = `
    <div class="section-header">
      <div>
        <div class="brand-sub">Hard Mode Bestiary · Offline Portraits Bundled</div>
        <h1>Enemy Bestiary</h1>
        <p class="muted small" style="margin:4px 0 0;">All ${ctx.data.enemies.length} enemies with local portraits, 2×2 Drop & Steal grids, full affinities (Weak/Resist/Null/Absorb/Immune), and spawns.</p>
      </div>
      <div class="seg-tabs" style="margin:0;">
        <button class="seg-tab ${vs.viewMode === 'gallery' ? 'active' : ''}" id="mode-gallery">Portrait Hunt</button>
        <button class="seg-tab ${vs.viewMode === 'dossier' ? 'active' : ''}" id="mode-dossier">Table View</button>
      </div>
    </div>

    <div class="chip-row" id="enemy-families">
      ${families.map((f) => `<button class="chip ${f === vs.activeFamily ? 'active' : ''}" data-fam="${escapeHtml(f)}">${escapeHtml(f)}</button>`).join('')}
    </div>

    <div class="filter-bar">
      <input type="search" id="enemy-search" class="input" style="flex:1;min-width:220px;" value="${escapeHtml(vs.search)}" placeholder="Search enemy name, loot item, weakness, absorb, story location, or mission ID (e.g. M6-6-3)..." />
      <label class="small" style="display:flex;align-items:center;gap:6px;cursor:pointer;">
        <input type="checkbox" id="enemy-boss-only" ${vs.bossOnly ? 'checked' : ''} /> Bosses Only
      </label>
      <button type="button" class="btn btn-ghost btn-sm" id="enemy-reset" hidden>${icon('filter-x', 14)} Reset</button>
      <span class="small muted mono" id="enemy-count"></span>
    </div>

    <div id="enemies-host"></div>
  `;

  const host = container.querySelector('#enemies-host');
  const countEl = container.querySelector('#enemy-count');
  const resetBtn = container.querySelector('#enemy-reset');

  function updateResetVisibility() {
    const dirty = vs.activeFamily !== 'All' || vs.bossOnly || Boolean(vs.search.trim());
    if (resetBtn) resetBtn.hidden = !dirty;
  }

  function getLootNames(en) {
    return ['commonDrop', 'rareDrop', 'commonSteal', 'rareSteal']
      .map((s) => ctx.indexes.itemById.get(en.loot?.[s])?.name || '')
      .filter(Boolean);
  }

  function renderItemPill(itemId, label, tone) {
    if (!itemId) return '';
    const it = ctx.indexes.itemById.get(itemId);
    if (!it) return '';
    return `<a class="pill pill-link ${tone}" href="#/game/${escapeHtml(ctx.meta.slug)}/items/${encodeURIComponent(it.id)}" title="${escapeHtml(label)}">${escapeHtml(label)}: ${escapeHtml(it.name)}</a>`;
  }

  function wireZoomHandlers() {
    host.querySelectorAll('[data-zoom-id]').forEach((el) => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        const en = ctx.indexes.enemyById.get(el.dataset.zoomId);
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

  function update() {
    updateResetVisibility();
    const q = vs.search.trim().toLowerCase();
    const filtered = ctx.data.enemies.filter((en) => {
      if (vs.activeFamily !== 'All' && en.family !== vs.activeFamily) return false;
      if (vs.bossOnly && !en.isBoss) return false;
      if (!q) return true;
      const affStr = [
        ...(en.affinities?.weak || []),
        ...(en.affinities?.resist || []),
        ...(en.affinities?.null || []),
        ...(en.affinities?.absorb || [])
      ].join(' ');
      const hay = `${en.name} ${en.family} ${getLootNames(en).join(' ')} ${affStr} ${(en.storyLocations || []).join(' ')} ${(en.spawns || []).map((s) => s.missionId).join(' ')}`.toLowerCase();
      return hay.includes(q);
    });
    countEl.textContent = `${filtered.length} enemies`;

    if (vs.viewMode === 'gallery') {
      if (!filtered.length) {
        host.innerHTML = `<div class="empty-state">No enemies match your filter.</div>`;
        return;
      }
      host.innerHTML = `
        <div class="grid-auto">
          ${filtered
            .map((en) => {
              const port = ctx.resolvePortrait(en);
              const mBadges = (en.spawns || [])
                .slice(0, 3)
                .map((sp) => `<a class="pill pill-link pill-cyan mono" href="#/game/${escapeHtml(ctx.meta.slug)}/missions/${encodeURIComponent(sp.missionId)}">${escapeHtml(sp.missionId)}</a>`)
                .join('');
              const storyBadge =
                !mBadges && en.storyChapter
                  ? `<a class="pill pill-link pill-warn mono" href="#/game/${escapeHtml(ctx.meta.slug)}/story/ch_${en.storyChapter}">Story Ch.${en.storyChapter}</a>`
                  : '';
              return `
              <article class="gallery-card">
                <div class="gallery-thumb" data-zoom-id="${escapeHtml(en.id)}" title="Tap to zoom portrait">
                  ${imgAttrHtml(port, en.name)}
                </div>
                <div class="gallery-meta">
                  <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">
                    <a href="#/game/${escapeHtml(ctx.meta.slug)}/enemies/${encodeURIComponent(en.id)}" style="font-weight:700;font-size:1rem;">${escapeHtml(en.name)}</a>
                    <span class="pill ${en.isBoss ? 'pill-danger' : 'pill-cyan'}">${escapeHtml(en.isBoss ? 'Boss' : en.family)}</span>
                  </div>
                  <div class="small muted mono">Lv.${en.stats?.level ?? '?'} · Hard HP ${formatNum(en.stats?.hpHard)}</div>
                  ${renderLootGrid(en, ctx)}
                  <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:2px;">
                    ${mBadges || storyBadge || `<span class="small muted">${escapeHtml((en.storyLocations || [])[0] || 'Story Encounter')}</span>`}
                    ${(en.spawns || []).length > 3 ? `<span class="small muted">+${en.spawns.length - 3}</span>` : ''}
                  </div>
                </div>
              </article>
            `;
            })
            .join('')}
        </div>
      `;

      wireZoomHandlers();
      return;
    }

    renderSortableTable({
      container: host,
      rows: filtered,
      initialSortKey: vs.sortKey,
      initialSortDir: vs.sortDir,
      onSortChange: (k, d) => {
        vs.sortKey = k;
        vs.sortDir = d;
      },
      onRowClick: (row) => ctx.router.navigate(`#/game/${ctx.meta.slug}/enemies/${encodeURIComponent(row.id)}`),
      columns: [
        {
          key: 'name',
          label: 'Enemy',
          render: (en) => {
            const port = ctx.resolvePortrait(en);
            return `
              <div style="display:flex;align-items:center;gap:10px;">
                <div class="enemy-thumb" data-zoom-id="${escapeHtml(en.id)}" title="Tap to zoom" style="width:48px;height:48px;">
                  ${imgAttrHtml(port, en.name)}
                </div>
                <div>
                  <strong>${escapeHtml(en.name)}</strong>
                  <div class="small muted">${escapeHtml(en.family)}${en.isBoss ? ' · <span style="color:var(--accent-danger)">BOSS</span>' : ''}</div>
                </div>
              </div>
            `;
          }
        },
        { key: 'level', label: 'Lv', numeric: true, sortValue: (r) => r.stats?.level || 0, render: (r) => `<span class="mono">${r.stats?.level ?? '—'}</span>` },
        { key: 'hpHard', label: 'Hard HP', numeric: true, sortValue: (r) => r.stats?.hpHard || 0, render: (r) => `<span class="mono">${formatNum(r.stats?.hpHard)}</span>` },
        {
          key: 'loot',
          label: 'Drops & Steals',
          sortable: false,
          render: (en) => `
            <div style="display:flex;flex-wrap:wrap;gap:4px;">
              ${renderItemPill(en.loot?.commonDrop, 'Drop', 'pill-mako')}
              ${renderItemPill(en.loot?.rareDrop, 'Rare Drop', 'pill-cyan')}
              ${renderItemPill(en.loot?.commonSteal, 'Steal', 'pill-warn')}
              ${renderItemPill(en.loot?.rareSteal, 'Rare Steal', 'pill-danger')}
            </div>
          `
        },
        {
          key: 'spawns',
          label: 'Locations',
          numeric: true,
          sortValue: (r) => (r.spawns || []).length,
          render: (r) =>
            (r.spawns || []).length
              ? `<span class="mono small">${r.spawns.slice(0, 3).map((s) => s.missionId).join(', ')}${r.spawns.length > 3 ? ` +${r.spawns.length - 3}` : ''}</span>`
              : `<span class="small muted">${r.storyChapter ? `Story Ch.${r.storyChapter}` : ((r.storyLocations || [])[0] || 'Story')}</span>`
        }
      ]
    });
    wireZoomHandlers();
  }

  container.querySelector('#mode-dossier').addEventListener('click', (e) => {
    vs.viewMode = 'dossier';
    ctx.storage.set('bestiaryMode', 'dossier');
    e.currentTarget.classList.add('active');
    container.querySelector('#mode-gallery').classList.remove('active');
    update();
  });
  container.querySelector('#mode-gallery').addEventListener('click', (e) => {
    vs.viewMode = 'gallery';
    ctx.storage.set('bestiaryMode', 'gallery');
    e.currentTarget.classList.add('active');
    container.querySelector('#mode-dossier').classList.remove('active');
    update();
  });
  container.querySelectorAll('#enemy-families .chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      vs.activeFamily = btn.dataset.fam;
      container.querySelectorAll('#enemy-families .chip').forEach((b) => b.classList.toggle('active', b === btn));
      update();
    });
  });
  container.querySelector('#enemy-search').addEventListener('input', (e) => {
    vs.search = e.target.value;
    update();
  });
  container.querySelector('#enemy-boss-only').addEventListener('change', (e) => {
    vs.bossOnly = e.target.checked;
    update();
  });
  resetBtn?.addEventListener('click', () => {
    vs.activeFamily = 'All';
    vs.bossOnly = false;
    vs.search = '';
    container.querySelector('#enemy-search').value = '';
    container.querySelector('#enemy-boss-only').checked = false;
    container.querySelectorAll('#enemy-families .chip').forEach((b) => b.classList.toggle('active', b.dataset.fam === 'All'));
    update();
  });

  update();
}

function renderEnemyDossier(container, ctx, enemy) {
  const slug = ctx.meta.slug;
  const port = ctx.resolvePortrait(enemy);

  const lootSlot = (label, hint, itemId, cls, tone) => {
    const it = itemId ? ctx.indexes.itemById.get(itemId) : null;
    return `
      <div class="loot-cell ${cls} ${it ? '' : 'loot-cell-empty'}" style="padding:12px;">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">
          <span class="loot-cell-label">${escapeHtml(label)}</span>
          <span class="small muted" style="font-size:0.7rem;">${escapeHtml(hint)}</span>
        </div>
        <div style="margin-top:6px;">
          ${
            it
              ? `<a class="pill pill-link ${tone}" href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(it.id)}">${escapeHtml(it.name)}</a>`
              : '<span class="muted small">None</span>'
          }
        </div>
      </div>
    `;
  };

  const bossSpawns = (enemy.spawns || []).filter((s) => s.role === 'boss');
  const randomSpawns = (enemy.spawns || []).filter((s) => s.role !== 'boss');

  const bossGuideMissions = bossSpawns
    .map((sp) => ctx.indexes.missionById.get(sp.missionId))
    .filter((m) => m && m.bossGuide);

  const missionBadges = (list, tone) =>
    list.length
      ? list
          .map((sp) => {
            const m = ctx.indexes.missionById.get(sp.missionId);
            return `<a class="pill pill-link ${tone} mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(sp.missionId)}">${escapeHtml(sp.missionId)}${m ? ` · ${escapeHtml(m.title)}` : ''}</a>`;
          })
          .join(' ')
      : '<span class="small muted">None</span>';

  const affRow = (label, list, cls) => {
    if (!list || !list.length) return `<div><strong>${label}:</strong> <span class="muted">None</span></div>`;
    return `<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;"><strong>${label}:</strong> ${list.map((v) => `<span class="pill ${cls}">${escapeHtml(v)}</span>`).join('')}</div>`;
  };

  const cf = enemy.combatFlags || {};
  const flagBadges = [];
  if (cf.nullPhysical) flagBadges.push('<span class="pill pill-danger">Null Physical</span>');
  if (cf.nullMagic) flagBadges.push('<span class="pill pill-danger">Null Magic</span>');
  if (cf.interruptible) flagBadges.push('<span class="pill pill-mako">Interruptible</span>');
  if (cf.stagger) flagBadges.push(`<span class="pill pill-cyan mono">Stagger ${cf.stagger}</span>`);

  const guideLinksHtml = bossGuideMissions
    .slice(0, 2)
    .map(
      (m) =>
        `<a class="btn btn-sm btn-primary" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(m.id)}">Tactical Kill Guide: ${escapeHtml(m.id)} →</a>`
    )
    .join('');

  container.innerHTML = `
    ${renderDossierNavBar({
      router: ctx.router,
      listRoute: `#/game/${escapeHtml(slug)}/enemies`,
      listLabel: 'All Enemies',
      rightHtml: guideLinksHtml
    })}

    <div class="dossier-header">
      <div class="portrait-box" id="enemy-zoom-box" title="Click to zoom">
        ${imgAttrHtml(port, enemy.name, 'eager')}
      </div>
      <div style="flex:1;min-width:220px;">
        <div class="brand-sub">${escapeHtml(enemy.family)}${enemy.isBoss ? ' · BOSS TARGET' : ''}</div>
        <h1 style="margin:4px 0;">${escapeHtml(enemy.name)}</h1>
        <div class="small muted" style="margin-bottom:8px;">Tap portrait to enlarge</div>
        <div style="display:flex;flex-wrap:wrap;gap:8px;">
          <span class="pill pill-mako mono">Lv. ${enemy.stats?.level ?? '—'}</span>
          <span class="pill pill-danger mono">Hard HP: ${formatNum(enemy.stats?.hpHard)}</span>
          <span class="pill pill-cyan mono">Normal HP: ${formatNum(enemy.stats?.hpNormal)}</span>
          <span class="pill mono">EXP ${formatNum(enemy.stats?.exp)} · SP ${formatNum(enemy.stats?.sp)} · ${formatNum(enemy.stats?.gil)} Gil</span>
          ${flagBadges.join('')}
        </div>
      </div>
    </div>

    <section class="card card-glow" style="margin-bottom:16px;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
        <h3 style="margin:0;">Drops & Steals</h3>
        <span class="pill mono">Drop Rate: ${escapeHtml(enemy.loot?.dropRate || '—')}</span>
      </div>
      <div class="loot-grid">
        ${lootSlot('Common Drop', 'Standard kill drop', enemy.loot?.commonDrop, 'loot-common-drop', 'pill-mako')}
        ${lootSlot('Rare Drop', "Guaranteed w/ Mog's Amulet", enemy.loot?.rareDrop, 'loot-rare-drop', 'pill-cyan')}
        ${lootSlot('Common Steal', "100% w/ Brigand's Gloves", enemy.loot?.commonSteal, 'loot-common-steal', 'pill-warn')}
        ${lootSlot('Rare Steal', "Mog's Amulet + Steal/Mug", enemy.loot?.rareSteal, 'loot-rare-steal', 'pill-danger')}
      </div>
    </section>

    <div class="grid-2" style="margin-bottom:16px;">
      <section class="card">
        <h3 style="margin-top:0;">Combat Stats & Affinities</h3>
        <div class="grid-3 small mono" style="gap:8px;margin-bottom:12px;">
          <div>ATK: <strong>${enemy.stats?.atk ?? '—'}</strong></div>
          <div>VIT: <strong>${enemy.stats?.vit ?? '—'}</strong></div>
          <div>MAG: <strong>${enemy.stats?.mag ?? '—'}</strong></div>
          <div>SPR: <strong>${enemy.stats?.spr ?? '—'}</strong></div>
          <div>LCK: <strong>${enemy.stats?.lck ?? '—'}</strong></div>
          <div>MP: <strong>${formatNum(enemy.stats?.mp)}</strong></div>
        </div>
        <div class="small" style="display:flex;flex-direction:column;gap:7px;">
          ${affRow('Weak', enemy.affinities?.weak, 'pill-mako')}
          ${affRow('Resists', enemy.affinities?.resist, 'pill-cyan')}
          ${affRow('Nullifies', enemy.affinities?.null, 'pill-warn')}
          ${affRow('Absorbs', enemy.affinities?.absorb, 'pill-danger')}
          ${affRow('Immune', enemy.affinities?.immune, '')}
          <div><strong>Abilities:</strong> ${(enemy.abilities || []).join(', ') || 'Standard attacks'}</div>
        </div>
      </section>

      <section class="card">
        <h3 style="margin-top:0;">Mission & Story Locations</h3>
        ${
          enemy.storyChapter || (enemy.storyLocations || []).length
            ? `
          <div style="margin-bottom:12px;">
            <div class="small muted" style="margin-bottom:6px;">Story / Field Appearances</div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;">
              ${enemy.storyChapter ? `<a class="pill pill-link pill-warn mono" href="#/game/${escapeHtml(slug)}/story/ch_${enEscape(enemy.storyChapter)}">Chapter ${enemy.storyChapter} Walkthrough →</a>` : ''}
              ${(enemy.storyLocations || []).map((loc) => `<span class="pill">${escapeHtml(loc)}</span>`).join('')}
            </div>
          </div>
        `
            : ''
        }
        <div style="margin-bottom:10px;">
          <div class="small muted" style="margin-bottom:6px;">Boss Encounters</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;">${missionBadges(bossSpawns, 'pill-danger')}</div>
        </div>
        <div>
          <div class="small muted" style="margin-bottom:6px;">Random Encounters</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;">${missionBadges(randomSpawns, 'pill-cyan')}</div>
        </div>
      </section>
    </div>
  `;

  wireDossierNavBar(container, ctx.router);

  container.querySelector('#enemy-zoom-box')?.addEventListener('click', () => {
    openLightbox({
      src: port.primary,
      fallbackSrc: port.fallback,
      title: enemy.name,
      subtitle: `${enemy.family} · Hard HP ${formatNum(enemy.stats?.hpHard)}`
    });
  });
}

function enEscape(val) {
  return encodeURIComponent(String(val ?? ''));
}
