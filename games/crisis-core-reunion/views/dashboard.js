import { escapeHtml, showToast } from '../../../core/ui.js';

export function renderDashboardView(container, ctx) {
  const slug = ctx.meta.slug;

  function render() {
    const zack = ctx.getZackState();
    const missions = ctx.data.missions || [];
    const shops = ctx.data.shops || [];
    const dmwImages = ctx.data.guides.dmwImages || [];
    const missables = ctx.data.guides.missablesByChapter || [];
    const extra = ctx.data.extra || {};
    const trophies = extra.trophies || [];
    const mailSenders = extra.mailSenders || [];
    const storyChapters = extra.storyChapters || [];
    const magicPots = extra.magicPotEncounters || [];

    const unlockedShops = ctx.storage.get('unlockedShops', { shop_shinra_shop: true });
    const dmwDone = ctx.storage.get('dmwDone', {});
    const missablesDone = ctx.storage.get('missablesDone', {});
    const trophiesDone = ctx.storage.get('trophiesDone', {});
    const mailDone = ctx.storage.get('mailDone', {});
    const storyDone = ctx.storage.get('storyDone', {});
    const magicPotDone = ctx.storage.get('magicPotDone', {});
    const bs = ctx.storage.get('busterProficiency', { guard: 0, strong: 0, command: 0, barrier: 0 });
    const bsTotal = Math.min(100, (Number(bs.guard) || 0) + (Number(bs.strong) || 0) + (Number(bs.command) || 0) + (Number(bs.barrier) || 0));

    const mDone = missions.filter((m) => zack.completedMissions[m.id]).length;
    const trDone = trophies.filter((t) => trophiesDone[t.id]).length;
    const shDone = shops.filter((s) => unlockedShops[s.id]).length;
    const dmwCount = dmwImages.filter((d) => dmwDone[d.id]).length;
    const mailCount = mailSenders.filter((ms) => mailDone[ms.id]).length;
    const stCount = storyChapters.filter((sc) => storyDone[sc.id]).length;
    const missCount = missables.filter((ms) => missablesDone[ms.id]).length;
    const mpCount = magicPots.filter((mp) => magicPotDone[mp.id]).length;

    const genjiIds = ['chk_genji_helm', 'chk_genji_armor', 'chk_genji_shield', 'chk_genji_glove'];
    const genjiCount = genjiIds.filter((id) => zack.checklist[id]).length;

    const totalItems =
      missions.length +
      trophies.length +
      shops.length +
      dmwImages.length +
      mailSenders.length +
      storyChapters.length +
      magicPots.length;
    const totalDone = mDone + trDone + shDone + dmwCount + mailCount + stCount + mpCount;
    const overallPct = totalItems ? Math.round((totalDone / totalItems) * 100) : 0;

    const chLabel = `Chapter ${zack.chapter}`;
    const chapterMissables = missables.filter((ms) => {
      if (missablesDone[ms.id]) return false;
      const mNums = (ms.chapter.match(/\d+/g) || []).map(Number);
      if (!mNums.length) return false;
      if (mNums.length === 1) return mNums[0] === zack.chapter || (zack.chapter <= 7 && ms.chapter.includes('CRITICAL'));
      return zack.chapter >= mNums[0] && zack.chapter <= mNums[mNums.length - 1];
    });

    const chapterTrophies = trophies.filter((tr) => {
      if (trophiesDone[tr.id] || !tr.missable) return false;
      const tNums = (tr.chapter.match(/\d+/g) || []).map(Number);
      if (!tNums.length) return false;
      if (tNums.length === 1) return tNums[0] === zack.chapter;
      return zack.chapter >= tNums[0] && zack.chapter <= tNums[tNums.length - 1];
    });

    const unlockableNext = missions
      .filter((m) => {
        if (zack.completedMissions[m.id] || m.chapterAvailable > zack.chapter) return false;
        const prereqs = m.prerequisiteMissionIds || [];
        return prereqs.every((pid) => zack.completedMissions[pid]);
      })
      .map((m) => ({
        mission: m,
        ready: ctx.evaluateHardModeReadiness(m, zack.level),
        delta: Math.abs((m.hardModeBenchmarks?.recommendedLevel || 1) - zack.level)
      }))
      .filter((x) => x.ready.key !== 'danger')
      .sort((a, b) => a.delta - b.delta || a.mission.stars - b.mission.stars)
      .slice(0, 6);

    const meters = [
      { label: 'Missions', done: mDone, total: missions.length, route: `#/game/${slug}/missions` },
      { label: 'Trophies', done: trDone, total: trophies.length, route: `#/game/${slug}/compendium/trophies` },
      { label: 'Story Chapters', done: stCount, total: storyChapters.length, route: `#/game/${slug}/story` },
      { label: 'Mail Senders', done: mailCount, total: mailSenders.length, route: `#/game/${slug}/compendium/mail` },
      { label: 'DMW Images', done: dmwCount, total: dmwImages.length, route: `#/game/${slug}/compendium/dmw` },
      { label: 'Network Shops', done: shDone, total: shops.length, route: `#/game/${slug}/compendium/shops` },
      { label: 'Missables Watch', done: missCount, total: missables.length, route: `#/game/${slug}/compendium/missables` },
      { label: 'Magic Pots', done: mpCount, total: magicPots.length, route: `#/game/${slug}/story/magic-pot` }
    ];

    const zackStatRow = (extra.mechanics?.zackBaseStats || []).find((r) => r.level === zack.level);

    container.innerHTML = `
      <div class="section-header">
        <div>
          <div class="brand-sub">Shinra Tactical Terminal · Complete 100% Compendium</div>
          <h1>Crisis Core Reunion — Command Center</h1>
          <p class="muted small" style="margin:4px 0 0;">Live progress across Missions, Story Chapters, Trophies, Mail, Shops, DMW, Genji Gear & Buster Sword.</p>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          <span class="pill pill-mako mono" style="font-size:0.86rem;">${overallPct}% Compendium (${totalDone}/${totalItems})</span>
          <span class="pill pill-cyan mono">Genji ${genjiCount}/4</span>
          <span class="pill pill-warn mono">Buster Sword ${bsTotal.toFixed(1)}%</span>
        </div>
      </div>

      <section class="card card-glow" style="margin-bottom:16px;">
        <div class="grid-3" style="align-items:center;margin-bottom:14px;">
          <div>
            <label class="small muted">Zack Level: <strong class="mono" style="color:var(--accent);font-size:1.05rem;">Lv. ${zack.level}</strong></label>
            <input type="range" id="dash-lv" min="1" max="99" value="${zack.level}" style="width:100%;margin-top:6px;accent-color:var(--accent);" />
            ${zackStatRow ? `<div class="small muted mono" style="margin-top:4px;">Base: HP ${zackStatRow.hp.toLocaleString()} · MP ${zackStatRow.mp} · AP ${zackStatRow.ap} · ATK/VIT/MAG/SPR ${zackStatRow.atk}</div>` : ''}
          </div>
          <div>
            <label class="small muted">Story Chapter</label>
            <select id="dash-ch" class="select" style="width:100%;margin-top:6px;">
              ${Array.from({ length: 10 }, (_, i) => `<option value="${i + 1}" ${zack.chapter === i + 1 ? 'selected' : ''}>Chapter ${i + 1}</option>`).join('')}
            </select>
          </div>
          <div>
            <div style="display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:6px;">
              <span>Overall 100% Completion</span>
              <strong class="mono">${overallPct}%</strong>
            </div>
            <div class="progress-track" style="height:10px;"><div class="progress-fill" style="width:${overallPct}%"></div></div>
            <div class="small muted" style="margin-top:4px;">All checklists auto-save to <code>localStorage</code>.</div>
          </div>
        </div>

        <div class="grid-4">
          ${meters
            .map((mt) => {
              const pct = mt.total ? Math.round((mt.done / mt.total) * 100) : 0;
              return `
              <a class="sub-panel dash-meter-card" href="${escapeHtml(mt.route)}" style="text-decoration:none;color:inherit;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                  <span style="font-weight:600;">${escapeHtml(mt.label)}</span>
                  <span class="mono small" style="color:var(--accent);">${mt.done}/${mt.total}</span>
                </div>
                <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
              </a>
            `;
            })
            .join('')}
        </div>
      </section>

      <div class="grid-2" style="margin-bottom:16px;">
        <section class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap;">
            <h3 style="margin:0;">Active Alerts for ${escapeHtml(chLabel)}</h3>
            <a class="btn btn-sm" href="#/game/${escapeHtml(slug)}/compendium/missables">All Missables →</a>
          </div>
          ${
            zack.chapter <= 7
              ? `<div class="alert alert-danger small" style="margin-bottom:10px;"><strong>Chapter 7 Point of No Return:</strong> Leaving Midgar permanently locks Midgar NPC missions, Fan Clubs, Flower Wagons & Reporter/Silver Elite mail!</div>`
              : ''
          }
          <div style="display:flex;flex-direction:column;gap:8px;">
            ${
              chapterMissables.length || chapterTrophies.length
                ? [
                    ...chapterMissables.map(
                      (ms) => `
                      <div class="sub-panel" style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">
                        <label style="display:flex;gap:8px;cursor:pointer;flex:1;">
                          <input type="checkbox" data-dash-miss="${escapeHtml(ms.id)}" />
                          <div>
                            <div style="font-weight:700;" class="small">${escapeHtml(ms.title)}</div>
                            <div class="small muted">${escapeHtml(ms.detail)}</div>
                          </div>
                        </label>
                        <span class="pill pill-warn mono">${escapeHtml(ms.chapter)}</span>
                      </div>
                    `
                    ),
                    ...chapterTrophies.map(
                      (tr) => `
                      <div class="sub-panel" style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">
                        <label style="display:flex;gap:8px;cursor:pointer;flex:1;">
                          <input type="checkbox" data-dash-tr="${escapeHtml(tr.id)}" />
                          <div>
                            <div style="font-weight:700;" class="small">${escapeHtml(tr.name)} (${escapeHtml(tr.grade)})</div>
                            <div class="small muted">${escapeHtml(tr.howToUnlock)}</div>
                          </div>
                        </label>
                        <span class="pill pill-danger mono">Missable Trophy</span>
                      </div>
                    `
                    )
                  ].join('')
                : `<div class="alert alert-mako small">No unchecked missables flagged specifically for ${escapeHtml(chLabel)}!</div>`
            }
          </div>
        </section>

        <section class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap;">
            <h3 style="margin:0;">Unlockable Next Missions (Lv.${zack.level} · Ch.${zack.chapter})</h3>
            <a class="btn btn-sm" href="#/game/${escapeHtml(slug)}/missions">All 300 Missions →</a>
          </div>
          <div style="display:flex;flex-direction:column;gap:8px;">
            ${
              unlockableNext.length
                ? unlockableNext
                    .map(
                      ({ mission: m, ready }) => `
                  <a class="hub-mission-card" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(m.id)}">
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">
                      <strong class="mono" style="color:var(--accent);">${escapeHtml(m.id)} · ${escapeHtml(m.title)}</strong>
                      <span class="pill ${ready.tone}">${m.stars}★ · ${ready.label}</span>
                    </div>
                    <div class="small muted" style="margin-top:2px;">Reward: ${escapeHtml(m.clearReward?.rawLabel || 'None')} · Boss: ${escapeHtml(m.bossGuide?.targetName || 'Target')}</div>
                  </a>
                `
                    )
                    .join('')
                : '<div class="empty-state small">No Ready/Stretch missions remain in this chapter—advance story chapter or check Challenge missions.</div>'
            }
          </div>
        </section>
      </div>

      <section class="card">
        <h3 style="margin-top:0;">Compendium Quick Tools</h3>
        <div class="grid-4">
          <a class="sub-panel dash-meter-card" href="#/game/${escapeHtml(slug)}/fusion-tracker" style="text-decoration:none;color:inherit;">
            <strong style="color:var(--accent);">True Fusion & Build Calc</strong>
            <div class="small muted" style="margin-top:4px;">Exact Materia result + stat output + 6-Materia / 4-Accessory live stat calculator.</div>
          </a>
          <a class="sub-panel dash-meter-card" href="#/game/${escapeHtml(slug)}/story/minigames" style="text-decoration:none;color:inherit;">
            <strong style="color:var(--accent-secondary);">Safe Code & Mini-Games</strong>
            <div class="small muted" style="margin-top:4px;">Interactive Shinra Manor Safe solver, Aerith affection, Squats, & Flower Wagons.</div>
          </a>
          <a class="sub-panel dash-meter-card" href="#/game/${escapeHtml(slug)}/missions/M9-6-6" style="text-decoration:none;color:inherit;">
            <strong style="color:var(--accent-danger);">Minerva Hard Mode Guide</strong>
            <div class="small muted" style="margin-top:4px;">20,000,000 HP superboss loadout, Judgment Arrow counter & 99x Phoenix Down Mug.</div>
          </a>
          <a class="sub-panel dash-meter-card" href="#/game/${escapeHtml(slug)}/guides/mechanics" style="text-decoration:none;color:inherit;">
            <strong style="color:var(--accent-warn);">Formulas & NG+ Matrix</strong>
            <div class="small muted" style="margin-top:4px;">Lv. 1–99 base stats, Skill Power, DMW math, Status Glossary & NG+ Carryover.</div>
          </a>
        </div>
      </section>
    `;

    container.querySelector('#dash-lv')?.addEventListener('change', (e) => {
      ctx.storage.set('zackLevel', Number(e.target.value) || 1);
      window.dispatchEvent(new CustomEvent('wiki:zack-updated'));
      render();
    });
    container.querySelector('#dash-ch')?.addEventListener('change', (e) => {
      ctx.storage.set('zackChapter', Number(e.target.value) || 1);
      window.dispatchEvent(new CustomEvent('wiki:zack-updated'));
      render();
    });
    container.querySelectorAll('[data-dash-miss]').forEach((el) => {
      el.addEventListener('change', () => {
        const cur = ctx.storage.get('missablesDone', {});
        cur[el.dataset.dashMiss] = el.checked;
        ctx.storage.set('missablesDone', cur);
        showToast('Missable checked off');
        render();
      });
    });
    container.querySelectorAll('[data-dash-tr]').forEach((el) => {
      el.addEventListener('change', () => {
        const cur = ctx.storage.get('trophiesDone', {});
        cur[el.dataset.dashTr] = el.checked;
        ctx.storage.set('trophiesDone', cur);
        showToast('Trophy marked unlocked');
        render();
      });
    });
  }

  render();
}
