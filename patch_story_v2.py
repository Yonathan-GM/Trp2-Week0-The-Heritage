"""Story revision 2. Run once from the Heritage folder:  python patch_story_v2.py

Keeps s01-s08 exactly as they are. Changes only the ending:
  s09  the great warka tree (same picture as before, now 8 s, only the first sentence)
  s10  NEW: the grandchildren playing in the shade (6 s; the old second sentence of s09)
  s11  NEW: the child asks Mother who planted it; she smiles and a small memory cloud above her
       head shows Grandmother planting (10 s). Replaces the old s10.
Adds characters kids, mother, child; updates the music cues and the target duration.
Expected length: about 87 s including the 3 s end card (limit 90).

It keeps storyboard.json.bak2, then runs the validator.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

PATH = Path("storyboard.json")

NEW_CHARACTERS = [
    {"id": "kids", "consent": "fictional_or_stylised",
     "description": "three small children playing, seen from behind or from the side as small stylised "
                    "figures in simple bright cotton clothes, stylised illustration"},
    {"id": "mother", "consent": "fictional_or_stylised",
     "description": "a gentle woman in her forties, dark hair under a light scarf, wearing a white cotton "
                    "shawl with a dark brown woven border over a simple dress, seen from the side, "
                    "stylised illustration"},
    {"id": "child", "consent": "fictional_or_stylised",
     "description": "a small child of about eight in a simple cotton tunic, seen from behind or the side, "
                    "stylised illustration"},
]

S10 = {
    "id": "s10",
    "reason": "Joy before the close: the grandchildren playing under the tree she planted, so the "
              "audience feels what the waiting bought.",
    "shot_size": "medium",
    "duration_s": 6,
    "characters": ["kids"],
    "image_prompt": "Medium shot of several small children laughing and playing tag in the dappled shade "
                    "under a huge spreading warka fig tree, thick roots and trunk beside them, golden "
                    "evening light, joyful movement",
    "motion_prompt": "Camera holds steady, the children run and laugh, leaves and dappled light move gently.",
    "fallback": "ken_burns",
    "narration": "እኛ የልጅ ልጆቿ በጥላው ሥር እንጫወታለን።",
    "subtitle_en": "We, her grandchildren, play in its shade.",
}

S11 = {
    "id": "s11",
    "reason": "Closes the loop: the story passes from her to my mother to me. The memory cloud shows "
              "Grandmother planting, so the film ends on her, not on us.",
    "shot_size": "medium",
    "duration_s": 10,
    "characters": ["mother", "child"],
    "image_prompt": "Medium shot in the shade of a huge warka tree: a small child looks up at his mother, "
                    "who sits smiling and gazing upward; above the mother's head floats a small soft "
                    "watercolour memory cloud containing a tiny painted scene of an elderly grandmother "
                    "in a white shawl kneeling to plant a seed beside a stone wall; thick tree trunk "
                    "behind them, warm evening light",
    "motion_prompt": "Camera holds steady, the memory cloud glows softly and drifts slightly, the mother's "
                     "scarf moves in the breeze.",
    "fallback": "ken_burns",
    "narration": "ማን እንደተከለው እናቴን ጠየቅኳት። ፈገግ አለችና፣ ስለ አያቴ፣ ሃያ ዓመት ስለጠበቀው ዘር ነገረችኝ።",
    "subtitle_en": "I asked my mother who planted it. She smiled and told me about my grandmother, "
                   "and the seed that waited twenty years.",
}


def main():
    if not PATH.exists():
        raise SystemExit("Run this from the Heritage folder (storyboard.json not found).")
    sb = json.loads(PATH.read_text(encoding="utf-8"))
    shots = {s["id"]: s for s in sb["shots"]}
    if "s11" in shots:
        raise SystemExit("Already patched (s11 exists). Nothing to do.")
    for need in ("s09", "s10"):
        if need not in shots:
            raise SystemExit(f"Shot {need} not found; send me your storyboard.json.")
    existing = {c["id"] for c in sb["characters"]}
    if existing & {"kids", "mother", "child"}:
        raise SystemExit("A character called kids/mother/child already exists; send me your storyboard.json.")

    shutil.copy(PATH, PATH.with_suffix(".json.bak2"))

    s09 = shots["s09"]       # picture and prompts unchanged, so the approved keyframe stays cached
    s09["duration_s"] = 8
    s09["reason"] = ("The reveal: the scale of the great tree where only a small shoot was, "
                     "with her grandchildren in its shade.")
    s09["narration"] = "ከሃያ ዓመት በኋላ፣ እሷ ትሠራበት በነበረው ቦታ ግዙፍ ዋርካ ቆሟል።"
    s09["subtitle_en"] = "Twenty years later, a great warka tree stands where she worked."

    sb["shots"] = [s for s in sb["shots"] if s["id"] not in ("s10",)] + [S10, S11]
    sb["characters"].extend(NEW_CHARACTERS)
    sb["meta"]["target_duration_s"] = 87

    cues = sb["music"]["cues"]
    for cue in cues:
        if cue["at_shot"] == "s10":
            cue["note"] = "playful and light, the theme at its warmest while the children play"
    cues.append({"at_shot": "s11", "note": "resolves, the opening theme returns once and fades out "
                                           "into the end card"})

    PATH.write_text(json.dumps(sb, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("Patched storyboard.json (backup: storyboard.json.bak2). Validating...")
    sys.exit(subprocess.run([sys.executable, "pipeline/validate.py"]).returncode)


if __name__ == "__main__":
    main()