"""Try Addis AI Amharic text-to-speech on one shot's narration before changing the pipeline.

Needs:  python -m pip install -U addisai      and      ADDIS_API_KEY=... in your .env file

Usage (run from the repo root):
  python scripts/addis_voice_test.py                      s01 line with voice am-hamen
  python scripts/addis_voice_test.py s06                  another shot
  python scripts/addis_voice_test.py s01 am-hamen <id2>   compare several voice ids

It prints the voice catalogue, the cost estimate, and saves WAV files to outputs/voice_test/.
It never prints your key.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from common import OUT, env          # noqa: E402
from validate import load            # noqa: E402

try:
    from addisai import AddisAI
except ImportError:
    raise SystemExit("The addisai package is missing. Run: python -m pip install -U addisai")


def main() -> None:
    shot_id = sys.argv[1] if len(sys.argv) > 1 else "s01"
    voices = sys.argv[2:] or ["am-hamen"]
    shot = next((s for s in load()["shots"] if s["id"] == shot_id), None)
    if not shot:
        raise SystemExit(f"No shot {shot_id} in storyboard.json")
    text = shot["narration"]
    print(f"Text ({shot_id}): {text}\n")

    addis = AddisAI(api_key=env("ADDIS_API_KEY"))

    print("Amharic voices available to your account:")
    try:
        for v in addis.voices.list(language="am"):
            print("  ", v)
    except Exception as e:  # noqa: BLE001
        print("   could not list voices:", type(e).__name__, str(e)[:200])

    out_dir = OUT / "voice_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    for voice_id in voices:
        print(f"\n--- {voice_id} ---")
        try:
            print("estimate:", addis.voice.estimate(voice_id=voice_id, text=text, language="am"))
            clip = addis.voice.generate(
                voice_id=voice_id,
                text=text,
                language="am",
                output_format="wav_44100",
            )
            path = out_dir / f"addis_{voice_id}_{shot_id}.wav"
            clip.to_file(str(path))
            print("usage:", clip.usage)
            print("saved:", path)
        except Exception as e:  # noqa: BLE001
            print("failed:", type(e).__name__, str(e)[:300])
    print("\nPlay the files in VLC and compare with other candidate voices.")


if __name__ == "__main__":
    main()
