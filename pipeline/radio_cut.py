"""Radio cut: narration over a quiet placeholder drone on a black screen.

Purpose: test the story and its timing with real people before any pictures exist.
The audio is mixed in plain Python (no FFmpeg filter graph), so it behaves the same on
every FFmpeg version; FFmpeg only attaches the finished audio to a black video.

Each shot's narration starts at its slot; a slot is the longer of the storyboard's
duration_s and the narration length + 0.4 s, so lines never overlap. The script prints
which shots need a longer duration_s.

Outputs: outputs/final/radio_cut.wav (audio only, plays anywhere) and
         outputs/final/radio_cut.mp4 (vertical black frame + the same audio).
"""
import array
import math
import re
import subprocess
import wave
from pathlib import Path

try:
    from .common import OUT, log_run
    from .validate import load
except ImportError:
    from common import OUT, log_run
    from validate import load

RATE = 24000
TAIL_S = 2.0
BED_LEVEL = 0.03   # drone loudness, fraction of full scale (voice stays on top)
FRAME = RATE // 100  # 10 ms analysis window
# Manual override: cut this many ms off the end of EVERY clip before fading. Leave 0 unless a
# scratch remains after the automatic trim; then try 150, 250, 350.
TRIM_TAIL_MS = 0


def read_pcm(path: str | Path) -> array.array:
    """Read a 24 kHz mono 16-bit WAV file into a signed 16-bit PCM array."""
    with wave.open(str(path), "rb") as w:
        if w.getframerate() != RATE or w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise SystemExit(
                f"{path}: expected 24 kHz mono 16-bit, got "
                f"{w.getframerate()} Hz, {w.getnchannels()} ch, {8 * w.getsampwidth()} bit"
            )
        pcm = array.array("h")
        pcm.frombytes(w.readframes(w.getnframes()))
        return pcm


def envelope_db(pcm: array.array) -> list[float]:
    """Loudness in dB for each 10 ms window."""
    env = []
    for i in range(0, len(pcm) - FRAME + 1, FRAME):
        seg = pcm[i:i + FRAME]
        rms = math.sqrt(sum(x * x for x in seg) / FRAME) / 32768
        env.append(20 * math.log10(rms) if rms > 0 else -120.0)
    return env


def trim_artifact_tail(pcm: array.array, min_gap_ms: int = 120, max_artifact_ms: int = 250) -> tuple[array.array, int, bool]:
    """Cut trailing silence, and any short burst that follows a pause at the end of the clip.

    A genuine last word is longer than max_artifact_ms; a click or hiss from the TTS is not.
    Returns (pcm, ms_removed, artifact_burst_removed).
    """
    env = envelope_db(pcm)
    if not env:
        return pcm, 0, False
    ordered = sorted(env)
    thr = max(-70.0, ordered[int(0.95 * (len(ordered) - 1))] - 35.0)  # relative to the speech level
    segs, i = [], 0
    while i < len(env):
        if env[i] > thr:
            j = i
            while j < len(env) and env[j] > thr:
                j += 1
            segs.append([i, j])
            i = j
        else:
            i += 1
    gap, art = min_gap_ms // 10, max_artifact_ms // 10
    merged = []
    for sg in segs:
        if merged and sg[0] - merged[-1][1] < gap:
            merged[-1][1] = sg[1]
        else:
            merged.append(sg)
    burst = False
    while len(merged) > 1 and merged[-1][1] - merged[-1][0] < art:
        merged.pop()
        burst = True
    if not merged:
        return pcm, 0, False
    end = min(len(pcm), (merged[-1][1] + 6) * FRAME)  # keep 60 ms after the last speech
    return pcm[:end], round((len(pcm) - end) / RATE * 1000), burst


def prepare(pcm: array.array, shot_id: str, report: list[tuple]) -> array.array:
    """Trim trailing TTS artifacts, log diagnostics, and remove DC offset/edge clicks."""
    env = envelope_db(pcm)
    n = len(env) // 5 * 5
    tail = [round(max(env[k:k + 5])) for k in range(max(0, n - 60), n, 5)]  # last 600 ms, 50 ms steps
    pcm, removed_ms, burst = trim_artifact_tail(pcm)
    if TRIM_TAIL_MS:
        pcm = pcm[:max(0, len(pcm) - int(TRIM_TAIL_MS * RATE / 1000))]
    report.append((shot_id, removed_ms, burst, tail))
    return declick(pcm)


def declick(pcm: array.array) -> array.array:
    """Remove DC offset and fade the edges so joins between clips do not click."""
    if not len(pcm):
        return pcm
    mean = sum(pcm) / len(pcm)
    out = array.array("h", (max(-32768, min(32767, int(x - mean))) for x in pcm))
    fade_in, fade_out = int(0.015 * RATE), int(0.10 * RATE)
    for i in range(min(fade_in, len(out))):
        out[i] = int(out[i] * i / fade_in)
    for i in range(min(fade_out, len(out))):
        out[-1 - i] = int(out[-1 - i] * i / fade_out)
    return out


def db(samples: array.array) -> float:
    """Return RMS loudness in dBFS for a PCM array."""
    if not len(samples):
        return -120.0
    rms = math.sqrt(sum(s * s for s in samples) / len(samples)) / 32768
    return 20 * math.log10(rms) if rms > 0 else -120.0


def main() -> None:
    sb = load()
    voice = array.array("h")
    report = []
    print(f"{'shot':5s} {'start':>6s} {'voice':>6s} {'slot':>6s}  note")
    for shot in sb["shots"]:
        wav = OUT / "narration" / f"{shot['id']}.wav"
        if not wav.exists():
            raise SystemExit(f"Missing {wav}. Run narration.py first.")
        pcm = prepare(read_pcm(wav), shot["id"], report)
        secs = len(pcm) / RATE
        slot = max(shot["duration_s"], secs + 0.4)
        note = ""
        if slot > shot["duration_s"]:
            note = f"voice too long: set duration_s to {min(12, round(slot + 0.5))} in storyboard.json"
        print(
            f"{shot['id']:5s} {len(voice) / RATE:6.1f} {secs:6.1f} {slot:6.1f}  {note}"
            f"{'   <-- SILENT FILE' if db(pcm) < -50 else ''}"
        )
        voice.extend(pcm)
        voice.extend(array.array("h", bytes(2 * max(0, int(slot * RATE) - len(pcm)))))
    print("\nTail check: loudness (dB) of the last 600 ms of each raw clip, in 50 ms steps")
    for sid, ms, burst, tail in report:
        print(f"{sid}  trimmed {ms:4d} ms  {'ARTIFACT BURST REMOVED' if burst else '':22s} {tail}")
    voice.extend(array.array("h", bytes(2 * int(TAIL_S * RATE))))
    total = len(voice) / RATE
    print(f"\nTotal radio cut: {total:.1f} s (film target 60-90 s incl. end card)")

    voice_db = db(voice)
    print(f"Voice track level: {voice_db:.1f} dB (about -20 to -10 is normal)")
    if voice_db < -50:
        raise SystemExit(
            "The voice track is silent: the narration files contain no sound. "
            "Re-check outputs/narration/*.wav in a player."
        )

    env_head = envelope_db(voice[:20 * RATE])
    first = next((i for i, e in enumerate(env_head) if e > -40), None)
    print("First voice in the audio: " + (f"{first / 100:.1f} s" if first is not None else "none in the first 20 s"))

    # placeholder drone: D3 + A3 sines, slow tremolo, 3 s fade in and out
    mix = array.array("h")
    amp = BED_LEVEL * 32767 / 2
    n = len(voice)
    for i in range(n):
        t = i / RATE
        fade = min(1.0, t / 3.0, (total - t) / 3.0)
        trem = 1.0 - 0.4 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.2 * t))
        bed = amp * trem * fade * (math.sin(2 * math.pi * 146.83 * t) + math.sin(2 * math.pi * 220.0 * t))
        v = voice[i] + bed
        mix.append(max(-32768, min(32767, int(v))))

    out_dir = OUT / "final"
    out_dir.mkdir(parents=True, exist_ok=True)
    wav_out, mp4_out = out_dir / "radio_cut.wav", out_dir / "radio_cut.mp4"
    with wave.open(str(wav_out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(mix.tobytes())
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c=black:s=720x1280:r=24:d={total:.2f}",
            "-i", str(wav_out),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", "-shortest", str(mp4_out),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    # Verify the MP4 itself, 5 s window by window, instead of trusting the encoder or the player.
    wins = []
    for t0 in range(0, int(total), 5):
        chk = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-ss", str(t0), "-t", "5", "-i", str(mp4_out),
                "-vn", "-af", "volumedetect", "-f", "null", "-",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        m = re.search(r"mean_volume:\s*(-?[\d.]+|-inf) dB", chk.stderr)
        wins.append((t0, float(m.group(1)) if m and m.group(1) != "-inf" else -120.0))
    print("MP4 audio by 5 s window (voice is about -20 dB, drone only about -45 dB):")
    print("  " + "   ".join(f"{a}-{a + 5}s: {v:.0f} dB{'  <-- QUIET' if v < -35 else ''}" for a, v in wins))
    log_run("radio_cut", "python+ffmpeg", {"shots": len(sb["shots"]), "total_s": round(total, 1)}, output=mp4_out)
    print(f"\nWrote {wav_out}\nWrote {mp4_out}")


if __name__ == "__main__":
    main()
