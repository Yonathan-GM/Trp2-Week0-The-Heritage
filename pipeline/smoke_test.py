"""Call each provider once and log latency to runs.jsonl.

Tells you today which free tiers actually work from your account.
Failures are logged and reported, not fatal, so you see every provider's status.
"""
import base64
import sys
import time

import requests

from common import env, log_run


def gemini_text():
    from common import gemini_text as call
    t0 = time.time()
    model, _ = call("Reply with the single word: ok")
    return model, time.time() - t0


def gemini_tts():
    key = env("GEMINI_API_KEY")
    model = "gemini-3.8-flash-tts"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    t0 = time.time()
    r = requests.post(url, headers={"x-goog-api-key": key}, timeout=120, json={
    "contents": [{"parts": [{"text": "Say calmly: hello"}]}],
    "generationConfig": {"responseModalities": ["AUDIO"]},
})
    r.raise_for_status()
    part = r.json()["candidates"][0]["content"]["parts"][0]
    assert "inlineData" in part, "no audio returned"
    base64.b64decode(part["inlineData"]["data"])
    return model, time.time() - t0


def cloudflare_image():
    acct, token = env("CLOUDFLARE_ACCOUNT_ID"), env("CLOUDFLARE_API_TOKEN")
    model = "@cf/black-forest-labs/flux-1-schnell"
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}"
    t0 = time.time()
    r = requests.post(url, headers={"Authorization": f"Bearer {token}"}, timeout=120,
                      json={"prompt": "a small clay teapot on a wooden table", "steps": 4})
    r.raise_for_status()
    return model, time.time() - t0


CHECKS = [("gemini_text", gemini_text), ("gemini_tts", gemini_tts), ("cloudflare_image", cloudflare_image)]


def main():
    failed = 0
    for name, fn in CHECKS:
        t0 = time.time()
        try:
            model, latency = fn()
            log_run("smoke", model, {"check": name}, latency_s=latency)
            print(f"[ok]   {name:18s} {latency:6.1f}s  ({model})")
        except Exception as e:  # noqa: BLE001
            failed += 1
            log_run("smoke", name, {"check": name}, latency_s=time.time() - t0,
                    ok=False, error=repr(e)[:300])
            print(f"[FAIL] {name:18s} {e!r}")
    print("\nKaggle/Colab (Wan 2.2, ACE-Step) cannot be smoke-tested from here: "
          "run notebooks/ by hand and note the result in FAILURES.md / COSTS.md.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
