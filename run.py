"""One command for the whole pipeline: python run.py

Runs the stages in order. Each stage caches its own output (by content hash), so a
re-run only redoes what changed in storyboard.json. Works on Windows, macOS and Linux.

  python run.py                    all stages
  python run.py --from keyframes   start at a stage (earlier stages are skipped)
  python run.py --only assemble    run a single stage
  python run.py --draft            half-size, fast assemble (passed to assemble.py)

Stages: validate, narration, keyframes, shots, music, assemble.
- 'shots' prepares/ingests the Wan 2.2 clips (made on a Kaggle GPU); shots without a clip
  fall back to a Ken Burns pan/zoom over the keyframe, so the film never depends on them.
- 'music' prepares the ACE-Step request (made on a Kaggle GPU). If no score exists in
  outputs/music/score.wav, the original score is synthesised locally by music_synth.py.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGES = ["validate", "narration", "keyframes", "shots", "music", "assemble"]
SCORE = ROOT / "outputs" / "music" / "score.wav"


def run(script, *extra):
    cmd = [sys.executable, str(ROOT / "pipeline" / script), *extra]
    return subprocess.run(cmd, cwd=ROOT).returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", choices=STAGES)
    ap.add_argument("--only", choices=STAGES)
    ap.add_argument("--draft", action="store_true", help="half-size assemble for a fast check")
    args = ap.parse_args()

    if args.only:
        todo = [args.only]
    else:
        todo = STAGES[STAGES.index(args.start):] if args.start else STAGES

    for stage in todo:
        script = f"{stage}.py"
        if not (ROOT / "pipeline" / script).exists():
            raise SystemExit(f"Missing pipeline/{script}")
        print(f"\n=== {stage} ===", flush=True)
        t0 = time.time()
        extra = ["--draft"] if stage == "assemble" and args.draft else []
        if run(script, *extra):
            raise SystemExit(f"\nStage '{stage}' failed. Fix it, then run: python run.py --from {stage}")
        if stage == "music" and not SCORE.exists():
            print("No AI-generated score found: synthesising the original score locally.", flush=True)
            if run("music_synth.py"):
                raise SystemExit("\nmusic_synth.py failed (it needs numpy: python -m pip install numpy)")
        print(f"=== {stage} done in {time.time() - t0:.1f} s ===", flush=True)

    print("\nAll done. Final films are in outputs/final/")


if __name__ == "__main__":
    main()