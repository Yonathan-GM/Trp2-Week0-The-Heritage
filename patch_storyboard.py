"""One-time edit of storyboard.json after reviewing the first keyframes. Run from the Heritage folder:

    python patch_storyboard.py

- grandmother description: names the shawl border colour so she looks the same in every shot
- s02, s05, s06: ask for bare soil with no sprout (FLUX drew a green plant in s06)
- s05 reason: says 9 seconds, matching duration_s

It checks every target exists, keeps storyboard.json.bak, and re-validates the file.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

PATH = Path("storyboard.json")

GRANDMOTHER = ("an elderly Ethiopian grandmother, small and slight, silver-grey hair under a thin scarf, "
               "wearing a white cotton shawl with a dark brown woven border and fringe over a simple "
               "pale dress, stylised illustration")
S02 = ("Close view of weathered hands pressing a seed into bare red-brown soil beside a stone wall, "
       "no plant or sprout visible, white shawl sleeve visible")
S06 = ("Medium close view of the elderly grandmother, thin and tired, kneeling and pressing one tiny seed "
       "into bare brown soil with her fingertips, no plant and no sprout anywhere, only bare earth, "
       "golden evening light, face turned downward")


def main():
    if not PATH.exists():
        raise SystemExit("Run this from the Heritage folder (storyboard.json not found).")
    sb = json.loads(PATH.read_text(encoding="utf-8"))
    shots = {s["id"]: s for s in sb["shots"]}
    chars = {c["id"]: c for c in sb["characters"]}
    for need in ("s02", "s05", "s06"):
        if need not in shots:
            raise SystemExit(f"Shot {need} not found.")
    if "grandmother" not in chars:
        raise SystemExit("Character 'grandmother' not found.")
    if chars["grandmother"]["description"] == GRANDMOTHER:
        raise SystemExit("Already patched. Nothing to do.")
    old5 = "kneeling to plant a seed"
    if shots["s05"]["image_prompt"].count(old5) != 1:
        raise SystemExit("s05 image_prompt differs from what I expected; send it to me.")

    shutil.copy(PATH, PATH.with_suffix(".json.bak"))
    chars["grandmother"]["description"] = GRANDMOTHER
    shots["s02"]["image_prompt"] = S02
    shots["s06"]["image_prompt"] = S06
    shots["s05"]["image_prompt"] = shots["s05"]["image_prompt"].replace(
        old5, "kneeling to press a seed into bare soil, no sprout visible")
    shots["s05"]["reason"] = shots["s05"]["reason"].replace("Held for 8 seconds", "Held for 9 seconds")
    PATH.write_text(json.dumps(sb, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("Patched storyboard.json (backup: storyboard.json.bak). Validating...")
    sys.exit(subprocess.run([sys.executable, "pipeline/validate.py"]).returncode)


if __name__ == "__main__":
    main()