#!/usr/bin/env python3
"""
Crisis Core: Final Fantasy VII Reunion (Hard Mode)
Data Ingestion, Relational Normalization & Integrity Validation Script (v2.0.0).

Uses Python 3 standard library only.
- Default run: fetches Fandom MediaWiki API data (cached under scripts/.cache/),
  normalizes all 300 missions, enemies/bosses, items/accessories/materia, 16 shops,
  18 DMW entries, Reunion guides/missables/farming matrix, and fusion rules into
  games/crisis-core-reunion/data/, generates PWA PNG/SVG assets, and validates
  zero broken IDs and zero enemy-less missions.
- --validate-only: verifies existing JSON datasets without network calls.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import re
import struct
import sys
import urllib.parse
import urllib.request
import zlib
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ccff7r_compendium_data import (
    CURATED_MISSION_ROUTE_NOTES,
    EXPANDED_MISSABLES,
    STORY_ENEMY_CHAPTERS,
    build_compendium_extra_json,
    build_full_fusion_rules,
    enrich_items_metadata,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "games" / "crisis-core-reunion" / "data"
ASSETS_DIR = ROOT / "games" / "crisis-core-reunion" / "assets"
PORTRAITS_DIR = ASSETS_DIR / "portraits"
ICONS_DIR = ROOT / "core" / "icons"
CACHE_DIR = Path(__file__).resolve().parent / ".cache"

API_BASE = "https://finalfantasy.fandom.com/api.php"
HEADERS = {"User-Agent": "PersonalGameWikiHub/2.0 (CrisisCoreReunion; static-build)"}

BRANCH_TITLES = [
    ("M1", "M1: Shinra Electric Power Company", "Shinra Electric Power Company"),
    ("M2", "M2: Monster Research Project", "Monster Research Project"),
    ("M3", "M3: Genesis's Forces", "Genesis's Forces"),
    ("M4", "M4: To End the War with Wutai", "To End the War with Wutai"),
    ("M5", "M5: Hojo's Laboratory", "Hojo's Laboratory"),
    ("M6", "M6: Seeking Precious Items", "Seeking Precious Items"),
    ("M7", "M7: Seeking Priceless Items", "Seeking Priceless Items"),
    ("M8", "M8: Zack, the Materia Hunter", "Zack, the Materia Hunter"),
    ("M9", "M9: Great Cavern of Wonders", "Great Cavern of Wonders"),
    ("M10", "M10: Mysteries of the World", "Mysteries of the World"),
]

EXTRA_ENEMY_PAGES = [
    "Bahamut (Crisis Core boss)",
    "Bahamut Fury (Crisis Core boss)",
    "Ifrit (Crisis Core boss)",
    "Crazy Dagger",
]

ITEM_ALIAS_MAP = {
    "soma drop": "Soma",
    "gysahl green": "Gysahl Greens",
    "gysahl greens": "Gysahl Greens",
    "phoenix down": "Phoenix Down",
    "hp+": "HP Up",
    "hp up+": "HP Up+",
    "hp up++": "HP Up++",
    "mp+": "MP Up",
    "mp up+": "MP Up+",
    "mp up++": "MP Up++",
    "ap+": "AP Up",
    "ap up+": "AP Up+",
    "ap up++": "AP Up++",
    "atk+": "ATK Up",
    "attack up": "ATK Up",
    "atk up+": "ATK Up+",
    "atk up++": "ATK Up++",
    "vit+": "VIT Up",
    "vitality up": "VIT Up",
    "vit up+": "VIT Up+",
    "vit up++": "VIT Up++",
    "mag+": "MAG Up",
    "magic up": "MAG Up",
    "mag up+": "MAG Up+",
    "mag up++": "MAG Up++",
    "magic up++": "MAG Up++",
    "spr+": "SPR Up",
    "spirit up": "SPR Up",
    "spr up+": "SPR Up+",
    "spr up++": "SPR Up++",
    "lck+": "LCK Up",
    "libra": "Libra",
    "bronze bracers": "Bronze Armlet",
    "silver bracers": "Silver Armlet",
    "gold bracers": "Gold Armlet",
    "rune bracers": "Rune Armlet",
    "rune bangle": "Rune Armlet",
    "mithril": "Mythril",
    "mythril": "Mythril",
    "zeio nut": "Zeio Nut",
    "fat chocobo feather": "Fat Chocobo Feather",
    "lunar harp": "Lunar Harp",
    "hero drink": "Hero Drink",
    "dark matter": "Dark Matter",
    "adamantite": "Adamantite",
    "mog's amulet": "Mog's Amulet",
    "mogs amulet": "Mog's Amulet",
    "mog's armlet": "Mog's Amulet",
    "mogs armlet": "Mog's Amulet",
    "jeweled ring": "Jeweled Ring",
    "adaman bangle": "Adaman Bangle",
    "genji helm": "Genji Helm",
    "genji armor": "Genji Armor",
    "genji shield": "Genji Shield",
    "genji glove": "Genji Glove",
    "divine slayer": "Divine Slayer",
    "heike soul": "Heike Soul",
    "costly punch": "Costly Punch",
    "aerial drain": "Aerial Drain",
    "hell firaga": "Hell Firaga",
    "hell blizzaga": "Hell Blizzaga",
    "hell thundaga": "Hell Thundaga",
    "status ward": "Status Ward",
    "moogle power": "Moogle Power",
    "dualcast": "Dualcast",
    "sp master": "SP Master",
    "ziedrich": "Ziedrich",
    "precious watch": "Precious Watch",
    "exa flare": "Exaflare",
    "mega flare": "Megaflare",
    "magic barrier": "MBarrier",
    "earring": "Earrings",
    "iron punch": "Iron Fist",
    "stop sword": "Stop Blade",
    "brigand's gloves": "Brigand's Gloves",
    "thief gloves": "Brigand's Gloves",
    "net shop shade": "Online Shop Shade",
    "network shop shade": "Online Shop Shade",
    "network shop duo": "Online Shop Duo",
    "mythril mine traders": "Mythril Mine Trading",
    "bone village commerce": "Bone Village Outlet",
    "sec.5 materia shop": "Sector 5 Materia Shop",
    "sec. 5 materia shop": "Sector 5 Materia Shop",
    "sector 5 - materia shop": "Sector 5 Materia Shop",
    "sec.6 accessory shop": "Sector 6 Accessory Shop",
    "sec. 6 accessory shop": "Sector 6 Accessory Shop",
    "sector 6 - accessory shop": "Sector 6 Accessory Shop",
    "sec.7 shop": "Sector 7 Shop",
    "sec. 7 shop": "Sector 7 Shop",
    "sector 7 - shop": "Sector 7 Shop",
    "sec.8 materia shop": "Sector 8 Materia Shop",
    "sec. 8 materia shop": "Sector 8 Materia Shop",
    "sector 8 - materia shop": "Sector 8 Materia Shop",
    "cactus thorn": "Cactus Thorn",
    "tonberry's knife": "Tonberry's Knife",
    "tonberrys knife": "Tonberry's Knife",
    "goddess key": "Goddess Key",
}

FORBIDDEN_ITEM_KEYS = {
    "commonDrop",
    "rareDrop",
    "commonSteal",
    "rareSteal",
    "droppedBy",
    "stolenFrom",
    "enemySources",
}


def slugify(text: str) -> str:
    s = text.replace("++", "_plus_plus").replace("+", "_plus")
    s = s.replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return s or "unknown"


def cached_api_get(params: dict[str, str], cache_key: str) -> dict[str, Any]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(cache_key.encode("utf-8")).hexdigest()[:16]
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", cache_key)[:40]
    cache_file = CACHE_DIR / f"{safe_name}_{digest}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    query = urllib.parse.urlencode(params)
    url = f"{API_BASE}?{query}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def fetch_pages_by_titles(titles: list[str]) -> dict[str, str]:
    results: dict[str, str] = {}
    for i in range(0, len(titles), 25):
        chunk = titles[i : i + 25]
        data = cached_api_get(
            {
                "action": "query",
                "titles": "|".join(chunk),
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "redirects": "1",
                "format": "json",
            },
            f"pages2_{i}_{chunk[0]}",
        )
        pages = data.get("query", {}).get("pages", {})
        for p in pages.values():
            title = p.get("title", "")
            revs = p.get("revisions") or []
            if revs:
                content = revs[0].get("slots", {}).get("main", {}).get("*", "")
                if content:
                    results[title] = content
    return results


def fetch_category_members(category: str) -> list[str]:
    members: list[str] = []
    cmcontinue = None
    idx = 0
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": "500",
            "format": "json",
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
        data = cached_api_get(params, f"cat2_{category}_{idx}")
        for m in data.get("query", {}).get("categorymembers", []):
            if m.get("ns") == 0:
                members.append(m["title"])
        cmcontinue = data.get("continue", {}).get("cmcontinue")
        if not cmcontinue:
            break
        idx += 1
    return members


def fetch_image_urls(filenames: list[str]) -> dict[str, str]:
    url_map: dict[str, str] = {}
    clean = sorted({f.strip() for f in filenames if f and f.strip()})
    for i in range(0, len(clean), 40):
        chunk = clean[i : i + 40]
        titles = "|".join(f"File:{name}" if not name.startswith("File:") else name for name in chunk)
        data = cached_api_get(
            {
                "action": "query",
                "titles": titles,
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json",
            },
            f"img2_{i}_{chunk[0]}",
        )
        pages = data.get("query", {}).get("pages", {})
        for p in pages.values():
            t = p.get("title", "")
            info = p.get("imageinfo") or []
            if info and info[0].get("url"):
                bare = t.replace("File:", "", 1).strip()
                url_map[bare.replace("_", " ").lower()] = info[0]["url"]
                url_map[bare.lower()] = info[0]["url"]
    return url_map


def clean_wiki_text(raw: str) -> str:
    if not raw:
        return ""
    s = raw
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<ref[^/]*/>", "", s)
    s = re.sub(r"<br\s*/?>", ", ", s, flags=re.I)
    s = re.sub(r"\{\{note\|[^}]*\}\}", "", s, flags=re.I)
    s = re.sub(r"\{\{J\|[^}]*\}\}", "", s)

    def _tpl_repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        parts = [p.strip() for p in inner.split("|")]
        if parts[0].upper() in ("LA", "L", "A"):
            return parts[-1] if len(parts) > 1 else ""
        if parts[0].lower() in ("file", "image"):
            return ""
        return parts[-1]

    for _ in range(3):
        s = re.sub(r"\{\{([^{}]+)\}\}", _tpl_repl, s)

    s = re.sub(r"\[\[(?:File|Image):[^\]]+\]\]", "", s, flags=re.I)

    def _link_repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        if "|" in inner:
            return inner.split("|")[-1].strip()
        return inner.split("#")[-1].strip()

    s = re.sub(r"\[\[([^\]]+)\]\]", _link_repl, s)
    s = re.sub(r"''+", "", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def canonical_item_name(raw_name: str) -> str:
    name = clean_wiki_text(raw_name)
    # Strip trailing/embedded annotations
    name = re.split(r"\s*\|\s*", name)[0]
    if "#" in name:
        name = name.split("#")[-1]
    name = re.sub(r"\([^)]*(?:Crisis Core|item|Materia|M|C|S|I|DMW|Accessory|Shop|rare|inventory|Nibelheim)[^)]*\)", "", name, flags=re.I)
    name = re.sub(r"\b(?:give to researcher and receive|receive)\b.*$", "", name, flags=re.I)
    name = re.sub(r"\s*w/\s*.*$", "", name, flags=re.I)
    name = re.sub(r"^\s*\d+\s*[x×]\s*", "", name, flags=re.I)
    name = re.sub(r"\s*[x×]\s*\d+\s*(?:\([^)]*\))?$", "", name, flags=re.I)
    name = re.sub(r"\s+\bitem\b$", "", name.strip(), flags=re.I)
    if not any(g in name.lower() for g in ("light ", "heaven ", "ground ", "star ", "life ", "being ", "sabbath ", "goddess")):
        name = re.sub(r"\s+\bmateria\b$", "", name.strip(), flags=re.I)
    name = name.strip(" .,:;-")
    low = name.lower()
    if low in ITEM_ALIAS_MAP:
        return ITEM_ALIAS_MAP[low]
    if low.endswith("s") and low[:-1] in ITEM_ALIAS_MAP:
        return ITEM_ALIAS_MAP[low[:-1]]
    return name


def parse_item_qty_entries(raw: str) -> list[tuple[str, int, str]]:
    """Splits a reward or chest cell into clean (canonical_name, quantity, raw_label) tuples."""
    if not raw:
        return []
    # Split on <br/> or commas outside brackets
    raw_parts = re.split(r"<br\s*/?>|,(?![^\[]*\])", raw, flags=re.I)
    out: list[tuple[str, int, str]] = []
    for part in raw_parts:
        cleaned = clean_wiki_text(part).strip()
        if not cleaned or cleaned.lower() in ("none", "-", "n/a", "—", "various"):
            continue
        if re.fullmatch(r"\d+", cleaned):
            continue
        qty = 1
        m_pre = re.match(r"^(\d+)\s*[x×]\s*(.+)$", cleaned, flags=re.I)
        m_suf = re.search(r"\b[x×]\s*(\d+)\b", cleaned, flags=re.I)
        if m_pre:
            qty = int(m_pre.group(1))
        elif m_suf:
            qty = int(m_suf.group(1))

        # Special researcher exchange notes like "SPR Mako Stone give to researcher and receive Esuna Materia"
        m_recv = re.search(r"\breceive\s+(.+)$", cleaned, flags=re.I)
        if m_recv:
            cname = canonical_item_name(m_recv.group(1))
        else:
            cname = canonical_item_name(cleaned)

        if not cname or re.fullmatch(r"\d+", cname) or cname.lower() in ("none", "various"):
            continue
        out.append((cname, qty, cleaned))
    return out


def parse_loot_field(raw: str) -> list[str]:
    """Parses an enemy steal/drop infobox value cleanly into 0..2 canonical item names."""
    if not raw:
        return []
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    raw = raw.split("|")[0]
    parts = re.split(r"<br\s*/?>|\n|;|/|,\s+", raw, flags=re.I)
    names: list[str] = []
    for part in parts:
        sub_links = re.findall(r"\[\[[^\]]+\]\]", part)
        candidates = sub_links if len(sub_links) >= 2 else [part]
        for cand in candidates:
            cleaned = clean_wiki_text(cand).strip()
            if not cleaned:
                continue
            cleaned = re.sub(r"\([^)]*\)", "", cleaned).strip()
            cleaned = re.sub(r"\bdrop rate\b.*$", "", cleaned, flags=re.I).strip()
            cleaned = re.sub(r"\bif the player\b.*$", "", cleaned, flags=re.I).strip()
            cleaned = re.sub(r"\bduring\b.*$", "", cleaned, flags=re.I).strip()
            cleaned = re.sub(r"\s+\bneed\b.*$", "", cleaned, flags=re.I).strip()
            cname = canonical_item_name(cleaned)
            if not cname:
                continue
            low = cname.lower()
            if low in ("none", "various", "n/a", "-", "—", "the faq had none", "faq had none", "unknown", "tbd") or re.fullmatch(r"\d+", low):
                continue
            if cname not in names:
                names.append(cname)
    return names[:2]


HEADER_CELL_NAMES = {
    "name", "cost", "mission", "description", "unlock", "rank", "treasures",
    "finish reward", "main effects", "fusion effects", "type", "effect",
    "acquire", "mp cost",
}


def parse_wikitable_rows(wikitext: str) -> list[list[str]]:
    rows: list[list[str]] = []
    in_table = False
    cur_row: list[str] = []
    for line in wikitext.splitlines():
        st = line.strip()
        if st.startswith("{|"):
            in_table = True
            cur_row = []
            continue
        if st.startswith("|}"):
            if cur_row:
                rows.append(cur_row)
            in_table = False
            cur_row = []
            continue
        if not in_table:
            continue
        if st.startswith("|-"):
            if cur_row:
                rows.append(cur_row)
            cur_row = []
            continue
        if st.startswith("|+"):
            continue
        if st.startswith("!"):
            cell = st.lstrip("!").strip()
            if not cell or cell.lower().startswith(("style=", "class=", "scope=")):
                continue
            if clean_wiki_text(cell).lower() in HEADER_CELL_NAMES:
                continue
            cur_row.append(cell)
            continue
        if st.startswith("|"):
            body = st[1:]
            if "||" in body:
                for part in body.split("||"):
                    cur_row.append(part.strip())
            else:
                if "|" in body and not body.strip().startswith("[[") and not body.strip().startswith("{{") and "style=" in body.split("|", 1)[0]:
                    body = body.split("|", 1)[1]
                cur_row.append(body.strip())
    if cur_row:
        rows.append(cur_row)
    return rows


def infer_chapter_from_unlock(unlock: str, branch: str, sub_num: int) -> int:
    m = re.search(r"Chapter\s*(\d+)", unlock, flags=re.I)
    if m:
        return max(1, min(10, int(m.group(1))))
    branch_num = int(branch[1:])
    if branch_num == 1:
        return 1 if sub_num <= 1 else min(9, 2 + sub_num)
    if branch_num in (2, 3, 4, 5, 6, 7, 8):
        return min(10, 3 + sub_num)
    if branch_num == 9:
        return min(10, 6 + (sub_num + 1) // 2)
    return min(10, 5 + sub_num)


def compute_hard_benchmarks(stars: int, mission_id: str) -> dict[str, Any]:
    presets = {
        1: (5, 1200, 15, 15, "Basic warm-up; Barrier + Battle Stance easily handles groups."),
        2: (10, 2200, 25, 25, "Keep Barrier up and practice Perfect Guards in Battle Stance."),
        3: (15, 3600, 40, 40, "Stack HP% via Potions after unlocking Item Fusion in Ch. 4 (M7-2-1)."),
        4: (22, 5500, 60, 60, "Equip 4 Accessory slots (M7-2-2 & M7-2-5) and Element/Status Ward."),
        5: (30, 8500, 85, 85, "Use Wall/Barrier and Darkness or High Jump; raise Buster Sword to 23%+."),
        6: (38, 13000, 110, 110, "Equip Adaman Bangle (M7-3-6) for Break HP Limit and Mog's Amulet for rare drops."),
        7: (46, 20000, 145, 145, "Unlock Costly Punch + Brutal (M7-4-6) and deplete boss Skill Power gauges."),
        8: (56, 35000, 185, 185, "Pair Status Ward + Hell Blizzaga/Firaga to neutralize instant-death mobs."),
        9: (68, 60000, 225, 225, "Push VIT/SPR to 220+ and HP 50k+ using 98/980% Libra conversion."),
        10: (80, 95000, 255, 255, "Endgame Hard Mode: max VIT/SPR 255, 99,999 HP & Genji equipment."),
    }
    lvl, hp, vit, spr, notes = presets.get(stars, presets[5])
    if mission_id == "M9-6-6":
        return {
            "recommendedLevel": 85,
            "hp": 99999,
            "vit": 255,
            "spr": 255,
            "notes": "Superboss Minerva (20,000,000 HP on Hard Mode): 255 VIT/SPR, 99,999 HP, Wall, Costly Punch, Aerial Drain, Mug (steal 99 Phoenix Downs), Genji set.",
        }
    return {
        "recommendedLevel": lvl,
        "hp": hp,
        "vit": vit,
        "spr": spr,
        "notes": notes,
    }


def parse_all_missions(mission_pages: dict[str, str]) -> list[dict[str, Any]]:
    missions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for branch, page_title, branch_name in BRANCH_TITLES:
        text = mission_pages.get(page_title, "")
        if not text:
            raise RuntimeError(f"Missing wikitext for {page_title}")

        if branch == "M1":
            cur_sub = "M1-1: Training Missions"
            sections = re.split(r"(^==[^=].*?==\s*$)", text, flags=re.M)
            for sec in sections:
                sec_s = sec.strip()
                if sec_s.startswith("==") and not sec_s.startswith("==="):
                    cur_sub = clean_wiki_text(sec_s.strip("="))
                    continue
                for row in parse_wikitable_rows(sec):
                    if len(row) < 6:
                        continue
                    head = clean_wiki_text(row[0])
                    m = re.match(r"^(M\d+-\d+-\d+)\s*[:\-]\s*(.+)$", head)
                    if not m:
                        continue
                    mid, title = m.group(1), m.group(2).strip()
                    if mid in seen_ids:
                        continue
                    seen_ids.add(mid)
                    desc = clean_wiki_text(row[1])
                    unlock = clean_wiki_text(row[2])
                    rank_str = clean_wiki_text(row[3])
                    stars = int(re.search(r"\d+", rank_str).group(0)) if re.search(r"\d+", rank_str) else 5
                    stars = max(1, min(10, stars))

                    treasures = [
                        {"itemId": f"item_{slugify(iname)}", "quantity": qty, "rawLabel": rlabel}
                        for iname, qty, rlabel in parse_item_qty_entries(row[4])
                    ]
                    reward_entries = parse_item_qty_entries(row[5])
                    clear_reward = None
                    if reward_entries:
                        rname, rqty, rlabel = reward_entries[0]
                        clear_reward = {"itemId": f"item_{slugify(rname)}", "quantity": rqty, "rawLabel": rlabel}
                        # If multiple items in reward (e.g. "Fat Chocobo Feather x2, Sector 8 - Materia Shop item"),
                        # add secondary unlock to treasures so both remain clickable!
                        for extra_name, extra_qty, extra_label in reward_entries[1:]:
                            treasures.append({"itemId": f"item_{slugify(extra_name)}", "quantity": extra_qty, "rawLabel": extra_label})

                    sub_num = int(mid.split("-")[1])
                    missions.append(
                        {
                            "id": mid,
                            "branch": branch,
                            "branchName": branch_name,
                            "subGroup": cur_sub,
                            "title": title,
                            "description": desc,
                            "stars": stars,
                            "chapterAvailable": infer_chapter_from_unlock(unlock, branch, sub_num),
                            "unlockCondition": unlock,
                            "hardModeBenchmarks": compute_hard_benchmarks(stars, mid),
                            "clearReward": clear_reward,
                            "treasures": treasures,
                            "bossEnemyIds": [],
                            "randomEnemyIds": [],
                            "_rawEnemies": [],
                        }
                    )
        else:
            cur_sub = f"{branch}-1"
            tokens = re.split(r"(^===?[^=].*?===?\s*$)", text, flags=re.M)
            i = 0
            while i < len(tokens):
                tok = tokens[i].strip()
                if tok.startswith("==") and not tok.startswith("==="):
                    cur_sub = clean_wiki_text(tok.strip("="))
                    i += 1
                    continue
                if tok.startswith("==="):
                    heading = clean_wiki_text(tok.strip("="))
                    body = tokens[i + 1] if i + 1 < len(tokens) else ""
                    i += 2
                    m = re.match(r"^(M\d+-\d+-\d+)\s*[:\-]\s*(.+)$", heading)
                    if not m:
                        continue
                    mid, title = m.group(1), m.group(2).strip()
                    if mid in seen_ids:
                        continue
                    seen_ids.add(mid)

                    desc_lines = []
                    for line in body.splitlines():
                        if line.strip().startswith("*"):
                            break
                        c = clean_wiki_text(line)
                        if c:
                            desc_lines.append(c)
                    desc = " ".join(desc_lines)

                    def _extract_bullet(label: str) -> str:
                        pat = rf"\*\s*'''\s*{label}\s*:?\s*'''\s*:?\s*(.+)"
                        mm = re.search(pat, body, flags=re.I)
                        return mm.group(1).strip() if mm else ""

                    unlock = clean_wiki_text(_extract_bullet("Unlock"))
                    enemies_raw = _extract_bullet("Enemies")
                    chests_raw = _extract_bullet("Chests")
                    reward_raw = _extract_bullet("Finish reward")

                    raw_enemies = []
                    if enemies_raw and clean_wiki_text(enemies_raw).lower() != "none":
                        for part in re.split(r",(?![^\[]*\])", enemies_raw):
                            ename = clean_wiki_text(part).strip(" .")
                            if ename:
                                raw_enemies.append(ename)

                    treasures = [
                        {"itemId": f"item_{slugify(iname)}", "quantity": qty, "rawLabel": rlabel}
                        for iname, qty, rlabel in parse_item_qty_entries(chests_raw)
                    ]
                    reward_entries = parse_item_qty_entries(reward_raw)
                    clear_reward = None
                    if reward_entries:
                        rname, rqty, rlabel = reward_entries[0]
                        clear_reward = {"itemId": f"item_{slugify(rname)}", "quantity": rqty, "rawLabel": rlabel}
                        for extra_name, extra_qty, extra_label in reward_entries[1:]:
                            treasures.append({"itemId": f"item_{slugify(extra_name)}", "quantity": extra_qty, "rawLabel": extra_label})

                    sub_num = int(mid.split("-")[1])
                    branch_num = int(branch[1:])
                    if branch_num == 9:
                        est_stars = min(10, 5 + sub_num)
                    elif branch_num == 10:
                        est_stars = min(10, 2 + sub_num * 2)
                    else:
                        est_stars = max(1, min(10, sub_num + (branch_num // 3)))
                    if mid == "M9-6-6":
                        est_stars = 10

                    missions.append(
                        {
                            "id": mid,
                            "branch": branch,
                            "branchName": branch_name,
                            "subGroup": cur_sub,
                            "title": title,
                            "description": desc,
                            "stars": est_stars,
                            "chapterAvailable": infer_chapter_from_unlock(unlock, branch, sub_num),
                            "unlockCondition": unlock,
                            "hardModeBenchmarks": compute_hard_benchmarks(est_stars, mid),
                            "clearReward": clear_reward,
                            "treasures": treasures,
                            "bossEnemyIds": [],
                            "randomEnemyIds": [],
                            "_rawEnemies": raw_enemies,
                        }
                    )
                else:
                    i += 1

    missions.sort(key=lambda m: tuple(int(p) for p in m["id"][1:].split("-")))
    return missions


def parse_infobox_fields(wikitext: str, tpl_name: str) -> dict[str, str]:
    idx = wikitext.lower().find("{{" + tpl_name.lower())
    if idx == -1:
        return {}
    depth = 0
    end = idx
    for pos in range(idx, len(wikitext) - 1):
        two = wikitext[pos : pos + 2]
        if two == "{{":
            depth += 1
        elif two == "}}":
            depth -= 1
            if depth == 0:
                end = pos
                break
    block = wikitext[idx + 2 : end]
    fields: dict[str, str] = {}
    cur_key = None
    cur_val: list[str] = []
    for line in block.splitlines()[1:]:
        if line.strip().startswith("|") and "=" in line:
            if cur_key is not None:
                fields[cur_key] = "\n".join(cur_val).strip()
            k, v = line.split("=", 1)
            cur_key = k.lstrip("| ").strip().lower()
            cur_val = [v.strip()]
        elif cur_key is not None:
            cur_val.append(line)
    if cur_key is not None:
        fields[cur_key] = "\n".join(cur_val).strip()

    # Normalize multi-phase boss keys ("1 hp", "1 location", "2 location", etc.)
    # Prefer Mission phase ("2 ..." if sec 2 = Mission) else "1 ..."
    mission_phase = None
    for phase in ("2", "3", "1"):
        sec_val = fields.get(f"sec {phase}", "").lower()
        loc_val = fields.get(f"{phase} location", "")
        if "mission" in sec_val or re.search(r"M\d+-\d+-\d+", loc_val):
            mission_phase = phase
            break
    if not mission_phase:
        mission_phase = "1"

    for k, v in list(fields.items()):
        m_ph = re.match(r"^(\d+)\s+(.+)$", k)
        if m_ph:
            ph, base_k = m_ph.group(1), m_ph.group(2)
            if ph == mission_phase or base_k not in fields:
                fields[base_k] = v

    # Aggregate ALL location fields across phases
    all_locs = [fields.get("location", "")]
    for phase in ("1", "2", "3", "4"):
        if f"{phase} location" in fields:
            all_locs.append(fields[f"{phase} location"])
    fields["_all_locations"] = "\n".join(x for x in all_locs if x)
    return fields


def parse_int_stat(raw: str) -> int | None:
    if not raw:
        return None
    cleaned = clean_wiki_text(raw).replace(",", "")
    m = re.search(r"-?\d+", cleaned)
    return int(m.group(0)) if m else None


def classify_enemy_family(name: str, wikitext: str, is_boss: bool) -> str:
    low = (name + " " + wikitext[:500]).lower()
    if is_boss or "minerva" in low or "bahamut" in low or "sephiroth" in low or ("genesis" in low and "boss" in low):
        return "Boss"
    if name.startswith("G ") or "genesis copy" in low:
        return "Genesis Copy"
    if name.startswith("A-") or "angeal copy" in low:
        return "Angeal Copy"
    if "shinra" in low or "trooper" in low or "captain" in low or "soldier" in low:
        return "Shinra"
    if "wutai" in low or "crescent unit" in low:
        return "Wutai"
    if any(k in low for k in ("gun", "machine", "turret", "sweeper", "guard", "mech", "mover", "saucer", "motor", "scorpion", "dagger", "spider")):
        return "Machine"
    if any(k in low for k in ("wolf", "hound", "worm", "sahagin", "bomb", "malboro", "behemoth", "chitin", "griffon", "dragon")):
        return "Beast"
    return "Fiend"


def parse_enemies(
    enemy_pages: dict[str, str],
    boss_names: set[str],
    boss_page_titles: set[str],
    valid_mission_ids: set[str],
    gallery_image_map: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
    enemies: list[dict[str, Any]] = []
    name_to_id: dict[str, str] = {}
    image_files: list[str] = []
    gallery_image_map = gallery_image_map or {}

    for page_title, text in sorted(enemy_pages.items()):
        stats_fields = parse_infobox_fields(text, "infobox enemy stats VIICC")
        if not stats_fields:
            stats_fields = parse_infobox_fields(text, "infobox enemy stats")
        if not stats_fields:
            continue

        info_fields = parse_infobox_fields(text, "infobox enemy")
        name = clean_wiki_text(stats_fields.get("name") or info_fields.get("name") or page_title)
        name = re.sub(r"\s*\((?:Crisis Core|boss|Crisis Core boss)\)\s*", "", name, flags=re.I).strip()
        if not name or name.lower().startswith("auto-regen"):
            continue

        eid = f"enemy_{slugify(name)}"
        if any(e["id"] == eid for e in enemies):
            eid = f"enemy_{slugify(page_title)}"

        image_file = clean_wiki_text(info_fields.get("image") or stats_fields.get("image") or "")
        if not image_file:
            image_file = gallery_image_map.get(name.lower(), "")
        if not image_file:
            m_file = re.search(r"\[\[(?:File|Image):([^|\]]+\.(?:png|jpe?g|webp|gif))", text, flags=re.I)
            if m_file:
                image_file = m_file.group(1).strip()
        if image_file:
            image_files.append(image_file)

        loc_text = stats_fields.get("_all_locations", "") + "\n" + info_fields.get("_all_locations", "")
        mission_codes = []
        for mc in re.findall(r"M\d+-\d+-\d+", loc_text):
            if mc in valid_mission_ids and mc not in mission_codes:
                mission_codes.append(mc)

        story_locations: list[str] = []
        for raw_line in re.split(r"[\n;]|<br\s*/?>", loc_text, flags=re.I):
            cl = clean_wiki_text(raw_line).strip(" .,-")
            if not cl or re.search(r"M\d+-\d+-\d+", cl):
                continue
            if cl.lower() in ("missions", "mission", "none", "n/a", "-", "—"):
                continue
            if cl not in story_locations:
                story_locations.append(cl)

        is_boss_global = (
            page_title in boss_page_titles
            or name.lower() in boss_names
            or "boss" in page_title.lower()
            or "superboss" in text[:400].lower()
            or "summon" in text[:400].lower()
        )
        family = classify_enemy_family(name, text, is_boss_global)

        weak = [clean_wiki_text(x).strip() for x in re.split(r",|<br\s*/?>", stats_fields.get("weak", "")) if clean_wiki_text(x).strip()]
        resist = [clean_wiki_text(x).strip() for x in re.split(r",|<br\s*/?>", stats_fields.get("halves", "") or stats_fields.get("resist", "")) if clean_wiki_text(x).strip()]
        nulls = [clean_wiki_text(x).strip() for x in re.split(r",|<br\s*/?>", stats_fields.get("null", "") or stats_fields.get("nullifies", "")) if clean_wiki_text(x).strip()]
        absorb = [clean_wiki_text(x).strip() for x in re.split(r",|<br\s*/?>", stats_fields.get("absorb", "")) if clean_wiki_text(x).strip()]
        immune = []
        for elem in ("fire", "ice", "lightning", "water", "wind", "earth", "holy", "dark", "gravity"):
            ev = clean_wiki_text(stats_fields.get(elem, "")).lower()
            if not ev:
                continue
            elabel = elem.title()
            if "weak" in ev and elabel not in weak:
                weak.append(elabel)
            elif ("halv" in ev or "resist" in ev) and elabel not in resist:
                resist.append(elabel)
            elif ("null" in ev or "void" in ev or ev == "0") and elabel not in nulls:
                nulls.append(elabel)
            elif "absorb" in ev and elabel not in absorb:
                absorb.append(elabel)
            elif "immune" in ev and elabel not in immune:
                immune.append(elabel)
        for status_k in ("poison", "silence", "stun", "stop", "death", "blow away"):
            val = clean_wiki_text(stats_fields.get(status_k, ""))
            if val.lower() == "immune":
                immune.append(status_k.title())

        def _parse_bool_flag(raw_v: str) -> bool:
            return clean_wiki_text(raw_v).lower() in ("true", "yes", "1", "y")

        def _parse_float_stat(raw_v: str) -> float | None:
            cv = clean_wiki_text(raw_v).replace(",", "")
            mm = re.search(r"-?\d+(?:\.\d+)?", cv)
            return float(mm.group(0)) if mm else None

        combat_flags = {
            "nullPhysical": _parse_bool_flag(stats_fields.get("nullphysical", "") or stats_fields.get("null physical", "")),
            "nullMagic": _parse_bool_flag(stats_fields.get("nullmagic", "") or stats_fields.get("nullmagical", "") or stats_fields.get("null magic", "")),
            "interruptible": _parse_bool_flag(stats_fields.get("interruptible", "")),
            "stagger": _parse_float_stat(stats_fields.get("stagger", "")),
            "recovery": _parse_float_stat(stats_fields.get("recovery", "")),
        }

        story_chapter = STORY_ENEMY_CHAPTERS.get(eid)
        if not story_chapter and story_locations:
            loc_low = " ".join(story_locations).lower()
            if "prologue" in loc_low or "tamblin" in loc_low or "wutai" in loc_low:
                story_chapter = 1
            elif "banora village" in loc_low or "banora" in loc_low and "underground" not in loc_low:
                story_chapter = 2
            elif "sector 5" in loc_low or "slums" in loc_low:
                story_chapter = 4
            elif "modeo" in loc_low or "excavation" in loc_low:
                story_chapter = 5
            elif "junon" in loc_low or "costa" in loc_low:
                story_chapter = 6
            elif "nibel" in loc_low or "manor" in loc_low:
                story_chapter = 8
            elif "gongaga" in loc_low:
                story_chapter = 9
            elif "underground" in loc_low or "judgment" in loc_low or "caged" in loc_low or "lake" in loc_low:
                story_chapter = 10

        abilities = [
            clean_wiki_text(a).strip()
            for a in re.split(r",|<br\s*/?>", stats_fields.get("abilities", ""))
            if clean_wiki_text(a).strip()
        ]

        drop_list = parse_loot_field(stats_fields.get("drop", ""))
        rare_drop_list = parse_loot_field(stats_fields.get("rare drop", ""))
        steal_list = parse_loot_field(stats_fields.get("steal", ""))
        rare_steal_list = parse_loot_field(stats_fields.get("rare steal", ""))

        common_drop = f"item_{slugify(drop_list[0])}" if drop_list else None
        rare_drop = f"item_{slugify(rare_drop_list[0])}" if rare_drop_list else (f"item_{slugify(drop_list[1])}" if len(drop_list) > 1 else None)
        common_steal = f"item_{slugify(steal_list[0])}" if steal_list else None
        rare_steal = f"item_{slugify(rare_steal_list[0])}" if rare_steal_list else (f"item_{slugify(steal_list[1])}" if len(steal_list) > 1 else None)

        loot = {
            "commonDrop": common_drop,
            "rareDrop": rare_drop,
            "commonSteal": common_steal,
            "rareSteal": rare_steal,
            "dropRate": clean_wiki_text(stats_fields.get("drop rate", "")) or "—",
        }

        spawns = [
            {"missionId": mid, "role": "boss" if is_boss_global else "random"}
            for mid in mission_codes
        ]

        family_slug = slugify(family).replace("_", "-")
        enemy_obj = {
            "id": eid,
            "name": name,
            "family": family,
            "isBoss": is_boss_global,
            "portrait": {
                "imageFile": image_file,
                "imageUrl": "",
                "localPath": None,
                "fallbackSvg": f"games/crisis-core-reunion/assets/portraits/family-{family_slug}.svg",
            },
            "stats": {
                "level": parse_int_stat(stats_fields.get("level", "")),
                "hpNormal": parse_int_stat(stats_fields.get("hp", "")),
                "hpHard": parse_int_stat(stats_fields.get("hp hard", "")) or parse_int_stat(stats_fields.get("hp", "")),
                "mp": parse_int_stat(stats_fields.get("mp", "")),
                "atk": parse_int_stat(stats_fields.get("atk", "")),
                "vit": parse_int_stat(stats_fields.get("vit", "")),
                "mag": parse_int_stat(stats_fields.get("mag", "")),
                "spr": parse_int_stat(stats_fields.get("spr", "")),
                "lck": parse_int_stat(stats_fields.get("lck", "")),
                "exp": parse_int_stat(stats_fields.get("exp", "")),
                "sp": parse_int_stat(stats_fields.get("sp", "") or stats_fields.get("sp awarded", "")),
                "gil": parse_int_stat(stats_fields.get("gil", "")),
            },
            "affinities": {
                "weak": weak,
                "resist": resist,
                "null": nulls,
                "absorb": absorb,
                "immune": immune,
            },
            "combatFlags": combat_flags,
            "storyLocations": story_locations,
            "storyChapter": story_chapter,
            "abilities": abilities,
            "loot": loot,
            "spawns": spawns,
        }
        enemies.append(enemy_obj)
        name_to_id[name.lower()] = eid
        name_to_id[re.sub(r"\s*\(.*?\)", "", page_title).strip().lower()] = eid

    enemies.sort(key=lambda e: e["name"].lower())
    return enemies, name_to_id, image_files


def parse_shops_data(shop_txt: str) -> list[dict[str, Any]]:
    shop_meta = {
        "shinra shop": ("Unlocked automatically at the start of Chapter 1.", None, 1, False),
        "sector 8 materia shop": ("Complete Mission M6-2-1 (talk to City Planning Director in Shinra Entrance).", "M6-2-1", 4, False),
        "sector 5 materia shop": ("Complete Mission M6-2-3 (Mako Excavation Site).", "M6-2-3", 4, False),
        "sector 6 accessory shop": ("Complete Mission M6-2-6 (Underground City).", "M6-2-6", 5, False),
        "sector 7 shop": ("Found in a treasure chest during Mission M4-4-3 (Infiltration).", "M4-4-3", 6, False),
        "research dept. qmc": ("Story unlock: awarded automatically after defeating G Eraser in Chapter 3/4.", None, 4, False),
        "research dept. qmc+": ("Found in a hidden chest in Gongaga Outskirts in Chapter 9/10 — PERMANENTLY MISSABLE!", None, 9, True),
        "the happy turtle": ("Found in a treasure chest during Mission M4-3-6 (Stop the Assailants).", "M4-3-6", 5, False),
        "wutai secret shop": ("Complete Mission M4-2-6 (The Five Saints of Wutai).", "M4-2-6", 5, False),
        "gongaga trading": ("Complete Mission M2-3-1 (Unidentified Monsters).", "M2-3-1", 5, False),
        "nibel accessories": ("Found in a treasure chest during Mission M6-4-4 (Mad Scientist?).", "M6-4-4", 6, False),
        "junon souvenirs": ("Found in a treasure chest during Mission M2-4-1 (A Solitary Island).", "M2-4-1", 6, False),
        "bone village outlet": ("Found in a treasure chest during Mission M7-5-3 (Girl on the Cliff).", "M7-5-3", 7, False),
        "mythril mine trading": ("Complete Mission M2-4-5 (Cave-In Investigation).", "M2-4-5", 6, False),
        "online shop duo": ("Found in a treasure chest during Mission M9-3-3 (Genesis's Ambition).", "M9-3-3", 7, False),
        "online shop shade": ("Found in a treasure chest during Mission M9-5-4 (Abnormal Power) — sells Genji Helm for 1M Gil.", "M9-5-4", 8, False),
    }

    shops: list[dict[str, Any]] = []
    shop_sections = re.split(r"(^====[^=].*?====\s*$)", shop_txt, flags=re.M)
    cur_raw_head = ""
    for sec in shop_sections:
        st = sec.strip()
        if st.startswith("===="):
            cur_raw_head = st.strip("=")
            continue
        if not cur_raw_head:
            continue
        # Handle "Net Shop Shade|Online Shop Shade" or "[[Sector 5|Sec.5]] Materia Shop"
        clean_head = clean_wiki_text(cur_raw_head.split("|")[-1] if "[[" not in cur_raw_head and "|" in cur_raw_head else cur_raw_head)
        clean_head = re.sub(r"\bSec\.?\s*(\d+)\b", r"Sector \1", clean_head)
        clean_head = clean_head.replace("Nibel Accessories", "Nibel Accessories")
        meta = shop_meta.get(clean_head.lower())
        if not meta:
            # Try matching key
            for k, v in shop_meta.items():
                if k in clean_head.lower():
                    meta = v
                    break
        unlock_cond, unlock_mid, ch_avail, missable = meta if meta else ("Unlock via story/mission progression.", None, 5, False)
        quote_m = re.search(r"\{\{Quote\|([^}|]+)", sec, flags=re.I)
        quote = clean_wiki_text(quote_m.group(1)) if quote_m else ""

        stock: list[dict[str, Any]] = []
        for row in parse_wikitable_rows(sec):
            if len(row) < 2:
                continue
            iname = canonical_item_name(row[0])
            if not iname or iname.lower() == "name":
                continue
            price_m = re.search(r"[\d,]+", clean_wiki_text(row[1]))
            price = int(price_m.group(0).replace(",", "")) if price_m else 0
            stock.append({"itemId": f"item_{slugify(iname)}", "price": price})

        if stock:
            shops.append(
                {
                    "id": f"shop_{slugify(clean_head)}",
                    "name": clean_head,
                    "quote": quote,
                    "unlockCondition": unlock_cond,
                    "unlockMissionId": unlock_mid,
                    "chapterAvailable": ch_avail,
                    "missable": missable,
                    "stock": stock,
                }
            )
    return shops


def parse_items_and_shops(pages: dict[str, str]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    items: dict[str, dict[str, Any]] = {}

    def ensure_item(name: str, category: str, sub_category: str = "", description: str = "", fusion: dict[str, Any] | None = None) -> dict[str, Any]:
        cname = canonical_item_name(name)
        iid = f"item_{slugify(cname)}"
        if iid not in items:
            items[iid] = {
                "id": iid,
                "name": cname,
                "category": category,
                "subCategory": sub_category,
                "description": description,
                "fusion": fusion,
                "shops": [],
                "clearRewardMissions": [],
                "treasureMissions": [],
            }
        else:
            if description and not items[iid]["description"]:
                items[iid]["description"] = description
            if fusion and not items[iid]["fusion"]:
                items[iid]["fusion"] = fusion
            if sub_category and not items[iid]["subCategory"]:
                items[iid]["subCategory"] = sub_category
            if category != "key-items" and items[iid]["category"] == "key-items":
                items[iid]["category"] = category
        return items[iid]

    items_txt = pages.get("Crisis Core -Final Fantasy VII- items", "")
    sections = re.split(r"(^===?[^=].*?===?\s*$)", items_txt, flags=re.M)
    cur_sec = "consumables"
    for sec in sections:
        st = sec.strip()
        if st.startswith("=="):
            h = clean_wiki_text(st.strip("=")).lower()
            if "mako" in h:
                cur_sec = "mako-stones"
            elif "stat" in h or "stone" in h:
                cur_sec = "stat-stones"
            elif "fusion" in h or "parameter" in h:
                cur_sec = "max-tier-fusion"
            elif "recovery" in h or "attack" in h or "disposable" in h:
                cur_sec = "consumables"
            else:
                cur_sec = "key-items"
            continue
        for row in parse_wikitable_rows(sec):
            if len(row) < 2:
                continue
            name = canonical_item_name(row[0])
            if not name or name.lower() in ("name", "item"):
                continue
            desc = clean_wiki_text(row[1])
            fusion_raw = clean_wiki_text(row[2]) if len(row) >= 3 else ""
            cat = cur_sec
            low_n = name.lower()
            if low_n in ("hero drink", "adamantite", "dark matter", "mythril", "gysahl greens", "fat chocobo feather", "lunar harp", "zeio nut"):
                cat = "max-tier-fusion"
            elif "mako stone" in low_n:
                cat = "mako-stones"
            elif low_n.endswith("stone") and any(k in low_n for k in ("hp", "mp", "ap", "power", "guard", "magic", "mind", "luck")):
                cat = "stat-stones"
            ensure_item(name, cat, cur_sec, desc, parse_fusion_note(name, fusion_raw))

    acc_txt = pages.get("Crisis Core -Final Fantasy VII- accessories", "")
    for row in parse_wikitable_rows(acc_txt):
        if len(row) < 2:
            continue
        name = canonical_item_name(row[0])
        if not name or name.lower() == "name":
            continue
        desc = clean_wiki_text(row[1])
        fusion_raw = clean_wiki_text(row[2]) if len(row) >= 3 else ""
        ensure_item(name, "accessories", "Accessory", desc, parse_fusion_note(name, fusion_raw))

    materia_pages = [
        ("Command materia (Crisis Core)", "Command"),
        ("Magic materia (Crisis Core)", "Magic"),
        ("Support materia (Crisis Core)", "Support"),
        ("Special materia", "Independent"),
    ]
    materia_table_meta: dict[str, dict[str, Any]] = {}
    for ptitle, subcat in materia_pages:
        mtxt = pages.get(ptitle, "")
        for row in parse_wikitable_rows(mtxt):
            if len(row) < 3:
                continue
            name = canonical_item_name(row[0])
            if not name or name.lower() in ("name", "materia"):
                continue
            desc = clean_wiki_text(row[2])
            it = ensure_item(name, "materia", subcat, desc, None)
            cost_val = None
            cost_type = "None"
            grade_val = None
            if subcat in ("Command", "Magic") and len(row) >= 6:
                cost_val = parse_int_stat(row[4])
                cost_type = "AP" if subcat == "Command" else "MP"
                grade_val = parse_int_stat(row[5])
            elif len(row) >= 5:
                grade_val = parse_int_stat(row[4])
            if grade_val is not None:
                grade_val = max(1, min(8, grade_val))
            materia_table_meta[it["id"]] = {
                "cost": cost_val,
                "costType": cost_type,
                "grade": grade_val,
            }

    curated_fusion = [
        ("Potion", "consumables", "Restores a small amount of HP.", "HP%", 10, 20, 999, True, "Only amplifies an EXISTING HP% stat on one of the two Materia."),
        ("Hi-Potion", "consumables", "Restores a moderate amount of HP.", "HP%", 10, 10, 999, True, "Only amplifies an EXISTING HP% stat."),
        ("X-Potion", "consumables", "Restores a large amount of HP (up to 99,999 in Reunion).", "HP%", 10, 5, 999, True, "Only amplifies an EXISTING HP% stat."),
        ("Ether", "consumables", "Restores MP.", "MP%", 10, 10, 999, True, "Only amplifies an EXISTING MP% stat."),
        ("Soma", "consumables", "Restores AP.", "AP%", 10, 10, 999, True, "Only amplifies an EXISTING AP% stat."),
        ("Elixir", "max-tier-fusion", "Fully restores HP, MP, and AP and removes status ailments.", "HP%", 10, 1, 999, True, "Amplifies existing HP% (+10% per Elixir)."),
        ("Phoenix Down", "max-tier-fusion", "Grants Auto-Raise status in battle.", "SPR", 1, 1, 100, False, "Adds SPR +1 per Phoenix Down (max +100)."),
        ("HP Mako Stone", "mako-stones", "Mako stone infused with vitality.", "HP%", 10, 5, 400, False, "5 stones = HP +10% (caps at +400%)."),
        ("MP Mako Stone", "mako-stones", "Mako stone infused with spirit energy.", "MP%", 10, 5, 400, False, "5 stones = MP +10% (caps at +400%)."),
        ("AP Mako Stone", "mako-stones", "Mako stone infused with combat energy.", "AP%", 10, 5, 400, False, "5 stones = AP +10% (caps at +400%)."),
        ("ATK Mako Stone", "mako-stones", "Mako stone infused with strength.", "ATK", 1, 5, 40, False, "5 stones = ATK +1 (caps at +40)."),
        ("VIT Mako Stone", "mako-stones", "Mako stone infused with endurance.", "VIT", 1, 5, 40, False, "5 stones = VIT +1 (caps at +40)."),
        ("MAG Mako Stone", "mako-stones", "Mako stone infused with magic.", "MAG", 1, 5, 40, False, "5 stones = MAG +1 (caps at +40)."),
        ("SPR Mako Stone", "mako-stones", "Mako stone infused with spirit.", "SPR", 1, 5, 40, False, "5 stones = SPR +1 (caps at +40)."),
        ("LCK Mako Stone", "mako-stones", "Mako stone infused with fortune.", "LCK", 1, 5, 40, False, "5 stones = LCK +1 (caps at +40)."),
        ("HP Stone", "stat-stones", "Condensed HP fusion catalyst.", "HP%", 10, 3, 660, False, "3 stones = HP +10% (caps at +660%)."),
        ("MP Stone", "stat-stones", "Condensed MP fusion catalyst.", "MP%", 10, 3, 660, False, "3 stones = MP +10% (caps at +660%)."),
        ("AP Stone", "stat-stones", "Condensed AP fusion catalyst.", "AP%", 10, 3, 660, False, "3 stones = AP +10% (caps at +660%)."),
        ("Power Stone", "stat-stones", "Condensed ATK fusion catalyst.", "ATK", 1, 3, 66, False, "3 stones = ATK +1 (caps at +66)."),
        ("Guard Stone", "stat-stones", "Condensed VIT fusion catalyst.", "VIT", 1, 3, 66, False, "3 stones = VIT +1 (caps at +66)."),
        ("Magic Stone", "stat-stones", "Condensed MAG fusion catalyst.", "MAG", 1, 3, 66, False, "3 stones = MAG +1 (caps at +66)."),
        ("Mind Stone", "stat-stones", "Condensed SPR fusion catalyst.", "SPR", 1, 3, 66, False, "3 stones = SPR +1 (caps at +66)."),
        ("Luck Stone", "stat-stones", "Condensed LCK fusion catalyst.", "LCK", 1, 3, 66, False, "3 stones = LCK +1 (caps at +66)."),
        ("Fat Chocobo Feather", "max-tier-fusion", "Max-tier HP fusion material.", "HP%", 10, 1, 999, False, "1 Feather = HP +10% (caps at +999%)."),
        ("Lunar Harp", "max-tier-fusion", "Max-tier MP fusion material.", "MP%", 10, 1, 999, False, "1 Harp = MP +10% (caps at +999%)."),
        ("Zeio Nut", "max-tier-fusion", "Max-tier AP fusion material.", "AP%", 10, 1, 999, False, "1 Nut = AP +10% (caps at +999%)."),
        ("Hero Drink", "max-tier-fusion", "Max-tier ATK fusion material.", "ATK", 1, 1, 100, False, "1 Hero Drink = ATK +1 (caps at +100)."),
        ("Adamantite", "max-tier-fusion", "Max-tier VIT fusion material.", "VIT", 1, 1, 100, False, "1 Adamantite = VIT +1 (caps at +100)."),
        ("Dark Matter", "max-tier-fusion", "Max-tier MAG fusion material.", "MAG", 1, 1, 100, False, "1 Dark Matter = MAG +1 (caps at +100)."),
        ("Mythril", "max-tier-fusion", "Max-tier SPR fusion material.", "SPR", 1, 1, 100, False, "1 Mythril = SPR +1 (caps at +100)."),
        ("Gysahl Greens", "max-tier-fusion", "Max-tier LCK fusion material.", "LCK", 1, 1, 100, False, "1 Gysahl Greens = LCK +1 (caps at +100)."),
    ]
    for cname, cat, desc, stat, per_u, step, cap, req_ex, notes in curated_fusion:
        item = ensure_item(cname, cat, cat, desc)
        item["category"] = cat
        item["fusion"] = {
            "stat": stat,
            "perUnit": per_u,
            "unitsPerStep": step,
            "maxBonus": cap,
            "requiresExistingStat": req_ex,
            "notes": notes,
        }

    # Ensure key DMW / Magic Pot / Reunion items exist with clean descriptions
    curated_extra = [
        ("Item Fusion Tome", "key-items", "Key Item", "Unlocks adding items to Materia Fusion (Clear M7-2-1)."),
        ("Keychain", "key-items", "Key Item", "Unlocks Accessory Slot 3 (Clear M7-2-2)."),
        ("Backpack", "key-items", "Key Item", "Unlocks Accessory Slot 4 (Clear M7-2-5)."),
        ("Cactus Thorn", "key-items", "Key Item", "Unlocks Cactuar DMW image (Clear M10-1-3)."),
        ("Tonberry's Knife", "key-items", "Key Item", "Unlocks Tonberry DMW image (Clear M10-2-3)."),
        ("Goddess Key", "key-items", "Key Item", "Rare key item carried by Behemoth King in the Depths of Judgment."),
        ("Mog's Amulet", "accessories", "Accessory", "Guarantees enemies drop their Rare Drop instead of Common Drop. Sold in Sector 7 Shop (M4-4-3)."),
        ("Brigand's Gloves", "accessories", "Accessory", "Always succeeds when using Steal or Mug. Sold in Sector 7 Shop (M4-4-3)."),
        ("Genji Helm", "accessories", "Accessory", "MP/AP Cost 0 and permanent Libra. Sold once in Online Shop Shade (M9-5-4) for 1,000,000 Gil."),
        ("Genji Armor", "accessories", "Accessory", "Break HP Limit (99,999), Endure, and Regen. Reward for 100% DMW completion."),
        ("Genji Shield", "accessories", "Accessory", "Permanent Barrier, MBarrier, Absorb all elements, and Status Immunity. Reward from Magic Pot in M7-6-6."),
        ("Genji Glove", "accessories", "Accessory", "Break Damage Limit (99,999) and Critical always. Found in chest in M9-6-4."),
        ("Divine Slayer", "accessories", "Accessory", "All stats +50, HP/MP/AP +100%, Break HP/Damage Limit, Absorb all elements. Reward from Minerva (M9-6-6)."),
        ("Heike Soul", "accessories", "Accessory", "Grants multiple powerful effects and doubles drops/Gil. Reward for 100% Mission completion (all 300)."),
        ("Exaflare", "materia", "DMW", "Bahamut Fury DMW Materia. Increases chance of rolling Bahamut Fury on the DMW."),
        ("Megaflare", "materia", "DMW", "Bahamut DMW Materia. Increases chance of rolling Bahamut on the DMW."),
        ("MBarrier", "materia", "Magic", "Applies Magic Barrier to halve incoming magical damage."),
        ("Iron Fist", "materia", "Command", "Unarmed punch attack that deals heavy damage."),
        ("Stop Blade", "materia", "Command", "Sword strike that inflicts Stop on enemies."),
        ("MAG Up++", "materia", "Independent", "Greatly raises Magic stat (+30 per level)."),
    ]
    for cname, cat, sub, desc in curated_extra:
        ensure_item(cname, cat, sub, desc)

    # Parse all 16 shops and sync stock into items
    shop_txt = pages.get("Shop (Crisis Core)", "")
    shops = parse_shops_data(shop_txt)
    for sh in shops:
        for entry in sh["stock"]:
            iid = entry["itemId"]
            raw_name = iid.replace("item_", "").replace("_plus_plus", "++").replace("_plus", "+").replace("_", " ").title()
            it = items.get(iid) or ensure_item(raw_name, "consumables", "Shop Stock", "")
            entry["itemId"] = it["id"]
            if not any(s["shopName"] == sh["name"] for s in it["shops"]):
                it["shops"].append({"shopName": sh["name"], "price": entry["price"], "unlockHint": sh["unlockCondition"]})

    return items, shops, materia_table_meta


def parse_fusion_note(item_name: str, note: str) -> dict[str, Any] | None:
    if not note:
        return None
    m = re.search(r"(\d+)\s*[x×]?\s*(?:per|→|->)?\s*(HP|MP|AP|ATK|VIT|MAG|SPR|LCK)\s*\+?(\d+)(%?)", note, flags=re.I)
    if not m:
        return None
    units = int(m.group(1))
    stat = m.group(2).upper() + ("%" if m.group(4) or m.group(2).upper() in ("HP", "MP", "AP") else "")
    per_unit = int(m.group(3))
    cap = 999 if "%" in stat else 100
    return {
        "stat": stat,
        "perUnit": per_unit,
        "unitsPerStep": units,
        "maxBonus": cap,
        "requiresExistingStat": item_name.lower() in ("potion", "hi-potion", "x-potion", "ether", "soma", "remedy", "elixir"),
        "notes": note,
    }


def reconcile_relations(
    missions: list[dict[str, Any]],
    enemies: list[dict[str, Any]],
    enemy_name_to_id: dict[str, str],
    items: dict[str, dict[str, Any]],
    shops: list[dict[str, Any]],
) -> None:
    enemy_by_id = {e["id"]: e for e in enemies}
    mission_by_id = {m["id"]: m for m in missions}

    # Explicit links for the 4 special missions where wiki table omits enemy names
    manual_mission_enemies = {
        "M1-4-2": [("enemy_red_scorpion", True)],
        "M5-1-2": [("enemy_bahamut", True)],
        "M5-1-4": [("enemy_bahamut_fury", True)],
        "M8-1-4": [("enemy_bahamut", True)],
    }
    for mid, pairs in manual_mission_enemies.items():
        m = mission_by_id.get(mid)
        if not m:
            continue
        for eid, is_boss in pairs:
            en = enemy_by_id.get(eid)
            if not en:
                continue
            arr = m["bossEnemyIds"] if is_boss else m["randomEnemyIds"]
            if eid not in arr:
                arr.append(eid)
            if not any(sp["missionId"] == mid for sp in en["spawns"]):
                en["spawns"].append({"missionId": mid, "role": "boss" if is_boss else "random"})

    for m in missions:
        raw_list = m.pop("_rawEnemies", [])
        for ename in raw_list:
            eid = enemy_name_to_id.get(ename.lower())
            if not eid:
                slug_cand = f"enemy_{slugify(ename)}"
                if slug_cand in enemy_by_id:
                    eid = slug_cand
            if not eid:
                continue
            en = enemy_by_id[eid]
            is_boss = en.get("isBoss", False) or (len(raw_list) == 1 and m["id"] not in ("M1-1-1",))
            target_arr = m["bossEnemyIds"] if is_boss else m["randomEnemyIds"]
            if eid not in target_arr:
                target_arr.append(eid)
            if not any(sp["missionId"] == m["id"] for sp in en["spawns"]):
                en["spawns"].append({"missionId": m["id"], "role": "boss" if is_boss else "random"})

    for en in enemies:
        for sp in en["spawns"]:
            mid = sp["missionId"]
            m = mission_by_id.get(mid)
            if not m:
                continue
            if sp["role"] == "boss":
                if en["id"] not in m["bossEnemyIds"] and en["id"] not in m["randomEnemyIds"]:
                    m["bossEnemyIds"].append(en["id"])
            else:
                if en["id"] not in m["randomEnemyIds"] and en["id"] not in m["bossEnemyIds"]:
                    m["randomEnemyIds"].append(en["id"])

    mission_star_overrides = {
        "M1-4-2": 6,
        "M1-4-3": 6,
        "M4-4-3": 6,
        "M6-6-3": 8,
        "M7-3-6": 6,
        "M7-4-6": 7,
        "M7-6-6": 10,
        "M8-4-4": 6,
        "M8-6-4": 9,
        "M9-5-3": 9,
        "M9-5-4": 10,
        "M9-6-4": 10,
        "M9-6-6": 10,
        "M10-2-3": 3,
    }

    for m in missions:
        linked_eids = [eid for eid in (m["bossEnemyIds"] + m["randomEnemyIds"]) if eid != "enemy_magic_pot"]
        levels = [enemy_by_id[eid]["stats"]["level"] for eid in linked_eids if eid in enemy_by_id and enemy_by_id[eid]["stats"]["level"]]
        if m["id"] in mission_star_overrides:
            stars = mission_star_overrides[m["id"]]
            m["stars"] = stars
            m["hardModeBenchmarks"] = compute_hard_benchmarks(stars, m["id"])
        elif levels and m["branch"] != "M1":
            max_lv = max(levels)
            if max_lv <= 8:
                stars = 1
            elif max_lv <= 14:
                stars = 2
            elif max_lv <= 20:
                stars = 3
            elif max_lv <= 27:
                stars = 4
            elif max_lv <= 35:
                stars = 5
            elif max_lv <= 44:
                stars = 6
            elif max_lv <= 54:
                stars = 7
            elif max_lv <= 64:
                stars = 8
            elif max_lv <= 76:
                stars = 9
            else:
                stars = 10
            m["stars"] = stars
            m["hardModeBenchmarks"] = compute_hard_benchmarks(stars, m["id"])

    def _ensure_ref_item(item_id: str | None, fallback_label: str = "") -> None:
        if not item_id or item_id in items:
            return
        label = fallback_label or item_id.replace("item_", "").replace("_plus_plus", "++").replace("_plus", "+").replace("_", " ").title()
        low = label.lower()
        cat = "key-items"
        sub = "Key / Unlock"
        desc = f"Obtained from Crisis Core missions, chests, or enemies ({label})."
        if re.search(r"\b[\d,]+\s*gil\b", low):
            sub = "Gil Chest"
            desc = f"Treasure chest containing {label}."
        elif any(k in low for k in ("shop", "commerce", "dept", "online", "shade", "duo", "trading", "souvenirs", "turtle", "outlet", "accessories")):
            sub = "Shop Unlock"
            desc = f"Network shop unlock item: adds {label} to the Worldwide Network shop menu."
        elif any(k in low for k in ("bangle", "armlet", "ring", "amulet", "belt", "glove", "helm", "armor", "shield", "suit", "ribbon", "brutal", "ziedrich", "slayer", "soul", "hairpin", "charm", "watch", "knuckles", "cape", "earrings", "talisman", "brooch", "badge", "headband", "vest", "band", "scarf", "crown", "bracelet")):
            cat = "accessories"
            sub = "Accessory"
            desc = f"Equipment accessory ({label})."
        elif any(k in low for k in ("materia", "fira", "firaga", "blizz", "thund", "cur", "drain", "punch", "jump", "dash", "libra", "barrier", "wall", "ultima", "flare", "darkness", "mug", "steal", "quak", "grav", "tri-", "blade", "shock", "up")):
            cat = "materia"
            sub = "Materia"
            desc = f"Equipable Materia ({label})."
        items[item_id] = {
            "id": item_id,
            "name": label,
            "category": cat,
            "subCategory": sub,
            "description": desc,
            "fusion": None,
            "shops": [],
            "clearRewardMissions": [],
            "treasureMissions": [],
        }

    for en in enemies:
        for slot in ("commonDrop", "rareDrop", "commonSteal", "rareSteal"):
            _ensure_ref_item(en["loot"].get(slot))

    for m in missions:
        if m["clearReward"]:
            _ensure_ref_item(m["clearReward"]["itemId"], canonical_item_name(m["clearReward"]["rawLabel"]))
            iid = m["clearReward"]["itemId"]
            if m["id"] not in items[iid]["clearRewardMissions"]:
                items[iid]["clearRewardMissions"].append(m["id"])
        for t in m["treasures"]:
            _ensure_ref_item(t["itemId"], canonical_item_name(t["rawLabel"]))
            iid = t["itemId"]
            if m["id"] not in items[iid]["treasureMissions"]:
                items[iid]["treasureMissions"].append(m["id"])

        unlock_str = m.get("unlockCondition") or ""
        prereqs = []
        for pm in re.findall(r"M\d+-\d+-\d+", unlock_str):
            if pm in mission_by_id and pm != m["id"] and pm not in prereqs:
                prereqs.append(pm)
        m["prerequisiteMissionIds"] = prereqs
        low_un = unlock_str.lower()
        if prereqs:
            m["unlockType"] = "mission"
        elif any(k in low_un for k in ("talk", "speak", "npc", "midgar", "shinra", "fan", "reporter", "spy", "director", "wonder", "chest")):
            m["unlockType"] = "npc"
        elif any(k in low_un for k in ("chapter", "story", "automatic", "start", "prologue", "available")):
            m["unlockType"] = "story"
        else:
            m["unlockType"] = "progression"

        if m["id"] in CURATED_MISSION_ROUTE_NOTES:
            m["routeNotes"] = CURATED_MISSION_ROUTE_NOTES[m["id"]]


CURATED_BOSS_GUIDES: dict[str, dict[str, Any]] = {
    "M9-6-6": {
        "targetName": "Minerva",
        "encounterType": "Superboss",
        "threatRating": "Extreme",
        "summary": "Hard Mode's ultimate 20,000,000 HP superboss. Requires 99,999 HP, 255 VIT & SPR, Costly Punch, and Mug for 99x Phoenix Downs.",
        "recommendedLoadout": {
            "materia": ["Costly Punch", "Curaga", "Wall", "Mug", "Aerial Drain", "SP Master"],
            "accessories": ["Genji Shield", "Genji Armor", "Genji Glove", "Genji Helm / Ziedrich"],
            "statTargets": "Rec Lv.85+ · HP 99,999 · VIT 255 · SPR 255"
        },
        "weaknessesAndCounters": [
            "No elemental weaknesses; halves/resists Fire, Ice, and Lightning — use defense-ignoring Costly Punch (99,999 dmg per swing).",
            "Immune to all status ailments, Gravity, and Death; SP Master + Genji Shield/Ziedrich keeps damage survivable.",
            "Carries 99x Phoenix Downs as Rare Steal — use Mug with Mog's Amulet + Brigand's Gloves (or Heike Soul) to restock Raise mid-fight."
        ],
        "keyAttacksToWatch": [
            "Judgment Arrow: Ultimate attack — breaks your Auto-Raise (Reraise) buff and hits hard; break her Limit Gauge during windup or immediately reapply Phoenix Down.",
            "Photon Feather / Crimson Flare: Rapid homing orbs and flame pillars — sidestep/dash perpendicularly or iframe with Aerial Drain.",
            "Thor's Hammer / Krysta: Heavy lightning/ice bursts — keep Wall active and heal immediately with Curaga."
        ],
        "killSteps": [
            "Open with Phoenix Down (Auto-Raise) and Wall, then Mug Minerva once to snag 99x Phoenix Downs.",
            "Circle behind Minerva, dodge her Photon Feathers/slashed combos, and punish openings with Costly Punch for 99,999 damage.",
            "When she charges Judgment Arrow, burst the gauge down to reduce damage; if Judgment Arrow lands, immediately use another Phoenix Down.",
            "Keep HP above 40,000 with Curaga/X-Potions (staying below ~110% HP threshold if needed for Costly Punch, though 99,999 HP works cleanly) until 20M HP hits zero."
        ],
        "proTip": "Judgment Arrow removes Auto-Raise even if you survive it — make re-popping a Phoenix Down your #1 reflex right after the animation ends."
    },
    "M5-1-1": {
        "targetName": "Ifrit",
        "encounterType": "Story Boss",
        "threatRating": "Low",
        "summary": "Classic fire summon boss weak to Ice. Keep Barrier up and break Hellfire's gauge to win cleanly.",
        "recommendedLoadout": {
            "materia": ["Blizzara / Blizzaga", "Barrier", "Cura", "Assault Twister", "Libra"],
            "accessories": ["Flame Armlet", "Bronze Bangle", "Earrings"],
            "statTargets": "Rec Lv.12+ · HP 2,200+ · VIT 25 · SPR 25"
        },
        "weaknessesAndCounters": [
            "Weak to Ice — Blizzara/Blizzaga and Blizzard Blade deal bonus damage and stagger him faster.",
            "Absorbs Fire — never cast Fire/Fira/Hell Firaga or you will heal him."
        ],
        "keyAttacksToWatch": [
            "Hellfire: Limit Gauge finisher — unload Ice spells and Strong Attacks during the countdown to drop the gauge.",
            "Crimson Rush / Fireball: Telegraphed lunge and fire projectiles — dodge sideways and punish from his flank."
        ],
        "killSteps": [
            "Cast Barrier at the start and lock on while strafing around Ifrit's melee swings.",
            "Spam Blizzara/Blizzaga from mid-range or weave Battle Stance combos after dodging his lunge.",
            "Focus everything into breaking the Hellfire gauge when he charges, then finish with Ice burst."
        ],
        "proTip": "Equipping Flame Armlet or Fire-warding accessories trivializes his fire attacks even on Hard Mode."
    },
    "M8-1-1": {
        "targetName": "Ifrit",
        "encounterType": "Story Boss",
        "threatRating": "Low",
        "summary": "Rematch against Ifrit to unlock his DMW summon. Weak to Ice and absorbs all Fire damage.",
        "recommendedLoadout": {
            "materia": ["Blizzara / Blizzaga", "Barrier", "Cura", "Assault Twister"],
            "accessories": ["Flame Armlet", "Bronze Bangle", "Earrings"],
            "statTargets": "Rec Lv.12+ · HP 2,200+ · VIT 25 · SPR 25"
        },
        "weaknessesAndCounters": [
            "Weak to Ice — Blizzara/Blizzaga shreds his HP and quickly empties the Hellfire gauge.",
            "Absorbs Fire — remove any Fire Materia before entering."
        ],
        "keyAttacksToWatch": [
            "Hellfire: Limit Gauge attack — break the gauge with Ice casts + Buster Sword Stance.",
            "Blazing Slam / Fireballs: Sidestep out of the red impact zone and counter."
        ],
        "killSteps": [
            "Open with Barrier and circle Ifrit to bait his melee slam.",
            "Chain Blizzara/Blizzaga casts whenever he recovers from an attack.",
            "Break Hellfire's gauge to earn a free stagger window and claim the Ifrit DMW unlock."
        ],
        "proTip": "Clearing M8-1-1 unlocks the Ifrit Materia for your DMW roster — an easy early Ch. 2/3 grab."
    },
    "M5-1-2": {
        "targetName": "Bahamut",
        "encounterType": "Story Boss",
        "threatRating": "Low",
        "summary": "Aerial dragon boss with no elemental weaknesses. Dodge claw swipes, jump through beams, and break Megaflare.",
        "recommendedLoadout": {
            "materia": ["High Jump", "Wall / Barrier", "Cura", "Darkness", "Fira / Thundara"],
            "accessories": ["Muscle Belt", "Shinra Beta", "Bulletproof Vest"],
            "statTargets": "Rec Lv.18+ · HP 4,000+ · VIT 45 · SPR 45"
        },
        "weaknessesAndCounters": [
            "No elemental weaknesses; relies on balanced physical and non-elemental beam damage.",
            "High Jump / Aerial Drain grants invincibility frames to dodge sweeping breath attacks while dealing heavy physical hits."
        ],
        "keyAttacksToWatch": [
            "Megaflare: Major Limit Gauge laser — burst the gauge to minimize damage or hold Wall + full HP.",
            "Flare Breath / Claw Combo: Wide front cone — dodge behind Bahamut's wings to stay safe."
        ],
        "killSteps": [
            "Apply Wall or Barrier/MBarrier immediately at the start of the fight.",
            "Stay behind or beside Bahamut, using High Jump or Battle Stance slashes after his claw combos.",
            "Save Limit Breaks or high-damage Command Materia to shatter the Megaflare gauge."
        ],
        "proTip": "Watch Bahamut's wings: when he hovers back to charge a beam, trigger High Jump to evade completely and land a counter."
    },
    "M8-1-4": {
        "targetName": "Bahamut",
        "encounterType": "Story Boss",
        "threatRating": "Low",
        "summary": "DMW unlock rematch vs Bahamut. Maintain Wall, stay off his centerline, and burst Megaflare.",
        "recommendedLoadout": {
            "materia": ["High Jump", "Wall / Barrier", "Cura", "Darkness"],
            "accessories": ["Muscle Belt", "Shinra Beta", "Bulletproof Vest"],
            "statTargets": "Rec Lv.18+ · HP 4,000+ · VIT 45 · SPR 45"
        },
        "weaknessesAndCounters": [
            "Balanced defenses without elemental weak points — physical Command Materia and Buster Sword Stance hit reliably.",
            "Vulnerable to sustained stagger pressure during Megaflare windup."
        ],
        "keyAttacksToWatch": [
            "Megaflare: Charge attack — break the gauge quickly or guard with MBarrier + full HP.",
            "Tail Sweep & Flare Breath: Avoid standing directly in front of his head."
        ],
        "killSteps": [
            "Cast Wall/MBarrier and close distance diagonally.",
            "Alternate High Jump and Strong Attack punishes on his flanks.",
            "Drain the Megaflare gauge whenever it appears and finish him for the Bahamut DMW Materia."
        ],
        "proTip": "Clearing M8-1-4 unlocks Bahamut on the DMW, progressing your 100% DMW Genji Armor requirement."
    },
    "M5-1-4": {
        "targetName": "Bahamut Fury",
        "encounterType": "Story Boss",
        "threatRating": "Extreme",
        "summary": "9★ Hard Mode cosmic dragon boss. Hits very hard with Exaflare and Cluster projectiles; bring Break HP Limit + Wall.",
        "recommendedLoadout": {
            "materia": ["Costly Punch", "Aerial Drain", "Curaga", "Wall", "Graviga / Darkness"],
            "accessories": ["Adaman Bangle", "Brutal / Genji Glove", "Ziedrich", "Sprint Shoes"],
            "statTargets": "Rec Lv.68+ · HP 35,000+ · VIT 180+ · SPR 180+"
        },
        "weaknessesAndCounters": [
            "No elemental weakness and immune to most ailments — pure non-elemental Costly Punch + Aerial Drain is king.",
            "High Hard Mode HP (353,970) rewards Break Damage Limit (Brutal or Buster Sword 23%+)."
        ],
        "keyAttacksToWatch": [
            "Exaflare: Screen-filling Limit Gauge blast — break the gauge with Costly Punch or hold Wall + Auto-Raise (Phoenix Down).",
            "Cluster / Hexafang: Tracking energy spheres and dash strikes — dodge sideways continuously until the salvo finishes."
        ],
        "killSteps": [
            "Pop Phoenix Down and Wall immediately at mission start.",
            "Dash laterally through Cluster volleys, then close in for Costly Punch or Aerial Drain.",
            "Break Exaflare's gauge with rapid Costly Punch hits to prevent heavy party-wipe damage."
        ],
        "proTip": "Aerial Drain's hang-time dodges Hexafang cleanly while topping off your HP bar."
    },
    "M8-5-6": {
        "targetName": "Bahamut Fury",
        "encounterType": "Story Boss",
        "threatRating": "Extreme",
        "summary": "9★ Treasure Info finale featuring Bahamut Fury. Maintain Wall, dodge Cluster orbs, and punish with Costly Punch.",
        "recommendedLoadout": {
            "materia": ["Costly Punch", "Aerial Drain", "Curaga", "Wall", "Mug"],
            "accessories": ["Adaman Bangle", "Brutal / Genji Glove", "Ziedrich", "Champion Belt"],
            "statTargets": "Rec Lv.68+ · HP 35,000+ · VIT 180+ · SPR 180+"
        },
        "weaknessesAndCounters": [
            "No elemental weaknesses; Costly Punch ignores his high defenses for consistent 99,999 hits.",
            "Bring Adaman Bangle (M7-3-6) and Brutal (M7-4-6) so Exaflare cannot one-shot you."
        ],
        "keyAttacksToWatch": [
            "Exaflare: Limit Gauge nuke — burst down the gauge or rely on Phoenix Down + Wall.",
            "Cluster / Homing Lasers: Sprint and roll laterally, never straight backward."
        ],
        "killSteps": [
            "Buff Wall and Phoenix Down before engaging.",
            "Bait his melee swipe, dodge behind him, and land Costly Punch or Aerial Drain.",
            "Focus every hit into the Exaflare gauge during charge phases until Bahamut Fury falls."
        ],
        "proTip": "Clearing M8-5-6 unlocks the Bahamut Fury DMW summon (Exaflare)."
    },
    "M5-1-5": {
        "targetName": "Genesis",
        "encounterType": "Story Boss",
        "threatRating": "High",
        "summary": "Fast swordsman & mage boss who chains Black Flurry and Dark Energy. Guard his slashes and punish recovery.",
        "recommendedLoadout": {
            "materia": ["Costly Punch / High Jump", "Curaga", "Wall", "Darkness", "Aerial Drain"],
            "accessories": ["Adaman Bangle", "Brutal", "Force Bracelet", "Twisted Headband"],
            "statTargets": "Rec Lv.46+ · HP 18,000+ · VIT 135 · SPR 135"
        },
        "weaknessesAndCounters": [
            "Immune to instant-death cheese and most statuses; weak to aggressive stagger pressure after his sword combos.",
            "Physical attacks from behind or during Dark Energy recovery deal reliable criticals."
        ],
        "keyAttacksToWatch": [
            "Black Flurry / Apocalypse: Multi-hit dark slash and beam — guard or dash wide around him.",
            "Dark Energy / Homing Fireballs: Circle-strafe until orbs dissipate before rushing in."
        ],
        "killSteps": [
            "Keep Wall active and stay mid-range to read his sword dash tells.",
            "Guard or dodge behind his 3-hit slash combo, then counter with Costly Punch or Battle Stance Strong Attack.",
            "Burn the Limit Gauge if Apocalypse begins charging, and heal with Curaga between waves."
        ],
        "proTip": "Buster Sword Stance Guard absorbs Genesis's physical flurries and turns every parry into a boosted punish."
    },
    "M5-1-6": {
        "targetName": "Angeal Penance",
        "encounterType": "Story Boss",
        "threatRating": "Moderate",
        "summary": "Winged boss with directional Defense of Lust counter-stance and elemental wing attacks. Always flank behind him.",
        "recommendedLoadout": {
            "materia": ["High Jump", "Wall / Barrier", "Cura / Curaga", "Darkness", "Assault Twister+"],
            "accessories": ["Shinra Beta", "Earrings", "Doc's Code", "Safety Bit"],
            "statTargets": "Rec Lv.28+ · HP 7,500+ · VIT 75 · SPR 75"
        },
        "weaknessesAndCounters": [
            "No elemental weaknesses; punishes frontal attacks whenever his Defense of Lust shield is raised.",
            "Always circle to his back — back-attacks bypass Defense of Lust and score guaranteed crits."
        ],
        "keyAttacksToWatch": [
            "Charge of Greed / Thunder of Envy: Lightning and rush attacks — equip Thunder/Lightning ward or Wall and dodge laterally.",
            "Wings of Pride: Heavy Limit Gauge attack — burst the gauge down from behind."
        ],
        "killSteps": [
            "Cast Wall and immediately roll behind Angeal Penance.",
            "Pause frontal strikes when he raises his wing guard (Defense of Lust) and reposition behind him.",
            "Use High Jump or Assault Twister+ into his back until he falls."
        ],
        "proTip": "Never mash into his front guard — one dash behind him turns Defense of Lust into a free damage window."
    },
    "M5-2-1": {
        "targetName": "Sephiroth",
        "encounterType": "Story Boss",
        "threatRating": "High",
        "summary": "Deadly duelist featuring Heartless Angel (drops HP to 1) and Octaslash. Keep a fast heal ready at all times.",
        "recommendedLoadout": {
            "materia": ["Curaga", "Wall", "Costly Punch / High Jump", "Aerial Drain", "Mug"],
            "accessories": ["Adaman Bangle", "Brutal", "Ziedrich / Shinra Alpha", "Safety Bit"],
            "statTargets": "Rec Lv.40+ · HP 14,000+ · VIT 120 · SPR 120"
        },
        "weaknessesAndCounters": [
            "Immune to Death and Stop; vulnerable to quick counter-attacks right after his Masamune dash combos.",
            "Keep X-Potions/Elixirs or Curaga slotted next to your primary attack for instant Heartless Angel recovery."
        ],
        "keyAttacksToWatch": [
            "Heartless Angel: Drops Zack's HP to 1 — dodge or immediately cast Curaga/X-Potion before his next slash.",
            "Telluric Fury / Shadow Flare: Wide ground wave and tracking dark orbs — sidestep and keep moving.",
            "Octaslash: Limit Gauge finisher — burst the gauge down to avoid lethal multi-slash damage."
        ],
        "killSteps": [
            "Apply Wall and Phoenix Down at the start so a sudden Heartless Angel combo cannot end the run.",
            "Stay at medium range, dodge his Masamune lunge, and punish his back with High Jump or Costly Punch.",
            "The instant you see Heartless Angel, cancel into Curaga or an X-Potion before re-engaging."
        ],
        "proTip": "If you stay close and stun/interrupt him during Heartless Angel's hover windup, you can sometimes cancel it altogether."
    },
    "M5-2-2": {
        "targetName": "Sephiroth + 4 Materia Orbs",
        "encounterType": "Multi-Target Boss",
        "threatRating": "Extreme",
        "summary": "Sephiroth backed by Fire, Blizzard, Thunder, and Support Materia orbs. Destroy the Support/Elemental orbs first.",
        "recommendedLoadout": {
            "materia": ["Costly Punch / Darkness", "Quake / Ultima", "Curaga", "Wall", "Aerial Drain"],
            "accessories": ["Adaman Bangle", "Brutal", "Elemental Ring / Force Bracelet", "Ribbon / Super Ribbon"],
            "statTargets": "Rec Lv.45+ · HP 18,000+ · VIT 135 · SPR 135"
        },
        "weaknessesAndCounters": [
            "Destroying the 4 floating Materia orbs strips Sephiroth's elemental barrage and buff/heal support.",
            "AoE Darkness, Quake, or Assault Twister+ clips multiple orbs while damaging Sephiroth."
        ],
        "keyAttacksToWatch": [
            "Heartless Angel: Drops HP to 1 — follow immediately with Curaga or X-Potion.",
            "Synchronized Firaga/Blizzaga/Thundaga from the orbs — keep Wall up and prioritize the Support Materia orb first."
        ],
        "killSteps": [
            "Cast Wall + Phoenix Down, then immediately target and destroy Support Materia and the elemental orbs.",
            "Use Quake/Darkness or Aerial Drain to clear remaining orbs while dodging Sephiroth's lunges.",
            "Once alone, punish Sephiroth's sword swings and heal instantly after any Heartless Angel."
        ],
        "proTip": "Killing the Support Materia orb first stops it from buffing and supporting Sephiroth throughout the fight."
    },
    "M5-2-3": {
        "targetName": "Hollander",
        "encounterType": "Story Boss",
        "threatRating": "High",
        "summary": "Ailment-spamming boss who summons Land Worms and heals himself. Status immunity (Ribbon / Status Ward) trivializes him.",
        "recommendedLoadout": {
            "materia": ["Hell Firaga / Hell Blizzaga", "Status Ward", "Costly Punch / Darkness", "Curaga", "Dispel"],
            "accessories": ["Ribbon / Super Ribbon", "Adaman Bangle", "Brigand's Gloves", "Shinra Alpha"],
            "statTargets": "Rec Lv.40+ · HP 14,000+ · VIT 115 · SPR 115"
        },
        "weaknessesAndCounters": [
            "Hollander's main threat is Poison, Silence, Curse, and Stop flasks — equip Ribbon or Status Ward + Hell-aga for 100% status immunity.",
            "High burst damage stops him from out-healing with potions/Curaga and clears summoned Land Worms fast."
        ],
        "keyAttacksToWatch": [
            "Status Flasks / Bad Breath-style debuffs: Blocked completely by Status Ward + Hell Firaga/Blizzaga.",
            "Land Worm Summon + Self-Heal: Wipe Land Worms with AoE Darkness/Quake so they don't Stop-lock you."
        ],
        "killSteps": [
            "Equip Status Ward + a Hell-aga Materia (or Ribbon) before starting the mission.",
            "Open with Wall and rush Hollander down with Costly Punch or High Jump.",
            "Clear any spawned Land Worms immediately with AoE Command/Magic Materia, then finish Hollander."
        ],
        "proTip": "A single Hell Firaga/Blizzaga + Status Ward combo completely shuts down both Hollander's flasks and Land Worm Stop."
    },
    "M1-1-1": {
        "targetName": "Sentry",
        "encounterType": "Mission Boss",
        "threatRating": "Low",
        "summary": "Introductory SOLDIER simulation against Shinra Sentries. Great spot for Battle Stance practice and AFK DMW spins.",
        "recommendedLoadout": {
            "materia": ["Fire / Thunder", "Cure", "Assault Twister", "Libra"],
            "accessories": ["Bronze Bangle", "Earrings"],
            "statTargets": "Rec Lv.3+ · HP 900+ · VIT 15 · SPR 15"
        },
        "weaknessesAndCounters": [
            "Low Hard HP (945) and no elemental immunities — basic sword combos and Fire/Thunder clear in seconds."
        ],
        "keyAttacksToWatch": [
            "Quintuple Shot / Tonfa: Block with Guard or Battle Stance to build early Buster Sword Proficiency."
        ],
        "killSteps": [
            "Activate Battle Stance, block or sidestep the Sentry's Tonfa swing, and land Strong Attack.",
            "Sweep groups with Assault Twister or basic combos."
        ],
        "proTip": "Later on, M1-1-1 is the #1 AFK DMW mastering mission: equip 4x boost Materia + Regen/Auto-Potion and let Sentries hit you while you earn 100% DMW."
    },
    "M1-1-3": {
        "targetName": "50 Shinra Troopers (Sergeant & Chief Petty Officer)",
        "encounterType": "Endurance Gauntlet",
        "threatRating": "Moderate",
        "summary": "50-wave Shinra infantry gauntlet. Bring AoE wave-clear and sustain so chip damage doesn't add up.",
        "recommendedLoadout": {
            "materia": ["Darkness / Assault Twister+", "Quake / Thundaga", "Aerial Drain", "Wall", "Curaga"],
            "accessories": ["Adaman Bangle / Platinum Bangle", "Brutal", "Twisted Headband"],
            "statTargets": "Rec Lv.30+ · HP 8,500+ · VIT 85 · SPR 85"
        },
        "weaknessesAndCounters": [
            "No elemental immunities; AoE Darkness, Quake, or Assault Twister+ clears entire squads in one cast.",
            "Raise Buster Sword Proficiency to 23%+ for Break Damage Limit on Strong Attacks."
        ],
        "keyAttacksToWatch": [
            "Concentrated Gunfire & Grenades: Keep Wall active so stray shots don't stagger or chip you down."
        ],
        "killSteps": [
            "Cast Wall and group troopers together by circling the perimeter.",
            "Spam Darkness, Quake, or Assault Twister+ to wipe waves instantly.",
            "Top off HP with Aerial Drain or Curaga between spawns until all 50 fall."
        ],
        "proTip": "Pairing Drain/Aerial Drain with Wall lets you clear all 50 troopers without spending items."
    },
    "M1-1-4": {
        "targetName": "100 Shinra Troopers (Sergeant Major & Special Ops)",
        "encounterType": "Endurance Gauntlet",
        "threatRating": "Moderate",
        "summary": "100-enemy Shinra survival gauntlet. AoE Command/Magic Materia and Regen/Drain sustain make it effortless.",
        "recommendedLoadout": {
            "materia": ["Darkness / Assault Twister+", "Quake / Electrocute", "Aerial Drain", "Wall", "Curaga"],
            "accessories": ["Adaman Bangle", "Brutal", "Sprint Shoes"],
            "statTargets": "Rec Lv.30+ · HP 8,500+ · VIT 85 · SPR 85"
        },
        "weaknessesAndCounters": [
            "Troopers lack high magical/physical resistances — AoE Quake or Darkness hits every spawn simultaneously."
        ],
        "keyAttacksToWatch": [
            "Crossfire & Stun Grenades: Keep moving, maintain Wall, and stay near the edges to prevent being surrounded."
        ],
        "killSteps": [
            "Maintain Wall and herd enemies into tight packs.",
            "Clear packs with Quake, Electrocute, or Darkness.",
            "Use Aerial Drain whenever HP dips below 60% until all 100 are defeated."
        ],
        "proTip": "Great early-mid spot to farm SP and DMW limit triggers while building Buster Sword Proficiency."
    },
    "M1-1-5": {
        "targetName": "200 Shinra Troopers (Warrant Officer & Combatant)",
        "encounterType": "Endurance Gauntlet",
        "threatRating": "Moderate",
        "summary": "200-trooper endurance mission. Prioritize MP/HP sustain (Osmose/Aerial Drain/Regen) alongside fast AoE clears.",
        "recommendedLoadout": {
            "materia": ["Quake / Darkness", "Aerial Drain", "Wall", "Osmose / Curaga", "Assault Twister+"],
            "accessories": ["Adaman Bangle", "Brutal", "Precious Watch / Gold Hairpin"],
            "statTargets": "Rec Lv.32+ · HP 9,500+ · VIT 90 · SPR 90"
        },
        "weaknessesAndCounters": [
            "Warrant Officers have ~94k Hard HP — Break Damage Limit (23%+ Buster Sword or Brutal) cuts clear time in half."
        ],
        "keyAttacksToWatch": [
            "Multi-directional rifle volleys and grenades — never stand stationary in the center of the arena."
        ],
        "killSteps": [
            "Open with Wall and circle-strafe to keep all troopers on one side of Zack.",
            "Chain Quake/Darkness/Assault Twister+ and recover HP with Aerial Drain.",
            "Refresh Wall every few waves until the 200-kill counter finishes."
        ],
        "proTip": "Clear reward is HP Up++, and Warrant Officers/Combatants feed steady SP for fusion."
    },
    "M1-1-6": {
        "targetName": "1,000 Shinra Troopers (Ensign & Guard)",
        "encounterType": "Endurance Gauntlet",
        "threatRating": "High",
        "summary": "The famous 1,000-trooper marathon. Bring Genji Helm (0 MP/AP) or Osmose + Quake/Electrocute/Darkness for fast clears.",
        "recommendedLoadout": {
            "materia": ["Quake / Electrocute", "Darkness", "Aerial Drain", "Wall", "Curaga", "Osmose"],
            "accessories": ["Adaman Bangle", "Brutal", "Genji Helm / Soul of Thamasa", "Precious Watch"],
            "statTargets": "Rec Lv.38+ · HP 15,000+ · VIT 110+ · SPR 110+"
        },
        "weaknessesAndCounters": [
            "Ensigns reach 122,520 Hard HP — Quake + Dualcast or Costly Punch / Assault Twister+ clears waves quickly.",
            "0-MP/AP accessories (Genji Helm, Soul of Thamasa, Black Cowl) prevent running dry mid-marathon."
        ],
        "keyAttacksToWatch": [
            "Endless flanking gunfire & status/knockback hits — keep Wall up and use Aerial Drain to heal off chip damage."
        ],
        "killSteps": [
            "Equip AoE clear (Quake/Electrocute/Darkness) and sustain (Wall + Aerial Drain + Curaga).",
            "Hug one edge of the map so spawns funnel in front of you rather than behind.",
            "Rhythmically wipe waves and refresh Wall/MP until all 1,000 troopers drop for the Mug Materia reward."
        ],
        "proTip": "Reward is Mug — a mandatory Materia for stealing 99x Phoenix Downs from Minerva and farming Mako/Stat Stones."
    },
    "M3-2-3": {
        "targetName": "General's Tank + Support Machine",
        "encounterType": "Multi-Target Boss",
        "threatRating": "Moderate",
        "summary": "Armored tank boss paired with a Support Machine that heals and buffs it. Kill the Support Machine first!",
        "recommendedLoadout": {
            "materia": ["Thundara / Thundaga", "High Jump", "Wall / Barrier", "Cura", "Dispel"],
            "accessories": ["Muscle Belt", "Shinra Beta", "Earrings"],
            "statTargets": "Rec Lv.24+ · HP 6,000+ · VIT 65 · SPR 65"
        },
        "weaknessesAndCounters": [
            "Mechanical targets — Lightning spells (Thundara/Thundaga) deal heavy bonus damage.",
            "Destroying the Support Machine immediately stops constant barrier/heal casts on the General's Tank."
        ],
        "keyAttacksToWatch": [
            "Tank Cannon & Support Repairs: Dodge behind the tank's turret and eliminate the Support Machine right away."
        ],
        "killSteps": [
            "Cast Barrier/Wall and immediately focus down the Support Machine with Thundara/High Jump.",
            "Circle behind the General's Tank to avoid frontal cannon blasts.",
            "Finish the Tank with Lightning magic and Battle Stance Strong Attacks."
        ],
        "proTip": "Always prioritize Support Machine adds in Shinra mech fights — removing their healing cuts the fight length by 70%."
    },
    "M6-6-5": {
        "targetName": "Gaea Malboro",
        "encounterType": "Mission Boss",
        "threatRating": "Extreme",
        "summary": "10★ endgame Malboro with 1.28M Hard HP, Really Bad Breath, and Ultima. Status immunity is mandatory.",
        "recommendedLoadout": {
            "materia": ["Costly Punch", "Hell Firaga / Hell Blizzaga", "Status Ward", "Wall", "Curaga", "Aerial Drain"],
            "accessories": ["Genji Shield / Super Ribbon", "Adaman Bangle", "Genji Glove / Brutal", "Ziedrich"],
            "statTargets": "Rec Lv.75+ · HP 50,000+ · VIT 200+ · SPR 200+"
        },
        "weaknessesAndCounters": [
            "Zero elemental weaknesses and huge 1.28M Hard HP — Costly Punch (99,999 dmg) is the fastest kill tool.",
            "Super Ribbon, Genji Shield, or Status Ward + Hell-aga completely neutralizes Really Bad Breath."
        ],
        "keyAttacksToWatch": [
            "Really Bad Breath: Inflicts Poison, Silence, Stop, Curse, and Stun simultaneously — fatal without status protection.",
            "Ultima: Massive non-elemental nuke — keep Wall up and HP above 30,000."
        ],
        "killSteps": [
            "Verify Ribbon/Genji Shield or Status Ward + Hell-aga is equipped before starting.",
            "Open with Wall + Phoenix Down and circle behind Gaea Malboro.",
            "Burst down its 1.28M HP with Costly Punch, healing with Curaga/Aerial Drain after Ultima."
        ],
        "proTip": "Steal or farm safely only after locking in full Stop/Status immunity."
    },
    "M7-6-6": {
        "targetName": "Diatryma (Plus Magic Pot Genji Shield Encounter)",
        "encounterType": "Mission Boss",
        "threatRating": "Extreme",
        "summary": "10★ mission boss Diatryma — and home of the special Magic Pot that awards the Genji Shield!",
        "recommendedLoadout": {
            "materia": ["Costly Punch", "Gil Toss", "Octaslash DMW (optional)", "Curaga", "Wall", "Aerial Drain"],
            "accessories": ["Adaman Bangle", "Genji Glove / Brutal", "Ziedrich", "Super Ribbon"],
            "statTargets": "Rec Lv.75+ · HP 50,000+ · VIT 200+ · SPR 200+"
        },
        "weaknessesAndCounters": [
            "Diatryma hits hard physically and casts high-tier magic — Costly Punch + Wall handles it cleanly.",
            "Magic Pot bonus encounter: Must satisfy Gil Toss → Costly Punch → 99,999 damage → Octaslash to earn Genji Shield!"
        ],
        "keyAttacksToWatch": [
            "Diatryma Aerial Dive & Flare/Energy: Dodge sideways and keep Wall active.",
            "Magic Pot Escape: Do NOT attack Magic Pot normally; perform its exact 4 requested moves."
        ],
        "killSteps": [
            "Bring Gil Toss, Costly Punch, and ≥99,999 damage capability (plus Octaslash Materia if hunting Magic Pot).",
            "For Diatryma: open with Wall + Phoenix Down, dodge its dives, and punch it down with Costly Punch.",
            "If Magic Pot spawns in random battles, follow its prompts (Gil Toss, Costly Punch, 99,999 hit, Octaslash) to claim Genji Shield."
        ],
        "proTip": "Equip Octaslash DMW Materia (from M1-3-x/Shop) in M7-6-6 to boost Sephiroth's Octaslash rate when Magic Pot asks for it."
    },
    "M9-6-4": {
        "targetName": "Great Malboro / Emperor Sahagin / Diatryma",
        "encounterType": "Multi-Target Boss",
        "threatRating": "Extreme",
        "summary": "10★ cavern biomegauntlet housing the Genji Glove treasure chest. Bring full status immunity and Costly Punch.",
        "recommendedLoadout": {
            "materia": ["Costly Punch", "Aerial Drain", "Curaga", "Wall", "Mug"],
            "accessories": ["Genji Shield / Super Ribbon", "Adaman Bangle", "Brutal", "Ziedrich"],
            "statTargets": "Rec Lv.80+ · HP 60,000+ · VIT 220+ · SPR 220+"
        },
        "weaknessesAndCounters": [
            "Great Malboro's Bad Breath inflicts Stop/Death/ailments — Genji Shield or Super Ribbon is essential.",
            "Costly Punch ignores high endgame VIT/SPR across all targets."
        ],
        "keyAttacksToWatch": [
            "Bad Breath / Gastric Juice: Instant status lock without Ribbon/Status Ward.",
            "Ultima / Energy from endgame mobs: Keep Wall + Phoenix Down active."
        ],
        "killSteps": [
            "Grab every chest along the cavern paths (especially Genji Glove!) before fighting the boss marker.",
            "Pop Phoenix Down + Wall, then focus down Great Malboro first with Costly Punch.",
            "Clean up Emperor Sahagin and Diatryma using Costly Punch + Aerial Drain sustain."
        ],
        "proTip": "Don't forget to open the side chest for Genji Glove — it grants permanent Break Damage Limit & 100% Critical!"
    },
    "M9-6-5": {
        "targetName": "Goliath & Mock Troopers A/B/C",
        "encounterType": "Multi-Target Boss",
        "threatRating": "Extreme",
        "summary": "10★ final cavern gauntlet guarding SP Master. Goliath has 1.75M+ Hard HP — burst it down with Costly Punch.",
        "recommendedLoadout": {
            "materia": ["Costly Punch", "Aerial Drain", "Curaga", "Wall", "Mug"],
            "accessories": ["Genji Shield", "Genji Glove / Brutal", "Adaman Bangle", "Ziedrich"],
            "statTargets": "Rec Lv.82+ · HP 75,000+ · VIT 230+ · SPR 230+"
        },
        "weaknessesAndCounters": [
            "High endgame defenses across Goliath and Mock Troopers — Costly Punch (99,999 dmg) bypasses all armor.",
            "Kill Mock Troopers quickly with Aerial Drain / Costly Punch so they cannot flank while you fight Goliath."
        ],
        "keyAttacksToWatch": [
            "Goliath Heavy Cannon & Power Slams: Massive physical/energy bursts — stay behind Goliath with Wall + Phoenix Down up."
        ],
        "killSteps": [
            "Apply Wall and Phoenix Down before engaging the boss arena.",
            "Eliminate Mock Trooper adds quickly or kite behind Goliath to avoid crossfire.",
            "Circle behind Goliath and loop Costly Punch + Curaga until it drops for SP Master."
        ],
        "proTip": "Clearing M9-6-5 rewards SP Master, which pairs with M9-5-3 SP farming for the Minerva fight."
    },
    "M10-1-1": {
        "targetName": "Kactuar",
        "targetEnemyIds": ["enemy_kactuar"],
        "encounterType": "Mission Boss",
        "threatRating": "Low",
        "summary": "Nimble desert Cactoid that fires fixed-damage 1,000 Needles. Keep HP > 1,500 and rush it down.",
        "recommendedLoadout": {
            "materia": ["Assault Twister / High Jump", "Cura", "Barrier", "Fira / Blizzara"],
            "accessories": ["Bronze Bangle", "Sprint Shoes", "Twisted Headband"],
            "statTargets": "Rec Lv.15+ · HP 2,000+ · VIT 30 · SPR 30"
        },
        "weaknessesAndCounters": [
            "Low HP pool; fast-startup Command Materia or basic melee combos finish Kactuar before it flees or spams Needles."
        ],
        "keyAttacksToWatch": [
            "1,000 Needles: Deals fixed 1,000 damage ignoring defense — dodge sideways when it stops and shakes."
        ],
        "killSteps": [
            "Keep HP above 1,500 at all times so 1,000 Needles cannot one-shot you.",
            "Close distance with dash attacks or High Jump to interrupt its Needle windup.",
            "Finish Kactuar quickly before Raijincho lightning adds chip your HP."
        ],
        "proTip": "Fixed-damage Needle attacks bypass VIT/Barrier — raw max HP is your best safety net."
    },
    "M10-1-2": {
        "targetName": "Kactuar",
        "encounterType": "Mission Boss",
        "threatRating": "Low",
        "summary": "Second Cactoid hunt with Raijincho & Trap support. Watch for 1,000 Needles fixed damage.",
        "recommendedLoadout": {
            "materia": ["High Jump / Assault Twister", "Cura", "Barrier", "Blizzara"],
            "accessories": ["Shinra Beta", "Thunder Armlet", "Twisted Headband"],
            "statTargets": "Rec Lv.18+ · HP 2,800+ · VIT 35 · SPR 35"
        },
        "weaknessesAndCounters": [
            "Low HP; burst Kactuar immediately and avoid Raijincho's Lightning strikes."
        ],
        "keyAttacksToWatch": [
            "1,000 Needles: Fixed 1,000 damage — roll sideways out of line-of-sight."
        ],
        "killSteps": [
            "Maintain HP > 1,500 and rush Kactuar down first.",
            "Dodge sideways on Needle windup and punish with High Jump / Strong Attack."
        ],
        "proTip": "Grab the Cursed Ring / AP Up chest along the path before ending the mission."
    },
    "M10-1-3": {
        "targetName": "Kactuer",
        "targetEnemyIds": ["enemy_kactuer"],
        "encounterType": "Mission Boss",
        "threatRating": "Moderate",
        "summary": "King Cactoid boss armed with 10,000 Needles! Keep HP above 10,000 or dodge every Needle volley.",
        "recommendedLoadout": {
            "materia": ["Costly Punch / High Jump", "Curaga", "Wall", "Darkness"],
            "accessories": ["Adaman Bangle / Platinum Bangle", "Brutal", "Twisted Headband"],
            "statTargets": "Rec Lv.25+ · HP 11,000+ · VIT 55 · SPR 55"
        },
        "weaknessesAndCounters": [
            "Low overall HP for its threat level — High Jump or Costly Punch ends the fight in a few clean hits.",
            "10,000 Needles ignores VIT/Wall, so Break HP Limit (Adaman Bangle or +HP% Materia) prevents one-shots."
        ],
        "keyAttacksToWatch": [
            "10,000 Needles: Fixed 10,000 damage — fatal if HP ≤ 9,999! Dodge laterally or jump over it with High Jump/Aerial Drain."
        ],
        "killSteps": [
            "Boost max HP over 10,500 (via HP Up% Materia or Adaman Bangle) or bring Phoenix Down.",
            "Track Kactuer closely and punish its pauses with High Jump or Costly Punch.",
            "Heal immediately after any 10,000 Needles hit and finish it to earn the Cactus Thorn (Cactuar DMW)."
        ],
        "proTip": "Completing M10-1-3 awards Cactus Thorn, unlocking Cactuar on your DMW!"
    },
    "M10-2-1": {
        "targetName": "Tonberry",
        "encounterType": "Mission Boss",
        "threatRating": "Low",
        "summary": "Slow but lethal close-range stalker with Chef's Knife & Everyone's Grudge. Kite and strike from behind.",
        "recommendedLoadout": {
            "materia": ["High Jump", "Fira / Thundara", "Cura", "Barrier"],
            "accessories": ["Safety Bit", "Shinra Beta", "Earrings"],
            "statTargets": "Rec Lv.18+ · HP 3,500+ · VIT 40 · SPR 40"
        },
        "weaknessesAndCounters": [
            "Very slow movement speed — ranged magic and Jump attacks hit safely without entering Chef's Knife range."
        ],
        "keyAttacksToWatch": [
            "Chef's Knife / Everyone's Grudge: Heavy close-range stab & grudge damage — never trade hits face-to-face."
        ],
        "killSteps": [
            "Stay out of melee range until Tonberry finishes its slow step forward.",
            "Flank behind Tonberry and strike with High Jump or elemental spells, then back out."
        ],
        "proTip": "Never stand directly in front of a Tonberry; circle behind it for safe critical hits."
    },
    "M10-2-2": {
        "targetName": "Tonberry",
        "encounterType": "Mission Boss",
        "threatRating": "Low",
        "summary": "Swarm of Tonberries in the cavern. Avoid getting cornered by multiple Chef's Knives at once.",
        "recommendedLoadout": {
            "materia": ["Darkness / Assault Twister", "High Jump", "Cura", "Barrier"],
            "accessories": ["Safety Bit", "Shinra Beta", "Muscle Belt"],
            "statTargets": "Rec Lv.20+ · HP 4,000+ · VIT 45 · SPR 45"
        },
        "weaknessesAndCounters": [
            "Slow walk speed lets you kite packs in circles and cleave them with Darkness or Assault Twister."
        ],
        "keyAttacksToWatch": [
            "Chef's Knife / Everyone's Grudge: High burst if two Tonberries stab together — keep moving."
        ],
        "killSteps": [
            "Kite the Tonberry group into a tight cluster.",
            "Drop AoE Darkness/Quake or High Jump in and roll back out.",
            "Pick off survivors from behind."
        ],
        "proTip": "Watch your mini-map corners so you don't back into a trailing Tonberry."
    },
    "M10-2-3": {
        "targetName": "Master Tonberry",
        "encounterType": "Mission Boss",
        "threatRating": "Moderate",
        "summary": "King of Tonberries with lethal Chef's Knife & Everyone's Grudge (plus optional Magic Pot encounters). Stay mobile!",
        "recommendedLoadout": {
            "materia": ["High Jump / Aerial Drain", "Costly Punch", "Curaga", "Wall"],
            "accessories": ["Safety Bit / Ribbon", "Adaman Bangle", "Brutal"],
            "statTargets": "Rec Lv.25+ · HP 8,000+ · VIT 65 · SPR 65"
        },
        "weaknessesAndCounters": [
            "Slow turning speed makes back-attacks easy; Aerial Drain / High Jump dodges Chef's Knife cleanly.",
            "Magic Pot can spawn in random encounters here — bring Jump, Fira, Gravity, and Assault Twister if hunting its DMW."
        ],
        "keyAttacksToWatch": [
            "Chef's Knife & Everyone's Grudge: Massive burst at close range — dodge behind him or use Jump i-frames."
        ],
        "killSteps": [
            "Apply Wall and kite Master Tonberry into open space.",
            "Bait his Chef's Knife lunge, roll behind him, and punish with High Jump/Costly Punch.",
            "Finish Master Tonberry to claim Tonberry's Knife and unlock Tonberry on your DMW."
        ],
        "proTip": "Clearing M10-2-3 awards Tonberry's Knife (Tonberry DMW). Don't attack Magic Pot if it appears — match its 4 skill requests!"
    },
}


ABILITY_COUNTERS: dict[str, str] = {
    "ultima": "Ultima (AoE non-elemental nuke): Keep Wall + high HP/SPR active and heal immediately with Curaga.",
    "flare": "Flare (Heavy non-elemental magic): Maintain MBarrier/Wall and sprint laterally during cast.",
    "energy": "Energy (Piercing non-elemental blasts): Sidestep continuously and counter during recovery.",
    "exaflare": "Exaflare (Massive beam finisher): Burst the Limit Gauge down or hold Wall + Phoenix Down.",
    "megaflare": "Megaflare (Dragon beam finisher): Break the Limit Gauge before cast completes or guard with Wall.",
    "judgment arrow": "Judgment Arrow (Dispels Auto-Raise + massive hit): Break gauge if possible and immediately re-pop Phoenix Down.",
    "graviga": "Graviga (% HP gravity nuke): Pair Safety Bit/Death ward or heal right away with Curaga.",
    "gravity": "Gravity (% HP damage): Keep HP topped up so follow-up hits aren't lethal.",
    "firaga": "Firaga (Heavy Fire AoE): Dodge out of the flame ring or equip Fire Armlet / Flame Armlet.",
    "tri-fire": "Tri-Fire (3x homing Fire): Roll diagonally through the gaps or wear Fire-absorbing gear.",
    "blizzaga": "Blizzaga (Ice burst): Dash clear of the frost ground telegraph; Ice-warding gear helps.",
    "thundaga": "Thundaga (Lightning strike): Keep moving or equip Thunder/Lightning Armlet.",
    "tri-thundaga": "Tri-Thundaga (Triple lightning orbs): Sprint laterally until all 3 bolts detonate.",
    "electrocute": "Electrocute (Multi-hit lightning field): Stay outside the electric ring with ranged/Jump attacks.",
    "self-destruct": "Self-Destruct (Kamikaze explosion): Burst down before low HP or dodge back / Aerial Drain to iframe.",
    "bad breath": "Bad Breath (Multi-status cone): Equip Ribbon, Super Ribbon, or Status Ward + Hell-aga.",
    "really bad breath": "Really Bad Breath (All-ailment + Stop): Mandatory Ribbon / Genji Shield / Status Ward + Hell-aga.",
    "nightmare breath": "Nightmare Breath (Status/heavy breath): Dodge behind the enemy or run Status Ward.",
    "silence gas": "Silence Gas (Inflicts Silence): Equip Status Ward, Esuna/Remedy, or rely on Command Materia (Punch/Jump).",
    "smoke vent": "Smoke Vent (Blind/status cloud): Flank behind the mech and stay out of frontal vents.",
    "anesthetic missile": "Anesthetic Missile (Stun/Stop risk): Dodge laterally and keep Status Ward/Ribbon on.",
    "anti-ap field": "Anti-AP Field (Drains AP): Lean on Magic/Costly Punch or carry Soma/Genji Helm.",
    "anti-mp field": "Anti-MP Field (Drains MP): Rely on Command Materia (Costly Punch/Aerial Drain) or Ethers.",
    "osmose": "Osmose (MP drain): Bring Ethers or 0-MP gear like Genji Helm.",
    "drain": "Drain (HP leech): Out-DPS with Costly Punch or interrupt with Battle Stance Strong Attack.",
    "curaga": "Curaga (Boss self-heal): Pressure relentlessly with Break Damage Limit so it cannot stall.",
    "cura": "Cura (Boss heal): Interrupt cast animations with Strong Attacks or Jump.",
    "wall": "Wall (Boss casts Barrier + MBarrier): Cast Dispel immediately or pierce it with Costly Punch / Buster Sword 47%+.",
    "barrier": "Barrier (Halves physical damage): Strip with Dispel, switch to Magic, or pierce with Costly Punch.",
    "mbarrier": "MBarrier (Halves magic damage): Strip with Dispel or switch to physical Command attacks.",
    "dispel": "Dispel (Removes Zack's Wall/Barrier): Reapply Wall right after getting hit.",
    "blast shot": "Blast Shot (Heavy shot + Stun/Silence): Roll sideways when cannon locks on.",
    "shinra type-100 cannon": "Shinra Type-100 Cannon (Heavy beam): Strafe behind the turret and punish the long cooldown.",
    "quintuple shot": "Quintuple Shot (5-hit gunfire): Guard with Buster Sword Stance or dodge behind cover.",
    "blood spiller": "Blood Spiller (Multi-slash): Guard or back-dash, then counter-hit.",
    "combo attack": "Combo Attack (Melee flurry): Block in Battle Stance or roll behind their back.",
    "drill attack": "Drill Attack (Spinning rush): Sidestep the charge line and attack the rear.",
    "1,000 needles": "1,000 Needles (Fixed 1,000 dmg): Keep HP > 1,500 and sidestep.",
    "10,000 needles": "10,000 Needles (Fixed 10,000 dmg): Break HP Limit (> 10k HP) or dodge/Jump.",
    "chef's knife": "Chef's Knife (Heavy close stab): Kite and strike only from behind.",
    "everyone's grudge": "Everyone's Grudge (Burst counter): Keep Wall up and avoid trading head-on.",
}


def _select_boss_targets(mission: dict[str, Any], enemy_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    boss_ids = list(dict.fromkeys(mission.get("bossEnemyIds") or []))
    if boss_ids:
        if mission["id"] == "M5-2-2" and "enemy_sephiroth" in boss_ids:
            boss_ids = ["enemy_sephiroth"] + [eid for eid in boss_ids if eid != "enemy_sephiroth"]
        return [enemy_by_id[eid] for eid in boss_ids if eid in enemy_by_id]

    rand_ids = list(dict.fromkeys(mission.get("randomEnemyIds") or []))
    cands = [enemy_by_id[eid] for eid in rand_ids if eid in enemy_by_id and eid != "enemy_magic_pot"]
    if not cands:
        cands = [enemy_by_id[eid] for eid in rand_ids if eid in enemy_by_id]
    if not cands:
        return []

    title_desc = f"{mission.get('title', '')} {mission.get('description', '')}".lower()
    named = [e for e in cands if len(e["name"]) >= 4 and e["name"].lower() in title_desc]
    if named:
        named.sort(key=lambda e: (e["stats"].get("hpHard") or 0, e["stats"].get("level") or 0), reverse=True)
        return named[:4]

    cands.sort(key=lambda e: (e["stats"].get("hpHard") or 0, e["stats"].get("level") or 0), reverse=True)
    top_hp = cands[0]["stats"].get("hpHard") or 0
    if mission["id"] in ("M1-1-3", "M1-1-4", "M1-1-5", "M1-1-6"):
        return cands[:2]
    same_tier = [e for e in cands if (e["stats"].get("hpHard") or 0) == top_hp]
    if len(same_tier) > 1:
        return same_tier[:4]
    return [cands[0]]


def _build_synthesized_boss_guide(
    mission: dict[str, Any],
    targets: list[dict[str, Any]],
    enemy_by_id: dict[str, dict[str, Any]],
    item_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    primary = targets[0]
    stars = mission.get("stars", 5)
    bm = mission.get("hardModeBenchmarks") or {}
    rec_lv = bm.get("recommendedLevel") or 1
    rec_hp = bm.get("hp") or 1500
    rec_vit = bm.get("vit") or 20
    rec_spr = bm.get("spr") or 20

    target_ids = [e["id"] for e in targets]
    target_name = (
        primary["name"]
        if len(targets) == 1
        else " + ".join(e["name"] for e in targets[:3]) + (f" (+{len(targets) - 3} more)" if len(targets) > 3 else "")
    )
    max_hp = max((e["stats"].get("hpHard") or 0) for e in targets)

    if mission["id"] == "M9-6-6":
        enc_type = "Superboss"
    elif mission["id"] in ("M1-1-3", "M1-1-4", "M1-1-5", "M1-1-6"):
        enc_type = "Endurance Gauntlet"
    elif mission["branch"] == "M5" or mission["id"] in ("M8-1-1", "M8-1-4", "M8-5-6", "M3-1-3", "M3-2-4", "M3-2-6", "M4-1-2"):
        enc_type = "Story Boss"
    elif len(targets) > 1:
        enc_type = "Multi-Target Boss"
    elif mission.get("bossEnemyIds"):
        enc_type = "Mission Boss"
    else:
        enc_type = "Primary Target"

    if stars >= 9 or max_hp >= 500000:
        threat = "Extreme"
    elif stars >= 7 or max_hp >= 180000:
        threat = "High"
    elif stars >= 4 or max_hp >= 40000:
        threat = "Moderate"
    else:
        threat = "Low"

    # Aggregate affinities & stats across target(s)
    weaks: list[str] = []
    avoid_elems: list[str] = []
    immunes: list[str] = []
    all_abilities: list[str] = []
    for e in targets:
        aff = e.get("affinities") or {}
        for w in aff.get("weak", []):
            if w not in weaks:
                weaks.append(w)
        for av in aff.get("absorb", []) + aff.get("null", []) + aff.get("resist", []):
            if av not in avoid_elems:
                avoid_elems.append(av)
        for im in aff.get("immune", []):
            if im not in immunes:
                immunes.append(im)
        for ab in e.get("abilities", []):
            if ab not in all_abilities:
                all_abilities.append(ab)

    p_stats = primary.get("stats") or {}
    p_vit = p_stats.get("vit") or 0
    p_spr = p_stats.get("spr") or 0

    weaknesses_counters: list[str] = []
    elem_spell_map = {
        "Fire": ("Fira / Firaga", "Fire"),
        "Ice": ("Blizzara / Blizzaga", "Ice"),
        "Lightning": ("Thundara / Thundaga", "Lightning"),
        "Water": ("Water / Watera", "Water"),
    }
    if weaks:
        recs = [f"{w} ({elem_spell_map.get(w, (w + ' Magic', w))[0]})" for w in weaks]
        weaknesses_counters.append(f"Elemental Weaknesses: Hit with {', '.join(recs)} for bonus damage and faster staggers.")
    else:
        weaknesses_counters.append("No elemental weaknesses — rely on non-elemental Command Materia or physical crits from behind.")

    if avoid_elems:
        weaknesses_counters.append(f"Elemental Warning: Resists/Absorbs/Nulls {', '.join(avoid_elems)} — keep those elements off your loadout.")

    if p_vit >= 90 and p_spr >= 90:
        weaknesses_counters.append(
            f"High Hard Mode Defenses (VIT {p_vit} / SPR {p_spr}): Use defense-ignoring Costly Punch, Graviga, or Buster Sword 47%+ Barrier Pierce."
        )
    elif p_vit > p_spr * 1.25 and p_vit >= 30:
        weaknesses_counters.append(
            f"Physical Tank (VIT {p_vit} vs SPR {p_spr}): Magic attacks (Firaga/Blizzaga/Electrocute/Energy) or Costly Punch outperform basic slashes."
        )
    elif p_spr > p_vit * 1.25 and p_spr >= 30:
        weaknesses_counters.append(
            f"Magic Resistant (SPR {p_spr} vs VIT {p_vit}): Physical Command Materia (High Jump, Aerial Drain, Assault Twister+, Battle Stance) hits hardest."
        )
    else:
        weaknesses_counters.append(
            f"Balanced Defenses (VIT {p_vit} / SPR {p_spr}): Back-attacks with Battle Stance Strong Attack or your highest-stat Materia melt HP cleanly."
        )

    if "Stop" not in immunes and stars <= 8:
        weaknesses_counters.append("Not listed as Stop-immune: Stop Blade or Hell-aga Materia can lock the target in place.")
    elif "Death" not in immunes and stars <= 7 and not mission.get("bossEnemyIds"):
        weaknesses_counters.append("Not Death-immune: Hell Firaga / Hell Blizzaga / Hell Thundaga (+ Status Strike) can trigger instant-kill procs.")
    elif immunes:
        weaknesses_counters.append(f"Status/Effect Immunities: {', '.join(immunes[:6])}.")

    # Key attacks
    attacks_watch: list[str] = []
    has_status_hazard = False
    has_buff_hazard = False
    for ab in all_abilities:
        low_ab = ab.lower()
        if any(k in low_ab for k in ("breath", "silence", "smoke", "anesthetic", "poison", "stop", "stun", "death")):
            has_status_hazard = True
        if any(k in low_ab for k in ("wall", "barrier", "mbarrier", "curaga", "cura")):
            has_buff_hazard = True
        matched = ABILITY_COUNTERS.get(low_ab)
        if matched and matched not in attacks_watch:
            attacks_watch.append(matched)
        elif len(attacks_watch) < 4:
            attacks_watch.append(f"{ab}: Watch the windup animation, dodge diagonally behind {primary['name']}, and punish recovery.")
        if len(attacks_watch) >= 4:
            break
    if not attacks_watch:
        attacks_watch.append(
            f"Standard {primary['family']} melee & ranged volleys: Guard in Battle Stance or roll behind {primary['name']} before countering."
        )

    # Star-scaled Materia & Accessories
    if stars <= 2:
        mat_list = ["Cure / Cura", "Barrier", "Assault Twister", "Libra"]
        acc_list = ["Bronze Bangle", "Earrings / Muscle Belt"]
        opener = "Cast Barrier if needed, lock on, and circle behind the target."
        damage_loop = "Weave Battle Stance Strong Attacks and Assault Twister into the enemy's back for guaranteed crits."
    elif stars <= 4:
        mat_list = ["Cura", "Barrier / Wall", "High Jump", "Assault Twister"]
        acc_list = ["Shinra Beta", "Muscle Belt", "Earrings"]
        opener = "Open with Barrier (or Wall) so Hard Mode hits stay manageable."
        damage_loop = "Use High Jump to dodge telegraphed swings and follow with Battle Stance or elemental weakness spells."
    elif stars <= 6:
        mat_list = ["Curaga", "Wall", "High Jump / Aerial Drain", "Darkness"]
        acc_list = ["Adaman Bangle (or Platinum Bangle)", "Shinra Alpha", "Force Bracelet / Champion Belt"]
        opener = "Cast Wall right away and equip Break HP Limit (Adaman Bangle from M7-3-6) if available."
        damage_loop = "Clear surrounding adds with Darkness/Quake, then focus the boss with Aerial Drain or High Jump back-attacks."
    elif stars <= 8:
        mat_list = ["Costly Punch", "Aerial Drain", "Curaga", "Wall", "Mug"]
        acc_list = ["Adaman Bangle", "Brutal", "Ziedrich / Shinra Alpha", "Brigand's Gloves"]
        opener = "Apply Wall (and Phoenix Down for safety) before closing in."
        damage_loop = "Flank behind the target and loop Costly Punch (99,999 dmg w/ Brutal) and Aerial Drain for invincibility + full heals."
    else:
        mat_list = ["Costly Punch", "Aerial Drain", "Curaga", "Wall", "Mug"]
        acc_list = ["Adaman Bangle", "Genji Glove / Brutal", "Genji Shield / Super Ribbon", "Genji Helm / Ziedrich"]
        opener = "Pop Phoenix Down (Auto-Raise) + Wall at second zero — 9–10★ Hard Mode enemies can spike 20k+ damage."
        damage_loop = "Stay behind the boss, dodge heavy casts laterally, and loop Costly Punch + Aerial Drain until HP hits zero."

    if weaks:
        spell_rec = elem_spell_map.get(weaks[0], (f"{weaks[0]} Magic", weaks[0]))[0]
        if spell_rec not in mat_list:
            mat_list.insert(2, spell_rec)
    if has_status_hazard:
        if "Status Ward" not in mat_list:
            mat_list.append("Status Ward")
        if stars >= 5 and not any("Ribbon" in a for a in acc_list):
            acc_list.append("Ribbon / Super Ribbon")
    if has_buff_hazard and "Dispel" not in mat_list:
        mat_list.append("Dispel")

    kill_steps = [
        f"Prep & Opener: {opener}",
        f"Core Kill Loop: {damage_loop}",
        f"Counter Hazards: {attacks_watch[0]}",
    ]
    if len(targets) > 1:
        kill_steps.append(
            f"Multi-Target Priority: Focus down one target at a time (starting with {primary['name']} or any healer/support unit) to stop crossfire."
        )

    # Check notable loot or Magic Pot spawn for step 4 / Pro Tip
    all_mission_eids = set((mission.get("bossEnemyIds") or []) + (mission.get("randomEnemyIds") or []))
    rare_steal_id = (primary.get("loot") or {}).get("rareSteal")
    rare_drop_id = (primary.get("loot") or {}).get("rareDrop")
    rare_steal_name = item_by_id[rare_steal_id]["name"] if rare_steal_id in item_by_id else None
    rare_drop_name = item_by_id[rare_drop_id]["name"] if rare_drop_id in item_by_id else None

    if "enemy_magic_pot" in all_mission_eids and mission["id"] != "M7-6-6":
        pro_tip = "Bonus Magic Pot spawns in random encounters here! Don't kill it — perform its 4 requested skills/spells to earn rare rewards."
    elif rare_steal_name:
        pro_tip = f"{primary['name']} carries {rare_steal_name} as a Rare Steal — weave a Mug (w/ Brigand's Gloves + Mog's Amulet) before landing the killing blow."
    elif rare_drop_name:
        pro_tip = f"Equip Mog's Amulet (Sector 7 Shop, M4-4-3) to guarantee {primary['name']}'s Rare Drop: {rare_drop_name}."
    elif stars >= 7:
        pro_tip = "Raise Buster Sword Proficiency to 23% (Break Damage Limit) and 47% (Barrier Pierce) so Battle Stance slices straight through Hard Mode guards."
    else:
        pro_tip = "Use Buster Sword Battle Stance + Perfect Guard on telegraphed hits to build Proficiency while dealing heavy counter damage."

    summary = (
        f"Defeat {target_name} (Lv.{p_stats.get('level') or '?'}, {max_hp:,} Hard HP). "
        + (f"Weak to {', '.join(weaks)}. " if weaks else "No elemental weakness; ")
        + (f"Watch for {all_abilities[0]}." if all_abilities else "Flank from behind and punish recovery.")
    )

    return {
        "targetName": target_name,
        "targetEnemyIds": target_ids,
        "encounterType": enc_type,
        "threatRating": threat,
        "summary": summary,
        "recommendedLoadout": {
            "materia": mat_list[:6],
            "accessories": acc_list[:4],
            "statTargets": f"Rec Lv.{rec_lv} · HP {rec_hp:,} · VIT {rec_vit} · SPR {rec_spr}",
        },
        "weaknessesAndCounters": weaknesses_counters,
        "keyAttacksToWatch": attacks_watch,
        "killSteps": kill_steps,
        "proTip": pro_tip,
    }


def attach_mission_boss_guides(
    missions: list[dict[str, Any]],
    enemies: list[dict[str, Any]],
    items: dict[str, dict[str, Any]],
) -> None:
    enemy_by_id = {e["id"]: e for e in enemies}
    for m in missions:
        targets = _select_boss_targets(m, enemy_by_id)
        if not targets:
            raise RuntimeError(f"Mission {m['id']} has no enemies to build bossGuide")
        synth = _build_synthesized_boss_guide(m, targets, enemy_by_id, items)
        curated = CURATED_BOSS_GUIDES.get(m["id"])
        if curated:
            guide = {
                "targetName": curated["targetName"],
                "targetEnemyIds": curated.get("targetEnemyIds") or synth["targetEnemyIds"],
                "encounterType": curated["encounterType"],
                "threatRating": curated["threatRating"],
                "summary": curated["summary"],
                "recommendedLoadout": curated["recommendedLoadout"],
                "weaknessesAndCounters": curated["weaknessesAndCounters"],
                "keyAttacksToWatch": curated["keyAttacksToWatch"],
                "killSteps": curated["killSteps"],
                "proTip": curated["proTip"],
            }
        else:
            guide = synth
        m["bossGuide"] = guide
        if not m["bossEnemyIds"] and guide.get("targetEnemyIds"):
            m["bossEnemyIds"] = list(guide["targetEnemyIds"])
            m["randomEnemyIds"] = [eid for eid in m.get("randomEnemyIds", []) if eid not in m["bossEnemyIds"]]
            for beid in m["bossEnemyIds"]:
                en = enemy_by_id.get(beid)
                if not en:
                    continue
                existing_sp = next((sp for sp in en["spawns"] if sp["missionId"] == m["id"]), None)
                if existing_sp:
                    existing_sp["role"] = "boss"
                else:
                    en["spawns"].append({"missionId": m["id"], "role": "boss"})


def build_guides_json() -> dict[str, Any]:
    return {
        "levelBrackets": [
            {
                "id": "lv_1_15",
                "label": "Lv. 1–15 (Ch. 1–3 Early Story)",
                "minLevel": 1,
                "maxLevel": 15,
                "benchmarks": {
                    "hp": "1,200 – 3,500",
                    "vit": "15 – 40",
                    "spr": "15 – 40",
                    "gear": "Bronze/Iron Bangle, Barrier, Cura, Assault Twister, Battle Stance Perfect Guard",
                },
                "priorityMissions": ["M1-1-1", "M1-2-1", "M1-2-3", "M3-1-1", "M4-1-1", "M6-1-1", "M8-1-1"],
                "expRoute": "Clear M1-1-x, M3-1-x, and M4-1-x branches. Use Battle Stance Strong Attack & Perfect Guard in M1-2-1 to start building Buster Sword Proficiency.",
                "spGilRoute": "Sell duplicate bangles; open M6-1-x chests for Phoenix Downs and Hi-Potions. Join all 3 Fan Clubs in Ch. 2/3.",
                "fusionFocus": "Hold onto Potions and Mako Stones until Chapter 4 when M7-2-1 unlocks Item Fusion.",
            },
            {
                "id": "lv_15_25",
                "label": "Lv. 15–25 (Ch. 4–5 Midgame Pivot)",
                "minLevel": 15,
                "maxLevel": 25,
                "benchmarks": {
                    "hp": "4,000 – 9,999",
                    "vit": "45 – 85",
                    "spr": "45 – 85",
                    "gear": "4 Accessory Slots (M7-2-2 & M7-2-5), Item Fusion Tome (M7-2-1), Mog's Amulet (M4-4-3)",
                },
                "priorityMissions": ["M4-4-3", "M7-2-1", "M7-2-2", "M7-2-5", "M6-2-1", "M6-2-3", "M8-2-1", "M8-3-2"],
                "expRoute": "Push M3-2-x (M3-2-2 G Bladers = 720 Gil & 665 EXP), M5-1-6 Angeal Penance (4,711 EXP / 3k SP / 4k Gil), and M8-3-2 for free Status Ward. Interrupt Skill Power gauges in Battle Stance.",
                "spGilRoute": "Farm M3-2-2 G Bladers (720 Gil + Drainra/Osmose steals to SP-convert) and M5-1-6 Angeal Penance (4,000 Gil / 3,000 SP). Once ready for 6★ M4-4-3, grab Sector 7 Shop and buy Mog's Amulet + Brigand's Gloves (10,000 Gil each).",
                "fusionFocus": "Unlock Item Fusion Tome (M7-2-1). Buy HP Up (Sec. 8 Shop M6-2-1) and stack HP% using cheap 50 Gil Shinra Shop Potions.",
            },
            {
                "id": "lv_25_40",
                "label": "Lv. 25–40 (Ch. 6–7 Break Limit Era)",
                "minLevel": 25,
                "maxLevel": 40,
                "benchmarks": {
                    "hp": "15,000 – 35,000",
                    "vit": "90 – 150",
                    "spr": "90 – 150",
                    "gear": "Adaman Bangle (M7-3-6), Brutal (M7-4-6), Status Ward (M8-3-2) + Darkness/Death, Buster Sword 23%+ (Damage Break)",
                },
                "priorityMissions": ["M1-5-6", "M5-2-3", "M7-3-6", "M7-4-6", "M7-5-3", "M8-4-4", "M8-5-2", "M10-2-3"],
                "expRoute": "Farm M1-5-6 Guardian Eyes (8,083 EXP) or M5-2-3 Hollander (9,977 EXP); clear M7-4-6 for Brutal (Break Damage Limit) and hit 23% Buster Sword Proficiency.",
                "spGilRoute": "Farm M8-5-2 Mover (2,000 SP + 2–3x no-damage kill chain!) and M5-2-3 Hollander (3,000 Gil + Dark Matter steals). Unlock Bone Village Outlet in M7-5-3.",
                "fusionFocus": "Unlock Moogle Power (M8-4-4) and run M1-1-1 AFK mastering. Wrap up ALL Midgar missables before ending Chapter 7!",
            },
            {
                "id": "lv_40_60",
                "label": "Lv. 40–60 (Ch. 8–9 Cavern & Stat Maxing)",
                "minLevel": 40,
                "maxLevel": 60,
                "benchmarks": {
                    "hp": "40,000 – 75,000",
                    "vit": "160 – 220",
                    "spr": "160 – 220",
                    "gear": "Costly Punch, Aerial Drain, Wall, Jeweled Ring + Mog's Amulet, Buster Sword 47%+ (Barrier Pierce)",
                },
                "priorityMissions": ["M6-6-3", "M8-6-4", "M9-1-1", "M9-2-6", "M9-5-3", "M9-5-4"],
                "expRoute": "M8-6-4 (Scissor Chitins) or M9-5-x corridors with Costly Punch + Hell Blizzaga.",
                "spGilRoute": "M9-5-3 (Three Stars) for 20,000+ SP/kill & high Gil; M6-6-3 Lesser Worms for Dark Matter. Grab Research Dept. QMC+ in Ch. 9 Gongaga!",
                "fusionFocus": "Use the Dark Matter 98/980% Libra conversion loop to push VIT, SPR, ATK/MAG, and HP% toward endgame caps.",
            },
            {
                "id": "lv_60_99",
                "label": "Lv. 60–99 (Minerva & 10★ Endgame)",
                "minLevel": 60,
                "maxLevel": 99,
                "benchmarks": {
                    "hp": "99,999",
                    "vit": "255",
                    "spr": "255",
                    "gear": "Genji Helm, Genji Armor, Genji Shield, Genji Glove, Ziedrich / Divine Slayer",
                },
                "priorityMissions": ["M9-5-3", "M9-5-4", "M9-6-4", "M7-6-6", "M9-6-5", "M9-6-6"],
                "expRoute": "M8-6-4 (Scissor Chitins) or M9-6-4 / M9-6-5 encounters with Costly Punch for fast Lv. 99.",
                "spGilRoute": "M9-5-3 Three Stars (SP/Gil) + Mug Minerva in M9-6-6 for 99 Phoenix Downs (use or sell for 495,000 Gil/run).",
                "fusionFocus": "Finalize 4–6 endgame Materia (Costly Punch +999% HP, Aerial Drain +100 VIT, Curaga +100 SPR, Wall/Mug/SP Master).",
            },
        ],
        "farmingMatrix": [
            {"stage": "early", "category": "EXP", "resource": "Early EXP & Mako Stones (1–2★)", "bestMissionId": "M10-4-2", "enemyId": "enemy_sea_worm", "itemId": "item_mag_mako_stone", "setup": "Bronze Bangle + Assault Twister + Cura", "method": "Sea Worm (M10-4-2, 177 EXP), Guard Spider (M3-1-2, 162 EXP), and Ifrit (M5-1-1, 162 EXP) feed fast early DMW levels.", "yield": "162–177 EXP / kill"},
            {"stage": "early", "category": "SP & Gil", "resource": "Early Gil & Sellable Gear (1–2★)", "bestMissionId": "M5-1-1", "enemyId": "enemy_ifrit", "itemId": "item_wrist_band", "setup": "Bronze Bangle + Blizzard + Cura (zero farming gear)", "method": "Clear Ifrit (M5-1-1, 180 Gil) or Guard Spider (M3-1-2, 120 Gil); sell duplicate M6-1-x chest bangles/vests.", "yield": "120–180 Gil + Chests"},
            {"stage": "early", "category": "SP & Gil", "resource": "Early SP & Materia Convert (1–2★)", "bestMissionId": "M5-1-1", "enemyId": "enemy_ifrit", "itemId": "item_atk_up", "setup": "Convert unwanted duplicate Materia into SP", "method": "Vajradhara Tai/Wu (M4-1-2, 80 SP), A-Ahriman (M5-1-3, 80 SP), Ifrit (M5-1-1, 162 SP), plus Materia-to-SP conversion.", "yield": "80–162 SP / kill"},
            {"stage": "early-mid", "category": "SP & Gil", "resource": "Early-Mid Gil Farm (3–4★)", "bestMissionId": "M3-2-2", "enemyId": "enemy_g_blader", "itemId": "item_drainra", "setup": "Assault Twister + Barrier + Cura", "method": "G Blader (M3-2-2 / M3-2-3, 720 Gil + Drainra), G Smasher (M3-2-1, 640 Gil), Master Tonberry (M10-2-3, 1,000 Gil).", "yield": "640–1,000 Gil / kill"},
            {"stage": "early-mid", "category": "EXP", "resource": "All-in-One 4★ Jackpot Boss", "bestMissionId": "M5-1-6", "enemyId": "enemy_angeal_penance", "itemId": "item_lightning_armlet", "setup": "Barrier + Cura + Assault Twister (Skill Power breaks)", "method": "Angeal Penance in M5-1-6 drops massive early-mid EXP, SP, and Gil simultaneously.", "yield": "4,711 EXP · 3k SP · 4k Gil"},
            {"stage": "early-mid", "category": "SP & Gil", "resource": "Early-Mid SP Farm (4★)", "bestMissionId": "M10-1-3", "enemyId": "enemy_kactuer", "itemId": "item_gold_armlet", "setup": "Assault Twister + Safety Bit (in M10-1-3 chest)", "method": "Kactuer gives 800 SP + sellable Silver/Gold Armlets; Bahamut (M5-1-2) gives 408 SP.", "yield": "800–3,000 SP / kill"},
            {"stage": "mid-late", "category": "EXP", "resource": "Mid-Late Fast EXP (5–7★)", "bestMissionId": "M1-5-6", "enemyId": "enemy_guardian_eyes", "itemId": "item_shinra_beta_plus", "setup": "Wall / Barrier + Curaga + Lightning/Gravity", "method": "Guardian Eyes (M1-5-6, 8,083 EXP) or Tarantula (M1-5-3, 6,380 EXP) level Zack smoothly past Lv. 40.", "yield": "6,380–8,083 EXP / kill"},
            {"stage": "mid-late", "category": "SP & Gil", "resource": "Mid-Late Gil + Early Dark Matter (6★)", "bestMissionId": "M5-2-3", "enemyId": "enemy_hollander", "itemId": "item_dark_matter", "setup": "Mug (M1-1-6) + Brigand's Gloves + Mog's Amulet (M4-4-3)", "method": "Hollander in M5-2-3 yields 3,000 Gil, 1,780 SP, 9,977 EXP, AND Dark Matter steals before 8★!", "yield": "3,000 Gil + Dark Matter"},
            {"stage": "mid-late", "category": "SP & Gil", "resource": "Mid-Late Mover SP Chain (6★)", "bestMissionId": "M8-5-2", "enemyId": "enemy_mover", "itemId": "item_hypno_crown", "setup": "Wall + Strong AoE (kill adds BEFORE Mover, no damage taken)", "method": "Mover gives 2,000 SP base; defeating adds first without taking damage multiplies SP 2x–3x!", "yield": "2,000–6,000 SP / fight"},
            {"stage": "endgame", "category": "EXP", "resource": "Fast EXP (Endgame 9–10★)", "bestMissionId": "M8-6-4", "enemyId": "enemy_scissor_chitin", "itemId": "item_costly_punch", "setup": "Costly Punch + Brutal/Genji Glove + Wall", "method": "Clear Scissor Chitins in M8-6-4 (5,460 EXP) or Goliath in M9-6-5 (23,264 EXP) / Great Malboro in M9-6-4 (31,936 EXP).", "yield": "5,460–31,936 EXP / kill"},
            {"stage": "endgame", "category": "SP & Gil", "resource": "Top Endgame Gil (Holy Tonberry)", "bestMissionId": "M9-6-2", "enemyId": "enemy_holy_tonberry", "itemId": "item_gold_rolling_pin", "setup": "Precious Watch + Brigand's Gloves + Jeweled Ring + Mug", "method": "Holy Tonberry gives 20,000 Gil (40k w/ Precious Watch) + Gold Rolling Pin rare steal (sells 50,000 Gil!).", "yield": "70,000–90,000 Gil / kill"},
            {"stage": "endgame", "category": "SP & Gil", "resource": "Top Speed SP & Gil (Three Stars)", "bestMissionId": "M9-5-3", "enemyId": "enemy_three_stars", "itemId": "item_mogs_amulet", "setup": "Mog's Amulet + Jeweled Ring + Precious Watch + Mug", "method": "Farm Three Stars (20,000 SP) & Tycoon in M9-5-3; sell Mythril Armlets & SP-convert stolen Tri-Thundaga.", "yield": "20,000+ SP + 50k+ Gil/min"},
            {"stage": "endgame", "category": "SP & Gil", "resource": "8★ SP + Dark Matter Combo", "bestMissionId": "M6-6-3", "enemyId": "enemy_mover_ex", "itemId": "item_flare", "setup": "Mog's Amulet + Brigand's Gloves + Mug + Costly Punch", "method": "Farm Mover EX (8,000 SP + Flare steal worth ~10.5k SP) & Lesser Worms (Dark Matter) in M6-6-3.", "yield": "8,000–24,000 SP + Dark Matter"},
            {"stage": "endgame", "category": "SP & Gil", "resource": "99x Phoenix Down / Gil", "bestMissionId": "M9-6-6", "enemyId": "enemy_minerva", "itemId": "item_phoenix_down", "setup": "Mug + Brigand's Gloves + Wall + 99,999 HP", "method": "Mug Minerva once per attempt to steal 99x Phoenix Downs (keep or sell for 495k Gil).", "yield": "99 Phoenix Downs / run"},
            {"stage": "endgame", "category": "Fusion Stats", "resource": "Dark Matter (MAG +1)", "bestMissionId": "M6-6-3", "enemyId": "enemy_lesser_worm", "itemId": "item_dark_matter", "setup": "Mog's Amulet (Sector 7 Shop M4-4-3) + Jeweled Ring", "method": "Common drop from Lesser Worms; fastest base for 98/980% Libra conversion.", "yield": "1–2 Dark Matter / fight"},
            {"stage": "endgame", "category": "Fusion Stats", "resource": "Fat Chocobo Feather (HP +10%)", "bestMissionId": "M9-2-6", "enemyId": "enemy_jabberwock", "itemId": "item_fat_chocobo_feather", "setup": "Mog's Amulet + Brigand's Gloves + Mug", "method": "Steal/Rare Drop from Jabberwock (M9-2-6) or Humbaba (M6-6-6); or stack HP% early with Shinra Potions.", "yield": "1–3 Feathers / fight"},
            {"stage": "endgame", "category": "Fusion Stats", "resource": "Adamantite (VIT +1)", "bestMissionId": "M9-6-5", "enemyId": "enemy_goliath", "itemId": "item_adamantite", "setup": "Mug + Brigand's Gloves + Mog's Amulet", "method": "Drop & Common Steal from Goliath in M9-6-5 (also Crazy Sword in M7-6-4/M9-4-1 & Grandpanzer in M9-3-3).", "yield": "1+ Adamantite / fight"},
            {"stage": "mid-late", "category": "Fusion Stats", "resource": "Mythril (SPR +1)", "bestMissionId": "M7-3-5", "enemyId": "enemy_g_paladin", "itemId": "item_mythril", "setup": "Mug + Brigand's Gloves + Mog's Amulet", "method": "Rare Steal from G Paladin (M7-3-5, 7★), Common Steal from Mover EX (M6-6-3, 8★), or G Purgatorio (M3-4-6, 9★).", "yield": "1+ Mythril / fight"},
            {"stage": "endgame", "category": "Fusion Stats", "resource": "Hero Drink (ATK +1)", "bestMissionId": "M9-6-3", "enemyId": "enemy_master_blade", "itemId": "item_hero_drink", "setup": "Mog's Amulet + Brigand's Gloves + Mug", "method": "Rare Drop & Steal from Master Blade (M9-6-3) or Rare Steal from Iron Claw (M6-5-6 / M9-3-6).", "yield": "1+ Hero Drink / fight"},
            {"stage": "endgame", "category": "Fusion Stats", "resource": "Gysahl Greens (LCK +1) / Zeio Nut / Lunar Harp", "bestMissionId": "M9-5-5", "enemyId": None, "itemId": "item_gysahl_greens", "setup": "M9-6-x chests + Dark Matter 98 conversion", "method": "Convert a +98 Dark Matter Libra with 1x Gysahl Greens, Zeio Nut, or Lunar Harp instead of farming 99x.", "yield": "1 catalyst converts +98!"},
            {"stage": "mid-late", "category": "Reunion Systems", "resource": "Materia Mastering (AFK Loop)", "bestMissionId": "M1-1-1", "enemyId": "enemy_sentry", "itemId": "item_moogle_power", "setup": "1–2 Mastered Moogle Power (M8-4-4) + Faerie Ring", "method": "Sit in M1-1-1 with weak troopers; DMW reels spin nonstop and Moogle Power levels all 6 slots.", "yield": "Masters all 6 slots AFK"},
            {"stage": "early-mid", "category": "Reunion Systems", "resource": "Buster Sword Proficiency 100%", "bestMissionId": "M1-2-1", "enemyId": None, "itemId": None, "setup": "Battle Stance + M1-2-1 (Guards) + M1-1-3 (Kills)", "method": "M1-2-1 gunfire for Perfect Guard (31.66%), M1-1-3 for Strong Attack & Command Kills (63.3%), M9-6-5 for Barrier Pierce (5%).", "yield": "Damage Break @ 23% / Barrier Pierce @ 47%"},
            {"stage": "endgame", "category": "Reunion Systems", "resource": "DMW 100% (Genji Armor)", "bestMissionId": "M1-1-1", "enemyId": None, "itemId": "item_genji_armor", "setup": "Equip QMC+/Shade DMW Materia + Faerie Ring", "method": "Equip character/summon boost Materia (Octaslash, Healing Wave, etc.) and AFK in M1-1-1 until 100%.", "yield": "Unlocks Genji Armor"},
        ],
        "dmwImages": [
            {"id": "dmw_zack", "name": "Zack", "group": "Character", "limitBreak": "Chain Slash", "unlockCondition": "Story (Default)", "missionId": None, "missable": False, "boostMateriaId": None},
            {"id": "dmw_sephiroth", "name": "Sephiroth", "group": "Character", "limitBreak": "Octaslash", "unlockCondition": "Story (Chapter 1)", "missionId": None, "missable": False, "boostMateriaId": "item_octaslash"},
            {"id": "dmw_angeal", "name": "Angeal", "group": "Character", "limitBreak": "Rush Assault", "unlockCondition": "Story (Chapter 1)", "missionId": None, "missable": False, "boostMateriaId": "item_rush_assault"},
            {"id": "dmw_tseng", "name": "Tseng", "group": "Character", "limitBreak": "Air Strike", "unlockCondition": "Story (Chapter 2)", "missionId": None, "missable": False, "boostMateriaId": "item_air_strike"},
            {"id": "dmw_cloud", "name": "Cloud", "group": "Character", "limitBreak": "Meteor Shots", "unlockCondition": "Story (Chapter 4)", "missionId": None, "missable": False, "boostMateriaId": "item_meteor_shots"},
            {"id": "dmw_aerith", "name": "Aerith", "group": "Character", "limitBreak": "Healing Wave", "unlockCondition": "Story (Chapter 4)", "missionId": None, "missable": False, "boostMateriaId": "item_healing_wave"},
            {"id": "dmw_cissnei", "name": "Cissnei", "group": "Character", "limitBreak": "Lucky Stars", "unlockCondition": "Story (Chapter 5)", "missionId": None, "missable": False, "boostMateriaId": "item_lucky_stars"},
            {"id": "dmw_ifrit", "name": "Ifrit", "group": "Summon", "limitBreak": "Hellfire", "unlockCondition": "Clear Mission M8-1-1 (Rematch with Ifrit)", "missionId": "M8-1-1", "missable": False, "boostMateriaId": "item_hellfire"},
            {"id": "dmw_bahamut", "name": "Bahamut", "group": "Summon", "limitBreak": "Megaflare", "unlockCondition": "Clear Mission M8-1-4 (Rematch with Bahamut)", "missionId": "M8-1-4", "missable": False, "boostMateriaId": "item_megaflare"},
            {"id": "dmw_odin", "name": "Odin", "group": "Summon", "limitBreak": "Zantetsuken", "unlockCondition": "Clear Mission M8-1-6 (Mystery Materia)", "missionId": "M8-1-6", "missable": False, "boostMateriaId": "item_zantetsuken"},
            {"id": "dmw_phoenix", "name": "Phoenix", "group": "Summon", "limitBreak": "Rebirth Flame", "unlockCondition": "MISSABLE: Chapter 8 Nibelheim Seven Wonders #1 — inspect the Water Tower after talking to the boy.", "missionId": None, "missable": True, "boostMateriaId": "item_rebirth_flame"},
            {"id": "dmw_bahamut_fury", "name": "Bahamut Fury", "group": "Summon", "limitBreak": "Exaflare", "unlockCondition": "Clear Mission M8-5-6 (Treasure Info 6)", "missionId": "M8-5-6", "missable": False, "boostMateriaId": "item_exaflare"},
            {"id": "dmw_chocobo", "name": "Chocobo", "group": "Chocobo Mode", "limitBreak": "Chocobo Stomp", "unlockCondition": "Clear Mission M8-4-1 (Suspicious Mail 1)", "missionId": "M8-4-1", "missable": False, "boostMateriaId": "item_chocobo_stomp"},
            {"id": "dmw_cactuar", "name": "Cactuar", "group": "Chocobo Mode", "limitBreak": "1,000 Needles", "unlockCondition": "Defeat Cactuar in M3-1-3, then clear M10-1-3 (Cactuar Found?)", "missionId": "M10-1-3", "missable": False, "boostMateriaId": "item_1000_needles"},
            {"id": "dmw_tonberry", "name": "Tonberry", "group": "Chocobo Mode", "limitBreak": "Murderous Thrust", "unlockCondition": "Defeat Tonberry in M6-1-5, then clear M10-2-3 (Master Tonberry)", "missionId": "M10-2-3", "missable": False, "boostMateriaId": "item_murderous_thrust"},
            {"id": "dmw_cait_sith", "name": "Cait Sith", "group": "Chocobo Mode", "limitBreak": "Courage Boost!", "unlockCondition": "Clear Mission M8-4-3 (Suspicious Mail 3)", "missionId": "M8-4-3", "missable": False, "boostMateriaId": "item_courage_boost"},
            {"id": "dmw_moogle", "name": "Moogle", "group": "Chocobo Mode", "limitBreak": "Moogle Power", "unlockCondition": "Clear Mission M8-4-4 (Suspicious Mail 4)", "missionId": "M8-4-4", "missable": False, "boostMateriaId": "item_moogle_power"},
            {"id": "dmw_magic_pot", "name": "Magic Pot", "group": "Chocobo Mode", "limitBreak": "Item Mugger", "unlockCondition": "Satisfy Magic Pot in M10-2-3 (Jump -> Fira -> Gravity -> Assault Twister)", "missionId": "M10-2-3", "missable": False, "boostMateriaId": "item_item_mugger"},
        ],
        "missablesByChapter": EXPANDED_MISSABLES,
        "sections": [
            {
                "id": "guide_exp_leveling",
                "title": "1. EXP & Leveling Guide (All Stages: Lv. 1–99)",
                "badge": "Leveling",
                "summary": "Early, Mid, and Endgame EXP routes (Sea Worm -> Angeal Penance -> Guardian Eyes -> Scissor Chitin/Goliath).",
                "refs": {"missions": ["M10-4-2", "M5-1-6", "M1-5-6", "M8-6-4", "M9-6-4"], "items": ["item_assault_twister", "item_status_ward", "item_hell_blizzaga", "item_costly_punch"]},
                "blocks": [
                    {"heading": "Early to Early-Mid (1–4★ · Lv. 1–28)", "body": "Crisis Core ties level-ups to hidden EXP + DMW 7-7-7 rolls. Early on, hunt Sea Worm (M10-4-2, 177 EXP), Guard Spider (M3-1-2, 162 EXP), and Ifrit (M5-1-1). By 3–4★, repeat Angeal Penance (M5-1-6, 4,711 EXP) or General's Tank (M3-2-3, 918 EXP), and clear M8-3-2 for free Status Ward. NEVER abandon a mission or earned EXP is lost!"},
                    {"heading": "Mid-Late to Endgame (5–10★ · Lv. 28–99)", "body": "In 5–7★, farm Guardian Eyes (M1-5-6, 8,083 EXP) or Hollander (M5-2-3, 9,977 EXP) and clear M7-4-6 (Wyerd, 5,966 EXP) for Brutal. At 8–10★, farm G Dominator (M7-4-5, 7,770 EXP), Scissor Chitins (M8-6-4, 5,460 EXP fast loop), Goliath (M9-6-5, 23,264 EXP), and Great Malboro (M9-6-4, 31,936 EXP)."},
                ],
            },
            {
                "id": "guide_sp_gil",
                "title": "2. All-Stage SP & Gil Farming Guide (Early → Endgame)",
                "badge": "Economy",
                "summary": "How to earn Gil and SP BEFORE Sector 7/Online Shop Shade (M5-1-1, M3-2-2, M5-1-6, M10-1-3, M5-2-3, M8-5-2, M9-5-3, M9-6-2).",
                "refs": {"missions": ["M5-1-1", "M3-2-2", "M5-1-6", "M10-1-3", "M4-4-3", "M5-2-3", "M8-5-2", "M9-5-3", "M9-6-2", "M9-6-6"], "items": ["item_mogs_amulet", "item_brigands_gloves", "item_precious_watch", "item_jeweled_ring", "item_gold_rolling_pin", "item_phoenix_down"]},
                "blocks": [
                    {"heading": "Early & Early-Mid Economy (1–4★ · No Farming Accessories Yet)", "body": "Before unlocking Sector 7 Shop (M4-4-3, 6★), farm Ifrit (M5-1-1, 180 Gil / 162 SP), G Bladers in M3-2-2 (720 Gil + Drainra/Osmose steals you can SP-convert!), Kactuer in M10-1-3 (800 SP + Silver/Gold Armlets), and Angeal Penance in M5-1-6 (4,000 Gil & 3,000 SP per clear). Convert duplicate Materia for instant early SP!"},
                    {"heading": "Mid-Late Mover Chains & Endgame Breaks (5–10★)", "body": "At 6★, grab Mog's Amulet & Brigand's Gloves (M4-4-3) + Mug (M1-1-6), farm Hollander (M5-2-3, 3k Gil + Dark Matter), and hunt Mover (M8-5-2, 2k SP) killing adds first without taking damage for Reunion's 2x–3x SP Chain multiplier. Endgame: Three Stars (M9-5-3, 20k SP), Holy Tonberry (M9-6-2, 20k Gil + 50k Gold Rolling Pin steal), and Minerva 99x Phoenix Downs (M9-6-6)."},
                ],
            },
            {
                "id": "guide_fusion_pipelines",
                "title": "3. Stat Fusion Material Farming & 98/980% Pipeline",
                "badge": "Stat Maxing",
                "summary": "Reunion changes (no repeat clear rewards), M7-2-1 Item Fusion Tome, Potion HP% rule, M6-6-3 Dark Matter, and 98/980% Libra conversion.",
                "refs": {"missions": ["M7-2-1", "M6-6-3", "M9-2-6", "M3-4-6", "M9-6-5", "M9-6-3"], "items": ["item_potion", "item_dark_matter", "item_adamantite", "item_mythril", "item_fat_chocobo_feather", "item_hero_drink", "item_gysahl_greens", "item_libra"]},
                "blocks": [
                    {"heading": "Reunion Difference: No Repeatable Clear Rewards", "body": "Unlike PSP, Crisis Core Reunion only awards Mission Clear Rewards once. Instead of re-clearing missions for 99 items, farm Dark Matter from Lesser Worms in M6-6-3 (with Mog's Amulet) and convert +98 MAG Libra Materia into any stat!"},
                    {"heading": "Consumable Potion HP% Rule", "body": "Clear M7-2-1 in Chapter 4 for the Item Fusion Tome. Consumables (Potion, Hi-Potion, Ether, Elixir) ONLY amplify an EXISTING matching stat bonus on one of the two Materia! Two +0 Materia + 99 Potions = +0%. Fuse an HP Up (+10% HP) with cheap 50 Gil Potions (20 = +10% HP) first."},
                    {"heading": "The 98 / 980% Conversion Loop", "body": "Never push an intermediate Libra transfer Materia to +99 or +999%—stop at +98 (or +980% HP). Then fuse that +98 Libra with your target skill (e.g., Costly Punch, Curaga, Aerial Drain) plus just ONE Hero Drink / Adamantite / Mythril / Fat Chocobo Feather to switch the stat and hit max cleanly."},
                ],
            },
            {
                "id": "guide_dmw_materia_leveling",
                "title": "4. Materia Leveling & Complete 18-Image DMW 100% Guide",
                "badge": "Genji Armor",
                "summary": "Exact hidden EXP & slot 1–6 reels, Moogle Power (M8-4-4), M1-1-1 AFK loop, and unlocking all 18 DMW entries.",
                "refs": {"missions": ["M1-1-1", "M8-1-1", "M8-1-4", "M8-1-6", "M8-4-1", "M8-4-3", "M8-4-4", "M8-5-6", "M10-1-3", "M10-2-3"], "items": ["item_moogle_power", "item_genji_armor", "item_faerie_ring", "item_safety_bit"]},
                "blocks": [
                    {"heading": "How Materia Leveling & DMW Memories Work", "body": "DMW reels spin continuously during battle. Matching numbers 1–6 level up the Materia in that slot; triple matches give +2/+3 levels. Character DMW % advances as you view each character's 6 memory scenes (skipping them still counts!). Summons/Chocobo Modes jump straight to 100% after triggering once."},
                    {"heading": "M1-1-1 AFK Mastering & 100% DMW Loop", "body": "Equip Faerie Ring (auto-Regen) + Safety Bit + 1–2 mastered Moogle Power Materia (M8-4-4) or DMW-boost Materia (from QMC+ / Shade), enter M1-1-1, and let weak troopers tap Zack while the DMW masters all 6 Materia slots and fills missing DMW memories. Remember to finish the mission so progress saves!"},
                ],
            },
            {
                "id": "guide_magic_pot",
                "title": "5. Magic Pot Complete Encounters Guide (All 6 Missions)",
                "badge": "Genji Shield",
                "summary": "Exact locations and attack sequences for all 6 Magic Pot encounters: M10-2-3 (DMW), M7-6-6 (Genji Shield), M2-2-6, M2-5-4, M2-5-5, and M2-5-6.",
                "refs": {"missions": ["M10-2-3", "M7-6-6", "M2-2-6", "M2-5-4", "M2-5-5", "M2-5-6"], "items": ["item_genji_shield", "item_costly_punch", "item_gil_toss", "item_octaslash", "item_ultima"]},
                "blocks": [
                    {"heading": "M10-2-3: Unlock Magic Pot DMW (Do This First!)", "body": "Equip Jump, Fira, Gravity, and Assault Twister. Enter M10-2-3 (Master Tonberry), dodge Tonberries until Magic Pot appears, do NOT attack it blindly—wait for its speech bubbles and cast Jump -> Fira -> Gravity -> Assault Twister in order."},
                    {"heading": "M7-6-6: Obtain Genji Shield", "body": "Equip Gil Toss, Costly Punch, Break Damage Limit (Brutal/Genji Glove/Buster Sword 23%+), and Octaslash Materia (Research Dept. QMC+). In M7-6-6, perform: Gil Toss -> Costly Punch -> 99,999 Damage -> Octaslash DMW."},
                    {"heading": "M2-2-6, M2-5-4, M2-5-5 & M2-5-6 Bonus Encounters", "body": "M2-2-6 requests Blizzard -> Fire -> Thunder -> Gravity. M2-5-4 requests Ultima -> Tri-Fire -> Iron Fist -> Electrocute. M2-5-5 requests Ultima -> Tri-Thundaga -> Electrocute -> Flare. M2-5-6 requests Flare -> Energy -> Ultima -> Costly Punch. See the Story & Side-Quests tab for interactive checklists!"},
                ],
            },
            {
                "id": "guide_buster_sword",
                "title": "6. Buster Sword Proficiency & Skill Power (Reunion)",
                "badge": "Reunion New",
                "summary": "How the 4 Proficiency pools add up to 100%, unlocking Break Damage Limit at 23% and Barrier Pierce at 47%, plus Skill Power cancellation.",
                "refs": {"missions": ["M1-2-1", "M1-1-3", "M9-6-5"], "items": ["item_costly_punch", "item_darkness"]},
                "blocks": [
                    {"heading": "4 Proficiency Pools (100% Cap)", "body": "Proficiency splits across Perfect Guard in Battle Stance (31.66%), Strong Attack kills (31.66%), Command Materia kills from Battle Stance (31.66%), and Barrier-Piercing kills (5%). At 23% you unlock Battle Stance Damage Limit Break (99,999); at 47% you shatter enemy Barriers automatically."},
                    {"heading": "Fastest Farm & Skill Power Gauge", "body": "Farm Perfect Guards in M1-2-1 against rapid-fire gunners, Strong Attack & Command kills in M1-1-3 (50 Shinra Troopers), and Barrier kills in M9-6-5. Against Reunion bosses, dump Battle Stance Costly Punch into their Skill Power bar to weaken or completely cancel their Limit Breaks!"},
                ],
            },
            {
                "id": "guide_missables",
                "title": "7. Chapter-by-Chapter Missables & 100% Checklist",
                "badge": "Ch. 7 Warning",
                "summary": "Every permanently missable quest, shop, mail sender, and summon from Prologue to Chapter 10.",
                "refs": {"missions": ["M6-2-1", "M4-4-3"], "items": ["item_cursed_ring", "item_rebirth_flame", "item_research_dept_qmc_plus"]},
                "blocks": [
                    {"heading": "Chapter 1–7 (Midgar Point of No Return)", "body": "Finish Fort Tamblin's 16 groups & Supply Pod Cursed Ring in Ch. 1, join all 3 Fan Clubs by Ch. 3, ace Aerith's Ch. 4 mini-games, talk to the Reporter & Silver Elite in Ch. 5, Cissnei in Ch. 6, and clear ALL Midgar NPC mission triggers before ending Chapter 7."},
                    {"heading": "Chapter 8–9 Critical Missables", "body": "In Ch. 8 Nibelheim, inspect the Water Tower via the Seven Wonders quest for the missable Phoenix DMW summon. In Ch. 9/10 Gongaga, open the outskirts chest for Research Dept. QMC+—if missed, you cannot unlock all 16 shops on that run."},
                ],
            },
            {
                "id": "guide_combat_meta",
                "title": "8. Hard Mode Combat Meta & Genji Blueprint",
                "badge": "Meta Build",
                "summary": "Wall, Costly Punch, Aerial Drain, Status Ward + Hell-aga, and where to collect all 4 Genji pieces + Ziedrich/Heike Soul.",
                "refs": {"missions": ["M7-3-6", "M7-4-6", "M7-6-6", "M9-5-4", "M9-6-4", "M9-6-6"], "items": ["item_costly_punch", "item_aerial_drain", "item_wall", "item_status_ward", "item_hell_blizzaga", "item_adaman_bangle", "item_brutal", "item_genji_helm", "item_genji_armor", "item_genji_shield", "item_genji_glove", "item_divine_slayer", "item_heike_soul"]},
                "blocks": [
                    {"heading": "Core Hard Mode Loadout", "body": "Run Costly Punch (99,999 defense-ignoring damage), Aerial Drain (i-frames + full heal), Curaga, Wall (or Genji Shield), Status Ward + Hell Blizzaga (ailment immunity + AoE Death), and Dualcast/Electrocute or Mug."},
                    {"heading": "Genji Gear Locations", "body": "Genji Helm: Online Shop Shade (M9-5-4, 1,000,000 Gil). Genji Armor: 100% DMW completion. Genji Shield: Magic Pot in M7-6-6. Genji Glove: Chest in M9-6-4. Bonus: Adaman Bangle (M7-3-6), Brutal (M7-4-6), Ziedrich (M9-5-6 chest), Heike Soul (100% of all 300 missions)."},
                ],
            },
            {
                "id": "guide_minerva",
                "title": "9. Hard Mode Superboss: Minerva (20,000,000 HP)",
                "badge": "M9-6-6 Boss",
                "summary": "Stat requirements, Phoenix Down loop, dodging Judgment Arrow & Photon Feather, and depleting Skill Power on Hard Mode.",
                "refs": {"missions": ["M9-6-6"], "items": ["item_costly_punch", "item_aerial_drain", "item_curaga", "item_phoenix_down", "item_mug", "item_divine_slayer", "item_genji_shield", "item_genji_armor", "item_genji_helm", "item_genji_glove"]},
                "blocks": [
                    {"heading": "Mandatory Pre-Fight Stats & Gear", "body": "Hard Mode Minerva has 20,000,000 HP, 255 ATK/MAG, and 255 SPR. Reach 255 VIT, 255 SPR, and 99,999 HP. Equip Genji Helm, Genji Armor, Genji Shield, and Genji Glove (or Ziedrich + Adaman Bangle). Bring Costly Punch, Aerial Drain, Curaga, Mug, and SP Master/Stat-stick Materia."},
                    {"heading": "Tactics & Judgment Arrow Counter", "body": "Mug her immediately for 99x Phoenix Downs and keep Auto-Raise active at ALL times—Judgment Arrow dispels Raise and hits hard, so deplete her Skill Power bar when Judgment Arrow charges, or time Aerial Drain's invulnerability frames. Use Battle Stance Costly Punch behind her back for 99,999 hits until Divine Slayer drops."},
                ],
            },
            {
                "id": "guide_fusion_recipes",
                "title": "10. Materia Fusion Class Rules & Key Recipes",
                "badge": "Recipes",
                "summary": "How Materia rank & classes determine fusion output, plus the most important Hard Mode fusions.",
                "refs": {"missions": ["M7-2-1", "M9-5-4"], "items": ["item_costly_punch", "item_aerial_drain", "item_wall", "item_curaga", "item_hell_blizzaga", "item_dualcast"]},
                "blocks": [
                    {"heading": "Mastered Bonus & Class Priority", "body": "Fusing two Mastered Materia often bumps the resulting Materia up a grade (e.g., Fira -> Firaga). Combining Magic + Command usually yields a Command or Dark Magic ability, while Special (Purple) Materia like Libra/HP Up act as clean stat carriers without altering your primary attack skill when fused properly."},
                    {"heading": "Interactive Simulator", "body": "Use the Fusion Calc & Tracker tab to test Materia stat combinations, check Consumable vs. Mako/Stat Stone vs. Max-Tier catalyst caps, and jump directly to enemy farming spots for any catalyst."},
                ],
            },
        ],
        "farmingPlaybooks": [
            {
                "id": "farm_gil",
                "shortLabel": "Gil (All Stages)",
                "title": "Gil & Loot Economy Playbook (Early → Endgame)",
                "badge": "180 → 495k Gil",
                "summary": "Concrete Gil & sellable-drop routes at every mission tier—starting with zero farming accessories in Ch. 1–5 up to 495k/run endgame.",
                "bestMissionId": "M9-6-2",
                "enemyId": "enemy_holy_tonberry",
                "recommendedGear": ["item_precious_watch", "item_jeweled_ring", "item_mogs_amulet", "item_brigands_gloves", "item_mug"],
                "steps": [
                    {
                        "tier": "early",
                        "stage": "Early · Ch. 1–3 (1–2★ · No Farming Gear Needed)",
                        "missionId": "M5-1-1",
                        "enemyId": "enemy_ifrit",
                        "yield": "180+ Gil / fight + Sell Gear",
                        "gearIds": ["item_bronze_bangle", "item_wrist_band", "item_cura"],
                        "detail": "Farm Ifrit in M5-1-1/M8-1-1 (180 Gil + Hi-Potion/ATK Up drops & Wrist Band rare steal) or Guard Spider in M3-1-2 (120 Gil + Bulletproof Vest steal) and Sweeper in M7-1-2 (84 Gil + Power Wrist steal). Open M6-1-x chests and sell duplicate bangles and Ether/armlets you don't equip."
                    },
                    {
                        "tier": "early-mid",
                        "stage": "Early-Mid · Ch. 4–5 (3–4★ · Pre-Sector 7 Shop)",
                        "missionId": "M3-2-2",
                        "enemyId": "enemy_g_blader",
                        "yield": "720–4,000 Gil / kill",
                        "gearIds": ["item_assault_twister", "item_barrier", "item_cura"],
                        "detail": "Farm G Bladers in M3-2-2 (3★) or M3-2-3 (4★) for 720 Gil per kill, G Smashers in M3-2-1 (640 Gil + Diamond Gloves rare steal), and Master Tonberry in M10-2-3 (1,000 Gil). Once strong enough for 4★ bosses, repeat Angeal Penance in M5-1-6 for 4,000 Gil + Lightning Armlet per clear—this easily funds your Sector 7 Shop purchases!"
                    },
                    {
                        "tier": "mid-late",
                        "stage": "Mid-Late · Ch. 6–7 (5–7★ · Sector 7 Shop Unlocked)",
                        "missionId": "M5-2-3",
                        "enemyId": "enemy_hollander",
                        "yield": "3,000+ Gil + Armlets & Dark Matter",
                        "gearIds": ["item_mug", "item_brigands_gloves", "item_mogs_amulet", "item_wall"],
                        "detail": "Open the Sector 7 Shop chest in M4-4-3 (6★) and buy Mog's Amulet + Brigand's Gloves (10,000 Gil each), plus clear M1-1-6 (6★) for Mug. Farm Hollander in M5-2-3 (3,000 Gil + Dark Matter steals), G Paladin in M7-3-5 (1,240 Gil + Mythril), or Guardian Eyes in M1-5-6 (611 Gil + sellable Shinra Beta+)."
                    },
                    {
                        "tier": "endgame",
                        "stage": "Endgame · Ch. 8–10 (9–10★ · Full Economy Break)",
                        "missionId": "M9-6-2",
                        "enemyId": "enemy_holy_tonberry",
                        "yield": "70k–495k Gil / run",
                        "gearIds": ["item_precious_watch", "item_jeweled_ring", "item_mogs_amulet", "item_brigands_gloves", "item_mug"],
                        "detail": "Buy Precious Watch (2x battle Gil) and Jeweled Ring (2x item drops) in Online Shop Shade (M9-5-4). Farm Holy Tonberry in M9-6-2 (20,000 base Gil -> 40k w/ Precious Watch + Gold Rolling Pin rare steal worth 50,000 Gil each!), M9-5-3 Three Stars (sell Mythril Armlets & Tri-Thundaga), or Mug Minerva in M9-6-6 for 99x Phoenix Downs (495,000 Gil/run)."
                    }
                ],
                "proTip": "Don't waste Gil buying Potions late-game once you have Cura/Curaga; prioritize Sector 7 Shop (M4-4-3) for Brigand's Gloves + Mog's Amulet first, and save 1,000,000 Gil in endgame for Genji Helm."
            },
            {
                "id": "farm_sp",
                "shortLabel": "SP (All Stages)",
                "title": "SP (SOLDIER Points) Playbook (Early → Endgame)",
                "badge": "80 → 40k SP/Kill",
                "summary": "How to build SP from Chapter 1 (without Mover EX or Three Stars) all the way up to 40,000 SP endgame payouts.",
                "bestMissionId": "M9-5-3",
                "enemyId": "enemy_three_stars",
                "recommendedGear": ["item_costly_punch", "item_mug", "item_mogs_amulet", "item_genji_glove"],
                "steps": [
                    {
                        "tier": "early",
                        "stage": "Early · Ch. 1–3 (1–2★ · Materia Convert + Bosses)",
                        "missionId": "M5-1-1",
                        "enemyId": "enemy_ifrit",
                        "yield": "80–162 SP / kill + Convert",
                        "gearIds": ["item_bronze_bangle", "item_cura", "item_assault_twister"],
                        "detail": "Convert unwanted duplicate Materia into SP from the Materia menu (your #1 early SP source!). In combat, hunt Vajradhara Tai & Wu in M4-1-2 (1★, 80 SP each), A-Ahriman in M5-1-3 (2★, 80 SP), and Ifrit in M5-1-1 / M8-1-1 (2★, 162 SP)."
                    },
                    {
                        "tier": "early-mid",
                        "stage": "Early-Mid · Ch. 4–5 (3–4★ · Kactuer & Angeal Penance)",
                        "missionId": "M10-1-3",
                        "enemyId": "enemy_kactuer",
                        "yield": "408–3,000 SP / kill",
                        "gearIds": ["item_assault_twister", "item_barrier", "item_cura"],
                        "detail": "Hunt Kactuer in M10-1-3 (4★, 800 SP per kill + sellable Silver/Gold Armlets) and Bahamut in M5-1-2 / M8-1-4 (3★, 408 SP). Ready for a 4★ boss? Repeat Angeal Penance in M5-1-6 for 3,000 SP per clear! Also SP-convert extra Drainra/Osmose stolen from M3-2-2 G Bladers."
                    },
                    {
                        "tier": "mid-late",
                        "stage": "Mid-Late · Ch. 6–8 (6–8★ · Mover SP Chain)",
                        "missionId": "M8-5-2",
                        "enemyId": "enemy_mover",
                        "yield": "2,000–8,000 SP (2–3x Chain!)",
                        "gearIds": ["item_wall", "item_curaga", "item_mug", "item_adaman_bangle"],
                        "detail": "Farm Mover in M8-5-2 (6★, 2,000 SP base) and Hollander in M5-2-3 (6★, 1,780 SP). HIDDEN REUNION TIP: Kill weaker enemies BEFORE finishing Movers without taking damage to stack a 2x–3x SP Chain multiplier! At 8★, upgrade to Mover RE (M2-3-3/M6-4-2, 4,000 SP) and Mover EX (M6-6-3, 8,000 SP + steal Flare to SP-convert!)."
                    },
                    {
                        "tier": "endgame",
                        "stage": "Endgame · Ch. 9–10 (9–10★ · Three Stars & Minerva)",
                        "missionId": "M9-5-3",
                        "enemyId": "enemy_three_stars",
                        "yield": "20,000–40,000 SP / kill",
                        "gearIds": ["item_costly_punch", "item_genji_glove", "item_mug", "item_mogs_amulet"],
                        "detail": "Farm Three Stars in M9-5-3 / M9-5-2 (20,000 SP base + Tri-Fire/Tri-Thundaga steals to convert), Kactuare in M9-6-1 (24,000 SP), or Minerva in M9-6-6 (40,000 SP per clear). Keep 500k+ SP in reserve before doing +98/+980% fusions or using SP Turbo/Master."
                    }
                ],
                "proTip": "Reunion hides an SP Chain bonus: defeating small adds before killing a Mover/Three Stars without taking HP damage boosts your SP payout up to 3x!"
            },
            {
                "id": "farm_exp",
                "shortLabel": "EXP (All Stages)",
                "title": "EXP & Character Leveling Playbook (Lv 1 → 99)",
                "badge": "Lv 1 → 99",
                "summary": "Fastest EXP missions for every tier of the game, paired with accessible defensive gear (no Costly Punch required early).",
                "bestMissionId": "M8-6-4",
                "enemyId": "enemy_scissor_chitin",
                "recommendedGear": ["item_costly_punch", "item_brutal", "item_genji_glove", "item_status_ward", "item_hell_blizzaga"],
                "steps": [
                    {
                        "tier": "early",
                        "stage": "Early · Ch. 1–3 (1–2★ · Lv 1–16)",
                        "missionId": "M10-4-2",
                        "enemyId": "enemy_sea_worm",
                        "yield": "69–177 EXP / kill",
                        "gearIds": ["item_bronze_bangle", "item_assault_twister", "item_cura"],
                        "detail": "Clear M1, M3, M4, and M8 branches naturally. Top 1–2★ EXP targets are Sea Worm (M10-4-2, 177 EXP), Guard Spider (M3-1-2, 162 EXP), and Ifrit (M5-1-1/M8-1-1, 162 EXP). Level-ups happen when hidden EXP crosses a threshold AND DMW hits 7-7-7. CRITICAL: Never forfeit/abandon a mission or all EXP gained during it is wiped!"
                    },
                    {
                        "tier": "early-mid",
                        "stage": "Early-Mid · Ch. 4–5 (3–4★ · Lv 16–30)",
                        "missionId": "M5-1-6",
                        "enemyId": "enemy_angeal_penance",
                        "yield": "665–4,711 EXP / kill",
                        "gearIds": ["item_assault_twister", "item_barrier", "item_cura", "item_hp_up"],
                        "detail": "General's Tank (918 EXP) and G Blader (665 EXP) in M3-2-3 give reliable 4★ mob EXP, while Angeal Penance in M5-1-6 awards a huge 4,711 EXP (plus 3,000 SP & 4,000 Gil) per clear. Also clear M8-3-2 (4★) for free Status Ward early!"
                    },
                    {
                        "tier": "mid-late",
                        "stage": "Mid-Late · Ch. 6–8 (5–7★ · Lv 30–55)",
                        "missionId": "M1-5-6",
                        "enemyId": "enemy_guardian_eyes",
                        "yield": "5,769–9,977 EXP / kill",
                        "gearIds": ["item_wall", "item_curaga", "item_adaman_bangle", "item_status_ward"],
                        "detail": "Hunt Guardian Eyes in M1-5-6 (8,083 EXP), Tarantula in M1-5-3 (6,380 EXP), and Hollander in M5-2-3 (9,977 EXP). Clear M7-3-6 (6★) for Adaman Bangle and M7-4-6 (7★, Wyerd 5,966 EXP) for Brutal, or reach 23% Buster Sword Proficiency for free Break Damage Limit."
                    },
                    {
                        "tier": "endgame",
                        "stage": "Endgame · Ch. 8–10 (8–10★ · Lv 55–99)",
                        "missionId": "M8-6-4",
                        "enemyId": "enemy_scissor_chitin",
                        "yield": "5,460–31,936 EXP / kill",
                        "gearIds": ["item_costly_punch", "item_genji_glove", "item_status_ward", "item_hell_blizzaga"],
                        "detail": "Farm G Dominator in M7-4-5 (8★, 7,770 EXP) or loop Scissor Chitins in M8-6-4 (9★, 5,460 EXP, very fast spawns) with Costly Punch + Break Damage Limit. At 10★ with 200+ VIT/SPR, Goliath (M9-6-5, 23,264 EXP) and Great Malboro (M9-6-4, 31,936 EXP) rocket you to Lv. 99."
                    }
                ],
                "proTip": "You do NOT need to stay in one fight waiting for 7-7-7—hidden EXP keeps accumulating across missions and triggers rapid catch-up level-ups whenever 7-7-7 hits, as long as you finish the mission."
            },
            {
                "id": "farm_catalysts",
                "shortLabel": "Stat Catalysts",
                "title": "Stat Catalyst & Fusion Farming Playbook (All Stages)",
                "badge": "Mako → Max Tier",
                "summary": "Progress from Ch. 1–4 Mako Stones and 50 Gil Potions to 5–7★ Stat Stones and the endgame 98/980% Dark Matter Libra trick.",
                "bestMissionId": "M6-6-3",
                "enemyId": "enemy_lesser_worm",
                "recommendedGear": ["item_mogs_amulet", "item_brigands_gloves", "item_jeweled_ring", "item_mug"],
                "steps": [
                    {
                        "tier": "early",
                        "stage": "Early · Ch. 1–3 (1–2★ · Pre-Item Fusion)",
                        "missionId": "M10-4-2",
                        "enemyId": "enemy_sea_worm",
                        "yield": "Stockpile Mako Stones (5 = +1/+10%)",
                        "gearIds": ["item_bronze_bangle", "item_cura"],
                        "detail": "Item Fusion isn't unlocked until Chapter 4 (M7-2-1), so NEVER sell Mako Stones or Potions! Stockpile early drops/steals from Sea Worm in M10-4-2 (MAG/SPR/MP Mako Stones) and Grashtrike in M2-1-1 (ATK Mako Stones)."
                    },
                    {
                        "tier": "early-mid",
                        "stage": "Early-Mid · Ch. 4–5 (3–4★ · Item Fusion Tome + Potions)",
                        "missionId": "M7-2-1",
                        "enemyId": "enemy_g_eraser",
                        "yield": "Potions (+HP%) & Mako Stones (+40)",
                        "gearIds": ["item_hp_up", "item_vit_up", "item_spr_up", "item_libra"],
                        "detail": "Clear M7-2-1 (3★) to unlock Item Fusion! Buy HP Up (Sec. 8 M6-2-1) and cheap 50 Gil Shinra Potions—remember consumables ONLY amplify an EXISTING HP% stat! Farm 3–4★ Mako Stones from General's Tank M3-2-3 (HP), Tonberry M10-2-1 (ATK/HP), Coast Runner M10-4-1 (VIT/LCK), G Diver M3-2-2 (SPR), and Kactuer M10-1-3 (LCK)."
                    },
                    {
                        "tier": "mid-late",
                        "stage": "Mid-Late · Ch. 6–7 (5–7★ · Stat Stones + Early Dark Matter)",
                        "missionId": "M5-2-3",
                        "enemyId": "enemy_hollander",
                        "yield": "Stat Stones (3 = +1) + Early Dark Matter",
                        "gearIds": ["item_mug", "item_brigands_gloves", "item_mogs_amulet", "item_libra"],
                        "detail": "Farm Stat Stones (cap +66) from Break Machine M1-5-4 (HP/Guard), Spike Machine M1-5-5 (Power/Guard), Evilgoyle M7-3-1 (Magic), and Nightmare M8-3-3 (Mind). Huge midgame shortcut: Steal Dark Matter from Hollander in M5-2-3 (6★) and rare-steal Mythril from G Paladin in M7-3-5 (7★)!"
                    },
                    {
                        "tier": "endgame",
                        "stage": "Endgame · Ch. 8–10 (8–10★ · 98/980% Libra Loop)",
                        "missionId": "M6-6-3",
                        "enemyId": "enemy_lesser_worm",
                        "yield": "+100 Stats & +999% HP",
                        "gearIds": ["item_mogs_amulet", "item_jeweled_ring", "item_brigands_gloves", "item_mug"],
                        "detail": "With Mog's Amulet + Jeweled Ring, Lesser Worms in M6-6-3 drop Dark Matter rapidly—stack 98 onto a Libra (+98 MAG) and convert it with JUST ONE Adamantite (Goliath M9-6-5), Mythril (G Purgatorio M3-4-6), Hero Drink (Master Blade M9-6-3), Fat Chocobo Feather (Jabberwock M9-2-6 / Humbaba M6-6-6), or Gysahl Greens (Kactuare M9-6-1)."
                    }
                ],
                "proTip": "Reunion removed repeatable Mission Clear Rewards, so don't burn 99x rare catalysts—build a +98 MAG / +980% HP Libra carrier and use ONE final catalyst to convert it cleanly."
            },
            {
                "id": "farm_materia_mastery",
                "shortLabel": "Materia Mastery",
                "title": "Materia Leveling & AFK Mastering Playbook (All Stages)",
                "badge": "Slots 1–6 → AFK",
                "summary": "How to level Materia quickly from Chapter 1 onward, before and after unlocking Moogle Power & Faerie Ring.",
                "bestMissionId": "M1-1-1",
                "enemyId": "enemy_sentry",
                "recommendedGear": ["item_moogle_power", "item_faerie_ring", "item_safety_bit"],
                "steps": [
                    {
                        "tier": "early",
                        "stage": "Early · Ch. 1–3 (1–2★ · Active DMW Slot Leveling)",
                        "missionId": "M1-1-1",
                        "enemyId": "enemy_sentry",
                        "yield": "Slots 1–4 Level Ups",
                        "gearIds": ["item_bronze_bangle", "item_cura"],
                        "detail": "Your equipped Materia slots correspond to DMW numbers 1–6! Rolling a double number levels that exact slot (+1), while triples jump +2 to +3 levels immediately. Fight longer multi-wave early missions (like M1-1-x) so reels keep spinning."
                    },
                    {
                        "tier": "early-mid",
                        "stage": "Early-Mid · Ch. 4–5 (3–4★ · Unlock 6 Slots & Safety Bit)",
                        "missionId": "M1-1-1",
                        "enemyId": "enemy_sentry",
                        "yield": "Safe Passive Loop (Pre-Moogle)",
                        "gearIds": ["item_safety_bit", "item_barrier", "item_cura"],
                        "detail": "Grab a free Safety Bit from the chest in M10-1-3 (4★) and reach Chapter 5+ for 6 Materia slots. If you need quick mastery before Moogle Power, idle in M1-1-1 behind Barrier/guarding while healing periodically—always kill the final Sentry to save levels!"
                    },
                    {
                        "tier": "mid-late",
                        "stage": "Mid-Late · Ch. 6–7 (5–7★ · Unlock Moogle Power AFK)",
                        "missionId": "M8-4-4",
                        "enemyId": "enemy_guard_fang",
                        "yield": "Full AFK 6-Slot Mastery",
                        "gearIds": ["item_moogle_power", "item_faerie_ring", "item_safety_bit"],
                        "detail": "Clear M8-4-4 (6★) to unlock Moogle DMW, then unlock Junon Souvenirs (chest in M2-4-1, 6★) to buy Moogle Power Materia and Mythril Mine Trading (clear M2-4-5, 6★) for Faerie Ring (Auto-Regen). Now Moogle Power levels ALL equipped Materia at once!"
                    },
                    {
                        "tier": "endgame",
                        "stage": "Endgame · Ch. 8–10 (8–10★ · High-Grade Materia AFK)",
                        "missionId": "M1-1-1",
                        "enemyId": "enemy_sentry",
                        "yield": "Master 4–5 Endgame Slots AFK",
                        "gearIds": ["item_moogle_power", "item_faerie_ring", "item_genji_armor"],
                        "detail": "Equip 1–2 mastered Moogle Power Materia alongside Costly Punch, Aerial Drain, Wall, and Curaga, put on Faerie Ring (or Genji Armor), enter M1-1-1, and let Sentries hit Zack AFK. CRITICAL: Finish the mission before leaving or all levels are lost!"
                    }
                ],
                "proTip": "NEVER leave an AFK farming mission via Abandon Mission—you must clear the encounter for Materia levels and EXP to lock in."
            },
            {
                "id": "farm_buster_sword",
                "shortLabel": "Buster Sword 100%",
                "title": "Buster Sword Proficiency Playbook (Reunion)",
                "badge": "23% / 47% Perks",
                "summary": "Reunion-exclusive stance progression from Chapter 1 onward: unlock Damage Limit Break at 23% and Barrier Pierce at 47%.",
                "bestMissionId": "M1-2-1",
                "enemyId": None,
                "recommendedGear": ["item_costly_punch", "item_assault_twister", "item_darkness"],
                "steps": [
                    {
                        "tier": "early",
                        "stage": "Early · Ch. 1–3 (1–2★ · Unlock Stance Habit)",
                        "missionId": "M1-1-1",
                        "enemyId": "enemy_sentry",
                        "yield": "Start Guard & Strong Pools",
                        "gearIds": ["item_assault_twister", "item_bronze_bangle"],
                        "detail": "As soon as Zack inherits the Buster Sword, build the habit of snapping into Battle Stance before unleashing Assault Twister or Strong Attack finishers—even early 1–2★ clears chip away at the 63.32% offense pools."
                    },
                    {
                        "tier": "early-mid",
                        "stage": "Early-Mid · Ch. 4–5 (2–4★ · Rush 23% Damage Break)",
                        "missionId": "M3-1-2",
                        "enemyId": "enemy_heli_gunner",
                        "yield": "23% = Free 99,999 Damage Break",
                        "gearIds": ["item_barrier", "item_assault_twister", "item_cura"],
                        "detail": "Use gunfire from Heli Gunner (M3-1-2) or early rapid-fire troopers to practice Perfect Guards in Battle Stance (31.66% pool) + Command kills. Hitting just 23% proficiency gives every Battle Stance attack/skill Break Damage Limit BEFORE Brutal or Genji Glove!"
                    },
                    {
                        "tier": "mid-late",
                        "stage": "Mid-Late · Ch. 6–7 (5–7★ · M1-2-1 & M1-1-3 Max Pools)",
                        "missionId": "M1-1-3",
                        "enemyId": "enemy_sergeant",
                        "yield": "47% = Free Barrier Pierce",
                        "gearIds": ["item_assault_twister", "item_wall", "item_adaman_bangle"],
                        "detail": "Farm Perfect Guards in M1-2-1 (5★ Security Officers) and Strong Attack / Command Materia kills in M1-1-3 (5★, 50 Shinra Troopers) with AoE Assault Twister / Quake. Crossing 47% lets Battle Stance bypass enemy Barrier & MBarrier!"
                    },
                    {
                        "tier": "endgame",
                        "stage": "Endgame · Ch. 8–10 (8–10★ · 5% Barrier Pool & Limit Breaks)",
                        "missionId": "M9-6-5",
                        "enemyId": "enemy_goliath",
                        "yield": "100% Cap + Boss Skill Power Break",
                        "gearIds": ["item_costly_punch", "item_genji_glove"],
                        "detail": "Finish the final 5% Barrier-piercing kill pool in M9-6-5 against buffed Mock Troopers / Goliath. Against Hard Mode bosses (including Minerva), snap into Battle Stance + Costly Punch to drain their purple Skill Power bar and cancel Limit Breaks."
                    }
                ],
                "proTip": "Reaching 23% Buster Sword Proficiency lets Battle Stance Costly Punch hit 99,999 without needing Genji Glove or Brutal—a massive power spike in midgame!"
            },
            {
                "id": "farm_dmw",
                "shortLabel": "DMW 100% (Genji)",
                "title": "100% DMW & Genji Armor Playbook (Chapter-by-Chapter)",
                "badge": "18 Images",
                "summary": "Track every DMW character, summon, and Chocobo Mode by story chapter so nothing gets missed on your way to Genji Armor.",
                "bestMissionId": "M1-1-1",
                "enemyId": None,
                "recommendedGear": ["item_genji_armor", "item_faerie_ring", "item_moogle_power"],
                "steps": [
                    {
                        "tier": "early",
                        "stage": "Early · Ch. 1–3 (1–2★ · Story Cast + Ifrit)",
                        "missionId": "M8-1-1",
                        "enemyId": "enemy_ifrit",
                        "yield": "Zack, Sephiroth, Angeal, Tseng, Ifrit",
                        "gearIds": ["item_bronze_bangle", "item_cura"],
                        "detail": "Sephiroth, Angeal (Ch. 1), and Tseng (Ch. 2) join through story. Clear M8-1-1 (2★) to unlock Ifrit DMW immediately—summons hit 100% the very first time they trigger in combat!"
                    },
                    {
                        "tier": "early-mid",
                        "stage": "Early-Mid · Ch. 4–5 (3–4★ · Cloud, Aerith, Cissnei & Chocobo Trio)",
                        "missionId": "M10-1-3",
                        "enemyId": "enemy_kactuer",
                        "yield": "Bahamut, Cactuar, Tonberry, Magic Pot",
                        "gearIds": ["item_assault_twister", "item_barrier", "item_safety_bit"],
                        "detail": "Story adds Cloud & Aerith (Ch. 4) and Cissnei (Ch. 5). Early missions unlock Bahamut (M8-1-4, 3★), Cactuar (M10-1-3, 4★), Tonberry & Magic Pot (M10-2-3, 3★ — obey Magic Pot's Jump -> Fira -> Gravity -> Assault Twister sequence!)."
                    },
                    {
                        "tier": "mid-late",
                        "stage": "Mid-Late · Ch. 6–7 (5–7★ · Odin, Moogle, Cait Sith, Chocobo)",
                        "missionId": "M8-4-4",
                        "enemyId": "enemy_guard_fang",
                        "yield": "16/18 Unlocks Before Leaving Midgar",
                        "gearIds": ["item_moogle_power", "item_faerie_ring"],
                        "detail": "Clear M8-1-6 (6★ Odin), M8-4-1 (5★ Chocobo), M8-4-3 (6★ Cait Sith), and M8-4-4 (6★ Moogle). Also unlock Junon Souvenirs (M2-4-1, 6★) & Bone Village Outlet (M7-5-3, 7★) for summon/Chocobo boost Materia."
                    },
                    {
                        "tier": "endgame",
                        "stage": "Endgame · Ch. 8–10 (8–10★ · Ch. 8 Phoenix + QMC+ → 100%)",
                        "missionId": "M1-1-1",
                        "enemyId": None,
                        "yield": "100% DMW = Genji Armor",
                        "gearIds": ["item_genji_armor", "item_faerie_ring", "item_octaslash"],
                        "detail": "MISSABLE ALERT: In Ch. 8 Nibelheim, inspect the Water Tower via Seven Wonders for Phoenix DMW. Clear M8-5-6 (9★) for Bahamut Fury, grab Research Dept. QMC+ in Ch. 9 Gongaga for character boost Materia, then idle in M1-1-1 with Faerie Ring until 100% unlocks Genji Armor! (Skipping cutscenes still counts!)"
                    }
                ],
                "proTip": "Check the Shops, DMW & Missables tab to check off all 18 portraits—every character needs 6 memory scenes (skipping cutscenes counts!), while Summons need just 1 trigger."
            },
        ],
        "statLevelingGuides": [
            {
                "id": "stat_hp",
                "stat": "HP%",
                "title": "HP% Stat-Leveling Materia Guide",
                "cap": "+999% HP",
                "priority": "Critical (Hard Mode Core)",
                "whyMatters": "Costly Punch ignores enemy VIT/DEF and deals 99,999 damage when Zack's current HP is high. Paired with Adaman Bangle or Genji Armor (Break HP Limit), +999% HP lets Zack survive Minerva's Judgment Arrow.",
                "consumableItemId": "item_potion",
                "consumableRule": "20 Potions = +10% (10 Hi-Potions / 5 X-Potions / 1 Elixir = +10%). CRITICAL: Consumables ONLY work if one of the two fused Materia ALREADY has an HP% bonus!",
                "makoStoneId": "item_hp_mako_stone",
                "statStoneId": "item_hp_stone",
                "maxItemId": "item_fat_chocobo_feather",
                "targetMateriaIds": ["item_costly_punch", "item_curaga", "item_aerial_drain", "item_hp_up"],
                "phases": [
                    {"phase": "Early (Ch. 4 — Item Fusion Tome M7-2-1)", "missionId": "M7-2-1", "detail": "Buy HP Up from Sector 8 Materia Shop (M6-2-1) so you already have an HP% stat. Fuse it with cheap 50 Gil Shinra Shop Potions (99 Potions = +40–50% per fusion) or mix in HP Mako Stones."},
                    {"phase": "Midgame (HP Stones & HP Up++)", "missionId": "M6-2-1", "detail": "Use HP Stones (3 = +10%, max +660%) or keep stacking Potions/Hi-Potions onto a Libra carrier until you cross +500% HP. Equip Adaman Bangle (M7-3-6) to break the 9,999 HP ceiling."},
                    {"phase": "Endgame (+999% HP via 980% Trick)", "missionId": "M9-2-6", "detail": "Build a Libra up to +980% HP using Potions/X-Potions/Elixirs or Fat Chocobo Feathers (Jabberwock M9-2-6 / Humbaba M6-6-6), then fuse with Costly Punch + 1–2 Fat Chocobo Feathers to hit +999% HP."}
                ],
                "proTip": "One single +999% HP Materia plus Zack's Lv. 70+ base HP (~7,500–9,999) + Genji Armor/Adaman Bangle easily reaches 99,999 HP without wasting a second Materia slot on HP%!"
            },
            {
                "id": "stat_vit",
                "stat": "VIT",
                "title": "VIT (Vitality) Stat-Leveling Materia Guide",
                "cap": "+100 VIT",
                "priority": "Critical (255 VIT Mandatory)",
                "whyMatters": "Reduces all physical damage taken on Hard Mode. At 255 VIT + Barrier/Wall, endgame bosses deal survivable chip damage instead of 50,000+ one-shots.",
                "consumableItemId": None,
                "consumableRule": "No shop consumable raises VIT—start with VIT Mako Stones, Guard Stones, or Dark Matter converted via Adamantite.",
                "makoStoneId": "item_vit_mako_stone",
                "statStoneId": "item_guard_stone",
                "maxItemId": "item_adamantite",
                "targetMateriaIds": ["item_aerial_drain", "item_wall", "item_mug", "item_high_jump"],
                "phases": [
                    {"phase": "Early (VIT Mako Stones)", "missionId": "M8-2-2", "detail": "Farm VIT Mako Stones (5 = +1 VIT, max +40) from early Shinra/Wutai missions and stack onto a Libra or Barrier Materia."},
                    {"phase": "Midgame (Guard Stones)", "missionId": "M7-6-4", "detail": "Steal Guard Stones (3 = +1 VIT, max +66) from Crazy Sword (M3-5-4 / M7-6-4) or heavy mech units while unlocking Break Limit gear."},
                    {"phase": "Endgame (+100 VIT Conversion)", "missionId": "M9-6-5", "detail": "Either farm Adamantite directly from Goliath (M9-6-5) / Crazy Sword (M7-6-4, M9-4-1) / Grandpanzer (M9-3-3), OR stack 98 Dark Matter on Libra in M6-6-3 and convert with just 1–2 Adamantite!"}
                ],
                "proTip": "At Lv. 75+, Zack has ~60–75 base VIT. One +100 VIT Materia + Ziedrich (+100 VIT) or Divine Slayer (+50 VIT) + a second +100 VIT Materia hits the 255 cap cleanly."
            },
            {
                "id": "stat_spr",
                "stat": "SPR",
                "title": "SPR (Spirit) Stat-Leveling Materia Guide",
                "cap": "+100 SPR",
                "priority": "Critical (255 SPR Mandatory)",
                "whyMatters": "Reduces all magical damage (including Minerva's Ultima, Crimson Flare, and Krysta) and boosts Curaga healing.",
                "consumableItemId": "item_phoenix_down",
                "consumableRule": "Phoenix Down acts as a +1 SPR (max +100) catalyst in Materia Fusion! You can steal 99x from Minerva (M9-6-6) or convert via Mythril.",
                "makoStoneId": "item_spr_mako_stone",
                "statStoneId": "item_mind_stone",
                "maxItemId": "item_mythril",
                "targetMateriaIds": ["item_curaga", "item_wall", "item_status_ward", "item_sp_master"],
                "phases": [
                    {"phase": "Early (SPR Mako Stones)", "missionId": "M8-2-1", "detail": "Stack SPR Mako Stones (5 = +1 SPR, max +40) onto Cura or Barrier early for magic defense against mages."},
                    {"phase": "Midgame (Mind Stones & Mythril)", "missionId": "M3-4-6", "detail": "Equip Mog's Amulet + Brigand's Gloves and Mug G Purgatorio in M3-4-6 (or M8-6-6) for direct Mythril (+1 SPR each, max +100) and Mind Stones."},
                    {"phase": "Endgame (+100 SPR Conversion)", "missionId": "M9-6-6", "detail": "Build a +98 Dark Matter Libra in M6-6-3 and fuse with 1–2 Mythril (or Phoenix Downs stolen from Minerva in M9-6-6) onto Curaga or Status Ward."}
                ],
                "proTip": "Always put +100 SPR on your healing/defensive staple (Curaga or Wall) and +100 VIT on Aerial Drain or Mug so your stats never leave your loadout when swapping offensive spells."
            },
            {
                "id": "stat_atk",
                "stat": "ATK",
                "title": "ATK (Attack) Stat-Leveling Materia Guide",
                "cap": "+100 ATK",
                "priority": "High (Physical / Battle Stance)",
                "whyMatters": "Maximizes Battle Stance Strong Attacks, Aerial Drain, High Jump, Assault Twister+, and Mug. Note: Costly Punch ignores ATK and scales off HP instead!",
                "consumableItemId": None,
                "consumableRule": "No consumable raises ATK—use ATK Mako Stones, Power Stones, or Hero Drinks (1 = +1 ATK, max +100).",
                "makoStoneId": "item_atk_mako_stone",
                "statStoneId": "item_power_stone",
                "maxItemId": "item_hero_drink",
                "targetMateriaIds": ["item_aerial_drain", "item_high_jump", "item_darkness", "item_mug"],
                "phases": [
                    {"phase": "Early (ATK Mako Stones)", "missionId": "M1-3-1", "detail": "Stack ATK Mako Stones (5 = +1 ATK, max +40) onto Assault Twister or Jump in early chapters."},
                    {"phase": "Midgame (Power Stones)", "missionId": "M8-6-4", "detail": "Use Power Stones (3 = +1 ATK, max +66) dropped by mid/late physical enemies and clear rewards."},
                    {"phase": "Endgame (+100 ATK via Hero Drink)", "missionId": "M9-6-3", "detail": "Farm Hero Drinks from Master Blade (M9-6-3) or Iron Claw (M6-5-6 / M9-3-6), or convert a +98 Dark Matter Libra using 1–2 Hero Drinks onto Aerial Drain."}
                ],
                "proTip": "If you run a Costly Punch build for Minerva, prioritize HP%, VIT 255, and SPR 255 BEFORE ATK—only add +100 ATK on your 4th/5th slot once defenses are capped."
            },
            {
                "id": "stat_mag",
                "stat": "MAG",
                "title": "MAG (Magic) Stat-Leveling Materia Guide",
                "cap": "+100 MAG",
                "priority": "High (Easiest Stat to Max)",
                "whyMatters": "Drives Electrocute, Energy, Quake, Ultima, Hell-aga, and Curaga. Because Dark Matter is effortless to farm in M6-6-3, MAG is the universal backbone for leveling ALL other stats!",
                "consumableItemId": None,
                "consumableRule": "No consumable raises MAG—Dark Matter (1 = +1 MAG, max +100) is the fastest-farmed catalyst in the game.",
                "makoStoneId": "item_mag_mako_stone",
                "statStoneId": "item_magic_stone",
                "maxItemId": "item_dark_matter",
                "targetMateriaIds": ["item_electrocute", "item_energy", "item_quake", "item_ultima", "item_hell_blizzaga"],
                "phases": [
                    {"phase": "Early (MAG Mako Stones)", "missionId": "M8-2-3", "detail": "Feed MAG Mako Stones (5 = +1 MAG, max +40) into Fira/Blizzara/Thundara for early caster clears."},
                    {"phase": "Midgame (Magic Stones)", "missionId": "M6-6-3", "detail": "Lesser Worms in M6-6-3 drop both Dark Matter (Common) and Magic Stones (Rare) at once."},
                    {"phase": "Endgame (+100 MAG & Conversion Hub)", "missionId": "M6-6-3", "detail": "Farm 99x Dark Matter from Lesser Worms in M6-6-3 (with Mog's Amulet + Jeweled Ring). Fuse 98 onto Libra for any stat conversion, or 99 directly onto Dualcast/Electrocute/Ultima!"}
                ],
                "proTip": "Keep a spare stack of 99 Dark Matter at all times—it turns any new Materia into a +98/+100 stat stick in 60 seconds."
            },
            {
                "id": "stat_lck",
                "stat": "LCK",
                "title": "LCK (Luck) Stat-Leveling Materia Guide",
                "cap": "+100 LCK",
                "priority": "Situational (Crit & Steal)",
                "whyMatters": "Increases Critical Hit rate and slightly aids drop/steal consistency. Note: Genji Glove guarantees 100% critical hits regardless of LCK.",
                "consumableItemId": None,
                "consumableRule": "No consumable raises LCK—use LCK Mako Stones, Luck Stones, or Gysahl Greens (1 = +1 LCK, max +100).",
                "makoStoneId": "item_lck_mako_stone",
                "statStoneId": "item_luck_stone",
                "maxItemId": "item_gysahl_greens",
                "targetMateriaIds": ["item_mug", "item_sp_master", "item_libra"],
                "phases": [
                    {"phase": "Early / Mid (LCK Mako & Luck Stones)", "missionId": "M8-2-6", "detail": "Only invest spare LCK stones if not equipping Genji Glove."},
                    {"phase": "Endgame (+100 LCK via 1 Gysahl Greens)", "missionId": "M9-6-4", "detail": "Grab Gysahl Greens from M9-6-x chests or M10-3-2, then convert a +98 Dark Matter Libra with 1 Gysahl Greens if you want 255 LCK without Genji Glove."}
                ],
                "proTip": "If you already wear Genji Glove (M9-6-4) or Divine Slayer (M9-6-6), skip LCK completely and put VIT/SPR/ATK/MAG on your Materia slots instead."
            },
            {
                "id": "stat_mp",
                "stat": "MP%",
                "title": "MP% Stat-Leveling Materia Guide",
                "cap": "+999% MP",
                "priority": "Situational (Pre-Genji Helm)",
                "whyMatters": "Fuels Dualcast + Ultima / Electrocute / Curaga spam before you obtain Genji Helm (which makes all MP & AP costs 0).",
                "consumableItemId": "item_ether",
                "consumableRule": "10 Ethers = +10% MP (max +999%). Requires an EXISTING MP% bonus on one of the two fused Materia!",
                "makoStoneId": "item_mp_mako_stone",
                "statStoneId": "item_mp_stone",
                "maxItemId": "item_lunar_harp",
                "targetMateriaIds": ["item_dualcast", "item_ultima", "item_electrocute", "item_curaga"],
                "phases": [
                    {"phase": "Early / Mid (MP Up + Ethers)", "missionId": "M6-2-1", "detail": "Buy MP Up from Sector 8 Materia Shop (M6-2-1) and feed cheap Shinra Shop Ethers (200 Gil) or MP Mako Stones."},
                    {"phase": "Endgame (Lunar Harp or Skip via Genji Helm)", "missionId": "M9-5-4", "detail": "Convert a +980% HP/MP Libra with 1 Lunar Harp if needed, OR buy Genji Helm from Online Shop Shade (M9-5-4) for 1,000,000 Gil to make MP% completely unnecessary!"}
                ],
                "proTip": "Once you buy Genji Helm (0 MP/AP cost), replace any +MP% Materia with +HP%, +VIT, +SPR, or +MAG."
            },
            {
                "id": "stat_ap",
                "stat": "AP%",
                "title": "AP% Stat-Leveling Materia Guide",
                "cap": "+999% AP",
                "priority": "Situational (Pre-Genji Helm)",
                "whyMatters": "Powers Aerial Drain, High Jump, and Assault Twister+ spam before acquiring Genji Helm (0 AP cost). Note: Costly Punch costs HP, not AP!",
                "consumableItemId": "item_soma",
                "consumableRule": "10 Soma = +10% AP (max +999%). Requires an EXISTING AP% bonus on one of the two fused Materia!",
                "makoStoneId": "item_ap_mako_stone",
                "statStoneId": "item_ap_stone",
                "maxItemId": "item_zeio_nut",
                "targetMateriaIds": ["item_aerial_drain", "item_high_jump", "item_costly_punch"],
                "phases": [
                    {"phase": "Early / Mid (AP Up + Soma)", "missionId": "M6-2-1", "detail": "Buy AP Up from Sector 8 Materia Shop (M6-2-1) and stack Shinra Shop Soma (200 Gil) or AP Stones."},
                    {"phase": "Endgame (Zeio Nut or Genji Helm)", "missionId": "M9-5-4", "detail": "Convert with 1 Zeio Nut (M9-6-x chests) if needed, or simply equip Genji Helm (M9-5-4) for infinite AP."}
                ],
                "proTip": "Buster Sword Proficiency's passive Necromose also refunds MP/AP on every kill, making dedicated +AP% Materia rarely needed."
            },
        ],
        "endgameBuildBlueprints": [
            {
                "id": "build_minerva_slayer",
                "name": "Minerva Hard Mode Slayer (255 VIT/SPR · 99,999 HP)",
                "role": "Endgame Bosses & M9-6-6",
                "accessories": ["item_genji_helm", "item_genji_armor", "item_genji_shield", "item_genji_glove"],
                "altAccessories": "Pre-Genji swap: Adaman Bangle (M7-3-6) + Brutal (M7-4-6) + Ziedrich (M9-5-6)",
                "materiaSlots": [
                    {"materiaId": "item_costly_punch", "stat": "HP% +999%", "role": "Primary 99,999 defense-ignoring DPS"},
                    {"materiaId": "item_aerial_drain", "stat": "VIT +100", "role": "Invulnerability frames + full heal + VIT cap"},
                    {"materiaId": "item_curaga", "stat": "SPR +100", "role": "Emergency burst heal + SPR cap"},
                    {"materiaId": "item_mug", "stat": "VIT +100", "role": "Steal 99x Phoenix Downs + second VIT cap"},
                    {"materiaId": "item_wall", "stat": "SPR +100", "role": "Backup Barrier/MBarrier + second SPR cap"},
                    {"materiaId": "item_sp_master", "stat": "ATK +100", "role": "Extra damage/mitigation (or Libra / High Jump)"},
                ],
            },
            {
                "id": "build_arcane_dualcast",
                "name": "Dualcast Arcane Nuke (255 MAG · 255 VIT/SPR)",
                "role": "AoE Speed Clearing (M8-6-4 / M9-5-3)",
                "accessories": ["item_genji_helm", "item_genji_armor", "item_ziedrich", "item_genji_glove"],
                "altAccessories": "Genji Helm gives 0 MP cost; Ziedrich adds +100 to ATK/VIT/MAG/SPR!",
                "materiaSlots": [
                    {"materiaId": "item_dualcast", "stat": "MAG +100", "role": "Double-casts every offensive spell"},
                    {"materiaId": "item_electrocute", "stat": "MAG +100", "role": "Heavy multi-hit lightning burst"},
                    {"materiaId": "item_ultima", "stat": "HP% +999%", "role": "Screen-wide non-elemental finisher"},
                    {"materiaId": "item_hell_blizzaga", "stat": "VIT +100", "role": "Instant-death mob wipe"},
                    {"materiaId": "item_status_ward", "stat": "SPR +100", "role": "All-ailment immunity paired w/ Hell Blizzaga"},
                    {"materiaId": "item_curaga", "stat": "SPR +100", "role": "Full heal + 255 SPR"},
                ],
            },
            {
                "id": "build_loot_farmer",
                "name": "All-Purpose Loot, SP & Gil Farmer",
                "role": "M6-6-3 · M9-5-3 · M9-6-3 · M3-4-6",
                "accessories": ["item_mogs_amulet", "item_jeweled_ring", "item_precious_watch", "item_brigands_gloves"],
                "altAccessories": "Swap Brigand's Gloves for Genji Glove once Buster Sword 23%+ breaks damage cap.",
                "materiaSlots": [
                    {"materiaId": "item_costly_punch", "stat": "HP% +999%", "role": "One-shots tough targets"},
                    {"materiaId": "item_mug", "stat": "VIT +100", "role": "100% Steal + damage in one action"},
                    {"materiaId": "item_hell_blizzaga", "stat": "MAG +100", "role": "Instant-kills trash packs"},
                    {"materiaId": "item_status_ward", "stat": "SPR +100", "role": "Stops Stop/Death/Stun ambushes"},
                    {"materiaId": "item_aerial_drain", "stat": "ATK +100", "role": "Sustained HP heal"},
                    {"materiaId": "item_moogle_power", "stat": "LCK +100", "role": "Levels equipped Materia passively"},
                ],
            },
        ],
    }


def build_fusion_rules_json(fusion_txt: str = "", items: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    return build_full_fusion_rules(fusion_txt, items or {})


def download_enemy_portraits(enemies: list[dict[str, Any]]) -> tuple[int, int, int]:
    """Downloads compact Fandom thumbnails locally so the PWA works 100% offline."""
    out_dir = PORTRAITS_DIR / "enemies"
    out_dir.mkdir(parents=True, exist_ok=True)

    def _to_thumb_url(raw_url: str) -> str:
        if not raw_url:
            return ""
        if "/revision/latest" in raw_url and "scale-to-width-down" not in raw_url:
            return raw_url.replace("/revision/latest", "/revision/latest/scale-to-width-down/220", 1)
        return raw_url

    def _fetch_one(en: dict[str, Any]) -> tuple[str, str | None, bool]:
        eid = en["id"]
        url = _to_thumb_url(en["portrait"].get("imageUrl", ""))
        if not url:
            return eid, None, False
        ext_m = re.search(r"\.(png|jpe?g|webp|gif)(?:\?|$|/)", en["portrait"].get("imageFile", "") or url, flags=re.I)
        ext = f".{ext_m.group(1).lower()}" if ext_m else ".png"
        if ext == ".jpeg":
            ext = ".jpg"
        dest = out_dir / f"{eid}{ext}"
        rel_path = f"games/crisis-core-reunion/assets/portraits/enemies/{eid}{ext}"
        if dest.exists() and dest.stat().st_size > 200:
            return eid, rel_path, True
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PersonalGameWikiHub/4.0",
                "Referer": "https://finalfantasy.fandom.com/",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            if data and len(data) > 200:
                dest.write_bytes(data)
                return eid, rel_path, True
        except Exception:
            pass
        return eid, None, False

    ok = 0
    fail = 0
    by_id = {e["id"]: e for e in enemies}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_fetch_one, en) for en in enemies]
        for fut in as_completed(futures):
            eid, rel_path, success = fut.result()
            if success and rel_path:
                by_id[eid]["portrait"]["localPath"] = rel_path
                ok += 1
            else:
                fail += 1
    return ok, fail, len(enemies)


def make_png_rgba(width: int, height: int, pixel_fn) -> bytes:
    raw_rows = bytearray()
    for y in range(height):
        raw_rows.append(0)
        for x in range(width):
            r, g, b, a = pixel_fn(x, y, width, height)
            raw_rows.extend((r, g, b, a))

    def _chunk(ctype: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(ctype + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw_rows), 9)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def mako_icon_pixel(x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
    cx, cy = w / 2.0, h / 2.0
    dx, dy = (x - cx) / (w / 2.0), (y - cy) / (h / 2.0)
    dist = (dx * dx + dy * dy) ** 0.5
    r, g, b, a = 7, 11, 16, 255
    if 0.62 <= dist <= 0.76:
        return (0, 229, 163, 255)
    if 0.55 <= dist < 0.62 or 0.76 < dist <= 0.82:
        return (56, 189, 248, 200)
    if abs(dx) + abs(dy) < 0.36:
        t = 1.0 - (abs(dx) + abs(dy)) / 0.36
        return (int(20 + 180 * t), int(210 + 45 * t), int(170 + 70 * t), 255)
    if (abs(dx) < 0.04 and 0.4 < abs(dy) < 0.88) or (abs(dy) < 0.04 and 0.4 < abs(dx) < 0.88):
        return (0, 229, 163, 230)
    return (r, g, b, a)


def generate_visual_assets() -> None:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    PORTRAITS_DIR.mkdir(parents=True, exist_ok=True)

    icon_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <rect width="128" height="128" rx="26" fill="#070b10"/>
  <circle cx="64" cy="64" r="46" fill="none" stroke="#00e5a3" stroke-width="6"/>
  <circle cx="64" cy="64" r="35" fill="none" stroke="#38bdf8" stroke-width="2" stroke-dasharray="8 6"/>
  <polygon points="64,34 90,64 64,94 38,64" fill="#00e5a3" fill-opacity="0.22" stroke="#00e5a3" stroke-width="3"/>
  <circle cx="64" cy="64" r="9" fill="#00e5a3"/>
</svg>"""
    (ICONS_DIR / "icon.svg").write_text(icon_svg, encoding="utf-8")
    (ICONS_DIR / "icon-192.png").write_bytes(make_png_rgba(192, 192, mako_icon_pixel))
    (ICONS_DIR / "icon-512.png").write_bytes(make_png_rgba(512, 512, mako_icon_pixel))

    cover_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 320">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#070b10"/>
      <stop offset="55%" stop-color="#0d1b28"/>
      <stop offset="100%" stop-color="#062925"/>
    </linearGradient>
    <radialGradient id="glow" cx="72%" cy="48%" r="45%">
      <stop offset="0%" stop-color="#00e5a3" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#00e5a3" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="640" height="320" fill="url(#bg)"/>
  <rect width="640" height="320" fill="url(#glow)"/>
  <g stroke="#38bdf8" stroke-opacity="0.16" stroke-width="1">
    <path d="M0 64 H640 M0 128 H640 M0 192 H640 M0 256 H640"/>
    <path d="M80 0 V320 M160 0 V320 M240 0 V320 M320 0 V320 M400 0 V320 M480 0 V320 M560 0 V320"/>
  </g>
  <circle cx="470" cy="160" r="88" fill="none" stroke="#00e5a3" stroke-width="3" stroke-opacity="0.8"/>
  <circle cx="470" cy="160" r="64" fill="none" stroke="#38bdf8" stroke-width="2" stroke-dasharray="10 6"/>
  <polygon points="470,96 528,160 470,224 412,160" fill="#00e5a3" fill-opacity="0.18" stroke="#00e5a3" stroke-width="2.5"/>
  <text x="42" y="108" fill="#00e5a3" font-family="Segoe UI, sans-serif" font-size="16" font-weight="700" letter-spacing="4">SHINRA SOLDIER TERMINAL</text>
  <text x="42" y="156" fill="#e6f1f8" font-family="Segoe UI, sans-serif" font-size="34" font-weight="800">CRISIS CORE</text>
  <text x="42" y="192" fill="#38bdf8" font-family="Segoe UI, sans-serif" font-size="22" font-weight="700">FFVII REUNION</text>
  <rect x="42" y="218" width="150" height="30" rx="15" fill="#00e5a3" fill-opacity="0.18" stroke="#00e5a3"/>
  <text x="117" y="238" text-anchor="middle" fill="#00e5a3" font-family="Consolas, monospace" font-size="13" font-weight="700">HARD MODE WIKI</text>
</svg>"""
    (ASSETS_DIR / "cover.svg").write_text(cover_svg, encoding="utf-8")

    family_styles = [
        ("shinra", "#38bdf8", "SHINRA"),
        ("genesis-copy", "#f43f5e", "G-COPY"),
        ("angeal-copy", "#a855f7", "A-COPY"),
        ("wutai", "#f59e0b", "WUTAI"),
        ("beast", "#10b981", "BEAST"),
        ("machine", "#60a5fa", "MECH"),
        ("fiend", "#c084fc", "FIEND"),
        ("boss", "#ef4444", "BOSS"),
    ]
    for slug, color, label in family_styles:
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 160">
  <rect width="160" height="160" rx="16" fill="#070b10"/>
  <circle cx="80" cy="72" r="46" fill="{color}" fill-opacity="0.13" stroke="{color}" stroke-width="2.5"/>
  <polygon points="80,34 114,72 80,110 46,72" fill="none" stroke="{color}" stroke-width="2"/>
  <circle cx="80" cy="72" r="10" fill="{color}"/>
  <text x="80" y="142" text-anchor="middle" fill="{color}" font-family="Consolas, monospace" font-size="14" font-weight="700">{label}</text>
</svg>"""
        (PORTRAITS_DIR / f"family-{slug}.svg").write_text(svg, encoding="utf-8")


def validate_dataset(data_dir: Path) -> None:
    missions = json.loads((data_dir / "missions.json").read_text(encoding="utf-8"))
    enemies = json.loads((data_dir / "enemies.json").read_text(encoding="utf-8"))
    items = json.loads((data_dir / "items.json").read_text(encoding="utf-8"))
    shops = json.loads((data_dir / "shops.json").read_text(encoding="utf-8"))
    guides = json.loads((data_dir / "guides.json").read_text(encoding="utf-8"))
    fusion_rules = json.loads((data_dir / "fusion-rules.json").read_text(encoding="utf-8"))
    extra_path = data_dir / "compendium-extra.json"
    if not extra_path.exists():
        raise SystemExit("Validation FAILED: missing compendium-extra.json")
    extra = json.loads(extra_path.read_text(encoding="utf-8"))

    errors: list[str] = []

    if len(missions) != 300:
        errors.append(f"Expected exactly 300 missions, found {len(missions)}")
    if len(shops) != 16:
        errors.append(f"Expected exactly 16 shops, found {len(shops)}")
    if len(guides.get("dmwImages", [])) != 18:
        errors.append(f"Expected 18 DMW entries, found {len(guides.get('dmwImages', []))}")

    mission_ids = {m["id"] for m in missions}
    enemy_ids = {e["id"] for e in enemies}
    item_ids = {it["id"] for it in items}

    # Verify zero dirty placeholder item IDs or generic placeholder descriptions
    for iid in item_ids:
        if (
            re.fullmatch(r"item_\d+", iid)
            or "drop_rate" in iid
            or iid.startswith("item_none_")
            or iid in ("item_various", "item_adamantite_adamantite", "item_mag_mako_stone_fire", "item_esuna_materia", "item_poison_materia", "item_silence_materia")
        ):
            errors.append(f"Dirty item ID detected: {iid}")
    for it in items:
        if "Obtained from Crisis Core missions" in (it.get("description") or ""):
            errors.append(f"Generic placeholder description remained on {it['id']}")

    # Strict Relational Rule: no enemy drop/steal lists inside items.json
    for it in items:
        bad_keys = FORBIDDEN_ITEM_KEYS.intersection(it.keys())
        if bad_keys:
            errors.append(f"Strict Relational Rule violated on {it['id']}: forbidden keys {sorted(bad_keys)}")

    for en in enemies:
        for slot in ("commonDrop", "rareDrop", "commonSteal", "rareSteal"):
            iid = en["loot"].get(slot)
            if iid and iid not in item_ids:
                errors.append(f"Broken item ref {iid} in enemy {en['id']} slot {slot}")
        for sp in en.get("spawns", []):
            if sp["missionId"] not in mission_ids:
                errors.append(f"Broken mission ref {sp['missionId']} in enemy {en['id']}")

    no_enemy_missions = []
    missing_boss_guides = []
    for m in missions:
        if not m.get("bossEnemyIds"):
            errors.append(f"Mission {m['id']} has empty bossEnemyIds")
        if not m.get("bossEnemyIds") and not m.get("randomEnemyIds"):
            no_enemy_missions.append(m["id"])
        for pm in m.get("prerequisiteMissionIds", []):
            if pm not in mission_ids:
                errors.append(f"Broken prerequisiteMissionId {pm} in mission {m['id']}")
        cr = m.get("clearReward")
        if cr and cr.get("itemId") not in item_ids:
            errors.append(f"Broken clearReward {cr.get('itemId')} in mission {m['id']}")
        for tr in m.get("treasures", []):
            if tr.get("itemId") not in item_ids:
                errors.append(f"Broken treasure {tr.get('itemId')} in mission {m['id']}")
        for eid in m.get("bossEnemyIds", []) + m.get("randomEnemyIds", []):
            if eid not in enemy_ids:
                errors.append(f"Broken enemy ref {eid} in mission {m['id']}")
        bg = m.get("bossGuide")
        if not isinstance(bg, dict):
            missing_boss_guides.append(m["id"])
        else:
            for req_str in ("targetName", "encounterType", "threatRating", "summary", "proTip"):
                if not str(bg.get(req_str) or "").strip():
                    errors.append(f"Missing bossGuide.{req_str} in mission {m['id']}")
            t_ids = bg.get("targetEnemyIds") or []
            if not t_ids:
                errors.append(f"Empty bossGuide.targetEnemyIds in mission {m['id']}")
            for teid in t_ids:
                if teid not in enemy_ids:
                    errors.append(f"Broken bossGuide targetEnemyId {teid} in mission {m['id']}")
            loadout = bg.get("recommendedLoadout") or {}
            if not loadout.get("materia") or not loadout.get("accessories") or not str(loadout.get("statTargets") or "").strip():
                errors.append(f"Incomplete bossGuide.recommendedLoadout in mission {m['id']}")
            if not bg.get("weaknessesAndCounters") or not bg.get("keyAttacksToWatch") or len(bg.get("killSteps") or []) < 2:
                errors.append(f"Incomplete bossGuide tactics/steps in mission {m['id']}")

    if missing_boss_guides:
        errors.append(f"{len(missing_boss_guides)} mission(s) missing bossGuide: {missing_boss_guides[:10]}")

    if no_enemy_missions:
        errors.append(f"{len(no_enemy_missions)} mission(s) have 0 enemies: {no_enemy_missions[:10]}")

    shop_by_id = {s["id"]: s for s in shops}
    sec5 = shop_by_id.get("shop_sector_5_materia_shop")
    sec7 = shop_by_id.get("shop_sector_7_shop")
    if not sec5 or len(sec5.get("stock", [])) != 6:
        errors.append(f"Sector 5 Materia Shop expected 6 items, found {len(sec5.get('stock', [])) if sec5 else 0}")
    if not sec7 or len(sec7.get("stock", [])) != 12:
        errors.append(f"Sector 7 Shop expected 12 items, found {len(sec7.get('stock', [])) if sec7 else 0}")

    for sh in shops:
        if sh.get("unlockMissionId") and sh["unlockMissionId"] not in mission_ids:
            errors.append(f"Broken shop unlockMissionId {sh['unlockMissionId']} in {sh['id']}")
        for st in sh.get("stock", []):
            if st["itemId"] not in item_ids:
                errors.append(f"Broken shop stock itemId {st['itemId']} in {sh['id']}")

    mission_by_id = {m["id"]: m for m in missions}
    enemy_by_id = {e["id"]: e for e in enemies}

    mission_enemies = {
        m["id"]: set(m.get("bossEnemyIds", []) + m.get("randomEnemyIds", []))
        for m in missions
    }
    valid_stages = {"early", "early-mid", "mid-late", "endgame"}

    for b in guides.get("levelBrackets", []):
        for mid in b.get("priorityMissions", []):
            if mid not in mission_ids:
                errors.append(f"Broken guide bracket mission ref {mid}")
    for fm in guides.get("farmingMatrix", []):
        mid = fm.get("bestMissionId")
        eid = fm.get("enemyId")
        iid = fm.get("itemId")
        st = fm.get("stage")
        if st not in valid_stages:
            errors.append(f"Invalid farmingMatrix stage '{st}' in {fm.get('resource')}")
        if mid and mid not in mission_ids:
            errors.append(f"Broken farmingMatrix mission ref {mid}")
        if eid and eid not in enemy_ids:
            errors.append(f"Broken farmingMatrix enemy ref {eid}")
        if iid and iid not in item_ids:
            errors.append(f"Broken farmingMatrix item ref {iid}")
        if mid and eid:
            if eid not in mission_enemies.get(mid, set()):
                errors.append(f"FarmingMatrix mismatch: {eid} does not spawn in {mid}")
        if fm.get("category") == "Fusion Stats" and eid and iid:
            en_obj = enemy_by_id[eid]
            if iid not in en_obj["loot"].values():
                errors.append(f"FarmingMatrix mismatch: {iid} is not in {eid} loot")
    for d in guides.get("dmwImages", []):
        if d.get("missionId") and d["missionId"] not in mission_ids:
            errors.append(f"Broken dmw mission ref {d['missionId']}")
        if d.get("boostMateriaId") and d["boostMateriaId"] not in item_ids:
            errors.append(f"Broken dmw boostMateriaId {d['boostMateriaId']}")
    for ms in guides.get("missablesByChapter", []):
        if ms.get("missionId") and ms["missionId"] not in mission_ids:
            errors.append(f"Broken missables mission ref {ms['missionId']}")
    for sec in guides.get("sections", []):
        refs = sec.get("refs", {})
        for mid in refs.get("missions", []):
            if mid not in mission_ids:
                errors.append(f"Broken guide section mission ref {mid}")
        for iid in refs.get("items", []):
            if iid not in item_ids:
                errors.append(f"Broken guide section item ref {iid}")

    for rec in fusion_rules.get("keyRecipes", []):
        if rec.get("resultId") not in item_ids:
            errors.append(f"Broken fusion recipe resultId {rec.get('resultId')}")

    mat_catalog = fusion_rules.get("materiaCatalog") or {}
    for it in items:
        if it.get("category") == "materia" and it["id"] not in mat_catalog:
            errors.append(f"Materia {it['id']} missing from fusion-rules.json materiaCatalog")
    for ov in fusion_rules.get("specialOverrides", []):
        if ov.get("resultId") not in item_ids:
            errors.append(f"Broken specialOverride resultId {ov.get('resultId')}")

    # Validate compendium-extra.json
    story_chapters = extra.get("storyChapters", [])
    trophies = extra.get("trophies", [])
    mail_senders = extra.get("mailSenders", [])
    magic_pots = extra.get("magicPotEncounters", [])
    if len(story_chapters) != 10:
        errors.append(f"Expected 10 storyChapters, found {len(story_chapters)}")
    if len(trophies) != 51:
        errors.append(f"Expected 51 trophies, found {len(trophies)}")
    if len(mail_senders) != 20:
        errors.append(f"Expected 20 mailSenders, found {len(mail_senders)}")
    if len(magic_pots) != 6:
        errors.append(f"Expected 6 magicPotEncounters, found {len(magic_pots)}")
    story_ids = {sc["id"] for sc in story_chapters}
    for sc in story_chapters:
        for b in sc.get("bosses", []):
            if b.get("enemyId") not in enemy_ids:
                errors.append(f"Broken story boss enemyId {b.get('enemyId')} in {sc['id']}")
    for tr in trophies:
        if tr.get("missionId") and tr["missionId"] not in mission_ids:
            errors.append(f"Broken trophy missionId {tr['missionId']} in {tr['id']}")
        if tr.get("storyChapterId") and tr["storyChapterId"] not in story_ids:
            errors.append(f"Broken trophy storyChapterId {tr['storyChapterId']} in {tr['id']}")
    for mp in magic_pots:
        if mp.get("missionId") not in mission_ids:
            errors.append(f"Broken magicPot missionId {mp.get('missionId')}")
        if mp.get("rewardItemId") and mp["rewardItemId"] not in item_ids:
            errors.append(f"Broken magicPot rewardItemId {mp['rewardItemId']}")
        for rq in mp.get("requests", []):
            if rq.get("itemId") and rq["itemId"] not in item_ids:
                errors.append(f"Broken magicPot request itemId {rq['itemId']}")
    for se in (extra.get("mechanics") or {}).get("statusEffects", []):
        for iid in se.get("itemIds", []):
            if iid not in item_ids:
                errors.append(f"Broken statusEffect itemId {iid} in {se['id']}")

    for pb in guides.get("farmingPlaybooks", []):
        if pb.get("bestMissionId") and pb["bestMissionId"] not in mission_ids:
            errors.append(f"Broken playbook bestMissionId {pb['bestMissionId']}")
        if pb.get("enemyId") and pb["enemyId"] not in enemy_ids:
            errors.append(f"Broken playbook enemyId {pb['enemyId']}")
        for iid in pb.get("recommendedGear", []):
            if iid not in item_ids:
                errors.append(f"Broken playbook gear {iid}")
        for st in pb.get("steps", []):
            tier = st.get("tier")
            smid = st.get("missionId")
            seid = st.get("enemyId")
            if tier not in valid_stages:
                errors.append(f"Invalid playbook step tier '{tier}' in {pb['id']}")
            if smid and smid not in mission_ids:
                errors.append(f"Broken playbook step missionId {smid}")
            if seid:
                if seid not in enemy_ids:
                    errors.append(f"Broken playbook step enemyId {seid} in {pb['id']}")
                elif smid and seid not in mission_enemies.get(smid, set()):
                    errors.append(f"Playbook step mismatch in {pb['id']}: {seid} does not spawn in {smid}")
            for giid in st.get("gearIds", []):
                if giid not in item_ids:
                    errors.append(f"Broken playbook step gearId {giid} in {pb['id']}")

    for sg in guides.get("statLevelingGuides", []):
        for k in ("consumableItemId", "makoStoneId", "statStoneId", "maxItemId"):
            if sg.get(k) and sg[k] not in item_ids:
                errors.append(f"Broken statGuide {sg['id']} {k}={sg[k]}")
        for iid in sg.get("targetMateriaIds", []):
            if iid not in item_ids:
                errors.append(f"Broken statGuide targetMateria {iid}")
        for ph in sg.get("phases", []):
            if ph.get("missionId") and ph["missionId"] not in mission_ids:
                errors.append(f"Broken statGuide phase missionId {ph['missionId']}")

    for bp in guides.get("endgameBuildBlueprints", []):
        for iid in bp.get("accessories", []):
            if iid not in item_ids:
                errors.append(f"Broken blueprint accessory {iid}")
        for ms in bp.get("materiaSlots", []):
            if ms.get("materiaId") not in item_ids:
                errors.append(f"Broken blueprint materiaId {ms.get('materiaId')}")

    if errors:
        for err in errors[:30]:
            print(f"[ERROR] {err}", file=sys.stderr)
        raise SystemExit(f"Validation FAILED with {len(errors)} error(s).")

    boss_guide_count = sum(1 for m in missions if isinstance(m.get("bossGuide"), dict))
    boss_eid_count = sum(1 for m in missions if m.get("bossEnemyIds"))
    print(
        f"[OK] Validated Crisis Core Reunion v4 dataset: "
        f"{len(missions)} missions (0 enemy-less, {boss_eid_count} bossEnemyIds, {boss_guide_count} boss guides), "
        f"{len(enemies)} enemies, {len(items)} items, {len(shops)} shops, "
        f"{len(guides.get('dmwImages', []))} DMW, {len(trophies)} trophies, {len(story_chapters)} chapters, "
        f"{len(mail_senders)} mail senders, {len(magic_pots)} magic pots, "
        f"0 broken IDs, Strict Relational Rule passed."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing JSON datasets")
    parser.add_argument("--download-portraits", action="store_true", help="Bundle compact enemy portraits locally for offline PWA")
    args = parser.parse_args()

    if args.validate_only:
        validate_dataset(DATA_DIR)
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    generate_visual_assets()

    print("[1/6] Fetching mission pages (M1–M10)...")
    mission_pages = fetch_pages_by_titles([t for _, t, _ in BRANCH_TITLES])
    missions = parse_all_missions(mission_pages)
    valid_mids = {m["id"] for m in missions}
    print(f"      Parsed {len(missions)} missions.")

    print("[2/6] Fetching enemy, boss & special encounter pages...")
    enemy_titles = fetch_category_members("Category:Enemies_in_Crisis_Core_-Final_Fantasy_VII-")
    boss_titles = fetch_category_members("Category:Bosses_in_Crisis_Core_-Final_Fantasy_VII-")
    boss_page_titles = set(boss_titles) | {
        "Bahamut (Crisis Core boss)",
        "Bahamut Fury (Crisis Core boss)",
        "Ifrit (Crisis Core boss)",
    }
    all_enemy_titles = sorted(set(enemy_titles) | boss_page_titles | set(EXTRA_ENEMY_PAGES))
    enemy_pages = fetch_pages_by_titles(all_enemy_titles)
    bestiary_index_pages = fetch_pages_by_titles(["Crisis Core -Final Fantasy VII- enemies"])
    idx_txt = bestiary_index_pages.get("Crisis Core -Final Fantasy VII- enemies", "")
    boss_names: set[str] = {"minerva", "bahamut", "bahamut fury", "ifrit", "sephiroth", "angeal penance", "genesis", "genesis avatar"}
    gallery_image_map: dict[str, str] = {}
    for line in idx_txt.splitlines():
        if "|" in line:
            left, right = line.split("|", 1)
            left_s = left.strip()
            if re.search(r"\.(?:png|jpe?g|webp|gif)$", left_s, flags=re.I):
                ename = clean_wiki_text(right).strip()
                if ename:
                    gallery_image_map.setdefault(ename.lower(), left_s)
    if "==Bosses==" in idx_txt:
        boss_sec = idx_txt.split("==Bosses==", 1)[1]
        for line in boss_sec.splitlines():
            if "|" in line:
                boss_names.add(clean_wiki_text(line.split("|", 1)[1]).lower())

    enemies, enemy_name_to_id, image_files = parse_enemies(enemy_pages, boss_names, boss_page_titles, valid_mids, gallery_image_map)
    img_urls = fetch_image_urls(image_files)
    for en in enemies:
        fname = en["portrait"]["imageFile"].replace("_", " ").lower().strip()
        if fname and fname in img_urls:
            en["portrait"]["imageUrl"] = img_urls[fname]
        # Preserve already-bundled local portrait if present on disk
        for ext in (".png", ".jpg", ".webp", ".gif"):
            cand = PORTRAITS_DIR / "enemies" / f"{en['id']}{ext}"
            if cand.exists() and cand.stat().st_size > 200:
                en["portrait"]["localPath"] = f"games/crisis-core-reunion/assets/portraits/enemies/{en['id']}{ext}"
                break
    if args.download_portraits:
        print("      Bundling compact enemy portraits locally for offline PWA...")
        ok_p, fail_p, tot_p = download_enemy_portraits(enemies)
        print(f"      Portraits bundled: {ok_p}/{tot_p} succeeded ({fail_p} fallback).")
    print(f"      Parsed {len(enemies)} verified enemies/bosses.")

    print("[3/6] Fetching items, accessories, materia & all 16 shops...")
    item_titles = [
        "Crisis Core -Final Fantasy VII- items",
        "Crisis Core -Final Fantasy VII- accessories",
        "Command materia (Crisis Core)",
        "Magic materia (Crisis Core)",
        "Support materia (Crisis Core)",
        "Special materia",
        "Shop (Crisis Core)",
        "Materia Fusion",
    ]
    item_pages = fetch_pages_by_titles(item_titles)
    items_dict, shops, materia_table_meta = parse_items_and_shops(item_pages)
    print(f"      Parsed {len(shops)} shops.")

    print("[4/6] Reconciling Item <-> Enemy <-> Mission <-> Shop links & Boss Kill Guides...")
    reconcile_relations(missions, enemies, enemy_name_to_id, items_dict, shops)
    attach_mission_boss_guides(missions, enemies, items_dict)
    enrich_items_metadata(items_dict, materia_table_meta)
    items_list = sorted(items_dict.values(), key=lambda x: (x["category"], x["name"].lower()))

    print("[5/6] Writing normalized JSON databases...")
    guides = build_guides_json()
    fusion_rules = build_fusion_rules_json(item_pages.get("Materia Fusion", ""), items_dict)
    compendium_extra = build_compendium_extra_json(enemies, items_dict, missions)

    (DATA_DIR / "missions.json").write_text(json.dumps(missions, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "enemies.json").write_text(json.dumps(enemies, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "items.json").write_text(json.dumps(items_list, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "shops.json").write_text(json.dumps(shops, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "guides.json").write_text(json.dumps(guides, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "fusion-rules.json").write_text(json.dumps(fusion_rules, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "compendium-extra.json").write_text(json.dumps(compendium_extra, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[6/6] Running strict integrity validation...")
    validate_dataset(DATA_DIR)


if __name__ == "__main__":
    main()
