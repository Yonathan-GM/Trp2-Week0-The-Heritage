# COSTS.md

Cost and latency record for the story-to-video pipeline.

**Cost basis:** All stages below ran on **free tiers** or locally on CPU; measured out-of-pocket cost for this project was **$0.00**. List-price equivalents are noted separately below and should be verified against provider pricing pages before citing for commercial budgets.

Latency figures are **measured** from `runs.jsonl` unless noted otherwise.

---

## Measured latency by stage

| Stage | Model / provider | Measured latency (cache miss) | Sample size (`runs.jsonl`) |
|---|---|---|---|
| Narration (primary) | Addis AI (`am-yohanes-calm`) | 5.5–7.9 s per clip | 11 generated runs (11 cache hits) |
| Narration (voice test) | Addis AI (`am-hamen`) | 5.3–8.4 s per clip | 11 generated runs |
| Narration (earlier trial) | Gemini 3.8 Flash audio | 3.2–5.5 s per short call (excl. 429 retries) | 32 ok calls (34 failed due to 429 rate limits) |
| Keyframes | FLUX.1 schnell (Cloudflare) | 2.0–9.1 s per image | 26 generated runs (27 cache hits) |
| Text | Gemini 3.5 Flash | 24.8 s (after two 503s on newer models) | 1 successful run |
| Music (local fallback) | `pipeline/music_synth.py` (NumPy) | 65.6 s (88.0 s stereo WAV) | 1 run |

Notes:
- Text latency reflects a 30-character prompt on `gemini-3.5-flash` after `gemini-3.8-flash` and `gemini-3.7-flash` both returned HTTP 503 (see `FAIL-01`).
- Earlier Gemini audio narration hit strict free-tier daily/minute quotas (34 failed calls), which motivated switching primary narration to Addis AI (`EXP-03`).

---

## Measured cost

| Stage | Cost basis | Measured cost |
|---|---|---|
| Narration (Addis AI) | Free tier / trial credits | $0.00 |
| Keyframes (Cloudflare) | Free daily neuron allowance | $0.00 |
| Music (local NumPy synth) | Local CPU execution | $0.00 |
| Assembly (FFmpeg + Pillow) | Local CPU execution | $0.00 |
| Text (Gemini smoke test) | Free tier | $0.00 |
| **Total** | | **$0.00** |

---

## List-price equivalents

| Stage | Provider | Unit | List price | Date checked |
|---|---|---|---|---|
| Keyframes | Cloudflare Workers AI (FLUX.1 schnell) | per 1024x1024 image at 4 steps | $0.00063 ($0.0000528 per 512x512 tile + $0.0001056 per step) | 2026-11-26 |
| Narration (TTS) | Addis AI | per generated audio minute / credit | Billed via Addis AI credit packs; check account dashboard (`addis.voice.estimate` logs per-request usage) | 2026-11-26 |
| Text | Google (Gemini 3.5 Flash) | per 1M input/output tokens | Free tier ($0.00); check Google AI Studio pricing page for paid-tier token rates | 2026-11-26 |
| Music & Assembly (local) | Local Python + FFmpeg | per render | $0.00 (commodity CPU compute) | 2026-11-26 |

**Pricing sources:**
- Cloudflare Workers AI pricing page
- Addis AI account dashboard & `addis.voice.estimate(...)`
- Google AI / Gemini API pricing page

---

## Assumptions and caveats

- Free-tier availability and rate limits are subject to change; measured latencies were taken under free-tier conditions and may not reflect paid-tier throughput.
- List-price equivalents exclude retries, failed requests, and local storage/egress.
