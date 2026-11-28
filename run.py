"""One command for the whole pipeline: python run.py

Runs the stages in order. Each stage caches its own output (by content hash), so a
re-run only redoes what changed in storyboard.json. Works on Windows, macOS and Linux.

  python run.py                    all stages
  python run.py --from keyframes   start at a stage (earlier stages are skipped)
  python run.py --only assemble    run a single stage
  python run.py --draft            half-size, fast assemble (passed to assemble.py)
  python run.py --dry-run          print planned stages without executing them

Stages: validate, narration, keyframes, shots, music, assemble.
- 'shots' prepares/ingests the Wan 2.2 clips (made on a Kaggle GPU); shots without a clip
  fall back to a Ken Burns pan/zoom over the keyframe, so the film never depends on them.
- 'music' prepares the ACE-Step request (made on a Kaggle GPU). If no score exists in
  outputs/music/score.wav, the original score is synthesised locally by music_synth.py.
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGES = ["validate", "narration", "keyframes", "shots", "music", "assemble"]
FFMPEG_STAGES = {"narration", "assemble"}
SCORE = ROOT / "outputs" / "music" / "score.wav"


def run_stage(script: str, *extra: str) -> int:
    """Execute a pipeline stage script from the repository root."""
    cmd = [sys.executable, str(ROOT / "pipeline" / script), *extra]
    return subprocess.run(cmd, cwd=ROOT).returncode


def resolve_stages(start: str | None = None, only: str | None = None) -> list[str]:
    """Return the ordered list of pipeline stages to execute."""
    if only:
        return [only]
    return STAGES[STAGES.index(start):] if start else list(STAGES)


def check_media_tools(stages: list[str]) -> None:
    """Fail fast with a helpful message if required FFmpeg binaries are missing."""
    if not (set(stages) & FFMPEG_STAGES):
        return
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise SystemExit(
            f"Missing required tool(s) on PATH: {', '.join(missing)}. "
            "Install FFmpeg and ensure ffmpeg/ffprobe are on PATH."
        )


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the Heritage Short pipeline.")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--from", dest="start", choices=STAGES, help="Start from a specific stage")
    group.add_argument("--only", choices=STAGES, help="Run a single stage")
    ap.add_argument("--draft", action="store_true", help="Half-size assemble for a fast check")
    ap.add_argument("--dry-run", action="store_true", help="Show stages that would run and exit")
    args = ap.parse_args()

    todo = resolve_stages(start=args.start, only=args.only)
    if args.dry_run:
        print("Planned stages:", " -> ".join(todo))
        if "assemble" in todo and args.draft:
            print("Assemble mode: --draft (half resolution)")
        return

    check_media_tools(todo)

    for stage in todo:
        script = f"{stage}.py"
        if not (ROOT / "pipeline" / script).exists():
            raise SystemExit(f"Missing pipeline/{script}")
        print(f"\n=== {stage} ===", flush=True)
        t0 = time.time()
        extra = ["--draft"] if stage == "assemble" and args.draft else []
        if run_stage(script, *extra):
            raise SystemExit(f"\nStage '{stage}' failed. Fix it, then run: python run.py --from {stage}")
        if stage == "music" and not SCORE.exists():
            print("No AI-generated score found: synthesising the original score locally.", flush=True)
            if run_stage("music_synth.py"):
                raise SystemExit("\nmusic_synth.py failed (it needs numpy: python -m pip install numpy)")
        print(f"=== {stage} done in {time.time() - t0:.1f} s ===", flush=True)

    print("\nAll done. Final films are in outputs/final/")


if __name__ == "__main__":
    main()
