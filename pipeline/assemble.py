"""Assemble the film: per-shot video, narration, ducked music, burned-in subtitles, end card.

Reads storyboard.json (via validate.load) and whatever exists in outputs/:
  outputs/narration/sNN.wav        narration (required)
  outputs/clips/sNN*.mp4           Wan clip for a shot (preferred)
  outputs/keyframes/sNN*.png|jpg   keyframe image -> Ken Burns pan/zoom (fallback);
                                   9:16 fills the frame, 16:9 shows the whole picture on a blurred copy
  outputs/music/*                  chosen ACE-Step track (else a placeholder drone)
A shot with neither clip nor keyframe becomes a dark placeholder card, so the whole
pipeline can be tested before any pictures exist.

Outputs: outputs/final/film_vertical.mp4 (1080x1920) and film_horizontal.mp4 (1920x1080).

Usage:
  python pipeline/assemble.py                  both formats, full size
  python pipeline/assemble.py --draft          half size, fast check
  python pipeline/assemble.py --only vertical  one format

Needs: ffmpeg + ffprobe on PATH, and Pillow (pip install pillow) for subtitle images.
"""
import argparse
import array
import hashlib
import json
import math
import re
import subprocess
import textwrap
import wave

from common import OUT, log_run
from validate import load
from radio_cut import RATE, prepare, read_pcm

# ---- settings you may tune -------------------------------------------------
FPS = 24
FADE_S = 0.3            # short dip at each shot edge; set 0 for hard cuts
MUSIC_GAIN = 0.5        # music level before ducking
MAX_CROP = 0.50         # if source and frame shape differ more than this, use blurred fill instead of cropping
TARGET_LUFS = -14
TARGET_TP = -1
SUB_MAX_CHARS = 40
SUB_MAX_LINES = 2
FORMATS = {"vertical": (1080, 1920), "horizontal": (1920, 1080)}
SUB_BOTTOM = {"vertical": 0.80, "horizontal": 0.90}
FIT = {"vertical": "cover", "horizontal": "contain"}   # cover: picture fills the frame; contain: whole picture on a blurred copy
ZOOM = 0.08            # total slow zoom during a Ken Burns shot (8 %)   # bottom of subtitle block, fraction of height (safe area)

# where earlier pipeline steps are assumed to write; change here if yours differ
CLIP_DIRS = [OUT / "clips", OUT / "shots", OUT / "video"]
IMAGE_DIRS = [OUT / "keyframes", OUT / "images"]
MUSIC_DIR = OUT / "music"

FONT_CANDIDATES = [
    "C:/Windows/Fonts/seguisb.ttf", "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "seguisb.ttf", "arial.ttf", "DejaVuSans-Bold.ttf",
]


# ---- small helpers ---------------------------------------------------------
def ff(args, what, check=True):
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *map(str, args)],
                       capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"ffmpeg failed ({what}):\n{r.stderr[-1800:]}")
    return r


def probe_video(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    return int(s["width"]), int(s["height"])


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def write_wav(path, pcm, rate):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def find_file(dirs, exts, sid):
    hits = []
    for d in dirs:
        if d.is_dir():
            for p in d.iterdir():
                if p.suffix.lower() in exts and (p.stem == sid or p.stem.startswith(sid + "_")):
                    hits.append(p)
    return max(hits, key=lambda p: p.stat().st_mtime) if hits else None


def find_source(sid):
    clip = find_file(CLIP_DIRS, {".mp4", ".mov", ".webm"}, sid)
    if clip:
        return "clip", clip
    img = find_file(IMAGE_DIRS, {".png", ".jpg", ".jpeg", ".webp"}, sid)
    if img:
        return "image", img
    return "placeholder", None


def find_music(sb):
    if not MUSIC_DIR.is_dir():
        return None
    files = sorted(p for p in MUSIC_DIR.rglob("*")
                   if p.suffix.lower() in {".wav", ".mp3", ".flac", ".m4a", ".ogg"})
    if not files:
        return None
    score = MUSIC_DIR / "score.wav"
    if score.exists():
        return score
    chosen = sb["music"].get("chosen_candidate")
    if chosen is not None:
        for p in files:
            if str(chosen) in p.stem:
                return p
    for p in files:
        if "chosen" in p.stem.lower() or p.stem.lower() == "music":
            return p
    print(f"WARNING: music.chosen_candidate is null; using {files[0].name}. "
          f"Set it in storyboard.json once you have picked one.")
    return files[0]


# ---- subtitles -------------------------------------------------------------
def smart(text):
    text = re.sub(r"(^|[\s(\[])'", lambda m: m.group(1) + "\u2018", text)
    return text.replace("'", "\u2019")


def break_long(s, limit):
    if len(s) <= limit:
        return [s]
    mid = len(s) // 2
    spaces = [i for i, c in enumerate(s) if c == " "]
    if not spaces:
        return [s]
    best = min(spaces, key=lambda i: abs(i - mid) - (8 if s[i - 1] in ",;:" else 0))
    return break_long(s[:best].strip(), limit) + break_long(s[best:].strip(), limit)


def split_chunks(text):
    limit = SUB_MAX_CHARS * SUB_MAX_LINES - 10   # slack so two balanced lines always fit
    chunks, cur = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", smart(text.strip())):
        for piece in break_long(sentence, limit):
            if cur and len(cur) + 1 + len(piece) <= limit:
                cur += " " + piece
            else:
                if cur:
                    chunks.append(cur)
                cur = piece
    if cur:
        chunks.append(cur)
    return chunks


def balance(chunk):
    for width in range(max(len(chunk) // 2, 10), SUB_MAX_CHARS + 1):
        lines = textwrap.wrap(chunk, width)
        if len(lines) <= SUB_MAX_LINES:
            return lines
    return textwrap.wrap(chunk, SUB_MAX_CHARS)


def make_cues(text, voice_s):
    """List of (start, end, lines) in seconds from the start of the shot, spread over the voice."""
    chunks = split_chunks(text)
    total = sum(len(c) for c in chunks)
    span = max(voice_s, 1.0)
    t, cues = 0.1, []
    for c in chunks:
        d = span * len(c) / total
        cues.append([t, t + d, balance(c)])
        t += d
    cues[-1][1] += 0.3
    return cues


def load_font(size):
    from PIL import ImageFont
    for f in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_text_png(lines, W, H, path, y_anchor, size_frac, boxed, centered=False):
    from PIL import Image, ImageDraw
    size = int(min(W, H) * size_frac)
    max_w = int(W * 0.84)
    while True:
        font = load_font(size)
        widths = [font.getlength(l) for l in lines]
        if max(widths) <= max_w or size <= 16:
            break
        size -= 2
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    line_h = int(size * 1.3)
    block_h = line_h * len(lines)
    top = int(y_anchor - block_h / 2) if centered else int(y_anchor - block_h)
    if boxed:
        pad = int(size * 0.45)
        bw = max(widths)
        d.rounded_rectangle((W / 2 - bw / 2 - pad, top - pad * 0.4, W / 2 + bw / 2 + pad,
                             top + block_h + pad * 0.1), radius=int(size * 0.4), fill=(0, 0, 0, 150))
    for i, l in enumerate(lines):
        w = font.getlength(l)
        d.text(((W - w) / 2, top + i * line_h), l, font=font, fill=(255, 255, 255, 255),
               stroke_width=max(1, size // 18), stroke_fill=(0, 0, 0, 255))
    img.save(path)


# ---- audio -----------------------------------------------------------------
def build_voice(sb, end_s):
    voice = array.array("h")
    timeline, report = [], []
    for shot in sb["shots"]:
        wav = OUT / "narration" / f"{shot['id']}.wav"
        if not wav.exists():
            raise SystemExit(f"Missing {wav}. Run narration.py first.")
        pcm = prepare(read_pcm(wav), shot["id"], report)
        secs = len(pcm) / RATE
        slot = max(shot["duration_s"], secs + 0.4)
        timeline.append({"shot": shot, "start": len(voice) / RATE, "voice_s": secs, "slot": slot})
        voice.extend(pcm)
        voice.extend(array.array("h", bytes(2 * (int(slot * RATE) - len(pcm)))))
    voice.extend(array.array("h", bytes(2 * int(end_s * RATE))))
    return voice, timeline


def mix_audio(voice_wav, music, total, out_wav):
    if music:
        music_in = ["-i", music]
    else:
        music_in = ["-f", "lavfi", "-i",
                    f"aevalsrc=0.3*(sin(2*PI*146.83*t)+sin(2*PI*220*t)):s=48000:d={total:.2f}"]
    fmt = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"

    def graph(new_amix):
        mix = "amix=inputs=2:duration=first:normalize=0" if new_amix else "amix=inputs=2:duration=first,volume=2"
        return (f"[0:a]{fmt},asplit=2[v1][v2];"
                f"[1:a]{fmt},volume={MUSIC_GAIN},atrim=0:{total:.2f},apad=whole_dur={total:.2f},"
                f"afade=t=in:d=2,afade=t=out:st={total - 3:.2f}:d=3[m];"
                f"[m][v1]sidechaincompress=threshold=0.02:ratio=6:attack=300:release=1500[duck];"
                f"[duck][v2]{mix}[mix]")

    for new_amix in (True, False):
        r = ff(["-i", voice_wav, *music_in, "-filter_complex", graph(new_amix), "-map", "[mix]",
                "-ar", 48000, "-ac", 2, out_wav], "audio mix", check=False)
        if r.returncode == 0:
            return
    raise SystemExit(f"ffmpeg failed (audio mix):\n{r.stderr[-1800:]}")


def measure(src):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
                        f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    if not m:
        raise SystemExit("Could not measure loudness:\n" + r.stderr[-800:])
    return json.loads(m.group(0))


def normalise(src, dst):
    s = measure(src)
    af = (f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11:measured_I={s['input_i']}:"
          f"measured_LRA={s['input_lra']}:measured_TP={s['input_tp']}:"
          f"measured_thresh={s['input_thresh']}:offset={s['target_offset']}:linear=true,aresample=48000")
    ff(["-i", src, "-af", af, "-ar", 48000, "-ac", 2, dst], "loudness normalisation")
    after = measure(dst)
    print(f"Audio loudness: before {float(s['input_i']):.1f} LUFS, "
          f"after {float(after['input_i']):.1f} LUFS, true peak {float(after['input_tp']):.1f} dBTP "
          f"(target {TARGET_LUFS} / {TARGET_TP})")


# ---- video -----------------------------------------------------------------
def fit_graph(inp, W, H, sw, sh, out):
    """Filter text turning the source into exactly W x H: crop if the shapes are close, else blurred fill."""
    if abs((sw / sh) / (W / H) - 1) <= MAX_CROP:
        return f"[{inp}]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[{out}]"
    return (f"[{inp}]split[fa][fb];"
            f"[fa]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:5,eq=brightness=-0.08[fbg];"
            f"[fb]scale={W}:{H}:force_original_aspect_ratio=decrease[ffg];"
            f"[fbg][ffg]overlay=(W-w)/2:(H-h)/2,setsar=1[{out}]")


def smoothstep(p):
    return p * p * (3 - 2 * p)


def kb_frames(path, W, H, n, idx, fit):
    """Yield n raw RGB frames of a slow pan/zoom over one picture, smooth to the sub-pixel.

    fit="cover":   the picture fills the frame (the sides are cropped, so keep subjects centred).
    fit="contain": the whole picture is shown, centred, on a blurred copy of itself.
    The crop box uses float coordinates, so there is no pixel stepping (the shake that
    ffmpeg's zoompan filter produced).
    """
    from PIL import Image, ImageEnhance
    src = Image.open(path).convert("RGB")
    sw, sh = src.size
    bg = None
    if fit == "cover":
        out_w, out_h = W, H
        if sw / sh > W / H:
            bh0, bw0 = float(sh), sh * W / H
        else:
            bw0, bh0 = float(sw), sw * H / W
    else:
        k = min(W / sw, H / sh)
        out_w, out_h = round(sw * k), round(sh * k)
        bw0, bh0 = float(sw), float(sh)
        s = max(W / sw, H / sh)
        big = src.resize((max(W, round(sw * s)), max(H, round(sh * s))), Image.BICUBIC)
        left, top = (big.width - W) // 2, (big.height - H) // 2
        bg = big.crop((left, top, left + W, top + H))
        bg = bg.resize((max(2, W // 8), max(2, H // 8)), Image.BILINEAR)
        from PIL import ImageFilter
        bg = bg.filter(ImageFilter.GaussianBlur(4)).resize((W, H), Image.BICUBIC)
        bg = ImageEnhance.Brightness(bg).enhance(0.8)
    zoom_in = idx % 2 == 0
    fx0, fx1 = {2: (0.62, 0.38), 3: (0.38, 0.62)}.get(idx % 4, (0.5, 0.5))
    for i in range(n):
        p = smoothstep(i / max(1, n - 1))
        z = 1 + ZOOM * (p if zoom_in else 1 - p)
        bw, bh = bw0 / z, bh0 / z
        fx = fx0 + (fx1 - fx0) * p
        x0, y0 = fx * (sw - bw), 0.5 * (sh - bh)
        piece = src.resize((out_w, out_h), Image.BICUBIC, box=(x0, y0, x0 + bw, y0 + bh))
        if bg is None:
            frame = piece
        else:
            frame = bg.copy()
            frame.paste(piece, ((W - out_w) // 2, (H - out_h) // 2))
        yield frame.tobytes()


def make_segment(idx, tl, W, H, work, sub_bottom, fit):
    shot, slot = tl["shot"], tl["slot"]
    n = max(1, round(slot * FPS))
    kind, src = find_source(shot["id"])
    cues = make_cues(shot["subtitle_en"], tl["voice_s"])
    stat = src.stat() if src else None
    key = hashlib.sha1(json.dumps([str(src), stat.st_mtime_ns if stat else 0, stat.st_size if stat else 0,
                                   cues, W, H, round(slot, 3), idx % 4, FADE_S, FPS, fit, ZOOM, "kb2"]
                                  ).encode()).hexdigest()[:8]
    out = work / "segments" / f"{shot['id']}_{W}x{H}_{key}.mp4"
    if out.exists():
        return out, kind

    pngs = []
    for k, (t0, t1, lines) in enumerate(cues):
        p = work / "subs" / f"{shot['id']}_{W}x{H}_{key}_{k}.png"
        render_text_png(lines, W, H, p, H * sub_bottom, 0.047, boxed=True)
        pngs.append((t0, t1, p))

    frames = None
    if kind == "clip":
        sw, sh = probe_video(src)
        inputs = ["-i", src]
        graph = (f"[0:v]setpts={stretch_of(src, slot):.4f}*PTS,fps={FPS}[src];"
                 + fit_graph("src", W, H, sw, sh, "fit") +
                 f";[fit]tpad=stop_mode=clone:stop_duration={slot:.2f}[base]")
    elif kind == "image":
        inputs = ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", FPS, "-i", "-"]
        graph = "[0:v]null[base]"
        frames = kb_frames(src, W, H, n, idx, fit)
    else:
        inputs = ["-f", "lavfi", "-i", f"color=c=0x2b2118:s={W}x{H}:r={FPS}:d={slot:.2f}"]
        graph = "[0:v]null[base]"

    prev = "base"
    for k, (t0, t1, p) in enumerate(pngs):
        inputs += ["-i", p]
        graph += f";[{prev}][{k + 1}:v]overlay=0:0:enable='between(t,{t0:.2f},{t1:.2f})'[v{k + 1}]"
        prev = f"v{k + 1}"
    if FADE_S > 0:
        graph += (f";[{prev}]fade=t=in:st=0:d={FADE_S},fade=t=out:st={slot - FADE_S:.2f}:d={FADE_S},"
                  f"format=yuv420p[out]")
    else:
        graph += f";[{prev}]format=yuv420p[out]"

    tmp = out.with_name(out.stem + "_tmp.mp4")     # write to a temp name so a failed run is never cached
    args = [*inputs, "-filter_complex", graph, "-map", "[out]", "-t", f"{slot:.3f}", "-r", FPS, "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", 18, tmp]
    if frames is None:
        ff(args, f"segment {shot['id']}")
    else:
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *map(str, args)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for fr in frames:
                proc.stdin.write(fr)
        except BrokenPipeError:
            pass
        proc.stdin.close()
        err = proc.stderr.read().decode(errors="replace")
        if proc.wait():
            raise SystemExit(f"ffmpeg failed (segment {shot['id']}):\n{err[-1800:]}")
    tmp.replace(out)
    return out, kind


def stretch_of(src, slot, max_stretch=2.0):
    """Slow-down factor so a short Wan clip fills more of its slot (the rest is held)."""
    d = duration(src)
    return min(max(slot / d, 1.0), max_stretch) if d > 0 else 1.0


def make_end_card(sb, W, H, work):
    secs = float(sb["end_card"]["duration_s"])
    png = work / "subs" / f"endcard_{W}x{H}.png"
    render_text_png([sb["end_card"]["text"]], W, H, png, H / 2, 0.07, boxed=False, centered=True)
    out = work / "segments" / f"endcard_{W}x{H}.mp4"
    graph = (f"[0:v][1:v]overlay=0:0,fade=t=in:st=0:d=0.5,fade=t=out:st={secs - 0.5:.2f}:d=0.5,"
             f"format=yuv420p[out]")
    ff(["-f", "lavfi", "-i", f"color=c=0x1e1812:s={W}x{H}:r={FPS}:d={secs}", "-i", png,
        "-filter_complex", graph, "-map", "[out]", "-t", f"{secs:.3f}", "-r", FPS, "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", 18, out], "end card")
    return out


def concat(segs, out, work, name):
    lst = work / f"concat_{name}.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in segs), encoding="utf-8")
    ff(["-f", "concat", "-safe", 0, "-i", lst, "-c", "copy", out], "concat")


# ---- main ------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(FORMATS))
    ap.add_argument("--draft", action="store_true", help="half size, for fast checks")
    args = ap.parse_args()
    try:
        import PIL  # noqa: F401
    except ImportError:
        raise SystemExit("Pillow is missing. Run: pip install pillow")

    sb = load()
    end_s = float(sb["end_card"]["duration_s"])
    work = OUT / "assemble"
    final = OUT / "final"
    for d in (work / "segments", work / "subs", final):
        d.mkdir(parents=True, exist_ok=True)

    voice, timeline = build_voice(sb, end_s)
    total = len(voice) / RATE
    print(f"Timeline: {total:.1f} s including {end_s:.0f} s end card (brief: 60-90 s)")
    voice_wav = work / "voice.wav"
    write_wav(voice_wav, voice, RATE)

    music = find_music(sb)
    print("Music: " + (str(music) if music else "none found, using placeholder drone"))
    mixed, audio = work / "audio_mix.wav", work / "audio_final.wav"
    mix_audio(voice_wav, music, total, mixed)
    normalise(mixed, audio)

    scale = 0.5 if args.draft else 1
    last, kinds = None, {}
    for name, (W0, H0) in FORMATS.items():
        if args.only and args.only != name:
            continue
        W, H = int(W0 * scale), int(H0 * scale)
        print(f"\nBuilding {name} {W}x{H}")
        segs = []
        for i, tl in enumerate(timeline):
            seg, kind = make_segment(i, tl, W, H, work, SUB_BOTTOM[name], FIT[name])
            kinds[tl["shot"]["id"]] = kind
            print(f"  {tl['shot']['id']}  {kind:11s} slot {tl['slot']:.1f} s")
            segs.append(seg)
        segs.append(make_end_card(sb, W, H, work))
        video = work / f"video_{name}.mp4"
        concat(segs, video, work, name)
        out = final / f"film_{name}{'_draft' if args.draft else ''}.mp4"
        ff(["-i", video, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
            "-b:a", "192k", "-movflags", "+faststart", "-shortest", out], "final mux")
        print(f"  wrote {out}  (video {duration(video):.1f} s, file {duration(out):.1f} s)")
        last = out

    missing = [s for s, k in kinds.items() if k == "placeholder"]
    kb = [s for s, k in kinds.items() if k == "image"]
    print(f"\nWan clips: {sum(1 for k in kinds.values() if k == 'clip')}, "
          f"Ken Burns from keyframe: {len(kb)} {kb}, placeholder cards: {len(missing)} {missing}")
    log_run("assemble", "ffmpeg", {"total_s": round(total, 1), "draft": args.draft,
                                   "placeholders": len(missing)}, output=last)


if __name__ == "__main__":
    main()