import { escapeHtml, formatNum, openLightbox, showToast } from '../../../core/ui.js';

const STAGE_META = {
  early: { label: 'Early · 1–2★', cls: 'stage-early' },
  'early-mid': { label: 'Early-Mid · 3–4★', cls: 'stage-early-mid' },
  'mid-late': { label: 'Mid-Late · 5–7★', cls: 'stage-mid-late' },
  endgame: { label: 'Endgame · 8–10★', cls: 'stage-endgame' }
};

function formatYieldStats(st) {
  if (!st) return '';
  const parts = [];
  if (st.gil > 0) parts.push(`${st.gil.toLocaleString()} Gil`);
  if (st.sp > 0) parts.push(`${st.sp.toLocaleString()} SP`);
  if (st.exp > 0) parts.push(`${st.exp.toLocaleString()} EXP`);
  return parts.join(' · ');
}

export function renderGuidesView(container, ctx, selectedSectionId = null) {
  const slug = ctx.meta.slug;
  const playbooks = ctx.data.guides.farmingPlaybooks || [];
  const statGuides = ctx.data.guides.statLevelingGuides || [];
  const blueprints = ctx.data.guides.endgameBuildBlueprints || [];
  const matrix = ctx.data.guides.farmingMatrix || [];
  const sections = ctx.data.guides.sections || [];
  const mechanics = ctx.data.extra?.mechanics || {};

  const zack = ctx.getZackState ? ctx.getZackState() : { level: 1, chapter: 1 };
  const recommendedStage =
    zack.chapter <= 3 && zack.level < 15
      ? 'early'
      : zack.chapter <= 5 && zack.level < 25
        ? 'early-mid'
        : zack.chapter <= 7 && zack.level < 42
          ? 'mid-late'
          : 'endgame';

  let activeMode = ctx.storage.get('guidesTab', 'playbooks');
  let activeStage = ctx.storage.get('guidesStage', 'all');
  if (selectedSectionId) {
    if (selectedSectionId === 'playbooks' || selectedSectionId === 'stats' || selectedSectionId === 'systems' || selectedSectionId === 'mechanics') {
      activeMode = selectedSectionId;
    } else if (playbooks.some((p) => p.id === selectedSectionId)) {
      activeMode = 'playbooks';
    } else if (statGuides.some((s) => s.id === selectedSectionId)) {
      activeMode = 'stats';
    } else if (sections.some((s) => s.id === selectedSectionId)) {
      activeMode = 'systems';
    }
  }

  let activePlaybookId = (playbooks.some((p) => p.id === selectedSectionId) && selectedSectionId) || playbooks[0]?.id || '';
  let activeStatId = (statGuides.some((s) => s.id === selectedSectionId) && selectedSectionId) || statGuides[0]?.id || '';
  let showBuilds = false;
  let lookupLv = zack.level || 25;
  let statusSearch = '';

  function syncGuidesRoute() {
    const rootCrumb = { label: 'Crisis Core', route: `#/game/${slug}/dashboard` };
    const guidesCrumb = { label: 'Guides & Mechanics', route: `#/game/${slug}/guides` };

    if (activeMode === 'playbooks') {
      const pb = playbooks.find((p) => p.id === activePlaybookId) || playbooks[0];
      if (pb) {
        const label = pb.shortLabel || pb.title;
        ctx.router.replaceCurrent(`#/game/${slug}/guides/${encodeURIComponent(pb.id)}`, {
          label,
          typeLabel: 'Guide',
          breadcrumbs: [rootCrumb, guidesCrumb, { label, route: null }]
        });
      }
    } else if (activeMode === 'stats') {
      const sg = !showBuilds ? (statGuides.find((s) => s.id === activeStatId) || statGuides[0]) : null;
      if (showBuilds) {
        ctx.router.replaceCurrent(`#/game/${slug}/guides/stats`, {
          label: 'Endgame Builds',
          typeLabel: 'Guide',
          breadcrumbs: [rootCrumb, guidesCrumb, { label: 'Endgame Builds', route: null }]
        });
      } else if (sg) {
        const label = `${sg.stat} Guide`;
        ctx.router.replaceCurrent(`#/game/${slug}/guides/${encodeURIComponent(sg.id)}`, {
          label,
          typeLabel: 'Guide',
          breadcrumbs: [rootCrumb, guidesCrumb, { label, route: null }]
        });
      }
    } else if (activeMode === 'systems') {
      ctx.router.replaceCurrent(`#/game/${slug}/guides/systems`, {
        label: 'Bosses & Systems',
        typeLabel: 'Guide',
        breadcrumbs: [rootCrumb, guidesCrumb, { label: 'Bosses & Systems', route: null }]
      });
    } else {
      ctx.router.replaceCurrent(`#/game/${slug}/guides/mechanics`, {
        label: 'Mechanics & Formulas',
        typeLabel: 'Guide',
        breadcrumbs: [rootCrumb, guidesCrumb, { label: 'Mechanics & Formulas', route: null }]
      });
    }
  }

  const itemPill = (iid, prefix = '') => {
    if (!iid) return '';
    const it = ctx.indexes.itemById.get(iid);
    if (!it) return '';
    return `<a class="pill pill-link pill-cyan" href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(it.id)}">${prefix ? `${escapeHtml(prefix)}: ` : ''}${escapeHtml(it.name)}</a>`;
  };

  const missionPill = (mid, withStars = false) => {
    if (!mid) return '';
    const m = ctx.indexes.missionById.get(mid);
    const starTxt = withStars && m?.stars ? ` (${m.stars}★)` : '';
    return `<a class="pill pill-link pill-mako mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(mid)}">${escapeHtml(mid)}${escapeHtml(starTxt)}${m ? ` · ${escapeHtml(m.title)}` : ''}</a>`;
  };

  const enemyPill = (eid) => {
    if (!eid) return '';
    const en = ctx.indexes.enemyById.get(eid);
    if (!en) return '';
    return `<a class="pill pill-link pill-danger" href="#/game/${escapeHtml(slug)}/enemies/${encodeURIComponent(en.id)}">${escapeHtml(en.name)}</a>`;
  };

  const stageBadgeHtml = (tier) => {
    const meta = STAGE_META[tier];
    if (!meta) return '';
    return `<span class="stage-badge ${meta.cls}">${escapeHtml(meta.label)}</span>`;
  };

  function renderCatalystLiveSources(itemId, label) {
    if (!itemId) return '';
    const it = ctx.indexes.itemById.get(itemId);
    if (!it) return '';
    const loot = ctx.getItemLootSources(itemId);
    const allEnemies = new Map();
    for (const slot of ['commonDrop', 'rareDrop', 'commonSteal', 'rareSteal']) {
      for (const en of loot[slot] || []) {
        if (!allEnemies.has(en.id)) {
          allEnemies.set(en.id, { enemy: en, slots: [] });
        }
        const tag = { commonDrop: 'Drop', rareDrop: 'Rare Drop', commonSteal: 'Steal', rareSteal: 'Rare Steal' }[slot];
        allEnemies.get(en.id).slots.push(tag);
      }
    }
    const topSources = Array.from(allEnemies.values()).slice(0, 5);

    return `
      <div class="sub-panel">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:8px;flex-wrap:wrap;">
          <div>
            <span class="small muted">${escapeHtml(label)}</span><br/>
            <a href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(it.id)}" style="font-weight:700;">${escapeHtml(it.name)}</a>
          </div>
          ${it.fusion ? `<span class="pill pill-mako mono">${escapeHtml(it.fusion.stat)} +${it.fusion.perUnit}${it.fusion.stat.includes('%') ? '%' : ''} / ${it.fusion.unitsPerStep}x (Max +${it.fusion.maxBonus})</span>` : ''}
        </div>
        ${
          topSources.length
            ? topSources
                .map(({ enemy, slots }) => {
                  const firstM = (enemy.spawns || [])[0]?.missionId;
                  const port = ctx.resolvePortrait(enemy);
                  return `
                  <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:6px 0;border-top:1px solid var(--border-subtle);flex-wrap:wrap;">
                    <span class="small" style="display:flex;align-items:center;gap:8px;min-width:0;">
                      <img class="mini-portrait" referrerpolicy="no-referrer" src="${escapeHtml(port.primary)}" alt="" style="width:34px;height:34px;" onerror="if(this.dataset.step!=='1'){this.dataset.step='1';this.src='${escapeHtml(port.secondary)}';}else{this.onerror=null;this.src='${escapeHtml(port.fallback)}';}" />
                      <span>
                        <a href="#/game/${escapeHtml(slug)}/enemies/${encodeURIComponent(enemy.id)}" style="font-weight:600;">${escapeHtml(enemy.name)}</a>
                        <div class="muted" style="font-size:0.74rem;">${escapeHtml(slots.join(', '))}</div>
                      </span>
                    </span>
                    ${firstM ? `<a class="pill pill-link pill-cyan mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(firstM)}">${escapeHtml(firstM)}</a>` : ''}
                  </div>
                `;
                })
                .join('')
            : '<div class="small muted">Check item dossier for chests & clear rewards.</div>'
        }
      </div>
    `;
  }

  function render() {
    container.innerHTML = `
      <div class="section-header">
        <div>
          <div class="brand-sub">Hard Mode Field Manual & Encyclopedia</div>
          <h1>Farming, Stat-Leveling & Mechanics</h1>
          <p class="muted small" style="margin:4px 0 0;">Playbooks for EXP/SP/Gil/DMW, all 8 stat-leveling Materia guides, Hard Mode boss tactics, Lv.1–99 stats, Status Glossary, and NG+ matrix.</p>
        </div>
      </div>

      <div class="seg-tabs" id="guides-seg">
        <button class="seg-tab ${activeMode === 'playbooks' ? 'active' : ''}" data-gmode="playbooks">Farming Playbooks</button>
        <button class="seg-tab ${activeMode === 'stats' ? 'active' : ''}" data-gmode="stats">Stat-Leveling Materia (8)</button>
        <button class="seg-tab ${activeMode === 'systems' ? 'active' : ''}" data-gmode="systems">Bosses & Systems</button>
        <button class="seg-tab ${activeMode === 'mechanics' ? 'active' : ''}" data-gmode="mechanics">Mechanics & Formulas</button>
      </div>

      <div id="guides-body"></div>
    `;

    const body = container.querySelector('#guides-body');

    if (activeMode === 'playbooks') {
      const pb = playbooks.find((p) => p.id === activePlaybookId) || playbooks[0];
      const stepsAll = pb?.steps || [];
      const visibleSteps = activeStage === 'all' ? stepsAll : stepsAll.filter((st) => st.tier === activeStage);
      const filteredMatrix = activeStage === 'all' ? matrix : matrix.filter((r) => r.stage === activeStage);
      const showEndgameHeader = activeStage === 'all' || activeStage === 'endgame';

      body.innerHTML = `
        <div class="chip-row" id="pb-chips">
          ${playbooks.map((p) => `<button class="chip ${p.id === pb?.id ? 'active' : ''}" data-pb="${escapeHtml(p.id)}">${escapeHtml(p.shortLabel)}</button>`).join('')}
        </div>

        <div class="chip-row" id="stage-chips" style="margin-bottom:14px;">
          <button class="chip ${activeStage === 'all' ? 'active' : ''}" data-stage="all">All Stages</button>
          <button class="chip ${activeStage === 'early' ? 'active' : ''}" data-stage="early">Early (1–2★)</button>
          <button class="chip ${activeStage === 'early-mid' ? 'active' : ''}" data-stage="early-mid">Early-Mid (3–4★)</button>
          <button class="chip ${activeStage === 'mid-late' ? 'active' : ''}" data-stage="mid-late">Mid-Late (5–7★)</button>
          <button class="chip ${activeStage === 'endgame' ? 'active' : ''}" data-stage="endgame">Endgame (8–10★)</button>
          <button class="chip ${activeStage === recommendedStage ? 'active' : ''}" data-stage="match-zack" title="Jump to stage matching Zack's Ch. ${zack.chapter} Lv. ${zack.level}">Match Zack (Ch. ${zack.chapter} · Lv. ${zack.level})</button>
        </div>

        ${
          pb
            ? `
          <article class="card card-glow" style="margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap;margin-bottom:8px;">
              <div>
                <h2 style="margin:0 0 4px;">${escapeHtml(pb.title)}</h2>
                <p class="prose muted" style="margin:0;">${escapeHtml(pb.summary)}</p>
              </div>
              <span class="pill pill-mako mono">${escapeHtml(pb.badge)}</span>
            </div>

            ${
              showEndgameHeader
                ? `
              <div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:12px 0 14px;">
                <span class="small muted">Endgame Peak Setup:</span>
                ${missionPill(pb.bestMissionId, true)}
                ${enemyPill(pb.enemyId)}
                ${(pb.recommendedGear || []).map((g) => itemPill(g)).join('')}
              </div>
            `
                : `
              <div class="small muted" style="margin:8px 0 12px;">
                Showing ${stageBadgeHtml(activeStage)} routes with accessible gear for this tier.
              </div>
            `
            }

            <div class="step-timeline" style="margin-bottom:14px;">
              ${visibleSteps
                .map((st, idx) => {
                  const tier = st.tier || 'early';
                  const en = st.enemyId ? ctx.indexes.enemyById.get(st.enemyId) : null;
                  const port = en ? ctx.resolvePortrait(en) : null;
                  const yieldStats = en ? formatYieldStats(en.stats) : '';
                  return `
                  <div class="step-item tier-${escapeHtml(tier)}">
                    <div class="step-item-head">
                      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                        ${stageBadgeHtml(tier)}
                        <strong style="color:var(--accent);">${activeStage === 'all' ? `${idx + 1}. ` : ''}${escapeHtml(st.stage)}</strong>
                      </div>
                      ${missionPill(st.missionId, true)}
                    </div>
                    ${
                      en || st.yield
                        ? `
                      <div class="step-enemy-bar">
                        <div style="display:flex;align-items:center;gap:9px;min-width:0;flex-wrap:wrap;">
                          ${
                            en && port
                              ? `
                            <img class="mini-portrait js-zoom-portrait" referrerpolicy="no-referrer" src="${escapeHtml(port.primary)}" data-secondary="${escapeHtml(port.secondary)}" data-fallback="${escapeHtml(port.fallback)}" data-name="${escapeHtml(en.name)}" data-sub="${escapeHtml(en.family)}${en.stats?.level ? ` · Lv. ${en.stats.level}` : ''}" alt="${escapeHtml(en.name)}" style="width:40px;height:40px;cursor:zoom-in;" onerror="if(this.dataset.step!=='1'){this.dataset.step='1';this.src=this.dataset.secondary;}else{this.onerror=null;this.src=this.dataset.fallback;}" />
                            ${enemyPill(en.id)}
                            ${yieldStats ? `<span class="small muted mono">${escapeHtml(yieldStats)}</span>` : ''}
                          `
                              : ''
                          }
                        </div>
                        ${st.yield ? `<span class="pill pill-mako mono">${escapeHtml(st.yield)}</span>` : ''}
                      </div>
                    `
                        : ''
                    }
                    <div class="prose">${escapeHtml(st.detail)}</div>
                    ${
                      (st.gearIds || []).length
                        ? `
                      <div class="step-gear-row">
                        <span class="small muted">Gear for this stage:</span>
                        ${st.gearIds.map((g) => itemPill(g)).join('')}
                      </div>
                    `
                        : ''
                    }
                  </div>
                `;
                })
                .join('')}
            </div>

            <div class="alert alert-mako"><strong>Pro Tip:</strong> ${escapeHtml(pb.proTip)}</div>
          </article>
        `
            : ''
        }

        <details class="guide-accordion">
          <summary>
            <strong>Quick Farming Reference (${filteredMatrix.length}${activeStage === 'all' ? ' Total Resources' : ` matching / ${matrix.length} total`})</strong>
            <span class="pill pill-cyan">Expand</span>
          </summary>
          <div class="guide-accordion-body">
            <div class="grid-2" style="padding-top:12px;">
              ${filteredMatrix
                .map(
                  (r) => `
                  <div class="sub-panel" style="display:flex;flex-direction:column;gap:6px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;flex-wrap:wrap;">
                      <strong style="color:var(--accent);">${escapeHtml(r.resource)}</strong>
                      <div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap;">
                        ${stageBadgeHtml(r.stage)}
                        <span class="pill pill-cyan">${escapeHtml(r.category)}</span>
                      </div>
                    </div>
                    <div class="small"><strong>Setup:</strong> ${escapeHtml(r.setup)}</div>
                    <div class="small muted">${escapeHtml(r.method)}</div>
                    <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:auto;">
                      ${missionPill(r.bestMissionId, true)}
                      ${enemyPill(r.enemyId)}
                      ${itemPill(r.itemId)}
                      <span class="pill mono">${escapeHtml(r.yield)}</span>
                    </div>
                  </div>
                `
                )
                .join('')}
            </div>
          </div>
        </details>
      `;

      body.querySelectorAll('#pb-chips .chip').forEach((btn) => {
        btn.addEventListener('click', () => {
          activePlaybookId = btn.dataset.pb;
          syncGuidesRoute();
          render();
        });
      });

      body.querySelectorAll('#stage-chips .chip').forEach((btn) => {
        btn.addEventListener('click', () => {
          const st = btn.dataset.stage;
          activeStage = st === 'match-zack' ? recommendedStage : st;
          ctx.storage.set('guidesStage', activeStage);
          render();
        });
      });

      body.querySelectorAll('.js-zoom-portrait').forEach((img) => {
        img.addEventListener('click', () => {
          openLightbox({
            src: img.src,
            fallbackSrc: img.dataset.fallback || '',
            title: img.dataset.name || 'Enemy',
            subtitle: img.dataset.sub || ''
          });
        });
      });
    } else if (activeMode === 'stats') {
      const sg = !showBuilds ? (statGuides.find((s) => s.id === activeStatId) || statGuides[0]) : null;
      body.innerHTML = `
        <div class="chip-row" id="stat-chips">
          ${statGuides.map((s) => `<button class="chip ${!showBuilds && s.id === sg?.id ? 'active' : ''}" data-sg="${escapeHtml(s.id)}">${escapeHtml(s.stat)} (${escapeHtml(s.cap)})</button>`).join('')}
          <button class="chip ${showBuilds ? 'active' : ''}" data-sg="builds">6-Slot Endgame Builds (${blueprints.length})</button>
        </div>

        ${
          showBuilds
            ? `
          <div style="display:flex;flex-direction:column;gap:14px;">
            ${blueprints
              .map(
                (bp) => `
                <article class="card card-glow">
                  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
                    <h2 style="margin:0;font-size:1.15rem;">${escapeHtml(bp.name)}</h2>
                    <span class="pill pill-mako">${escapeHtml(bp.role)}</span>
                  </div>
                  <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;">
                    <span class="small muted" style="align-self:center;">Accessories:</span>
                    ${(bp.accessories || []).map((a) => itemPill(a)).join('')}
                  </div>
                  <div class="small muted" style="margin-bottom:12px;">${escapeHtml(bp.altAccessories)}</div>
                  <div class="grid-3">
                    ${(bp.materiaSlots || [])
                      .map(
                        (ms, idx) => `
                        <div class="sub-panel">
                          <div style="display:flex;justify-content:space-between;gap:6px;margin-bottom:4px;">
                            <span class="small muted mono">Slot ${idx + 1}</span>
                            <span class="pill pill-mako mono">${escapeHtml(ms.stat)}</span>
                          </div>
                          <div>${itemPill(ms.materiaId)}</div>
                          <div class="small muted" style="margin-top:5px;">${escapeHtml(ms.role)}</div>
                        </div>
                      `
                      )
                      .join('')}
                  </div>
                </article>
              `
              )
              .join('')}
          </div>
        `
            : sg
              ? `
          <article class="card card-glow" style="margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
              <div>
                <div class="brand-sub">${escapeHtml(sg.priority)}</div>
                <h2 style="margin:2px 0 4px;">${escapeHtml(sg.title)}</h2>
                <p class="prose muted" style="margin:0;">${escapeHtml(sg.whyMatters)}</p>
              </div>
              <span class="pill pill-mako mono" style="font-size:0.86rem;">Cap: ${escapeHtml(sg.cap)}</span>
            </div>

            <div class="alert alert-warn" style="margin-bottom:14px;">
              <strong>Consumable & Catalyst Rule:</strong> ${escapeHtml(sg.consumableRule)}
            </div>

            <div style="margin-bottom:14px;">
              <div class="small muted" style="margin-bottom:6px;">Best Target Materia to Infuse ${escapeHtml(sg.stat)} Into</div>
              <div style="display:flex;flex-wrap:wrap;gap:6px;">
                ${(sg.targetMateriaIds || []).map((id) => itemPill(id)).join('')}
              </div>
            </div>

            <h3 style="margin:0 0 8px;font-size:1rem;">Step-by-Step Leveling Pipeline</h3>
            <div class="step-timeline" style="margin-bottom:16px;">
              ${(sg.phases || [])
                .map(
                  (ph, idx) => `
                  <div class="step-item">
                    <div class="step-item-head">
                      <strong style="color:var(--accent);">Phase ${idx + 1}: ${escapeHtml(ph.phase)}</strong>
                      ${missionPill(ph.missionId)}
                    </div>
                    <div class="prose">${escapeHtml(ph.detail)}</div>
                  </div>
                `
                )
                .join('')}
            </div>

            <h3 style="margin:0 0 8px;font-size:1rem;">Live Enemy Drop & Steal Sources (From Bestiary)</h3>
            <div class="grid-3" style="margin-bottom:14px;">
              ${renderCatalystLiveSources(sg.makoStoneId, 'Tier 1: Mako Stone (5 = +1)')}
              ${renderCatalystLiveSources(sg.statStoneId, 'Tier 2: Stat Stone (3 = +1)')}
              ${renderCatalystLiveSources(sg.maxItemId, 'Tier 3: Max Catalyst (1 = +1)')}
            </div>

            <div class="alert alert-mako"><strong>Pro Tip:</strong> ${escapeHtml(sg.proTip)}</div>
          </article>
        `
              : ''
        }
      `;

      body.querySelectorAll('#stat-chips .chip').forEach((btn) => {
        btn.addEventListener('click', () => {
          const id = btn.dataset.sg;
          if (id === 'builds') {
            showBuilds = true;
          } else {
            showBuilds = false;
            activeStatId = id;
          }
          syncGuidesRoute();
          render();
        });
      });
    } else if (activeMode === 'systems') {
      body.innerHTML = `
        <div style="display:flex;flex-direction:column;gap:10px;">
          ${sections
            .map((sec, idx) => {
              const isOpen = selectedSectionId && sections.some((s) => s.id === selectedSectionId) ? selectedSectionId === sec.id : idx === 0;
              const mRefs = (sec.refs?.missions || []).map((mid) => missionPill(mid)).join(' ');
              const iRefs = (sec.refs?.items || []).map((iid) => itemPill(iid)).join(' ');
              return `
                <details class="guide-accordion" id="${escapeHtml(sec.id)}" ${isOpen ? 'open' : ''}>
                  <summary>
                    <div style="min-width:0;">
                      <strong style="font-size:1.03rem;">${escapeHtml(sec.title)}</strong>
                      <div class="small muted">${escapeHtml(sec.summary)}</div>
                    </div>
                    <span class="pill pill-mako">${escapeHtml(sec.badge || 'Guide')}</span>
                  </summary>
                  <div class="guide-accordion-body">
                    <div class="grid-2" style="padding:12px 0;">
                      ${(sec.blocks || [])
                        .map(
                          (b) => `
                          <div class="sub-panel">
                            <h4 style="margin:0 0 6px;color:var(--accent);">${escapeHtml(b.heading)}</h4>
                            <p class="prose" style="margin:0;">${escapeHtml(b.body)}</p>
                          </div>
                        `
                        )
                        .join('')}
                    </div>
                    <div style="display:flex;flex-wrap:wrap;gap:6px;">
                      ${mRefs} ${iRefs}
                    </div>
                  </div>
                </details>
              `;
            })
            .join('')}
        </div>
      `;

      if (selectedSectionId && sections.some((s) => s.id === selectedSectionId)) {
        setTimeout(() => {
          document.getElementById(selectedSectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 40);
      }
    } else {
      const zackStats = mechanics.zackBaseStats || [];
      const row = zackStats.find((r) => r.level === lookupLv) || zackStats[0];
      const milestones = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99].map((lv) => zackStats.find((r) => r.level === lv)).filter(Boolean);
      const dmwMech = mechanics.dmwMechanics || {};
      const rCombat = mechanics.reunionCombat || {};
      const statuses = (mechanics.statusEffects || []).filter((s) => {
        const q = statusSearch.trim().toLowerCase();
        if (!q) return true;
        return `${s.name} ${s.kind} ${s.effect} ${s.counter}`.toLowerCase().includes(q);
      });
      const vsPsp = mechanics.reunionVsPsp || [];
      const ngPlus = mechanics.ngPlusCarryover || [];
      const ngDone = ctx.storage.get('ngPlusDone', {});

      body.innerHTML = `
        <section class="card card-glow" style="margin-bottom:16px;">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
            <h2 style="margin:0;">Zack Base Stat & EXP Table (Lv. 1–99)</h2>
            <span class="pill pill-mako mono">Lookup: Lv. ${lookupLv}</span>
          </div>
          <div style="margin-bottom:12px;">
            <input type="range" id="mech-lv" min="1" max="99" value="${lookupLv}" style="width:100%;accent-color:var(--accent);" />
          </div>
          ${
            row
              ? `<div class="grid-4 mono small" style="margin-bottom:14px;">
                  <div class="sub-panel"><div class="muted">Base HP</div><strong style="color:var(--accent);font-size:1.1rem;">${formatNum(row.hp)}</strong></div>
                  <div class="sub-panel"><div class="muted">Base MP / AP</div><strong style="color:var(--accent-secondary);font-size:1.1rem;">${row.mp} / ${row.ap}</strong></div>
                  <div class="sub-panel"><div class="muted">ATK / VIT / MAG / SPR</div><strong>${row.atk} / ${row.vit} / ${row.mag} / ${row.spr}</strong></div>
                  <div class="sub-panel"><div class="muted">LCK · Cumulative EXP</div><strong>${row.lck} · ${formatNum(row.totalExp)}</strong></div>
                </div>`
              : ''
          }
          <div class="table-wrap">
            <table class="wiki-table small mono">
              <thead><tr><th>Lv</th><th>HP</th><th>MP</th><th>AP</th><th>ATK</th><th>VIT</th><th>MAG</th><th>SPR</th><th>LCK</th><th>Total EXP</th></tr></thead>
              <tbody>
                ${milestones.map((m) => `<tr><td>${m.level}</td><td>${formatNum(m.hp)}</td><td>${m.mp}</td><td>${m.ap}</td><td>${m.atk}</td><td>${m.vit}</td><td>${m.mag}</td><td>${m.spr}</td><td>${m.lck}</td><td>${formatNum(m.totalExp)}</td></tr>`).join('')}
              </tbody>
            </table>
          </div>
        </section>

        <div class="grid-2" style="margin-bottom:16px;">
          <section class="card">
            <h3 style="margin-top:0;">DMW Deep Mechanics</h3>
            <p class="small muted">${escapeHtml(dmwMech.hiddenExpRule || '')}</p>
            <div style="display:flex;flex-direction:column;gap:6px;margin-bottom:10px;">
              ${(dmwMech.emotionalPhases || []).map((ep) => `<div class="sub-panel small"><strong>${escapeHtml(ep.state)}</strong> <span class="pill pill-cyan mono">${escapeHtml(ep.multiplier)}</span><div class="muted" style="margin-top:2px;">${escapeHtml(ep.notes)}</div></div>`).join('')}
            </div>
            <div class="alert alert-mako small" style="margin-bottom:8px;"><strong>Limit Verge (Reunion):</strong> ${escapeHtml(dmwMech.limitVerge || '')}</div>
            <div class="alert alert-warn small"><strong>Curse Warning:</strong> ${escapeHtml(dmwMech.curseWarning || '')}</div>
          </section>

          <section class="card">
            <h3 style="margin-top:0;">Skill Power Gauge & Buster Sword Stance</h3>
            <div class="small muted" style="margin-bottom:6px;">Boss Skill Power Bar Reduction</div>
            <div style="display:flex;flex-direction:column;gap:6px;margin-bottom:12px;">
              ${(rCombat.skillPowerGauge || []).map((sp) => `<div class="sub-panel small"><div style="display:flex;justify-content:space-between;"><strong>${escapeHtml(sp.threshold)}</strong><span class="pill pill-mako">${escapeHtml(sp.reduction)}</span></div><div class="muted">${escapeHtml(sp.note)}</div></div>`).join('')}
            </div>
            <div class="small muted" style="margin-bottom:6px;">Buster Sword Proficiency Milestones</div>
            <div style="display:flex;flex-direction:column;gap:6px;">
              ${(rCombat.battleStance || []).map((bs) => `<div class="sub-panel small"><div style="display:flex;justify-content:space-between;"><strong>${escapeHtml(bs.perk)}</strong><span class="pill pill-cyan mono">${escapeHtml(bs.unlock)}</span></div><div class="muted">${escapeHtml(bs.effect)}</div></div>`).join('')}
            </div>
          </section>
        </div>

        <section class="card" style="margin-bottom:16px;">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
            <h3 style="margin:0;">Status Effects & Elements Glossary (${statuses.length})</h3>
            <input type="search" id="status-search" class="input" style="min-width:220px;" value="${escapeHtml(statusSearch)}" placeholder="Filter statuses (Stop, Curse, Death, Barrier)..." />
          </div>
          <div class="grid-2">
            ${statuses
              .map(
                (st) => `
              <div class="sub-panel">
                <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:4px;">
                  <strong>${escapeHtml(st.name)}</strong>
                  <span class="pill ${st.kind === 'Ailment' ? 'pill-danger' : st.kind === 'Buff' ? 'pill-mako' : 'pill-warn'}">${escapeHtml(st.kind)}</span>
                </div>
                <div class="small" style="margin-bottom:4px;">${escapeHtml(st.effect)}</div>
                <div class="small muted" style="margin-bottom:6px;"><strong>Counter:</strong> ${escapeHtml(st.counter)}</div>
                <div style="display:flex;flex-wrap:wrap;gap:4px;">${(st.itemIds || []).map((iid) => itemPill(iid)).join('')}</div>
              </div>
            `
              )
              .join('')}
          </div>
        </section>

        <div class="grid-2">
          <section class="card">
            <h3 style="margin-top:0;">Reunion vs. Original PSP Changes</h3>
            <div style="display:flex;flex-direction:column;gap:8px;">
              ${vsPsp
                .map(
                  (rowItem) => `
                <div class="sub-panel small">
                  <strong style="color:var(--accent);">${escapeHtml(rowItem.feature)}</strong>
                  <div class="muted" style="margin-top:2px;"><strong>PSP:</strong> ${escapeHtml(rowItem.psp)}</div>
                  <div style="margin-top:2px;"><strong>Reunion:</strong> ${escapeHtml(rowItem.reunion)}</div>
                </div>
              `
                )
                .join('')}
            </div>
          </section>

          <section class="card">
            <h3 style="margin-top:0;">New Game+ Carryover Matrix</h3>
            <div style="display:flex;flex-direction:column;gap:8px;">
              ${ngPlus
                .map(
                  (ng, idx) => `
                <label class="sub-panel small" style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;cursor:pointer;">
                  <span style="display:flex;gap:8px;align-items:flex-start;flex:1;">
                    <input type="checkbox" data-ng-chk="ng_${idx}" ${ngDone[`ng_${idx}`] ? 'checked' : ''} style="margin-top:3px;" />
                    <span>
                      <strong>${escapeHtml(ng.item)}</strong>
                      <div class="muted" style="margin-top:2px;">${escapeHtml(ng.note)}</div>
                    </span>
                  </span>
                  <span class="pill ${ng.carriesOver ? 'pill-mako' : 'pill-danger'}">${ng.carriesOver ? 'Carries Over' : 'Resets'}</span>
                </label>
              `
                )
                .join('')}
            </div>
          </section>
        </div>
      `;

      body.querySelector('#mech-lv')?.addEventListener('input', (e) => {
        lookupLv = Number(e.target.value) || 1;
        render();
      });
      body.querySelector('#status-search')?.addEventListener('input', (e) => {
        statusSearch = e.target.value;
        render();
        const inp = container.querySelector('#status-search');
        if (inp) {
          inp.focus();
          inp.setSelectionRange(inp.value.length, inp.value.length);
        }
      });
      body.querySelectorAll('[data-ng-chk]').forEach((el) => {
        el.addEventListener('change', () => {
          const cur = ctx.storage.get('ngPlusDone', {});
          cur[el.dataset.ngChk] = el.checked;
          ctx.storage.set('ngPlusDone', cur);
          showToast('NG+ checklist updated');
        });
      });
    }

    container.querySelectorAll('#guides-seg .seg-tab').forEach((btn) => {
      btn.addEventListener('click', () => {
        activeMode = btn.dataset.gmode;
        ctx.storage.set('guidesTab', activeMode);
        syncGuidesRoute();
        render();
      });
    });
  }

  render();
}
