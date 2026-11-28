import { escapeHtml, formatNum, showToast } from '../../../core/ui.js';

const COMP_TABS = {
  trophies: '51 Trophies',
  mail: '20 Mail & Fan Clubs',
  shops: 'All 16 Shops',
  dmw: '18-Image DMW',
  missables: 'Chapter Missables'
};

export function renderCompendiumView(container, ctx, selectedSection = null) {
  const [secTab, focusId] = String(selectedSection || '').split('/');
  let activeTab = ctx.storage.get('compendiumTab', 'trophies');
  if (secTab && COMP_TABS[secTab]) {
    activeTab = secTab;
  }

  let shopSearch = '';
  let missChapter = 'ALL';
  let trophyGrade = 'ALL';
  let trophyMissOnly = false;
  let trophySearch = '';
  let mailCategory = 'ALL';
  let mailMissOnly = false;
  let didInitialFocusScroll = false;

  function syncTabRoute(tabId) {
    const slug = ctx.meta.slug;
    const label = COMP_TABS[tabId] || tabId;
    ctx.router.replaceCurrent(`#/game/${slug}/compendium/${tabId}`, {
      label,
      typeLabel: 'Tracker',
      breadcrumbs: [
        { label: 'Crisis Core', route: `#/game/${slug}/dashboard` },
        { label: 'Trackers & Trophies', route: `#/game/${slug}/compendium` },
        { label, route: null }
      ]
    });
  }

  function render() {
    const slug = ctx.meta.slug;
    const shops = ctx.data.shops || [];
    const dmwImages = ctx.data.guides.dmwImages || [];
    const missables = ctx.data.guides.missablesByChapter || [];
    const trophies = ctx.data.extra?.trophies || [];
    const mailSenders = ctx.data.extra?.mailSenders || [];

    const unlockedShops = ctx.storage.get('unlockedShops', { shop_shinra_shop: true });
    const dmwDone = ctx.storage.get('dmwDone', {});
    const missablesDone = ctx.storage.get('missablesDone', {});
    const trophiesDone = ctx.storage.get('trophiesDone', {});
    const mailDone = ctx.storage.get('mailDone', {});

    const shopCount = shops.filter((s) => unlockedShops[s.id]).length;
    const dmwCount = dmwImages.filter((d) => dmwDone[d.id]).length;
    const missCount = missables.filter((m) => missablesDone[m.id]).length;
    const trophyCount = trophies.filter((t) => trophiesDone[t.id]).length;
    const mailCount = mailSenders.filter((m) => mailDone[m.id]).length;

    container.innerHTML = `
      <div class="section-header">
        <div>
          <div class="brand-sub">Reunion 100% Completion Trackers</div>
          <h1>Trophies, Mail, Shops, DMW & Missables</h1>
          <p class="muted small" style="margin:4px 0 0;">Track all 51 Trophies, 20 Mail Senders & 5 Fan Clubs, 16 Shops, 18 DMW entries, and every chapter missable.</p>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">
          <span class="pill pill-mako mono">Trophies ${trophyCount}/${trophies.length}</span>
          <span class="pill pill-cyan mono">Mail ${mailCount}/${mailSenders.length}</span>
          <span class="pill pill-mako mono">Shops ${shopCount}/${shops.length}</span>
          <span class="pill pill-cyan mono">DMW ${dmwCount}/${dmwImages.length}</span>
          <span class="pill pill-warn mono">Missables ${missCount}/${missables.length}</span>
        </div>
      </div>

      <div class="seg-tabs" id="comp-tabs">
        <button class="seg-tab ${activeTab === 'trophies' ? 'active' : ''}" data-ctab="trophies">51 Trophies</button>
        <button class="seg-tab ${activeTab === 'mail' ? 'active' : ''}" data-ctab="mail">20 Mail & Fan Clubs</button>
        <button class="seg-tab ${activeTab === 'shops' ? 'active' : ''}" data-ctab="shops">All 16 Shops</button>
        <button class="seg-tab ${activeTab === 'dmw' ? 'active' : ''}" data-ctab="dmw">18-Image DMW</button>
        <button class="seg-tab ${activeTab === 'missables' ? 'active' : ''}" data-ctab="missables">Chapter Missables</button>
      </div>

      <div id="comp-body"></div>
    `;

    const body = container.querySelector('#comp-body');

    if (activeTab === 'trophies') {
      const pct = trophies.length ? Math.round((trophyCount / trophies.length) * 100) : 0;
      const q = trophySearch.trim().toLowerCase();
      const filtered = trophies.filter((t) => {
        if (trophyGrade !== 'ALL' && t.grade !== trophyGrade) return false;
        if (trophyMissOnly && !t.missable) return false;
        if (!q) return true;
        return `${t.name} ${t.description} ${t.howToUnlock} ${t.chapter} ${t.category}`.toLowerCase().includes(q);
      });

      const gradeCls = {
        Platinum: 'trophy-platinum',
        Gold: 'trophy-gold',
        Silver: 'trophy-silver',
        Bronze: 'trophy-bronze'
      };

      body.innerHTML = `
        <div class="card card-glow" style="margin-bottom:14px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <strong>PlayStation / Steam Achievement Progress (51 Total)</strong>
            <span class="mono pill pill-mako">${trophyCount}/${trophies.length} (${pct}%)</span>
          </div>
          <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
        </div>

        <div class="chip-row" id="tr-grades">
          ${['ALL', 'Platinum', 'Gold', 'Silver', 'Bronze']
            .map((g) => `<button class="chip ${trophyGrade === g ? 'active' : ''}" data-tgrade="${g}">${g === 'ALL' ? `All (${trophies.length})` : g}</button>`)
            .join('')}
        </div>

        <div class="filter-bar">
          <input type="search" id="tr-search" class="input" style="flex:1;min-width:200px;" value="${escapeHtml(trophySearch)}" placeholder="Filter trophies (e.g. Minerva, Safe, Fan Club, Mail, Waterfall)..." />
          <label class="small" style="display:flex;align-items:center;gap:6px;cursor:pointer;">
            <input type="checkbox" id="tr-miss-only" ${trophyMissOnly ? 'checked' : ''} /> Missable Only (${trophies.filter((t) => t.missable).length})
          </label>
          <span class="small muted mono">${filtered.length} shown</span>
        </div>

        <div style="display:flex;flex-direction:column;gap:8px;">
          ${filtered
            .map((t) => {
              const checked = Boolean(trophiesDone[t.id]);
              return `
              <div class="card" style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
                <label style="display:flex;align-items:flex-start;gap:10px;cursor:pointer;flex:1;">
                  <input type="checkbox" data-tr-chk="${escapeHtml(t.id)}" ${checked ? 'checked' : ''} style="margin-top:4px;" />
                  <div>
                    <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:3px;">
                      <span class="pill ${gradeCls[t.grade] || ''}">${escapeHtml(t.grade)}</span>
                      <strong>${escapeHtml(t.name)}</strong>
                      ${t.missable ? '<span class="pill pill-danger">MISSABLE</span>' : ''}
                      <span class="pill pill-cyan mono">${escapeHtml(t.chapter)}</span>
                    </div>
                    <div class="small" style="margin-bottom:2px;">${escapeHtml(t.description)}</div>
                    <div class="small muted">${escapeHtml(t.howToUnlock)}</div>
                  </div>
                </label>
                <div style="display:flex;flex-direction:column;gap:4px;align-items:flex-end;flex-shrink:0;">
                  ${t.missionId ? `<a class="pill pill-link pill-mako mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(t.missionId)}">${escapeHtml(t.missionId)}</a>` : ''}
                  ${t.storyChapterId ? `<a class="pill pill-link pill-cyan mono" href="#/game/${escapeHtml(slug)}/story/${encodeURIComponent(t.storyChapterId)}">${escapeHtml(t.storyChapterId.replace('ch_', 'Ch. '))}</a>` : ''}
                </div>
              </div>
            `;
            })
            .join('')}
        </div>
      `;

      body.querySelectorAll('#tr-grades .chip').forEach((btn) => {
        btn.addEventListener('click', () => {
          trophyGrade = btn.dataset.tgrade;
          render();
        });
      });
      body.querySelector('#tr-search')?.addEventListener('input', (e) => {
        trophySearch = e.target.value;
        render();
        const inp = container.querySelector('#tr-search');
        if (inp) {
          inp.focus();
          inp.setSelectionRange(inp.value.length, inp.value.length);
        }
      });
      body.querySelector('#tr-miss-only')?.addEventListener('change', (e) => {
        trophyMissOnly = e.target.checked;
        render();
      });
      body.querySelectorAll('[data-tr-chk]').forEach((el) => {
        el.addEventListener('change', () => {
          const cur = ctx.storage.get('trophiesDone', {});
          cur[el.dataset.trChk] = el.checked;
          ctx.storage.set('trophiesDone', cur);
          showToast('Trophy progress saved');
          render();
        });
      });
    } else if (activeTab === 'mail') {
      const categories = ['ALL', ...Array.from(new Set(mailSenders.map((m) => m.category)))];
      const filtered = mailSenders.filter((m) => {
        if (mailCategory !== 'ALL' && m.category !== mailCategory) return false;
        if (mailMissOnly && !m.missable) return false;
        return true;
      });

      body.innerHTML = `
        <div class="alert alert-danger small" style="margin-bottom:12px;">
          <strong>Mail Completionist & Fan Club Rule:</strong> All 20 senders must be triggered in a <strong>single playthrough</strong> before the Chapter 7 Midgar Point of No Return (and Squats/Reporter/Cissnei triggers). Never report the Sector 8 Reporter!
        </div>

        <div class="chip-row" id="mail-cats">
          ${categories.map((c) => `<button class="chip ${mailCategory === c ? 'active' : ''}" data-mcat="${escapeHtml(c)}">${escapeHtml(c)}</button>`).join('')}
        </div>

        <div class="filter-bar">
          <label class="small" style="display:flex;align-items:center;gap:6px;cursor:pointer;">
            <input type="checkbox" id="mail-miss-only" ${mailMissOnly ? 'checked' : ''} /> Missable Senders Only
          </label>
          <span class="small muted mono">${filtered.length} senders</span>
        </div>

        <div class="grid-2">
          ${filtered
            .map((ms) => {
              const checked = Boolean(mailDone[ms.id]);
              return `
              <article class="card ${ms.missable ? 'card-glow' : ''}">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:6px;">
                  <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                    <input type="checkbox" data-mail-chk="${escapeHtml(ms.id)}" ${checked ? 'checked' : ''} />
                    <strong style="font-size:1.02rem;">${escapeHtml(ms.name)}</strong>
                  </label>
                  <div style="display:flex;gap:4px;flex-wrap:wrap;">
                    ${ms.missable ? '<span class="pill pill-danger">MISSABLE</span>' : ''}
                    <span class="pill pill-cyan mono">${escapeHtml(ms.chapters)}</span>
                    <span class="pill pill-mako mono">${ms.mailCount} mails</span>
                  </div>
                </div>
                <div class="small" style="margin-bottom:6px;"><strong>How to Unlock:</strong> ${escapeHtml(ms.unlockCondition)}</div>
                <div class="small muted"><strong>Guardrail:</strong> ${escapeHtml(ms.missableChoices)}</div>
              </article>
            `;
            })
            .join('')}
        </div>
      `;

      body.querySelectorAll('#mail-cats .chip').forEach((btn) => {
        btn.addEventListener('click', () => {
          mailCategory = btn.dataset.mcat;
          render();
        });
      });
      body.querySelector('#mail-miss-only')?.addEventListener('change', (e) => {
        mailMissOnly = e.target.checked;
        render();
      });
      body.querySelectorAll('[data-mail-chk]').forEach((el) => {
        el.addEventListener('change', () => {
          const cur = ctx.storage.get('mailDone', {});
          cur[el.dataset.mailChk] = el.checked;
          ctx.storage.set('mailDone', cur);
          showToast('Mail sender checklist saved');
          render();
        });
      });
    } else if (activeTab === 'shops') {
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
              const isFocused = !didInitialFocusScroll && focusId === sh.id;
              return `
              <article class="card ${sh.missable ? 'card-glow' : ''} ${isFocused ? 'highlight-pulse' : ''}" id="shop-card-${escapeHtml(sh.id)}">
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

      if (!didInitialFocusScroll && focusId) {
        const targetCard = body.querySelector(`#shop-card-${CSS.escape(focusId)}`);
        if (targetCard) {
          didInitialFocusScroll = true;
          requestAnimationFrame(() => targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' }));
        }
      }

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
            <strong>Phoenix (Rebirth Flame)</strong> in Chapter 8 Nibelheim (Water Tower Seven Wonder) is the <strong>ONLY missable DMW image</strong>. Trigger Summons/Chocobo Modes once for instant 100%; view all 6 memories per Character via M1-1-1 AFK + boost Materia.
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
          <strong>Point of No Return:</strong> Leaving Midgar at the end of <strong>Chapter 7</strong> permanently locks all Midgar NPC mission triggers, Fan Clubs, Flower Wagons, and Midgar mail senders.
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
        syncTabRoute(activeTab);
        render();
      });
    });
  }

  render();
}
