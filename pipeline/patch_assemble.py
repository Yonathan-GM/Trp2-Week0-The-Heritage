"""Apply three small fixes to pipeline/assemble.py. Run once from the Heritage folder:

    python patch_assemble.py

1. Square keyframes crop to fill 9:16 and 16:9 (MAX_CROP 0.25 -> 0.50) instead of a blurred band.
2. music: prefer outputs/music/score.wav (the chosen track), not the first candidate file.
3. Wan clips shorter than their slot are slowed down (up to 2x) before the last frame is held.

It checks that every target text occurs exactly once, keeps a backup, and re-checks the syntax.
"""
import py_compile
import shutil
from pathlib import Path

TARGET = Path("pipeline/assemble.py")

EDITS = [
    ("MAX_CROP = 0.25", "MAX_CROP = 0.50"),
    ('    chosen = sb["music"].get("chosen_candidate")',
     '    score = MUSIC_DIR / "score.wav"\n'
     '    if score.exists():\n'
     '        return score\n'
     '    chosen = sb["music"].get("chosen_candidate")'),
    ('graph = (f"[0:v]fps={FPS}[src];" + fit_graph("src", W, H, sw, sh, "fit") +',
     'graph = (f"[0:v]setpts={stretch_of(src, slot):.4f}*PTS,fps={FPS}[src];" '
     '+ fit_graph("src", W, H, sw, sh, "fit") +'),
    ("def make_end_card(sb, W, H, work):",
     "def stretch_of(src, slot, max_stretch=2.0):\n"
     '    """Slow-down factor so a short Wan clip fills more of its slot (the rest is held)."""\n'
     "    d = duration(src)\n"
     "    return min(max(slot / d, 1.0), max_stretch) if d > 0 else 1.0\n"
     "\n\n"
     "def make_end_card(sb, W, H, work):"),
]


def main():
    if not TARGET.exists():
        raise SystemExit("Run this from the Heritage folder (pipeline/assemble.py not found).")
    text = TARGET.read_text(encoding="utf-8")
    if "def stretch_of" in text:
        raise SystemExit("assemble.py is already patched. Nothing to do.")
    for old, _ in EDITS:
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"Cannot patch: expected 1 match, found {n} for:\n  {old[:70]}\n"
                             "Your assemble.py differs from the one I wrote; send me its first 60 lines.")
    shutil.copy(TARGET, TARGET.with_suffix(".py.bak"))
    for old, new in EDITS:
        text = text.replace(old, new)
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    py_compile.compile(str(TARGET), doraise=True)
    print("Patched pipeline/assemble.py (backup: assemble.py.bak). Syntax OK.")


if __name__ == "__main__":
    main()