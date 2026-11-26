# Heritage Short

A 60-90 second AI-made short film about a story that matters to my family, built as a
reproducible pipeline: one file, `storyboard.json`, is the contract between every stage.

> TODO: one-paragraph description of the film and who it is for (see DESIGN.md).

## Run it

```bash
git clone <this repo> && cd heritage-short
cp .env.example .env        # add GEMINI_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN
make setup                  # pip install -r requirements.txt (needs ffmpeg on PATH)
make film                   # validate -> narration -> keyframes -> shots -> music -> assemble
```

Outputs land in `outputs/final/` (`film_vertical.mp4`, `film_horizontal.mp4`).

Re-runs are incremental: each stage hashes its inputs and regenerates only what changed.
Change one line in `storyboard.json`, run `make film`, and only that shot is regenerated.
Every model call (hit or miss) is logged as one line in `runs.jsonl`.

## Stages

| Stage | Command | Model | Runs on |
|---|---|---|---|
| Validate | `make validate` | JSON Schema | local |
| Narration | `make narration` | Gemini TTS | Gemini API |
| Keyframes | `make keyframes` | FLUX.1 schnell | Cloudflare Workers AI |
| Moving shots | `make shots` | Wan 2.2 TI2V-5B | Kaggle notebook (manual hand-off) |
| Music | `make music` | ACE-Step 1.5 | Kaggle/Colab (manual hand-off) |
| Assemble | `make assemble` | FFmpeg | local |

Wan and ACE-Step run on borrowed GPUs, so those two stages write a job file, you run the
notebook, copy the results back, and re-run the stage to log them. Shots without a clip
fall back to a subtle keyframe zoom, fitted with blurred fill when needed.

## What it costs

All free tiers; see COSTS.md for measured latency, GPU minutes and list-price equivalents.

## Docs

DESIGN.md (audience, tests) · ARCHITECTURE.md · EXPERIMENTS.md · FAILURES.md · COSTS.md · ETHICS.md

## Made with AI

The film carries an end card stating it was made with AI. See ETHICS.md for consent, licences and labelling.
