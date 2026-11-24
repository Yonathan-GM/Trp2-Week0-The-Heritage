"""Stage: keyframes. One PNG per shot via Cloudflare Workers AI (FLUX), cached by hash.

The prompt for every shot = image_prompt + character descriptions + style_block,
so the look stays fixed and only the shot content changes.
"""
import base64

import requests

from common import OUT, cached_output, content_hash, env
from validate import load

MODEL = "@cf/black-forest-labs/flux-1-schnell"
STEPS = 4


def build_prompt(sb, shot):
    chars = {c["id"]: c["description"] for c in sb["characters"]}
    who = " ".join(chars[c] for c in shot.get("characters", []))
    return f"{shot['image_prompt']} {who} {sb['style']['style_block']}".strip()


def generate(prompt, seed, out_path):
    url = (f"https://api.cloudflare.com/client/v4/accounts/{env('CLOUDFLARE_ACCOUNT_ID')}"
           f"/ai/run/{MODEL}")
    r = requests.post(url, headers={"Authorization": f"Bearer {env('CLOUDFLARE_API_TOKEN')}"},
                      timeout=180, json={"prompt": prompt, "steps": STEPS, "seed": seed})
    r.raise_for_status()
    out_path.write_bytes(base64.b64decode(r.json()["result"]["image"]))


def main():
    sb = load()
    for shot in sb["shots"]:
        prompt = build_prompt(sb, shot)
        seed = shot.get("seed", sb["style"].get("seed", 0))
        key = content_hash(MODEL, STEPS, prompt, seed)
        out = OUT / "keyframes" / f"{shot['id']}.png"
        _, hit = cached_output("keyframes", key, out,
                               lambda p, pr=prompt, sd=seed: generate(pr, sd, p),
                               MODEL, {"shot": shot["id"], "steps": STEPS, "prompt": prompt}, seed=seed)
        print(f"{shot['id']}: {'cached' if hit else 'generated'}")


if __name__ == "__main__":
    main()
