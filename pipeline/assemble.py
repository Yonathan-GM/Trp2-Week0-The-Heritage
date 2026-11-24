"""Stage: assembly. FFmpeg builds both aspect ratios from the storyboard.

Per shot: use the Wan clip if present, else a Ken Burns pan-and-zoom over the keyframe.
Then: concat, narration (placed per shot), score ducked under the voice with
sidechaincompress, burned-in English subtitles, end card, loudnorm to -14 LUFS / -1 dBTP.

STATUS: skeleton. Implement `build_shot_clip`, `build_audio`, `burn_subtitles`, `end_card`
and `export` next. Ask your coding agent to fill each in and test it with ffprobe.
"""
import subprocess
from pathlib import Path

from common import OUT
from validate import load

FORMATS = {"vertical": (1080, 1920), "horizontal": (1920, 1080)}
FPS = 24


def run(cmd):
    subprocess.run(cmd, check=True)


def build_shot_clip(shot, size, out_path):
    """Return a clip of exactly shot['duration_s'] at `size` (use Wan clip or Ken Burns)."""
    raise NotImplementedError


def build_audio(sb, out_path):
    """Narration per shot on a timeline + ducked score, loudnormed."""
    raise NotImplementedError


def burn_subtitles(video_in, sb, out_path):
    """Burn subtitle_en lines, max 2 lines x ~40 chars, inside the safe area."""
    raise NotImplementedError


def end_card(sb, size, out_path):
    raise NotImplementedError


def export(sb, name, size):
    raise NotImplementedError


def main():
    sb = load()
    (OUT / "final").mkdir(parents=True, exist_ok=True)
    for name, size in FORMATS.items():
        export(sb, name, size)


if __name__ == "__main__":
    main()
