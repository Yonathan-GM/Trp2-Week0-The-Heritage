"""Stage: narration. One WAV per shot, spoken by Addis AI (Amharic), cached by hash.

Output: outputs/narration/<shot>.wav as 24 kHz mono 16-bit, which is what radio_cut.py and
assemble.py expect (Addis returns 44.1 kHz, so each clip is converted with ffmpeg).

Needs:  python -m pip install -U addisai    ADDIS_API_KEY in .env    ffmpeg on PATH

Usage:
  python pipeline/narration.py            every shot; lines whose text and voice are unchanged
                                          come from the cache and are not charged again
  python pipeline/narration.py s11 s05    only these shots
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from common import OUT, cached_output, content_hash, env
from validate import load

try:
    from addisai import AddisAI
except ImportError:
    raise SystemExit("The addisai package is missing. Run: python -m pip install -U addisai")

try:
    from addisai import InsufficientCreditsError, RateLimitError
except ImportError:                      # older SDK without these names
    class InsufficientCreditsError(Exception):
        pass

    class RateLimitError(Exception):
        pass

PROVIDER = "addis-ai"
VOICE = "am-yohanes-calm"        # change after comparing voices with addis_voice_test.py
LANGUAGE = "am"
VOICE_SETTINGS = None     # e.g. {"speed": 50, "stability": 50, "similarity": 50, "style": 0}
RATE = 24000
MAX_TRIES = 3

_client = None


def client():
    global _client
    if _client is None:
        _client = AddisAI(api_key=env("ADDIS_API_KEY"))
    return _client


def synth(text, out_path):
    args = {"voice_id": VOICE, "text": text, "language": LANGUAGE, "output_format": "wav_44100"}
    if VOICE_SETTINGS:
        args["voice_settings"] = VOICE_SETTINGS
    clip = None
    for attempt in range(1, MAX_TRIES + 1):
        try:
            clip = client().voice.generate(**args)
            break
        except InsufficientCreditsError as e:
            raise SystemExit(f"Addis AI credits are used up: {e}")
        except RateLimitError as e:
            wait = getattr(e, "retry_after", None) or 2 * attempt
            print(f"  rate limited, waiting {wait} s (try {attempt}/{MAX_TRIES})")
            time.sleep(wait)
    if clip is None:
        raise SystemExit("Addis AI kept rate-limiting; try again in a minute.")

    with tempfile.TemporaryDirectory() as d:
        raw = Path(d) / "raw.wav"
        clip.to_file(str(raw))
        r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(raw),
                            "-ar", str(RATE), "-ac", "1", "-sample_fmt", "s16", "-f", "wav", str(out_path)],
                           capture_output=True, text=True)
        if r.returncode:
            raise SystemExit("ffmpeg could not convert the Addis audio:\n" + r.stderr[-800:])
    try:    # keep the credits used, for COSTS.md
        with open(OUT / "narration" / "addis_usage.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "voice": VOICE,
                                "chars": len(text), "usage": getattr(clip, "usage", None)},
                               ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def main():
    sb = load()
    wanted = set(sys.argv[1:])
    known = {s["id"] for s in sb["shots"]}
    if wanted - known:
        raise SystemExit(f"Unknown shot id(s): {sorted(wanted - known)}. Known: {sorted(known)}")
    (OUT / "narration").mkdir(parents=True, exist_ok=True)
    made = 0
    for shot in sb["shots"]:
        if wanted and shot["id"] not in wanted:
            continue
        text = shot["narration"].strip()
        if not text:
            print(f"{shot['id']}: no narration text, skipped")
            continue
        key = content_hash(PROVIDER, VOICE, LANGUAGE, json.dumps(VOICE_SETTINGS, sort_keys=True), text)
        out = OUT / "narration" / f"{shot['id']}.wav"
        _, hit = cached_output("narration", key, out, lambda p, t=text: synth(t, p),
                               f"{PROVIDER}:{VOICE}", {"shot": shot["id"], "chars": len(text)}, seed=None)
        print(f"{shot['id']}: {'cached' if hit else 'generated'}")
        made += 0 if hit else 1
    print(f"\n{made} clip(s) generated this run.")


if __name__ == "__main__":
    main()
