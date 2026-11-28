# Personal Game Wiki Hub (PWA)

A modular, offline-ready, client-side **Personal Game Wiki Hub** built for desktop and mobile (iOS & Android PWA), designed to be hosted directly on **GitHub Pages** so updates are as simple as editing HTML or JSON files in your GitHub repository.

---

## 📱 Install & Update on Your Phone

1. **Host on GitHub Pages**:
   - In your GitHub repo: **Settings → Pages → Build and deployment → Deploy from a branch (`main` / `/`)**.
2. **Install on iPhone / iPad (Safari)**:
   - Open your GitHub Pages URL in Safari.
   - Tap the **Share** button → **Add to Home Screen**.
3. **Install on Android (Chrome)**:
   - Open your GitHub Pages URL in Chrome.
   - Tap **⋮ Menu** → **Install App** (or **Add to Home Screen**).
4. **Update from Anywhere**:
   - Whenever you edit `index.html`, `core/*`, or any `games/<slug>/data/*.json` file in your GitHub repo and push/commit, GitHub Pages deploys automatically.
   - Open the app on your phone while online (the Service Worker uses Network-First for HTML/JS/JSON), or tap **⟳ Check GitHub Updates** on the Hub / sidebar to force-sync the latest databases without touching your saved `localStorage` progress.
5. **Backup / Transfer Progress**:
   - Use **⬇ Backup Saves** / **⬆ Restore Saves** on the Hub (`#/`) to export or import all checklists, cleared missions, Zack levels, and Materia builds as JSON.

---

## 🎮 Included Module: Crisis Core: FFVII Reunion (100% Compendium)

- **100% Compendium Dashboard**: Live progress meters across Missions (`x/300`), Trophies (`x/51`), Story Chapters (`x/10`), Mail Senders (`x/20`), DMW (`x/18`), Shops (`x/16`), Missables, Magic Pots (`x/6`), Genji Set (`x/4`), and Buster Sword Proficiency, plus active chapter missable alerts.
- **Story Walkthroughs, Mini-Games & Magic Pots**: Full Chapters 1–10 scenario & story boss guide, interactive **Shinra Manor Safe Code Calculator**, all 10 mini-games (Seven Wonders, 3 Flower Wagons, Sector 5, Squats, Modeoheim, Gongaga Waterfall, Depths of Judgment), and all 6 Magic Pot encounters.
- **All 300 Missions** (`M1-1-1` through `M10-4-3`) with **Unlockable Now** filter, upstream/downstream unlock chains, route/chest notes, Hard Mode benchmarks, clear rewards, treasure chests, and Boss Kill Guides.
- **365 Enemies Bestiary** with offline-bundled local portraits, Hard Mode HP/stats, full elemental/status affinities (`Weak`, `Resist`, `Null`, `Absorb`, `Immune`), combat flags (`Null Physical`/`Magic`), story locations, and all 4 loot slots.
- **Relational Item Database** enforcing the **Strict Relational Rule**: `items.json` contains **zero** hardcoded enemy drop/steal lists; the 4-Quadrant Enemy Drop & Steal Matrix is computed dynamically from `enemies.json`, alongside Materia Cost/Grade/Reverse Fusion Recipes and Accessory effect filters.
- **51 Trophies, 20 Mail Senders (5 Fan Clubs), 16 Shops, 18 DMW & Chapter Missables Trackers**.
- **Guides, Lv. 1–99 Formulas & NG+ Matrix**: Farming playbooks, all 8 stat-leveling Materia guides, Zack Lv. 1–99 base stat table, DMW/Skill Power/Battle Stance mechanics, Status Glossary, Reunion vs. PSP table, and NG+ Carryover Checklist.
- **True Materia Fusion Engine & Live Build Stat Calculator** (`localStorage` namespaced under `wiki:crisis-core-reunion:*`).

---

## 🧩 How to Add a New Game

Adding another game requires **zero changes** to `index.html` or `core/`:

1. Create a folder at `games/<game-slug>/`:
   ```text
   games/<game-slug>/
   ├── config.json          # Theme CSS tokens, navigation tabs, checklistItems
   ├── module.js            # Exports createGameModule({ meta, config, storage, router })
   ├── assets/
   │   └── cover.svg        # Cover art shown on the Game Library Hub
   ├── data/                # Normalized JSON datasets (items, enemies, guides, etc.)
   └── views/               # ES module view renderers
   ```
2. Register the game in `games/registry.json`:
   ```json
   {
     "id": "my-game",
     "slug": "my-game-slug",
     "title": "My Game Title",
     "subtitle": "Compendium Subtitle",
     "edition": "100% Guide",
     "theme": {
       "name": "Custom Theme",
       "accent": "#00e5a3",
       "accentSecondary": "#38bdf8",
       "bgPrimary": "#070b10",
       "bgSurface": "#0f1722"
     },
     "coverArt": "games/my-game-slug/assets/cover.svg",
     "tags": ["RPG", "Tracker"],
     "dataPath": "games/my-game-slug/data",
     "modulePath": "games/my-game-slug/module.js",
     "configPath": "games/my-game-slug/config.json"
   }
   ```
3. Commit and push to GitHub—the new game card will appear on `#/` automatically.

---

## 🔧 Local Development & Data Validation

```bash
# Re-ingest and validate Crisis Core relational JSONs (zero external Python deps)
python scripts/ccff7r_parse_and_validate.py

# Validate existing JSONs offline (0 broken IDs check)
python scripts/ccff7r_parse_and_validate.py --validate-only

# Serve locally
python -m http.server 8765
```
