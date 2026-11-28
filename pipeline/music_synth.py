"""Original score, synthesised by code: plucked lyre + warm pad + soft shaker in D minor, 68 bpm.

A fallback for when the AI music model (ACE-Step on Kaggle) is not available. Fully local,
reproducible (fixed random seed) and with no third-party licence. The loudness arc follows the
music cues in storyboard.json: sparse at the start, almost nothing at s03, a swell at s06,
near silence at s07, the theme returning at s08, full and warm at s09/s10, resolving at s11.

Needs: python -m pip install numpy
Usage:  python pipeline/music_synth.py          writes outputs/music/score.wav
        python pipeline/music_synth.py --force  overwrite an existing score.wav
"""
import sys
import time
import wave
from typing import Any

try:
    import numpy as np
except ImportError:
    raise SystemExit("numpy is missing. Run: python -m pip install numpy")

try:
    from .common import OUT, log_run
    from .validate import load
except ImportError:
    from common import OUT, log_run
    from validate import load

SR = 44100
BPM = 68
BEAT = 60.0 / BPM
BAR = 4 * BEAT
CHORDS = [
    [50, 53, 57, 62],    # Dm   (MIDI note numbers: root, third, fifth, octave)
    [46, 50, 53, 58],    # Bb
    [53, 57, 60, 65],    # F
    [48, 52, 55, 60],    # C
]
PATTERN = [0, 1, 2, 1, 3, 2, 1, 2]   # which chord tone each eighth note plays
# (pluck, pad, shaker) level per shot, from the cue notes in storyboard.json
LEVELS = {
    "s01": (0.50, 0.25, 0.0), "s02": (0.50, 0.30, 0.0), "s03": (0.12, 0.12, 0.0),
    "s04": (0.30, 0.25, 0.0), "s05": (0.35, 0.35, 0.0), "s06": (0.40, 0.85, 0.0),
    "s07": (0.00, 0.30, 0.0), "s08": (0.55, 0.40, 0.0), "s09": (0.85, 0.80, 0.35),
    "s10": (0.85, 0.65, 0.55), "s11": (0.55, 0.65, 0.15),
}
DEFAULT = (0.4, 0.3, 0.0)


def freq(m: int | float) -> float:
    """Convert MIDI note number to frequency in Hz."""
    return 440.0 * 2 ** ((m - 69) / 12)


def shot_slots(sb: dict[str, Any]) -> list[float]:
    """Compute per-shot slot durations matching assemble.py / radio_cut.py."""
    slots = []
    for s in sb["shots"]:
        v = 0.0
        w = OUT / "narration" / f"{s['id']}.wav"
        if w.exists():
            with wave.open(str(w)) as f:
                v = f.getnframes() / f.getframerate()
        slots.append(max(s["duration_s"], v + 0.4))
    return slots


def curves(sb: dict[str, Any], slots: list[float], total: float, t: np.ndarray) -> list[np.ndarray]:
    """Per-sample level curves (pluck, pad, shaker), smooth between shots."""
    pts: list[list[tuple[float, float]]] = [[], [], []]
    start = 0.0
    for s, slot in zip(sb["shots"], slots):
        lv = LEVELS.get(s["id"], DEFAULT)
        ramp = min(0.8, slot / 3.0)
        for k in range(3):
            pts[k] += [(start + ramp, lv[k]), (start + slot - ramp, lv[k])]
        start += slot
    out = []
    for k in range(3):
        if not pts[k]:
            out.append(np.zeros_like(t))
            continue
        xs = [0.0] + [p[0] for p in pts[k]] + [total]
        ys = [pts[k][0][1]] + [p[1] for p in pts[k]] + [pts[k][-1][1]]
        out.append(np.interp(t, xs, ys))
    return out


def pluck(f: float, dur: float = 2.4) -> np.ndarray:
    """Synthesize a warm plucked-lyre note using damped harmonic partials."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    amps = [1.0, 0.55, 0.30, 0.16, 0.08, 0.04]
    decays = [1.8, 3.0, 4.5, 6.5, 9.0, 12.0]       # upper partials die faster: bright attack, mellow tail
    y = sum(
        a * np.sin(2 * np.pi * f * (k + 1) * t) * np.exp(-d * t)
        for k, (a, d) in enumerate(zip(amps, decays))
    )
    y *= np.minimum(1.0, t / 0.006)                # 6 ms attack, no click
    return y * 0.35


def pad_bar(notes: list[int], dur: float) -> np.ndarray:
    """Synthesize a detuned warm pad chord over a Hann window."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for m in notes:
        f = freq(m)
        for det in (0.997, 1.003):
            y += (
                np.sin(2 * np.pi * f * det * t)
                + 0.35 * np.sin(2 * np.pi * 2 * f * det * t)
                + 0.12 * np.sin(2 * np.pi * 3 * f * det * t)
            )
    return y * np.hanning(n) * 0.05


def main() -> None:
    force = "--force" in sys.argv
    sb = load()
    score = OUT / "music" / "score.wav"
    if score.exists() and not force:
        raise SystemExit(f"{score} already exists. Use --force to replace it.")
    t0 = time.time()
    slots = shot_slots(sb)
    total = sum(slots) + float(sb["end_card"]["duration_s"])
    n = int(total * SR)
    t = np.arange(n) / SR
    pluck_lv, pad_lv, shake_lv = curves(sb, slots, total, t)
    rng = np.random.default_rng(7)

    # pad: one chord per bar, overlapping Hann windows (hop = 1 bar, length = 2 bars)
    pad = np.zeros(n)
    bars = int(total / BAR) + 2
    for k in range(bars):
        a = int((k - 0.5) * BAR * SR)
        seg = pad_bar([m - 12 if i in (0, 2) else m for i, m in enumerate(CHORDS[k % 4])], 2 * BAR)
        lo, hi = max(a, 0), min(a + len(seg), n)
        if hi > lo:
            pad[lo:hi] += seg[lo - a:hi - a]
    pad *= pad_lv

    # plucked arpeggio, one note per eighth, quieter or skipped where the cue says "thin"
    left, right = np.zeros(n), np.zeros(n)
    eighth = BEAT / 2
    count = int(total / eighth)
    cache: dict[int, np.ndarray] = {}
    for i in range(count):
        at = int(i * eighth * SR)
        lvl = pluck_lv[min(at, n - 1)]
        if lvl < 0.05:
            continue
        bar = int(i // 8)
        m = CHORDS[bar % 4][PATTERN[i % 8]]
        if m not in cache:
            cache[m] = pluck(freq(m))
        note = cache[m] * lvl * (0.9 + 0.1 * rng.random())
        end = min(at + len(note), n)
        g = 0.62 if i % 2 == 0 else 0.38           # alternate sides for gentle width
        left[at:end] += note[:end - at] * g
        right[at:end] += note[:end - at] * (1 - g)

    # light shaker on the off-beats
    m_len = int(SR * 0.06)
    env = np.exp(-np.arange(m_len) / (SR * 0.015))
    for i in range(count):
        if i % 2 == 0:
            continue
        at = int(i * eighth * SR)
        lvl = shake_lv[min(at, n - 1)]
        if lvl < 0.05 or at + m_len > n:
            continue
        noise = np.diff(rng.standard_normal(m_len + 1)) * env * 0.05 * lvl
        left[at:at + m_len] += noise
        right[at:at + m_len] += noise * 0.8

    left += pad
    right += pad
    fade_in = np.minimum(1.0, t / 1.5)
    fade_out = np.minimum(1.0, (total - t) / 3.0)
    mix = np.stack([left * fade_in * fade_out, right * fade_in * fade_out], axis=1)
    mix *= 0.7 / max(1e-9, np.abs(mix).max())

    score.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(score), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype("<i2").tobytes())

    print(f"Wrote {score}: {total:.1f} s, {bars} bars of Dm - Bb - F - C at {BPM} bpm")
    print("Level per shot (dB, quieter = thinner):")
    start = 0.0
    for s, slot in zip(sb["shots"], slots):
        seg = mix[int(start * SR):int((start + slot) * SR)]
        rms = np.sqrt(np.mean(seg ** 2)) if len(seg) else 0
        print(f"  {s['id']}: {20 * np.log10(max(rms, 1e-6)):6.1f} dB")
        start += slot
    log_run(
        "music",
        "python-synth-numpy",
        {"bpm": BPM, "key": "D minor", "duration_s": round(total, 1)},
        latency_s=round(time.time() - t0, 1),
        output=score,
    )


if __name__ == "__main__":
    main()
