import { renderDashboardView } from './views/dashboard.js';
import { renderStoryView } from './views/story.js';
import { renderItemsView } from './views/items.js';
import { renderEnemiesView } from './views/enemies.js';
import { renderMissionsView } from './views/missions.js';
import { renderCompendiumView } from './views/compendium.js';
import { renderSuggesterView } from './views/suggester.js';
import { renderGuidesView } from './views/guides.js';
import { renderFusionTrackerView } from './views/fusion-tracker.js';

/**
 * Crisis Core: Final Fantasy VII Reunion (100% Compendium) Module.
 * Enforces Strict Relational Rule:
 *   items.json contains zero hardcoded enemy drop/steal arrays.
 *   All 4-quadrant Item <-> Enemy <-> Mission links are computed dynamically at runtime.
 */
export async function createGameModule({ meta, config, storage, router }) {
  const base = `./${meta.dataPath}`;
  const [missions, enemies, items, shops, guides, fusionRules, extra] = await Promise.all([
    fetch(`${base}/missions.json`).then((r) => r.json()),
    fetch(`${base}/enemies.json`).then((r) => r.json()),
    fetch(`${base}/items.json`).then((r) => r.json()),
    fetch(`${base}/shops.json`).then((r) => r.json()),
    fetch(`${base}/guides.json`).then((r) => r.json()),
    fetch(`${base}/fusion-rules.json`).then((r) => r.json()),
    fetch(`${base}/compendium-extra.json`).then((r) => r.json()).catch(() => ({}))
  ]);

  const itemById = new Map(items.map((it) => [it.id, it]));
  const enemyById = new Map(enemies.map((en) => [en.id, en]));
  const missionById = new Map(missions.map((m) => [m.id, m]));
  const shopById = new Map(shops.map((s) => [s.id, s]));
  const shopByName = new Map(shops.map((s) => [s.name.toLowerCase(), s]));

  // Build reverse unlock graph: missionId -> downstream missions unlocked by it
  const unlocksByMission = new Map();
  for (const m of missions) {
    for (const pid of m.prerequisiteMissionIds || []) {
      if (!unlocksByMission.has(pid)) unlocksByMission.set(pid, []);
      unlocksByMission.get(pid).push(m);
    }
  }

  const itemLootMatrix = new Map();
  for (const it of items) {
    itemLootMatrix.set(it.id, {
      commonDrop: [],
      rareDrop: [],
      commonSteal: [],
      rareSteal: []
    });
  }
  for (const en of enemies) {
    const loot = en.loot || {};
    for (const slot of ['commonDrop', 'rareDrop', 'commonSteal', 'rareSteal']) {
      const iid = loot[slot];
      if (iid && itemLootMatrix.has(iid)) {
        itemLootMatrix.get(iid)[slot].push(en);
      }
    }
  }

  function getItemLootSources(itemId) {
    return (
      itemLootMatrix.get(itemId) || {
        commonDrop: [],
        rareDrop: [],
        commonSteal: [],
        rareSteal: []
      }
    );
  }

  function resolvePortrait(en) {
    const p = en?.portrait || {};
    const fallback = `./${p.fallbackSvg || 'games/crisis-core-reunion/assets/portraits/family-fiend.svg'}`;
    const local = p.localPath ? `./${p.localPath}` : '';
    const remote = p.imageUrl || '';
    return {
      primary: local || remote || fallback,
      secondary: remote || fallback,
      fallback
    };
  }

  /**
   * Computes resulting Materia (and rule explanation) for any Materia A + Materia B + optional Mastered flags.
   */
  function computeMateriaFusion(matAId, masteredA = false, matBId, masteredB = false, catalystId = null) {
    const catMap = fusionRules?.materiaCatalog || {};
    const classDefs = fusionRules?.classDefinitions || {};
    const classMatrix = fusionRules?.classMatrix || {};
    const overrides = fusionRules?.specialOverrides || [];

    const mA = itemById.get(matAId);
    const mB = itemById.get(matBId);
    const infoA = catMap[matAId];
    const infoB = catMap[matBId];
    if (!mA || !mB || !infoA || !infoB) {
      return { resultItem: mA || null, resultClass: infoA?.fusionClass || '—', targetGrade: 1, reason: 'Select two valid Materia.' };
    }

    // 1. Check exact special overrides (symmetric)
    for (const ov of overrides) {
      if (ov.matchClasses) {
        const [c1, c2] = ov.matchClasses;
        if ((infoA.fusionClass === c1 && infoB.fusionClass === c2) || (infoA.fusionClass === c2 && infoB.fusionClass === c1)) {
          const rItem = itemById.get(ov.resultId);
          if (rItem) {
            return {
              resultItem: rItem,
              resultClass: catMap[rItem.id]?.fusionClass || 'Special',
              targetGrade: catMap[rItem.id]?.grade || 8,
              reason: ov.note
            };
          }
        }
      }
      if (ov.matchNames) {
        const [n1, n2] = ov.matchNames.map((s) => s.toLowerCase());
        const aL = mA.name.toLowerCase();
        const bL = mB.name.toLowerCase();
        if ((aL === n1 && bL === n2) || (aL === n2 && bL === n1)) {
          const rItem = itemById.get(ov.resultId);
          if (rItem) {
            return {
              resultItem: rItem,
              resultClass: catMap[rItem.id]?.fusionClass || 'Special',
              targetGrade: catMap[rItem.id]?.grade || 7,
              reason: ov.note
            };
          }
        }
      }
    }

    // 2. Class lookup + Grade calculation
    const cA = infoA.fusionClass;
    const cB = infoB.fusionClass;
    let resClass = classMatrix[cA]?.[cB] || classMatrix[cB]?.[cA] || cA;

    // 3. Target grade: max(gradeA, gradeB) + mastered bonus (+1 each, max 8)
    const masterBonus = (masteredA ? 1 : 0) + (masteredB ? 1 : 0);
    const baseGrade = Math.max(infoA.grade || 1, infoB.grade || 1);
    const targetGrade = Math.max(1, Math.min(8, baseGrade + masterBonus));

    // Catalyst grade floor (if high-tier item pushes grade)
    const catItem = catalystId ? itemById.get(catalystId) : null;
    const catBoost = catItem?.category === 'max-tier-fusion' ? 1 : 0;
    const finalGrade = Math.max(1, Math.min(8, Math.max(targetGrade, baseGrade + catBoost)));

    const rows = classDefs[resClass] || classDefs[cA] || [];
    let chosen = rows.find((r) => r.grade === finalGrade && r.itemId);
    if (!chosen) {
      chosen = [...rows].reverse().find((r) => r.grade <= finalGrade && r.itemId) || rows.find((r) => r.itemId);
    }
    const resultItem = chosen?.itemId ? itemById.get(chosen.itemId) : mA;

    const reason =
      cA === cB
        ? `Same class (${cA}): Base Grade ${baseGrade}${masterBonus ? ` + ${masterBonus} Mastered` : ''} → Grade ${finalGrade}.`
        : `${cA} (G${infoA.grade}) + ${cB} (G${infoB.grade}) → ${resClass} at Grade ${finalGrade}${masterBonus ? ` (+${masterBonus} Mastered)` : ''}.`;

    return {
      resultItem,
      resultClass: resClass,
      targetGrade: finalGrade,
      reason
    };
  }

  /**
   * Reverse recipe lookup: returns curated + algorithmic ways to fuse targetMateriaId.
   */
  function findRecipesForMateria(targetItemId) {
    const recipes = [];
    const seen = new Set();
    const pushRecipe = (aName, bName, note, aId = null, bId = null) => {
      const key = `${aName}__${bName}`;
      if (seen.has(key)) return;
      seen.add(key);
      recipes.push({ ingredientA: aName, ingredientB: bName, note, aId, bId });
    };

    for (const kr of fusionRules?.keyRecipes || []) {
      if (kr.resultId === targetItemId) {
        pushRecipe(kr.ingredientA, kr.ingredientB, kr.note);
      }
    }
    for (const ov of fusionRules?.specialOverrides || []) {
      if (ov.resultId === targetItemId && ov.matchNames) {
        pushRecipe(ov.matchNames[0], ov.matchNames[1], ov.note);
      }
    }

    const catMap = fusionRules?.materiaCatalog || {};
    const targetInfo = catMap[targetItemId];
    const targetItem = itemById.get(targetItemId);
    if (targetInfo && targetItem) {
      const tClass = targetInfo.fusionClass;
      const tGrade = targetInfo.grade || 1;
      const classDefs = fusionRules?.classDefinitions || {};
      const classMatrix = fusionRules?.classMatrix || {};

      const sameRows = (classDefs[tClass] || []).filter((r) => r.itemId && r.itemId !== targetItemId && r.grade <= tGrade);
      if (sameRows.length) {
        const lower = sameRows[sameRows.length - 1];
        if (tGrade > lower.grade) {
          pushRecipe(
            `${lower.name} (Mastered)`,
            tGrade - lower.grade >= 2 ? `${lower.name} (Mastered)` : 'Libra (Mastered)',
            `Grade-bump within ${tClass} class (Grade ${lower.grade} → ${tGrade}).`,
            lower.itemId,
            tGrade - lower.grade >= 2 ? lower.itemId : 'item_libra'
          );
        }
      }

      for (const [cA, rowMap] of Object.entries(classMatrix)) {
        for (const [cB, resC] of Object.entries(rowMap)) {
          if (resC !== tClass || cA === tClass || cB === tClass) continue;
          if (cB === 'Libra' || cA === 'Libra') continue;
          const listA = (classDefs[cA] || []).filter((r) => r.itemId);
          const listB = (classDefs[cB] || []).filter((r) => r.itemId);
          const pickA = listA.find((r) => r.grade >= Math.max(1, tGrade - 1)) || listA[listA.length - 1];
          const pickB = listB.find((r) => r.grade >= 1) || listB[0];
          if (pickA && pickB) {
            pushRecipe(
              pickA.name,
              pickB.name,
              `${cA} + ${cB} → ${tClass} (Grade ${tGrade})`,
              pickA.itemId,
              pickB.itemId
            );
          }
          if (recipes.length >= 8) break;
        }
        if (recipes.length >= 8) break;
      }

      if (!recipes.length && targetItem.name) {
        pushRecipe(targetItem.name, 'Libra (w/ +98 or +980% stat)', 'Keep your Materia intact while infusing stats via Libra transfer.');
      }
    }
    return recipes.slice(0, 8);
  }

  function getZackState() {
    return {
      level: Number(storage.get('zackLevel', 25)) || 25,
      chapter: Number(storage.get('zackChapter', 4)) || 4,
      completedMissions: storage.get('completedMissions', {}),
      checklist: storage.get('checklist', {}),
      build: storage.get('build', {
        materia: Array.from({ length: 6 }, () => ({ name: '', stat: 'HP%', bonus: 0 })),
        accessories: ['', '', '', '']
      })
    };
  }

  function getSidebarStatus() {
    const zack = getZackState();
    const missionsDone = missions.filter((m) => zack.completedMissions[m.id]).length;
    return {
      level: zack.level,
      chapter: zack.chapter,
      missionsDone,
      missionsTotal: missions.length
    };
  }

  function toggleMissionComplete(missionId) {
    const completed = storage.get('completedMissions', {});
    completed[missionId] = !completed[missionId];
    storage.set('completedMissions', completed);
    window.dispatchEvent(new CustomEvent('wiki:zack-updated'));
    return completed[missionId];
  }

  function evaluateHardModeReadiness(mission, zackLevel) {
    const rec = mission.hardModeBenchmarks?.recommendedLevel || 1;
    const diff = zackLevel - rec;
    if (diff >= 0) return { key: 'ready', label: 'Ready', tone: 'pill-mako' };
    if (diff >= -8) return { key: 'stretch', label: 'Stretch', tone: 'pill-warn' };
    return { key: 'danger', label: 'Danger', tone: 'pill-danger' };
  }

  function resolveRouteMeta(viewId, entityId = null) {
    const slug = meta.slug;
    const rootCrumb = { label: 'Crisis Core', route: `#/game/${slug}/dashboard` };
    const tabObj = (config.tabs || []).find((t) => t.id === viewId);
    const tabLabel = tabObj?.label || viewId;
    const viewRoute = `#/game/${slug}/${viewId}`;

    if (viewId === 'missions') {
      if (entityId && missionById.has(entityId)) {
        const m = missionById.get(entityId);
        return {
          title: `${m.id}: ${m.title}`,
          typeLabel: 'Mission',
          breadcrumbs: [rootCrumb, { label: 'Missions', route: viewRoute }, { label: `${m.id} · ${m.title}`, route: null }]
        };
      }
      return {
        title: 'Missions (300)',
        typeLabel: 'Missions',
        breadcrumbs: [rootCrumb, { label: 'Missions', route: null }]
      };
    }

    if (viewId === 'items') {
      if (entityId && itemById.has(entityId)) {
        const it = itemById.get(entityId);
        return {
          title: it.name,
          typeLabel: 'Item',
          breadcrumbs: [rootCrumb, { label: 'Items & Materia', route: viewRoute }, { label: it.name, route: null }]
        };
      }
      return {
        title: 'Items & Materia',
        typeLabel: 'Database',
        breadcrumbs: [rootCrumb, { label: 'Items & Materia', route: null }]
      };
    }

    if (viewId === 'enemies') {
      if (entityId && enemyById.has(entityId)) {
        const en = enemyById.get(entityId);
        return {
          title: en.name,
          typeLabel: en.isBoss ? 'Boss' : 'Enemy',
          breadcrumbs: [rootCrumb, { label: 'Enemy Bestiary', route: viewRoute }, { label: en.name, route: null }]
        };
      }
      return {
        title: 'Enemy Bestiary',
        typeLabel: 'Bestiary',
        breadcrumbs: [rootCrumb, { label: 'Enemy Bestiary', route: null }]
      };
    }

    if (viewId === 'story') {
      const chapters = extra.storyChapters || [];
      if (entityId === 'minigames') {
        return {
          title: 'Mini-Games & Safe Code',
          typeLabel: 'Story',
          breadcrumbs: [rootCrumb, { label: 'Story & Side-Quests', route: viewRoute }, { label: 'Mini-Games & Safe Code', route: null }]
        };
      }
      if (entityId === 'magic-pot') {
        return {
          title: 'Magic Pots (All 6)',
          typeLabel: 'Story',
          breadcrumbs: [rootCrumb, { label: 'Story & Side-Quests', route: viewRoute }, { label: 'Magic Pots', route: null }]
        };
      }
      const ch = chapters.find((c) => c.id === entityId);
      if (ch) {
        return {
          title: `Ch. ${ch.chapter}: ${ch.title}`,
          typeLabel: 'Story',
          breadcrumbs: [rootCrumb, { label: 'Story & Side-Quests', route: viewRoute }, { label: `Chapter ${ch.chapter}`, route: null }]
        };
      }
      return {
        title: 'Story & Side-Quests',
        typeLabel: 'Story',
        breadcrumbs: [rootCrumb, { label: 'Story & Side-Quests', route: null }]
      };
    }

    if (viewId === 'compendium') {
      const [secTab, focusId] = String(entityId || '').split('/');
      const tabLabels = {
        trophies: '51 Trophies',
        mail: '20 Mail & Fan Clubs',
        shops: 'All 16 Shops',
        dmw: '18-Image DMW',
        missables: 'Chapter Missables'
      };
      if (secTab && tabLabels[secTab]) {
        const subCrumb = { label: tabLabels[secTab], route: `${viewRoute}/${secTab}` };
        if (secTab === 'shops' && focusId && shopById.has(focusId)) {
          const sh = shopById.get(focusId);
          return {
            title: sh.name,
            typeLabel: 'Shop',
            breadcrumbs: [rootCrumb, { label: 'Trackers & Trophies', route: viewRoute }, subCrumb, { label: sh.name, route: null }]
          };
        }
        return {
          title: tabLabels[secTab],
          typeLabel: 'Tracker',
          breadcrumbs: [rootCrumb, { label: 'Trackers & Trophies', route: viewRoute }, { label: tabLabels[secTab], route: null }]
        };
      }
      return {
        title: 'Trackers & Trophies',
        typeLabel: 'Tracker',
        breadcrumbs: [rootCrumb, { label: 'Trackers & Trophies', route: null }]
      };
    }

    if (viewId === 'guides') {
      const pb = (guides.farmingPlaybooks || []).find((p) => p.id === entityId);
      const sg = (guides.statLevelingGuides || []).find((s) => s.id === entityId);
      const sec = (guides.sections || []).find((s) => s.id === entityId);
      const gModeLabels = {
        playbooks: 'Farming Playbooks',
        stats: 'Stat-Leveling Materia',
        systems: 'Bosses & Systems',
        mechanics: 'Mechanics & Formulas'
      };
      if (pb) {
        return {
          title: pb.shortLabel || pb.title,
          typeLabel: 'Guide',
          breadcrumbs: [rootCrumb, { label: 'Guides & Mechanics', route: viewRoute }, { label: pb.shortLabel || pb.title, route: null }]
        };
      }
      if (sg) {
        return {
          title: `${sg.stat} Guide`,
          typeLabel: 'Guide',
          breadcrumbs: [rootCrumb, { label: 'Guides & Mechanics', route: viewRoute }, { label: `${sg.stat} Guide`, route: null }]
        };
      }
      if (sec) {
        return {
          title: sec.title,
          typeLabel: 'Guide',
          breadcrumbs: [rootCrumb, { label: 'Guides & Mechanics', route: viewRoute }, { label: sec.title, route: null }]
        };
      }
      if (entityId && gModeLabels[entityId]) {
        return {
          title: gModeLabels[entityId],
          typeLabel: 'Guide',
          breadcrumbs: [rootCrumb, { label: 'Guides & Mechanics', route: viewRoute }, { label: gModeLabels[entityId], route: null }]
        };
      }
      return {
        title: 'Guides & Mechanics',
        typeLabel: 'Guides',
        breadcrumbs: [rootCrumb, { label: 'Guides & Mechanics', route: null }]
      };
    }

    if (viewId === 'dashboard') {
      return {
        title: 'Command Center',
        typeLabel: 'Overview',
        breadcrumbs: [rootCrumb, { label: 'Command Center', route: null }]
      };
    }

    return {
      title: tabLabel,
      typeLabel: tabObj?.group || 'View',
      breadcrumbs: [rootCrumb, { label: tabLabel, route: null }]
    };
  }

  const ctx = {
    meta,
    config,
    storage,
    router,
    viewState: {},
    data: { missions, enemies, items, shops, guides, fusionRules, extra },
    indexes: { itemById, enemyById, missionById, shopById, shopByName, unlocksByMission },
    getItemLootSources,
    resolvePortrait,
    computeMateriaFusion,
    findRecipesForMateria,
    getZackState,
    getSidebarStatus,
    toggleMissionComplete,
    evaluateHardModeReadiness
  };

  function getSearchEntities() {
    const out = [];
    for (const sc of extra.storyChapters || []) {
      out.push({
        id: sc.id,
        type: 'story',
        typeLabel: `Story Ch.${sc.chapter}`,
        title: sc.title,
        subtitle: `${sc.location} · ${sc.summary}`,
        keywords: `${(sc.keyObjectives || []).join(' ')} ${(sc.storyPickups || []).join(' ')} ${sc.missableAlert || ''}`,
        route: `#/game/${meta.slug}/story/${encodeURIComponent(sc.id)}`
      });
    }
    for (const tr of extra.trophies || []) {
      out.push({
        id: tr.id,
        type: 'trophy',
        typeLabel: `Trophy (${tr.grade})`,
        title: tr.name,
        subtitle: `${tr.chapter} · ${tr.description}`,
        keywords: `${tr.howToUnlock} ${tr.missable ? 'missable trophy achievement' : 'trophy achievement'} ${tr.category}`,
        route: `#/game/${meta.slug}/compendium/trophies`
      });
    }
    for (const ms of extra.mailSenders || []) {
      out.push({
        id: ms.id,
        type: 'mail',
        typeLabel: ms.missable ? 'Missable Mail' : 'Mail Sender',
        title: `${ms.name} (${ms.mailCount} mails)`,
        subtitle: `${ms.chapters} · ${ms.unlockCondition}`,
        keywords: `${ms.category} ${ms.missableChoices || ''} fan club mail completionist`,
        route: `#/game/${meta.slug}/compendium/mail`
      });
    }
    for (const mg of extra.minigames || []) {
      out.push({
        id: mg.id,
        type: 'minigame',
        typeLabel: `Mini-Game (${mg.chapter})`,
        title: mg.title,
        subtitle: mg.summary,
        keywords: `${mg.trophy || ''} ${(mg.steps || []).join(' ')} safe code seven wonders flower wagon squats`,
        route: `#/game/${meta.slug}/story/minigames`
      });
    }
    for (const mp of extra.magicPotEncounters || []) {
      out.push({
        id: mp.id,
        type: 'magicpot',
        typeLabel: `Magic Pot (${mp.missionId})`,
        title: mp.title,
        subtitle: `Requests: ${(mp.requests || []).map((r) => r.action).join(' → ')} · Reward: ${mp.rewardName}`,
        keywords: `${mp.missionId} ${mp.rewardName} ${mp.tips}`,
        route: `#/game/${meta.slug}/story/magic-pot`
      });
    }
    for (const se of extra.mechanics?.statusEffects || []) {
      out.push({
        id: se.id,
        type: 'status',
        typeLabel: `${se.kind}`,
        title: `Status: ${se.name}`,
        subtitle: `${se.effect} · Counter: ${se.counter}`,
        keywords: `status ailment buff immunity ${se.name}`,
        route: `#/game/${meta.slug}/guides/mechanics`
      });
    }
    for (const m of missions) {
      const bg = m.bossGuide;
      out.push({
        id: m.id,
        type: 'mission',
        typeLabel: `Mission ${m.stars}★`,
        title: `${m.id}: ${m.title}`,
        subtitle: `${bg ? `Boss: ${bg.targetName} · ` : ''}${m.branchName} · ${m.unlockCondition || ''}`,
        keywords: `${m.clearReward?.rawLabel || ''} ${(m.treasures || []).map((t) => t.rawLabel).join(' ')} ${bg?.targetName || ''} ${bg?.encounterType || ''} ${bg?.summary || ''}`,
        route: `#/game/${meta.slug}/missions/${encodeURIComponent(m.id)}`
      });
    }
    for (const it of items) {
      out.push({
        id: it.id,
        type: 'item',
        typeLabel: it.category,
        title: it.name,
        subtitle: it.description || it.subCategory || '',
        keywords: `${it.fusion?.stat || ''} ${(it.shops || []).map((s) => s.shopName).join(' ')} ${(it.accessory?.effectTags || []).join(' ')}`,
        route: `#/game/${meta.slug}/items/${encodeURIComponent(it.id)}`
      });
    }
    for (const en of enemies) {
      out.push({
        id: en.id,
        type: 'enemy',
        typeLabel: en.isBoss ? 'Boss' : en.family,
        title: en.name,
        subtitle: `Lv.${en.stats?.level ?? '?'} · Hard HP ${en.stats?.hpHard ?? '?'} · ${(en.spawns || []).map((s) => s.missionId).slice(0, 4).join(', ') || (en.storyLocations || []).join(', ')}`,
        keywords: `${en.family} ${(en.affinities?.weak || []).join(' ')} ${(en.storyLocations || []).join(' ')}`,
        route: `#/game/${meta.slug}/enemies/${encodeURIComponent(en.id)}`
      });
    }
    for (const sh of shops) {
      out.push({
        id: sh.id,
        type: 'shop',
        typeLabel: sh.missable ? 'Missable Shop' : 'Shop',
        title: sh.name,
        subtitle: sh.unlockCondition,
        keywords: (sh.stock || []).map((st) => itemById.get(st.itemId)?.name || '').join(' '),
        route: `#/game/${meta.slug}/compendium/shops/${encodeURIComponent(sh.id)}`
      });
    }
    for (const d of guides.dmwImages || []) {
      out.push({
        id: d.id,
        type: 'dmw',
        typeLabel: `DMW ${d.group}`,
        title: `${d.name} (${d.limitBreak})`,
        subtitle: d.unlockCondition,
        keywords: d.missable ? 'missable dmw genji armor' : 'dmw',
        route: `#/game/${meta.slug}/compendium/dmw`
      });
    }
    for (const pb of guides.farmingPlaybooks || []) {
      out.push({
        id: pb.id,
        type: 'playbook',
        typeLabel: 'Farming Playbook',
        title: pb.title,
        subtitle: pb.summary,
        keywords: `${pb.shortLabel} ${pb.proTip}`,
        route: `#/game/${meta.slug}/guides/${encodeURIComponent(pb.id)}`
      });
    }
    for (const sg of guides.statLevelingGuides || []) {
      out.push({
        id: sg.id,
        type: 'statguide',
        typeLabel: `${sg.stat} Guide`,
        title: sg.title,
        subtitle: `${sg.cap} · ${sg.priority}`,
        keywords: `${sg.stat} ${sg.whyMatters}`,
        route: `#/game/${meta.slug}/guides/${encodeURIComponent(sg.id)}`
      });
    }
    for (const sec of guides.sections || []) {
      out.push({
        id: sec.id,
        type: 'guide',
        typeLabel: 'Guide',
        title: sec.title,
        subtitle: sec.summary,
        keywords: (sec.blocks || []).map((b) => b.heading).join(' '),
        route: `#/game/${meta.slug}/guides/${encodeURIComponent(sec.id)}`
      });
    }
    return out;
  }

  async function renderView({ container, viewId, entityId }) {
    switch (viewId) {
      case 'dashboard':
        renderDashboardView(container, ctx);
        break;
      case 'story':
        renderStoryView(container, ctx, entityId);
        break;
      case 'items':
        renderItemsView(container, ctx, entityId);
        break;
      case 'enemies':
        renderEnemiesView(container, ctx, entityId);
        break;
      case 'missions':
        renderMissionsView(container, ctx, entityId);
        break;
      case 'compendium':
        renderCompendiumView(container, ctx, entityId);
        break;
      case 'suggester':
        renderSuggesterView(container, ctx);
        break;
      case 'guides':
        renderGuidesView(container, ctx, entityId);
        break;
      case 'fusion-tracker':
        renderFusionTrackerView(container, ctx);
        break;
      default:
        renderDashboardView(container, ctx);
    }
  }

  return {
    meta,
    config,
    getSearchEntities,
    getSidebarStatus,
    resolveRouteMeta,
    renderView
  };
}
