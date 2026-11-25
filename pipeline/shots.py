"""Stage: moving shots.

Wan 2.2 TI2V-5B runs on Kaggle/Colab, not here. This stage:
  1. writes outputs/shots/jobs.json and outputs/shots/wan_input.zip (jobs + the keyframes they
     need) for only the shots whose keyframe or motion prompt changed;
  2. ingests clips you copied back from the notebook into outputs/shots/<id>.mp4, logs them
     (with the notebook's seconds-per-clip from outputs/shots/timings.json if present);
  3. moves a clip made from an OLD keyframe to outputs/shots/stale/ so assemble.py never uses it;
  4. leaves every other shot to the Ken Burns fallback in assemble.py.

Workflow: python pipeline/shots.py -> upload wan_input.zip to Kaggle -> run the notebook ->
download wan_clips.zip, unzip into outputs/shots/ -> python pipeline/shots.py again to log them.
"""
import hashlib
import json
import time
import zipfile

from common import CACHE, OUT, content_hash, log_run
from validate import load

MODEL = "Wan2.2-TI2V-5B"
RES = "480x832"          # width x height: portrait, because the 9:16 film is the main version
NUM_FRAMES = 121         # 5 s at 24 fps (must be 4k+1)
STEPS = 30
PRIORITY = ["s09", "s08", "s01"]   # generated first; edit to taste


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def main():
    sb = load()
    width, height = (int(v) for v in RES.split("x"))
    shots_dir = OUT / "shots"
    stale_dir = shots_dir / "stale"
    shots_dir.mkdir(parents=True, exist_ok=True)
    state_dir = CACHE / "shots"
    state_dir.mkdir(parents=True, exist_ok=True)

    timings = {}
    tfile = shots_dir / "timings.json"
    if tfile.exists():
        try:
            timings = json.loads(tfile.read_text(encoding="utf-8"))
        except ValueError:
            print("timings.json is not valid JSON; ignoring it")

    order = sorted(sb["shots"], key=lambda s: (PRIORITY.index(s["id"]) if s["id"] in PRIORITY
                                              else len(PRIORITY), s["id"]))
    jobs = []
    for shot in order:
        sid = shot["id"]
        seed = shot.get("seed", 0)
        kf = OUT / "keyframes" / f"{sid}.png"
        if not kf.exists():
            print(f"{sid}: no keyframe yet, skipping")
            continue
        key = content_hash(MODEL, RES, NUM_FRAMES, STEPS, file_hash(kf), shot["motion_prompt"], seed)
        marker = state_dir / f"{sid}.hash"
        clip = shots_dir / f"{sid}.mp4"
        new_clip = clip.exists() and (not marker.exists() or clip.stat().st_mtime > marker.stat().st_mtime)
        if new_clip:
            marker.write_text(key)
            log_run("shots", MODEL, {"shot": sid, "res": RES, "frames": NUM_FRAMES, "steps": STEPS,
                                     "ingested": True}, seed=seed, latency_s=timings.get(sid), output=clip)
            print(f"{sid}: ingested from notebook ({timings.get(sid, '?')} s; add GPU time to COSTS.md)")
        elif clip.exists() and marker.exists() and marker.read_text() == key:
            log_run("shots", MODEL, {"shot": sid}, latency_s=0.0, cache="hit", output=clip)
            print(f"{sid}: cached")
        else:
            if clip.exists():
                stale_dir.mkdir(exist_ok=True)
                clip.replace(stale_dir / f"{sid}_{int(time.time())}.mp4")
                print(f"{sid}: keyframe or prompt changed, old clip moved to shots/stale/")
            marker.unlink(missing_ok=True)
            jobs.append({"id": sid, "keyframe": f"keyframes/{sid}.png",
                         "motion_prompt": shot["motion_prompt"], "seed": seed,
                         "width": width, "height": height, "num_frames": NUM_FRAMES,
                         "steps": STEPS, "hash": key})
            print(f"{sid}: needs generation")

    (shots_dir / "jobs.json").write_text(json.dumps(jobs, indent=2), encoding="utf-8")
    zip_path = shots_dir / "wan_input.zip"
    if jobs:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(shots_dir / "jobs.json", "jobs.json")
            for j in jobs:
                z.write(OUT / j["keyframe"], j["keyframe"])
    elif zip_path.exists():
        zip_path.unlink()
    print(f"\n{len(jobs)} job(s) written ({time.strftime('%H:%M:%S')})."
          + (f" Upload {zip_path} to Kaggle." if jobs else "")
          + " Shots without a clip use the Ken Burns fallback.")


if __name__ == "__main__":
    main()