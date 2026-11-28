"""Shared helpers: runs.jsonl logging, content-hash caching, retries, and redaction.

Every model call goes through `log_run` or `cached_output`, writing one JSON line
to runs.jsonl (stage, model, params, seed, latency, cost, cache status).
"""
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs.jsonl"
CACHE = ROOT / ".cache"
OUT = ROOT / "outputs"

load_dotenv(ROOT / ".env")

TEXT_MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"]

_REDACT_PATTERNS = [
    (re.compile(r"(key=|Bearer\s+|x-goog-api-key[\"']?\s*[:=]\s*[\"']?)[^&\s'\"]+", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{12,}"), "[REDACTED_KEY]"),
    (re.compile(r"\bsk-[0-9A-Za-z]{12,}"), "[REDACTED_KEY]"),
]


def env(name: str) -> str:
    """Return required environment variable or raise an actionable error."""
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Missing {name}. Copy .env.example to .env and fill it in.")
    return val


def content_hash(*parts: Any) -> str:
    """Stable 16-char SHA-256 hex digest of everything that determines an output."""
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def redact(s: Any) -> str:
    """Mask API keys and bearer tokens before logging or displaying error messages."""
    text = str(s)
    for pattern, repl in _REDACT_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def log_run(
    stage: str,
    model: str,
    params: dict[str, Any],
    seed: int | None = None,
    latency_s: float | None = None,
    cost_usd: float = 0.0,
    cache: str = "miss",
    ok: bool = True,
    error: str | None = None,
    gpu_minutes: float | None = None,
    output: str | Path | None = None,
) -> dict[str, Any]:
    """Append one structured JSON execution record to runs.jsonl."""
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


def retry(
    fn: Callable[[], Any],
    attempts: int = 3,
    base_delay: float = 2.0,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> Any:
    """Call fn(); retry with exponential backoff. Re-raises after the last attempt."""
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    last: BaseException | None = None
    for i in range(attempts):
        try:
            return fn()
        except retry_on as e:  # noqa: PERF203
            last = e
            if i < attempts - 1:
                time.sleep(base_delay * (2 ** i))
    assert last is not None
    raise last


def cached_output(
    stage: str,
    key: str,
    out_path: str | Path,
    producer: Callable[[Path], Any],
    model: str,
    params: dict[str, Any],
    seed: int | None = None,
    cost_usd: float = 0.0,
) -> tuple[Path, bool]:
    """Run `producer(out_path)` only if the content hash changed or the file is missing.

    The hash is stored in .cache/<stage>/<name>.hash; runs.jsonl records every hit and miss.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    marker = CACHE / stage / (out_path.name + ".hash")
    marker.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists() and marker.exists() and marker.read_text(encoding="utf-8") == key:
        log_run(stage, model, params, seed=seed, latency_s=0.0, cost_usd=0.0,
                cache="hit", output=out_path)
        return out_path, True

    t0 = time.time()
    try:
        retry(lambda: producer(out_path))
    except Exception as e:
        log_run(stage, model, params, seed=seed, latency_s=time.time() - t0,
                ok=False, error=redact(repr(e))[:300])
        raise
    log_run(stage, model, params, seed=seed, latency_s=time.time() - t0,
            cost_usd=cost_usd, cache="miss", output=out_path)
    marker.write_text(key, encoding="utf-8")
    return out_path, False


def gemini_text(prompt: str, models: Iterable[str] = TEXT_MODELS) -> tuple[str, str]:
    """Try each model in order; fall through on 429/5xx. Logs every attempt."""
    last: BaseException | None = None
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        t0 = time.time()
        try:
            r = requests.post(
                url,
                headers={"x-goog-api-key": env("GEMINI_API_KEY")},
                timeout=90,
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            if r.status_code in (429, 500, 502, 503, 504):
                raise RuntimeError(f"{r.status_code} from {model}")
            r.raise_for_status()
            log_run("text", model, {"prompt_chars": len(prompt)}, latency_s=time.time() - t0)
            return model, r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:  # noqa: BLE001
            log_run(
                "text",
                model,
                {"prompt_chars": len(prompt)},
                latency_s=time.time() - t0,
                ok=False,
                error=redact(repr(e))[:300],
            )
            last = e
    if last is None:
        raise RuntimeError("No Gemini text models configured")
    raise last
