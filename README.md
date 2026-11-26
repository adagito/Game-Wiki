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

## 🎮 Included Module: Crisis Core: FFVII Reunion (Hard Mode)

- **All 300 Missions** (`M1-1-1` through `M10-4-3`) with branch/star/chapter/readiness filters, Hard Mode benchmarks, clear rewards, treasure chests, and Boss/Random Encounter links.
- **337+ Enemies Bestiary** with Hard Mode HP, stats, weaknesses/immunities, Dossier + Portrait Gallery (zoom lightbox), and all 4 loot slots.
- **Relational Item Database** enforcing the **Strict Relational Rule**: `items.json` contains **zero** hardcoded enemy drop/steal lists; the 4-Quadrant Enemy Drop & Steal Matrix is computed dynamically from `enemies.json`.
- **Hard Mode Level & Chapter Route Suggester** (Lv. 1–99, Ch. 1–10).
- **Hard Mode Farming & Meta Guides** (DMW AFK mastering, Potion/Libra 98–980% pipelines, M6-6-3 / M8-6-4 / M9-5-3 farms, Costly Punch & Genji meta).
- **Interactive Materia Fusion Calculator & Personal Tracker** (`localStorage` namespaced under `wiki:crisis-core-reunion:*`).

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
