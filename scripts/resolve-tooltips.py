"""Resolve SC2 tooltip <d ref="..."/> placeholders using XML catalog data."""
import mpyq
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

map_path = r"D:\starcraft2\凯瑞甘生存2 最新版.SC2Map"
archive = mpyq.MPQArchive(map_path)

# Build comprehensive field catalog from all XML files
# Key format: "CatalogType/EntryId/FieldPath" -> value
fields = {}

flist = archive.read_file("(listfile)").decode("utf-8", errors="replace").split("\r\n")
xml_files = [f for f in flist if f.endswith(".xml") and "GameData" in f]

def index_element(catalog_type, entry_id, elem, prefix=""):
    """Recursively index all fields in an XML element."""
    # Index attributes
    for attr, val in elem.attrib.items():
        if attr == "id":
            continue
        path = f"{prefix}{attr}" if not prefix else f"{prefix}.{attr}"
        key = f"{catalog_type}/{entry_id}/{path}"
        fields[key] = val

    # Index child elements
    child_counts = {}
    for child in elem:
        tag = child.tag
        child_counts[tag] = child_counts.get(tag, 0)

        idx = child_counts[tag]
        index_attr = child.get("index", "")

        if prefix:
            base = f"{prefix}.{tag}"
        else:
            base = tag

        # Store with array index
        indexed_base = f"{base}[{idx}]"
        if index_attr:
            indexed_base_named = f"{base}[{index_attr}]"
        else:
            indexed_base_named = None

        # If element has 'value' attribute, store it
        val = child.get("value")
        if val is not None:
            fields[f"{catalog_type}/{entry_id}/{base}"] = val
            fields[f"{catalog_type}/{entry_id}/{indexed_base}"] = val
            if indexed_base_named:
                fields[f"{catalog_type}/{entry_id}/{indexed_base_named}"] = val

        # Also store all other attributes
        for attr, aval in child.attrib.items():
            if attr in ("id", "value", "index"):
                continue
            fields[f"{catalog_type}/{entry_id}/{base}.{attr}"] = aval
            fields[f"{catalog_type}/{entry_id}/{indexed_base}.{attr}"] = aval
            if indexed_base_named:
                fields[f"{catalog_type}/{entry_id}/{indexed_base_named}.{attr}"] = aval

        # Recurse into children
        index_element(catalog_type, entry_id, child, base)
        if indexed_base != base:
            index_element(catalog_type, entry_id, child, indexed_base)
        if indexed_base_named and indexed_base_named != base:
            index_element(catalog_type, entry_id, child, indexed_base_named)

        child_counts[tag] += 1


# Map SC2 catalog type names to XML tag prefixes
TYPE_MAP = {
    "Abil": "CAbil",
    "Behavior": "CBehavior",
    "Effect": "CEffect",
    "Unit": "CUnit",
    "Weapon": "CWeapon",
    "Upgrade": "CUpgrade",
    "Validator": "CValidator",
}

print("Parsing XML files...")
for xf in xml_files:
    raw = archive.read_file(xf)
    if not raw or len(raw) < 100:
        continue
    try:
        text = raw.decode("utf-8", errors="replace")
        # Wrap in root if needed
        if not text.strip().startswith("<?xml"):
            text = '<?xml version="1.0"?><Root>' + text + '</Root>'
        root = ET.fromstring(text)
    except ET.ParseError:
        # Try fixing common issues
        try:
            text = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;)', '&amp;', text)
            root = ET.fromstring(text)
        except:
            continue

    for elem in root.iter():
        entry_id = elem.get("id")
        if not entry_id:
            continue
        tag = elem.tag
        # Determine catalog type
        cat_type = None
        for sc2_type, prefix in TYPE_MAP.items():
            if tag.startswith(prefix):
                cat_type = sc2_type
                break
        if not cat_type:
            # Use tag without C prefix as type
            cat_type = tag[1:] if tag.startswith("C") else tag

        index_element(cat_type, entry_id, elem)

print(f"Indexed {len(fields)} field values")

# Now resolve d refs
# A reference is `CatType,Id,Field`. Expressions wrap refs in arithmetic, e.g.
#   (Behavior,X,Modification.MoveSpeedMultiplier-1)*100   (ref first, then -1)
#   Effect,X,PeriodCount / 2                              (ref then division)
#   Abil,X,Cost[0].Cooldown.TimeUse                       (bare ref)
# General approach: substitute every resolvable ref with its numeric value,
# then safely evaluate the remaining pure-arithmetic string.
REF_RE = re.compile(
    r'(Abil|Behavior|Effect|Unit|Weapon|Upgrade|Validator|CUnit|CWeapon),'
    r'(\w+),'
    r'([A-Za-z_]\w*(?:\.\w+|\[[^\]]+\])*)'
)
SAFE_EXPR_RE = re.compile(r'^[\d.\s+\-*/()]+$')


def resolve_ref(ref_str):
    """Resolve a d ref expression to a formatted number string, or None."""
    ref_str = ref_str.strip()

    # Skip runtime expressions with $ (e.g. $BehaviorStackCount:...$)
    if "$" in ref_str:
        return None

    # Substitute each Catalog,Id,Field reference with its numeric value.
    failed = [False]

    def sub(m):
        val = resolve_simple_ref(f"{m.group(1)},{m.group(2)},{m.group(3)}")
        if val is None:
            failed[0] = True
            return "0"
        try:
            return repr(float(val))
        except (TypeError, ValueError):
            failed[0] = True
            return "0"

    expr = REF_RE.sub(sub, ref_str)
    if failed[0]:
        return None

    # Bare number (no surrounding math) — return as-is via format.
    expr = expr.strip()
    if not SAFE_EXPR_RE.match(expr):
        return None
    try:
        result = eval(expr, {"__builtins__": {}}, {})  # safe: validated chars only
        return format_num(float(result))
    except (ZeroDivisionError, SyntaxError, ValueError, TypeError):
        return None


def resolve_simple_ref(ref_str):
    """Resolve a simple Catalog,Id,Field reference."""
    parts = ref_str.split(",", 2)
    if len(parts) < 3:
        return None
    cat_type = parts[0].strip()
    entry_id = parts[1].strip()
    field_path = parts[2].strip()

    key = f"{cat_type}/{entry_id}/{field_path}"
    if key in fields:
        return fields[key]

    # Try without array index for first element
    alt_key = re.sub(r'\[0\]', '', key)
    if alt_key in fields:
        return fields[alt_key]

    # Try fuzzy: field might be stored with different nesting
    prefix = f"{cat_type}/{entry_id}/"
    for k, v in fields.items():
        if k.startswith(prefix) and field_path in k:
            return v

    return None


def format_num(n):
    if n == int(n):
        return str(int(n))
    return f"{n:.2f}".rstrip("0").rstrip(".")


# Load abilities and Button/Tooltips
data_gs = archive.read_file(r"zhCN.SC2Data\LocalizedData\GameStrings.txt")
gs_content = data_gs.decode("utf-8", errors="replace")

button_tooltips = {}
for line in gs_content.split("\n"):
    if "=" not in line:
        continue
    key, _, val = line.partition("=")
    if key.strip().startswith("Button/Tooltip/") and val.strip():
        button_tooltips[key.strip()[15:]] = val.strip()

with open("data/abilities.json", "r", encoding="utf-8") as f:
    abilities = json.load(f)

# Resolve all d refs in tooltips
resolved_count = 0
unresolved_count = 0

def replace_drefs(tooltip):
    global resolved_count, unresolved_count
    def replacer(m):
        global resolved_count, unresolved_count
        ref = m.group(1)
        val = resolve_ref(ref)
        if val is not None:
            resolved_count += 1
            return val
        else:
            unresolved_count += 1
            return ""  # Remove unresolvable refs
    return re.sub(r'<d ref="([^"]+)"[^/]*/>', replacer, tooltip)

# Process abilities
for aid, abil in abilities.items():
    btn_tip = button_tooltips.get(aid)
    if btn_tip and "<d ref" in btn_tip:
        abil["tooltip"] = replace_drefs(btn_tip)
    elif btn_tip and not abil.get("tooltip"):
        abil["tooltip"] = btn_tip

# 策展 face 覆盖(见 data/seed/ability-face.seed.json)：显示身份取指令卡按钮面，
# tooltip 也必须从该 face 的原始 Button/Tooltip 解析 <d ref>，否则 build_abilities
# 产出的 [?] 占位不会被替换。上面的主循环按 ability id 取 tooltip，取不到 face 的。
face_seed_path = Path("data/seed/ability-face.seed.json")
if face_seed_path.exists():
    face_seed = json.loads(face_seed_path.read_text(encoding="utf-8"))

    def tip_from_face(face_id, fallback):
        """从按钮面的原始 tooltip 解析 <d ref>；face 无 tooltip 则回退。"""
        raw = button_tooltips.get(face_id)
        if raw and "<d ref" in raw:
            return replace_drefs(raw)
        return raw or fallback

    for aid, face_id in face_seed.get("global", {}).items():
        if aid.startswith("_") or aid not in abilities:
            continue
        abilities[aid]["tooltip"] = tip_from_face(face_id, abilities[aid].get("tooltip", ""))

    for aid, heroes in face_seed.get("perHero", {}).items():
        if aid.startswith("_") or aid not in abilities:
            continue
        per = abilities[aid].get("perHero") or {}
        for hero, face_id in heroes.items():
            if hero.startswith("_") or hero not in per:
                continue
            per[hero]["tooltip"] = tip_from_face(face_id, per[hero].get("tooltip", ""))

print(f"Resolved: {resolved_count}, Unresolved: {unresolved_count}")

# Clean up empty remnants
def clean_remnants(tip):
    if not tip:
        return tip
    # Clean empty color spans
    tip = re.sub(r'<c val="[^"]*">\s*</c>', '', tip)
    # Clean lines that became empty after ref removal
    lines = tip.split("<n/>")
    cleaned = []
    for line in lines:
        plain = re.sub(r'<[^>]*>', '', line).strip()
        if not plain:
            continue
        # Remove lines that are just ":" or "：" with no content
        if re.match(r'^[^:：]*[：:]\s*$', plain):
            continue
        cleaned.append(line)
    return "<n/>".join(cleaned)


for aid, abil in abilities.items():
    abil["tooltip"] = clean_remnants(abil.get("tooltip", ""))
    for o in (abil.get("perHero") or {}).values():
        if isinstance(o, dict) and "tooltip" in o:
            o["tooltip"] = clean_remnants(o.get("tooltip", ""))

with open("data/abilities.json", "w", encoding="utf-8") as f:
    json.dump(abilities, f, indent=2, ensure_ascii=False)

# Show results
print("\nSample results:")
for aid in ["KerriganRazorSwarm", "KerriganFungalGrowth", "KerriganPrimalRoar", "AewynBless"]:
    tip = abilities[aid].get("tooltip", "")
    plain = re.sub(r'<[^>]*>', '', tip).replace("<n/>", " | ")
    print(f"  {aid}: {plain[:150]}")
