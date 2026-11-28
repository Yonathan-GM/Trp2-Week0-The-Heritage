# The Seed That Waited Twenty Years

A reproducible, contract-driven AI short-film pipeline in **Amharic with English subtitles** (under 90 seconds). It tells a true family story: Grandmother Tiseme kept planting a single *warka* (fig) seed despite failed seedlings, hungry goats, and gentle village laughter—and years after she passed away, it grew into a tree that shelters her grandchildren.

Designed **vertical-first (9:16)** for family viewing on phones and messaging apps, with a **16:9 horizontal cut** rendered from the same contract.

---

## Key Features

- **Single Source of Truth (`storyboard.json`):** Validated against `schema/storyboard.schema.json` and cross-field rules before any stage runs.
- **Incremental Content-Hash Caching:** Every stage hashes its inputs (prompts, voice settings, parameters, upstream files) into `.cache/` and logs every hit, miss, latency, and error as structured JSON lines in `runs.jsonl`.
- **Graceful Local Fallbacks:** Optional GPU stages (Wan 2.2 video clips and ACE-Step music) can be offloaded to Kaggle notebooks, while local Pillow sub-pixel Ken Burns motion and deterministic NumPy score synthesis (`pipeline/music_synth.py`) ensure the full film builds end-to-end without GPU queues.
- **Broadcast-Style Audio & Subtitles:** Two-pass EBU R128 loudness normalisation (`-14 LUFS`, `-1 dBTP`), sidechain-ducked score under narration, and safe-area burned-in subtitles.

---

## Quickstart

### Requirements

- **Python 3.10+**
- **FFmpeg** (`ffmpeg` and `ffprobe` available on `PATH`)

### Setup & Run

```bash
git clone https://github.com/Yonathan-GM/Trp2-Week0-The-Heritage
cd Trp2-Week0-The-Heritage
python -m pip install -r requirements.txt
cp .env.example .env   # add ADDIS_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN
python run.py
```

Required API keys in `.env`:
- `ADDIS_API_KEY` — Amharic narration (`pipeline/narration.py`)
- `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` — keyframe generation (`pipeline/keyframes.py`)
- `GEMINI_API_KEY` — optional, used only by `pipeline/smoke_test.py`

### Outputs

Final renders are written to `outputs/final/`:
- `film_vertical.mp4` — `1080x1920` (9:16 primary cut)
- `film_horizontal.mp4` — `1920x1080` (16:9 cut)

---

## CLI & Workflow Commands

| Command | Description |
|---|---|
| `python run.py` | Run all pipeline stages in order |
| `python run.py --dry-run` | Print planned stages without executing |
| `python run.py --draft` | Half-size assembly for fast iteration |
| `python run.py --only keyframes` | Run a single pipeline stage |
| `python run.py --from music` | Resume from a specific stage |
| `python pipeline/smoke_test.py` | Probe configured API providers |
| `python -m unittest discover -s tests -v` | Run automated unit tests |
| `python check_submission.py` | Verify secrets, docs, schema, and git hygiene |
| `make film` | Equivalent to `python run.py` |

---

## Pipeline Architecture

| Stage | Script | Model / Engine | Execution |
|---|---|---|---|
| Validate | `pipeline/validate.py` | JSON Schema Draft 2020-12 + cross-field checks | Local |
| Narration | `pipeline/narration.py` | Addis AI Amharic TTS (`am-yohanes-calm`) | Addis AI API |
| Keyframes | `pipeline/keyframes.py` | FLUX.1 schnell | Cloudflare Workers AI |
| Moving shots | `pipeline/shots.py` | Wan 2.2 TI2V-5B (optional) | Kaggle notebook |
| Music | `pipeline/music.py` / `pipeline/music_synth.py` | ACE-Step 1.5 (optional) or deterministic NumPy synth | Kaggle / Local |
| Assemble | `pipeline/assemble.py` | FFmpeg + Pillow | Local |

### Framing, Audio & Subtitles

- **9:16 (Vertical):** Crops to fill the frame (keyframes keep subjects centred).
- **16:9 (Horizontal):** Displays the full square keyframe centred over a darkened, blurred copy of itself so nothing is cropped.
- **Audio Mix:** Narration is placed on a non-overlapping shot timeline; the score is sidechain-ducked underneath (`threshold=0.02`, `ratio=6`, `attack=300ms`, `release=1500ms`) and normalised to `-14 LUFS` / `-1 dBTP`.
- **Subtitles:** English captions wrapped to at most 2 lines and 40 characters per line inside the safe area, burned in via Pillow + FFmpeg.

### Reproducibility Caveat

Cloudflare's `@cf/black-forest-labs/flux-1-schnell` endpoint rejects a `seed` parameter (HTTP 400 / error 5006), so freshly generated keyframes vary across uncached runs. Visual consistency relies on explicit character descriptions, a shared `style_block`, and `.cache/` hash markers.

---

## Project Layout

```text
.
├── run.py                      # Single-command pipeline orchestrator
├── check_submission.py         # Automated pre-submission & hygiene checks
├── storyboard.json             # Storyboard contract (shots, characters, music, timing)
├── schema/storyboard.schema.json
├── pipeline/                   # Modular stage scripts & shared helpers
├── scripts/                    # Developer helper scripts (voice auditioning)
├── tests/                      # Automated unit tests (unittest)
├── outputs/                    # Stage artifacts and final MP4 exports
└── *.md                        # Design, architecture, experiments, failures, costs, ethics
```

---

## Documentation

- [DESIGN.md](DESIGN.md) — Audience, story beats, AI-assisted workflow, and viewer tests
- [ARCHITECTURE.md](ARCHITECTURE.md) — Stage contract, caching, failure handling, and logging
- [EXPERIMENTS.md](EXPERIMENTS.md) — Logged experiments (`EXP-01` – `EXP-10`)
- [FAILURES.md](FAILURES.md) — Incident & failure log (`FAIL-01` – `FAIL-18`)
- [COSTS.md](COSTS.md) — Measured latencies, free-tier usage, and cost notes
- [ETHICS.md](ETHICS.md) — Consent, model licences, AI labelling, and privacy controls
