"""Legacy stage: narration via Gemini TTS (superseded by pipeline/narration.py using Addis AI)."""
import base64
import time
import wave
from pathlib import Path

import requests

try:
    from .common import OUT, cached_output, content_hash, env, log_run
    from .validate import load
except ImportError:
    from common import OUT, cached_output, content_hash, env, log_run
    from validate import load

# ---- change these two lines to change how the narrator sounds ----------------
MODEL = "gemini-3.8-flash-tts"
VOICE = "Charon"   # other prebuilt voices include: Charon, Puck, Fenrir, Orus, Zephyr, Aoede, Leda, Sulafat, Gacrux
# ------------------------------------------------------------------------------
STYLE = ""
GAP_S = 20             # pause between generated shots (free-tier limits are tight)
MAX_429_RETRIES = 5    # waits 20+40+60+80+100 s, then stops cleanly


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def synth(text: str, lang: str, out_path: Path, shot_id: str = "") -> None:
    del lang
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    prompt = f"{STYLE}: {text}" if STYLE else text
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}},
        },
    }
    for attempt in range(1, MAX_429_RETRIES + 1):
        r = requests.post(url, headers={"x-goog-api-key": env("GEMINI_API_KEY")}, timeout=180, json=body)
        if r.status_code != 429:
            break
        wait = 20 * attempt
        log_run(
            "narration",
            MODEL,
            {"shot": shot_id, "attempt": attempt, "wait_s": wait},
            ok=False,
            error="429: " + r.text[:300].replace("\n", " "),
        )
        print(f"  {shot_id}: 429 quota/rate limit, waiting {wait}s [{attempt}/{MAX_429_RETRIES}]")
        time.sleep(wait)
    else:
        print("\nStill rate limited after all waits. Full server message:\n" + r.text[:900])
        print("\nFinished shots are cached. Re-run later, or try another TTS model in MODEL.")
        raise SystemExit(2)
    r.raise_for_status()
    pcm = base64.b64decode(r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
    with wave.open(str(out_path), "wb") as w:  # 24 kHz mono 16-bit PCM
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)


def main() -> None:
    sb = load()
    lang = sb["meta"]["narration_language"]
    for shot in sb["shots"]:
        key = content_hash(MODEL, VOICE, STYLE, lang, shot["narration"])
        out = OUT / "narration" / f"{shot['id']}.wav"
        _, hit = cached_output(
            "narration",
            key,
            out,
            lambda p, s=shot: synth(s["narration"], lang, p, s["id"]),
            MODEL,
            {"voice": VOICE, "lang": lang, "shot": shot["id"]},
        )
        dur = wav_seconds(out)
        flag = "  <-- LONGER than the shot" if dur > shot["duration_s"] else ""
        print(f"{shot['id']}: {'cached' if hit else 'generated'}  {dur:.1f}s of {shot['duration_s']}s{flag}")
        if not hit:
            time.sleep(GAP_S)


if __name__ == "__main__":
    main()
