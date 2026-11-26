import { escapeHtml, showToast } from '../../../core/ui.js';

export function renderFusionTrackerView(container, ctx) {
  const materiaList = ctx.data.items.filter((i) => i.category === 'materia');
  const catalystList = ctx.data.items.filter((i) => i.fusion);
  const stats = ctx.data.fusionRules?.statCategories || ['HP%', 'MP%', 'AP%', 'ATK', 'VIT', 'MAG', 'SPR', 'LCK'];
  const checklistItems = ctx.config.checklistItems || [];
  const accessories = ctx.data.items.filter((i) => i.category === 'accessories');

  const state = {
    matA: materiaList.find((m) => m.name === 'Libra')?.id || materiaList[0]?.id || '',
    statA: 'None',
    valA: 0,
    matB: materiaList.find((m) => m.name === 'HP Up')?.id || materiaList[1]?.id || '',
    statB: 'HP%',
    valB: 10,
    catId: catalystList.find((c) => c.name === 'Potion')?.id || catalystList[0]?.id || '',
    catQty: 20
  };

  function computeFusion() {
    const mA = ctx.indexes.itemById.get(state.matA);
    const mB = ctx.indexes.itemById.get(state.matB);
    const cat = ctx.indexes.itemById.get(state.catId);

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

      return { mA, mB, cat, finalStat, total, added, cap, warnings };
    }

    return { mA, mB, cat, finalStat, total: baseVal, added: 0, cap: 999, warnings };
  }

  function render() {
    const zack = ctx.getZackState();
    const sim = computeFusion();
    const slug = ctx.meta.slug;
    const doneChecks = checklistItems.filter((c) => zack.checklist[c.id]).length;
    const doneMissions = Object.values(zack.completedMissions).filter(Boolean).length;

    container.innerHTML = `
      <div class="section-header">
        <div>
          <div class="brand-sub">Interactive Tools & Persistent Save</div>
          <h1>⚗️ Materia Fusion Calculator & Personal Tracker</h1>
        </div>
        <span class="pill pill-mako mono">Auto-saved to localStorage</span>
      </div>

      <section class="card card-glow" style="margin-bottom:18px;">
        <h2 style="margin-top:0;">Materia Fusion Stat Simulator</h2>
        <div class="grid-3" style="margin-bottom:14px;">
          <div class="card" style="background:var(--bg-secondary);">
            <div class="small muted">Materia Slot 1</div>
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
            <div class="small muted">Materia Slot 2</div>
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

        <div class="card" style="background:var(--bg-primary);border-color:var(--border-strong);margin-bottom:10px;">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
            <div>
              <div class="small muted">Projected Stat Output</div>
              <div style="font-size:1.3rem;font-weight:800;color:var(--accent);" class="mono">
                ${sim.finalStat === 'None' ? 'No Stat Bonus (+0)' : `${escapeHtml(sim.finalStat)} +${sim.total}${sim.finalStat.includes('%') ? '%' : ''}`}
              </div>
              <div class="small muted">${escapeHtml(sim.cat?.fusion?.notes || '')}</div>
            </div>
            <div class="small mono muted">Catalyst Contribution: +${sim.added} (Cap +${sim.cap})</div>
          </div>
        </div>

        ${sim.warnings.map((w) => `<div class="alert alert-warn" style="margin-top:8px;">⚠️ ${escapeHtml(w)}</div>`).join('')}

        <details style="margin-top:12px;">
          <summary class="small" style="cursor:pointer;color:var(--accent-secondary);font-weight:600;">View Iconic Hard Mode Fusion Recipes</summary>
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

      <div class="grid-2">
        <section class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
            <h3 style="margin:0;">✅ Hard Mode Progression Checklist</h3>
            <span class="pill pill-mako mono">${doneChecks}/${checklistItems.length} · ${doneMissions}/300 Missions</span>
          </div>
          <div style="display:flex;flex-direction:column;gap:8px;">
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

        <section class="card">
          <h3 style="margin-top:0;">🛡️ 6-Slot Materia + 4-Slot Accessory Scratchpad</h3>
          <div class="small muted" style="margin-bottom:8px;">Materia Loadout (6 Slots)</div>
          <div style="display:flex;flex-direction:column;gap:6px;margin-bottom:14px;">
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

          <div class="small muted" style="margin-bottom:8px;">Accessory Loadout (4 Slots)</div>
          <div class="grid-2" style="gap:8px;">
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
        </section>
      </div>
    `;

    container.querySelector('#sim-mata').addEventListener('change', (e) => { state.matA = e.target.value; render(); });
    container.querySelector('#sim-stata').addEventListener('change', (e) => { state.statA = e.target.value; render(); });
    container.querySelector('#sim-vala').addEventListener('change', (e) => { state.valA = Number(e.target.value) || 0; render(); });
    container.querySelector('#sim-matb').addEventListener('change', (e) => { state.matB = e.target.value; render(); });
    container.querySelector('#sim-statb').addEventListener('change', (e) => { state.statB = e.target.value; render(); });
    container.querySelector('#sim-valb').addEventListener('change', (e) => { state.valB = Number(e.target.value) || 0; render(); });
    container.querySelector('#sim-cat').addEventListener('change', (e) => { state.catId = e.target.value; render(); });
    container.querySelector('#sim-qty').addEventListener('change', (e) => { state.catQty = Math.max(1, Math.min(99, Number(e.target.value) || 1)); render(); });

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
        const i = Number(el.dataset.bmat);
        b.materia[i].name = el.value;
      });
      container.querySelectorAll('[data-bstat]').forEach((el) => {
        const i = Number(el.dataset.bstat);
        b.materia[i].stat = el.value;
      });
      container.querySelectorAll('[data-bval]').forEach((el) => {
        const i = Number(el.dataset.bval);
        b.materia[i].bonus = Number(el.value) || 0;
      });
      container.querySelectorAll('[data-bacc]').forEach((el) => {
        const i = Number(el.dataset.bacc);
        b.accessories[i] = el.value;
      });
      ctx.storage.set('build', b);
    };
    container.querySelectorAll('[data-bmat],[data-bstat],[data-bval],[data-bacc]').forEach((el) => {
      el.addEventListener('change', () => {
        saveBuild();
        showToast('Build saved');
      });
    });
  }

  render();
}
