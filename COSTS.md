# COSTS.md

Cost and latency record for the story-to-video pipeline.

**Cost basis:** All stages below ran on **free tiers**; measured cost for this
project was **$0.00**. List-price equivalents are noted separately below and
must be re-checked before citing.

Latency figures are **measured** from the run log unless marked otherwise.

---

## Measured latency by stage

| Stage | Model / provider | Measured latency | Sample size |
|---|---|---|---|
| Narration | Gemini 3.8 Flash TTS | 3.2–5.5 s per short call | 8 successful runs |
| Keyframes | FLUX.1 schnell (Cloudflare) | 2.1–3.5 s per image | 8 successful runs |
| Text | Gemini 3.5 Flash | 24.8 s (after two 503s on newer models) | 1 successful run |

Notes:
- Text latency reflects a 30-character prompt on `gemini-3.5-flash` after
  `gemini-3.8-flash` and `gemini-3.7-flash` both returned 503. See FAIL-01.
- Narration and keyframe latencies are per-call/per-image for short inputs.

---

## Measured cost

| Stage | Cost basis | Measured cost |
|---|---|---|
| Narration | Free tier | $0.00 |
| Keyframes | Free tier | $0.00 |
| Text | Free tier | $0.00 |
| **Total** | | **$0.00** |

---

## List-price equivalents (to be completed)

List prices below are **not yet verified**. Fill in from each provider's public
pricing page and record the date checked. Do not cite these figures until the
date is recorded.

| Stage | Provider | Unit | List price | Date checked |
|---|---|---|---|---|
| Narration (TTS) | Google (Gemini) | per 1M characters | [TBD] | [YYYY-MM-DD] |
| Keyframes | Cloudflare (FLUX.1 schnell) | per image | [TBD] | [YYYY-MM-DD] |
| Text | Google (Gemini 3.5 Flash) | per 1M input/output tokens | [TBD] | [YYYY-MM-DD] |

**Pricing sources to check:**
- Google AI / Gemini API pricing page
- Cloudflare Workers AI pricing page

---

## Assumptions and caveats

- Free-tier availability and rate limits are subject to change; measured
  latencies were taken under free-tier conditions and may not reflect paid-tier
  performance.
- List-price equivalents are indicative only and exclude retries, failed
  requests, and storage/egress.