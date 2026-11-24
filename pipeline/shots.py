"""Stage: moving shots.

Wan 2.2 TI2V-5B runs on Kaggle/Colab, not here. This stage:
  1. writes outputs/shots/jobs.json: only the shots whose keyframe or motion prompt changed;
  2. ingests any clips you copied back from the notebook into outputs/shots/<id>.mp4 and logs them;
  3. leaves every other shot to the Ken Burns fallback in assemble.py.

Workflow: `make shots` -> upload jobs.json + keyframes to the notebook -> run it ->
download clips into outputs/shots/ -> `make shots` again to log them.
"""
import json
import time

from common import CACHE, OUT, content_hash, log_run
from validate import load

MODEL = "Wan2.2-TI2V-5B"
DRAFT_RES = "832x480"


def main():
    sb = load()
    shots_dir = OUT / "shots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    state_dir = CACHE / "shots"
    state_dir.mkdir(parents=True, exist_ok=True)

    jobs = []
    for shot in sb["shots"]:
        kf = OUT / "keyframes" / f"{shot['id']}.png"
        if not kf.exists():
            print(f"{shot['id']}: no keyframe yet, skipping")
            continue
        key = content_hash(MODEL, DRAFT_RES, kf.read_bytes().hex()[:4096], shot["motion_prompt"],
                           shot.get("seed", 0))
        marker = state_dir / f"{shot['id']}.hash"
        clip = shots_dir / f"{shot['id']}.mp4"
        if clip.exists() and marker.exists() and marker.read_text() == key:
            log_run("shots", MODEL, {"shot": shot["id"]}, latency_s=0.0, cache="hit", output=clip)
            print(f"{shot['id']}: cached")
        elif clip.exists() and not marker.exists():
            marker.write_text(key)  # clip ingested from the notebook
            log_run("shots", MODEL, {"shot": shot["id"], "res": DRAFT_RES, "ingested": True},
                    seed=shot.get("seed", 0), latency_s=None, output=clip)
            print(f"{shot['id']}: ingested from notebook (add GPU minutes to COSTS.md)")
        else:
            jobs.append({"id": shot["id"], "keyframe": f"keyframes/{shot['id']}.png",
                         "motion_prompt": shot["motion_prompt"], "seed": shot.get("seed", 0),
                         "resolution": DRAFT_RES, "hash": key})
            print(f"{shot['id']}: needs generation")

    (shots_dir / "jobs.json").write_text(json.dumps(jobs, indent=2), encoding="utf-8")
    print(f"\n{len(jobs)} job(s) written to outputs/shots/jobs.json "
          f"({time.strftime('%H:%M:%S')}). Shots without a clip use the Ken Burns fallback.")


if __name__ == "__main__":
    main()
