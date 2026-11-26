"""Stage: keyframes. One PNG per shot via Cloudflare Workers AI (FLUX schnell), cached by hash.

The prompt for every shot = image_prompt + character descriptions + framing hint + style_block,
so the look stays fixed and only the shot content changes.

Cloudflare's flux-1-schnell accepts only prompt and steps: a "seed" field is rejected with
error 5006 (tested 25 Nov 2026), so the look is held by the style block and character
descriptions alone, not by a fixed seed. There is also no width/height, so every
keyframe is a 1024x1024 square. assemble.py fits it to 9:16 / 16:9 with blurred fill when
cropping would remove too much of the image, which is why FRAMING asks for a centred subject.

Usage:
  python pipeline/keyframes.py              all shots (cached ones are skipped)
  python pipeline/keyframes.py s09 s06 s01  only these shots (check the look before spending quota)
"""
import base64
import io
import sys
import time

import requests
from PIL import Image

from common import OUT, cached_output, content_hash, env
from validate import load

MODEL = "@cf/black-forest-labs/flux-1-schnell"
STEPS = 4
FRAMING = "subject centred in the middle of the frame"


def build_prompt(sb, shot):
    chars = {c["id"]: c["description"] for c in sb["characters"]}
    who = " ".join(chars[c] for c in shot.get("characters", []))
    parts = [shot["image_prompt"], who, FRAMING + ".", sb["style"]["style_block"]]
    return " ".join(p.strip() for p in parts if p.strip())


def generate(prompt, seed, out_path):
    url = (f"https://api.cloudflare.com/client/v4/accounts/{env('CLOUDFLARE_ACCOUNT_ID')}"
           f"/ai/run/{MODEL}")
    r = requests.post(url, headers={"Authorization": f"Bearer {env('CLOUDFLARE_API_TOKEN')}"},
                      timeout=180, json={"prompt": prompt, "steps": STEPS})  # the API rejects "seed" (error 5006)
    if r.status_code != 200:
        raise SystemExit(f"Cloudflare returned {r.status_code}: {r.text[:300]}\n"
                         f"(429 or a quota message means today's free allowance is used up.)")
    raw = base64.b64decode(r.json()["result"]["image"])
    # Cloudflare sends JPEG data; save a real PNG so the .png name is truthful.
    Image.open(io.BytesIO(raw)).convert("RGB").save(out_path, format="PNG")


def main():
    sb = load()
    wanted = set(sys.argv[1:])
    known = {s["id"] for s in sb["shots"]}
    if wanted - known:
        raise SystemExit(f"Unknown shot id(s): {sorted(wanted - known)}. Known: {sorted(known)}")
    (OUT / "keyframes").mkdir(parents=True, exist_ok=True)
    made = 0
    for shot in sb["shots"]:
        if wanted and shot["id"] not in wanted:
            continue
        prompt = build_prompt(sb, shot)
        seed = shot.get("seed", sb["style"].get("seed", 0))
        key = content_hash(MODEL, STEPS, prompt, seed)
        out = OUT / "keyframes" / f"{shot['id']}.png"
        _, hit = cached_output("keyframes", key, out,
                               lambda p, pr=prompt, sd=seed: generate(pr, sd, p),
                               MODEL, {"shot": shot["id"], "steps": STEPS, "prompt": prompt}, seed=seed)
        print(f"{shot['id']}: {'cached' if hit else 'generated'}")
        if not hit:
            made += 1
            time.sleep(0.5)
    print(f"\n{made} image(s) generated this run (free daily allowance is limited).")


if __name__ == "__main__":
    main()