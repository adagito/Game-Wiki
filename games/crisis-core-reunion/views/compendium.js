import { escapeHtml, formatNum, showToast } from '../../../core/ui.js';

export function renderCompendiumView(container, ctx, selectedSection = null) {
  let activeTab = ctx.storage.get('compendiumTab', 'shops');
  if (selectedSection === 'dmw' || selectedSection === 'missables' || selectedSection === 'shops') {
    activeTab = selectedSection;
  }

  let shopSearch = '';
  let missChapter = 'ALL';

  function render() {
    const slug = ctx.meta.slug;
    const shops = ctx.data.shops || [];
    const dmwImages = ctx.data.guides.dmwImages || [];
    const missables = ctx.data.guides.missablesByChapter || [];

    const unlockedShops = ctx.storage.get('unlockedShops', { shop_shinra_shop: true });
    const dmwDone = ctx.storage.get('dmwDone', {});
    const missablesDone = ctx.storage.get('missablesDone', {});

    const shopCount = shops.filter((s) => unlockedShops[s.id]).length;
    const dmwCount = dmwImages.filter((d) => dmwDone[d.id]).length;
    const missCount = missables.filter((m) => missablesDone[m.id]).length;

    container.innerHTML = `
      <div class="section-header">
        <div>
          <div class="brand-sub">Reunion 100% Completion</div>
          <h1>🏪 Shops, 18-Image DMW & Missables</h1>
          <p class="muted small" style="margin:4px 0 0;">Track all 16 network shops, 18 DMW entries for Genji Armor, and every chapter-locked missable.</p>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">
          <span class="pill pill-mako mono">Shops ${shopCount}/${shops.length}</span>
          <span class="pill pill-cyan mono">DMW ${dmwCount}/${dmwImages.length}</span>
          <span class="pill pill-warn mono">Missables ${missCount}/${missables.length}</span>
        </div>
      </div>

      <div class="seg-tabs" id="comp-tabs">
        <button class="seg-tab ${activeTab === 'shops' ? 'active' : ''}" data-ctab="shops">🏪 All 16 Shops</button>
        <button class="seg-tab ${activeTab === 'dmw' ? 'active' : ''}" data-ctab="dmw">🎰 18-Image DMW Tracker</button>
        <button class="seg-tab ${activeTab === 'missables' ? 'active' : ''}" data-ctab="missables">⚠️ Chapter Missables</button>
      </div>

      <div id="comp-body"></div>
    `;

    const body = container.querySelector('#comp-body');

    if (activeTab === 'shops') {
      const q = shopSearch.trim().toLowerCase();
      const filteredShops = shops.filter((sh) => {
        if (!q) return true;
        const stockNames = (sh.stock || []).map((st) => ctx.indexes.itemById.get(st.itemId)?.name || '').join(' ');
        return `${sh.name} ${sh.unlockCondition} ${stockNames}`.toLowerCase().includes(q);
      });

      body.innerHTML = `
        <div class="filter-bar">
          <input type="search" id="shop-search" class="input" style="flex:1;min-width:220px;" value="${escapeHtml(shopSearch)}" placeholder="Filter shops or stock (e.g. Mog's Amulet, Dualcast, Genji Helm, QMC+)..." />
          <span class="small muted mono">${filteredShops.length} shops</span>
        </div>
        <div class="grid-2">
          ${filteredShops
            .map((sh) => {
              const checked = Boolean(unlockedShops[sh.id]);
              return `
              <article class="card ${sh.missable ? 'card-glow' : ''}">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:6px;">
                  <div>
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                      <input type="checkbox" data-shop-chk="${escapeHtml(sh.id)}" ${checked ? 'checked' : ''} />
                      <strong style="font-size:1.05rem;">${escapeHtml(sh.name)}</strong>
                    </label>
                    ${sh.quote ? `<div class="small muted" style="font-style:italic;margin-top:2px;">"${escapeHtml(sh.quote)}"</div>` : ''}
                  </div>
                  <div style="display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end;">
                    ${sh.missable ? '<span class="pill pill-danger">MISSABLE</span>' : ''}
                    <span class="pill pill-cyan mono">Ch.${sh.chapterAvailable}+</span>
                  </div>
                </div>
                <div class="small" style="margin-bottom:10px;">
                  <strong>Unlock:</strong> ${escapeHtml(sh.unlockCondition)}
                  ${sh.unlockMissionId ? ` <a class="pill pill-link pill-mako mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(sh.unlockMissionId)}">${escapeHtml(sh.unlockMissionId)}</a>` : ''}
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:6px;">
                  ${(sh.stock || [])
                    .map((st) => {
                      const it = ctx.indexes.itemById.get(st.itemId);
                      return `<a class="pill pill-link" href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(st.itemId)}">${escapeHtml(it?.name || st.itemId)} <span class="mono muted">${formatNum(st.price)}g</span></a>`;
                    })
                    .join('')}
                </div>
              </article>
            `;
            })
            .join('')}
        </div>
      `;

      body.querySelector('#shop-search').addEventListener('input', (e) => {
        shopSearch = e.target.value;
        render();
        const inp = container.querySelector('#shop-search');
        if (inp) {
          inp.focus();
          inp.setSelectionRange(inp.value.length, inp.value.length);
        }
      });
      body.querySelectorAll('[data-shop-chk]').forEach((el) => {
        el.addEventListener('change', () => {
          const cur = ctx.storage.get('unlockedShops', { shop_shinra_shop: true });
          cur[el.dataset.shopChk] = el.checked;
          ctx.storage.set('unlockedShops', cur);
          showToast('Shop checklist updated');
          render();
        });
      });
    } else if (activeTab === 'dmw') {
      const pct = dmwImages.length ? Math.round((dmwCount / dmwImages.length) * 100) : 0;
      const groups = ['Character', 'Summon', 'Chocobo Mode'];

      body.innerHTML = `
        <div class="card card-glow" style="margin-bottom:16px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <strong>DMW 18-Image Roster (100% DMW → Genji Armor)</strong>
            <span class="mono pill pill-mako">${dmwCount}/${dmwImages.length} (${pct}%)</span>
          </div>
          <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
          <div class="alert alert-warn" style="margin-top:10px;">
            ⚠️ <strong>Phoenix (Rebirth Flame)</strong> in Chapter 8 Nibelheim (Water Tower Seven Wonder) is the <strong>ONLY missable DMW image</strong>. Trigger Summons/Chocobo Modes once for instant 100%; view all 6 memories per Character via M1-1-1 AFK + boost Materia.
          </div>
        </div>

        ${groups
          .map((grp) => {
            const list = dmwImages.filter((d) => d.group === grp);
            return `
            <section class="card" style="margin-bottom:14px;">
              <h3 style="margin-top:0;">${escapeHtml(grp)}s (${list.length})</h3>
              <div class="grid-3">
                ${list
                  .map((d) => {
                    const checked = Boolean(dmwDone[d.id]);
                    const mat = d.boostMateriaId ? ctx.indexes.itemById.get(d.boostMateriaId) : null;
                    return `
                    <div class="card" style="background:var(--bg-secondary);">
                      <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:4px;">
                        <label style="display:flex;align-items:center;gap:6px;cursor:pointer;">
                          <input type="checkbox" data-dmw-chk="${escapeHtml(d.id)}" ${checked ? 'checked' : ''} />
                          <strong>${escapeHtml(d.name)}</strong>
                        </label>
                        ${d.missable ? '<span class="pill pill-danger">MISSABLE</span>' : `<span class="pill pill-cyan">${escapeHtml(d.limitBreak)}</span>`}
                      </div>
                      <div class="small muted" style="margin-bottom:6px;">${escapeHtml(d.unlockCondition)}</div>
                      <div style="display:flex;flex-wrap:wrap;gap:4px;">
                        ${d.missionId ? `<a class="pill pill-link pill-mako mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(d.missionId)}">${escapeHtml(d.missionId)}</a>` : ''}
                        ${mat ? `<a class="pill pill-link pill-cyan" href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(mat.id)}">Boost: ${escapeHtml(mat.name)}</a>` : ''}
                      </div>
                    </div>
                  `;
                  })
                  .join('')}
              </div>
            </section>
          `;
          })
          .join('')}
      `;

      body.querySelectorAll('[data-dmw-chk]').forEach((el) => {
        el.addEventListener('change', () => {
          const cur = ctx.storage.get('dmwDone', {});
          cur[el.dataset.dmwChk] = el.checked;
          ctx.storage.set('dmwDone', cur);
          showToast('DMW tracker saved');
          render();
        });
      });
    } else {
      const chapters = ['ALL', ...Array.from(new Set(missables.map((m) => m.chapter)))];
      const filtered = missables.filter((m) => missChapter === 'ALL' || m.chapter === missChapter);

      body.innerHTML = `
        <div class="alert alert-danger" style="margin-bottom:14px;">
          🚨 <strong>Point of No Return:</strong> Leaving Midgar at the end of <strong>Chapter 7</strong> permanently locks all Midgar NPC mission triggers, Fan Clubs, and Midgar mail senders.
        </div>

        <div class="chip-row" id="miss-chaps">
          ${chapters.map((c) => `<button class="chip ${missChapter === c ? 'active' : ''}" data-mchap="${escapeHtml(c)}">${escapeHtml(c)}</button>`).join('')}
        </div>

        <div style="display:flex;flex-direction:column;gap:10px;">
          ${filtered
            .map((m) => {
              const checked = Boolean(missablesDone[m.id]);
              return `
              <div class="card" style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
                <label style="display:flex;align-items:flex-start;gap:10px;cursor:pointer;flex:1;">
                  <input type="checkbox" data-miss-chk="${escapeHtml(m.id)}" ${checked ? 'checked' : ''} style="margin-top:4px;" />
                  <div>
                    <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:3px;">
                      <span class="pill pill-warn mono">${escapeHtml(m.chapter)}</span>
                      <strong>${escapeHtml(m.title)}</strong>
                      <span class="pill pill-cyan">${escapeHtml(m.category)}</span>
                    </div>
                    <div class="small muted">${escapeHtml(m.detail)}</div>
                  </div>
                </label>
                ${m.missionId ? `<a class="pill pill-link pill-mako mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(m.missionId)}">${escapeHtml(m.missionId)}</a>` : ''}
              </div>
            `;
            })
            .join('')}
        </div>
      `;

      body.querySelectorAll('#miss-chaps .chip').forEach((btn) => {
        btn.addEventListener('click', () => {
          missChapter = btn.dataset.mchap;
          render();
        });
      });
      body.querySelectorAll('[data-miss-chk]').forEach((el) => {
        el.addEventListener('change', () => {
          const cur = ctx.storage.get('missablesDone', {});
          cur[el.dataset.missChk] = el.checked;
          ctx.storage.set('missablesDone', cur);
          showToast('Missable progress saved');
          render();
        });
      });
    }

    container.querySelectorAll('#comp-tabs .seg-tab').forEach((btn) => {
      btn.addEventListener('click', () => {
        activeTab = btn.dataset.ctab;
        ctx.storage.set('compendiumTab', activeTab);
        render();
      });
    });
  }

  render();
}
