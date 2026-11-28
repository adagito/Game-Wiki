import { escapeHtml, formatNum, icon, openLightbox, showToast } from '../../../core/ui.js';

export function renderStoryView(container, ctx, selectedParam = null) {
  const slug = ctx.meta.slug;
  const extra = ctx.data.extra || {};
  const chapters = extra.storyChapters || [];
  const minigames = extra.minigames || [];
  const magicPots = extra.magicPotEncounters || [];

  let activeTab = ctx.storage.get('storyTab', 'chapters');
  let activeChapterId = ctx.storage.get('activeStoryChapter', chapters[0]?.id || 'ch_1');

  if (selectedParam) {
    if (selectedParam === 'minigames' || selectedParam === 'magic-pot' || selectedParam === 'chapters') {
      activeTab = selectedParam;
    } else if (chapters.some((c) => c.id === selectedParam)) {
      activeTab = 'chapters';
      activeChapterId = selectedParam;
    }
  }

  const safeState = {
    books: 4,
    faces: 2,
    cans: 1,
    chairs: 7
  };

  function syncStoryRoute() {
    const rootCrumb = { label: 'Crisis Core', route: `#/game/${slug}/dashboard` };
    const storyCrumb = { label: 'Story & Side-Quests', route: `#/game/${slug}/story` };
    if (activeTab === 'minigames') {
      ctx.router.replaceCurrent(`#/game/${slug}/story/minigames`, {
        label: 'Mini-Games & Safe Code',
        typeLabel: 'Story',
        breadcrumbs: [rootCrumb, storyCrumb, { label: 'Mini-Games & Safe Code', route: null }]
      });
    } else if (activeTab === 'magic-pot') {
      ctx.router.replaceCurrent(`#/game/${slug}/story/magic-pot`, {
        label: 'Magic Pots (All 6)',
        typeLabel: 'Story',
        breadcrumbs: [rootCrumb, storyCrumb, { label: 'Magic Pots', route: null }]
      });
    } else {
      const ch = chapters.find((c) => c.id === activeChapterId) || chapters[0];
      if (ch) {
        ctx.router.replaceCurrent(`#/game/${slug}/story/${encodeURIComponent(ch.id)}`, {
          label: `Ch. ${ch.chapter}: ${ch.title}`,
          typeLabel: 'Story',
          breadcrumbs: [rootCrumb, storyCrumb, { label: `Chapter ${ch.chapter}`, route: null }]
        });
      }
    }
  }

  function render() {
    const storyDone = ctx.storage.get('storyDone', {});
    const magicPotDone = ctx.storage.get('magicPotDone', {});
    const chCount = chapters.filter((c) => storyDone[c.id]).length;
    const mpCount = magicPots.filter((mp) => magicPotDone[mp.id]).length;

    container.innerHTML = `
      <div class="section-header">
        <div>
          <div class="brand-sub">Main Scenario, Side-Quests & Special Encounters</div>
          <h1>Story Walkthrough, Mini-Games & Magic Pots</h1>
          <p class="muted small" style="margin:4px 0 0;">Complete Chapters 1–10 walkthroughs with story boss dossiers, all 10 mini-games + Safe Code solver, and all 6 Magic Pot sequences.</p>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">
          <span class="pill pill-mako mono">Chapters ${chCount}/${chapters.length}</span>
          <span class="pill pill-cyan mono">Magic Pots ${mpCount}/${magicPots.length}</span>
        </div>
      </div>

      <div class="seg-tabs" id="story-tabs">
        <button class="seg-tab ${activeTab === 'chapters' ? 'active' : ''}" data-stab="chapters">Chapters 1–10</button>
        <button class="seg-tab ${activeTab === 'minigames' ? 'active' : ''}" data-stab="minigames">Mini-Games & Safe Code</button>
        <button class="seg-tab ${activeTab === 'magic-pot' ? 'active' : ''}" data-stab="magic-pot">Magic Pot (All 6)</button>
      </div>

      <div id="story-body"></div>
    `;

    const body = container.querySelector('#story-body');

    if (activeTab === 'chapters') {
      const chIndex = Math.max(0, chapters.findIndex((c) => c.id === activeChapterId));
      const ch = chapters[chIndex] || chapters[0];
      const prevCh = chIndex > 0 ? chapters[chIndex - 1] : null;
      const nextCh = chIndex < chapters.length - 1 ? chapters[chIndex + 1] : null;
      const isDone = Boolean(storyDone[ch?.id]);

      body.innerHTML = `
        <div class="chip-row" id="ch-chips">
          ${chapters
            .map(
              (c) =>
                `<button class="chip ${c.id === ch?.id ? 'active' : ''}" data-chid="${escapeHtml(c.id)}">${storyDone[c.id] ? '✓ ' : ''}Ch. ${c.chapter}</button>`
            )
            .join('')}
        </div>

        ${
          ch
            ? `
          <article class="card card-glow" style="margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
              <div>
                <div class="brand-sub">${escapeHtml(ch.location)}</div>
                <h2 style="margin:2px 0 4px;">${escapeHtml(ch.title)}</h2>
                <p class="prose muted" style="margin:0;">${escapeHtml(ch.summary)}</p>
              </div>
              <label class="btn btn-sm ${isDone ? 'btn-primary' : ''}" style="cursor:pointer;">
                <input type="checkbox" id="ch-done-chk" ${isDone ? 'checked' : ''} style="margin-right:6px;" />
                ${isDone ? '✓ Chapter Cleared' : 'Mark Chapter Cleared'}
              </label>
            </div>

            ${ch.missableAlert ? `<div class="alert alert-danger small" style="margin-bottom:14px;">${escapeHtml(ch.missableAlert)}</div>` : ''}

            <div class="grid-2" style="margin-bottom:14px;">
              <div class="sub-panel">
                <h4 style="margin:0 0 8px;color:var(--accent);">Key Story & Missable Objectives</h4>
                <ul class="boss-bullet-list small">
                  ${(ch.keyObjectives || []).map((obj) => `<li>${escapeHtml(obj)}</li>`).join('')}
                </ul>
              </div>
              <div class="sub-panel">
                <h4 style="margin:0 0 8px;color:var(--accent-secondary);">Notable Chapter Pickups & Unlocks</h4>
                <div style="display:flex;flex-wrap:wrap;gap:6px;">
                  ${(ch.storyPickups || []).map((pk) => `<span class="pill pill-cyan">${escapeHtml(pk)}</span>`).join('')}
                </div>
              </div>
            </div>

            <h3 style="margin:0 0 10px;">Story Bosses in Chapter ${ch.chapter}</h3>
            <div class="grid-2">
              ${(ch.bosses || [])
                .map((b) => {
                  const en = ctx.indexes.enemyById.get(b.enemyId);
                  const port = ctx.resolvePortrait(en);
                  const affWeak = (en?.affinities?.weak || []).join(', ');
                  const affAbs = (en?.affinities?.absorb || []).join(', ');
                  return `
                  <div class="sub-panel" style="display:flex;gap:12px;align-items:flex-start;">
                    ${
                      en
                        ? `
                      <div class="enemy-thumb js-story-zoom" data-eid="${escapeHtml(en.id)}" style="width:62px;height:62px;flex-shrink:0;" title="Tap to zoom">
                        <img referrerpolicy="no-referrer" src="${escapeHtml(port.primary)}" alt="${escapeHtml(en.name)}" onerror="if(this.dataset.step!=='1'){this.dataset.step='1';this.src='${escapeHtml(port.secondary)}';}else{this.onerror=null;this.src='${escapeHtml(port.fallback)}';}" />
                      </div>
                    `
                        : ''
                    }
                    <div style="min-width:0;flex:1;">
                      <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;flex-wrap:wrap;">
                        ${
                          en
                            ? `<a href="#/game/${escapeHtml(slug)}/enemies/${encodeURIComponent(en.id)}" style="font-weight:700;">${escapeHtml(b.name)}</a>`
                            : `<strong>${escapeHtml(b.name)}</strong>`
                        }
                        ${en ? `<span class="pill pill-danger mono">Hard HP ${formatNum(en.stats?.hpHard)}</span>` : ''}
                      </div>
                      ${affWeak || affAbs ? `<div class="small muted mono" style="margin:3px 0;">${affWeak ? `Weak: ${escapeHtml(affWeak)}` : ''}${affWeak && affAbs ? ' · ' : ''}${affAbs ? `Absorb: ${escapeHtml(affAbs)}` : ''}</div>` : ''}
                      <div class="small" style="margin-top:4px;">${escapeHtml(b.tactics)}</div>
                    </div>
                  </div>
                `;
                })
                .join('')}
            </div>

            ${
              prevCh || nextCh
                ? `
              <div class="dossier-pager">
                <div>${prevCh ? `<button type="button" class="btn btn-sm" data-step-ch="${escapeHtml(prevCh.id)}">${icon('chevron-left', 14)} Chapter ${prevCh.chapter}</button>` : ''}</div>
                <div>${nextCh ? `<button type="button" class="btn btn-sm" data-step-ch="${escapeHtml(nextCh.id)}">Chapter ${nextCh.chapter} ${icon('chevron-right', 14)}</button>` : ''}</div>
              </div>
            `
                : ''
            }
          </article>
        `
            : ''
        }
      `;

      body.querySelectorAll('#ch-chips .chip, [data-step-ch]').forEach((btn) => {
        btn.addEventListener('click', () => {
          activeChapterId = btn.dataset.chid || btn.dataset.stepCh;
          ctx.storage.set('activeStoryChapter', activeChapterId);
          syncStoryRoute();
          render();
          window.scrollTo({ top: 0, behavior: 'smooth' });
        });
      });
      body.querySelector('#ch-done-chk')?.addEventListener('change', (e) => {
        const cur = ctx.storage.get('storyDone', {});
        cur[ch.id] = e.target.checked;
        ctx.storage.set('storyDone', cur);
        showToast(`Chapter ${ch.chapter} status saved`);
        render();
      });
      body.querySelectorAll('.js-story-zoom').forEach((el) => {
        el.addEventListener('click', () => {
          const en = ctx.indexes.enemyById.get(el.dataset.eid);
          if (!en) return;
          const port = ctx.resolvePortrait(en);
          openLightbox({
            src: port.primary,
            fallbackSrc: port.fallback,
            title: en.name,
            subtitle: `${en.family} · Hard HP ${formatNum(en.stats?.hpHard)}`
          });
        });
      });
    } else if (activeTab === 'minigames') {
      const code = `${safeState.books}${safeState.faces}${safeState.cans}${safeState.chairs}`;
      body.innerHTML = `
        <section class="card card-glow" style="margin-bottom:16px;">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
            <div>
              <div class="brand-sub">Seven Wonders of Nibelheim #4 (Chapter 8)</div>
              <h2 style="margin:2px 0 0;">Shinra Manor Safe Code Calculator</h2>
            </div>
            <div class="safe-code-display mono" id="safe-code-out">${escapeHtml(code)}</div>
          </div>
          <p class="small muted" style="margin:0 0 12px;">The 4-digit safe code is randomized per playthrough! Peek through the 4 keyholes in Shinra Manor rooms and enter the exact counts below:</p>
          <div class="grid-4">
            <div class="sub-panel">
              <label class="small muted">Digit 1: Books NOT on shelf (2F East)</label>
              <input type="number" min="0" max="9" class="input mono" id="safe-d1" value="${safeState.books}" style="width:100%;margin-top:6px;" />
            </div>
            <div class="sub-panel">
              <label class="small muted">Digit 2: Smiling Faces / Ghosts (2F West)</label>
              <input type="number" min="0" max="9" class="input mono" id="safe-d2" value="${safeState.faces}" style="width:100%;margin-top:6px;" />
            </div>
            <div class="sub-panel">
              <label class="small muted">Digit 3: Banora Apples & Cans (1F East)</label>
              <input type="number" min="0" max="9" class="input mono" id="safe-d3" value="${safeState.cans}" style="width:100%;margin-top:6px;" />
            </div>
            <div class="sub-panel">
              <label class="small muted">Digit 4: Chairs (1F West)</label>
              <input type="number" min="0" max="9" class="input mono" id="safe-d4" value="${safeState.chairs}" style="width:100%;margin-top:6px;" />
            </div>
          </div>
        </section>

        <div style="display:flex;flex-direction:column;gap:10px;">
          ${minigames
            .map(
              (mg, idx) => `
              <details class="guide-accordion" ${idx === 0 ? 'open' : ''}>
                <summary>
                  <div style="min-width:0;">
                    <strong style="font-size:1.02rem;">${escapeHtml(mg.title)}</strong>
                    <div class="small muted">${escapeHtml(mg.summary)}</div>
                  </div>
                  <div style="display:flex;gap:6px;flex-wrap:wrap;">
                    ${mg.missable ? '<span class="pill pill-danger">MISSABLE</span>' : ''}
                    <span class="pill pill-cyan mono">${escapeHtml(mg.chapter)}</span>
                    ${mg.trophy ? `<span class="pill pill-mako">${escapeHtml(mg.trophy)}</span>` : ''}
                  </div>
                </summary>
                <div class="guide-accordion-body">
                  <ul class="boss-bullet-list small" style="margin-top:10px;">
                    ${(mg.steps || []).map((st) => `<li>${escapeHtml(st)}</li>`).join('')}
                  </ul>
                </div>
              </details>
            `
            )
            .join('')}
        </div>
      `;

      const updateSafe = () => {
        const d1 = Math.max(0, Math.min(9, Number(body.querySelector('#safe-d1').value) || 0));
        const d2 = Math.max(0, Math.min(9, Number(body.querySelector('#safe-d2').value) || 0));
        const d3 = Math.max(0, Math.min(9, Number(body.querySelector('#safe-d3').value) || 0));
        const d4 = Math.max(0, Math.min(9, Number(body.querySelector('#safe-d4').value) || 0));
        safeState.books = d1;
        safeState.faces = d2;
        safeState.cans = d3;
        safeState.chairs = d4;
        body.querySelector('#safe-code-out').textContent = `${d1}${d2}${d3}${d4}`;
      };
      ['#safe-d1', '#safe-d2', '#safe-d3', '#safe-d4'].forEach((sel) => {
        body.querySelector(sel)?.addEventListener('input', updateSafe);
      });
    } else {
      body.innerHTML = `
        <div class="alert alert-warn small" style="margin-bottom:14px;">
          <strong>Magic Pot Rule:</strong> Never attack Magic Pot outright! Wait for each speech bubble and perform the <strong>exact 4 abilities in order</strong>. Clear <strong>M10-2-3</strong> first for Magic Pot DMW, and <strong>M7-6-6</strong> for the mandatory <strong>Genji Shield</strong>.
        </div>

        <div class="grid-2">
          ${magicPots
            .map((mp) => {
              const checked = Boolean(magicPotDone[mp.id]);
              const rewItem = mp.rewardItemId ? ctx.indexes.itemById.get(mp.rewardItemId) : null;
              return `
              <article class="card ${mp.missionId === 'M7-6-6' || mp.missionId === 'M10-2-3' ? 'card-glow' : ''}">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:8px;">
                  <label style="display:flex;align-items:flex-start;gap:8px;cursor:pointer;flex:1;">
                    <input type="checkbox" data-mp-chk="${escapeHtml(mp.id)}" ${checked ? 'checked' : ''} style="margin-top:4px;" />
                    <div>
                      <strong style="font-size:1.02rem;">${escapeHtml(mp.title)}</strong>
                      <div class="small muted">${escapeHtml(mp.priority)}</div>
                    </div>
                  </label>
                  <a class="pill pill-link pill-mako mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(mp.missionId)}">${escapeHtml(mp.missionId)}</a>
                </div>

                <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;align-items:center;">
                  ${(mp.requests || [])
                    .map((rq, idx) => {
                      const it = rq.itemId ? ctx.indexes.itemById.get(rq.itemId) : null;
                      const pill = it
                        ? `<a class="pill pill-link pill-cyan" href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(it.id)}">${rq.step}. ${escapeHtml(rq.action)}</a>`
                        : `<span class="pill pill-cyan">${rq.step}. ${escapeHtml(rq.action)}</span>`;
                      return `${pill}${idx < mp.requests.length - 1 ? '<span class="muted">→</span>' : ''}`;
                    })
                    .join('')}
                </div>

                <div class="small" style="margin-bottom:6px;">
                  <strong>Reward:</strong>
                  ${
                    rewItem
                      ? `<a class="pill pill-link pill-mako" href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(rewItem.id)}">${escapeHtml(mp.rewardName)}</a>`
                      : escapeHtml(mp.rewardName)
                  }
                </div>
                <div class="small muted">${escapeHtml(mp.tips)}</div>
              </article>
            `;
            })
            .join('')}
        </div>
      `;

      body.querySelectorAll('[data-mp-chk]').forEach((el) => {
        el.addEventListener('change', () => {
          const cur = ctx.storage.get('magicPotDone', {});
          cur[el.dataset.mpChk] = el.checked;
          ctx.storage.set('magicPotDone', cur);
          showToast('Magic Pot checklist updated');
          render();
        });
      });
    }

    container.querySelectorAll('#story-tabs .seg-tab').forEach((btn) => {
      btn.addEventListener('click', () => {
        activeTab = btn.dataset.stab;
        ctx.storage.set('storyTab', activeTab);
        syncStoryRoute();
        render();
      });
    });
  }

  render();
}
