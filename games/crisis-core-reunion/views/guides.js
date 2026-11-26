import { escapeHtml } from '../../../core/ui.js';

export function renderGuidesView(container, ctx, selectedSectionId = null) {
  const sections = ctx.data.guides.sections || [];
  const slug = ctx.meta.slug;

  container.innerHTML = `
    <div class="section-header">
      <div>
        <div class="brand-sub">Hard Mode Field Manual</div>
        <h1>📘 Dedicated Hard Mode Farming & Meta Guides</h1>
        <p class="muted small" style="margin:4px 0 0;">DMW mastering, Potion/Libra 98-980% fusion loops, EXP/SP/Gil missions, and Minerva survival meta.</p>
      </div>
    </div>

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

  if (selectedSectionId) {
    document.getElementById(selectedSectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}
