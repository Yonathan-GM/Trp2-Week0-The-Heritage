"""Make the child, the mother and the playing kids look Ethiopian, with warm deep brown skin.
Run from the Heritage folder, AFTER patch_story_v2.py:   python patch_child_look.py

Only the character descriptions change, so only shots s10 and s11 are affected (their
keyframes regenerate; all other cached pictures stay). Keeps storyboard.json.bak3.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

PATH = Path("storyboard.json")

NEW = {
    "child": ("a small Ethiopian child of about eight with warm deep brown skin and short black curly hair, "
              "in a simple cotton tunic, seen from behind or the side, stylised illustration"),
    "mother": ("a gentle Ethiopian woman in her forties with warm deep brown skin, dark hair under a light "
               "scarf, wearing a white cotton shawl with a dark brown woven border over a simple dress, "
               "seen from the side, stylised illustration"),
    "kids": ("three small Ethiopian children with warm deep brown skin and short black hair, playing, seen "
             "from behind or from the side as small stylised figures in simple bright cotton clothes, "
             "stylised illustration"),
}


def main():
    if not PATH.exists():
        raise SystemExit("Run this from the Heritage folder (storyboard.json not found).")
    sb = json.loads(PATH.read_text(encoding="utf-8"))
    chars = {c["id"]: c for c in sb["characters"]}
    missing = [k for k in NEW if k not in chars]
    if missing:
        raise SystemExit(f"Characters {missing} not found. Run python patch_story_v2.py first.")
    if all(chars[k]["description"] == v for k, v in NEW.items()):
        raise SystemExit("Already patched. Nothing to do.")
    shutil.copy(PATH, PATH.with_suffix(".json.bak3"))
    for k, v in NEW.items():
        chars[k]["description"] = v
    PATH.write_text(json.dumps(sb, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("Patched child, mother and kids (backup: storyboard.json.bak3). Validating...")
    sys.exit(subprocess.run([sys.executable, "pipeline/validate.py"]).returncode)


if __name__ == "__main__":
    main()