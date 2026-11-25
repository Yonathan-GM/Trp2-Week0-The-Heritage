# FAILURES.md

Failure log for the story-to-video pipeline. All timestamps in the source log
(`runs.jsonl`) are UTC; local times below are Addis Ababa time (EAT, UTC+3).

Each entry records: what failed, the measured evidence, and what was done about
it. Speculation is labeled explicitly and is not presented as fact.

---

## FAIL-01 — Gemini 3.8 Flash returns 503 (service unavailable)

**Stage:** Text generation
**Status:** Resolved via fallback to `gemini-3.5-flash`
**Severity:** Medium (blocked text stage until fallback)

### Observed behavior

- `gemini-3.8-flash` returned HTTP 503 on **four separate runs** between
  **16:01 and 16:46 EAT**. It **never succeeded** — zero successful calls in
  the logged window.
- On the final run, the fallback model `gemini-3.7-flash` **also returned 503**,
  approximately **1 second after** the first failure. Both newer models were
  unavailable at that moment.
- `gemini-3.5-flash` **succeeded**, with a measured latency of **24.8 s** for a
  **30-character prompt**.

### Notes

- The 24.8 s latency is recorded as a **measured fact**. The cause was not
  determined. A plausible but **unverified** explanation is internal reasoning
  overhead; this is not asserted as the cause.

### Resolution

Fallback chain to `gemini-3.5-flash` succeeded and produced the required text.
Evidence retained at lines 10 and 13 of `runs.jsonl`.

---

## FAIL-02 — 404 on `gemini-3.8-flash-lite` (invalid model name)

**Stage:** Text generation
**Status:** Resolved (model name corrected)
**Severity:** Low (configuration error, not a service fault)

### Observed behavior

- **Five runs** returned HTTP 404 for `gemini-3.8-flash-lite`.
- The model **has no text variant**, so the request could never succeed.

### Root cause

Incorrect model name supplied in the guidance used to configure the pipeline.
This was an input/configuration error, not a provider outage.

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