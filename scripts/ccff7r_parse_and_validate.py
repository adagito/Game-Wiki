#!/usr/bin/env python3
"""
Crisis Core: Final Fantasy VII Reunion (Hard Mode)
Data Ingestion, Relational Normalization & Integrity Validation Script.

Uses Python 3 standard library only.
- Default run: fetches Fandom MediaWiki API data (cached under scripts/.cache/),
  normalizes all 300 missions, enemies, items/accessories/materia/shops, guides,
  and fusion rules into games/crisis-core-reunion/data/, generates PWA PNG/SVG
  assets, and validates zero broken IDs.
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
HEADERS = {"User-Agent": "PersonalGameWikiHub/1.0 (CrisisCoreReunion; static-build)"}

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

ITEM_ALIAS_MAP = {
    "soma drop": "Soma",
    "gysahl green": "Gysahl Greens",
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
    "atk up+": "ATK Up+",
    "atk up++": "ATK Up++",
    "vit+": "VIT Up",
    "vit up+": "VIT Up+",
    "vit up++": "VIT Up++",
    "mag+": "MAG Up",
    "mag up+": "MAG Up+",
    "mag up++": "MAG Up++",
    "spr+": "SPR Up",
    "spr up+": "SPR Up+",
    "spr up++": "SPR Up++",
    "lck+": "LCK Up",
    "libra": "Libra",
    "bronze bracers": "Bronze Armlet",
    "silver bracers": "Silver Armlet",
    "gold bracers": "Gold Armlet",
    "rune bracers": "Rune Armlet",
    "mithril": "Mythril",
    "zeio nut": "Zeio Nut",
    "fat chocobo feather": "Fat Chocobo Feather",
    "lunar harp": "Lunar Harp",
    "hero drink": "Hero Drink",
    "dark matter": "Dark Matter",
    "adamantite": "Adamantite",
    "gysahl greens": "Gysahl Greens",
    "mog's amulet": "Mog's Amulet",
    "mogs amulet": "Mog's Amulet",
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
    "minerva": "Minerva",
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
    s = text.replace("'", "").replace("’", "")
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
            f"pages_{i}_{chunk[0]}",
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
        data = cached_api_get(params, f"cat_{category}_{idx}")
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
            f"img_{i}_{chunk[0]}",
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

    # {{LA|Target|Label}} or {{A|Label}}
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

    # [[File:...]]
    s = re.sub(r"\[\[(?:File|Image):[^\]]+\]\]", "", s, flags=re.I)

    # [[Target|Display]] -> Display, [[Target]] -> Target
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
    name = re.sub(r"\s*\((?:Crisis Core|item|Materia|M|C|S|I|DMW|Accessory)\)\s*", "", name, flags=re.I)
    name = re.sub(r"\s*\(Materia\)\s*", "", name, flags=re.I)
    name = re.sub(r"\s*w/\s*.*$", "", name, flags=re.I)
    name = re.sub(r"\s*x\s*\d+$", "", name, flags=re.I)
    name = re.sub(r"\s*×\s*\d+$", "", name, flags=re.I)
    name = name.strip(" .,:;-")
    low = name.lower()
    if low in ITEM_ALIAS_MAP:
        return ITEM_ALIAS_MAP[low]
    if low.endswith("s") and low[:-1] in ITEM_ALIAS_MAP:
        return ITEM_ALIAS_MAP[low[:-1]]
    return name


def parse_item_qty_entry(raw: str) -> tuple[str, int, str]:
    """Returns (canonical_name, quantity, raw_label)"""
    cleaned = clean_wiki_text(raw).strip()
    if not cleaned or cleaned.lower() in ("none", "-", "n/a", "—"):
        return ("", 0, "")
    # Extract bonus note like 'Rebirth Flame w/MAG +80'
    qty = 1
    m_qty = re.search(r"(?:\bx\s*|×\s*)(\d+)\b", cleaned, flags=re.I)
    if m_qty:
        qty = int(m_qty.group(1))
    name = canonical_item_name(cleaned)
    return (name, qty, cleaned)


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
        if st.startswith("|+") or st.startswith("!"):
            # Could be header or row title (!{{A|...}})
            if st.startswith("!{{") or st.startswith("![["):
                cell = st.lstrip("!").strip()
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
    # Sensible chapter gates for Crisis Core branches
    branch_num = int(branch[1:])
    if branch_num == 1:
        return 1 if sub_num <= 1 else min(9, 2 + sub_num)
    if branch_num in (2, 3, 4, 5):
        return min(10, 3 + sub_num)
    if branch_num in (6, 7, 8):
        return min(10, 3 + sub_num)
    if branch_num == 9:
        return min(10, 6 + (sub_num + 1) // 2)
    return min(10, 5 + sub_num)


def compute_hard_benchmarks(stars: int, mission_id: str) -> dict[str, Any]:
    presets = {
        1: (5, 1200, 15, 15, "Basic warm-up; Barrier helps against groups."),
        2: (10, 2200, 25, 25, "Keep Barrier up and dodge heavy windups."),
        3: (15, 3600, 40, 40, "Stack HP% via Potions after Chapter 4."),
        4: (22, 5500, 60, 60, "Start pairing Element/Status Ward for safety."),
        5: (30, 8500, 85, 85, "Use Wall/Barrier and Darkness or Jump skills."),
        6: (38, 13000, 110, 110, "Equip Adaman Bangle (M7-3-6) for Break HP Limit."),
        7: (46, 20000, 145, 145, "Aim for Costly Punch + Brutal (M7-4-6) ASAP."),
        8: (56, 35000, 185, 185, "Use Status Ward + Hell-aga to neutralize mobs."),
        9: (68, 60000, 225, 225, "Push VIT/SPR to 220+ and HP 50k+."),
        10: (80, 95000, 255, 255, "Endgame Hard Mode: max VIT/SPR 255 & Genji gear."),
    }
    lvl, hp, vit, spr, notes = presets.get(stars, presets[5])
    if mission_id == "M9-6-6":
        return {
            "recommendedLevel": 85,
            "hp": 99999,
            "vit": 255,
            "spr": 255,
            "notes": "Superboss Minerva (20M HP on Hard Mode): 255 VIT/SPR, 99,999 HP, Wall, Costly Punch, Mug (steal 99 Phoenix Downs), Genji set.",
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

        # Track sub-group headings like ==M2-1: Monsters in Midgar==
        if branch == "M1":
            # Table-based format
            cur_sub = "M1-1: Training Missions"
            lines = text.splitlines()
            # Split by ==M1- sections
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
                    stars = int(re.search(r"\d+", rank_str).group(0)) if re.search(r"\d+", rank_str) else 1
                    stars = max(1, min(10, stars))
                    treasures_raw = row[4]
                    reward_raw = row[5]

                    treasures = []
                    if clean_wiki_text(treasures_raw).lower() not in ("none", "-", ""):
                        for part in re.split(r",|<br\s*/?>", treasures_raw):
                            iname, qty, rlabel = parse_item_qty_entry(part)
                            if iname:
                                treasures.append({"itemId": f"item_{slugify(iname)}", "quantity": qty, "rawLabel": rlabel})

                    rname, rqty, rlabel = parse_item_qty_entry(reward_raw)
                    clear_reward = (
                        {"itemId": f"item_{slugify(rname)}", "quantity": rqty, "rawLabel": rlabel}
                        if rname
                        else None
                    )
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
            # Heading + bullet format (M2..M10)
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

                    # Description is italicized lines before *'''Unlock:'''
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

                    treasures = []
                    if chests_raw and clean_wiki_text(chests_raw).lower() not in ("none", "-", ""):
                        for part in re.split(r",(?![^\[]*\])|<br\s*/?>", chests_raw):
                            iname, qty, rlabel = parse_item_qty_entry(part)
                            if iname:
                                treasures.append({"itemId": f"item_{slugify(iname)}", "quantity": qty, "rawLabel": rlabel})

                    rname, rqty, rlabel = parse_item_qty_entry(reward_raw)
                    clear_reward = (
                        {"itemId": f"item_{slugify(rname)}", "quantity": rqty, "rawLabel": rlabel}
                        if rname
                        else None
                    )

                    # Base stars estimate by branch/subGroup (refined after enemies are linked)
                    sub_num = int(mid.split("-")[1])
                    step_num = int(mid.split("-")[2])
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

    # Deterministic order M1-1-1 .. M10-4-3
    def _sort_key(m: dict[str, Any]) -> tuple[int, int, int]:
        a, b, c = m["id"][1:].split("-")
        return (int(a), int(b), int(c))

    missions.sort(key=_sort_key)
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
    return fields


def parse_int_stat(raw: str) -> int | None:
    if not raw:
        return None
    cleaned = clean_wiki_text(raw).replace(",", "")
    m = re.search(r"-?\d+", cleaned)
    return int(m.group(0)) if m else None


def classify_enemy_family(name: str, wikitext: str, is_boss: bool) -> str:
    low = (name + " " + wikitext[:500]).lower()
    if is_boss or "minerva" in low or "bahamut" in low or "sephiroth" in low or "genesis" in low and "boss" in low:
        return "Boss"
    if name.startswith("G ") or "genesis copy" in low:
        return "Genesis Copy"
    if name.startswith("A-") or "angeal copy" in low:
        return "Angeal Copy"
    if "shinra" in low or "trooper" in low or "captain" in low or "solider" in low or "soldier" in low:
        return "Shinra"
    if "wutai" in low or "crescent unit" in low:
        return "Wutai"
    if any(k in low for k in ("gun", "machine", "turret", "sweeper", "guard", "mech", "mover", "saucer", "motor")):
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
        # Strictly require an enemy stats infobox to avoid non-enemy pages (e.g. Auto-Regen)
        stats_fields = parse_infobox_fields(text, "infobox enemy stats VIICC")
        if not stats_fields:
            stats_fields = parse_infobox_fields(text, "infobox enemy stats")
        if not stats_fields:
            continue

        info_fields = parse_infobox_fields(text, "infobox enemy")
        name = clean_wiki_text(stats_fields.get("name") or info_fields.get("name") or page_title)
        name = re.sub(r"\s*\((?:Crisis Core|boss)\)\s*", "", name, flags=re.I).strip()
        if not name or name.lower().startswith("auto-regen"):
            continue

        eid = f"enemy_{slugify(name)}"
        if any(e["id"] == eid for e in enemies):
            # Disambiguate rare duplicate names using page title
            eid = f"enemy_{slugify(page_title)}"

        image_file = clean_wiki_text(info_fields.get("image") or stats_fields.get("image") or "")
        if image_file:
            image_files.append(image_file)

        # Parse Mission spawn codes M#-#-#
        loc_text = (stats_fields.get("location", "") + "\n" + info_fields.get("location", ""))
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

        # Affinities (list keys + individual elemental fields)
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

        def _loot_item(key: str) -> str | None:
            raw_val = stats_fields.get(key, "")
            iname, _, _ = parse_item_qty_entry(raw_val)
            return f"item_{slugify(iname)}" if iname else None

        loot = {
            "commonDrop": _loot_item("drop"),
            "rareDrop": _loot_item("rare drop"),
            "commonSteal": _loot_item("steal"),
            "rareSteal": _loot_item("rare steal"),
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
                "sp": parse_int_stat(stats_fields.get("sp", "")),
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


def parse_items_and_shops(pages: dict[str, str]) -> dict[str, dict[str, Any]]:
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

    # 1. Items page
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
            fusion_obj = parse_fusion_note(name, fusion_raw)
            ensure_item(name, cat, cur_sec, desc, fusion_obj)

    # 2. Accessories
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

    # 3. Materia pages
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
            # Magic/Command/Special/Support tables have Effect in col 2
            desc = clean_wiki_text(row[2])
            ensure_item(name, "materia", subcat, desc, None)

    # 4. Shops
    shop_txt = pages.get("Shop (Crisis Core)", "")
    shop_sections = re.split(r"(^====[^=].*?====\s*$)", shop_txt, flags=re.M)
    cur_shop = ""
    cur_unlock = ""
    for sec in shop_sections:
        st = sec.strip()
        if st.startswith("===="):
            cur_shop = clean_wiki_text(st.strip("="))
            cur_unlock = ""
            continue
        if cur_shop:
            m_unlock = re.search(r"unlocked[^\n.]+", sec, flags=re.I)
            if m_unlock:
                cur_unlock = clean_wiki_text(m_unlock.group(0))
            for row in parse_wikitable_rows(sec):
                if len(row) < 2:
                    continue
                iname = canonical_item_name(row[0])
                if not iname or iname.lower() == "name":
                    continue
                price_m = re.search(r"[\d,]+", clean_wiki_text(row[1]))
                price = int(price_m.group(0).replace(",", "")) if price_m else 0
                item = ensure_item(iname, "consumables", "", "")
                if not any(s["shopName"] == cur_shop for s in item["shops"]):
                    item["shops"].append({"shopName": cur_shop, "price": price, "unlockHint": cur_unlock})

    # Ensure core curated fusion items & Hard Mode essentials always exist with exact stats
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

    return items


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
) -> None:
    enemy_by_id = {e["id"]: e for e in enemies}
    mission_by_id = {m["id"]: m for m in missions}

    # 1. Link rawEnemies from M2..M10 into missions + enemy spawns
    for m in missions:
        raw_list = m.pop("_rawEnemies", [])
        for ename in raw_list:
            eid = enemy_name_to_id.get(ename.lower())
            if not eid:
                # Fallback fuzzy match
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

    # 2. Ensure every enemy.spawns entry is reflected in mission boss/randomEnemyIds
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

    # 3. Refine M2..M10 star ratings from linked enemy levels
    for m in missions:
        linked_eids = m["bossEnemyIds"] + m["randomEnemyIds"]
        levels = [enemy_by_id[eid]["stats"]["level"] for eid in linked_eids if eid in enemy_by_id and enemy_by_id[eid]["stats"]["level"]]
        if levels and m["branch"] != "M1":
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
            if m["id"] == "M9-6-6":
                stars = 10
            m["stars"] = stars
            m["hardModeBenchmarks"] = compute_hard_benchmarks(stars, m["id"])

    # 4. Ensure every itemId referenced in missions & enemies exists in items.json
    def _ensure_ref_item(item_id: str | None, fallback_label: str = "") -> None:
        if not item_id or item_id in items:
            return
        label = fallback_label or item_id.replace("item_", "").replace("_", " ").title()
        low = label.lower()
        cat = "key-items"
        sub = "Key / Unlock"
        if "shop" in low or "commerce" in low or "dept" in low or "online" in low or "shade" in low or "emporium" in low or "delivery" in low:
            sub = "Shop Unlock"
        elif any(k in low for k in ("bangle", "armlet", "ring", "amulet", "belt", "glove", "helm", "armor", "shield", "suit", "ribbon", "brutal", "ziedrich", "slayer", "soul", "hairpin", "charm", "watch", "knuckles", "cape", "earrings", "talismans", "talisman", "brooch", "badge", "headband", "vest", "band", "scarf")):
            cat = "accessories"
            sub = "Accessory"
        elif any(k in low for k in ("materia", "fira", "firaga", "blizz", "thund", "cur", "drain", "punch", "jump", "dash", "libra", "barrier", "wall", "ultima", "flare", "darkness", "mug", "steal", "quak", "grav", "tri-")):
            cat = "materia"
            sub = "Materia"
        items[item_id] = {
            "id": item_id,
            "name": label,
            "category": cat,
            "subCategory": sub,
            "description": f"Obtained from Crisis Core missions, chests, or enemies ({label}).",
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


def build_guides_json(missions: list[dict[str, Any]], enemies: list[dict[str, Any]], items: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "levelBrackets": [
            {
                "id": "lv_1_15",
                "label": "Lv. 1–15 (Early Story / Ch. 1–3)",
                "minLevel": 1,
                "maxLevel": 15,
                "benchmarks": {
                    "hp": "1,200 – 3,500",
                    "vit": "15 – 40",
                    "spr": "15 – 40",
                    "gear": "Bronze/Iron Bangle, Barrier, Cura, Assault Twister"
                },
                "priorityMissions": ["M1-1-1", "M1-2-1", "M1-2-3", "M3-1-1", "M4-1-1", "M6-1-1", "M8-1-1"],
                "expRoute": "Clear M1-1-x and M3-1-x branches naturally; avoid multi-star spikes until Barrier is equipped.",
                "spGilRoute": "Sell duplicate early bangles; open chests in M6-1-x for early Phoenix Downs and Hi-Potions.",
                "fusionFocus": "Collect Potions & early Stat Mako Stones. Wait for Chapter 4 Item Fusion Tome (M7-2-1) before burning items."
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
                    "gear": "4 Accessory Slots (M7-2-2 & M7-2-5), Item Fusion Tome (M7-2-1), Mog's Amulet (M4-4-3 Shop)"
                },
                "priorityMissions": ["M4-4-3", "M7-2-1", "M7-2-2", "M7-2-5", "M6-2-3", "M8-2-1"],
                "expRoute": "M3-2-x and M5-1-x encounters while pushing M7-2-x for Keychain & Backpack.",
                "spGilRoute": "Buy Mog's Amulet from Sector 7 Shop (unlocked via M4-4-3) so drops/steals guarantee rare rolls.",
                "fusionFocus": "Unlock Item Fusion Tome (M7-2-1) and stack +HP% on an HP Up or Libra using cheap Shinra Shop Potions (50 Gil each)."
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
                    "gear": "Adaman Bangle (M7-3-6), Brutal (M7-4-6), Status Ward + Hell-aga Materia"
                },
                "priorityMissions": ["M7-3-6", "M7-4-6", "M7-5-3", "M8-4-4", "M6-6-3"],
                "expRoute": "M6-5-x and M7-4-x encounters with Darkness or Hell Blizzaga + Status Ward.",
                "spGilRoute": "M7-5-3 unlocks Bone Village Commerce; farm M6-6-3 Lesser Worms for Dark Matter & Gil.",
                "fusionFocus": "Use M8-4-4 Moogle Power + M1-1-1 AFK leveling, then fuse Hell Blizzaga/Firaga + Status Ward to wipe 7–8★ mobs."
            },
            {
                "id": "lv_40_60",
                "label": "Lv. 40–60 (Late Cavern / Stat Maxing)",
                "minLevel": 40,
                "maxLevel": 60,
                "benchmarks": {
                    "hp": "40,000 – 75,000",
                    "vit": "160 – 220",
                    "spr": "160 – 220",
                    "gear": "Costly Punch, Aerial Drain, Wall, Jeweled Ring + Mog's Amulet"
                },
                "priorityMissions": ["M6-6-3", "M8-6-4", "M9-1-1", "M9-5-3", "M9-5-4"],
                "expRoute": "M8-6-4 (Scissor Chitins) gives fast EXP + high Gil drops.",
                "spGilRoute": "M9-5-3 (Three Stars) gives massive SP + Gil; M6-6-3 Lesser Worms drop/steal Dark Matter.",
                "fusionFocus": "Build 98/980% Libra transfer Materia with Dark Matter (M6-6-3), Adamantite, Mythril, and Fat Chocobo Feathers."
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
                    "gear": "Genji Helm, Genji Armor, Genji Shield, Genji Glove, Ziedrich / Divine Slayer"
                },
                "priorityMissions": ["M9-5-3", "M9-5-4", "M9-6-4", "M7-6-6", "M9-6-6"],
                "expRoute": "M8-6-4 / M9-6-x encounters for rapid Lv 99.",
                "spGilRoute": "M9-5-3 Three Stars (SP/Gil) + Mog's Amulet + Steal/Mug Minerva for 99 Phoenix Downs (sell extra if needed).",
                "fusionFocus": "Finalize 4 endgame Materia with +100 VIT, +100 SPR, +999% HP (Costly Punch, Aerial Drain, Curaga, Wall/Mug)."
            }
        ],
        "sections": [
            {
                "id": "guide_materia_leveling",
                "title": "Materia Leveling & DMW Mechanics",
                "badge": "DMW Loop",
                "summary": "Exact hidden EXP counter mechanics, slot 1–6 reels, Moogle Power, and the M1-1-1 AFK mastering setup.",
                "refs": {
                    "missions": ["M1-1-1", "M8-4-4"],
                    "items": ["item_moogle_power", "item_safety_bit", "item_ribbon"]
                },
                "blocks": [
                    {
                        "heading": "How Materia Leveling Actually Works",
                        "body": "Each equipped Materia (slots 1–6) has a hidden EXP counter. Whenever the DMW reels spin and land on two matching numbers in slots 1–6 (e.g., 2-2-x or x-5-5), the Materia in that numbered slot gains level-ups (or +2/+3 levels on triple matches!)."
                    },
                    {
                        "heading": "Moogle Power & M1-1-1 AFK Mastering Loop",
                        "body": "Unlock Moogle Power in M8-4-4. Equip 1–2 mastered Moogle Power Materia (to boost Cait Sith/Moogle DMW limit breaks that level all equipped Materia simultaneously) alongside the Materia you want to master, plus auto-regen/status immunity. Enter M1-1-1 (Shinra's Basic Training), leave Zack guarding or idling while weak troopers chip minimal damage, and let the DMW passively master your entire loadout."
                    }
                ]
            },
            {
                "id": "guide_fusion_pipelines",
                "title": "Materia Fusion & Stat-Farming Pipelines",
                "badge": "98 / 980% Trick",
                "summary": "Chapter 4 Item Fusion Tome (M7-2-1), Potion HP% stacking, Mako/Stat Stones, Dark Matter (M6-6-3), and Libra conversion loops.",
                "refs": {
                    "missions": ["M7-2-1", "M6-6-3", "M10-4-3"],
                    "items": ["item_potion", "item_dark_matter", "item_adamantite", "item_mythril", "item_fat_chocobo_feather", "item_libra"]
                },
                "blocks": [
                    {
                        "heading": "Step 1: Item Fusion Tome & Potion HP% Rule",
                        "body": "Clear M7-2-1 in Chapter 4 to unlock Item Fusion. CRITICAL RULE: Consumables like Potions, Hi-Potions, Ethers, and Elixirs ONLY amplify an EXISTING matching stat bonus on one of the two Materia! Fusing two +0% Materia with 99 Potions produces +0%. Start with an HP Up (+10% HP) or any Materia that already carries HP%, then fuse cheap Shinra Shop Potions (20 Potions = +10% HP) to scale up to +999% HP."
                    },
                    {
                        "heading": "Step 2: Mako Stones, Stat Stones & Max-Tier Catalysts",
                        "body": "Mako Stones require 5 per step (max +40 / +400%); Stat Stones require 3 per step (max +66 / +660%). Max-tier items grant +1 per item up to +100 (or +10% up to +999%): Hero Drink (ATK), Adamantite (VIT), Dark Matter (MAG), Mythril (SPR), Gysahl Greens (LCK), Fat Chocobo Feather (HP%), Lunar Harp (MP%), Zeio Nut (AP%)."
                    },
                    {
                        "heading": "Step 3: The Libra 98 / 980% Conversion Loop",
                        "body": "Do NOT push an intermediate stat-stick Materia to +99 or +999%—once maxed, some recipes lock out item upgrades. Stop your cheap Libra transfer Materia at +98 (or +980% HP), then fuse it with your target skill (e.g., Costly Punch or Curaga) plus 1–2 final catalyst items (e.g., Dark Matter or Mythril) to transfer the full +100 / +999% bonus cleanly."
                    }
                ]
            },
            {
                "id": "guide_exp_sp_gil",
                "title": "EXP / SP / Gil Routes by Level",
                "badge": "Endgame Farms",
                "summary": "Targeted mission loops including M6-6-3 (Dark Matter), M8-6-4 (Scissor Chitins), and M9-5-3 (Three Stars).",
                "refs": {
                    "missions": ["M6-6-3", "M8-6-4", "M9-5-3"],
                    "items": ["item_dark_matter", "item_mogs_amulet", "item_jeweled_ring"]
                },
                "blocks": [
                    {
                        "heading": "M6-6-3: Dark Matter & Early Endgame Gil",
                        "body": "Equip Mog's Amulet (rare drops guaranteed) and Jeweled Ring (doubles drops). Run M6-6-3 and farm Lesser Worms for Dark Matter drops/steals—convert unneeded Dark Matter into MAG +100 Libra bases or sell excess."
                    },
                    {
                        "heading": "M8-6-4: Scissor Chitins (EXP & Gil)",
                        "body": "One of the fastest late-game EXP and Gil loops. Clear the mission or chain random encounters with Costly Punch / Hell Blizzaga + Status Ward."
                    },
                    {
                        "heading": "M9-5-3: Three Stars (Endgame SP & Gil)",
                        "body": "The premier SP & Gil farming mission in Reunion. Combine Mog's Amulet + Costly Punch + Mug/Steal to fund 1,000,000+ SP Materia fusions and Net Shop Shade purchases (Genji Helm)."
                    }
                ]
            },
            {
                "id": "guide_combat_meta",
                "title": "Hard Mode Combat Meta & Break Limit Gear",
                "badge": "Minerva Ready",
                "summary": "Essential Hard Mode defensive layers, Status Ward + Hell-aga crowd control, Costly Punch, Aerial Drain, and Genji equipment.",
                "refs": {
                    "missions": ["M4-4-3", "M7-3-6", "M7-4-6", "M7-6-6", "M9-5-4", "M9-6-4", "M9-6-6"],
                    "items": ["item_costly_punch", "item_aerial_drain", "item_status_ward", "item_hell_blizzaga", "item_mogs_amulet", "item_adaman_bangle", "item_brutal", "item_genji_helm", "item_genji_armor", "item_genji_shield", "item_genji_glove", "item_divine_slayer"]
                },
                "blocks": [
                    {
                        "heading": "Defense First: Barrier, MBarrier, Wall & 255 VIT/SPR",
                        "body": "On Hard Mode, enemy ATK/MAG scaling punishes glass cannons. Maintain Wall (or Barrier + MBarrier) constantly, push VIT and SPR toward 255 for 10★ missions, and equip Adaman Bangle (M7-3-6) early for Break HP Limit until you obtain Genji Armor."
                    },
                    {
                        "heading": "Offense: Costly Punch & Aerial Drain",
                        "body": "Equip Brutal (M7-4-6) or Genji Glove (M9-6-4) for Break Damage Limit (99,999). Costly Punch ignores enemy DEF/VIT and scales off Zack's HP—pairing it with 99,999 HP deals capped 99,999 damage per swing. Aerial Drain gives invulnerability frames + full HP recovery."
                    },
                    {
                        "heading": "Mob Clearing: Status Ward + Hell-aga",
                        "body": "Link Status Ward with Hell Firaga / Hell Blizzaga / Hell Thundaga to grant Zack immunity to Poison, Silence, Stun, Stop, and Death simultaneously while casting AoE Death/status nukes."
                    },
                    {
                        "heading": "Genji Checklist",
                        "body": "Genji Helm: Buy from Net Shop Shade (unlocked in M9-5-4) for 1,000,000 Gil. Genji Armor: Achieve 100% DMW progress. Genji Shield: Magic Pot encounter in M7-6-6 (use Gil Toss, Costly Punch, 99,999 dmg, Octaslash). Genji Glove: Chest in M9-6-4."
                    }
                ]
            }
        ]
    }


def build_fusion_rules_json(items: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "statCategories": ["HP%", "MP%", "AP%", "ATK", "VIT", "MAG", "SPR", "LCK"],
        "rulesNotes": [
            "Consumables (Potion, Hi-Potion, X-Potion, Ether, Soma, Elixir) ONLY amplify an existing matching stat bonus on one of the fused Materia. On two +0 Materia they add +0.",
            "Mako Stones add +1 per 5 stones (max +40) or +10% per 5 stones (max +400%).",
            "Stat Stones add +1 per 3 stones (max +66) or +10% per 3 stones (max +660%).",
            "Max-tier fusion items (Hero Drink, Adamantite, Dark Matter, Mythril, Gysahl Greens, Fat Chocobo Feather, Lunar Harp, Zeio Nut) add +1 (max +100) or +10% (max +999%) per item.",
            "When building a Libra transfer Materia, stop at +98 (or +980% HP) so it remains open to item conversion during final fusion."
        ],
        "keyRecipes": [
            {
                "result": "Costly Punch",
                "resultId": "item_costly_punch",
                "ingredientA": "Goblin Punch / Iron Fist / Magical Punch",
                "ingredientB": "Any DMW Materia (or Libra w/ +980% HP)",
                "note": "Hard Mode MVP: ignores defense, 99,999 damage at high HP."
            },
            {
                "result": "Aerial Drain",
                "resultId": "item_aerial_drain",
                "ingredientA": "High Jump",
                "ingredientB": "Drain / Osmose / Assault Twister",
                "note": "Grants invincibility frames during jump and drains HP."
            },
            {
                "result": "Curaga",
                "resultId": "item_curaga",
                "ingredientA": "Cura",
                "ingredientB": "HP Up / Libra / Barrier",
                "note": "Full-heal staple; fuse with Fat Chocobo Feathers or Potions for +999% HP."
            },
            {
                "result": "Wall",
                "resultId": "item_wall",
                "ingredientA": "Barrier",
                "ingredientB": "MBarrier",
                "note": "Applies both Barrier and MBarrier in a single cast."
            },
            {
                "result": "Hell Blizzaga",
                "resultId": "item_hell_blizzaga",
                "ingredientA": "Blizzaga",
                "ingredientB": "Status Strike / Poison / Silence / Stop",
                "note": "Pair with Status Ward for multi-ailment immunity + AoE Death."
            },
            {
                "result": "Hell Firaga",
                "resultId": "item_hell_firaga",
                "ingredientA": "Firaga",
                "ingredientB": "Status Strike / Poison / Silence / Stop",
                "note": "Pair with Status Ward for multi-ailment immunity + AoE Death."
            },
            {
                "result": "Darkness",
                "resultId": "item_darkness",
                "ingredientA": "Assault Twister / Jump",
                "ingredientB": "Drain / Gravity / Dark Fire",
                "note": "Fast midgame AoE HP-cost wave clear."
            },
            {
                "result": "Dualcast",
                "resultId": "item_dualcast",
                "ingredientA": "Buy: Net Shop Shade (M9-5-4)",
                "ingredientB": "Or fuse High-Rank Magic + Ultima/Energy",
                "note": "Casts equipped Magic Materia twice per turn."
            },
            {
                "result": "SP Master",
                "resultId": "item_sp_master",
                "ingredientA": "Reward: M9-5-4 / M9-6-5",
                "ingredientB": "SP Turbo + SP Barrier",
                "note": "Increases damage & defense while spending SP."
            }
        ]
    }


def make_png_rgba(width: int, height: int, pixel_fn) -> bytes:
    """Pure-Python RGBA PNG generator (stdlib zlib + struct)."""
    raw_rows = bytearray()
    for y in range(height):
        raw_rows.append(0)  # filter type 0
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
    # Dark obsidian background with subtle border & glowing Mako ring + Buster blade motif
    r, g, b, a = 7, 11, 16, 255
    if 0.62 <= dist <= 0.76:
        return (0, 229, 163, 255)
    if 0.55 <= dist < 0.62 or 0.76 < dist <= 0.82:
        return (56, 189, 248, 200)
    # Center Mako diamond
    if abs(dx) + abs(dy) < 0.36:
        t = 1.0 - (abs(dx) + abs(dy)) / 0.36
        return (int(20 + 180 * t), int(210 + 45 * t), int(170 + 70 * t), 255)
    # Crosshair accents
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
    guides = json.loads((data_dir / "guides.json").read_text(encoding="utf-8"))
    fusion_rules = json.loads((data_dir / "fusion-rules.json").read_text(encoding="utf-8"))

    errors: list[str] = []

    if len(missions) != 300:
        errors.append(f"Expected exactly 300 missions, found {len(missions)}")

    mission_ids = {m["id"] for m in missions}
    enemy_ids = {e["id"] for e in enemies}
    item_ids = {it["id"] for it in items}

    # Strict Relational Rule: no enemy drop/steal lists inside items.json
    for it in items:
        bad_keys = FORBIDDEN_ITEM_KEYS.intersection(it.keys())
        if bad_keys:
            errors.append(f"Strict Relational Rule violated on {it['id']}: forbidden keys {sorted(bad_keys)}")

    # Check enemy -> item & enemy -> mission references
    for en in enemies:
        for slot in ("commonDrop", "rareDrop", "commonSteal", "rareSteal"):
            iid = en["loot"].get(slot)
            if iid and iid not in item_ids:
                errors.append(f"Broken item ref {iid} in enemy {en['id']} slot {slot}")
        for sp in en.get("spawns", []):
            if sp["missionId"] not in mission_ids:
                errors.append(f"Broken mission ref {sp['missionId']} in enemy {en['id']}")

    # Check mission -> item & mission -> enemy references
    for m in missions:
        cr = m.get("clearReward")
        if cr and cr.get("itemId") not in item_ids:
            errors.append(f"Broken clearReward {cr.get('itemId')} in mission {m['id']}")
        for tr in m.get("treasures", []):
            if tr.get("itemId") not in item_ids:
                errors.append(f"Broken treasure {tr.get('itemId')} in mission {m['id']}")
        for eid in m.get("bossEnemyIds", []) + m.get("randomEnemyIds", []):
            if eid not in enemy_ids:
                errors.append(f"Broken enemy ref {eid} in mission {m['id']}")

    # Check guides refs
    for b in guides.get("levelBrackets", []):
        for mid in b.get("priorityMissions", []):
            if mid not in mission_ids:
                errors.append(f"Broken guide bracket mission ref {mid}")
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

    if errors:
        for err in errors[:30]:
            print(f"[ERROR] {err}", file=sys.stderr)
        raise SystemExit(f"Validation FAILED with {len(errors)} error(s).")

    print(
        f"[OK] Validated Crisis Core dataset: "
        f"{len(missions)} missions, {len(enemies)} enemies, {len(items)} items, "
        f"{len(guides.get('sections', []))} guide sections, 0 broken IDs, Strict Relational Rule passed."
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

    print("[1/5] Fetching mission pages (M1–M10)...")
    mission_pages = fetch_pages_by_titles([t for _, t, _ in BRANCH_TITLES])
    missions = parse_all_missions(mission_pages)
    valid_mids = {m["id"] for m in missions}
    print(f"      Parsed {len(missions)} missions.")

    print("[2/5] Fetching enemy & boss categories...")
    enemy_titles = fetch_category_members("Category:Enemies_in_Crisis_Core_-Final_Fantasy_VII-")
    boss_titles = fetch_category_members("Category:Bosses_in_Crisis_Core_-Final_Fantasy_VII-")
    boss_page_titles = set(boss_titles)
    all_enemy_titles = sorted(set(enemy_titles) | boss_page_titles)
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
    print(f"      Parsed {len(enemies)} verified enemies.")

    print("[3/5] Fetching items, accessories, materia & shops...")
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
    items_dict = parse_items_and_shops(item_pages)

    print("[4/5] Reconciling Item <-> Enemy <-> Mission links...")
    reconcile_relations(missions, enemies, enemy_name_to_id, items_dict)
    items_list = sorted(items_dict.values(), key=lambda x: (x["category"], x["name"].lower()))

    guides = build_guides_json(missions, enemies, items_dict)
    fusion_rules = build_fusion_rules_json(items_dict)

    (DATA_DIR / "missions.json").write_text(json.dumps(missions, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "enemies.json").write_text(json.dumps(enemies, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "items.json").write_text(json.dumps(items_list, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "guides.json").write_text(json.dumps(guides, indent=2, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "fusion-rules.json").write_text(json.dumps(fusion_rules, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[5/5] Running integrity validation...")
    validate_dataset(DATA_DIR)


if __name__ == "__main__":
    main()
