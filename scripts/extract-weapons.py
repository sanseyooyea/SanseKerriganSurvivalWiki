"""Extract weapon stats (damage, attack period) from hero XML files."""
import mpyq
import re
import json

map_path = r"D:\starcraft2\凯瑞甘生存2 最新版.SC2Map"
archive = mpyq.MPQArchive(map_path)

flist = archive.read_file("(listfile)").decode("utf-8", errors="replace").split("\r\n")
hero_xmls = [f for f in flist if "Heroes" in f and f.endswith(".xml")
             and "InDevelopment" not in f]

results = {}

for path in hero_xmls:
    data = archive.read_file(path)
    if not data:
        continue
    content = data.decode("utf-8", errors="replace")
    name = path.split("H-")[1].replace(".xml", "")

    # Find CWeaponLegacy definitions
    weapons = re.findall(
        r'<CWeaponLegacy id="([^"]+)">(.*?)</CWeaponLegacy>',
        content, re.DOTALL
    )

    # Find CEffectDamage for weapon damage amounts
    damages = {}
    for m in re.finditer(r'<CEffectDamage id="([^"]+)">(.*?)</CEffectDamage>', content, re.DOTALL):
        dmg_id = m.group(1)
        amount = re.search(r'<Amount value="([^"]+)"', m.group(2))
        if amount:
            damages[dmg_id] = float(amount.group(1))

    hero_weapons = []
    for wep_id, wep_body in weapons:
        period = re.search(r'<Period value="([^"]+)"', wep_body)
        display_effect = re.search(r'<DisplayEffect value="([^"]+)"', wep_body)
        attack_count = re.search(r'<DisplayAttackCount value="([^"]+)"', wep_body)
        range_val = re.search(r'<Range value="([^"]+)"', wep_body)

        dmg = 0
        if display_effect and display_effect.group(1) in damages:
            dmg = damages[display_effect.group(1)]

        hero_weapons.append({
            "id": wep_id,
            "damage": dmg,
            "period": float(period.group(1)) if period else 1.0,
            "attackCount": int(attack_count.group(1)) if attack_count else 1,
            "range": float(range_val.group(1)) if range_val else 0,
        })

    if hero_weapons:
        # Use the first/primary weapon
        primary = hero_weapons[0]
        results[name] = {
            "damage": primary["damage"],
            "period": primary["period"],
            "attackCount": primary["attackCount"],
            "range": primary["range"],
            "dps": round(primary["damage"] * primary["attackCount"] / primary["period"], 1) if primary["period"] > 0 else 0,
        }

# Print results
for name, stats in sorted(results.items()):
    print(f"{name}: dmg={stats['damage']} x{stats['attackCount']}, period={stats['period']}s, range={stats['range']}, dps={stats['dps']}")

# Save to file
with open("data/weapon_stats.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(results)} heroes to data/weapon_stats.json")
