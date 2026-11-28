import { escapeHtml, formatNum, showToast } from '../../../core/ui.js';

export function renderFusionTrackerView(container, ctx) {
  const materiaList = ctx.data.items.filter((i) => i.category === 'materia');
  const catalystList = ctx.data.items.filter((i) => i.fusion);
  const stats = ctx.data.fusionRules?.statCategories || ['HP%', 'MP%', 'AP%', 'ATK', 'VIT', 'MAG', 'SPR', 'LCK'];
  const checklistItems = ctx.config.checklistItems || [];
  const accessories = ctx.data.items.filter((i) => i.category === 'accessories');
  const blueprints = ctx.data.guides.endgameBuildBlueprints || [];
  const baseStatsTable = ctx.data.extra?.mechanics?.zackBaseStats || [];

  const preload = ctx.storage.get('fusionPreload', null);
  if (preload) {
    ctx.storage.remove('fusionPreload');
  }

  if (!ctx.viewState.fusion) {
    ctx.viewState.fusion = {
      matA: materiaList.find((m) => m.name === 'Libra')?.id || materiaList[0]?.id || '',
      masterA: false,
      statA: 'None',
      valA: 0,
      matB: materiaList.find((m) => m.name === 'HP Up')?.id || materiaList[1]?.id || '',
      masterB: false,
      statB: 'HP%',
      valB: 10,
      catId: catalystList.find((c) => c.name === 'Potion')?.id || catalystList[0]?.id || '',
      catQty: 20,
      reverseTargetId: materiaList.find((m) => m.name === 'Costly Punch')?.id || materiaList[0]?.id || ''
    };
  }
  const state = ctx.viewState.fusion;

  if (preload) {
    if (preload.matA) state.matA = preload.matA;
    if (preload.matB) state.matB = preload.matB;
    if (preload.masterA !== undefined) state.masterA = Boolean(preload.masterA);
    if (preload.masterB !== undefined) state.masterB = Boolean(preload.masterB);
  }

  function computeFusion() {
    const mA = ctx.indexes.itemById.get(state.matA);
    const mB = ctx.indexes.itemById.get(state.matB);
    const cat = ctx.indexes.itemById.get(state.catId);

    const matOutput = ctx.computeMateriaFusion
      ? ctx.computeMateriaFusion(state.matA, state.masterA, state.matB, state.masterB, state.catId)
      : { resultItem: mA, resultClass: '—', targetGrade: 1, reason: '' };

    const aHas = state.statA !== 'None' && state.valA > 0;
    const bHas = state.statB !== 'None' && state.valB > 0;
    let baseStat = aHas ? state.statA : bHas ? state.statB : 'None';
    let baseVal = aHas && bHas && state.statA === state.statB
      ? Math.max(state.valA, state.valB) + Math.floor(Math.min(state.valA, state.valB) / 2)
      : aHas
        ? state.valA
        : bHas
          ? state.valB
          : 0;

    const warnings = [];
    let added = 0;
    let finalStat = baseStat;

    if (cat?.fusion) {
      const f = cat.fusion;
      const steps = Math.floor(state.catQty / Math.max(1, f.unitsPerStep));
      const rawAdd = steps * f.perUnit;

      if (f.requiresExistingStat) {
        if (baseStat !== f.stat || baseVal <= 0) {
          warnings.push(
            `${cat.name} is a consumable catalyst and ONLY amplifies an EXISTING ${f.stat} bonus. Because neither Materia currently has ${f.stat} > 0, it adds +0!`
          );
        } else {
          added = rawAdd;
        }
      } else {
        if (baseStat !== 'None' && baseStat !== f.stat) {
          warnings.push(`Catalyst ${cat.name} converts the Materia's bonus from ${baseStat} to ${f.stat} (or combines depending on rank).`);
          finalStat = f.stat;
          added = rawAdd;
        } else {
          finalStat = f.stat;
          added = rawAdd;
        }
      }

      const cap = f.maxBonus || (finalStat.includes('%') ? 999 : 100);
      const total = Math.min(cap, (finalStat === baseStat ? baseVal : 0) + added);
      const isLibra = mA?.name === 'Libra' || mB?.name === 'Libra';
      if (isLibra && ((finalStat.includes('%') && total >= 990) || (!finalStat.includes('%') && total >= 99))) {
        warnings.push(
          `Warning: Pushing an intermediate Libra transfer Materia to ${total}${finalStat.includes('%') ? '%' : ''} locks out some item conversions! Stop at 98 (or 980%) before transferring.`
        );
      }

      return { mA, mB, cat, matOutput, finalStat, total, added, cap, warnings };
    }

    return { mA, mB, cat, matOutput, finalStat, total: baseVal, added: 0, cap: 999, warnings };
  }

  function computeBuildSummary(zack) {
    const baseRow = baseStatsTable.find((r) => r.level === zack.level) || {
      hp: 2730, mp: 214, ap: 218, atk: 30, vit: 30, mag: 30, spr: 30, lck: 24
    };
    const matBonus = { 'HP%': 0, 'MP%': 0, 'AP%': 0, ATK: 0, VIT: 0, MAG: 0, SPR: 0, LCK: 0 };
    for (const sl of zack.build.materia || []) {
      if (sl.name && sl.stat && matBonus[sl.stat] !== undefined) {
        matBonus[sl.stat] += Number(sl.bonus) || 0;
      }
    }

    const accByName = new Map(accessories.map((a) => [a.name, a]));
    const accSum = { hpPct: 0, mpPct: 0, apPct: 0, atk: 0, vit: 0, mag: 0, spr: 0, lck: 0 };
    let breakHp = false, breakMp = false, breakAp = false, breakDmg = false, zeroMp = false, zeroAp = false;
    const absorbElems = new Set();
    const immuneElems = new Set();
    const halveElems = new Set();
    const immuneStatuses = new Set();
    const autoBuffs = new Set();

    for (const accName of zack.build.accessories || []) {
      const acc = accByName.get(accName);
      const mods = acc?.accessory?.statMods;
      if (!mods) continue;
      for (const k of ['hpPct', 'mpPct', 'apPct', 'atk', 'vit', 'mag', 'spr', 'lck']) {
        accSum[k] += Number(mods[k]) || 0;
      }
      if (mods.breakHp) breakHp = true;
      if (mods.breakMp) breakMp = true;
      if (mods.breakAp) breakAp = true;
      if (mods.breakDmg) breakDmg = true;
      if (mods.zeroMp) zeroMp = true;
      if (mods.zeroAp) zeroAp = true;
      for (const el of mods.absorbElems || []) absorbElems.add(el);
      for (const el of mods.immuneElems || []) immuneElems.add(el);
      for (const el of mods.halveElems || []) halveElems.add(el);
      for (const st of mods.immuneStatuses || []) immuneStatuses.add(st);
      for (const bf of mods.autoBuffs || []) autoBuffs.add(bf);
    }

    const bs = ctx.storage.get('busterProficiency', { guard: 0, strong: 0, command: 0, barrier: 0 });
    const bsTotal = (Number(bs.guard) || 0) + (Number(bs.strong) || 0) + (Number(bs.command) || 0) + (Number(bs.barrier) || 0);
    if (bsTotal >= 23) breakDmg = true;

    const hpCap = breakHp ? 99999 : 9999;
    const mpCap = breakMp ? 9999 : 999;
    const apCap = breakAp ? 9999 : 999;

    const totalHpPct = Math.max(-90, matBonus['HP%'] + accSum.hpPct);
    const totalMpPct = Math.max(-90, matBonus['MP%'] + accSum.mpPct);
    const totalApPct = Math.max(-90, matBonus['AP%'] + accSum.apPct);

    const clamp255 = (v) => Math.max(1, Math.min(255, v));

    return {
      hp: Math.min(hpCap, Math.floor(baseRow.hp * (1 + totalHpPct / 100))),
      mp: zeroMp ? '∞ (0 Cost)' : Math.min(mpCap, Math.floor(baseRow.mp * (1 + totalMpPct / 100))),
      ap: zeroAp ? '∞ (0 Cost)' : Math.min(apCap, Math.floor(baseRow.ap * (1 + totalApPct / 100))),
      atk: clamp255(baseRow.atk + matBonus.ATK + accSum.atk),
      vit: clamp255(baseRow.vit + matBonus.VIT + accSum.vit),
      mag: clamp255(baseRow.mag + matBonus.MAG + accSum.mag),
      spr: clamp255(baseRow.spr + matBonus.SPR + accSum.spr),
      lck: clamp255(baseRow.lck + matBonus.LCK + accSum.lck),
      hpCap,
      breakHp,
      breakDmg,
      breakMp,
      breakAp,
      absorbElems: [...absorbElems],
      immuneElems: [...immuneElems],
      halveElems: [...halveElems],
      immuneStatuses: [...immuneStatuses],
      autoBuffs: [...autoBuffs]
    };
  }

  function render() {
    const zack = ctx.getZackState();
    const sim = computeFusion();
    const buildSummary = computeBuildSummary(zack);
    const slug = ctx.meta.slug;
    const doneChecks = checklistItems.filter((c) => zack.checklist[c.id]).length;
    const doneMissions = Object.values(zack.completedMissions).filter(Boolean).length;
    const bs = ctx.storage.get('busterProficiency', { guard: 0, strong: 0, command: 0, barrier: 0 });
    const bsTotal = Math.min(100, (Number(bs.guard) || 0) + (Number(bs.strong) || 0) + (Number(bs.command) || 0) + (Number(bs.barrier) || 0));
    const reverseRecipes = ctx.findRecipesForMateria ? ctx.findRecipesForMateria(state.reverseTargetId) : [];
    const customBuilds = ctx.storage.get('customBuilds', []);

    const renderRecIngredient = (name, itemId) => {
      if (itemId && ctx.indexes.itemById.has(itemId)) {
        return `<a href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(itemId)}" style="color:var(--accent-secondary);font-weight:700;">${escapeHtml(name)}</a>`;
      }
      return `<span style="color:var(--accent-secondary);font-weight:700;">${escapeHtml(name)}</span>`;
    };

    container.innerHTML = `
      <div class="section-header">
        <div>
          <div class="brand-sub">True Fusion Engine & Live Build Stat Calculator</div>
          <h1>Materia Fusion Engine & Build Calculator</h1>
        </div>
        <span class="pill pill-mako mono">Auto-saved to localStorage</span>
      </div>

      <section class="card card-glow" style="margin-bottom:18px;">
        <h2 style="margin-top:0;">True Materia Fusion Simulator (Result + Stats)</h2>
        <div class="grid-3" style="margin-bottom:14px;">
          <div class="card" style="background:var(--bg-secondary);">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span class="small muted">Materia Slot 1 ${sim.mA ? `· <a href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(sim.mA.id)}">Dossier →</a>` : ''}</span>
              <label class="small" style="display:flex;align-items:center;gap:4px;cursor:pointer;">
                <input type="checkbox" id="sim-masta" ${state.masterA ? 'checked' : ''} /> ★ Mastered
              </label>
            </div>
            <select id="sim-mata" class="select" style="width:100%;margin:6px 0;">
              ${materiaList.map((m) => `<option value="${escapeHtml(m.id)}" ${m.id === state.matA ? 'selected' : ''}>${escapeHtml(m.name)}</option>`).join('')}
            </select>
            <div style="display:flex;gap:6px;">
              <select id="sim-stata" class="select" style="flex:1;">
                <option value="None">No Stat (+0)</option>
                ${stats.map((s) => `<option value="${s}" ${s === state.statA ? 'selected' : ''}>${s}</option>`).join('')}
              </select>
              <input id="sim-vala" class="input mono" type="number" min="0" max="999" value="${state.valA}" style="width:86px;" />
            </div>
          </div>

          <div class="card" style="background:var(--bg-secondary);">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span class="small muted">Materia Slot 2 ${sim.mB ? `· <a href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(sim.mB.id)}">Dossier →</a>` : ''}</span>
              <label class="small" style="display:flex;align-items:center;gap:4px;cursor:pointer;">
                <input type="checkbox" id="sim-mastb" ${state.masterB ? 'checked' : ''} /> ★ Mastered
              </label>
            </div>
            <select id="sim-matb" class="select" style="width:100%;margin:6px 0;">
              ${materiaList.map((m) => `<option value="${escapeHtml(m.id)}" ${m.id === state.matB ? 'selected' : ''}>${escapeHtml(m.name)}</option>`).join('')}
            </select>
            <div style="display:flex;gap:6px;">
              <select id="sim-statb" class="select" style="flex:1;">
                <option value="None">No Stat (+0)</option>
                ${stats.map((s) => `<option value="${s}" ${s === state.statB ? 'selected' : ''}>${s}</option>`).join('')}
              </select>
              <input id="sim-valb" class="input mono" type="number" min="0" max="999" value="${state.valB}" style="width:86px;" />
            </div>
          </div>

          <div class="card" style="background:var(--bg-secondary);">
            <div class="small muted">Item Catalyst + Quantity</div>
            <select id="sim-cat" class="select" style="width:100%;margin:6px 0;">
              ${catalystList.map((c) => `<option value="${escapeHtml(c.id)}" ${c.id === state.catId ? 'selected' : ''}>${escapeHtml(c.name)} (${escapeHtml(c.fusion.stat)})</option>`).join('')}
            </select>
            <div style="display:flex;gap:6px;align-items:center;">
              <input id="sim-qty" class="input mono" type="number" min="1" max="99" value="${state.catQty}" style="width:86px;" />
              ${sim.cat ? `<a class="pill pill-link pill-cyan" href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(sim.cat.id)}">Where to farm ${escapeHtml(sim.cat.name)} →</a>` : ''}
            </div>
          </div>
        </div>

        <div class="card fusion-result-banner" style="background:var(--bg-primary);margin-bottom:10px;">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
            <div>
              <div class="small muted">Resulting Materia & Stat Bonus</div>
              <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:3px;">
                ${
                  sim.matOutput?.resultItem
                    ? `<a href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(sim.matOutput.resultItem.id)}" style="font-size:1.25rem;font-weight:800;color:var(--accent-secondary);">${escapeHtml(sim.matOutput.resultItem.name)}</a>`
                    : ''
                }
                <span style="font-size:1.2rem;font-weight:800;color:var(--accent);" class="mono">
                  ${sim.finalStat === 'None' ? 'No Stat Bonus (+0)' : `${escapeHtml(sim.finalStat)} +${sim.total}${sim.finalStat.includes('%') ? '%' : ''}`}
                </span>
              </div>
              <div class="small muted" style="margin-top:4px;">${escapeHtml(sim.matOutput?.reason || '')} ${escapeHtml(sim.cat?.fusion?.notes || '')}</div>
            </div>
            <div class="small mono muted">Grade ${sim.matOutput?.targetGrade || 1} · Catalyst: +${sim.added} (Cap +${sim.cap})</div>
          </div>
        </div>

        ${sim.warnings.map((w) => `<div class="alert alert-warn" style="margin-top:8px;">${escapeHtml(w)}</div>`).join('')}

        <div class="sub-panel" style="margin-top:14px;">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
            <strong class="small" style="color:var(--accent);">Reverse Recipe Lookup (How to Fuse Any Materia)</strong>
            <select id="rev-target" class="select" style="min-width:220px;">
              ${materiaList.map((m) => `<option value="${escapeHtml(m.id)}" ${m.id === state.reverseTargetId ? 'selected' : ''}>${escapeHtml(m.name)}</option>`).join('')}
            </select>
          </div>
          <div class="grid-2">
            ${
              reverseRecipes.length
                ? reverseRecipes
                    .map(
                      (rc, idx) => `
                    <div class="card" style="background:var(--bg-secondary);padding:10px;display:flex;justify-content:space-between;align-items:center;gap:8px;">
                      <div>
                        <div class="small mono">${renderRecIngredient(rc.ingredientA, rc.aId)} <span class="muted">+</span> ${renderRecIngredient(rc.ingredientB, rc.bId)}</div>
                        <div class="small muted">${escapeHtml(rc.note)}</div>
                      </div>
                      ${
                        rc.aId && rc.bId
                          ? `<button class="btn btn-sm" data-load-rec="${idx}">Try</button>`
                          : ''
                      }
                    </div>
                  `
                    )
                    .join('')
                : '<div class="small muted">Direct shop/mission reward Materia.</div>'
            }
          </div>
        </div>

        <details style="margin-top:12px;">
          <summary class="small" style="cursor:pointer;color:var(--accent-secondary);font-weight:600;">Essential Hard Mode Fusion Recipes (${(ctx.data.fusionRules?.keyRecipes || []).length})</summary>
          <div class="grid-3" style="margin-top:10px;">
            ${(ctx.data.fusionRules?.keyRecipes || [])
              .map(
                (r) => `
                <div class="card" style="background:var(--bg-secondary);">
                  <a href="#/game/${escapeHtml(slug)}/items/${encodeURIComponent(r.resultId)}" style="font-weight:700;">${escapeHtml(r.result)}</a>
                  <div class="small mono" style="margin:4px 0;">${escapeHtml(r.ingredientA)} + ${escapeHtml(r.ingredientB)}</div>
                  <div class="small muted">${escapeHtml(r.note)}</div>
                </div>
              `
              )
              .join('')}
          </div>
        </details>
      </section>

      <section class="card card-glow" style="margin-bottom:18px;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
          <div>
            <h2 style="margin:0;">Live 6-Slot Materia + 4-Slot Accessory Build Calculator</h2>
            <div class="small muted">Combines Zack Lv.${zack.level} Base Stats + Materia Bonuses + Accessory Stat Mods & Limits</div>
          </div>
          <div style="display:flex;gap:6px;flex-wrap:wrap;">
            ${blueprints.map((bp, idx) => `<button class="btn btn-sm" data-load-bp="${idx}">Load: ${escapeHtml(bp.name.split('(')[0].trim())}</button>`).join('')}
            <button class="btn btn-sm btn-primary" id="btn-save-preset">Save Preset</button>
          </div>
        </div>

        <div class="live-stat-summary" style="margin-bottom:14px;">
          <div class="grid-4 mono small" style="margin-bottom:8px;">
            <div class="sub-panel"><div class="muted">Final HP (Cap ${formatNum(buildSummary.hpCap)})</div><strong style="color:var(--accent);font-size:1.15rem;">${formatNum(buildSummary.hp)}</strong></div>
            <div class="sub-panel"><div class="muted">Final MP / AP</div><strong style="color:var(--accent-secondary);font-size:1.05rem;">${escapeHtml(String(buildSummary.mp))} / ${escapeHtml(String(buildSummary.ap))}</strong></div>
            <div class="sub-panel"><div class="muted">ATK / VIT</div><strong style="font-size:1.1rem;">${buildSummary.atk} / ${buildSummary.vit}</strong></div>
            <div class="sub-panel"><div class="muted">MAG / SPR / LCK</div><strong style="font-size:1.1rem;">${buildSummary.mag} / ${buildSummary.spr} / ${buildSummary.lck}</strong></div>
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;">
            ${buildSummary.breakHp ? '<span class="pill pill-mako">Break HP (99,999)</span>' : '<span class="pill">HP Cap 9,999</span>'}
            ${buildSummary.breakDmg ? '<span class="pill pill-mako">Break Damage (99,999)</span>' : '<span class="pill">Dmg Cap 9,999</span>'}
            ${buildSummary.absorbElems.length ? `<span class="pill pill-cyan">Absorbs: ${escapeHtml(buildSummary.absorbElems.join(', '))}</span>` : ''}
            ${buildSummary.immuneElems.length ? `<span class="pill pill-cyan">Nulls: ${escapeHtml(buildSummary.immuneElems.join(', '))}</span>` : ''}
            ${buildSummary.halveElems.length ? `<span class="pill">Halves: ${escapeHtml(buildSummary.halveElems.join(', '))}</span>` : ''}
            ${buildSummary.immuneStatuses.length ? `<span class="pill pill-mako">Status Immune: ${escapeHtml(buildSummary.immuneStatuses.join(', '))}</span>` : ''}
            ${buildSummary.autoBuffs.length ? `<span class="pill pill-warn">Auto: ${escapeHtml(buildSummary.autoBuffs.join(', '))}</span>` : ''}
          </div>
        </div>

        <div class="grid-2">
          <div>
            <div class="small muted" style="margin-bottom:8px;">Materia Loadout (6 Slots)</div>
            <div style="display:flex;flex-direction:column;gap:6px;">
              ${zack.build.materia
                .map(
                  (slot, idx) => `
                  <div style="display:flex;gap:6px;">
                    <select class="select" data-bmat="${idx}" style="flex:2;">
                      <option value="">— Slot ${idx + 1} Empty —</option>
                      ${materiaList.map((m) => `<option value="${escapeHtml(m.name)}" ${m.name === slot.name ? 'selected' : ''}>${escapeHtml(m.name)}</option>`).join('')}
                    </select>
                    <select class="select" data-bstat="${idx}" style="flex:1;">
                      ${stats.map((s) => `<option value="${s}" ${s === slot.stat ? 'selected' : ''}>${s}</option>`).join('')}
                    </select>
                    <input class="input mono" type="number" min="0" max="999" data-bval="${idx}" value="${slot.bonus || 0}" style="width:76px;" />
                  </div>
                `
                )
                .join('')}
            </div>
          </div>

          <div>
            <div class="small muted" style="margin-bottom:8px;">Accessory Loadout (4 Slots)</div>
            <div class="grid-2" style="gap:8px;margin-bottom:12px;">
              ${zack.build.accessories
                .map(
                  (acc, idx) => `
                  <select class="select" data-bacc="${idx}">
                    <option value="">— Acc ${idx + 1} Empty —</option>
                    ${accessories.map((a) => `<option value="${escapeHtml(a.name)}" ${a.name === acc ? 'selected' : ''}>${escapeHtml(a.name)}</option>`).join('')}
                  </select>
                `
                )
                .join('')}
            </div>
            ${
              customBuilds.length
                ? `
              <div class="small muted" style="margin-bottom:6px;">Saved Custom Presets</div>
              <div style="display:flex;flex-wrap:wrap;gap:6px;">
                ${customBuilds
                  .map(
                    (cb, idx) => `
                  <span class="pill pill-cyan" style="gap:6px;">
                    <button style="background:none;border:none;color:inherit;cursor:pointer;font-weight:600;" data-load-custom="${idx}">${escapeHtml(cb.name)}</button>
                    <button style="background:none;border:none;color:var(--accent-danger);cursor:pointer;" data-del-custom="${idx}" title="Delete">×</button>
                  </span>
                `
                  )
                  .join('')}
              </div>
            `
                : '<div class="small muted">Tip: Click Save Preset to store multiple builds for Minerva, Dualcast, or Farming.</div>'
            }
          </div>
        </div>
      </section>

      <section class="card" style="margin-bottom:18px;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
          <h3 style="margin:0;">Buster Sword Proficiency Tracker (Reunion Exclusive)</h3>
          <div style="display:flex;gap:6px;flex-wrap:wrap;">
            <span class="pill ${bsTotal >= 23 ? 'pill-mako' : 'pill-warn'}">23%: Damage Limit Break ${bsTotal >= 23 ? '✓' : ''}</span>
            <span class="pill ${bsTotal >= 47 ? 'pill-mako' : 'pill-warn'}">47%: Barrier Piercing ${bsTotal >= 47 ? '✓' : ''}</span>
            <span class="pill pill-cyan mono">${bsTotal.toFixed(1)}% / 100%</span>
          </div>
        </div>
        <div class="grid-4">
          <div class="card" style="background:var(--bg-secondary);padding:10px;">
            <div class="small muted">Perfect Guard (max 31.66%)</div>
            <input type="number" step="0.5" min="0" max="31.66" class="input mono" data-bs="guard" value="${bs.guard}" style="width:100%;margin-top:6px;" />
            <div class="small muted" style="margin-top:4px;">Farm: <a href="#/game/${escapeHtml(slug)}/missions/M1-2-1">M1-2-1</a></div>
          </div>
          <div class="card" style="background:var(--bg-secondary);padding:10px;">
            <div class="small muted">Strong Attack (max 31.66%)</div>
            <input type="number" step="0.5" min="0" max="31.66" class="input mono" data-bs="strong" value="${bs.strong}" style="width:100%;margin-top:6px;" />
            <div class="small muted" style="margin-top:4px;">Farm: <a href="#/game/${escapeHtml(slug)}/missions/M1-1-3">M1-1-3</a></div>
          </div>
          <div class="card" style="background:var(--bg-secondary);padding:10px;">
            <div class="small muted">Command Kills (max 31.66%)</div>
            <input type="number" step="0.5" min="0" max="31.66" class="input mono" data-bs="command" value="${bs.command}" style="width:100%;margin-top:6px;" />
            <div class="small muted" style="margin-top:4px;">Farm: <a href="#/game/${escapeHtml(slug)}/missions/M1-1-3">M1-1-3</a></div>
          </div>
          <div class="card" style="background:var(--bg-secondary);padding:10px;">
            <div class="small muted">Barrier Pierce (max 5%)</div>
            <input type="number" step="0.5" min="0" max="5" class="input mono" data-bs="barrier" value="${bs.barrier}" style="width:100%;margin-top:6px;" />
            <div class="small muted" style="margin-top:4px;">Farm: <a href="#/game/${escapeHtml(slug)}/missions/M9-6-5">M9-6-5</a></div>
          </div>
        </div>
      </section>

      <section class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <h3 style="margin:0;">Hard Mode Progression Checklist</h3>
          <span class="pill pill-mako mono">${doneChecks}/${checklistItems.length} · ${doneMissions}/300 Missions</span>
        </div>
        <div class="grid-2" style="gap:8px;">
          ${checklistItems
            .map(
              (c) => `
              <label class="enemy-source-row" style="cursor:pointer;align-items:center;justify-content:space-between;">
                <span style="display:flex;align-items:center;gap:8px;">
                  <input type="checkbox" data-chk-id="${escapeHtml(c.id)}" ${zack.checklist[c.id] ? 'checked' : ''} />
                  <span class="small">${escapeHtml(c.label)}</span>
                </span>
                ${c.missionId ? `<a class="pill pill-link pill-cyan mono" href="#/game/${escapeHtml(slug)}/missions/${encodeURIComponent(c.missionId)}">${escapeHtml(c.missionId)}</a>` : ''}
              </label>
            `
            )
            .join('')}
        </div>
      </section>
    `;

    container.querySelector('#sim-mata').addEventListener('change', (e) => { state.matA = e.target.value; render(); });
    container.querySelector('#sim-masta').addEventListener('change', (e) => { state.masterA = e.target.checked; render(); });
    container.querySelector('#sim-stata').addEventListener('change', (e) => { state.statA = e.target.value; render(); });
    container.querySelector('#sim-vala').addEventListener('change', (e) => { state.valA = Number(e.target.value) || 0; render(); });
    container.querySelector('#sim-matb').addEventListener('change', (e) => { state.matB = e.target.value; render(); });
    container.querySelector('#sim-mastb').addEventListener('change', (e) => { state.masterB = e.target.checked; render(); });
    container.querySelector('#sim-statb').addEventListener('change', (e) => { state.statB = e.target.value; render(); });
    container.querySelector('#sim-valb').addEventListener('change', (e) => { state.valB = Number(e.target.value) || 0; render(); });
    container.querySelector('#sim-cat').addEventListener('change', (e) => { state.catId = e.target.value; render(); });
    container.querySelector('#sim-qty').addEventListener('change', (e) => { state.catQty = Math.max(1, Math.min(99, Number(e.target.value) || 1)); render(); });
    container.querySelector('#rev-target').addEventListener('change', (e) => { state.reverseTargetId = e.target.value; render(); });

    container.querySelectorAll('[data-load-rec]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const rc = reverseRecipes[Number(btn.dataset.loadRec)];
        if (!rc) return;
        if (rc.aId) state.matA = rc.aId;
        if (rc.bId) state.matB = rc.bId;
        state.masterA = rc.ingredientA.includes('Mastered');
        state.masterB = rc.ingredientB.includes('Mastered');
        render();
      });
    });

    container.querySelectorAll('[data-load-bp]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const bp = blueprints[Number(btn.dataset.loadBp)];
        if (!bp) return;
        const nextBuild = {
          materia: (bp.materiaSlots || []).slice(0, 6).map((ms) => {
            const mObj = ctx.indexes.itemById.get(ms.materiaId);
            const parts = String(ms.stat || '').split(' ');
            const statKey = parts[0] || 'HP%';
            const val = Number(String(parts[1] || '0').replace(/[^0-9-]/g, '')) || 0;
            return { name: mObj?.name || '', stat: statKey, bonus: val };
          }),
          accessories: (bp.accessories || []).slice(0, 4).map((aid) => ctx.indexes.itemById.get(aid)?.name || '')
        };
        while (nextBuild.materia.length < 6) nextBuild.materia.push({ name: '', stat: 'HP%', bonus: 0 });
        while (nextBuild.accessories.length < 4) nextBuild.accessories.push('');
        ctx.storage.set('build', nextBuild);
        showToast(`Loaded ${bp.name.split('(')[0].trim()}`);
        render();
      });
    });

    container.querySelector('#btn-save-preset')?.addEventListener('click', () => {
      const label = window.prompt('Preset name (e.g., "Minerva Setup"):', `Custom Build ${customBuilds.length + 1}`);
      if (!label) return;
      const cur = ctx.storage.get('customBuilds', []);
      cur.push({ name: label.trim(), build: ctx.getZackState().build });
      ctx.storage.set('customBuilds', cur);
      showToast(`Saved preset "${label.trim()}"`);
      render();
    });
    container.querySelectorAll('[data-load-custom]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const cb = customBuilds[Number(btn.dataset.loadCustom)];
        if (!cb) return;
        ctx.storage.set('build', cb.build);
        showToast(`Loaded "${cb.name}"`);
        render();
      });
    });
    container.querySelectorAll('[data-del-custom]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const cur = ctx.storage.get('customBuilds', []);
        cur.splice(Number(btn.dataset.delCustom), 1);
        ctx.storage.set('customBuilds', cur);
        render();
      });
    });

    container.querySelectorAll('[data-bs]').forEach((el) => {
      el.addEventListener('change', () => {
        const cur = ctx.storage.get('busterProficiency', { guard: 0, strong: 0, command: 0, barrier: 0 });
        cur[el.dataset.bs] = Math.max(0, Number(el.value) || 0);
        ctx.storage.set('busterProficiency', cur);
        showToast('Buster Sword Proficiency updated');
        render();
      });
    });

    container.querySelectorAll('[data-chk-id]').forEach((el) => {
      el.addEventListener('change', () => {
        const cur = ctx.storage.get('checklist', {});
        cur[el.dataset.chkId] = el.checked;
        ctx.storage.set('checklist', cur);
        showToast('Checklist updated');
        render();
      });
    });

    const saveBuild = () => {
      const b = ctx.getZackState().build;
      container.querySelectorAll('[data-bmat]').forEach((el) => {
        b.materia[Number(el.dataset.bmat)].name = el.value;
      });
      container.querySelectorAll('[data-bstat]').forEach((el) => {
        b.materia[Number(el.dataset.bstat)].stat = el.value;
      });
      container.querySelectorAll('[data-bval]').forEach((el) => {
        b.materia[Number(el.dataset.bval)].bonus = Number(el.value) || 0;
      });
      container.querySelectorAll('[data-bacc]').forEach((el) => {
        b.accessories[Number(el.dataset.bacc)] = el.value;
      });
      ctx.storage.set('build', b);
    };
    container.querySelectorAll('[data-bmat],[data-bstat],[data-bval],[data-bacc]').forEach((el) => {
      el.addEventListener('change', () => {
        saveBuild();
        showToast('Build updated');
        render();
      });
    });
  }

  render();
}
