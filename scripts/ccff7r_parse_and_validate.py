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
) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
    enemies: list[dict[str, Any]] = []
    name_to_id: dict[str, str] = {}
    image_files: list[str] = []

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
        if image_file:
            image_files.append(image_file)

        loc_text = stats_fields.get("_all_locations", "") + "\n" + info_fields.get("_all_locations", "")
        mission_codes = []
        for mc in re.findall(r"M\d+-\d+-\d+", loc_text):
            if mc in valid_mission_ids and mc not in mission_codes:
                mission_codes.append(mc)

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
        nulls = [clean_wiki_text(x).strip() for x in re.split(r",|<br\s*/?>", stats_fields.get("null", "")) if clean_wiki_text(x).strip()]
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
            elif "null" in ev and elabel not in nulls:
                nulls.append(elabel)
            elif "absorb" in ev and elabel not in absorb:
                absorb.append(elabel)
            elif "immune" in ev and elabel not in immune:
                immune.append(elabel)
        for status_k in ("poison", "silence", "stun", "stop", "death", "blow away"):
            val = clean_wiki_text(stats_fields.get(status_k, ""))
            if val.lower() == "immune":
                immune.append(status_k.title())

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
    for ptitle, subcat in materia_pages:
        mtxt = pages.get(ptitle, "")
        for row in parse_wikitable_rows(mtxt):
            if len(row) < 3:
                continue
            name = canonical_item_name(row[0])
            if not name or name.lower() in ("name", "materia"):
                continue
            desc = clean_wiki_text(row[2])
            ensure_item(name, "materia", subcat, desc, None)

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

    return items, shops


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
                "priorityMissions": ["M4-4-3", "M7-2-1", "M7-2-2", "M7-2-5", "M6-2-1", "M6-2-3", "M8-2-1"],
                "expRoute": "Push M3-2-x and M5-1-x; interrupt boss Skill Power gauges with Command Materia while in Battle Stance.",
                "spGilRoute": "Grab Sector 7 Shop in M4-4-3 chest and buy Mog's Amulet (10,000 Gil) + Brigand's Gloves (10,000 Gil) immediately.",
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
                    "gear": "Adaman Bangle (M7-3-6), Brutal (M7-4-6), Status Ward + Hell-aga, Buster Sword 23%+ (Damage Break)",
                },
                "priorityMissions": ["M7-3-6", "M7-4-6", "M7-5-3", "M8-4-4", "M6-6-3", "M10-2-3"],
                "expRoute": "Farm M6-5-x and M7-4-x with Darkness or Hell Blizzaga + Status Ward; hit 23% Buster Sword Proficiency for free Break Damage Limit.",
                "spGilRoute": "Unlock Bone Village Outlet in M7-5-3; start farming Lesser Worms in M6-6-3 for Dark Matter & Rune Armlet Gil.",
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
            {"category": "EXP", "resource": "Fast EXP (Endgame)", "bestMissionId": "M8-6-4", "enemyId": "enemy_scissor_chitin", "itemId": "item_costly_punch", "setup": "Costly Punch + Brutal/Genji Glove + Barrier", "method": "Clear Scissor Chitins in M8-6-4; fast spawn loop and solid Gil.", "yield": "~5,460 EXP / Chitin"},
            {"category": "EXP", "resource": "Early/Mid EXP & Mob Wipe", "bestMissionId": "M6-5-3", "enemyId": None, "itemId": "item_hell_blizzaga", "setup": "Status Ward + Hell Blizzaga + Mog's Amulet", "method": "Status Ward grants immunity while Hell Blizzaga instant-deaths non-boss mobs.", "yield": "Fast 6–7★ EXP & Stone drops"},
            {"category": "SP & Gil", "resource": "Best SP & Gil Farm", "bestMissionId": "M9-5-3", "enemyId": "enemy_three_stars", "itemId": "item_mogs_amulet", "setup": "Mog's Amulet + Jeweled Ring + Precious Watch + Mug", "method": "Farm Three Stars (20,000 SP) & Tycoon in M9-5-3; Precious Watch doubles Gil, Jeweled Ring doubles item drops.", "yield": "20,000+ SP + 50k+ Gil/min"},
            {"category": "SP & Gil", "resource": "Midgame SP + Dark Matter", "bestMissionId": "M6-6-3", "enemyId": "enemy_lesser_worm", "itemId": "item_dark_matter", "setup": "Mog's Amulet + Costly Punch / Darkness", "method": "Run intersections in M6-6-3 for Lesser Worms & Mover EX.", "yield": "Dark Matter + high SP"},
            {"category": "SP & Gil", "resource": "99x Phoenix Down / Gil", "bestMissionId": "M9-6-6", "enemyId": "enemy_minerva", "itemId": "item_phoenix_down", "setup": "Mug + Brigand's Gloves + Wall + 99,999 HP", "method": "Mug Minerva once per attempt to steal 99x Phoenix Downs (keep or sell for 495k Gil).", "yield": "99 Phoenix Downs / run"},
            {"category": "Fusion Stats", "resource": "Dark Matter (MAG +1)", "bestMissionId": "M6-6-3", "enemyId": "enemy_lesser_worm", "itemId": "item_dark_matter", "setup": "Mog's Amulet (Sector 7 Shop M4-4-3) + Jeweled Ring", "method": "Common drop from Lesser Worms; fastest base for 98/980% Libra conversion.", "yield": "1–2 Dark Matter / fight"},
            {"category": "Fusion Stats", "resource": "Fat Chocobo Feather (HP +10%)", "bestMissionId": "M9-2-6", "enemyId": "enemy_jabberwock", "itemId": "item_fat_chocobo_feather", "setup": "Mog's Amulet + Brigand's Gloves + Mug", "method": "Steal/Rare Drop from Jabberwock (M9-2-6) or Humbaba (M6-6-6); or stack HP% with Shinra Shop Potions.", "yield": "1–3 Feathers / fight"},
            {"category": "Fusion Stats", "resource": "Adamantite (VIT +1)", "bestMissionId": "M9-6-5", "enemyId": "enemy_goliath", "itemId": "item_adamantite", "setup": "Mug + Brigand's Gloves + Mog's Amulet", "method": "Drop & Common Steal from Goliath in M9-6-5 (also Crazy Sword in M7-6-4/M9-4-1 & Grandpanzer in M9-3-3).", "yield": "1+ Adamantite / fight"},
            {"category": "Fusion Stats", "resource": "Mythril (SPR +1)", "bestMissionId": "M3-4-6", "enemyId": "enemy_g_purgatorio", "itemId": "item_mythril", "setup": "Mug + Brigand's Gloves + Mog's Amulet", "method": "Rare Drop & Common Steal from G Purgatorio in M3-4-6 (also M3-5-1–M3-5-3, M8-6-6), or convert +98 Libra.", "yield": "1+ Mythril / fight"},
            {"category": "Fusion Stats", "resource": "Hero Drink (ATK +1)", "bestMissionId": "M9-6-3", "enemyId": "enemy_master_blade", "itemId": "item_hero_drink", "setup": "Mog's Amulet + Brigand's Gloves + Mug", "method": "Rare Drop & Steal from Master Blade (M9-6-3) or Rare Steal from Iron Claw (M6-5-6 / M9-3-6).", "yield": "1+ Hero Drink / fight"},
            {"category": "Fusion Stats", "resource": "Gysahl Greens (LCK +1) / Zeio Nut / Lunar Harp", "bestMissionId": "M9-5-5", "enemyId": None, "itemId": "item_gysahl_greens", "setup": "M9-6-x chests + Dark Matter 98 conversion", "method": "Convert a +98 Dark Matter Libra with 1x Gysahl Greens, Zeio Nut, or Lunar Harp instead of farming 99x.", "yield": "1 catalyst converts +98!"},
            {"category": "Reunion Systems", "resource": "Materia Mastering (AFK Loop)", "bestMissionId": "M1-1-1", "enemyId": "enemy_sentry", "itemId": "item_moogle_power", "setup": "1–2 Mastered Moogle Power + Faerie Ring / Regen", "method": "Sit in M1-1-1 with weak troopers; DMW reels spin nonstop and Moogle Power levels all 6 slots.", "yield": "Masters all 6 slots AFK"},
            {"category": "Reunion Systems", "resource": "Buster Sword Proficiency 100%", "bestMissionId": "M1-2-1", "enemyId": None, "itemId": None, "setup": "Battle Stance + M1-2-1 (Guards) + M1-1-3 (Kills)", "method": "M1-2-1 gunfire for Perfect Guard (31.66%), M1-1-3 for Strong Attack & Command Kills (63.3%), M9-6-5 for Barrier Pierce (5%).", "yield": "Damage Break @ 23% / Barrier Pierce @ 47%"},
            {"category": "Reunion Systems", "resource": "DMW 100% (Genji Armor)", "bestMissionId": "M1-1-1", "enemyId": None, "itemId": "item_genji_armor", "setup": "Equip QMC+/Shade DMW Materia + Faerie Ring", "method": "Equip character/summon boost Materia (Octaslash, Healing Wave, etc.) and AFK in M1-1-1 until 100%.", "yield": "Unlocks Genji Armor"},
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
        "missablesByChapter": [
            {"id": "miss_ch1_fort_tamblin", "chapter": "Chapter 1", "title": "Hero of the Wutai War? (All 16 Groups)", "category": "Trophy / Gear", "detail": "In Fort Tamblin Courtyard, defeat all 16 enemy groups (including rotating walls & watchtowers) to receive the top evaluation from Lazard.", "missionId": None},
            {"id": "miss_ch1_cursed_ring", "chapter": "Chapter 1", "title": "Cursed Ring (Supply Pod)", "category": "Accessory", "detail": "Before departing for Wutai, inspect the Supply Pod 20 times in the Training Room/briefing area to receive Cursed Ring.", "missionId": None},
            {"id": "miss_ch2_mako_miner", "chapter": "Chapter 2", "title": "Master Mako Stone Miner / Materia Room", "category": "Trophy", "detail": "Complete all Materia Room mini-requests in Shinra Building before progressing to Banora.", "missionId": None},
            {"id": "miss_ch2_fan_clubs", "chapter": "Chapter 2–3", "title": "Join 3 Fan Clubs (Genesis, Angeal, LOVELESS)", "category": "Mail Senders", "detail": "Talk to the fans in Sector 8 Fountain & Loveless Avenue in Ch. 2 or Ch. 3 (last chance!) for Mail Completionist.", "missionId": None},
            {"id": "miss_ch4_minigames", "chapter": "Chapter 4", "title": "Aerith Affection & Sector 5/8 Mini-Games", "category": "Trophies", "detail": "Win Perfume Blending 3x perfectly, Number Guessing, Wallet Catch, and Spy Catching before leaving Midgar.", "missionId": None},
            {"id": "miss_ch5_reporter_silver", "chapter": "Chapter 5", "title": "Reporter Mail & Silver Elite Mission NPC", "category": "Missions & Mail", "detail": "Do NOT report the Sector 8 Reporter; answer his quiz. Talk to the Shinra Entrance employee for Silver Elite missions & mail.", "missionId": None},
            {"id": "miss_ch6_cissnei_mail", "chapter": "Chapter 6", "title": "Zack Fan Club (Talk to Cissnei in Junon)", "category": "Mail Senders", "detail": "After Junon Defense, speak to Cissnei before leaving Junon; then finish with the Shinra receptionist in Ch. 7.", "missionId": None},
            {"id": "miss_ch7_point_of_no_return", "chapter": "Chapter 7 (CRITICAL)", "title": "Midgar Point of No Return — All 16 NPC Mission Chains", "category": "Point of No Return", "detail": "Leaving Midgar at the end of Ch. 7 permanently locks all Midgar NPC mission givers (M1-2-x, M2-1-x, M2-2-x, M4-3-x, M6-2-x, M7-1-x), Flower Wagon, and Fan Club mail!", "missionId": "M6-2-1"},
            {"id": "miss_ch8_phoenix", "chapter": "Chapter 8", "title": "Phoenix DMW Summon (Nibelheim Water Tower)", "category": "MISSABLE DMW", "detail": "Talk to the boy near the Nibelheim Inn to start Seven Wonders, then examine the Water Tower to earn Phoenix. Only missable DMW!", "missionId": None},
            {"id": "miss_ch9_qmc_plus", "chapter": "Chapter 9", "title": "Research Dept. QMC+ Shop (Gongaga Chest)", "category": "MISSABLE SHOP", "detail": "Open the hidden chest in Gongaga Village outskirts in Ch. 9/10 to unlock Research Dept. QMC+ before the final dungeon.", "missionId": None},
        ],
        "sections": [
            {
                "id": "guide_exp_leveling",
                "title": "1. EXP & Leveling Guide (Lv. 1–99)",
                "badge": "Leveling",
                "summary": "Fastest EXP progression brackets, DMW EXP mechanics, and why M8-6-4 Scissor Chitins dominates endgame leveling.",
                "refs": {"missions": ["M1-1-1", "M6-5-3", "M8-6-4", "M9-6-4"], "items": ["item_costly_punch", "item_hell_blizzaga", "item_status_ward"]},
                "blocks": [
                    {"heading": "Early to Midgame (Lv. 1–40)", "body": "Crisis Core ties level-ups to hidden EXP + DMW triple-number rolls (7-7-7). Progress M1, M3, M4, and M7 missions early; once you unlock Status Ward + Hell Blizzaga, wipe 6–7★ encounters in seconds."},
                    {"heading": "Endgame EXP (M8-6-4 Scissor Chitins)", "body": "Equip Costly Punch + Brutal or Genji Glove (or Buster Sword at 23%+ proficiency) and loop M8-6-4 (Scissor Chitins) or M9-6-x encounters. High-level enemies feed huge hidden EXP so DMW 7-7-7 triggers frequently."},
                ],
            },
            {
                "id": "guide_sp_gil",
                "title": "2. SP & Gil Farming Master Guide",
                "badge": "Economy",
                "summary": "Mog's Amulet + Jeweled Ring economy break, M9-5-3 Three Stars, M6-6-3 Lesser Worms, and Minerva's 99x Phoenix Downs.",
                "refs": {"missions": ["M4-4-3", "M6-6-3", "M9-5-3", "M9-6-6"], "items": ["item_mogs_amulet", "item_jeweled_ring", "item_phoenix_down", "item_genji_helm"]},
                "blocks": [
                    {"heading": "Mandatory Farming Gear", "body": "Buy Mog's Amulet (10,000 Gil, Sector 7 Shop via M4-4-3) so enemies always drop Rare Drops, and Brigand's Gloves (10,000 Gil) for 100% Steal/Mug success. In Online Shop Shade (M9-5-4), buy Jeweled Ring (10,000 Gil) to double item/Materia drop quantity and Precious Watch (10,000 Gil) to double Gil earned from battles."},
                    {"heading": "M9-5-3 (Three Stars) & Minerva", "body": "M9-5-3 is the #1 SP and Gil farm in Reunion—Three Stars and Tycoon yield massive SP plus sellable Mythril Armlets and Tri-Thundaga. If you already unlocked M9-6-6, Mug Minerva for 99x Phoenix Downs (495,000 Gil per run) and flee or die to repeat."},
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
                "title": "5. Magic Pot Complete Encounters Guide",
                "badge": "Genji Shield",
                "summary": "Exact locations and attack sequences for every Magic Pot encounter, including M10-2-3 (DMW) and M7-6-6 (Genji Shield).",
                "refs": {"missions": ["M10-2-3", "M7-6-6", "M2-2-6", "M2-5-4"], "items": ["item_genji_shield", "item_costly_punch", "item_gil_toss", "item_octaslash"]},
                "blocks": [
                    {"heading": "M10-2-3: Unlock Magic Pot DMW (Do This First!)", "body": "Equip Jump, Fira, Gravity, and Assault Twister. Enter M10-2-3 (Master Tonberry), dodge Tonberries until Magic Pot appears, do NOT attack it blindly—wait for its speech bubbles and cast Jump -> Fira -> Gravity -> Assault Twister in order."},
                    {"heading": "M7-6-6: Obtain Genji Shield", "body": "Equip Gil Toss, Costly Punch, Break Damage Limit (Brutal/Genji Glove/Buster Sword 23%+), and Octaslash Materia (Research Dept. QMC+). In M7-6-6, perform: Gil Toss -> Costly Punch -> 99,999 Damage -> Octaslash DMW. (Note: M2-2-6 & M2-5-4 also host early Magic Pots requesting Blizzard/Fire/Thunder/Gravity or Ultima.)"},
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
                "id": "farm_exp",
                "shortLabel": "EXP (Lv 1–99)",
                "title": "EXP & Character Leveling Playbook",
                "badge": "Lv 1 → 99",
                "summary": "How hidden EXP + DMW 7-7-7 level-ups work, and the fastest EXP missions from Chapter 1 to Lv 99.",
                "bestMissionId": "M8-6-4",
                "enemyId": "enemy_scissor_chitin",
                "recommendedGear": ["item_costly_punch", "item_brutal", "item_genji_glove", "item_status_ward", "item_hell_blizzaga"],
                "steps": [
                    {"stage": "Early (Lv 1–25 · Ch. 1–5)", "missionId": "M1-2-1", "detail": "Clear M1, M3, and M4 story-unlocked branches naturally. Level-ups occur when hidden EXP crosses a threshold AND the DMW hits 7-7-7; banked EXP carries over seamlessly so you never lose progress."},
                    {"stage": "Midgame (Lv 25–55 · Ch. 6–8)", "missionId": "M6-5-3", "detail": "Buy Status Ward + Hell Blizzaga from Wutai Secret Shop (M4-2-6). Pairing them gives immunity to status ailments while wiping non-boss encounters via instant Death for rapid 6–7★ EXP."},
                    {"stage": "Endgame (Lv 55–99 · Ch. 9+)", "missionId": "M8-6-4", "detail": "Farm Scissor Chitins in M8-6-4 (5,460 EXP each) with Costly Punch + Break Damage Limit, or clear Goliath encounters in M9-6-5 (23,264 EXP each) once your VIT/SPR are 200+."},
                ],
                "proTip": "You do NOT need to sit in one spot waiting for 7-7-7—hidden EXP accumulates silently and triggers multiple rapid level-ups as soon as the DMW rolls 7-7-7."
            },
            {
                "id": "farm_sp",
                "shortLabel": "SP (SOLDIER Pts)",
                "title": "SP (SOLDIER Points) Farming Playbook",
                "badge": "20,000+ SP/Kill",
                "summary": "Fund million-SP endgame Materia fusions and SP Master builds without running dry.",
                "bestMissionId": "M9-5-3",
                "enemyId": "enemy_three_stars",
                "recommendedGear": ["item_costly_punch", "item_mug", "item_mogs_amulet", "item_genji_glove"],
                "steps": [
                    {"stage": "Early / Mid (Ch. 4–7)", "missionId": "M6-6-3", "detail": "Convert duplicate low-rank Materia into SP via the Materia menu, and farm Mover EX / Lesser Worms in M6-6-3 while collecting Dark Matter."},
                    {"stage": "Endgame #1: Three Stars", "missionId": "M9-5-3", "detail": "Run M9-5-3 (Unusually Strong Monsters). Three Stars grants 20,000 SP per kill—equip Costly Punch + Break Damage Limit to one-shot packs on repeat."},
                    {"stage": "Endgame #2: Minerva", "missionId": "M9-6-6", "detail": "Each Minerva clear yields 40,000 SP (plus 99x Phoenix Downs via Mug). For pure speed per minute, M9-5-3 Three Stars remains faster."}
                ],
                "proTip": "Always keep a buffer of 500k+ SP before combining high-tier +98/+980% Materia—SP Turbo / SP Master also drain SP per hit in combat."
            },
            {
                "id": "farm_gil",
                "shortLabel": "Gil & Loot",
                "title": "Gil & Rare Drop Economy Playbook",
                "badge": "495k Gil / Run",
                "summary": "Break the game's Gil economy to afford 1,000,000 Gil Genji Helm and unlimited shop Materia.",
                "bestMissionId": "M9-5-3",
                "enemyId": "enemy_three_stars",
                "recommendedGear": ["item_precious_watch", "item_jeweled_ring", "item_mogs_amulet", "item_brigands_gloves"],
                "steps": [
                    {"stage": "Know the 3 Farming Accessories", "missionId": "M4-4-3", "detail": "Mog's Amulet (Sector 7 Shop M4-4-3) forces Rare Drops; Brigand's Gloves guarantees 100% Steal/Mug; Jeweled Ring doubles item drops; Precious Watch doubles battle Gil (both in Online Shop Shade M9-5-4)."},
                    {"stage": "M9-5-3 Three Stars & Tycoon Loop", "missionId": "M9-5-3", "detail": "Equip Mog's Amulet + Jeweled Ring + Precious Watch + Mug in M9-5-3. Sell stolen Tri-Thundaga / Mythril Armlets and dropped accessories for 50,000+ Gil/minute."},
                    {"stage": "Minerva 99x Phoenix Down Trick", "missionId": "M9-6-6", "detail": "Enter M9-6-6, Mug Minerva once to steal 99x Phoenix Downs, then intentionally lose or finish. Selling 99x Phoenix Downs nets 495,000 Gil per run."}
                ],
                "proTip": "Don't waste Gil on consumables late-game once you have Curaga + Aerial Drain; save 1,000,000 Gil first for Genji Helm in Online Shop Shade."
            },
            {
                "id": "farm_catalysts",
                "shortLabel": "Stat Catalysts",
                "title": "Max-Tier Fusion Material Playbook",
                "badge": "Reunion Meta",
                "summary": "Since Reunion removed repeatable Mission Clear Rewards, use the M6-6-3 Dark Matter + 98/980% Libra loop alongside direct catalyst farms.",
                "bestMissionId": "M6-6-3",
                "enemyId": "enemy_lesser_worm",
                "recommendedGear": ["item_mogs_amulet", "item_brigands_gloves", "item_jeweled_ring", "item_mug"],
                "steps": [
                    {"stage": "1. Dark Matter Base (Fastest Overall)", "missionId": "M6-6-3", "detail": "Equip Mog's Amulet + Jeweled Ring in M6-6-3. Lesser Worms drop Dark Matter reliably—stack 98 Dark Matter onto a cheap Libra Materia (+98 MAG), then fuse with JUST ONE target catalyst (Adamantite/Mythril/Hero Drink/Fat Chocobo Feather) to convert it!"},
                    {"stage": "2. Direct VIT & SPR Farms", "missionId": "M9-6-5", "detail": "Adamantite (VIT): Goliath in M9-6-5 (Drop & Steal), Crazy Sword in M7-6-4/M9-4-1, Grandpanzer in M9-3-3. Mythril (SPR): G Purgatorio in M3-4-6 / M8-6-6 (Rare Drop & Steal)."},
                    {"stage": "3. Direct ATK & HP% Farms", "missionId": "M9-6-3", "detail": "Hero Drink (ATK): Master Blade in M9-6-3 or Iron Claw in M6-5-6/M9-3-6. Fat Chocobo Feather (HP%): Jabberwock in M9-2-6 or Humbaba in M6-6-6 (also 50 Gil Shinra Potions amplify existing HP%!)."}
                ],
                "proTip": "Never farm 99 Adamantite or 99 Gysahl Greens manually unless you want to—98 Dark Matter + 1 single target catalyst achieves the exact same +100 stat!"
            },
            {
                "id": "farm_materia_mastery",
                "shortLabel": "Materia Mastery",
                "title": "Materia Leveling & AFK Mastering Playbook",
                "badge": "AFK M1-1-1",
                "summary": "How hidden Materia EXP and DMW slot 1–6 reels level Materia, plus the zero-effort M1-1-1 AFK setup.",
                "bestMissionId": "M1-1-1",
                "enemyId": "enemy_sentry",
                "recommendedGear": ["item_moogle_power", "item_faerie_ring", "item_safety_bit"],
                "steps": [
                    {"stage": "1. Unlock Moogle Power", "missionId": "M8-4-4", "detail": "Complete M8-4-4 (Suspicious Mail 4) to unlock Moogle on DMW, then buy Moogle Power Materia from Junon Souvenirs (M2-4-1)."},
                    {"stage": "2. Set Up the AFK M1-1-1 Loadout", "missionId": "M1-1-1", "detail": "Equip 1–2 Moogle Power Materia (levels ALL equipped Materia at once when Moogle triggers) in slots alongside the Materia you want to master, plus Faerie Ring (auto-Regen)."},
                    {"stage": "3. Let Reels Spin & Clear Mission", "missionId": "M1-1-1", "detail": "Enter M1-1-1, leave 1 Sentry alive (or hold block), and let DMW reels spin. CRITICAL: You MUST finish the mission before exiting—forfeiting discards Materia levels!"}
                ],
                "proTip": "Matching two numbers 1–6 levels the Materia in that exact slot number; triple matches jump +2 or +3 levels immediately."
            },
            {
                "id": "farm_buster_sword",
                "shortLabel": "Buster Sword 100%",
                "title": "Buster Sword Proficiency Playbook (Reunion)",
                "badge": "23% / 47% Perks",
                "summary": "Reunion-exclusive stance progression: unlock Damage Limit Break at 23% and Barrier Piercing at 47%.",
                "bestMissionId": "M1-2-1",
                "enemyId": None,
                "recommendedGear": ["item_costly_punch", "item_darkness"],
                "steps": [
                    {"stage": "Pool 1: Perfect Guard (31.66% cap)", "missionId": "M1-2-1", "detail": "Enter M1-2-1, hold Battle Stance near the rapid-fire Security Officers in the lower area, and absorb gunfire blocks repeatedly."},
                    {"stage": "Pool 2 & 3: Strong Attack + Command Kills (63.32%)", "missionId": "M1-1-3", "detail": "Enter M1-1-3 (50 Shinra Troopers). Enter Battle Stance before every swing or AoE Command Materia (Darkness / High Jump) until both pools cap out."},
                    {"stage": "Pool 4: Barrier Piercing (5% cap)", "missionId": "M9-6-5", "detail": "Wait until enemies cast Barrier/MBarrier in late missions like M9-6-5, then finish them while in Battle Stance to hit 100%."}
                ],
                "proTip": "Every time you see a boss charging a Skill Power bar in Reunion, enter Battle Stance and hit with Costly Punch—draining the gauge weakens or cancels their Limit Break."
            },
            {
                "id": "farm_dmw",
                "shortLabel": "DMW 100% (Genji)",
                "title": "100% DMW & Genji Armor Playbook",
                "badge": "18 Images",
                "summary": "Unlock all 7 Characters + 11 Summons/Chocobo Modes and push every entry to 100%.",
                "bestMissionId": "M1-1-1",
                "enemyId": None,
                "recommendedGear": ["item_genji_armor", "item_faerie_ring"],
                "steps": [
                    {"stage": "1. Secure Missable Ch. 8 Phoenix", "missionId": "M8-1-1", "detail": "Talk to the boy near Nibelheim Inn in Chapter 8 and examine the Water Tower for Phoenix (the ONLY missable DMW). Clear M8-1-1, M8-1-4, M8-1-6, M8-4-1..4, M8-5-6, M10-1-3, M10-2-3 for the rest."},
                    {"stage": "2. Summons vs. Character Memories", "missionId": "M10-2-3", "detail": "Summons & Chocobo Modes jump straight to 100% the very first time they trigger. Characters require viewing 6 memory scenes each (you can skip cutscenes and still get credit!)."},
                    {"stage": "3. AFK Farm Remaining % in M1-1-1", "missionId": "M1-1-1", "detail": "Buy DMW-boost Materia from Research Dept. QMC+ (Ch. 9), Junon Souvenirs (M2-4-1), and Bone Village Outlet (M7-5-3), equip them in M1-1-1 with Faerie Ring, and idle until 100% → Genji Armor!"}
                ],
                "proTip": "Check the Shops, DMW & Missables tab to check off all 18 DMW portraits and verify you bought the exact boost Materia."
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


def build_fusion_rules_json() -> dict[str, Any]:
    return {
        "statCategories": ["HP%", "MP%", "AP%", "ATK", "VIT", "MAG", "SPR", "LCK"],
        "rulesNotes": [
            "Consumables (Potion, Hi-Potion, X-Potion, Ether, Soma, Elixir) ONLY amplify an existing matching stat bonus on one of the fused Materia. On two +0 Materia they add +0.",
            "Mako Stones add +1 per 5 stones (max +40) or +10% per 5 stones (max +400%).",
            "Stat Stones add +1 per 3 stones (max +66) or +10% per 3 stones (max +660%).",
            "Max-tier fusion items (Hero Drink, Adamantite, Dark Matter, Mythril, Gysahl Greens, Fat Chocobo Feather, Lunar Harp, Zeio Nut) add +1 (max +100) or +10% (max +999%) per item.",
            "When building a Libra transfer Materia, stop at +98 (or +980% HP) so it remains open to item conversion during final fusion.",
        ],
        "keyRecipes": [
            {"result": "Costly Punch", "resultId": "item_costly_punch", "ingredientA": "Goblin Punch / Iron Fist / Magical Punch", "ingredientB": "Any DMW Materia (or Libra w/ +980% HP)", "note": "Hard Mode MVP: ignores defense, 99,999 damage at high HP."},
            {"result": "Magical Punch", "resultId": "item_magical_punch", "ingredientA": "Goblin Punch", "ingredientB": "Firaga / Blizzaga / Thundaga", "note": "Strong midgame bridge into Costly Punch."},
            {"result": "Aerial Drain", "resultId": "item_aerial_drain", "ingredientA": "High Jump", "ingredientB": "Drain / Osmose / Assault Twister", "note": "Grants invincibility frames during jump and heals to full HP."},
            {"result": "High Jump", "resultId": "item_high_jump", "ingredientA": "Jump", "ingredientB": "Darkness / Assault Twister", "note": "Upgraded jump; prerequisite for Aerial Drain."},
            {"result": "Darkness", "resultId": "item_darkness", "ingredientA": "Assault Twister / Jump", "ingredientB": "Drain / Gravity / Dark Fire", "note": "Fast midgame AoE HP-cost wave clear."},
            {"result": "Assault Twister+", "resultId": "item_assault_twister_plus", "ingredientA": "Assault Twister (M)", "ingredientB": "Vitality Up / Status Strike", "note": "Multi-hit spin attack; strong early Command Materia."},
            {"result": "Curaga", "resultId": "item_curaga", "ingredientA": "Cura", "ingredientB": "HP Up / Libra / Barrier", "note": "Full-heal staple; fuse with Potions/Feathers for +999% HP."},
            {"result": "Wall", "resultId": "item_wall", "ingredientA": "Barrier", "ingredientB": "MBarrier", "note": "Applies both Barrier and MBarrier in one cast."},
            {"result": "Hell Blizzaga", "resultId": "item_hell_blizzaga", "ingredientA": "Blizzaga", "ingredientB": "Status Strike / Poison / Silence / Stop", "note": "Pair with Status Ward for multi-ailment immunity + AoE Death."},
            {"result": "Hell Firaga", "resultId": "item_hell_firaga", "ingredientA": "Firaga", "ingredientB": "Status Strike / Poison / Silence / Stop", "note": "Pair with Status Ward for multi-ailment immunity + AoE Death."},
            {"result": "Hell Thundaga", "resultId": "item_hell_thundaga", "ingredientA": "Thundaga", "ingredientB": "Status Strike / Poison / Silence / Stop", "note": "Pair with Status Ward for multi-ailment immunity + AoE Death."},
            {"result": "Status Ward", "resultId": "item_status_ward", "ingredientA": "Buy: Wutai Secret Shop (M4-2-6, 40k Gil)", "ingredientB": "Or Esuna + Libra / Dispel", "note": "Protects against all statuses listed on paired Hell-aga Materia."},
            {"result": "Dualcast", "resultId": "item_dualcast", "ingredientA": "Buy: Online Shop Shade (M9-5-4)", "ingredientB": "Or High-Rank Magic + Ultima/Energy", "note": "Casts equipped Magic Materia twice per turn."},
            {"result": "Electrocute", "resultId": "item_electrocute", "ingredientA": "Thundaga (M)", "ingredientB": "Graviga / Flare / Energy", "note": "Massive multi-hit lightning magic burst."},
            {"result": "Energy", "resultId": "item_energy", "ingredientA": "Graviga / Flare", "ingredientB": "Status Ward / Dualcast / Libra", "note": "Non-elemental piercing magic; strong with Dualcast."},
            {"result": "Quake", "resultId": "item_quake", "ingredientA": "Graviga", "ingredientB": "Assault Twister+ / Darkness", "note": "Fast screen-wide AoE magic for farming."},
            {"result": "Ultima", "resultId": "item_ultima", "ingredientA": "Flare / Energy / Tri-Thundaga", "ingredientB": "DMW Materia / Libra", "note": "Highest single-cast AoE magic burst."},
            {"result": "Tri-Thundaga", "resultId": "item_tri_thundaga", "ingredientA": "Thundaga (M)", "ingredientB": "Steal: Three Stars (M9-5-3)", "note": "Triple lightning orbs; great for fusion rank ups."},
            {"result": "Mug", "resultId": "item_mug", "ingredientA": "Steal", "ingredientB": "Assault Twister / Vital Slash", "note": "Deals damage while stealing; essential for Minerva 99x Phoenix Downs."},
            {"result": "Gil Toss", "resultId": "item_gil_toss", "ingredientA": "Reward: M7-4-2 / M4-5-2", "ingredientB": "Command + Libra", "note": "Required for M7-6-6 Magic Pot (Genji Shield)."},
            {"result": "SP Master", "resultId": "item_sp_master", "ingredientA": "Reward: M9-6-5", "ingredientB": "SP Turbo + SP Barrier", "note": "Boosts damage & defense at SP cost; ideal with M9-5-3 SP farm."},
        ],
    }


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
    for m in missions:
        if not m.get("bossEnemyIds") and not m.get("randomEnemyIds"):
            no_enemy_missions.append(m["id"])
        cr = m.get("clearReward")
        if cr and cr.get("itemId") not in item_ids:
            errors.append(f"Broken clearReward {cr.get('itemId')} in mission {m['id']}")
        for tr in m.get("treasures", []):
            if tr.get("itemId") not in item_ids:
                errors.append(f"Broken treasure {tr.get('itemId')} in mission {m['id']}")
        for eid in m.get("bossEnemyIds", []) + m.get("randomEnemyIds", []):
            if eid not in enemy_ids:
                errors.append(f"Broken enemy ref {eid} in mission {m['id']}")

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

    for b in guides.get("levelBrackets", []):
        for mid in b.get("priorityMissions", []):
            if mid not in mission_ids:
                errors.append(f"Broken guide bracket mission ref {mid}")
    for fm in guides.get("farmingMatrix", []):
        mid = fm.get("bestMissionId")
        eid = fm.get("enemyId")
        iid = fm.get("itemId")
        if mid and mid not in mission_ids:
            errors.append(f"Broken farmingMatrix mission ref {mid}")
        if eid and eid not in enemy_ids:
            errors.append(f"Broken farmingMatrix enemy ref {eid}")
        if iid and iid not in item_ids:
            errors.append(f"Broken farmingMatrix item ref {iid}")
        if mid and eid:
            m_obj = mission_by_id[mid]
            if eid not in (m_obj.get("bossEnemyIds", []) + m_obj.get("randomEnemyIds", [])):
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

    for pb in guides.get("farmingPlaybooks", []):
        if pb.get("bestMissionId") and pb["bestMissionId"] not in mission_ids:
            errors.append(f"Broken playbook bestMissionId {pb['bestMissionId']}")
        if pb.get("enemyId") and pb["enemyId"] not in enemy_ids:
            errors.append(f"Broken playbook enemyId {pb['enemyId']}")
        for iid in pb.get("recommendedGear", []):
            if iid not in item_ids:
                errors.append(f"Broken playbook gear {iid}")
        for st in pb.get("steps", []):
            if st.get("missionId") and st["missionId"] not in mission_ids:
                errors.append(f"Broken playbook step missionId {st['missionId']}")

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

    print(
        f"[OK] Validated Crisis Core Reunion v3 dataset: "
        f"{len(missions)} missions (0 enemy-less), {len(enemies)} enemies, {len(items)} items, "
        f"{len(shops)} shops, {len(guides.get('dmwImages', []))} DMW, {len(guides.get('farmingPlaybooks', []))} playbooks, "
        f"{len(guides.get('statLevelingGuides', []))} stat guides, {len(guides.get('sections', []))} guide sections, "
        f"0 broken IDs, Strict Relational Rule passed."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing JSON datasets")
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
    if "==Bosses==" in idx_txt:
        boss_sec = idx_txt.split("==Bosses==", 1)[1]
        for line in boss_sec.splitlines():
            if "|" in line:
                boss_names.add(clean_wiki_text(line.split("|", 1)[1]).lower())

    enemies, enemy_name_to_id, image_files = parse_enemies(enemy_pages, boss_names, boss_page_titles, valid_mids)
    img_urls = fetch_image_urls(image_files)
    for en in enemies:
        fname = en["portrait"]["imageFile"].lower()
        if fname and fname in img_urls:
            en["portrait"]["imageUrl"] = img_urls[fname]
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
    items_dict, shops = parse_items_and_shops(item_pages)
    print(f"      Parsed {len(shops)} shops.")

    print("[4/6] Reconciling Item <-> Enemy <-> Mission <-> Shop links...")
    reconcile_relations(missions, enemies, enemy_name_to_id, items_dict, shops)
    items_list = sorted(items_dict.values(), key=lambda x: (x["category"], x["name"].lower()))

    print("[5/6] Writing normalized JSON databases...")
    guides = build_guides_json()
    fusion_rules = build_fusion_rules_json()

    (DATA_DIR / "missions.json").write_text(json.dumps(missions, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "enemies.json").write_text(json.dumps(enemies, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "items.json").write_text(json.dumps(items_list, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "shops.json").write_text(json.dumps(shops, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "guides.json").write_text(json.dumps(guides, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "fusion-rules.json").write_text(json.dumps(fusion_rules, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[6/6] Running strict integrity validation...")
    validate_dataset(DATA_DIR)


if __name__ == "__main__":
    main()
