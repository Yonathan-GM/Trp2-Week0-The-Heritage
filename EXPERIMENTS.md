# EXP-01 — Latency of Each Model Call

**Question:** How long does each stage take to plan a one-day build?

**Setup:** The smoke test and the first real runs, each call logged in `runs.jsonl`.

**Result:**
- FLUX.1 schnell on Cloudflare: 2.1–3.5 s per image
- Gemini TTS: 3.2–5.5 s per call, limited to 10 requests per day per model (reset at 11:00 EAT)
- Gemini text call: 24.8 s

**Decision:** Keyframes can be regenerated freely, but narration edits were batched — part of why the voice was later moved to Addis AI (EXP-03).

---

# EXP-02 — Which Gemini Text Model to Use

**Question:** Which text model is dependable enough for the helper in `common.py`?

**Setup:** The same request sent to a chain of models in order.

**Result:**
- `gemini-3.8-flash` and `gemini-3.7-flash` returned HTTP 503
- `gemini-3.5-flash` answered in 24.8 s

**Decision:** `gemini_text` falls back in order **3.8 → 3.7 → 3.5 → 3.1-flash-lite**, and logs which model answered.

---

# EXP-03 — Narration Voice: Gemini TTS vs Addis AI (Amharic)

**Question:** Which service gives usable Amharic narration for a family audience?

**Setup:** The same 10 narration lines.

- **Gemini TTS:** 3.2–5.5 s per call, 10 free requests per day per model, style instructions are read aloud so STYLE had to stay empty, and clip ends needed automatic tail trimming.
- **Addis AI voice `am-yohanes-calm`:** 11 clips.

**Result:**
- With Addis, the automatic tail trimming removed 0 ms from all 11 clips (no scratches)
- Clip lengths: 3.5–8.5 s
- First sound starts 0.1 s into the file
- Judged the Addis voice clearer and more natural in Amharic

**Decision:** Use Addis AI. *<add what your relatives said about the voice after Test 1>*

---

# EXP-04 — Keeping the Grandmother Consistent Without a Seed

**Hypothesis:** Naming exact clothing details in the character description keeps her recognisable.

**Before:** "white cotton shawl with a coloured border" → dark brown border in s01, purple in s06.

**After:** "white cotton shawl with a dark brown woven border and fringe" → the same shawl in both pictures.

**Decision:** Every recurring character description names colours and materials explicitly.

---

# EXP-05 — Stopping the Model from Drawing a Sprout

**Before:** "kneeling and placing one last seed in the soil" → gave a green seedling.

**After:** "pressing one tiny seed into bare brown soil … no plant and no sprout anywhere, only bare earth" → gave bare soil with one seed.

**Decision:** The same phrase was added to s02 and s05.

---

# EXP-06 — Ken Burns Method: ffmpeg `zoompan` vs Pillow Sub-pixel Crops

**Method:** `experiments/kb_jitter.py` tracks an off-centre white disc through a 7 s, 8% zoom and measures the spread (standard deviation) of its second difference, in pixels. Smooth motion gives about 0.

**Result:**
| Method | Spread (px) | Max (px) |
|---|---|---|
| `zoompan` | 0.4517 | 0.8937 |
| Sub-pixel crops | 0.0268 | 0.1241 |

Sub-pixel crops were about **17× smoother**.

**Decision:** Sub-pixel crops are the default for still shots.

---

# EXP-07 — 16:9 Framing: Fill vs Show-Everything

**Observation:** Filling a 16:9 frame from a square keyframe cuts away 44% of the picture height.

**Decision:**
- **16:9:** Shows the whole picture on a blurred, darkened copy of itself.
- **9:16:** Keeps the fill because the subjects are centred (the keyframe prompt asks for a centred subject).

---

# EXP-08 — Ducking and Loudness on the First Draft

**Setup:** `sidechaincompress` threshold 0.02, ratio 6, attack 300 ms, release 1500 ms, then two-pass `loudnorm` to −14 LUFS / −1 dBTP, with a placeholder drone as the score.

**Result:**
- Mix measured **−18.3 LUFS** before and **−14.2 LUFS** after normalisation
- True peak: **−1.0 dBTP**

---

# EXP-09 — How Long a Shot Lasts When the Voice Is Long

**Rule:** A shot lasts the longer of its `duration_s` and the narration length plus 0.4 s.

**Result with Addis (radio cut):** Total **86.7 s** for 11 shots; only s04 overran (6.3 s of voice in a 6 s slot), so its `duration_s` was raised to 7.