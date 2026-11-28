import {
  escapeHtml,
  formatNum,
  icon,
  openLightbox,
  renderDossierNavBar,
  renderSortableTable,
  wireDossierNavBar
} from '../../../core/ui.js';

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

const ACC_EFFECT_TAGS = [
  'All',
  'Break HP Limit',
  'Break Damage Limit',
  'Break MP Limit',
  'Break AP Limit',
  'Elemental Absorb',
  'Elemental Immunity',
  'Status Immunity',
  'Auto-Buff',
  'Drop/Steal Boost',
  'Zero MP/AP'
];

export function renderItemsView(container, ctx, selectedItemId = null) {
  if (selectedItemId && ctx.indexes.itemById.has(selectedItemId)) {
    renderItemDossier(container, ctx, ctx.indexes.itemById.get(selectedItemId));
    return;
  }

  if (!ctx.viewState.items) {
    ctx.viewState.items = {
      activeCat: 'all',
      materiaSub: 'All',
      materiaGrade: 'All',
      accTag: 'All',
      search: '',
      sortKey: 'name',
      sortDir: 'asc'
    };
  }
  const vs = ctx.viewState.items;

  container.innerHTML = `
    <div class="section-header">
      <div>
        <div class="brand-sub">Strict Relational Database</div>
        <h1>Item, Materia & Accessory Database</h1>
        <p class="muted small" style="margin:4px 0 0;">Enemy drop & steal matrices are computed live from <code>enemies.json</code>. Filter Materia by Grade/Cost or Accessories by Break Limits & Immunities.</p>
      </div>
      <span class="pill pill-mako mono">${ctx.data.items.length} Items Indexed</span>
    </div>

    <div class="chip-row" id="item-cats">
      ${CATEGORIES.map((c) => `<button class="chip ${c.id === vs.activeCat ? 'active' : ''}" data-cat="${c.id}">${escapeHtml(c.label)}</button>`).join('')}
    </div>

    <div id="item-subfilters"></div>

    <div class="filter-bar">
      <input type="search" id="item-search" class="input" style="flex:1;min-width:220px;" value="${escapeHtml(vs.search)}" placeholder="Filter by item name, fusion stat (HP%, VIT, MAG), accessory effect, or shop..." />
      <button type="button" class="btn btn-ghost btn-sm" id="item-reset" hidden>${icon('filter-x', 14)} Reset</button>
      <span class="small muted mono" id="item-count"></span>
    </div>

    <div class="desktop-table-wrap" id="items-table-host"></div>
    <div class="mobile-card-list" id="items-mobile-host"></div>
  `;

  const tableHost = container.querySelector('#items-table-host');
  const mobileHost = container.querySelector('#items-mobile-host');
  const subHost = container.querySelector('#item-subfilters');
  const countEl = container.querySelector('#item-count');
  const searchEl = container.querySelector('#item-search');
  const resetBtn = container.querySelector('#item-reset');

  function updateResetVisibility() {
    const dirty =
      vs.activeCat !== 'all' ||
      vs.materiaSub !== 'All' ||
      vs.materiaGrade !== 'All' ||
      vs.accTag !== 'All' ||
      Boolean(vs.search.trim());
    if (resetBtn) resetBtn.hidden = !dirty;
  }

  function renderSubfilters() {
    if (vs.activeCat === 'materia') {
      subHost.innerHTML = `
        <div class="filter-bar" style="margin-bottom:10px;">
          <select id="mat-sub" class="select">
            ${['All', 'Command', 'Magic', 'Support', 'Independent', 'DMW'].map((s) => `<option value="${s}" ${s === vs.materiaSub ? 'selected' : ''}>Type: ${s}</option>`).join('')}
          </select>
          <select id="mat-grade" class="select">
            <option value="All">All Grades (1–8)</option>
            ${Array.from({ length: 8 }, (_, i) => `<option value="${i + 1}" ${String(i + 1) === vs.materiaGrade ? 'selected' : ''}>Grade ${i + 1}</option>`).join('')}
          </select>
        </div>
      `;
      subHost.querySelector('#mat-sub')?.addEventListener('change', (e) => {
        vs.materiaSub = e.target.value;
        update();
      });
      subHost.querySelector('#mat-grade')?.addEventListener('change', (e) => {
        vs.materiaGrade = e.target.value;
        update();
      });
    } else if (vs.activeCat === 'accessories') {
      subHost.innerHTML = `
        <div class="chip-row" id="acc-tags" style="margin-bottom:10px;">
          ${ACC_EFFECT_TAGS.map((t) => `<button class="chip ${t === vs.accTag ? 'active' : ''}" data-atag="${escapeHtml(t)}">${escapeHtml(t)}</button>`).join('')}
        </div>
      `;
      subHost.querySelectorAll('[data-atag]').forEach((btn) => {
        btn.addEventListener('click', () => {
          vs.accTag = btn.dataset.atag;
          renderSubfilters();
          update();
        });
      });
    } else {
      subHost.innerHTML = '';
    }
  }

  function update() {
    updateResetVisibility();
    const q = vs.search.trim().toLowerCase();
    const filtered = ctx.data.items.filter((it) => {
      if (vs.activeCat !== 'all' && it.category !== vs.activeCat) return false;
      if (vs.activeCat === 'materia') {
        if (vs.materiaSub !== 'All' && it.subCategory !== vs.materiaSub) return false;
        if (vs.materiaGrade !== 'All' && String(it.materia?.grade || '') !== vs.materiaGrade) return false;
      }
      if (vs.activeCat === 'accessories' && vs.accTag !== 'All') {
        if (!(it.accessory?.effectTags || []).includes(vs.accTag)) return false;
      }
      if (!q) return true;
      const hay = `${it.name} ${it.description} ${it.subCategory} ${it.fusion?.stat || ''} ${(it.accessory?.effectTags || []).join(' ')} ${(it.shops || []).map((s) => s.shopName).join(' ')}`.toLowerCase();
      return hay.includes(q);
    });
    countEl.textContent = `${filtered.length} shown`;

    renderSortableTable({
      container: tableHost,
      rows: filtered,
      initialSortKey: vs.sortKey,
      initialSortDir: vs.sortDir,
      onSortChange: (k, d) => {
        vs.sortKey = k;
        vs.sortDir = d;
      },
      onRowClick: (row) => {
        ctx.router.navigate(`#/game/${ctx.meta.slug}/items/${encodeURIComponent(row.id)}`);
      },
      columns: [
        {
          key: 'name',
          label: 'Item',
          render: (r) => {
            const matInfo = r.materia
              ? `<span class="small mono" style="color:var(--accent-secondary);">G${r.materia.grade}${r.materia.cost ? ` · ${r.materia.cost} ${r.materia.costType}` : ''}</span>`
              : '';
            const accTags = (r.accessory?.effectTags || []).slice(0, 2).map((t) => `<span class="pill pill-mako" style="font-size:0.68rem;padding:1px 6px;">${escapeHtml(t)}</span>`).join(' ');
            return `<strong>${escapeHtml(r.name)}</strong><div class="small muted">${escapeHtml(r.subCategory || r.category)} ${matInfo}</div>${accTags ? `<div style="margin-top:3px;display:flex;gap:4px;flex-wrap:wrap;">${accTags}</div>` : ''}`;
          }
        },
        {
          key: 'category',
          label: 'Category',
          render: (r) => `<span class="pill pill-cyan">${escapeHtml(r.category)}</span>`
        },
        {
          key: 'fusion',
          label: 'Fusion / Grade',
          sortValue: (r) => r.fusion?.stat || (r.materia ? `G${r.materia.grade}` : 'zzz'),
          render: (r) =>
            r.fusion
              ? `<span class="pill pill-mako mono">${escapeHtml(r.fusion.stat)} +${r.fusion.perUnit}${r.fusion.stat.includes('%') ? '%' : ''} / ${r.fusion.unitsPerStep}x</span>`
              : r.materia
                ? `<span class="pill mono">G${r.materia.grade} · ${escapeHtml(r.materia.damageType)}</span>`
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

    if (mobileHost) {
      if (!filtered.length) {
        mobileHost.innerHTML = `<div class="empty-state">No matching items found.</div>`;
      } else {
        const sortedForMobile = [...filtered].sort((a, b) => a.name.localeCompare(b.name));
        mobileHost.innerHTML = sortedForMobile
          .map((r) => {
            const loot = ctx.getItemLootSources(r.id);
            const enemyCount = new Set([
              ...loot.commonDrop.map((e) => e.id),
              ...loot.rareDrop.map((e) => e.id),
              ...loot.commonSteal.map((e) => e.id),
              ...loot.rareSteal.map((e) => e.id)
            ]).size;
            const matInfo = r.materia
              ? `<span class="pill mono">G${r.materia.grade}${r.materia.cost ? ` · ${r.materia.cost} ${r.materia.costType}` : ''}</span>`
              : '';
            const fusionPill = r.fusion
              ? `<span class="pill pill-mako mono">${escapeHtml(r.fusion.stat)} +${r.fusion.perUnit}${r.fusion.stat.includes('%') ? '%' : ''}/${r.fusion.unitsPerStep}x</span>`
              : '';
            const accTags = (r.accessory?.effectTags || [])
              .slice(0, 2)
              .map((t) => `<span class="pill pill-mako">${escapeHtml(t)}</span>`)
              .join('');

            return `
              <article class="m-card" data-item-route="#/game/${escapeHtml(ctx.meta.slug)}/items/${encodeURIComponent(r.id)}">
                <div class="m-card-top">
                  <div class="m-card-body">
                    <div class="m-card-head">
                      <span class="m-card-title" style="margin-top:0;">${escapeHtml(r.name)}</span>
                      <span class="pill pill-cyan">${escapeHtml(r.category)}</span>
                    </div>
                    <div class="m-card-meta" style="margin-top:4px;">
                      <span>${escapeHtml(r.subCategory || r.category)}</span>
                      ${matInfo}
                      ${fusionPill}
                      ${accTags}
                    </div>
                    <div class="m-card-meta mono" style="margin-top:5px;">
                      <span>${enemyCount} enemies</span>
                      <span>·</span>
                      <span>${r.shops?.length || 0} shops</span>
                      <span>·</span>
                      <span>${(r.clearRewardMissions?.length || 0) + (r.treasureMissions?.length || 0)} missions</span>
                    </div>
                  </div>
                  <span class="m-card-chevron">${icon('chevron-right', 16)}</span>
                </div>
              </article>
            `;
          })
          .join('');

        mobileHost.querySelectorAll('.m-card[data-item-route]').forEach((card) => {
          card.addEventListener('click', () => {
            ctx.router.navigate(card.dataset.itemRoute);
          });
        });
      }
    }
  }

  container.querySelectorAll('#item-cats .chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      vs.activeCat = btn.dataset.cat;
      container.querySelectorAll('#item-cats .chip').forEach((b) => b.classList.toggle('active', b === btn));
      renderSubfilters();
      update();
    });
  });
  searchEl.addEventListener('input', () => {
    vs.search = searchEl.value;
    update();
  });
  resetBtn?.addEventListener('click', () => {
    vs.activeCat = 'all';
    vs.materiaSub = 'All';
    vs.materiaGrade = 'All';
    vs.accTag = 'All';
    vs.search = '';
    searchEl.value = '';
    container.querySelectorAll('#item-cats .chip').forEach((b) => b.classList.toggle('active', b.dataset.cat === 'all'));
    renderSubfilters();
    update();
  });

  renderSubfilters();
  update();
}

function renderItemDossier(container, ctx, item) {
  const loot = ctx.getItemLootSources(item.id);
  const slug = ctx.meta.slug;

  const renderQuadrant = (title, qClass, toneClass, enemies) => {
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
            const port = ctx.resolvePortrait(en);
            return `
              <div class="enemy-source-row">
                <div class="enemy-thumb" data-zoom-eid="${escapeHtml(en.id)}" title="Tap to zoom ${escapeHtml(en.name)}" style="width:52px;height:52px;">
                  <img referrerpolicy="no-referrer" src="${escapeHtml(port.primary)}" alt="${escapeHtml(en.name)}" loading="lazy" onerror="if(this.dataset.step!=='1'){this.dataset.step='1';this.src='${escapeHtml(port.secondary)}';}else{this.onerror=null;this.src='${escapeHtml(port.fallback)}';}" />
                </div>
                <div style="min-width:0;flex:1;">
                  <div style="display:flex;justify-content:space-between;gap:6px;align-items:center;flex-wrap:wrap;">
                    <a href="#/game/${escapeHtml(slug)}/enemies/${encodeURIComponent(en.id)}" style="font-weight:700;">${escapeHtml(en.name)}</a>
                    <span class="small muted mono">Lv.${en.stats?.level ?? '?'} · HP ${formatNum(en.stats?.hpHard)}</span>
                  </div>
                  <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px;">
                    ${missionBadges || (en.storyChapter ? `<a class="pill pill-link pill-warn mono" href="#/game/${escapeHtml(slug)}/story/ch_${en.storyChapter}">Story Ch.${en.storyChapter}</a>` : '<span class="small muted">Story / Field</span>')} ${more}
                  </div>
                </div>
              </div>
            `;
          })
          .join('')
      : '<div class="small muted">No enemy sources in this slot.</div>';

    return `
      <div class="matrix-quadrant ${qClass}">
        <h4><span>${escapeHtml(title)}</span><span class="pill ${toneClass}">${enemies.length}</span></h4>
        ${body}
      </div>
    `;
  };

  const shopsHtml = (item.shops || []).length
    ? item.shops
        .map((s) => {
          const shopObj = ctx.indexes.shopByName?.get(String(s.shopName || '').toLowerCase());
          const shopHref = shopObj ? `#/game/${escapeHtml(slug)}/compendium/shops/${encodeURIComponent(shopObj.id)}` : null;
          return `
            <div class="enemy-source-row" style="justify-content:space-between;align-items:center;">
              <div style="min-width:0;">
                ${
                  shopHref
                    ? `<a href="${shopHref}" style="font-weight:700;">${escapeHtml(s.shopName)} <span class="small muted">→</span></a>`
                    : `<strong>${escapeHtml(s.shopName)}</strong>`
                }
                ${s.unlockHint ? `<div class="small muted">${escapeHtml(s.unlockHint)}</div>` : ''}
              </div>
              <span class="pill pill-warn mono">${formatNum(s.price)} Gil</span>
            </div>
          `;
        })
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

  const recipes = item.category === 'materia' && ctx.findRecipesForMateria ? ctx.findRecipesForMateria(item.id) : [];
  const matMeta = item.materia;
  const fusionClass = ctx.data.fusionRules?.materiaCatalog?.[item.id]?.fusionClass;

  const renderIngredientLink = (name, itemId) => {
    if (itemId && ctx.indexes.itemById.has(itemId)) {
      return `<a href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(itemId)}" style="color:var(--accent);font-weight:700;">${escapeHtml(name)}</a>`;
    }
    return `<span style="color:var(--accent);font-weight:700;">${escapeHtml(name)}</span>`;
  };

  container.innerHTML = `
    ${renderDossierNavBar({
      router: ctx.router,
      listRoute: `#/game/${escapeHtml(slug)}/items`,
      listLabel: 'All Items'
    })}

    <div class="dossier-header">
      <div style="flex:1;min-width:240px;">
        <div class="brand-sub">${escapeHtml(item.category)} · ${escapeHtml(item.subCategory || 'General')}</div>
        <h1 style="margin:4px 0 6px;">${escapeHtml(item.name)}</h1>
        <p style="margin:0 0 8px;" class="muted">${escapeHtml(item.description || 'No description available.')}</p>
        ${
          matMeta
            ? `<div style="display:flex;flex-wrap:wrap;gap:6px;">
                <span class="pill pill-mako mono">Grade ${matMeta.grade}</span>
                ${fusionClass ? `<span class="pill pill-cyan">Class: ${escapeHtml(fusionClass)}</span>` : ''}
                ${matMeta.cost ? `<span class="pill pill-warn mono">${matMeta.cost} ${escapeHtml(matMeta.costType)}</span>` : ''}
                <span class="pill">${escapeHtml(matMeta.damageType)}</span>
                ${matMeta.spConvert ? `<span class="pill mono">SP Convert: ${formatNum(matMeta.spConvert.lv1)}–${formatNum(matMeta.spConvert.mastered)}</span>` : ''}
              </div>`
            : ''
        }
        ${
          item.accessory?.effectTags?.length
            ? `<div style="display:flex;flex-wrap:wrap;gap:6px;">${item.accessory.effectTags.map((t) => `<span class="pill pill-mako">${escapeHtml(t)}</span>`).join('')}</div>`
            : ''
        }
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

    ${
      item.category === 'materia'
        ? `
      <section class="card card-glow" style="margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
          <h3 style="margin:0;">How to Fuse ${escapeHtml(item.name)} (Reverse Recipes)</h3>
          <button class="btn btn-sm btn-primary" id="btn-open-fusion">Open in Fusion Calc →</button>
        </div>
        ${
          recipes.length
            ? `<div class="grid-2">${recipes
                .map(
                  (rc, idx) => `
                  <div class="sub-panel" style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                    <div style="min-width:0;">
                      <div class="small mono">${renderIngredientLink(rc.ingredientA, rc.aId)} <span class="muted">+</span> ${renderIngredientLink(rc.ingredientB, rc.bId)}</div>
                      <div class="small muted" style="margin-top:3px;">${escapeHtml(rc.note)}</div>
                    </div>
                    ${rc.aId && rc.bId ? `<button type="button" class="btn btn-sm" data-try-rec="${idx}">Try</button>` : ''}
                  </div>
                `
                )
                .join('')}</div>`
            : '<div class="small muted">Obtain via shops, mission rewards, or chests below.</div>'
        }
      </section>
    `
        : ''
    }

    <section class="card" style="margin-bottom:16px;">
      <h3 style="margin-top:0;">4-Quadrant Enemy Drop & Steal Matrix <span class="small muted">(Live from Bestiary)</span></h3>
      <div class="matrix-grid">
        ${renderQuadrant('Common Drop', 'q-cd', 'pill-mako', loot.commonDrop)}
        ${renderQuadrant('Rare Drop (Mog\'s Amulet)', 'q-rd', 'pill-cyan', loot.rareDrop)}
        ${renderQuadrant('Common Steal', 'q-cs', 'pill-warn', loot.commonSteal)}
        ${renderQuadrant('Rare Steal', 'q-rs', 'pill-danger', loot.rareSteal)}
      </div>
    </section>

    <div class="grid-3">
      <section class="card">
        <h3 style="margin-top:0;">Shops & Gil</h3>
        ${shopsHtml}
      </section>
      <section class="card">
        <h3 style="margin-top:0;">Mission Clear Rewards</h3>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">${missionLinks(item.clearRewardMissions || [])}</div>
      </section>
      <section class="card">
        <h3 style="margin-top:0;">Treasure Chests</h3>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">${missionLinks(item.treasureMissions || [])}</div>
      </section>
    </div>
  `;

  wireDossierNavBar(container, ctx.router);

  container.querySelector('#btn-open-fusion')?.addEventListener('click', () => {
    const first = recipes.find((r) => r.aId && r.bId);
    if (first) {
      ctx.storage.set('fusionPreload', { matA: first.aId, matB: first.bId });
    } else {
      ctx.storage.set('fusionPreload', { matA: item.id, matB: 'item_libra' });
    }
    ctx.router.navigate(`#/game/${slug}/fusion-tracker`);
  });

  container.querySelectorAll('[data-try-rec]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const rc = recipes[Number(btn.dataset.tryRec)];
      if (!rc) return;
      ctx.storage.set('fusionPreload', {
        matA: rc.aId,
        matB: rc.bId,
        masterA: rc.ingredientA.includes('Mastered'),
        masterB: rc.ingredientB.includes('Mastered')
      });
      ctx.router.navigate(`#/game/${slug}/fusion-tracker`);
    });
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
