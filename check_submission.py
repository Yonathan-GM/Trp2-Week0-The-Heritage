"""Pre-submission checker. Run from the repo root:

    python check_submission.py          report only
    python check_submission.py --fix    also apply the safe, additive fixes (.gitignore, requirements.txt)

It never prints a secret in full (only the first 4 characters) and never deletes anything.
Exit code 1 means at least one FAIL.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIX = "--fix" in sys.argv
results = []   # (level, message)


def add(level, msg):
    results.append((level, msg))
    print(f"[{level:4s}] {msg}")


def git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None
    return r.stdout if r.returncode == 0 else None


def mask(s):
    return f"{s[:4]}... ({len(s)} chars)"


SECRET_PATTERNS = {
    "Google API key (AIza...)": re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    "Google API key (AQ....)": re.compile(r"\bAQ\.[0-9A-Za-z_\-]{20,}"),
    "key= in a URL": re.compile(r"[?&]key=[0-9A-Za-z_\-\.]{12,}"),
    "Bearer token": re.compile(r"Bearer\s+[0-9A-Za-z_\-\.=]{20,}"),
    "assigned secret": re.compile(r"(?i)\b[A-Z_]*(?:API_KEY|TOKEN|SECRET)\s*[=:]\s*[\"']?[0-9A-Za-z_\-\.]{16,}"),
    "sk- key": re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
}


def scan_line(line):
    hits = []
    for name, rx in SECRET_PATTERNS.items():
        m = rx.search(line)
        if m:
            hits.append((name, mask(m.group(0))))
    return hits


TEXT_EXT = {".md", ".py", ".json", ".jsonl", ".txt", ".example", ".cfg", ".toml", ".yml", ".yaml",
            ".ipynb", ".csv", ".ini", ""}


def tracked_files():
    out = git("ls-files")
    if out is not None:
        return [ROOT / p for p in out.splitlines() if p]
    return [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and p.name != ".env"]


def read(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# ---------------------------------------------------------------- 1. files that must exist
def check_files():
    required = ["README.md", "ARCHITECTURE.md", "DESIGN.md", "EXPERIMENTS.md", "FAILURES.md", "COSTS.md",
                "ETHICS.md", "runs.jsonl", "storyboard.json", "schema/storyboard.schema.json", "run.py",
                "requirements.txt", ".env.example", ".gitignore", "pipeline/validate.py"]
    missing = [f for f in required if not (ROOT / f).exists()]
    add("FAIL" if missing else "OK", f"missing files: {missing}" if missing else "all required files present")


# ---------------------------------------------------------------- 2. secrets (files + history)
def check_secrets():
    found = []
    for p in tracked_files():
        if p.suffix.lower() in TEXT_EXT and p.exists() and p.stat().st_size < 3_000_000:
            for n, line in enumerate(read(p).splitlines(), 1):
                for name, m in scan_line(line):
                    found.append(f"{p.relative_to(ROOT)}:{n}  {name}  {m}")
    if found:
        add("FAIL", f"possible secrets in tracked files ({len(found)}):")
        for f in found[:15]:
            print("         " + f)
    else:
        add("OK", "no secrets found in tracked files")

    log = git("log", "--all", "-p", "-U0", "--no-color")
    if log is None:
        add("WARN", "git history not scanned (git missing or not a repository)")
        return
    commit, fname, hist = "", "", {}
    for line in log.splitlines():
        if line.startswith("commit "):
            commit = line.split()[1][:7]
        elif line.startswith("+++ "):
            fname = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("+") and not line.startswith("+++"):
            for name, m in scan_line(line):
                hist.setdefault((commit, fname, name, m), 0)
    if hist:
        add("FAIL", f"possible secrets in git HISTORY ({len(hist)}). Revoke those keys now; deleting the "
                    "line does not remove them from old commits:")
        for (c, f, name, m) in list(hist)[:15]:
            print(f"         commit {c}  {f}  {name}  {m}")
    else:
        add("OK", "no secrets found in git history")
    if "\n.env\n" in "\n" + "\n".join(git("ls-files").splitlines() if git("ls-files") else []) + "\n":
        add("FAIL", ".env is tracked by git")


# ---------------------------------------------------------------- 3. placeholders and stale statements
DOCS = ["README.md", "ARCHITECTURE.md", "DESIGN.md", "EXPERIMENTS.md", "FAILURES.md", "COSTS.md", "ETHICS.md"]


def check_docs():
    ph = re.compile(r"TODO|TBD|FIXME|<this repo>|lorem ipsum|\[fill|\bXXX\b|\?\?\?", re.I)
    bad = []
    texts = {}
    for d in DOCS:
        p = ROOT / d
        if p.exists():
            texts[d] = read(p)
            for n, line in enumerate(texts[d].splitlines(), 1):
                if ph.search(line):
                    bad.append(f"{d}:{n}  {line.strip()[:90]}")
    add("FAIL" if bad else "OK", f"{len(bad)} placeholder line(s):" if bad else "no TODO/TBD placeholders in docs")
    for b in bad[:20]:
        print("         " + b)

    def count(doc, rx):
        return len(set(re.findall(rx, texts.get(doc, ""))))

    n = count("EXPERIMENTS.md", r"EXP-\d+")
    add("OK" if n >= 10 else "WARN", f"EXPERIMENTS.md has {n} entries (brief asks for about 10)")
    n = count("FAILURES.md", r"FAIL-\d+")
    add("OK" if n >= 5 else "WARN", f"FAILURES.md has {n} entries")

    def has(doc, words, label):
        t = texts.get(doc, "").lower()
        miss = [w for w in words if w.lower() not in t]
        add("WARN" if miss else "OK", f"{doc}: missing mention of {miss}" if miss else f"{doc}: {label}")

    has("ETHICS.md", ["consent", "licen", "label"], "covers consent, licences and labelling")
    has("COSTS.md", ["list"], "mentions list-price equivalents")
    has("DESIGN.md", ["test 1", "test 2", "ai assistant"], "records both tests and AI-assisted story")
    has("ARCHITECTURE.md", ["storyboard.json"], "explains storyboard.json")
    has("README.md", ["python run.py"], "documents the one-command run")

    for d, t in texts.items():
        if "zenebech" in t.lower():
            add("WARN", f"{d} still uses the name 'Zenebech' (the storyboard and narration say Tiseme)")
    for d in ("README.md", "ARCHITECTURE.md", "ETHICS.md", "COSTS.md"):
        for n, line in enumerate(texts.get(d, "").splitlines(), 1):
            if "gemini tts" in line.lower():
                add("WARN", f"{d}:{n} says Gemini TTS; narration now uses Addis AI. Fix or explain: {line.strip()[:70]}")


# ---------------------------------------------------------------- 4. storyboard, consent, runs.jsonl
def check_data():
    r = subprocess.run([sys.executable, "pipeline/validate.py"], cwd=ROOT, capture_output=True, text=True)
    add("OK" if r.returncode == 0 else "FAIL", "validate.py: " + (r.stdout.strip() or r.stderr.strip())[:120])
    try:
        sb = json.loads(read(ROOT / "storyboard.json"))
        missing = [c["id"] for c in sb.get("characters", []) if not c.get("consent")]
        add("FAIL" if missing else "OK", f"characters without a consent record: {missing}" if missing
            else f"all {len(sb.get('characters', []))} characters have a consent record")
    except ValueError:
        add("FAIL", "storyboard.json is not valid JSON")
    p = ROOT / "runs.jsonl"
    if p.exists():
        lines = [l for l in read(p).splitlines() if l.strip()]
        bad = 0
        stages = {}
        for l in lines:
            try:
                rec = json.loads(l)
                stages[str(rec.get("stage"))] = stages.get(str(rec.get("stage")), 0) + 1
            except ValueError:
                bad += 1
        add("FAIL" if bad else "OK", f"runs.jsonl: {len(lines)} lines, {bad} unreadable; stages: {stages}")


# ---------------------------------------------------------------- 5. final films
def check_films():
    for name, size in (("film_vertical.mp4", (1080, 1920)), ("film_horizontal.mp4", (1920, 1080))):
        p = ROOT / "outputs" / "final" / name
        if not p.exists():
            add("WARN", f"{name} not found in outputs/final (build it with python run.py)")
            continue
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
                            "-show_entries", "format=duration", "-of", "json", str(p)],
                           capture_output=True, text=True)
        try:
            info = json.loads(r.stdout)
            dur = float(info["format"]["duration"])
            v = next(s for s in info["streams"] if s["codec_type"] == "video")
            a = any(s["codec_type"] == "audio" for s in info["streams"])
        except (ValueError, KeyError, StopIteration):
            add("FAIL", f"{name}: ffprobe could not read it")
            continue
        ok = 60 <= dur <= 90 and (v["width"], v["height"]) == size and a
        add("OK" if ok else "FAIL", f"{name}: {v['width']}x{v['height']}, {dur:.1f} s, audio={'yes' if a else 'NO'}"
                                    + ("" if ok else f" (need {size[0]}x{size[1]}, 60-90 s, with audio)"))


# ---------------------------------------------------------------- 6. git hygiene
def check_git():
    files = git("ls-files")
    if files is None:
        add("WARN", "not a git repository (or git missing)")
        return
    tracked = [f for f in files.splitlines() if f]
    junk = [f for f in tracked if re.search(r"(^|/)patch_.*\.py$|\.bak\d*$|\.bak\.|__pycache__|\.pyc$", f)]
    if junk:
        add("WARN", "scratch files are tracked; remove them from the repo:")
        for f in junk:
            print(f"         git rm --cached \"{f}\"")
    else:
        add("OK", "no patch scripts, backups or caches tracked")
    big = []
    for f in tracked:
        p = ROOT / f
        if p.exists() and p.stat().st_size > 25_000_000:
            big.append((f, p.stat().st_size / 1e6))
    for f, mb in big:
        add("FAIL" if mb > 90 else "WARN", f"large tracked file {f}: {mb:.0f} MB (GitHub rejects > 100 MB)")
    if not big:
        add("OK", "no oversized tracked files")
    if not (ROOT / "notebooks").exists():
        add("WARN", "no notebooks/ folder: put kaggle_wan_clips.ipynb and kaggle_acestep_music.ipynb there")


def check_ignore_and_requirements():
    gi = ROOT / ".gitignore"
    have = set(read(gi).splitlines()) if gi.exists() else set()
    want = [".env", "__pycache__/", "*.pyc", "*.bak*"]
    miss = [w for w in want if w not in have]
    if miss and FIX:
        with open(gi, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n" + "\n".join(miss) + "\n")
        add("OK", f".gitignore: added {miss}")
    else:
        add("WARN" if miss else "OK", f".gitignore is missing {miss} (run with --fix)" if miss else ".gitignore ok")
    rq = ROOT / "requirements.txt"
    names = {re.split(r"[<>=\[ ;#]", l.strip(), 1)[0].lower() for l in read(rq).splitlines() if l.strip()}
    need = ["pillow", "numpy", "addisai", "requests"]
    miss = [n for n in need if n not in names]
    if miss and FIX:
        with open(rq, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n".join([""] + miss) + "\n")
        add("OK", f"requirements.txt: added {miss}")
    else:
        add("WARN" if miss else "OK", f"requirements.txt is missing {miss} (run with --fix)" if miss
            else "requirements.txt ok")


def main():
    print(f"Checking {ROOT}\n")
    for fn in (check_files, check_secrets, check_docs, check_data, check_films, check_git,
               check_ignore_and_requirements):
        fn()
    fails = sum(1 for l, _ in results if l == "FAIL")
    warns = sum(1 for l, _ in results if l == "WARN")
    print(f"\n{fails} FAIL, {warns} WARN, {sum(1 for l, _ in results if l == 'OK')} OK")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()