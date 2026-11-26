import { escapeHtml } from '../../../core/ui.js';

export function renderGuidesView(container, ctx, selectedSectionId = null) {
  const sections = ctx.data.guides.sections || [];
  const matrix = ctx.data.guides.farmingMatrix || [];
  const slug = ctx.meta.slug;
  const categories = ['All', ...Array.from(new Set(matrix.map((r) => r.category)))];
  let activeCat = 'All';

  function renderMatrixCards() {
    const host = container.querySelector('#farming-matrix-host');
    if (!host) return;
    const rows = matrix.filter((r) => activeCat === 'All' || r.category === activeCat);
    host.innerHTML = rows
      .map((r) => {
        const m = r.bestMissionId ? ctx.indexes.missionById.get(r.bestMissionId) : null;
        const en = r.enemyId ? ctx.indexes.enemyById.get(r.enemyId) : null;
        const it = r.itemId ? ctx.indexes.itemById.get(r.itemId) : null;
        return `
          <article class="card" style="background:var(--bg-secondary);display:flex;flex-direction:column;gap:7px;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">
              <strong style="color:var(--accent);">${escapeHtml(r.resource)}</strong>
              <span class="pill pill-cyan">${escapeHtml(r.category)}</span>
            </div>
            <div class="small"><strong>Setup:</strong> ${escapeHtml(r.setup)}</div>
            <div class="small muted">${escapeHtml(r.method)}</div>
            <div style="display:flex;flex-wrap:wrap;gap:5px;margin-top:auto;">
              ${m ? `<a class="pill pill-link pill-mako mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(m.id)}">${escapeHtml(m.id)} · ${escapeHtml(m.title)}</a>` : ''}
              ${en ? `<a class="pill pill-link pill-danger" href="#/game/${escapeHtml(slug)}/enemies/${encodeURIComponent(en.id)}">${escapeHtml(en.name)}</a>` : ''}
              ${it ? `<a class="pill pill-link pill-warn" href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(it.id)}">${escapeHtml(it.name)}</a>` : ''}
              <span class="pill mono">${escapeHtml(r.yield)}</span>
            </div>
          </article>
        `;
      })
      .join('');
  }

  container.innerHTML = `
    <div class="section-header">
      <div>
        <div class="brand-sub">Hard Mode Field Manual</div>
        <h1>📘 Farming, Leveling & Reunion Meta Guides</h1>
        <p class="muted small" style="margin:4px 0 0;">Complete Crisis Core Reunion routes: EXP/SP/Gil, all 8 fusion stats, 18-image DMW, Magic Pots, Buster Sword Proficiency, Missables, and Minerva.</p>
      </div>
    </div>

    <section class="card card-glow" style="margin-bottom:18px;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
        <h2 style="margin:0;font-size:1.15rem;">🌾 Quick Farming Matrix (All Resources)</h2>
        <div class="chip-row" id="farm-cats" style="margin:0;">
          ${categories.map((c) => `<button class="chip ${c === 'All' ? 'active' : ''}" data-fcat="${escapeHtml(c)}">${escapeHtml(c)}</button>`).join('')}
        </div>
      </div>
      <div class="grid-2" id="farming-matrix-host"></div>
    </section>

    <div class="chip-row">
      ${sections
        .map(
          (s) =>
            `<a class="chip ${selectedSectionId === s.id ? 'active' : ''}" href="#/game/${escapeHtml(slug)}/guides/${encodeURIComponent(s.id)}">${escapeHtml(s.title)}</a>`
        )
        .join('')}
    </div>

    <div style="display:flex;flex-direction:column;gap:16px;">
      ${sections
        .map((sec) => {
          const mRefs = (sec.refs?.missions || [])
            .map((mid) => {
              const m = ctx.indexes.missionById.get(mid);
              return `<a class="pill pill-link pill-mako mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(mid)}">${escapeHtml(mid)}${m ? ` · ${escapeHtml(m.title)}` : ''}</a>`;
            })
            .join(' ');
          const iRefs = (sec.refs?.items || [])
            .map((iid) => {
              const it = ctx.indexes.itemById.get(iid);
              return it ? `<a class="pill pill-link pill-cyan" href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(it.id)}">${escapeHtml(it.name)}</a>` : '';
            })
            .join(' ');
          const isFocus = selectedSectionId === sec.id;
          return `
            <article class="card ${isFocus ? 'card-glow' : ''}" id="${escapeHtml(sec.id)}">
              <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px;">
                <h2 style="margin:0;font-size:1.2rem;">${escapeHtml(sec.title)}</h2>
                <span class="pill pill-mako">${escapeHtml(sec.badge || 'Guide')}</span>
              </div>
              <p class="muted small" style="margin-top:0;">${escapeHtml(sec.summary)}</p>
              <div class="grid-2" style="margin-bottom:12px;">
                ${(sec.blocks || [])
                  .map(
                    (b) => `
                    <div class="card" style="background:var(--bg-secondary);">
                      <h4 style="margin:0 0 6px;color:var(--accent);">${escapeHtml(b.heading)}</h4>
                      <p class="small" style="margin:0;">${escapeHtml(b.body)}</p>
                    </div>
                  `
                  )
                  .join('')}
              </div>
              <div style="display:flex;flex-wrap:wrap;gap:6px;">
                ${mRefs} ${iRefs}
              </div>
            </article>
          `;
        })
        .join('')}
    </div>
  `;

  renderMatrixCards();
  container.querySelectorAll('#farm-cats .chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      activeCat = btn.dataset.fcat;
      container.querySelectorAll('#farm-cats .chip').forEach((b) => b.classList.toggle('active', b === btn));
      renderMatrixCards();
    });
  });

  if (selectedSectionId) {
    document.getElementById(selectedSectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}
