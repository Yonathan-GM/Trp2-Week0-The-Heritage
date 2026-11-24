# ARCHITECTURE

## Contract

`storyboard.json` is the only thing stages share. It is validated against
`schema/storyboard.schema.json` (plus cross-field rules in `pipeline/validate.py`) before every
stage, so a bad edit fails in one second instead of after a GPU job.

## Stages

validate -> narration -> keyframes -> shots -> music -> assemble

Each stage is one script in `pipeline/`, reads the storyboard, writes to `outputs/<stage>/`.

## Caching

`common.cached_output` hashes everything that determines an output (model, params, prompt,
seed, upstream inputs). If the hash matches the stored marker in `.cache/` and the file exists,
the call is skipped and logged as a cache hit. Change one prompt and only that shot regenerates.

## Failure handling

- `common.retry`: three attempts with exponential backoff on every network call.
- Failures are logged to `runs.jsonl` with `ok: false` and the error.
- Wan/ACE-Step run on borrowed GPUs: stages write job files and ingest results, so a
  timed-out notebook loses at most one job.
- Any shot without a clip falls back to Ken Burns over its keyframe (`fallback` in the storyboard).
- Secrets live in `.env` (git-ignored); `.env.example` documents the names.

## Logging

One JSON line per model call in `runs.jsonl`: stage, model, params, seed, latency, cost, GPU minutes, cache hit/miss.

TODO: add a diagram once the assemble stage is built.
