"""One command for the whole pipeline: python run.py

Runs the stages in order. Each stage caches its own output (by content hash), so a
re-run only redoes what changed in storyboard.json. Works on Windows, macOS and Linux.

  python run.py                    all stages
  python run.py --from keyframes   start at a stage (earlier stages are skipped)
  python run.py --only assemble    run a single stage
  python run.py --draft            half-size, fast assemble (passed to assemble.py)

Stages: validate, narration, keyframes, shots, music, assemble.
Note: 'shots' and 'music' prepare jobs for the Kaggle notebooks (Wan, ACE-Step) and
ingest their results when present; run the notebooks between runs.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGES = ["validate", "narration", "keyframes", "shots", "music", "assemble"]


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
        script = ROOT / "pipeline" / f"{stage}.py"
        if not script.exists():
            raise SystemExit(f"Missing {script}")
        cmd = [sys.executable, str(script)]
        if stage == "assemble" and args.draft:
            cmd.append("--draft")
        print(f"\n=== {stage} ===", flush=True)
        t0 = time.time()
        if subprocess.run(cmd, cwd=ROOT).returncode:
            raise SystemExit(f"\nStage '{stage}' failed. Fix it, then run: python run.py --from {stage}")
        print(f"=== {stage} done in {time.time() - t0:.1f} s ===", flush=True)

    print("\nAll done. Final films are in outputs/final/")


if __name__ == "__main__":
    main()