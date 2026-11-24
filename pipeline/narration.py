"""Stage: narration. One WAV per shot via Gemini TTS, cached by content hash."""
import base64
import wave

import requests

from common import OUT, cached_output, content_hash, env
from validate import load

MODEL = "gemini-3.8-flash-tts"
VOICE = "Kore"  # change to taste; log the choice in EXPERIMENTS.md
STYLE = "Speak calmly, warmly and unhurriedly, like a family member telling a story."


def synth(text, lang, out_path):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    r = requests.post(url, headers={"x-goog-api-key": env("GEMINI_API_KEY")}, timeout=180, json={
        "contents": [{"parts": [{"text": f"{STYLE}\n\n{text}"}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}},
        },
    })
    r.raise_for_status()
    pcm = base64.b64decode(r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
    with wave.open(str(out_path), "wb") as w:  # 24 kHz mono 16-bit PCM
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)


def main():
    sb = load()
    lang = sb["meta"]["narration_language"]
    for shot in sb["shots"]:
        key = content_hash(MODEL, VOICE, STYLE, lang, shot["narration"])
        out = OUT / "narration" / f"{shot['id']}.wav"
        _, hit = cached_output("narration", key, out,
                               lambda p, s=shot: synth(s["narration"], lang, p),
                               MODEL, {"voice": VOICE, "lang": lang, "shot": shot["id"]})
        print(f"{shot['id']}: {'cached' if hit else 'generated'}")


if __name__ == "__main__":
    main()
