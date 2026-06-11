"""Sync data from BankEditor project to Wiki project."""
import shutil
import json
from pathlib import Path

BANK_EDITOR = Path(r"D:\starcraft2\SanseKerriganSurvivalBankEditor")
WIKI = Path(r"D:\starcraft2\SanseKerriganSurvivalWiki")

def sync():
    data_dir = WIKI / "data"
    icons_dir = WIKI / "public" / "icons"
    data_dir.mkdir(parents=True, exist_ok=True)
    icons_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(BANK_EDITOR / "role_data_extracted.json", data_dir / "roles.json")
    shutil.copy2(BANK_EDITOR / "ability_data.json", data_dir / "abilities.json")
    shutil.copy2(BANK_EDITOR / "veterancy_data.json", data_dir / "veterancy.json")

    src_icons = BANK_EDITOR / "src" / "main" / "resources" / "icons"
    for png in src_icons.glob("*.png"):
        shutil.copy2(png, icons_dir / png.name)

    with open(data_dir / "roles.json", "r", encoding="utf-8") as f:
        roles = json.load(f)
    print(f"Synced: {len(roles)} roles")

    with open(data_dir / "abilities.json", "r", encoding="utf-8") as f:
        abilities = json.load(f)
    print(f"Synced: {len(abilities)} abilities")

    icons_count = len(list(icons_dir.glob("*.png")))
    print(f"Synced: {icons_count} icons")

if __name__ == "__main__":
    sync()
    print("Done!")
