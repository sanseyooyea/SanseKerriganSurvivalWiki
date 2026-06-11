"""
Post-process wiki ability data. Runs AFTER sync-data.py as the final pipeline
step (BankEditor has no notion of button faces or ability classes, so this is
wiki-only and must be re-applied after every sync).

1. Translate untranslated ability names (ASCII nameZh) via the ability's button
   face: Abil.CmdButtonArray.DefaultButtonFace -> Button/Name/<face> (Chinese).
2. Filter non-combat menu buttons from each hero's ability list in roles.json:
   - all CAbilLearn (skill-point learn buttons)
   - CAbilBuild/Train/Research/WarpTrain/MorphPlacement whose name is generic
     ("Build"/"Train"/"建造建筑"/...) or equals the id. Keeps real abilities that
     share those classes (NovaTeleport, AscendantSummonVoidRift, KraithKingofPygalisk).
"""
import json, re
import mpyq

WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'
ROLES = WIKI + r'\data\roles.json'
ABILITIES = WIKI + r'\data\abilities.json'
CATALOG = WIKI + r'\data\catalog.json'
MAP_PATH = r'D:\starcraft2\凯瑞甘生存2 最新版.SC2Map'

GENERIC_NAMES = {
    'Build', 'Train', 'Research', 'Warp Train', 'Learn', 'Ability Learn',
    '建造建筑', '折跃建筑', '建造', '训练', '研究', '折跃单位', '训练单位',
}
MENU_CLASSES = {'CAbilBuild', 'CAbilTrain', 'CAbilResearch',
                'CAbilWarpTrain', 'CAbilMorphPlacement'}

archive = mpyq.MPQArchive(MAP_PATH)
gs = archive.read_file(
    r'zhCN.SC2Data\LocalizedData\GameStrings.txt').decode('utf-8-sig', 'replace')
button_name = {}
for line in gs.split('\n'):
    if line.startswith('Button/Name/'):
        k, _, v = line.partition('=')
        button_name[k[len('Button/Name/'):].strip()] = v.strip()

# Ability class per id, parsed from GameData XML (catalog.json flattens all
# CAbil* subclasses into one 'Abil' type, losing the class tag).
flist = archive.read_file('(listfile)').decode('utf-8', 'replace').split('\r\n')
abil_class = {}
tag_re = re.compile(r'<(CAbil\w+)\s+[^>]*id="([^"]+)"')
for f in flist:
    if not (f.endswith('.xml') and 'GameData' in f):
        continue
    d = archive.read_file(f)
    if not d:
        continue
    for tag, aid in tag_re.findall(d.decode('utf-8', 'replace').lstrip('﻿')):
        abil_class[aid] = tag

ABIL = json.load(open(CATALOG, encoding='utf-8')).get('Abil', {})


def is_ascii(s):
    return all(ord(c) < 128 for c in s)


def is_menu_button(aid):
    """True if the ability is a non-combat menu container (learn/build/train)."""
    c = abil_class.get(aid)
    if c == 'CAbilLearn':
        return True
    if c in MENU_CLASSES:
        nz = abilities.get(aid, {}).get('nameZh', '').strip()
        return nz in GENERIC_NAMES or nz == aid or 'Ability Learn' in nz
    return False


# --- Fix 1: translate untranslated names via button face ---
abilities = json.load(open(ABILITIES, encoding='utf-8'))
translated = 0
for aid, e in abilities.items():
    nz = e.get('nameZh', '')
    if nz and not is_ascii(nz):
        continue
    face = ABIL.get(aid, {}).get('CmdButtonArray.DefaultButtonFace')
    if face and face in button_name and not is_ascii(button_name[face]):
        e['nameZh'] = button_name[face]
        translated += 1

with open(ABILITIES, 'w', encoding='utf-8') as f:
    json.dump(abilities, f, ensure_ascii=False, indent=2)

# --- Fix 2: filter menu buttons from each hero's ability list ---
roles = json.load(open(ROLES, encoding='utf-8'))
removed = []
for r in roles:
    abil = r.get('abilities', [])
    kept = [a for a in abil if not is_menu_button(a)]
    for a in abil:
        if a not in kept:
            removed.append(f"{r['nameEn']}/{a}")
    r['abilities'] = kept

with open(ROLES, 'w', encoding='utf-8') as f:
    json.dump(roles, f, ensure_ascii=False, indent=2)

print(f'Translated {translated} ability names via button face')
print(f'Filtered {len(removed)} menu buttons from hero ability lists')
for x in removed:
    print(f'  REMOVED {x}')
