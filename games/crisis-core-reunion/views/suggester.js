import { escapeHtml, formatNum } from '../../../core/ui.js';

export function renderSuggesterView(container, ctx) {
  const zack = ctx.getZackState();
  let level = zack.level;
  let chapter = zack.chapter;
  const brackets = ctx.data.guides.levelBrackets || [];
  const baseStatsTable = ctx.data.extra?.mechanics?.zackBaseStats || [];

  function findBracket(lv) {
    return brackets.find((b) => lv >= b.minLevel && lv <= b.maxLevel) || brackets[brackets.length - 1];
  }

  function renderBody() {
    const bracket = findBracket(level);
    const completed = ctx.storage.get('completedMissions', {});
    const slug = ctx.meta.slug;
    const baseRow = baseStatsTable.find((r) => r.level === level);

    const candidates = ctx.data.missions
      .filter((m) => !completed[m.id] && m.chapterAvailable <= chapter)
      .map((m) => {
        const prereqs = m.prerequisiteMissionIds || [];
        const unlockable = prereqs.every((pid) => completed[pid]);
        return {
          mission: m,
          unlockable,
          ready: ctx.evaluateHardModeReadiness(m, level),
          delta: Math.abs((m.hardModeBenchmarks?.recommendedLevel || 1) - level)
        };
      })
      .filter((x) => x.ready.key !== 'danger')
      .sort((a, b) => Number(b.unlockable) - Number(a.unlockable) || a.delta - b.delta || a.mission.stars - b.mission.stars)
      .slice(0, 12);

    const priorityChips = (bracket.priorityMissions || [])
      .map((mid) => {
        const m = ctx.indexes.missionById.get(mid);
        const done = completed[mid];
        return `<a class="pill pill-link ${done ? 'pill-mako' : 'pill-warn'} mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(mid)}">${done ? '✓ ' : ''}${escapeHtml(mid)}${m ? ` · ${escapeHtml(m.title)}` : ''}</a>`;
      })
      .join(' ');

    container.innerHTML = `
      <div class="section-header">
        <div>
          <div class="brand-sub">Dynamic Tactical Planner</div>
          <h1>Hard Mode Leveling & Route Suggester</h1>
          <p class="muted small" style="margin:4px 0 0;">Set your current Zack Level and Story Chapter to get Hard Mode benchmarks, unlockable progression missions, and farming routes.</p>
        </div>
      </div>

      <div class="card card-glow" style="margin-bottom:16px;">
        <div class="grid-2" style="align-items:center;">
          <div>
            <label class="small muted">Current Zack Level: <strong id="lbl-lv" class="mono" style="color:var(--accent);font-size:1.05rem;">${level}</strong></label>
            <input type="range" id="rng-lv" min="1" max="99" value="${level}" style="width:100%;margin-top:6px;accent-color:var(--accent);" />
            ${
              baseRow
                ? `<div class="small muted mono" style="margin-top:6px;">Lv.${level} Base Stats: HP ${formatNum(baseRow.hp)} · MP ${baseRow.mp} · AP ${baseRow.ap} · ATK ${baseRow.atk} · VIT ${baseRow.vit} · MAG ${baseRow.mag} · SPR ${baseRow.spr} · LCK ${baseRow.lck}</div>`
                : ''
            }
          </div>
          <div>
            <label class="small muted">Current Story Chapter (1–10)</label>
            <select id="sel-ch" class="select" style="width:100%;margin-top:6px;">
              ${Array.from({ length: 10 }, (_, i) => `<option value="${i + 1}" ${chapter === i + 1 ? 'selected' : ''}>Chapter ${i + 1}</option>`).join('')}
            </select>
          </div>
        </div>
      </div>

      <div class="chip-row" id="bracket-tabs">
        ${brackets.map((b) => `<button class="chip ${b.id === bracket.id ? 'active' : ''}" data-lv="${b.minLevel}">${escapeHtml(b.label)}</button>`).join('')}
      </div>

      <div class="grid-2" style="margin-bottom:16px;">
        <section class="card">
          <h3 style="margin-top:0;">Target Hard Mode Benchmarks (${escapeHtml(bracket.label)})</h3>
          <div class="grid-3 mono" style="gap:10px;margin-bottom:12px;">
            <div class="card" style="background:var(--bg-secondary);padding:10px;"><div class="small muted">Target HP</div><strong>${escapeHtml(bracket.benchmarks.hp)}</strong></div>
            <div class="card" style="background:var(--bg-secondary);padding:10px;"><div class="small muted">Target VIT</div><strong>${escapeHtml(bracket.benchmarks.vit)}</strong></div>
            <div class="card" style="background:var(--bg-secondary);padding:10px;"><div class="small muted">Target SPR</div><strong>${escapeHtml(bracket.benchmarks.spr)}</strong></div>
          </div>
          <div class="small"><strong>Break Limit & Core Gear:</strong> ${escapeHtml(bracket.benchmarks.gear)}</div>
          <div style="margin-top:12px;">
            <div class="small muted" style="margin-bottom:6px;">High-Impact Milestone Missions</div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;">${priorityChips}</div>
          </div>
        </section>

        <section class="card">
          <h3 style="margin-top:0;">Tailored Farming Routes</h3>
          <div style="display:flex;flex-direction:column;gap:10px;" class="small">
            <div class="alert alert-mako"><strong>EXP Route:</strong> ${escapeHtml(bracket.expRoute)}</div>
            <div class="alert"><strong>SP & Gil Route:</strong> ${escapeHtml(bracket.spGilRoute)}</div>
            <div class="alert alert-warn"><strong>Materia Fusion Focus:</strong> ${escapeHtml(bracket.fusionFocus)}</div>
          </div>
        </section>
      </div>

      <section class="card">
        <h3 style="margin-top:0;">Best Progression Missions Right Now <span class="small muted">(Ch. ≤ ${chapter}, Incomplete, Unlockable First)</span></h3>
        <div class="grid-3">
          ${
            candidates.length
              ? candidates
                  .map(
                    ({ mission: m, ready, unlockable }) => `
                    <a class="card" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(m.id)}" style="background:var(--bg-secondary);display:flex;flex-direction:column;gap:6px;text-decoration:none;">
                      <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">
                        <strong class="mono" style="color:var(--accent);">${escapeHtml(m.id)}</strong>
                        <div style="display:flex;gap:4px;flex-wrap:wrap;">
                          ${unlockable ? '<span class="pill pill-cyan">Open</span>' : '<span class="pill">Chain</span>'}
                          <span class="pill ${ready.tone}">${m.stars}★ · ${ready.label}</span>
                        </div>
                      </div>
                      <div style="font-weight:600;color:var(--text-primary);">${escapeHtml(m.title)}</div>
                      <div class="small muted">Reward: ${escapeHtml(m.clearReward?.rawLabel || 'None')}</div>
                    </a>
                  `
                  )
                  .join('')
              : '<div class="empty-state">No uncompleted Ready/Stretch missions left in this chapter filter—advance chapters or check higher★ challenges!</div>'
          }
        </div>
      </section>
    `;

    container.querySelector('#rng-lv').addEventListener('input', (e) => {
      level = Number(e.target.value);
      ctx.storage.set('zackLevel', level);
      window.dispatchEvent(new CustomEvent('wiki:zack-updated'));
      renderBody();
    });
    container.querySelector('#sel-ch').addEventListener('change', (e) => {
      chapter = Number(e.target.value);
      ctx.storage.set('zackChapter', chapter);
      window.dispatchEvent(new CustomEvent('wiki:zack-updated'));
      renderBody();
    });
    container.querySelectorAll('#bracket-tabs .chip').forEach((btn) => {
      btn.addEventListener('click', () => {
        level = Number(btn.dataset.lv);
        ctx.storage.set('zackLevel', level);
        window.dispatchEvent(new CustomEvent('wiki:zack-updated'));
        renderBody();
      });
    });
  }

  renderBody();
}
