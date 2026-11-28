"""
Curated Crisis Core: Final Fantasy VII Reunion 100% Compendium datasets:
- Story Chapters 1-10 walkthroughs, pickups, and story boss tactics
- All 51 Reunion Trophies (1 Platinum, 2 Gold, 5 Silver, 43 Bronze)
- All 20 Mail Senders & 5 Fan Clubs with missable dialogue guardrails
- 10 Mini-Games & Side-Quests (Seven Wonders + Safe Code, Flower Wagons, Sector 5, etc.)
- All 6 Magic Pot Encounters
- Core Mechanics, Zack Lv.1-99 Stats, DMW, Reunion Combat, Status Effects, Reunion vs PSP, NG+
- Full Materia Fusion Class & Grade 1-8 Matrix + Accessory statMods & effectTags
"""

from __future__ import annotations

import re
from typing import Any


CURATED_MISSION_ROUTE_NOTES: dict[str, str] = {
    "M4-3-6": "Follow the left/west fork toward the dead-end alcove before engaging the boss target to grab The Happy Turtle shop chest.",
    "M4-4-3": "Sector 7 Shop chest sits on the side path before the final Wutai ambush room—sweep every branch before clearing the target.",
    "M6-2-1": "Talk to the City Planning Director in the Shinra Building Entrance Hall (Ch. 4+) to unlock M6-2-1; clearing it unlocks Sector 8 Materia Shop.",
    "M6-2-3": "Clearing M6-2-3 unlocks Sector 5 Materia Shop (ATK/VIT/MAG/SPR Up, Poison, Silence).",
    "M6-2-6": "Clearing M6-2-6 unlocks Sector 6 Accessory Shop (starter Bangles/Armlets/Vests/Earrings/Amulets).",
    "M6-4-4": "Check the northwest corner chest in the Gongaga-style cavern before triggering the boss fight to obtain Nibel Accessories.",
    "M6-6-3": "Equip Mog's Amulet + Jeweled Ring and run the side tunnels for Lesser Worms (Dark Matter) and Mover EX (8,000 SP + Flare steals).",
    "M7-2-1": "Mandatory early Ch. 4 unlock: clearing M7-2-1 awards the Item Fusion Tome so you can attach items during Materia Fusion.",
    "M7-2-2": "Clearing M7-2-2 awards Keychain, permanently unlocking Zack's 3rd Accessory Slot.",
    "M7-2-5": "Clearing M7-2-5 awards Backpack, permanently unlocking Zack's 4th Accessory Slot.",
    "M7-3-6": "Clear reward is Adaman Bangle (Break HP Limit to 99,999). Keep Barrier/Wall up against heavy physical hits.",
    "M7-4-6": "Clear reward is Brutal (Break Damage Limit to 99,999). Watch for Wyerd's dark casts and interrupt its Skill Power bar.",
    "M7-5-3": "In the labyrinthine Wasteland map, hug the outer perimeter alcoves to find the chest containing Bone Village Outlet before killing the boss.",
    "M7-6-6": "Equip Gil Toss + Costly Punch + Break Damage Limit (Brutal/Genji Glove/Buster Sword 23%+) + Octaslash Materia. Trigger random encounters until Magic Pot spawns, then obey: Gil Toss -> Costly Punch -> 99,999 Damage -> Octaslash for Genji Shield!",
    "M8-4-4": "Clear reward unlocks the Moogle DMW image, enabling Moogle Power AFK Materia leveling.",
    "M8-5-2": "Kill the small adds BEFORE defeating Mover without taking HP damage to trigger Reunion's 2x-3x SP Chain multiplier.",
    "M8-6-4": "Sweep the cavern loops for fast Scissor Chitin spawns (5,460 EXP each) with Costly Punch or Hell Blizzaga.",
    "M9-3-3": "Search the side alcoves for the Online Shop Duo chest before defeating the boss; Grandpanzer here also carries Adamantite.",
    "M9-5-3": "Best endgame SP/Gil loop: equip Mog's Amulet + Precious Watch + Jeweled Ring + Mug and farm Three Stars (20,000 SP) and Tycoons.",
    "M9-5-4": "Hug the left/upper cavern path to loot the chest containing Online Shop Shade (sells Dualcast, Jeweled Ring, Precious Watch, and Genji Helm for 1M Gil).",
    "M9-6-4": "Check the far-west/north dead-end chests in the Great Cavern to loot Genji Glove (Break Damage Limit + Always Critical) before facing Great Malboro.",
    "M9-6-5": "Goliath here drops/steals Adamantite (+1 VIT) and gives 23,264 EXP; mock troopers with Barriers help finish the final 5% Buster Sword Barrier Pierce pool.",
    "M9-6-6": "Superboss Arena: single direct fight against Minerva (20,000,000 HP). Pop Phoenix Down + Wall, Mug once for 99x Phoenix Downs, and loop Costly Punch.",
    "M10-2-3": "Equip Jump, Fira, Gravity, and Assault Twister before entering. Trigger random battles until Magic Pot appears, obey its 4 requests for the Magic Pot DMW, then clear Master Tonberry for Tonberry's Knife.",
}


STORY_ENEMY_CHAPTERS: dict[str, int] = {
    "enemy_unknown": 8,
    "enemy_baby_grangalan": 10,
    "enemy_behemoth": 1,
    "enemy_behemoth_king": 10,
    "enemy_blue_materia": 10,
    "enemy_crescent_unit_lux": 10,
    "enemy_death_machine": 10,
    "enemy_experiment_no_88": 8,
    "enemy_experiment_no_97": 8,
    "enemy_g_antenora": 10,
    "enemy_g_caina": 10,
    "enemy_g_judecca": 10,
    "enemy_g_lucifero": 10,
    "enemy_g_ptolomea": 10,
    "enemy_g_regicide": 10,
    "enemy_g_shadow_knight": 10,
    "enemy_g_shadow_mage": 10,
    "enemy_g_shadow_scythe": 10,
    "enemy_genesis_avatar": 10,
    "enemy_grangalan": 10,
    "enemy_grangalan_jr": 10,
    "enemy_green_materia": 10,
    "enemy_grenade": 10,
    "enemy_grosspanzer": 4,
    "enemy_materia": 10,
    "enemy_panzer_jr": 4,
    "enemy_red_materia": 10,
    "enemy_shinra_troop": 1,
    "enemy_yellow_materia": 10,
    "enemy_ifrit": 1,
    "enemy_g_eraser": 3,
    "enemy_guard_scorpion": 4,
    "enemy_g_eliminator": 5,
    "enemy_angeal_penance": 5,
    "enemy_sephiroth": 8,
    "enemy_genesis": 10,
    "enemy_genesis_final_boss": 10,
    "enemy_vajradhara_tai": 1,
    "enemy_vajradhara_wu": 1,
}


ACCESSORY_OVERRIDES: dict[str, dict[str, Any]] = {
    "item_genji_helm": {
        "tags": ["Zero MP/AP", "Auto-Buff"],
        "mods": {"zeroMp": True, "zeroAp": True, "autoBuffs": ["Libra"]},
    },
    "item_genji_armor": {
        "tags": ["Break HP Limit", "Auto-Buff"],
        "mods": {"breakHp": True, "autoBuffs": ["Endure", "Regen"]},
    },
    "item_genji_shield": {
        "tags": ["Elemental Absorb", "Status Immunity", "Auto-Buff"],
        "mods": {
            "absorbElems": ["Fire", "Ice", "Lightning"],
            "immuneStatuses": ["All"],
            "autoBuffs": ["Barrier", "MBarrier"],
        },
    },
    "item_genji_glove": {
        "tags": ["Break Damage Limit", "Auto-Buff"],
        "mods": {"breakDmg": True, "autoBuffs": ["Critical"]},
    },
    "item_divine_slayer": {
        "tags": ["Break HP Limit", "Break MP Limit", "Break AP Limit", "Break Damage Limit", "Elemental Absorb", "Stat Boost"],
        "mods": {
            "hpPct": 100, "mpPct": 100, "apPct": 100,
            "atk": 50, "vit": 50, "mag": 50, "spr": 50, "lck": 50,
            "breakHp": True, "breakMp": True, "breakAp": True, "breakDmg": True,
            "absorbElems": ["Fire", "Ice", "Lightning"],
        },
    },
    "item_heike_soul": {
        "tags": ["Break HP Limit", "Break MP Limit", "Break AP Limit", "Break Damage Limit", "Elemental Absorb", "Drop/Steal Boost", "Auto-Buff"],
        "mods": {
            "breakHp": True, "breakMp": True, "breakAp": True, "breakDmg": True,
            "absorbElems": ["Fire", "Ice", "Lightning"],
            "autoBuffs": ["Dualcast", "Libra", "Auto-Potion", "Smart Consumer", "SP Master", "Curse"],
        },
    },
    "item_ziedrich": {
        "tags": ["Elemental Halve", "Stat Boost"],
        "mods": {"atk": 100, "vit": 100, "mag": 100, "spr": 100, "halveElems": ["Fire", "Ice", "Lightning"]},
    },
    "item_adaman_bangle": {"tags": ["Break HP Limit"], "mods": {"breakHp": True}},
    "item_brutal": {"tags": ["Break Damage Limit"], "mods": {"breakDmg": True}},
    "item_black_cowl": {"tags": ["Break AP Limit"], "mods": {"breakAp": True}},
    "item_gold_hairpin": {"tags": ["Break MP Limit"], "mods": {"breakMp": True}},
    "item_mogs_amulet": {"tags": ["Drop/Steal Boost", "Stat Boost"], "mods": {"lck": 5}},
    "item_brigands_gloves": {"tags": ["Drop/Steal Boost"], "mods": {}},
    "item_jeweled_ring": {"tags": ["Drop/Steal Boost", "Stat Boost"], "mods": {"lck": 20}},
    "item_precious_watch": {"tags": ["Drop/Steal Boost", "Stat Boost"], "mods": {"lck": 10}},
    "item_sniper_eye": {"tags": ["Auto-Buff"], "mods": {"autoBuffs": ["Critical"]}},
    "item_soul_of_thamasa": {"tags": ["Zero MP/AP"], "mods": {"zeroMp": True}},
    "item_laurel_crown": {"tags": ["Zero MP/AP"], "mods": {"zeroAp": True}},
    "item_magic_master": {
        "tags": ["Zero MP/AP", "Stat Boost"],
        "mods": {"zeroMp": True, "mpPct": 50, "mag": 100, "spr": 100, "hpPct": -50, "apPct": -50, "atk": -100, "vit": -100},
    },
    "item_power_suit": {
        "tags": ["Stat Boost"],
        "mods": {"hpPct": 100, "atk": 100, "vit": 100, "mpPct": -50, "apPct": -50, "mag": -50, "spr": -50},
    },
    "item_energy_suit": {
        "tags": ["Stat Boost"],
        "mods": {"hpPct": 20, "apPct": 100, "atk": 100, "vit": 50, "mpPct": -50, "mag": -100, "spr": -50},
    },
    "item_assault_targe": {"tags": ["Stat Boost"], "mods": {"atk": 50, "vit": 50, "mag": -80, "spr": -80}},
    "item_impervious": {"tags": ["Stat Boost"], "mods": {"hpPct": 10, "mpPct": 10, "apPct": 10, "mag": 120, "spr": 120, "atk": -50, "vit": -50}},
    "item_ribbon": {"tags": ["Status Immunity"], "mods": {"immuneStatuses": ["Poison", "Silence", "Stun", "Stop", "Curse"]}},
    "item_super_ribbon": {"tags": ["Status Immunity"], "mods": {"immuneStatuses": ["All"]}},
    "item_safety_bit": {"tags": ["Status Immunity", "Stat Boost"], "mods": {"spr": 30, "immuneStatuses": ["Death"]}},
    "item_cursed_ring": {
        "tags": ["Stat Boost"],
        "mods": {"hpPct": 50, "mpPct": 50, "apPct": 50, "atk": 30, "vit": 30, "mag": 30, "spr": 30, "lck": 30, "autoBuffs": ["Curse"]},
    },
    "item_protect_ring": {"tags": ["Auto-Buff", "Stat Boost"], "mods": {"spr": 20, "autoBuffs": ["Barrier", "MBarrier"]}},
    "item_faerie_ring": {"tags": ["Auto-Buff", "Stat Boost"], "mods": {"spr": 20, "autoBuffs": ["Regen"]}},
    "item_moon_bracer": {"tags": ["Auto-Buff", "Stat Boost"], "mods": {"spr": 10, "autoBuffs": ["Barrier"]}},
    "item_shining_bracer": {"tags": ["Auto-Buff", "Stat Boost"], "mods": {"spr": 10, "autoBuffs": ["MBarrier"]}},
    "item_twisted_headband": {"tags": ["Auto-Buff", "Stat Boost"], "mods": {"hpPct": 10, "autoBuffs": ["Endure"]}},
    "item_wizard_bracelet": {"tags": ["Elemental Absorb", "Stat Boost"], "mods": {"mpPct": 60, "absorbElems": ["Fire", "Ice", "Lightning"]}},
    "item_dragon_armlet": {"tags": ["Elemental Halve", "Stat Boost"], "mods": {"mpPct": 30, "halveElems": ["Fire", "Ice", "Lightning"]}},
    "item_blaze_armlet": {"tags": ["Elemental Absorb", "Stat Boost"], "mods": {"mpPct": 30, "absorbElems": ["Fire"]}},
    "item_snow_armlet": {"tags": ["Elemental Absorb", "Stat Boost"], "mods": {"mpPct": 30, "absorbElems": ["Ice"]}},
    "item_bolt_armlet": {"tags": ["Elemental Absorb", "Stat Boost"], "mods": {"mpPct": 30, "absorbElems": ["Lightning"]}},
    "item_flame_armlet": {"tags": ["Elemental Immunity", "Stat Boost"], "mods": {"mpPct": 20, "immuneElems": ["Fire"]}},
    "item_frost_armlet": {"tags": ["Elemental Immunity", "Stat Boost"], "mods": {"mpPct": 20, "immuneElems": ["Ice"]}},
    "item_thunder_armlet": {"tags": ["Elemental Immunity", "Stat Boost"], "mods": {"mpPct": 20, "immuneElems": ["Lightning"]}},
    "item_force_of_nature": {"tags": ["Elemental Immunity", "Stat Boost"], "mods": {"mpPct": 40, "immuneElems": ["Fire", "Ice", "Lightning"]}},
    "item_escort_guard": {"tags": ["Elemental Immunity", "Status Immunity", "Stat Boost"], "mods": {"vit": 30, "spr": 30, "immuneElems": ["Fire", "Ice", "Lightning"]}},
}


def _parse_acc_stat_mods(desc: str) -> dict[str, Any]:
    mods: dict[str, Any] = {}
    d = desc or ""
    # Handle patterns like "HP +10%", "ATK, VIT +100", "ATK & MAG +5", "MAG, SPR -80"
    for m in re.finditer(r"((?:(?:HP|MP|AP|ATK|VIT|MAG|SPR|LCK|STR)\s*(?:[,&/]\s*|\band\s+)?)+)\s*([+-]\d+)(%?)", d, flags=re.I):
        keys_raw = m.group(1)
        val = int(m.group(2))
        is_pct = bool(m.group(3))
        for k in re.findall(r"HP|MP|AP|ATK|VIT|MAG|SPR|LCK|STR", keys_raw, flags=re.I):
            ku = k.upper()
            if ku == "STR":
                ku = "ATK"
            if ku in ("HP", "MP", "AP") or is_pct:
                fld = {"HP": "hpPct", "MP": "mpPct", "AP": "apPct"}.get(ku, ku.lower())
            else:
                fld = ku.lower()
            mods[fld] = mods.get(fld, 0) + val

    low = d.lower()
    if "hp limit becomes 99,999" in low or "breaks hp" in low:
        mods["breakHp"] = True
    if "mp limit becomes 9,999" in low or "breaks mp" in low:
        mods["breakMp"] = True
    if "ap limit becomes 9,999" in low or "breaks ap" in low:
        mods["breakAp"] = True
    if "damage limit becomes 99,999" in low or "damage limits" in low:
        mods["breakDmg"] = True
    if "no mp cost" in low or "zero mp" in low:
        mods["zeroMp"] = True
    if "no ap cost" in low or "zero ap" in low:
        mods["zeroAp"] = True

    for st in ("Poison", "Silence", "Stun", "Stop", "Curse"):
        if f"prevents {st.lower()}" in low or "prevents all status" in low:
            mods.setdefault("immuneStatuses", [])
            if st not in mods["immuneStatuses"]:
                mods["immuneStatuses"].append(st)
    if "instant death" in low and "prevents" in low:
        mods.setdefault("immuneStatuses", []).append("Death")

    for el in ("Fire", "Ice", "Lightning"):
        if f"absorbs {el.lower()}" in low or "absorbs fire, ice and lightning" in low or "absorbs all element" in low:
            mods.setdefault("absorbElems", [])
            if el not in mods["absorbElems"]:
                mods["absorbElems"].append(el)
        elif f"nullifies {el.lower()}" in low or "nullifies fire, ice" in low:
            mods.setdefault("immuneElems", [])
            if el not in mods["immuneElems"]:
                mods["immuneElems"].append(el)
        elif f"halves {el.lower()}" in low or "halves all elemental" in low:
            mods.setdefault("halveElems", [])
            if el not in mods["halveElems"]:
                mods["halveElems"].append(el)
    return mods


def _infer_acc_tags(mods: dict[str, Any], desc: str) -> list[str]:
    tags: list[str] = []
    low = (desc or "").lower()
    if mods.get("breakHp"):
        tags.append("Break HP Limit")
    if mods.get("breakDmg"):
        tags.append("Break Damage Limit")
    if mods.get("breakMp"):
        tags.append("Break MP Limit")
    if mods.get("breakAp"):
        tags.append("Break AP Limit")
    if mods.get("absorbElems"):
        tags.append("Elemental Absorb")
    if mods.get("immuneElems"):
        tags.append("Elemental Immunity")
    if mods.get("halveElems"):
        tags.append("Elemental Halve")
    if mods.get("immuneStatuses"):
        tags.append("Status Immunity")
    if mods.get("zeroMp") or mods.get("zeroAp"):
        tags.append("Zero MP/AP")
    if mods.get("autoBuffs") or any(k in low for k in ("persistent", "all attacks are critical", "auto-potion", "regen", "endure", "libra")):
        tags.append("Auto-Buff")
    if any(k in low for k in ("drop", "steal", "gil looted", "always rare")):
        tags.append("Drop/Steal Boost")
    if any(k in mods for k in ("hpPct", "mpPct", "apPct", "atk", "vit", "mag", "spr", "lck")):
        tags.append("Stat Boost")
    return tags or ["Utility"]


def _infer_materia_damage_type(sub: str, name: str, desc: str) -> str:
    low_n = name.lower()
    low_d = (desc or "").lower()
    if sub == "DMW" or any(k in low_d for k in ("dmw", "on the dmw")):
        return "DMW"
    if sub == "Support":
        return "Support"
    if sub == "Independent":
        return "Passive"
    if any(k in low_n for k in ("cure", "cura", "curaga", "full cure", "regen", "esuna")):
        return "Healing"
    if any(k in low_n for k in ("barrier", "mbarrier", "wall", "dispel")):
        return "Buff / Utility"
    if "ignores defense" in low_d or "costly punch" in low_n or "darkness" in low_n or "goblin punch" in low_n or "gil toss" in low_n:
        return "Piercing"
    if "gravity" in low_n or "graviga" in low_n:
        return "Gravity (%)"
    if sub == "Command":
        return "Physical"
    return "Magical"


def enrich_items_metadata(items: dict[str, dict[str, Any]], materia_table_meta: dict[str, dict[str, Any]]) -> None:
    """Adds structured Materia (cost, grade, damageType, spConvert) and Accessory (effectTags, statMods) metadata."""
    grade_sp_base = {1: 400, 2: 900, 3: 1800, 4: 3200, 5: 5500, 6: 8500, 7: 12000, 8: 16500}
    for iid, it in items.items():
        cat = it.get("category")
        if cat == "materia":
            tmeta = materia_table_meta.get(iid, {})
            sub = it.get("subCategory") or "Independent"
            name = it.get("name", "")
            desc = it.get("description", "")
            grade = tmeta.get("grade")
            if not grade:
                low_n = name.lower()
                if "++" in low_n or low_n in ("ultima", "costly punch", "aerial drain", "wall", "dualcast", "sp master", "status strike", "elemental strike", "full cure", "assault twister+"):
                    grade = 7 if low_n != "ultima" and low_n != "costly punch" and low_n != "aerial drain" and low_n != "sp master" else 8
                elif "aga" in low_n or "hell " in low_n or low_n in ("electrocute", "flare", "energy", "quake", "darkness", "high jump", "mug", "gil toss", "sp barrier", "status ward", "elemental ward"):
                    grade = 5
                elif "ara" in low_n or "+" in low_n or low_n in ("mbarrier", "regen", "osmose", "vital slash", "magical punch"):
                    grade = 3
                else:
                    grade = 2 if sub == "DMW" else 1
            cost = tmeta.get("cost")
            cost_type = tmeta.get("costType")
            if not cost_type:
                if sub == "Magic":
                    cost_type = "MP"
                elif sub == "Command":
                    cost_type = "AP"
                else:
                    cost_type = "None"
            dmg_type = _infer_materia_damage_type(sub, name, desc)
            base_sp = grade_sp_base.get(grade, 1000)
            it["materia"] = {
                "cost": cost,
                "costType": cost_type,
                "grade": grade,
                "damageType": dmg_type,
                "spConvert": {"lv1": base_sp, "mastered": base_sp * 4},
                "sellPrice": grade * 1250,
            }
        elif cat == "accessories":
            ov = ACCESSORY_OVERRIDES.get(iid)
            if ov:
                mods = dict(ov["mods"])
                tags = list(ov["tags"])
            else:
                mods = _parse_acc_stat_mods(it.get("description", ""))
                tags = _infer_acc_tags(mods, it.get("description", ""))
            it["accessory"] = {
                "effectTags": tags,
                "statMods": mods,
            }


def build_full_fusion_rules(fusion_txt: str, items: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    Builds the complete Crisis Core Materia Fusion database:
    - Grade 1-8 progression per Fusion Class (from cached Materia Fusion wikitext + curated classes)
    - Materia Catalog mapping every Materia itemId -> (fusionClass, grade, fusable)
    - Complete Class A x Class B -> Result Class matrix
    - Special override recipes (Costly Punch, Aerial Drain, Wall, Quake, Dualcast, Ultima, etc.)
    """
    # Canonical Crisis Core Fusion Class -> Grades 1..8 (exact game tables)
    class_grades: dict[str, list[str]] = {
        "Fire": ["Fire", "Fire", "Fira", "Fira", "Firaga", "Firaga", "Firaga", "Firaga"],
        "Ice": ["Blizzard", "Blizzard", "Blizzara", "Blizzara", "Blizzaga", "Blizzaga", "Blizzaga", "Blizzaga"],
        "Lightning": ["Thunder", "Thunder", "Thundara", "Thundara", "Thundaga", "Thundaga", "Thundaga", "Thundaga"],
        "Restore": ["Cure", "Cura", "Regen", "Curaga", "Curaga", "Curaga", "Curaga", "Full Cure"],
        "Defense": ["Barrier", "Barrier", "MBarrier", "Elemental Ward", "Elemental Ward", "Elemental Ward", "Wall", "Wall"],
        "Status Defense": ["Esuna", "Dispel", "Esuna", "Status Ward", "Dispel", "Status Ward", "Status Ward", "Status Ward"],
        "Absorb Mag": ["Drain", "Drain", "Osmose", "Drain", "Drainra", "Osmoga", "Drainga", "Drainga"],
        "Status Mag": ["Poison", "Silence", "Silence", "Stop", "Death", "Death", "Death", "Death"],
        "Fire & St": ["Dark Fire", "Dark Fire", "Dark Fira", "Dark Fira", "Dark Firaga", "Dark Firaga", "Hell Firaga", "Dark Firaga"],
        "Ice & St": ["Dark Blizzard", "Dark Blizzard", "Dark Blizzara", "Dark Blizzara", "Dark Blizzaga", "Dark Blizzaga", "Hell Blizzaga", "Dark Blizzaga"],
        "Lightning & St": ["Dark Thunder", "Dark Thunder", "Dark Thundara", "Dark Thundara", "Dark Thundaga", "Dark Thundaga", "Hell Thundaga", "Dark Thundaga"],
        "Gravity": ["Gravity", "Gravity", "Graviga", "Graviga", "Darkness", "Darkness", "Quake", "Quake"],
        "Ultimate": ["Tri-Thundaga", "Tri-Thundaga", "Tri-Thundaga", "Tri-Fire", "Electrocute", "Flare", "Energy", "Ultima"],
        "Quick Atk": ["Jump", "Jump", "Assault Twister", "Assault Twister", "High Jump", "High Jump", "Assault Twister+", "Assault Twister+"],
        "Quick Atk & St": ["Poison Twister", "Poison Twister", "Poison Aerial", "Stop Twister", "Silence Aerial", "Death Jump", "Death Twister", "Status Strike"],
        "Sword Arts": ["Power Attack", "Power Attack", "Vital Slash", "Vital Slash", "Blast Wave", "Exploder Blade", "Exploder Blade", "Exploder Blade"],
        "Blade Arts & St": ["Poison Blade", "Silence Blade", "Silence Blade", "Stop Blade", "Death Blade", "Death Blade", "Dispel Blade", "Dispel Blade"],
        "Fire Blade": ["Fire Blade", "Fire Blade", "Fira Blade", "Fire Blade", "Firaga Blade", "Firaga Blade", "Elemental Strike", "Elemental Strike"],
        "Ice Blade": ["Blizzard Blade", "Blizzard Blade", "Blizzara Blade", "Blizzara Blade", "Blizzaga Blade", "Blizzaga Blade", "Elemental Strike", "Elemental Strike"],
        "Lightning Blade": ["Thunder Blade", "Thunder Blade", "Thundara Blade", "Thundara Blade", "Thundaga Blade", "Thundaga Blade", "Elemental Strike", "Elemental Strike"],
        "Absorb Sword": ["Osmose Blade", "Osmose Blade", "Drain Blade", "Power Drain", "Power Osmose", "Power Drain", "Aerial Drain", "Aerial Drain"],
        "Item": ["Steal", "Steal", "Smart Consumer", "Smart Consumer", "Mug", "Mug", "Gil Toss", "Gil Toss"],
        "Punch": ["Goblin Punch", "Iron Fist", "Iron Fist", "Magical Punch", "Magical Punch", "Hammer Punch", "Hammer Punch", "Costly Punch"],
        "SP Turbo": ["SP Turbo Magic", "SP Turbo Magic", "SP Turbo Magic", "SP Turbo Magic", "SP Turbo Attack", "SP Turbo", "SP Barrier", "SP Master"],
        "HP Up": ["HP Up", "HP Up", "HP Up+", "HP Up+", "HP Up++", "HP Up++", "HP Up++", "HP Up++"],
        "MP Up": ["MP Up", "MP Up", "MP Up+", "MP Up+", "MP Up++", "MP Up++", "MP Up++", "MP Up++"],
        "AP Up": ["AP Up", "AP Up", "AP Up+", "AP Up+", "AP Up++", "AP Up++", "AP Up++", "AP Up++"],
        "ATK Up": ["ATK UP", "ATK UP", "ATK Up+", "ATK Up+", "ATK Up++", "ATK Up++", "ATK Up++", "ATK Up++"],
        "VIT Up": ["VIT UP", "VIT UP", "VIT Up+", "VIT Up+", "VIT Up++", "VIT Up++", "VIT Up++", "VIT Up++"],
        "MAG Up": ["MAG UP", "MAG UP", "MAG Up+", "MAG Up+", "MAG Up++", "MAG Up++", "MAG Up++", "MAG Up++"],
        "SPR Up": ["SPR UP", "SPR UP", "SPR Up+", "SPR Up+", "SPR Up++", "SPR Up++", "SPR Up++", "SPR Up++"],
        "LCK Up": ["Dash", "Dash", "Dash", "Libra", "Libra", "Dualcast", "Dualcast", "Dualcast"],
        "Libra": ["Libra", "Libra", "Libra", "Libra", "Libra", "Libra", "Libra", "Libra"],
        "DMW": ["Octaslash", "Rush Assault", "Air Strike", "Meteor Shots", "Healing Wave", "Lucky Stars", "Apocalypse", "Ultima"],
    }

    name_to_item = {it["name"].lower(): it["id"] for it in items.values() if it["category"] == "materia"}
    class_definitions: dict[str, list[dict[str, Any]]] = {}
    materia_catalog: dict[str, dict[str, Any]] = {}

    for cls_name, names in class_grades.items():
        entries = []
        for idx, mname in enumerate(names, start=1):
            iid = name_to_item.get(mname.lower())
            entries.append({"grade": idx, "name": mname, "itemId": iid})
            if iid and iid not in materia_catalog:
                # Base grade is first grade where this materia appears
                materia_catalog[iid] = {
                    "itemId": iid,
                    "name": items[iid]["name"],
                    "fusionClass": cls_name,
                    "grade": idx,
                    "dmwOnly": cls_name == "DMW",
                }
        class_definitions[cls_name] = entries

    # Ensure every single one of the 143 Materia has a catalog entry
    dmw_names = {
        "octaslash", "rush assault", "air strike", "meteor shots", "healing wave", "lucky stars",
        "apocalypse", "hellfire", "megaflare", "zantetsuken", "rebirth flame", "exaflare",
        "chocobo stomp", "1000 needles", "murderous thrust", "courage boost!", "moogle power", "item mugger"
    }
    for iid, it in items.items():
        if it["category"] != "materia":
            continue
        if iid not in materia_catalog:
            low_n = it["name"].lower()
            is_dmw = low_n in dmw_names or it.get("subCategory") == "DMW"
            cls = "DMW" if is_dmw else ("Quick Atk" if it.get("subCategory") == "Command" else "Libra")
            gr = (it.get("materia") or {}).get("grade", 2 if is_dmw else 1)
            materia_catalog[iid] = {
                "itemId": iid,
                "name": it["name"],
                "fusionClass": cls,
                "grade": gr,
                "dmwOnly": is_dmw,
            }

    # Class interaction rules (symmetric lookup rules + priority order)
    # Encoded cleanly as rule pairs so A+B and B+A behave identically
    class_pair_rules: dict[tuple[str, str], str] = {}

    def _add_pair(a: str, b: str, res: str) -> None:
        class_pair_rules[(a, b)] = res
        class_pair_rules[(b, a)] = res

    # Elemental magic triangles & Dark magic
    _add_pair("Fire", "Ice", "Lightning")
    _add_pair("Ice", "Lightning", "Fire")
    _add_pair("Fire", "Lightning", "Ice")
    for el, dark_el in [("Fire", "Fire & St"), ("Ice", "Ice & St"), ("Lightning", "Lightning & St")]:
        _add_pair(el, "Status Mag", dark_el)
        _add_pair(el, "Status Defense", dark_el)
        _add_pair(el, "Absorb Mag", dark_el)
        _add_pair(el, "Gravity", "Ultimate")
        _add_pair(el, "Sword Arts", f"{el} Blade")
        _add_pair(el, "Quick Atk", f"{el} Blade")
        _add_pair(el, "Punch", "Punch")
        _add_pair(el, "Restore", el)
        _add_pair(el, "Defense", "Defense")
        _add_pair(el, "Ultimate", "Ultimate")
        _add_pair(el, "DMW", "Ultimate")

    # Command + Magic / Status / Absorb
    _add_pair("Sword Arts", "Status Mag", "Blade Arts & St")
    _add_pair("Quick Atk", "Status Mag", "Quick Atk & St")
    _add_pair("Sword Arts", "Absorb Mag", "Absorb Sword")
    _add_pair("Quick Atk", "Absorb Mag", "Absorb Sword")
    _add_pair("Quick Atk", "Gravity", "Gravity")
    _add_pair("Sword Arts", "Gravity", "Gravity")
    _add_pair("Quick Atk", "Sword Arts", "Quick Atk")
    _add_pair("Quick Atk", "Item", "Item")
    _add_pair("Sword Arts", "Item", "Item")
    _add_pair("Absorb Mag", "Gravity", "Gravity")
    _add_pair("Status Mag", "Gravity", "Gravity")
    _add_pair("Gravity", "DMW", "Ultimate")
    _add_pair("Punch", "DMW", "Punch")
    _add_pair("Punch", "Gravity", "Punch")
    _add_pair("Punch", "Sword Arts", "Punch")
    _add_pair("Punch", "Quick Atk", "Punch")
    _add_pair("Punch", "Absorb Mag", "Punch")
    _add_pair("Punch", "Status Mag", "Punch")
    _add_pair("Restore", "Defense", "Restore")
    _add_pair("Restore", "Status Defense", "Status Defense")
    _add_pair("Defense", "Status Defense", "Status Defense")
    _add_pair("SP Turbo", "DMW", "SP Turbo")
    _add_pair("SP Turbo", "Ultimate", "SP Turbo")
    _add_pair("SP Turbo", "Defense", "SP Turbo")
    _add_pair("Item", "DMW", "Item")
    _add_pair("Fire & St", "Status Defense", "Fire & St")
    _add_pair("Ice & St", "Status Defense", "Ice & St")
    _add_pair("Lightning & St", "Status Defense", "Lightning & St")

    # Stat Up & Libra transfer behavior: Libra acts as pure neutral carrier unless paired with DMW
    stat_classes = ["HP Up", "MP Up", "AP Up", "ATK Up", "VIT Up", "MAG Up", "SPR Up", "LCK Up"]
    all_classes = list(class_grades.keys())
    for c in all_classes:
        _add_pair(c, c, c)
        if c not in ("DMW", "Libra"):
            _add_pair(c, "Libra", c)
    _add_pair("Libra", "DMW", "Libra")
    for sc in stat_classes:
        for c in all_classes:
            if c not in stat_classes and c not in ("DMW", "Libra") and (sc, c) not in class_pair_rules and (c, sc) not in class_pair_rules:
                _add_pair(sc, c, c)

    serializable_matrix: dict[str, dict[str, str]] = {}
    for (ca, cb), res in class_pair_rules.items():
        serializable_matrix.setdefault(ca, {})[cb] = res

    special_overrides = [
        {
            "id": "ov_costly_punch",
            "matchClasses": ["Punch", "DMW"],
            "resultId": "item_costly_punch",
            "note": "Any Punch Materia (Goblin Punch / Iron Fist / Magical Punch / Hammer Punch) + ANY DMW Materia = Costly Punch!",
        },
        {
            "id": "ov_aerial_drain",
            "matchNames": ["High Jump", "Drain"],
            "resultId": "item_aerial_drain",
            "note": "High Jump + Drain / Osmose / Assault Twister = Aerial Drain (i-frames + full heal).",
        },
        {
            "id": "ov_wall",
            "matchNames": ["Barrier", "MBarrier"],
            "resultId": "item_wall",
            "note": "Barrier + MBarrier = Wall (applies both buffs in one cast).",
        },
        {
            "id": "ov_quake",
            "matchNames": ["Graviga", "Darkness"],
            "resultId": "item_quake",
            "note": "Graviga + Darkness / Assault Twister+ = Quake (wide screen AoE).",
        },
        {
            "id": "ov_hell_firaga",
            "matchNames": ["Firaga", "Status Strike"],
            "resultId": "item_hell_firaga",
            "note": "Firaga + Status Strike (or Poison/Silence/Stop) = Hell Firaga.",
        },
        {
            "id": "ov_hell_blizzaga",
            "matchNames": ["Blizzaga", "Status Strike"],
            "resultId": "item_hell_blizzaga",
            "note": "Blizzaga + Status Strike (or Poison/Silence/Stop) = Hell Blizzaga.",
        },
        {
            "id": "ov_hell_thundaga",
            "matchNames": ["Thundaga", "Status Strike"],
            "resultId": "item_hell_thundaga",
            "note": "Thundaga + Status Strike (or Poison/Silence/Stop) = Hell Thundaga.",
        },
        {
            "id": "ov_ultima",
            "matchNames": ["Flare", "Octaslash"],
            "resultId": "item_ultima",
            "note": "High-grade Ultimate Magic (Flare / Energy / Tri-Thundaga) + DMW Materia = Ultima.",
        },
        {
            "id": "ov_dualcast",
            "matchNames": ["Ultima", "Libra"],
            "resultId": "item_dualcast",
            "note": "Dualcast can be bought directly from Online Shop Shade (M9-5-4, 30,000 Gil) or fused from high-grade Magic + LCK/Dash chains.",
        },
        {
            "id": "ov_mug",
            "matchNames": ["Steal", "Assault Twister"],
            "resultId": "item_mug",
            "note": "Steal + Mastered Assault Twister / Vital Slash = Mug.",
        },
    ]

    return {
        "statCategories": ["HP%", "MP%", "AP%", "ATK", "VIT", "MAG", "SPR", "LCK"],
        "rulesNotes": [
            "Resulting Materia depends on both Fusion Classes AND the highest Grade (1–8) between the two Materia (Mastered Materia each add +1 Grade, up to +2!).",
            "Consumables (Potion, Hi-Potion, X-Potion, Ether, Soma, Elixir) ONLY amplify an existing matching stat bonus on one of the fused Materia. On two +0 Materia they add +0.",
            "Mako Stones add +1 per 5 stones (max +40) or +10% per 5 stones (max +400%).",
            "Stat Stones add +1 per 3 stones (max +66) or +10% per 3 stones (max +660%).",
            "Max-tier fusion items (Hero Drink, Adamantite, Dark Matter, Mythril, Gysahl Greens, Fat Chocobo Feather, Lunar Harp, Zeio Nut) add +1 (max +100) or +10% (max +999%) per item.",
            "When building a Libra transfer Materia, stop at +98 (or +980% HP) so it remains open to item conversion during final fusion.",
        ],
        "classOrder": list(class_grades.keys()),
        "classDefinitions": class_definitions,
        "materiaCatalog": materia_catalog,
        "classMatrix": serializable_matrix,
        "specialOverrides": special_overrides,
        "keyRecipes": [
            {"result": "Costly Punch", "resultId": "item_costly_punch", "ingredientA": "Goblin Punch / Iron Fist / Magical Punch", "ingredientB": "Any DMW Materia (or Libra w/ +980% HP)", "note": "Hard Mode MVP: ignores defense, 99,999 damage at high HP."},
            {"result": "Magical Punch", "resultId": "item_magical_punch", "ingredientA": "Goblin Punch", "ingredientB": "Firaga / Blizzaga / Thundaga", "note": "Strong midgame bridge into Costly Punch."},
            {"result": "Aerial Drain", "resultId": "item_aerial_drain", "ingredientA": "High Jump", "ingredientB": "Drain / Osmose / Assault Twister", "note": "Grants invincibility frames during jump and heals to full HP."},
            {"result": "High Jump", "resultId": "item_high_jump", "ingredientA": "Jump", "ingredientB": "Darkness / Assault Twister", "note": "Upgraded jump; prerequisite for Aerial Drain."},
            {"result": "Darkness", "resultId": "item_darkness", "ingredientA": "Assault Twister / Jump", "ingredientB": "Drain / Gravity / Dark Fire", "note": "Fast midgame AoE HP-cost wave clear."},
            {"result": "Assault Twister+", "resultId": "item_assault_twister_plus", "ingredientA": "Assault Twister (M)", "ingredientB": "VIT UP / Status Strike", "note": "Multi-hit spin attack; strong early Command Materia."},
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


EXPANDED_MISSABLES: list[dict[str, Any]] = [
    {"id": "miss_ch1_fort_tamblin", "chapter": "Chapter 1", "title": "Hero of the Wutai War? (All 16 Groups)", "category": "Trophy / Gear", "detail": "In Fort Tamblin Courtyard, defeat all 16 enemy groups (including rotating walls & watchtowers) to receive the top evaluation from Lazard.", "missionId": None},
    {"id": "miss_ch1_cursed_ring", "chapter": "Chapter 1", "title": "Cursed Ring (Supply Pod)", "category": "Accessory", "detail": "Before departing for Wutai, inspect the Supply Pod 20 times in the Training Room/briefing area to receive Cursed Ring.", "missionId": None},
    {"id": "miss_ch1_wutai_prison", "chapter": "Chapter 1", "title": "Wutai Fortress Chests (Fire Armlet & Elixir)", "category": "Story Chests", "detail": "Loot every chest along the mountain path and Tamblin interior before defeating Vajradhara Tai & Wu.", "missionId": None},
    {"id": "miss_ch2_mako_miner", "chapter": "Chapter 2", "title": "Master Mako Stone Miner / Materia Room", "category": "Trophy", "detail": "Complete all Materia Room mini-requests (check chests and extract the 5 Mako Stones) in Shinra Building before progressing to Banora.", "missionId": None},
    {"id": "miss_ch2_fan_clubs", "chapter": "Chapter 2–3", "title": "Join 3 Fan Clubs (Genesis, Angeal, LOVELESS)", "category": "Mail Senders", "detail": "Talk to the fans in Sector 8 Fountain & Loveless Avenue in Ch. 2 or Ch. 3 (last chance!) for Mail Completionist.", "missionId": None},
    {"id": "miss_ch2_banora_lifestream", "chapter": "Chapter 2", "title": "Banora 5 Glowing Lifestream Spots & Shell Slicing", "category": "Trophy", "detail": "Collect all 5 glowing items around Banora Village before entering Angeal's house, then slice all 10 shells outside the factory for Banora Treasures.", "missionId": None},
    {"id": "miss_ch3_squats", "chapter": "Chapter 3–5", "title": "Training Room Squats (All 4 Challengers)", "category": "Trophy / Items", "detail": "Win all 4 Squat tiers in the SOLDIER Training Room before Chapter 7 ends (unlocks Flower Wagon parts & Shinra Trooper/Captain mail).", "missionId": None},
    {"id": "miss_ch3_genesis_study", "chapter": "Chapter 3", "title": "Prevent Red Leather / Study Group Disband", "category": "Mail Senders", "detail": "In Ch. 3 Sector 8 Fountain, encourage the Genesis Red Leather fan ('Someone wealthy...') and don't discourage Angeal/Study Group members.", "missionId": None},
    {"id": "miss_ch4_minigames", "chapter": "Chapter 4", "title": "Aerith Affection & Sector 5/8 Mini-Games", "category": "Trophies", "detail": "Win Perfume Blending (exact drops), Number Guessing, Materia Pick-Up, Wallet Catch, and Spy Catching before leaving Midgar.", "missionId": None},
    {"id": "miss_ch4_spies", "chapter": "Chapter 4", "title": "Catch All 6 Wutai Spies (M4-3-x Chain)", "category": "Missions", "detail": "Speak to the SOLDIER in Loveless Avenue and expose all 6 Wutai spies in Midgar (unlocks M4-3-1 through M4-3-6 and Happy Turtle shop).", "missionId": "M4-3-6"},
    {"id": "miss_ch5_reporter_silver", "chapter": "Chapter 5", "title": "Reporter Mail & Silver Elite Mission NPC", "category": "Missions & Mail", "detail": "Do NOT report the Sector 8 Reporter; answer his quiz. Talk to the Shinra Entrance employee ('Sephiroth never misses...') for Silver Elite & M2-2-x/M5-x triggers.", "missionId": None},
    {"id": "miss_ch5_modeoheim_sniper", "chapter": "Chapter 5", "title": "Modeoheim Sniper & Stealth Infiltration (5 Chests)", "category": "Trophies", "detail": "Hit every enemy/barrel with the Sniper Rifle without missing/overheating, then sneak past guards in the Mako Excavation Facility to loot all 5 chests.", "missionId": None},
    {"id": "miss_ch5_mako_fan", "chapter": "Chapter 5", "title": "City Planning Director (Sector 8 Shop M6-2-1)", "category": "Missions & Shop", "detail": "Speak to the City Planning Director in Shinra Entrance Hall to unlock M6-2-1 (Sector 8 Materia Shop).", "missionId": "M6-2-1"},
    {"id": "miss_ch6_cissnei_mail", "chapter": "Chapter 6", "title": "Zack Fan Club (Talk to Cissnei in Junon)", "category": "Mail Senders", "detail": "After Junon Defense, speak to Cissnei before leaving Junon; then finish with the Shinra receptionist in Ch. 7.", "missionId": None},
    {"id": "miss_ch6_junon_gates", "chapter": "Chapter 6", "title": "Junon Defense — Zero Enemies Past the Line", "category": "Trophy / Reward", "detail": "Defeat all invading machines at the Junon Upper Path so none breach the barrier for the bonus trophy & reward.", "missionId": None},
    {"id": "miss_ch7_flower_wagons", "chapter": "Chapter 7", "title": "Build All 3 Flower Wagons for Aerith", "category": "Trophy", "detail": "Complete all 3 Flower Wagon builds in Sector 5 Church before departing Midgar (requires Squatting, Spy/Mission & Shinra Bldg pickups).", "missionId": None},
    {"id": "miss_ch7_point_of_no_return", "chapter": "Chapter 7 (CRITICAL)", "title": "Midgar Point of No Return — All 16 NPC Mission Chains", "category": "Point of No Return", "detail": "Leaving Midgar at the end of Ch. 7 permanently locks all Midgar NPC mission givers (M1-2-x, M2-1-x, M2-2-x, M4-3-x, M6-2-x, M7-1-x), Flower Wagon, and Fan Club mail!", "missionId": "M6-2-1"},
    {"id": "miss_ch8_phoenix", "chapter": "Chapter 8", "title": "Phoenix DMW Summon (Nibelheim Water Tower)", "category": "MISSABLE DMW", "detail": "Talk to the boy near the Nibelheim Inn to start Seven Wonders, then examine the Water Tower to earn Phoenix. Only missable DMW!", "missionId": None},
    {"id": "miss_ch8_seven_wonders", "chapter": "Chapter 8", "title": "Seven Wonders of Nibelheim (All 7 Steps + Safe Code)", "category": "Trophy", "detail": "Solve Wonders 1–6 in Ch. 8 (Water Tower, Portrait, Bomb, Manor Safe, Cave, Burning Village) and Wonder 7 in Nibelheim Outskirts before Ch. 9.", "missionId": None},
    {"id": "miss_ch9_waterfall", "chapter": "Chapter 9", "title": "Gongaga Waterfall 7 Chests Mini-Game", "category": "Trophy", "detail": "In Gongaga Hills, dodge monsters and open all 7 treasure chests falling down the waterfall before fighting Zack's ambush.", "missionId": None},
    {"id": "miss_ch9_qmc_plus", "chapter": "Chapter 9", "title": "Research Dept. QMC+ Shop (Gongaga Chest)", "category": "MISSABLE SHOP", "detail": "Open the hidden chest in Gongaga Village outskirts in Ch. 9/10 to unlock Research Dept. QMC+ before the final dungeon.", "missionId": None},
    {"id": "miss_ch10_caged_goddess", "chapter": "Chapter 10", "title": "7 Goddess Materia & Depths of Judgment Caged Doors", "category": "Story Bosses / Gear", "detail": "Collect all 7 Goddess Materia in Banora Underground to open the Depths of Judgment gate and unlock Behemoth King's optional corridor.", "missionId": None},
]


def _build_zack_base_stats() -> list[dict[str, Any]]:
    """Returns Zack's Lv. 1-99 base stats and cumulative EXP table for Crisis Core Reunion."""
    # Exact anchor points from Crisis Core official progression, smoothly interpolated between anchors
    anchors = [
        (1, 610, 37, 42, 11, 11, 11, 11, 10, 0),
        (5, 830, 58, 62, 14, 14, 14, 14, 12, 340),
        (10, 1170, 88, 92, 18, 18, 18, 18, 15, 2240),
        (15, 1610, 124, 128, 22, 22, 22, 22, 18, 7600),
        (20, 2130, 166, 170, 26, 26, 26, 26, 21, 18500),
        (25, 2730, 214, 218, 30, 30, 30, 30, 24, 37200),
        (30, 3420, 268, 272, 34, 34, 34, 34, 27, 66100),
        (40, 4960, 386, 390, 41, 41, 41, 41, 32, 162000),
        (50, 6580, 514, 518, 48, 48, 48, 48, 37, 324000),
        (60, 7920, 646, 650, 55, 55, 55, 55, 42, 578000),
        (70, 8890, 774, 778, 61, 61, 61, 61, 46, 945000),
        (80, 9480, 882, 886, 66, 66, 66, 66, 50, 1445000),
        (90, 9820, 956, 960, 71, 71, 71, 71, 53, 2105000),
        (99, 9999, 999, 999, 75, 75, 75, 75, 56, 2860000),
    ]
    rows: list[dict[str, Any]] = []
    for lv in range(1, 100):
        a0 = anchors[0]
        a1 = anchors[-1]
        for idx in range(len(anchors) - 1):
            if anchors[idx][0] <= lv <= anchors[idx + 1][0]:
                a0, a1 = anchors[idx], anchors[idx + 1]
                break
        span = max(1, a1[0] - a0[0])
        t = (lv - a0[0]) / span
        lerp = lambda i: int(round(a0[i] + (a1[i] - a0[i]) * t))
        rows.append({
            "level": lv,
            "hp": min(9999, lerp(1)),
            "mp": min(999, lerp(2)),
            "ap": min(999, lerp(3)),
            "atk": lerp(4),
            "vit": lerp(5),
            "mag": lerp(6),
            "spr": lerp(7),
            "lck": lerp(8),
            "totalExp": lerp(9),
        })
    return rows


def build_compendium_extra_json(
    enemies: list[dict[str, Any]],
    items: dict[str, dict[str, Any]],
    missions: list[dict[str, Any]],
) -> dict[str, Any]:
    story_chapters = [
        {
            "id": "ch_1",
            "chapter": 1,
            "title": "Chapter 1: Hold Onto Your Dreams",
            "location": "Midgar Simulation · Wutai (Fort Tamblin)",
            "summary": "Zack's first mission as SOLDIER 2nd Class alongside Angeal in Wutai's Fort Tamblin, ending with the summon ambush by Genesis's allies.",
            "keyObjectives": [
                "Defeat Behemoth on the simulated Midgar train.",
                "Inspect the Supply Pod 20 times in the Training Room/briefing area for Cursed Ring (MISSABLE).",
                "Defeat all 16 enemy groups in Fort Tamblin Courtyard (including rotating walls & watchtowers) for Lazard's top evaluation (MISSABLE).",
                "Defeat Vajradhara Wu & Tai and then Ifrit with Sephiroth's aid.",
            ],
            "storyPickups": ["Cursed Ring (Supply Pod x20)", "Fire Armlet (Fort Tamblin)", "Elixir (Fort Tamblin)", "Earrings / Soma"],
            "missableAlert": "MISSABLE: Supply Pod Cursed Ring & Hero of the Wutai War? (16 enemy groups in Fort Tamblin Courtyard).",
            "bosses": [
                {"enemyId": "enemy_behemoth", "name": "Behemoth", "tactics": "Stay behind its tail to avoid Double Claw Swipe and Gyro Tail; use Battle Stance Strong Attacks."},
                {"enemyId": "enemy_vajradhara_wu", "name": "Vajradhara Wu & Tai", "tactics": "Separate them with dodges, cast Barrier, and focus one down at a time."},
                {"enemyId": "enemy_ifrit", "name": "Ifrit", "tactics": "Weak to Ice (Blizzard). Never cast Fire. Break Hellfire's Skill Power gauge immediately."},
            ],
        },
        {
            "id": "ch_2",
            "chapter": 2,
            "title": "Chapter 2: We're Not Monsters",
            "location": "Shinra Building · Banora Village",
            "summary": "Zack investigates Angeal's hometown of Banora alongside Tseng, uncovering Genesis's clones and a hidden factory.",
            "keyObjectives": [
                "Complete all Materia Room mini-requests in Shinra Building (MISSABLE trophy).",
                "Join Genesis Red Leather, Genesis Study Group, and Angeal Fan Clubs in Sector 8 (Ch. 2–3).",
                "Collect all 5 glowing Lifestream spots in Banora before the bombing raid (MISSABLE trophy).",
                "Slice all 10 artillery shells outside the Banora factory (MISSABLE).",
            ],
            "storyPickups": ["5 Banora Lifestream Treasures", "Magic/Power/Guard Mako Stones", "Banora Apple Juice / Hi-Potions"],
            "missableAlert": "MISSABLE: Master Mako Stone Miner (Materia Room), Banora 5 Lifestream Treasures, and Fan Club triggers.",
            "bosses": [
                {"enemyId": "enemy_guard_spider", "name": "Guard Spider", "tactics": "Weak to Lightning. Circle behind it when it fires machine-gun volleys."},
                {"enemyId": "enemy_g_erasers" if False else "enemy_g_eraser", "name": "G Eraser (Ch.3) / Banora Units", "tactics": "Use Thunder/Assault Twister and guard melee rushes in Battle Stance."},
            ],
        },
        {
            "id": "ch_3",
            "chapter": 3,
            "title": "Chapter 3: The Angels Dream of One Thing",
            "location": "Shinra Building · Sector 8 Streets",
            "summary": "Zack is promoted to SOLDIER 1st Class as Genesis Copies invade the Shinra Building.",
            "keyObjectives": [
                "Do Squat mini-game in SOLDIER Training Room as tiers unlock.",
                "LAST CHANCE: Join all 3 Sector 8 Fan Clubs (Red Leather, Study Group, Keepers of Honor) and give supportive dialogue.",
                "Defend Shinra Building floors and defeat G Eraser (auto-unlocks Research Dept. QMC shop!).",
            ],
            "storyPickups": ["Research Dept. QMC Shop (Story automatic)", "Cura / Barrier chests during Shinra defense"],
            "missableAlert": "LAST CHANCE for Sector 8 Fan Clubs & dialogue choices before Ch. 4 locks them!",
            "bosses": [
                {"enemyId": "enemy_g_eraser", "name": "G Eraser", "tactics": "Guard his spin slash in Battle Stance and punish with Fire/Thunder or Assault Twister. Unlocks Research Dept. QMC."},
            ],
        },
        {
            "id": "ch_4",
            "chapter": 4,
            "title": "Chapter 4: Where Did Everyone Go?",
            "location": "Sector 5 Slums · Sector 8 · Shinra HQ",
            "summary": "Zack meets Aerith Gainsborough in the Sector 5 Church and explores the slums before returning to Midgar during an emergency.",
            "keyObjectives": [
                "Win Sector 5 mini-games: Number Guessing, Perfume Blending (perfect drops), Materia Pick-Up, and Wallet Thief (MISSABLE trophies).",
                "Catch all 6 Wutai Spies in Midgar for the SOLDIER in Loveless Avenue (unlocks M4-3-x & Happy Turtle).",
                "Clear M7-2-1 ASAP for Item Fusion Tome and M6-2-1/M6-2-3 for Sector 8 & 5 Shops.",
            ],
            "storyPickups": ["Aerith Affection Points", "Item Fusion Tome (M7-2-1)", "Happy Turtle (M4-3-6)"],
            "missableAlert": "MISSABLE: Sector 5 mini-game trophies, Aerith affection bonuses, and 6 Wutai Spies.",
            "bosses": [
                {"enemyId": "enemy_grosspanzer", "name": "Grosspanzer", "tactics": "Weak to Lightning. Dodging behind the tank avoids Cannon blasts; finish off Panzer Jr. adds first."},
                {"enemyId": "enemy_guard_scorpion", "name": "Guard Scorpion", "tactics": "Cast Barrier, hit with Thunder/Thundara, and guard Tail Laser in Battle Stance."},
            ],
        },
        {
            "id": "ch_5",
            "chapter": 5,
            "title": "Chapter 5: So Good to Be Back",
            "location": "Modeoheim · Mako Excavation Facility",
            "summary": "Zack and Cloud infiltrate snowy Modeoheim to confront Hollander, Genesis, and Angeal.",
            "keyObjectives": [
                "Before leaving Midgar: answer the Reporter's quiz (do NOT report him) and talk to Silver Elite & City Planning Director.",
                "Ace the Modeoheim Sniper mini-game without missing or overheating (MISSABLE trophy).",
                "Sneak past guards in Mako Excavation Facility and open all 5 chests undetected (MISSABLE trophy).",
            ],
            "storyPickups": ["5 Stealth Facility Chests", "Dispel / Lightning Armlet", "M6-2-6 trigger"],
            "missableAlert": "MISSABLE: Sniper Elite & Master Infiltrator trophies in Modeoheim; Reporter & Silver Elite NPCs in Midgar.",
            "bosses": [
                {"enemyId": "enemy_g_eliminator", "name": "G Eliminator", "tactics": "Keep Barrier up, stay behind him, and interrupt his charged slash."},
                {"enemyId": "enemy_angeal_penance", "name": "Angeal Penance", "tactics": "Never attack his front when Defense of Lust is raised! Circle behind for back-crit Strong Attacks & High Jump."},
            ],
        },
        {
            "id": "ch_6",
            "chapter": 6,
            "title": "Chapter 6: Are You Still Protecting Your Honor?",
            "location": "Costa del Sol · Junon",
            "summary": "Zack rests at Costa del Sol before defending Junon against a massive Genesis machine assault.",
            "keyObjectives": [
                "Defeat all invading machines during Junon Defense without letting any pass the line (MISSABLE trophy).",
                "Talk to Cissnei in Junon after the defense to start Zack's Fan Club (MISSABLE mail sender).",
                "Unlock Sector 7 Shop (M4-4-3) for Mog's Amulet & Brigand's Gloves and M7-2-2/M7-2-5 for 4 Accessory Slots.",
            ],
            "storyPickups": ["Junon Defense Bonus Reward", "Cissnei Fan Club Starter", "4 Accessory Slots (M7-2-2 & M7-2-5)"],
            "missableAlert": "MISSABLE: Junon Defense perfect clear trophy & Cissnei Zack Fan Club trigger.",
            "bosses": [
                {"enemyId": "enemy_generals_tank", "name": "General's Tank", "tactics": "Weak to Lightning. Use Thundara/Thundaga and Wall/Barrier to shrug off cannon fire."},
                {"enemyId": "enemy_hollander", "name": "Hollander", "tactics": "Steal/Mug if possible, dodge his AoE potions/bombs, and punish with High Jump."},
            ],
        },
        {
            "id": "ch_7",
            "chapter": 7,
            "title": "Chapter 7: I Can't Stay Here Any Longer",
            "location": "Midgar (Sector 5, Sector 8, Shinra HQ)",
            "summary": "Zack returns to Midgar for the last time—building Flower Wagons for Aerith before departing for Nibelheim.",
            "keyObjectives": [
                "Build ALL 3 Flower Wagons for Aerith before speaking to Tseng/departing Midgar (MISSABLE trophy).",
                "Complete Zack Fan Club with the Shinra Receptionist.",
                "CRITICAL: Finish ALL 16 Midgar NPC mission triggers (M1-2-x, M2-1-x, M2-2-x, M4-3-x, M6-2-x, M7-1-x) BEFORE leaving!",
            ],
            "storyPickups": ["3 Flower Wagons", "All Midgar Mission Unlocks", "Bone Village Outlet (M7-5-3)"],
            "missableAlert": "POINT OF NO RETURN: Leaving Midgar at the end of Chapter 7 locks out Midgar forever!",
            "bosses": [
                {"enemyId": "enemy_cutter_machine", "name": "Cutter / Pile / Shot Machines", "tactics": "Clear Support Machine first or use Quake/Darkness + Wall."},
            ],
        },
        {
            "id": "ch_8",
            "chapter": 8,
            "title": "Chapter 8: If This World Were Mine",
            "location": "Nibelheim · Mt. Nibel · Shinra Manor",
            "summary": "Zack, Cloud, Tifa, and Sephiroth arrive in Nibelheim, where Sephiroth discovers his origins in Shinra Manor.",
            "keyObjectives": [
                "Complete Seven Wonders of Nibelheim #1–#6 (Water Tower = MISSABLE Phoenix DMW!; Shinra Manor Safe = Vital Slash + 4-digit peephole code).",
                "Watch the Shinra Manor Basement cutscene and survive the burning Nibelheim encounter.",
                "Do NOT miss Wonder #7 in Nibelheim Outskirts right after the fire!",
            ],
            "storyPickups": ["Phoenix DMW (Water Tower — MISSABLE)", "Vital Slash (Shinra Manor Safe)", "Wall / Drainga chests"],
            "missableAlert": "MISSABLE: Phoenix DMW (only missable DMW!) & Seven Wonders Expert trophy.",
            "bosses": [
                {"enemyId": "enemy_sephiroth", "name": "Sephiroth (Reactor)", "tactics": "Phase 1: Guard/dodge Octaslash & Heartless Angel; Phase 2: Stay away from the edge so you aren't knocked off the bridge!"},
            ],
        },
        {
            "id": "ch_9",
            "chapter": 9,
            "title": "Chapter 9: We'll All Be Heroes",
            "location": "Nibelheim Outskirts · Gongaga",
            "summary": "Four years after Nibelheim, Zack escapes with Cloud and fights through Shinra forces to Gongaga.",
            "keyObjectives": [
                "Complete Seven Wonders #7 in Nibelheim Outskirts for Wall Materia.",
                "Open the hidden chest in Gongaga Outskirts for Research Dept. QMC+ Shop (MISSABLE).",
                "Complete the Gongaga Waterfall 7-Chest mini-game (MISSABLE trophy).",
            ],
            "storyPickups": ["Research Dept. QMC+ (MISSABLE SHOP)", "7 Gongaga Waterfall Chests", "Wall Materia (Wonder #7)"],
            "missableAlert": "MISSABLE: Research Dept. QMC+ shop chest & Waterfall Chaser 7-chest trophy.",
            "bosses": [
                {"enemyId": "enemy_hollander", "name": "Hollander (Gongaga)", "tactics": "Uses Genesis Copy clones & status bombs. Bring Status Ward or Ribbon + High Jump / Costly Punch."},
            ],
        },
        {
            "id": "ch_10",
            "chapter": 10,
            "title": "Chapter 10: My Living Legacy",
            "location": "Banora Underground · Depths of Judgment · Midgar Outskirts",
            "summary": "The final chapter inside Banora's Lifestream cavern: solve the LOVELESS tablets, collect the 7 Goddess Materia, and defeat Genesis.",
            "keyObjectives": [
                "Collect all 7 Goddess Materia in Banora Underground to unlock the Depths of Judgment gate.",
                "Optional: Defeat Behemoth King in the Depths of Judgment for Goddess Key.",
                "Before touching the final save point/Genesis trigger, finish all remaining Missions (M1-M10) or prep for New Game+.",
            ],
            "storyPickups": ["7 Goddess Materia (Light, Heaven, Ground, Star, Life, Being, Sabbath)", "Goddess Key (Behemoth King)", "Energy / Flare chests"],
            "missableAlert": "Point of No Return inside Lake of Oblivion—save at the final save point before triggering the ending!",
            "bosses": [
                {"enemyId": "enemy_behemoth_king", "name": "Behemoth King", "tactics": "Optional Depth of Judgment boss (576k Hard HP). Drops Goddess Key. Loop Costly Punch behind it and heal through Comet/Quake."},
                {"enemyId": "enemy_genesis_avatar", "name": "Genesis Avatar", "tactics": "Break his sword barriers and clear summoned G Shadow adds with Quake/Darkness before bursting the Avatar."},
                {"enemyId": "enemy_genesis_final_boss", "name": "Genesis (Final)", "tactics": "Keep Wall + Phoenix Down active, dodge Black Flurry/Apocalypse, and finish with Costly Punch or Battle Stance."},
            ],
        },
    ]

    trophies = [
        {"id": "tr_01", "name": "My Living Legacy", "grade": "Platinum", "chapter": "Endgame", "missable": False, "category": "Collection", "description": "Acquire all trophies.", "howToUnlock": "Unlock all other 50 trophies across one or multiple playthroughs (or NG+).", "missionId": None, "storyChapterId": "ch_10"},
        {"id": "tr_02", "name": "Come and Get It", "grade": "Bronze", "chapter": "Ch. 1", "missable": False, "category": "Story", "description": "Complete Chapter 1.", "howToUnlock": "Clear the Wutai invasion and defeat Ifrit in Chapter 1.", "missionId": None, "storyChapterId": "ch_1"},
        {"id": "tr_03", "name": "We're Not Monsters", "grade": "Bronze", "chapter": "Ch. 2", "missable": False, "category": "Story", "description": "Complete Chapter 2.", "howToUnlock": "Investigate Banora and escape the bombing raid.", "missionId": None, "storyChapterId": "ch_2"},
        {"id": "tr_04", "name": "Angels Dream of One Thing", "grade": "Bronze", "chapter": "Ch. 3", "missable": False, "category": "Story", "description": "Complete Chapter 3.", "howToUnlock": "Defend Shinra HQ and defeat Genesis's forces.", "missionId": None, "storyChapterId": "ch_3"},
        {"id": "tr_05", "name": "Where Did Everyone Go?", "grade": "Bronze", "chapter": "Ch. 4", "missable": False, "category": "Story", "description": "Complete Chapter 4.", "howToUnlock": "Meet Aerith, clear Sector 5, and defeat Guard Scorpion.", "missionId": None, "storyChapterId": "ch_4"},
        {"id": "tr_06", "name": "Protect Your Honor", "grade": "Bronze", "chapter": "Ch. 5", "missable": False, "category": "Story", "description": "Complete Chapter 5.", "howToUnlock": "Infiltrate Modeoheim and defeat Angeal Penance.", "missionId": None, "storyChapterId": "ch_5"},
        {"id": "tr_07", "name": "Did You Think I Was Dead?", "grade": "Bronze", "chapter": "Ch. 6", "missable": False, "category": "Story", "description": "Complete Chapter 6.", "howToUnlock": "Defend Junon and confront Hollander.", "missionId": None, "storyChapterId": "ch_6"},
        {"id": "tr_08", "name": "I May Leave Shinra", "grade": "Bronze", "chapter": "Ch. 7", "missable": False, "category": "Story", "description": "Complete Chapter 7.", "howToUnlock": "Build the Flower Wagon and depart Midgar for Nibelheim.", "missionId": None, "storyChapterId": "ch_7"},
        {"id": "tr_09", "name": "I'm Coming to See You", "grade": "Bronze", "chapter": "Ch. 8", "missable": False, "category": "Story", "description": "Complete Chapter 8.", "howToUnlock": "Survive the Nibelheim Incident and face Sephiroth.", "missionId": None, "storyChapterId": "ch_8"},
        {"id": "tr_10", "name": "We'll All Be Heroes", "grade": "Bronze", "chapter": "Ch. 9", "missable": False, "category": "Story", "description": "Complete Chapter 9.", "howToUnlock": "Escape Nibelheim and survive Gongaga.", "missionId": None, "storyChapterId": "ch_9"},
        {"id": "tr_11", "name": "Thank You, Zack", "grade": "Silver", "chapter": "Ch. 10", "missable": False, "category": "Story", "description": "Complete the game.", "howToUnlock": "Defeat Genesis Avatar and Genesis in Chapter 10.", "missionId": None, "storyChapterId": "ch_10"},
        {"id": "tr_12", "name": "He Wouldn't Betray Us", "grade": "Bronze", "chapter": "Ch. 1", "missable": False, "category": "Combat", "description": "Use a Limit Break for the first time.", "howToUnlock": "Roll any triple character image on the DMW and activate Limit Verge.", "missionId": None, "storyChapterId": "ch_1"},
        {"id": "tr_13", "name": "Embrace Your Dreams", "grade": "Bronze", "chapter": "Ch. 1", "missable": False, "category": "Combat", "description": "Master a Materia for the first time.", "howToUnlock": "Level any Materia to Lv. 5 (Master) via DMW reels.", "missionId": "M1-1-1", "storyChapterId": None},
        {"id": "tr_14", "name": "Overpowered", "grade": "Bronze", "chapter": "Ch. 4+", "missable": False, "category": "Combat", "description": "Perform Materia Fusion for the first time.", "howToUnlock": "Unlock Materia Fusion in Ch. 3/4 and fuse any two Materia.", "missionId": "M7-2-1", "storyChapterId": None},
        {"id": "tr_15", "name": "First-Rate SOLDIER", "grade": "Bronze", "chapter": "Any", "missable": False, "category": "Combat", "description": "Defeat 100 enemies using Skills or Magic.", "howToUnlock": "Unlocked naturally while clearing missions and story.", "missionId": None, "storyChapterId": None},
        {"id": "tr_16", "name": "Limit Break Collector", "grade": "Bronze", "chapter": "Ch. 1", "missable": False, "category": "Combat", "description": "Use Buster Sword Stance for the first time.", "howToUnlock": "Enter Battle Stance (Square+X / Guard+Attack) after inheriting Buster Sword.", "missionId": "M1-2-1", "storyChapterId": None},
        {"id": "tr_17", "name": "SOLDIER of Legend", "grade": "Silver", "chapter": "Ch. 10", "missable": False, "category": "Combat", "description": "Complete the game on Hard Mode.", "howToUnlock": "Beat Chapter 10 on Hard difficulty (can switch to Hard right before final boss, or play whole run on Hard).", "missionId": None, "storyChapterId": "ch_10"},
        {"id": "tr_18", "name": "Hero of the Wutai War?", "grade": "Bronze", "chapter": "Ch. 1", "missable": True, "category": "Missable Mini-Game", "description": "Receive the top evaluation from Lazard in Wutai.", "howToUnlock": "In Ch. 1 Fort Tamblin Courtyard, defeat all 16 enemy groups (including rotating walls & watchtowers) before entering the castle.", "missionId": None, "storyChapterId": "ch_1"},
        {"id": "tr_19", "name": "Master Mako Stone Miner", "grade": "Bronze", "chapter": "Ch. 2", "missable": True, "category": "Missable Mini-Game", "description": "Obtain all items from the Materia Room.", "howToUnlock": "In Ch. 2 Shinra Building Materia Room, complete the researcher's Mako extraction mini-tasks for all 5 Mako Stones.", "missionId": None, "storyChapterId": "ch_2"},
        {"id": "tr_20", "name": "Banora Treasures", "grade": "Bronze", "chapter": "Ch. 2", "missable": True, "category": "Missable Mini-Game", "description": "Collect all items in Banora and enter the house before time runs out.", "howToUnlock": "Grab all 5 glowing Lifestream items around Banora Village before entering Angeal's house.", "missionId": None, "storyChapterId": "ch_2"},
        {"id": "tr_21", "name": "Slicin' SOLDIER", "grade": "Bronze", "chapter": "Ch. 2", "missable": True, "category": "Missable Mini-Game", "description": "Cut down all 10 artillery shells in Banora.", "howToUnlock": "Time your sword swings to slice all 10 shells outside the Banora factory.", "missionId": None, "storyChapterId": "ch_2"},
        {"id": "tr_22", "name": "Everyone's Hero", "grade": "Bronze", "chapter": "Ch. 3", "missable": True, "category": "Missable Mini-Game", "description": "Save all Shinra employees during the Sector 8 assault.", "howToUnlock": "Check every corridor in Shinra Building during the Ch. 3 attack and rescue every trapped employee.", "missionId": None, "storyChapterId": "ch_3"},
        {"id": "tr_23", "name": "Fan Club Aficionado", "grade": "Bronze", "chapter": "Ch. 2–7", "missable": True, "category": "Missable Mini-Game", "description": "Join every Fan Club.", "howToUnlock": "Join Red Leather, Study Group, Keepers of Honor (Ch. 2–3), Silver Elite (Ch. 5), and Zack Fan Club (Ch. 6–7).", "missionId": None, "storyChapterId": "ch_3"},
        {"id": "tr_24", "name": "Master Blender", "grade": "Bronze", "chapter": "Ch. 4", "missable": True, "category": "Missable Mini-Game", "description": "Mix the perfect perfume for Aerith.", "howToUnlock": "In Ch. 4 Sector 5 Slums, match the shopkeeper's exact drop count/timing at the perfume stand.", "missionId": None, "storyChapterId": "ch_4"},
        {"id": "tr_25", "name": "Bingo!", "grade": "Bronze", "chapter": "Ch. 4", "missable": True, "category": "Missable Mini-Game", "description": "Guess the exact number in the Sector 5 Market.", "howToUnlock": "Ask the kids for clues to narrow down the 1-digit secret number on your first try.", "missionId": None, "storyChapterId": "ch_4"},
        {"id": "tr_26", "name": "Godlike", "grade": "Bronze", "chapter": "Ch. 4", "missable": True, "category": "Missable Mini-Game", "description": "Collect Materia fastest in the Sector 5 mini-game.", "howToUnlock": "Clear the Materia Pick-Up mini-game in Sector 5 Market under 14 seconds.", "missionId": None, "storyChapterId": "ch_4"},
        {"id": "tr_27", "name": "Good Match For Aerith", "grade": "Bronze", "chapter": "Ch. 4", "missable": True, "category": "Missable Mini-Game", "description": "Max out Aerith's affection evaluation.", "howToUnlock": "Reach high Aerith affection by acing Sector 5 mini-games and returning the stolen wallet quickly.", "missionId": None, "storyChapterId": "ch_4"},
        {"id": "tr_28", "name": "Wutai's Nemesis", "grade": "Bronze", "chapter": "Ch. 4", "missable": True, "category": "Missable Mini-Game", "description": "Capture all Wutai spies in Midgar.", "howToUnlock": "Find and speak to all 6 disguised Wutai spies across Midgar in Chapter 4.", "missionId": "M4-3-6", "storyChapterId": "ch_4"},
        {"id": "tr_29", "name": "Fan Club Savior", "grade": "Bronze", "chapter": "Ch. 3–7", "missable": True, "category": "Missable Mini-Game", "description": "Prevent all Fan Clubs from disbanding.", "howToUnlock": "Pick supportive dialogue for Red Leather (Ch. 3), Study Group (Ch. 3/5), and Keepers of Honor (Ch. 5).", "missionId": None, "storyChapterId": "ch_5"},
        {"id": "tr_30", "name": "Sniper Elite", "grade": "Bronze", "chapter": "Ch. 5", "missable": True, "category": "Missable Mini-Game", "description": "Destroy all escaping enemies with the Sniper Rifle without missing or overheating.", "howToUnlock": "In Modeoheim ravine, upgrade the rifle at the start and snipe every fleeing guard cleanly.", "missionId": None, "storyChapterId": "ch_5"},
        {"id": "tr_31", "name": "Master Infiltrator", "grade": "Bronze", "chapter": "Ch. 5", "missable": True, "category": "Missable Mini-Game", "description": "Open all 5 chests in the Modeoheim facility without being spotted.", "howToUnlock": "Crouch behind crates in Mako Excavation Facility and loot all 5 chests unseen.", "missionId": None, "storyChapterId": "ch_5"},
        {"id": "tr_32", "name": "Immovable Object", "grade": "Bronze", "chapter": "Ch. 6", "missable": True, "category": "Missable Mini-Game", "description": "Defeat every enemy invading Junon without letting any pass.", "howToUnlock": "Intercept all waves on the Junon Upper Path before any robot reaches the elevator gate.", "missionId": None, "storyChapterId": "ch_6"},
        {"id": "tr_33", "name": "Midgar Full of Flowers", "grade": "Bronze", "chapter": "Ch. 7", "missable": True, "category": "Missable Mini-Game", "description": "Build all 3 Flower Wagons for Aerith.", "howToUnlock": "Collect parts from Training Room Squats, Midgar NPCs, and Shinra HQ and craft all 3 wagons in Ch. 7.", "missionId": None, "storyChapterId": "ch_7"},
        {"id": "tr_34", "name": "Seven Wonders Expert", "grade": "Bronze", "chapter": "Ch. 8–9", "missable": True, "category": "Missable Mini-Game", "description": "Solve all Seven Wonders of Nibelheim.", "howToUnlock": "Complete Wonders 1–6 in Ch. 8 (Water Tower, Portrait, Bomb, Manor Safe, Cave, Fire) and Wonder 7 in Ch. 9 Outskirts.", "missionId": None, "storyChapterId": "ch_8"},
        {"id": "tr_35", "name": "Cage Opener", "grade": "Bronze", "chapter": "Ch. 10", "missable": False, "category": "Story", "description": "Unlock all cages in the Depths of Judgment.", "howToUnlock": "Collect all 7 Goddess Materia in Banora Underground and open the cells.", "missionId": None, "storyChapterId": "ch_10"},
        {"id": "tr_36", "name": "Waterfall Chaser", "grade": "Bronze", "chapter": "Ch. 9", "missable": True, "category": "Missable Mini-Game", "description": "Open all 7 treasure chests falling down the Gongaga waterfall.", "howToUnlock": "In Ch. 9 Gongaga Hills, dodge monsters and collect all 7 chests.", "missionId": None, "storyChapterId": "ch_9"},
        {"id": "tr_37", "name": "Precise Restoration", "grade": "Bronze", "chapter": "Ch. 10", "missable": False, "category": "Combat", "description": "Obtain 100% accuracy in the Ch. 10 Escape / Shinra ambush.", "howToUnlock": "Clear all enemy waves cleanly in the Ch. 10 finale encounters.", "missionId": None, "storyChapterId": "ch_10"},
        {"id": "tr_38", "name": "Mission Completionist: 25%", "grade": "Bronze", "chapter": "Any", "missable": False, "category": "Missions", "description": "Complete 25% of all missions (75/300).", "howToUnlock": "Clear any 75 missions across M1–M10.", "missionId": None, "storyChapterId": None},
        {"id": "tr_39", "name": "Mission Completionist: 50%", "grade": "Bronze", "chapter": "Any", "missable": False, "category": "Missions", "description": "Complete 50% of all missions (150/300).", "howToUnlock": "Clear any 150 missions across M1–M10.", "missionId": None, "storyChapterId": None},
        {"id": "tr_40", "name": "Mission Completionist: 75%", "grade": "Bronze", "chapter": "Any", "missable": False, "category": "Missions", "description": "Complete 75% of all missions (225/300).", "howToUnlock": "Clear any 225 missions across M1–M10.", "missionId": None, "storyChapterId": None},
        {"id": "tr_41", "name": "Mission Completionist: 100%", "grade": "Gold", "chapter": "Endgame", "missable": True, "category": "Missions", "description": "Complete all 300 missions.", "howToUnlock": "Unlock all Midgar NPC missions before Ch. 7 Point of No Return and clear M1-1-1 through M10-4-3 (awards Heike Soul).", "missionId": "M9-6-6", "storyChapterId": "ch_7"},
        {"id": "tr_42", "name": "Mail Completionist", "grade": "Silver", "chapter": "Ch. 1–10", "missable": True, "category": "Collection", "description": "Receive mail from every sender (all 20 senders).", "howToUnlock": "Join all 5 Fan Clubs, prevent disbands, and trigger all missable NPCs (Reporter, Cissnei, Silver Elite) before Ch. 7 ends.", "missionId": None, "storyChapterId": "ch_7"},
        {"id": "tr_43", "name": "Shop Completionist", "grade": "Silver", "chapter": "Ch. 1–10", "missable": True, "category": "Collection", "description": "Unlock all 16 shops.", "howToUnlock": "Unlock all mission/story shops plus the MISSABLE Research Dept. QMC+ chest in Ch. 9/10 Gongaga.", "missionId": "M9-5-4", "storyChapterId": "ch_9"},
        {"id": "tr_44", "name": "DMW Master", "grade": "Gold", "chapter": "Ch. 1–10", "missable": True, "category": "Collection", "description": "Achieve 100% on every DMW entry (all 18 images).", "howToUnlock": "Don't miss Phoenix in Ch. 8 Nibelheim! Clear M8-x / M10-x summon & Chocobo missions, then AFK in M1-1-1 (awards Genji Armor).", "missionId": "M1-1-1", "storyChapterId": "ch_8"},
        {"id": "tr_45", "name": "Genji Equipment", "grade": "Bronze", "chapter": "Endgame", "missable": True, "category": "Collection", "description": "Collect all 4 Genji equipment pieces.", "howToUnlock": "Helm (Online Shop Shade M9-5-4), Armor (100% DMW), Shield (Magic Pot M7-6-6), Glove (M9-6-4 chest).", "missionId": "M7-6-6", "storyChapterId": None},
        {"id": "tr_46", "name": "Divine Rule Broken", "grade": "Silver", "chapter": "Endgame", "missable": False, "category": "Superboss", "description": "Defeat Minerva in Mission M9-6-6.", "howToUnlock": "Defeat Minerva (10M Normal / 20M Hard HP) in M9-6-6 using 99,999 HP, 255 VIT/SPR, Costly Punch & Mug.", "missionId": "M9-6-6", "storyChapterId": None},
        {"id": "tr_47", "name": "Goddess Base Discovered", "grade": "Bronze", "chapter": "Ch. 10", "missable": False, "category": "Story", "description": "Defeat Behemoth King in the Depths of Judgment.", "howToUnlock": "Open the locked gate with the 7 Goddess Materia in Ch. 10 and defeat Behemoth King.", "missionId": None, "storyChapterId": "ch_10"},
        {"id": "tr_48", "name": "Buster Sword Proficiency 100%", "grade": "Bronze", "chapter": "Any", "missable": False, "category": "Combat", "description": "Reach 100% Buster Sword Proficiency (or unlock Battle Stance perks).", "howToUnlock": "Max all 4 proficiency pools: Perfect Guard (31.66%), Strong Attack (31.66%), Command Kills (31.66%), Barrier Pierce (5%).", "missionId": "M1-2-1", "storyChapterId": None},
        {"id": "tr_49", "name": "Limit Verge Master", "grade": "Bronze", "chapter": "Ch. 1+", "missable": False, "category": "Combat", "description": "Cancel an enemy's Skill Power gauge completely.", "howToUnlock": "Attack a charging boss with Battle Stance / Costly Punch until the Skill Power bar hits 0%.", "missionId": "M5-1-1", "storyChapterId": None},
        {"id": "tr_50", "name": "99,999 Damage!", "grade": "Bronze", "chapter": "Ch. 6+", "missable": False, "category": "Combat", "description": "Deal 99,999 damage in a single hit.", "howToUnlock": "Equip Brutal (M7-4-6) or Genji Glove (M9-6-4) or reach 23% Buster Sword Proficiency, then use Costly Punch.", "missionId": "M7-4-6", "storyChapterId": None},
        {"id": "tr_51", "name": "Magic Pot's Favorite", "grade": "Bronze", "chapter": "Ch. 5+", "missable": False, "category": "Collection", "description": "Satisfy Magic Pot and earn its DMW or Genji Shield.", "howToUnlock": "Perform all 4 requested actions in M10-2-3 (Jump -> Fira -> Gravity -> Assault Twister) or M7-6-6 (Genji Shield).", "missionId": "M10-2-3", "storyChapterId": None},
    ]

    mail_senders = [
        {"id": "mail_shinra_news", "name": "Shinra News", "category": "Shinra / News", "mailCount": 12, "chapters": "Ch. 1–10", "missable": False, "unlockCondition": "Automatic story dispatches across all chapters.", "missableChoices": "Cannot be missed."},
        {"id": "mail_angeal", "name": "Angeal", "category": "Character", "mailCount": 2, "chapters": "Ch. 1–2", "missable": False, "unlockCondition": "Automatic story mails in Chapters 1 & 2.", "missableChoices": "Cannot be missed."},
        {"id": "mail_kunsel", "name": "Kunsel", "category": "Character", "mailCount": 13, "chapters": "Ch. 1–10", "missable": False, "unlockCondition": "Automatic story & mission-progress mails from Kunsel.", "missableChoices": "Cannot be missed."},
        {"id": "mail_lazard", "name": "Director Lazard", "category": "Character", "mailCount": 2, "chapters": "Ch. 2–5", "missable": False, "unlockCondition": "Automatic story progression mails.", "missableChoices": "Cannot be missed."},
        {"id": "mail_tseng", "name": "Tseng", "category": "Character", "mailCount": 3, "chapters": "Ch. 2–7", "missable": False, "unlockCondition": "Automatic story progression mails.", "missableChoices": "Cannot be missed."},
        {"id": "mail_sephiroth", "name": "Sephiroth", "category": "Character", "mailCount": 1, "chapters": "Ch. 3", "missable": False, "unlockCondition": "Automatic story progression mail.", "missableChoices": "Cannot be missed."},
        {"id": "mail_aerith", "name": "Aerith", "category": "Character", "mailCount": 7, "chapters": "Ch. 4–9", "missable": True, "unlockCondition": "Met in Chapter 4; more mails arrive based on affection & Ch. 7 Flower Wagons.", "missableChoices": "Do Ch. 4 Sector 5 mini-games and Ch. 7 Flower Wagons before leaving Midgar."},
        {"id": "mail_cissnei", "name": "Cissnei", "category": "Character", "mailCount": 6, "chapters": "Ch. 4–9", "missable": False, "unlockCondition": "Automatic story progression + Junon conversation.", "missableChoices": "Talk to Cissnei in Junon (Ch. 6) to also unlock Zack Fan Club."},
        {"id": "mail_cloud", "name": "Cloud", "category": "Character", "mailCount": 3, "chapters": "Ch. 5–8", "missable": False, "unlockCondition": "Automatic story mails after Modeoheim & Nibelheim.", "missableChoices": "Cannot be missed."},
        {"id": "mail_red_leather", "name": "Red Leather (Genesis Fan Club)", "category": "Fan Club", "mailCount": 4, "chapters": "Ch. 2–7", "missable": True, "unlockCondition": "Join from the girl in Sector 8 Fountain in Ch. 2 or Ch. 3.", "missableChoices": "In Ch. 3 Sector 8 Fountain, choose 'Someone wealthy' when asked how to save the club so it doesn't disband!"},
        {"id": "mail_study_group", "name": "Study Group (Genesis Fan Club)", "category": "Fan Club", "mailCount": 4, "chapters": "Ch. 2–7", "missable": True, "unlockCondition": "Join from the fan in Loveless Avenue in Ch. 2 or Ch. 3.", "missableChoices": "In Ch. 3/5, speak to her again and encourage her to merge/keep studying LOVELESS so the club survives."},
        {"id": "mail_keepers_honor", "name": "Keepers of Honor (Angeal Fan Club)", "category": "Fan Club", "mailCount": 4, "chapters": "Ch. 2–7", "missable": True, "unlockCondition": "Join from the fan near Sector 8 Fountain in Ch. 2 or Ch. 3.", "missableChoices": "In Ch. 5, talk to the boy outside Sector 8 Entrance & his mother in Sector 5 Slums to prevent disbanding."},
        {"id": "mail_silver_elite", "name": "Silver Elite (Sephiroth Fan Club)", "category": "Fan Club", "mailCount": 5, "chapters": "Ch. 5–7", "missable": True, "unlockCondition": "In Ch. 5–7, speak to the woman in Sector 6 Park (children's playground) and answer her Sephiroth quiz ('Masamune', 'Super Nova', 'Left-handed').", "missableChoices": "Answer all 3 Sephiroth trivia questions correctly before Ch. 7 ends."},
        {"id": "mail_zack_club", "name": "Zack Fan Club", "category": "Fan Club", "mailCount": 2, "chapters": "Ch. 6–7", "missable": True, "unlockCondition": "Talk to Cissnei in Junon (Ch. 6), then speak to the Receptionist in Shinra Building Entrance (Ch. 7).", "missableChoices": "Must talk to Cissnei in Junon BEFORE boarding the helicopter!"},
        {"id": "mail_reporter", "name": "Reporter", "category": "Secret / Side-Quest", "mailCount": 3, "chapters": "Ch. 5–7", "missable": True, "unlockCondition": "Speak to the suspicious Reporter near Sector 8 Fountain/Loveless Avenue in Ch. 5–7.", "missableChoices": "Choose 'Don't report him' to Hojo/Shinra! Reporting him permanently blocks his mail chain."},
        {"id": "mail_shinra_trooper", "name": "Shinra Trooper", "category": "Secret / Side-Quest", "mailCount": 2, "chapters": "Ch. 3–7", "missable": True, "unlockCondition": "Defeat the Shinra Trooper in Training Room Squats (Tier 1–2).", "missableChoices": "Complete Squat challenges before leaving Midgar at end of Ch. 7."},
        {"id": "mail_shinra_captain", "name": "Shinra Captain", "category": "Secret / Side-Quest", "mailCount": 2, "chapters": "Ch. 3–7", "missable": True, "unlockCondition": "Defeat the SOLDIER 3rd/2nd Class opponents in Training Room Squats (Tier 3–4).", "missableChoices": "Complete all 4 Squat tiers before leaving Midgar at end of Ch. 7."},
        {"id": "mail_treasure_princess", "name": "Treasure Princess (Yuffie)", "category": "Secret / Side-Quest", "mailCount": 14, "chapters": "Ch. 1–10", "missable": False, "unlockCondition": "Triggered by clearing M8-4-x / M8-5-x treasure mail missions.", "missableChoices": "Clear Yuffie's mission chains (M8-4-x through M8-6-x)."},
        {"id": "mail_lord_duo", "name": "Lord Duo", "category": "Secret / Side-Quest", "mailCount": 2, "chapters": "Ch. 7–10", "missable": False, "unlockCondition": "Arrives after unlocking Online Shop Duo (M9-3-3).", "missableChoices": "Unlock Online Shop Duo in M9-3-3."},
        {"id": "mail_mysterious", "name": "???", "category": "Secret / Side-Quest", "mailCount": 6, "chapters": "Ch. 5–10", "missable": False, "unlockCondition": "Arrives automatically as you clear M8-4-x Suspicious Mail & M9-x Great Cavern missions.", "missableChoices": "Clear M8-4-1..6 & M9-x."},
    ]

    minigames = [
        {
            "id": "mg_seven_wonders",
            "title": "Seven Wonders of Nibelheim & Shinra Manor Safe Code",
            "chapter": "Ch. 8–9",
            "missable": True,
            "trophy": "Seven Wonders Expert",
            "summary": "Talk to the boy near the Nibelheim Inn to start each Wonder in order. Includes the MISSABLE Phoenix DMW (#1) and the Shinra Manor Safe (#4).",
            "steps": [
                "Wonder 1 (Water Tower — MISSABLE DMW): Climb/examine the Nibelheim Water Tower for the Phoenix DMW Materia.",
                "Wonder 2 (Inn Portrait): Inspect the painting of the girl on the 2nd floor of the Nibelheim Inn, leave & return until it disappears, then check the Innkeeper.",
                "Wonder 3 (Mt. Nibel Bomb): Head onto Mt. Nibel trail and defeat the special Bomb monster (rewards Gold Shard / Safety Bit).",
                "Wonder 4 (Shinra Manor Safe): Inspect the locked safe upstairs in Shinra Manor. Look through the 4 keyholes in the manor rooms to count: [1] Books not on shelf (East room), [2] Smiling Faces / Ghosts (West room), [3] Banora Apples + Cans (2F East), [4] Chairs (2F West). Use the Safe Code Calculator below!",
                "Wonder 5 (Manor Basement): Examine the coffins in the underground cave/basement (rewards Vital Slash / Moogle).",
                "Wonder 6 (Burning Nibelheim): During the fire, rescue the boy's mother inside the burning house (1-minute timer; rewards ATK Up++).",
                "Wonder 7 (Ch. 9 Outskirts): In Chapter 9 Nibelheim Outskirts, inspect the glowing spot near the fence for Wall Materia.",
            ],
        },
        {
            "id": "mg_flower_wagons",
            "title": "Aerith's 3 Flower Wagons",
            "chapter": "Ch. 7",
            "missable": True,
            "trophy": "Midgar Full of Flowers",
            "summary": "Build all 3 Flower Wagons in Sector 5 Church BEFORE leaving Midgar at the end of Chapter 7.",
            "steps": [
                "Wagon 1 (Cute Wagon — Automatic Story): Tools (Sector 5/Church), Old Lumber (Loveless Ave), Worn Tires (Sector 8), Artisan's Specs (M1-2-x / Shinra).",
                "Wagon 2 (Cool Shinra Wagon): Clear all 4 Squat tiers in SOLDIER Training Room for Shinra Lunch Cart Specs, Shinra Ceramic, Shinra Treads, and Shinra Solder.",
                "Wagon 3 (Gorgeous Wagon): Craft via Mythril Tools (talk to researcher in Shinra Exhibit Room), Walnut Wood (Sector 8), Premium Tires (Sector 5), and Craftsmanship (Loveless Ave).",
            ],
        },
        {
            "id": "mg_perfume",
            "title": "Sector 5 Perfume Blending",
            "chapter": "Ch. 4",
            "missable": True,
            "trophy": "Master Blender",
            "summary": "At the Sector 5 Slums perfume stall, add the exact target drops of Mako perfume oil—zero over/under pours.",
            "steps": [
                "Wait for the shopkeeper's prompt: 1-drop gentle pour = tap once; large pour = hold briefly, or count the exact verbal recipe (e.g. 'just right' = 5 drops).",
                "Mixing the exact count yields '+10 Aerith Affection' and unlocks Master Blender.",
            ],
        },
        {
            "id": "mg_number_guess",
            "title": "Sector 5 Number Guessing",
            "chapter": "Ch. 4",
            "missable": True,
            "trophy": "Bingo!",
            "summary": "Pay 50 Gil to play, then ask the three nearby children for hints before locking your 1-digit guess.",
            "steps": [
                "Talk to all 3 kids around the market stall: Kid 1 reveals odd/even, Kid 2 reveals >5 or <=5, Kid 3 narrows it to 2 numbers.",
                "Guess correctly on the first attempt for Bingo! trophy and maximum Aerith Affection.",
            ],
        },
        {
            "id": "mg_materia_pickup_wallet",
            "title": "Sector 5 Materia Pick-Up & Wallet Thief",
            "chapter": "Ch. 4",
            "missable": True,
            "trophy": "Godlike / Good Match For Aerith",
            "summary": "Clear the Materia Pick-Up speed test under 14 seconds and catch the fleeing thief near the Sector 5 gate.",
            "steps": [
                "Materia Pick-Up: Sprint in a tight clockwise loop starting from the top-left chest to finish in ~11–13 seconds (under 14s = 'Godlike').",
                "Wallet Thief: Chase the kid along Sector 5 Market -> Station Street -> defeat the monsters quickly to boost Aerith Affection.",
            ],
        },
        {
            "id": "mg_aerith_affection",
            "title": "Aerith Affection Hidden Counter",
            "chapter": "Ch. 4 & Ch. 7",
            "missable": True,
            "trophy": "Good Match For Aerith",
            "summary": "Zack's hidden affection score with Aerith unlocks extra mails and the 'Good Match For Aerith' trophy.",
            "steps": [
                "+10 pts: Perfect Perfume Blend; +10 pts: Guess Number in 1 try; +10 pts: Godlike (<14s) Materia Pick-Up.",
                "+5 pts: Buy Aerith the white flower ribbon / accessories at market; +10 pts: Catch Wallet Thief within 15 seconds.",
                "+5 pts each: Dialogue choices praising Aerith or promising to come back in Ch. 4 & Ch. 7.",
                "Threshold: 60+ total points in Ch. 4 triggers the 'Good Match For Aerith' evaluation and trophy.",
            ],
        },
        {
            "id": "mg_banora_shells",
            "title": "Banora 5 Lifestream Treasures & 10 Shells",
            "chapter": "Ch. 2",
            "missable": True,
            "trophy": "Banora Treasures & Slicin' SOLDIER",
            "summary": "Collect all 5 glowing Lifestream items before entering Angeal's house, then slice all 10 artillery shells outside the factory.",
            "steps": [
                "5 Spots (75-second timer): [1] North road near water, [2] Orchard path east, [3] Behind factory entrance, [4] Town square well, [5] Near Angeal's house.",
                "10 Shells: Watch the red flash/spark as each shell approaches Zack and press Attack right before impact.",
            ],
        },
        {
            "id": "mg_squats",
            "title": "SOLDIER Training Room Squats (4 Tiers)",
            "chapter": "Ch. 3–7",
            "missable": True,
            "trophy": "Midgar Full of Flowers / Mail",
            "summary": "Beat all 4 challengers in the Shinra HQ SOLDIER Training Room.",
            "steps": [
                "Tier 1 (Shinra Trooper): 20+ squats -> Shinra Lunch Cart Specs + Trooper Mail.",
                "Tier 2 (SOLDIER 3rd Class): 30+ squats -> Shinra Ceramic.",
                "Tier 3 (SOLDIER 2nd Class): 45+ squats -> Shinra Treads.",
                "Tier 4 (SOLDIER 1st Class Captain): 60+ squats -> Shinra Solder + Captain Mail. Watch Zack's knees hit the lowest point before tapping!",
            ],
        },
        {
            "id": "mg_modeoheim",
            "title": "Modeoheim Sniper & Stealth Infiltration",
            "chapter": "Ch. 5",
            "missable": True,
            "trophy": "Sniper Elite & Master Infiltrator",
            "summary": "Zero-miss Sniper Rifle run followed by 5-chest Stealth Infiltration in the Mako Excavation Facility.",
            "steps": [
                "Sniper: Upgrade the rifle with enemy drops (Power/Barrel) from the first crate/guards; lead moving targets slightly and release zoom between shots to cool down.",
                "Stealth (5 Chests): Crouch behind crates when guards turn away; only move when the guard's patrol icon faces opposite. Loot all 5 chests before entering the boiler door.",
            ],
        },
        {
            "id": "mg_gongaga_depths",
            "title": "Gongaga Waterfall 7 Chests & Ch. 10 LOVELESS Puzzle",
            "chapter": "Ch. 9–10",
            "missable": True,
            "trophy": "Waterfall Chaser / Cage Opener",
            "summary": "Collect all 7 waterfall chests in Ch. 9 Gongaga, then gather all 7 Goddess Materia in Ch. 10 Banora Underground.",
            "steps": [
                "Gongaga Waterfall (Ch. 9): Hug the left/right edges of the river basin while chests fall; dodge Sahagin spawns and open all 7 chests.",
                "Depths of Judgment (Ch. 10): Inspect the 5 LOVELESS stone tablets to reveal portals, collect all 7 Goddess Materia (Light, Heaven, Ground, Star, Life, Being, Sabbath), and insert them into the altar to open the sealed cages & Behemoth King.",
            ],
        },
    ]

    magic_pot_encounters = [
        {
            "id": "mp_m10_2_3",
            "missionId": "M10-2-3",
            "title": "M10-2-3: Master Tonberry — Magic Pot DMW Unlock",
            "priority": "DO THIS FIRST (Unlocks Magic Pot DMW)",
            "requests": [
                {"step": 1, "action": "Jump", "itemId": "item_jump"},
                {"step": 2, "action": "Fira", "itemId": "item_fira"},
                {"step": 3, "action": "Gravity", "itemId": "item_gravity"},
                {"step": 4, "action": "Assault Twister", "itemId": "item_assault_twister"},
            ],
            "rewardName": "Magic Pot DMW Image (Item Mugger)",
            "rewardItemId": "item_item_mugger",
            "tips": "Equip Jump, Fira, Gravity, and Assault Twister before entering. Trigger random encounters until Magic Pot appears; wait for each speech bubble before performing the exact skill.",
        },
        {
            "id": "mp_m7_6_6",
            "missionId": "M7-6-6",
            "title": "M7-6-6: The Determined Recruiter — Genji Shield",
            "priority": "REQUIRED FOR GENJI SET & TROPHY",
            "requests": [
                {"step": 1, "action": "Gil Toss", "itemId": "item_gil_toss"},
                {"step": 2, "action": "Costly Punch", "itemId": "item_costly_punch"},
                {"step": 3, "action": "Deal 99,999 Damage (Break Damage Limit)", "itemId": "item_brutal"},
                {"step": 4, "action": "Octaslash (DMW Limit)", "itemId": "item_octaslash"},
            ],
            "rewardName": "Genji Shield",
            "rewardItemId": "item_genji_shield",
            "tips": "Equip Gil Toss, Costly Punch, Brutal/Genji Glove (or 23%+ Buster Sword), and 4x Octaslash Materia (buy from Research Dept. QMC+!). Wait patiently in battle for Octaslash to trigger as step 4.",
        },
        {
            "id": "mp_m2_2_6",
            "missionId": "M2-2-6",
            "title": "M2-2-6: The Nightmare Begins — Early Magic Pot",
            "priority": "Bonus Early Encounter",
            "requests": [
                {"step": 1, "action": "Blizzard", "itemId": "item_blizzard"},
                {"step": 2, "action": "Fire", "itemId": "item_fire"},
                {"step": 3, "action": "Thunder", "itemId": "item_thunder"},
                {"step": 4, "action": "Gravity", "itemId": "item_gravity"},
            ],
            "rewardName": "Elixir / Magic Pot Bonus",
            "rewardItemId": "item_elixir",
            "tips": "Early mission Magic Pot testing basic elemental spells + Gravity.",
        },
        {
            "id": "mp_m2_5_4",
            "missionId": "M2-5-4",
            "title": "M2-5-4: New Cavern — Midgame Magic Pot",
            "priority": "Bonus Midgame Encounter",
            "requests": [
                {"step": 1, "action": "Ultima", "itemId": "item_ultima"},
                {"step": 2, "action": "Tri-Fire", "itemId": "item_tri_fire"},
                {"step": 3, "action": "Iron Fist", "itemId": "item_iron_fist"},
                {"step": 4, "action": "Electrocute", "itemId": "item_electrocute"},
            ],
            "rewardName": "Elixir / Precious Watch / Rare Drop",
            "rewardItemId": "item_elixir",
            "tips": "Bring high-rank Magic (Ultima, Tri-Fire, Electrocute) plus Iron Fist before farming this random spawn.",
        },
        {
            "id": "mp_m2_5_5",
            "missionId": "M2-5-5",
            "title": "M2-5-5: Another Cavern — Advanced Magic Pot",
            "priority": "Bonus Encounter",
            "requests": [
                {"step": 1, "action": "Ultima", "itemId": "item_ultima"},
                {"step": 2, "action": "Tri-Thundaga", "itemId": "item_tri_thundaga"},
                {"step": 3, "action": "Electrocute", "itemId": "item_electrocute"},
                {"step": 4, "action": "Flare", "itemId": "item_flare"},
            ],
            "rewardName": "Elixir / High-Tier Catalyst",
            "rewardItemId": "item_elixir",
            "tips": "Requires late-game Ultimate Magic Materia; equip Genji Helm (0 MP) or Dualcast/Ethers.",
        },
        {
            "id": "mp_m2_5_6",
            "missionId": "M2-5-6",
            "title": "M2-5-6: The Great Beast — Endgame Magic Pot",
            "priority": "Bonus Encounter",
            "requests": [
                {"step": 1, "action": "Flare", "itemId": "item_flare"},
                {"step": 2, "action": "Energy", "itemId": "item_energy"},
                {"step": 3, "action": "Ultima", "itemId": "item_ultima"},
                {"step": 4, "action": "Costly Punch", "itemId": "item_costly_punch"},
            ],
            "rewardName": "Elixir / Rare Accessory",
            "rewardItemId": "item_elixir",
            "tips": "Pairs cleanly with an Arcane/Costly Punch endgame loadout while clearing M2-5-6.",
        },
    ]

    status_effects = [
        {"id": "st_poison", "name": "Poison", "kind": "Ailment", "effect": "Drains 5% Max HP periodically over time.", "counter": "Cure with Esuna, Remedy, or Potion; prevent with Star Pendant, Pearl Necklace, Ribbon, or Status Ward + Hell-aga.", "itemIds": ["item_star_pendant", "item_status_ward", "item_super_ribbon"]},
        {"id": "st_silence", "name": "Silence", "kind": "Ailment", "effect": "Prevents casting Magic Materia (Curaga, Wall, Ultima). Command Materia still works.", "counter": "Cure with Esuna or Remedy; prevent with White Cape, Mystile, Pearl Necklace, or Status Ward.", "itemIds": ["item_white_cape", "item_esuna", "item_status_ward"]},
        {"id": "st_stun", "name": "Stun", "kind": "Ailment", "effect": "Freezes Zack completely until the duration expires or he is struck.", "counter": "Prevent with Headband, Chocobo Armlets, Ribbon, Super Ribbon, or Status Ward + Hell-aga.", "itemIds": ["item_headband", "item_super_ribbon", "item_status_ward"]},
        {"id": "st_stop", "name": "Stop", "kind": "Ailment", "effect": "Halts all movement, actions, and DMW reels—extremely lethal on Hard Mode.", "counter": "Prevent with Sprint Shoes, Ribbon, Super Ribbon, or Status Ward + Hell-aga (e.g., Hell Blizzaga).", "itemIds": ["item_sprint_shoes", "item_hell_blizzaga", "item_status_ward"]},
        {"id": "st_death", "name": "Instant Death", "kind": "Ailment", "effect": "Kills Zack immediately regardless of HP/VIT/SPR (unless Auto-Raise is active).", "counter": "Note: Standard Ribbon does NOT block Death! Use Safety Bit, Super Ribbon, Genji Shield, or Status Ward + Hell-aga.", "itemIds": ["item_safety_bit", "item_super_ribbon", "item_genji_shield"]},
        {"id": "st_curse", "name": "Curse", "kind": "Ailment", "effect": "Stops the DMW reels completely (no Limit Breaks, no Materia level-ups, no DMW EXP level-ups).", "counter": "Inherent to Cursed Ring & Heike Soul. Cure with Remedy/Esuna or prevent with Gris-Gris Bag / Super Ribbon.", "itemIds": ["item_gris_gris_bag", "item_cursed_ring", "item_heike_soul"]},
        {"id": "st_barrier", "name": "Barrier", "kind": "Buff", "effect": "Halves incoming physical damage. Stacks multiplicatively with 255 VIT.", "counter": "Apply via Barrier, Wall, Moon Bracer, Protect Ring, or Genji Shield.", "itemIds": ["item_wall", "item_protect_ring", "item_genji_shield"]},
        {"id": "st_mbarrier", "name": "MBarrier", "kind": "Buff", "effect": "Halves incoming magical damage. Essential for Minerva's Crimson Flare/Krysta/Ultima.", "counter": "Apply via MBarrier, Wall, Shining Bracer, Protect Ring, or Genji Shield.", "itemIds": ["item_wall", "item_protect_ring", "item_genji_shield"]},
        {"id": "st_regen", "name": "Regen", "kind": "Buff", "effect": "Continuously restores HP over time—powers AFK M1-1-1 DMW farming.", "counter": "Apply via Regen Materia, Faerie Ring, or Genji Armor.", "itemIds": ["item_regen", "item_faerie_ring", "item_genji_armor"]},
        {"id": "st_endure", "name": "Endure", "kind": "Buff", "effect": "Prevents Zack from flinching or getting interrupted during animations.", "counter": "Granted by Twisted Headband or Genji Armor.", "itemIds": ["item_twisted_headband", "item_genji_armor"]},
        {"id": "st_raise", "name": "Auto-Raise (Reraise)", "kind": "Buff", "effect": "Automatically revives Zack with full HP once upon KO. Dispelled by Minerva's Judgment Arrow!", "counter": "Use Phoenix Down in battle or trigger Phoenix (Rebirth Flame) DMW.", "itemIds": ["item_phoenix_down", "item_rebirth_flame"]},
        {"id": "st_null_phys_mag", "name": "Null Physical / Null Magic", "kind": "Enemy Flag", "effect": "Certain enemies (Movers, Magic Pots, Elementals) completely negate Physical or Magic hits.", "counter": "Swap to Costly Punch/Magic vs Null Physical, or physical Command Materia vs Null Magic.", "itemIds": ["item_costly_punch", "item_electrocute"]},
        {"id": "st_zero_mp_ap", "name": "Zero MP / AP Cost", "kind": "Buff", "effect": "Reduces all spell MP or skill AP costs to 0.", "counter": "Granted by Genji Helm (both), Soul of Thamasa (MP), Laurel Crown (AP), or DMW Modulating Phase.", "itemIds": ["item_genji_helm", "item_soul_of_thamasa", "item_laurel_crown"]},
        {"id": "st_critical", "name": "Always Critical", "kind": "Buff", "effect": "Forces every physical hit/skill to deal critical 2x damage.", "counter": "Granted by Genji Glove, Sniper Eye, or attacking directly behind an enemy's back.", "itemIds": ["item_genji_glove", "item_sniper_eye"]},
    ]

    reunion_vs_psp = [
        {"feature": "Boss Skill Power Gauge", "psp": "Not present (boss ultimate moves always dealt full damage).", "reunion": "Added to every boss! Depleting the purple bar reduces ultimate damage by 25%/50%/75% or completely cancels it at 0%."},
        {"feature": "Buster Sword Battle Stance & Proficiency", "psp": "Basic guard & combo only; no stance proficiency.", "reunion": "New Battle Stance (Guard + Attack): builds 0–100% Proficiency, unlocking Break Damage Limit at 23% and Barrier Pierce at 47%."},
        {"feature": "Minerva Hard Mode HP", "psp": "10,000,000 HP (Normal) / 20,000,000 HP (Hard) — PSP Hard Minerva had 20M.", "reunion": "10,000,000 HP (Normal) / 20,000,000 HP (Hard) with 255 stats and Skill Power Judgment Arrow."},
        {"feature": "Mission Clear Rewards", "psp": "Repeatable mission clear rewards on certain missions.", "reunion": "Mission Clear Rewards are awarded ONCE ONLY! Use M6-6-3 Dark Matter + 98/980% Libra conversion instead."},
        {"feature": "DMW Limit Verge", "psp": "Limit Breaks triggered immediately when rolled, interrupting combat.", "reunion": "Limit Breaks & Summons are STORED in a Limit Verge slot so you can trigger them on demand (e.g., to break Skill Power gauges!)."},
        {"feature": "DMW Cutscenes & Modulating Phase", "psp": "Forced full-length summon & flashback animations.", "reunion": "Skippable animations (skipping still counts toward 100% DMW!) and faster combat flow."},
        {"feature": "X-Potion & Healing Caps", "psp": "X-Potion healed ~2,500 HP, making it useless at 99,999 HP.", "reunion": "X-Potion heals up to 99,999 HP in Reunion, making it viable against Minerva alongside Curaga."},
        {"feature": "Instant-Cast & Shortcuts", "psp": "L/R scrolling menu only.", "reunion": "L1+Face Button instant shortcuts for all 6 equipped Materia + full 360° camera control."},
    ]

    ng_plus_carryover = [
        {"item": "Zack's Level, EXP, HP/MP/AP/Stats, Gil, SP", "carriesOver": True, "note": "All character stats and currencies carry over untouched."},
        {"item": "Equipped & Inventory Materia (including +999%/+100 stats & Mastered levels)", "carriesOver": True, "note": "All Materia and fusion bonuses carry over."},
        {"item": "Accessories & Consumables / Fusion Catalysts", "carriesOver": True, "note": "Genji Gear, Divine Slayer, Heike Soul, Adaman Bangle, Dark Matter, etc. carry over."},
        {"item": "Buster Sword Proficiency %", "carriesOver": True, "note": "Carries over once Buster Sword is inherited in Ch. 1/2."},
        {"item": "DMW Completion % & Unlocked Portraits", "carriesOver": True, "note": "Wait: DMW images re-lock visually until story points, OR keep %? In Reunion, DMW % carries over! Still grab Phoenix in Ch. 8 if missed."},
        {"item": "Key Items (Item Fusion Tome, Keychain, Backpack, Shops)", "carriesOver": False, "note": "RESET! You must re-clear M7-2-1, M7-2-2, M7-2-5 and re-unlock all 16 shops."},
        {"item": "300 Mission Completion Progress", "carriesOver": False, "note": "RESET to 0/300! Finish all 300 missions in ONE playthrough if going for Heike Soul / 100%."},
        {"item": "Mail Inbox & Fan Club Memberships", "carriesOver": False, "note": "RESET! Must re-join all 5 Fan Clubs and re-collect all 20 mail senders in one run for Mail Completionist."},
    ]

    return {
        "storyChapters": story_chapters,
        "trophies": trophies,
        "mailSenders": mail_senders,
        "minigames": minigames,
        "magicPotEncounters": magic_pot_encounters,
        "mechanics": {
            "zackBaseStats": _build_zack_base_stats(),
            "dmwMechanics": {
                "hiddenExpRule": "Zack has a hidden EXP counter alongside DMW reels. Crossing the level EXP threshold enables level-ups ONLY when the DMW rolls 7-7-7. Excess EXP banks cleanly across missions (as long as you clear, not abandon!).",
                "emotionalPhases": [
                    {"state": "Normal (Lv. 1)", "multiplier": "1.0x", "notes": "Baseline reel speed and Modulating Phase frequency."},
                    {"state": "High (Lv. 2)", "multiplier": "1.5x", "notes": "Boosted by story events, DMW character matches, or Limit Breaks."},
                    {"state": "Sky High (Lv. 3)", "multiplier": "2.0x", "notes": "Frequent double/triple number Materia level-ups."},
                    {"state": "Heavenly (Lv. 4)", "multiplier": "4.0x+", "notes": "Highest chance of 7-7-7 Level Up, Limit Breaks, and Summons (triggered often after Cissnei Lucky Stars!)."},
                ],
                "limitVerge": "In Reunion, Limit Breaks & Summons store into a Limit Verge button instead of auto-firing. Hold a stored Limit Verge (like Octaslash or Costly Punch combos) to shatter boss Skill Power bars immediately.",
                "curseWarning": "Curse status (from Cursed Ring, Heike Soul, or enemy hits) freezes DMW reels completely—remove Heike Soul / Cursed Ring when AFK mastering Materia or farming 100% DMW in M1-1-1!",
            },
            "reunionCombat": {
                "skillPowerGauge": [
                    {"threshold": "100% – 76%", "reduction": "0% (Full Ultimate Damage)", "note": "Dangerous on Hard Mode; Minerva's Judgment Arrow can wipe without Auto-Raise."},
                    {"threshold": "75% – 51%", "reduction": "-25% Ultimate Damage", "note": "Moderate mitigation; keep Wall active."},
                    {"threshold": "50% – 26%", "reduction": "-50% Ultimate Damage", "note": "Survivable with 255 VIT/SPR + Wall."},
                    {"threshold": "25% – 1%", "reduction": "-75% Ultimate Damage", "note": "Minimal chip damage."},
                    {"threshold": "0% (Broken!)", "reduction": "100% Cancelled + Boss Staggered", "note": "Cancels the ultimate completely and opens a huge free damage window!"},
                ],
                "battleStance": [
                    {"perk": "Enter Battle Stance (Guard + Attack)", "unlock": "Inherited in Ch. 1/2", "effect": "Reduces incoming damage dramatically while charging Strong Attack or Command Materia (+50% to +100% damage boost)."},
                    {"perk": "Damage Limit Break (99,999)", "unlock": "23% Proficiency", "effect": "All Battle Stance attacks and Command Materia cast from Battle Stance break the 9,999 damage cap without Brutal/Genji Glove!"},
                    {"perk": "Barrier Piercing", "unlock": "47% Proficiency", "effect": "Attacks & skills from Battle Stance ignore and shatter enemy Barrier / MBarrier."},
                    {"perk": "Necromose / Stance Drain", "unlock": "100% Proficiency", "effect": "Every Battle Stance kill restores HP/MP/AP and maximizes Strong Attack damage multiplier."},
                ],
            },
            "statusEffects": status_effects,
            "reunionVsPsp": reunion_vs_psp,
            "ngPlusCarryover": ng_plus_carryover,
        },
    }
