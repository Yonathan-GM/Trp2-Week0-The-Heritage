# FAILURES.md

Failure log for the story-to-video pipeline. All timestamps in the source log (`runs.jsonl`) are UTC; local times below are Addis Ababa time (EAT, UTC+3).

Each entry records: what failed, the measured evidence, and what was done about it. Speculation is labeled explicitly and is not presented as fact.

---

## FAIL-01 — Gemini 3.8 Flash returns 503 (service unavailable)

**Stage:** Text generation
**Status:** Resolved via fallback to `gemini-3.5-flash`
**Severity:** Medium (blocked text stage until fallback)

### Observed behavior

- `gemini-3.8-flash` returned HTTP 503 on **four separate runs** between **16:01 and 16:46 EAT**. It **never succeeded** — zero successful calls in the logged window.
- On the final run, the fallback model `gemini-3.7-flash` **also returned 503**, approximately **1 second after** the first failure. Both newer models were unavailable at that moment.
- `gemini-3.5-flash` **succeeded**, with a measured latency of **24.8 s** for a **30-character prompt**.

### Notes

- The 24.8 s latency is recorded as a **measured fact**. The cause was not determined. A plausible but **unverified** explanation is internal reasoning overhead; this is not asserted as the cause.

### Resolution

Fallback chain to `gemini-3.5-flash` succeeded and produced the required text. Evidence retained at lines 10 and 13 of `runs.jsonl`.

---

## FAIL-02 — 404 on `gemini-3.8-flash-lite` (invalid model name)

**Stage:** Text generation
**Status:** Resolved (model name corrected)
**Severity:** Low (configuration error, not a service fault)

### Observed behavior

- **Five runs** returned HTTP 404 for `gemini-3.8-flash-lite`.
- The model **has no text variant**, so the request could never succeed.

### Root cause

Incorrect model name supplied in the guidance used to configure the pipeline. This was an input/configuration error, not a provider outage.

### Resolution

Model name corrected; subsequent runs used a valid text model.

---

## FAIL-04 — `NameError` during pipeline runs

**Stage:** Pipeline execution
**Status:** Resolved
**Severity:** Low (code defect)

### Observed behavior

- `NameError` raised on **lines 4 and 7** of `runs.jsonl`.
- **Update 2026-11-25 11:40:** The fade-out alone did not remove the scratch at the end of each clip, so the artifact is inside the TTS output, not only at the join. Added automatic trimming of short bursts after a pause at the end of each clip, plus a per-clip tail loudness report to diagnose it.

### Notes

Recorded here for completeness; see the run log for the exact traceback.

---

## FAIL-10 — Cloudflare rejected the seed parameter

**What happened:** The first real keyframe call returned HTTP 400, error 5006: *"Additional or unevaluated properties '/seed'"*. The model's documentation example showed a seed, the live API did not accept it.

**Cause:** `@cf/black-forest-labs/flux-1-schnell` accepts only `prompt` and `steps`.

**Fix:** Removed the seed from the request. The look is now held by the shared style block and by very specific character descriptions (see EXP-04).

**Consequence:** Keyframes are not bit-for-bit reproducible; the cache is what keeps the film stable.

---

## FAIL-11 — A green sprout appeared in the "planting" shot

**What happened:** The first s06 keyframe showed a seedling in the soil while the story says she plants her last seed, which gave away the s08 payoff.

**Cause:** The model read "planting a seed" as "plant growing".

**Fix:** Prompts for s02, s05 and s06 now say *"bare soil, no plant or sprout visible"* (EXP-05).

---

## FAIL-12 — The grandmother's shawl changed colour between shots

**What happened:** The border was dark brown in s01 and purple in s06.

**Cause:** The character description said only *"a coloured border"*, so the model picked a colour each time.

**Fix:** The description now names the border (*"dark brown woven border and fringe"*).

---

## FAIL-13 — A torn-paper border and a faint signature

**What happened:** s06 came back with a white torn-paper edge and a scribble in the corner, which would show as a white line in the vertical crop.

**Cause:** FLUX schnell has no negative prompt, so *"no text"* in the style block did not stop it.

**Fix:** The shot prompt itself says *"full-bleed painting filling the entire frame, no border, no signature"*.

---

## FAIL-14 — The Ken Burns motion was visibly shaky

**What happened:** The first assembled draft jittered on every still shot.

**Cause:** ffmpeg's `zoompan` filter moves the crop in whole-pixel steps, which shows on a slow move over a small (1024 px) source.

**Fix:** Frames are now cropped with float coordinates in Pillow and piped to ffmpeg (EXP-06).

---

## FAIL-15 — The horizontal film cut off the top and bottom of every picture

**What happened:** The 16:9 export filled the frame from square keyframes, losing about 44% of the height.

**Cause:** One "cover" rule for both formats.

**Fix:** 9:16 fills the frame (subjects are centred); 16:9 shows the whole picture centred on a blurred copy of itself (EXP-07).

---

## FAIL-16 — The free GPU queue was too long to wait for

**What happened:** On 26 Nov the Kaggle notebook queue position was 111 on the day both submissions were due.

**Fix:** The pipeline was designed so Wan and ACE-Step are optional: shots fall back to Ken Burns and the score can be synthesised by `pipeline/music_synth.py`.

---

## FAIL-17 — A project line ended up inside Python's own library

**What happened:** `python` and `pip` stopped working: `Lib/pathlib/__init__.py` contained `from common import OUT, log_run`, pasted by mistake while a standard-library file was open in the editor.

**Fix:** Removed the line, then reinstalled Python; the project folder was not affected.

**Lesson:** Check the file tab path before pasting; use `python -m pip` so a broken launcher cannot hide the cause.

---

## FAIL-18 — The editor preview could not play the output

**What happened:** The radio-cut MP4 seemed silent in VS Code's preview.

**Cause:** The preview cannot play AAC audio.

**Fix:** Verify with VLC, and `radio_cut.py` now measures the loudness of the MP4 itself in 5 s windows instead of trusting a player.