import { renderItemsView } from './views/items.js';
import { renderEnemiesView } from './views/enemies.js';
import { renderMissionsView } from './views/missions.js';
import { renderCompendiumView } from './views/compendium.js';
import { renderSuggesterView } from './views/suggester.js';
import { renderGuidesView } from './views/guides.js';
import { renderFusionTrackerView } from './views/fusion-tracker.js';

/**
 * Crisis Core: Final Fantasy VII Reunion (Hard Mode) Module.
 * Enforces Strict Relational Rule:
 *   items.json contains zero hardcoded enemy drop/steal arrays.
 *   All 4-quadrant Item <-> Enemy <-> Mission links are computed dynamically at runtime.
 */
export async function createGameModule({ meta, config, storage, router }) {
  const base = `./${meta.dataPath}`;
  const [missions, enemies, items, shops, guides, fusionRules] = await Promise.all([
    fetch(`${base}/missions.json`).then((r) => r.json()),
    fetch(`${base}/enemies.json`).then((r) => r.json()),
    fetch(`${base}/items.json`).then((r) => r.json()),
    fetch(`${base}/shops.json`).then((r) => r.json()),
    fetch(`${base}/guides.json`).then((r) => r.json()),
    fetch(`${base}/fusion-rules.json`).then((r) => r.json())
  ]);

  const itemById = new Map(items.map((it) => [it.id, it]));
  const enemyById = new Map(enemies.map((en) => [en.id, en]));
  const missionById = new Map(missions.map((m) => [m.id, m]));

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

  function toggleMissionComplete(missionId) {
    const completed = storage.get('completedMissions', {});
    completed[missionId] = !completed[missionId];
    storage.set('completedMissions', completed);
    return completed[missionId];
  }

  function evaluateHardModeReadiness(mission, zackLevel) {
    const rec = mission.hardModeBenchmarks?.recommendedLevel || 1;
    const diff = zackLevel - rec;
    if (diff >= 0) return { key: 'ready', label: 'Ready', tone: 'pill-mako' };
    if (diff >= -8) return { key: 'stretch', label: 'Stretch', tone: 'pill-warn' };
    return { key: 'danger', label: 'Danger', tone: 'pill-danger' };
  }

  const ctx = {
    meta,
    config,
    storage,
    router,
    data: { missions, enemies, items, shops, guides, fusionRules },
    indexes: { itemById, enemyById, missionById },
    getItemLootSources,
    getZackState,
    toggleMissionComplete,
    evaluateHardModeReadiness
  };

  function getSearchEntities() {
    const out = [];
    for (const m of missions) {
      out.push({
        id: m.id,
        type: 'mission',
        typeLabel: `Mission ${m.stars}★`,
        title: `${m.id}: ${m.title}`,
        subtitle: `${m.branchName} · ${m.unlockCondition || ''}`,
        keywords: `${m.clearReward?.rawLabel || ''} ${(m.treasures || []).map((t) => t.rawLabel).join(' ')}`,
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
        keywords: `${it.fusion?.stat || ''} ${(it.shops || []).map((s) => s.shopName).join(' ')}`,
        route: `#/game/${meta.slug}/items/${encodeURIComponent(it.id)}`
      });
    }
    for (const en of enemies) {
      out.push({
        id: en.id,
        type: 'enemy',
        typeLabel: en.isBoss ? 'Boss' : en.family,
        title: en.name,
        subtitle: `Lv.${en.stats?.level ?? '?'} · Hard HP ${en.stats?.hpHard ?? '?'} · ${(en.spawns || []).map((s) => s.missionId).slice(0, 4).join(', ')}`,
        keywords: `${en.family} ${(en.affinities?.weak || []).join(' ')}`,
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
        route: `#/game/${meta.slug}/compendium/shops`
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
        renderMissionsView(container, ctx, entityId);
    }
  }

  return {
    meta,
    config,
    getSearchEntities,
    renderView
  };
}
