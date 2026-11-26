import { escapeHtml, formatNum, renderSortableTable } from '../../../core/ui.js';

const CATEGORIES = [
  { id: 'all', label: 'All Items' },
  { id: 'consumables', label: 'Consumables' },
  { id: 'mako-stones', label: 'Mako Stones' },
  { id: 'stat-stones', label: 'Stat Stones' },
  { id: 'max-tier-fusion', label: 'Max-Tier Fusion' },
  { id: 'accessories', label: 'Accessories' },
  { id: 'materia', label: 'Materia' },
  { id: 'key-items', label: 'Key & Unlocks' }
];

export function renderItemsView(container, ctx, selectedItemId = null) {
  if (selectedItemId && ctx.indexes.itemById.has(selectedItemId)) {
    renderItemDossier(container, ctx, ctx.indexes.itemById.get(selectedItemId));
    return;
  }

  let activeCat = 'all';
  let search = '';

  container.innerHTML = `
    <div class="section-header">
      <div>
        <div class="brand-sub">Strict Relational Database</div>
        <h1>🧪 Item, Materia & Accessory Database</h1>
        <p class="muted small" style="margin:4px 0 0;">Enemy drop & steal matrices are computed live from <code>enemies.json</code>.</p>
      </div>
      <span class="pill pill-mako mono">${ctx.data.items.length} Items Indexed</span>
    </div>

    <div class="chip-row" id="item-cats">
      ${CATEGORIES.map((c) => `<button class="chip ${c.id === 'all' ? 'active' : ''}" data-cat="${c.id}">${escapeHtml(c.label)}</button>`).join('')}
    </div>

    <div class="filter-bar">
      <input type="search" id="item-search" class="input" style="flex:1;min-width:220px;" placeholder="Filter by item name, fusion stat (HP%, VIT, MAG), or shop..." />
      <span class="small muted mono" id="item-count"></span>
    </div>

    <div id="items-table-host"></div>
  `;

  const tableHost = container.querySelector('#items-table-host');
  const countEl = container.querySelector('#item-count');
  const searchEl = container.querySelector('#item-search');

  function update() {
    const q = search.trim().toLowerCase();
    const filtered = ctx.data.items.filter((it) => {
      if (activeCat !== 'all' && it.category !== activeCat) return false;
      if (!q) return true;
      const hay = `${it.name} ${it.description} ${it.subCategory} ${it.fusion?.stat || ''} ${(it.shops || []).map((s) => s.shopName).join(' ')}`.toLowerCase();
      return hay.includes(q);
    });
    countEl.textContent = `${filtered.length} shown`;

    renderSortableTable({
      container: tableHost,
      rows: filtered,
      initialSortKey: 'name',
      onRowClick: (row) => {
        ctx.router.navigate(`#/game/${ctx.meta.slug}/items/${encodeURIComponent(row.id)}`);
      },
      columns: [
        {
          key: 'name',
          label: 'Item',
          render: (r) => `<strong>${escapeHtml(r.name)}</strong><div class="small muted">${escapeHtml(r.subCategory || r.category)}</div>`
        },
        {
          key: 'category',
          label: 'Category',
          render: (r) => `<span class="pill pill-cyan">${escapeHtml(r.category)}</span>`
        },
        {
          key: 'fusion',
          label: 'Fusion Bonus',
          sortValue: (r) => r.fusion?.stat || 'zzz',
          render: (r) =>
            r.fusion
              ? `<span class="pill pill-mako mono">${escapeHtml(r.fusion.stat)} +${r.fusion.perUnit}${r.fusion.stat.includes('%') ? '%' : ''} / ${r.fusion.unitsPerStep}x</span>`
              : '<span class="muted">—</span>'
        },
        {
          key: 'sources',
          label: 'Live Sources',
          numeric: true,
          sortValue: (r) => {
            const loot = ctx.getItemLootSources(r.id);
            return loot.commonDrop.length + loot.rareDrop.length + loot.commonSteal.length + loot.rareSteal.length + (r.shops?.length || 0);
          },
          render: (r) => {
            const loot = ctx.getItemLootSources(r.id);
            const enemyCount = new Set([
              ...loot.commonDrop.map((e) => e.id),
              ...loot.rareDrop.map((e) => e.id),
              ...loot.commonSteal.map((e) => e.id),
              ...loot.rareSteal.map((e) => e.id)
            ]).size;
            return `<span class="small mono">${enemyCount} enemies · ${r.shops?.length || 0} shops · ${(r.clearRewardMissions?.length || 0) + (r.treasureMissions?.length || 0)} missions</span>`;
          }
        }
      ]
    });
  }

  container.querySelectorAll('#item-cats .chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      activeCat = btn.dataset.cat;
      container.querySelectorAll('#item-cats .chip').forEach((b) => b.classList.toggle('active', b === btn));
      update();
    });
  });
  searchEl.addEventListener('input', () => {
    search = searchEl.value;
    update();
  });

  update();
}

function renderItemDossier(container, ctx, item) {
  const loot = ctx.getItemLootSources(item.id);
  const slug = ctx.meta.slug;

  const renderQuadrant = (title, toneClass, enemies) => {
    const body = enemies.length
      ? enemies
          .map((en) => {
            const missions = (en.spawns || []).slice(0, 6);
            const missionBadges = missions
              .map(
                (sp) =>
                  `<a class="pill pill-link ${sp.role === 'boss' ? 'pill-danger' : 'pill-cyan'} mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(sp.missionId)}">${escapeHtml(sp.missionId)}</a>`
              )
              .join(' ');
            const more = (en.spawns || []).length > 6 ? `<span class="small muted">+${en.spawns.length - 6} more</span>` : '';
            const src = en.portrait?.imageUrl || `./${en.portrait?.fallbackSvg}`;
            const fb = `./${en.portrait?.fallbackSvg}`;
            return `
              <div class="enemy-source-row">
                <img class="mini-portrait" src="${escapeHtml(src)}" alt="${escapeHtml(en.name)}" onerror="this.onerror=null;this.src='${escapeHtml(fb)}';" />
                <div style="min-width:0;flex:1;">
                  <div style="display:flex;justify-content:space-between;gap:6px;align-items:center;">
                    <a href="#/game/${escapeHtml(slug)}/enemies/${encodeURIComponent(en.id)}" style="font-weight:600;">${escapeHtml(en.name)}</a>
                    <span class="small muted mono">Lv.${en.stats?.level ?? '?'}</span>
                  </div>
                  <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:5px;">
                    ${missionBadges || '<span class="small muted">Story / Field</span>'} ${more}
                  </div>
                </div>
              </div>
            `;
          })
          .join('')
      : '<div class="small muted">No enemy sources in this slot.</div>';

    return `
      <div class="matrix-quadrant">
        <h4><span>${escapeHtml(title)}</span><span class="pill ${toneClass}">${enemies.length}</span></h4>
        ${body}
      </div>
    `;
  };

  const shopsHtml = (item.shops || []).length
    ? item.shops
        .map(
          (s) => `
          <div class="enemy-source-row" style="justify-content:space-between;align-items:center;">
            <div>
              <strong>${escapeHtml(s.shopName)}</strong>
              ${s.unlockHint ? `<div class="small muted">${escapeHtml(s.unlockHint)}</div>` : ''}
            </div>
            <span class="pill pill-warn mono">${formatNum(s.price)} Gil</span>
          </div>
        `
        )
        .join('')
    : '<div class="small muted">Not sold in standard shops.</div>';

  const missionLinks = (mids) =>
    mids.length
      ? mids
          .map((mid) => {
            const m = ctx.indexes.missionById.get(mid);
            return `<a class="pill pill-link pill-mako mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(mid)}" title="${escapeHtml(m?.title || mid)}">${escapeHtml(mid)}${m ? ` · ${escapeHtml(m.title)}` : ''}</a>`;
          })
          .join(' ')
      : '<span class="small muted">None</span>';

  container.innerHTML = `
    <div style="margin-bottom:12px;">
      <a class="btn btn-sm" href="#/game/${escapeHtml(slug)}/items">← All Items</a>
    </div>

    <div class="dossier-header">
      <div style="flex:1;min-width:240px;">
        <div class="brand-sub">${escapeHtml(item.category)} · ${escapeHtml(item.subCategory || 'General')}</div>
        <h1 style="margin:4px 0 6px;">${escapeHtml(item.name)}</h1>
        <p style="margin:0;" class="muted">${escapeHtml(item.description || 'No description available.')}</p>
      </div>
      ${
        item.fusion
          ? `<div class="card" style="min-width:240px;background:var(--bg-primary);">
              <div class="small muted">Materia Fusion Catalyst</div>
              <div style="font-size:1.15rem;font-weight:700;color:var(--accent);" class="mono">
                ${escapeHtml(item.fusion.stat)} +${item.fusion.perUnit}${item.fusion.stat.includes('%') ? '%' : ''} per ${item.fusion.unitsPerStep}×
              </div>
              <div class="small muted">Cap: +${item.fusion.maxBonus}${item.fusion.stat.includes('%') ? '%' : ''}</div>
              ${item.fusion.requiresExistingStat ? `<div class="pill pill-warn" style="margin-top:6px;">Requires existing ${escapeHtml(item.fusion.stat)} stat</div>` : ''}
            </div>`
          : ''
      }
    </div>

    <section class="card" style="margin-bottom:16px;">
      <h3 style="margin-top:0;">4-Quadrant Enemy Drop & Steal Matrix <span class="small muted">(Live from enemies.json)</span></h3>
      <div class="matrix-grid">
        ${renderQuadrant('Common Drop', 'pill-mako', loot.commonDrop)}
        ${renderQuadrant('Rare Drop (Guaranteed w/ Mog\'s Amulet)', 'pill-cyan', loot.rareDrop)}
        ${renderQuadrant('Common Steal', 'pill-warn', loot.commonSteal)}
        ${renderQuadrant('Rare Steal', 'pill-danger', loot.rareSteal)}
      </div>
    </section>

    <div class="grid-3">
      <section class="card">
        <h3 style="margin-top:0;">🛒 Shops & Gil</h3>
        ${shopsHtml}
      </section>
      <section class="card">
        <h3 style="margin-top:0;">🏆 Mission Clear Rewards</h3>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">${missionLinks(item.clearRewardMissions || [])}</div>
      </section>
      <section class="card">
        <h3 style="margin-top:0;">📦 Treasure Chests</h3>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">${missionLinks(item.treasureMissions || [])}</div>
      </section>
    </div>
  `;
}
