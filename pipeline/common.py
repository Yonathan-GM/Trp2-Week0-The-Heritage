"""Shared helpers: runs.jsonl logging, content-hash caching, retries.

Every model call goes through `logged_call`, which writes one line to
runs.jsonl (stage, model, params, seed, latency, cost, cache status).
"""
import hashlib
import json
import os
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs.jsonl"
CACHE = ROOT / ".cache"
OUT = ROOT / "outputs"

load_dotenv(ROOT / ".env")


TEXT_MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"]


def env(name):
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Missing {name}. Copy .env.example to .env and fill it in.")
    return val


def content_hash(*parts):
    """Stable hash of everything that determines an output."""
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def log_run(stage, model, params, seed=None, latency_s=None, cost_usd=0.0,
            cache="miss", ok=True, error=None, gpu_minutes=None, output=None):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stage": stage,
        "model": model,
        "params": params,
        "seed": seed,
        "latency_s": None if latency_s is None else round(latency_s, 3),
        "cost_usd": cost_usd,
        "gpu_minutes": gpu_minutes,
        "cache": cache,
        "ok": ok,
        "error": error,
        "output": str(output) if output else None,
    }
    with RUNS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def retry(fn, attempts=3, base_delay=2.0, retry_on=(Exception,)):
    """Call fn(); retry with exponential backoff. Re-raises after the last attempt."""
    last = None
    for i in range(attempts):
        try:
            return fn()
        except retry_on as e:  # noqa: PERF203
            last = e
            if i < attempts - 1:
                time.sleep(base_delay * (2 ** i))
    raise last


def cached_output(stage, key, out_path, producer, model, params, seed=None, cost_usd=0.0):
    """Run `producer(out_path)` only if the content hash changed or the file is missing.

    The hash is stored in .cache/<stage>/<name>.hash next to nothing the grader
    needs to open; runs.jsonl records every hit and miss.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    marker = CACHE / stage / (out_path.name + ".hash")
    marker.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists() and marker.exists() and marker.read_text() == key:
        log_run(stage, model, params, seed=seed, latency_s=0.0, cost_usd=0.0,
                cache="hit", output=out_path)
        return out_path, True

    t0 = time.time()
    try:
        retry(lambda: producer(out_path))
    except Exception as e:
        log_run(stage, model, params, seed=seed, latency_s=time.time() - t0,
                ok=False, error=repr(e)[:300])
        raise
    log_run(stage, model, params, seed=seed, latency_s=time.time() - t0,
            cost_usd=cost_usd, cache="miss", output=out_path)
    marker.write_text(key)
    return out_path, False

import re
def redact(s):
    return re.sub(r"(key=|Bearer )[^&\s'\"]+", r"\1[REDACTED]", str(s))



def gemini_text(prompt, models=TEXT_MODELS):
    """Try each model in order; fall through on 429/5xx. Logs every attempt."""
    last = None
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        t0 = time.time()
        try:
            r = requests.post(url, headers={"x-goog-api-key": env("GEMINI_API_KEY")}, timeout=90,
                              json={"contents": [{"parts": [{"text": prompt}]}]})
            if r.status_code in (429, 500, 502, 503, 504):
                raise RuntimeError(f"{r.status_code} from {model}")
            r.raise_for_status()
            log_run("text", model, {"prompt_chars": len(prompt)}, latency_s=time.time() - t0)
            return model, r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:  # noqa: BLE001
            log_run("text", model, {"prompt_chars": len(prompt)}, latency_s=time.time() - t0,
                    ok=False, error=redact(repr(e))[:300])
            last = e
    raise last