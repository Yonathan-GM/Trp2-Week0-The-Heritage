"""Stage: music.

ACE-Step 1.5 runs on Kaggle/Colab. This stage writes outputs/music/request.json from the
storyboard (caption, tempo, key, duration, instrumental flag) for the notebook, and checks
that the chosen candidate exists as outputs/music/score.wav.

Generate ~3 candidates, copy them to outputs/music/candidate_<n>.wav, set
music.chosen_candidate in storyboard.json, copy the winner to score.wav, and record
why you chose it in EXPERIMENTS.md.
"""
import json

from common import OUT, content_hash, log_run
from validate import load


def main():
    sb = load()
    m = sb["music"]
    d = OUT / "music"
    d.mkdir(parents=True, exist_ok=True)
    req = {
        "caption": m["caption"] + (", instrumental" if m["instrumental"] else ""),
        "duration": m["duration_s"],
        "bpm": m.get("bpm"),
        "key": m.get("key"),
        "n_candidates": 3,
        "hash": content_hash(m["caption"], m["instrumental"], m.get("bpm"), m.get("key"), m["duration_s"]),
    }
    (d / "request.json").write_text(json.dumps(req, indent=2), encoding="utf-8")
    score = d / "score.wav"
    if score.exists():
        log_run("music", "ACE-Step-1.5", {"request": req["hash"], "chosen": m.get("chosen_candidate")},
                latency_s=0.0, cache="hit", output=score)
        print("score.wav present")
    else:
        print("No score.wav yet. Run the ACE-Step notebook with outputs/music/request.json, "
              "then copy the chosen candidate to outputs/music/score.wav.")


if __name__ == "__main__":
    main()
