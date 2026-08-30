#!/usr/bin/env python3
"""Pentagon Games Image Remix API — Python example.

    pip install requests
    IMGEN_KEY=ef_xxx python remix.py my_pet.png "make it a knight in golden armor"
"""
import os, sys, requests

BASE = os.environ.get("IMGEN_BASE", "https://imgen.pentagon.games")
KEY  = os.environ["IMGEN_KEY"]  # export IMGEN_KEY=ef_...

def remix(image_path, prompt, out="derivative.png", **params):
    with open(image_path, "rb") as f:
        r = requests.post(
            f"{BASE}/v1/edit",
            headers={"x-api-key": KEY},
            files={"image": f},
            data={"prompt": prompt, **params},
            timeout=300,
        )
    r.raise_for_status()
    with open(out, "wb") as g:
        g.write(r.content)
    print("saved", out)

def remix_url(image_url, prompt, out="derivative.png", **params):
    r = requests.post(
        f"{BASE}/v1/edit",
        headers={"x-api-key": KEY},
        data={"image_url": image_url, "prompt": prompt, **params},
        timeout=300,
    )
    r.raise_for_status()
    open(out, "wb").write(r.content)
    print("saved", out)

if __name__ == "__main__":
    img, prompt = sys.argv[1], sys.argv[2]
    # keep_creature guardrail baked into the example prompt
    remix(img, prompt + ", keep it a creature with its animal head and body, not human",
          negative_prompt="blurry, low quality, deformed, human face, human person",
          steps=35, cfg=4.0, seed=7)
