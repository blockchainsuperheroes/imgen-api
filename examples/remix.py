#!/usr/bin/env python3
"""Pentagon Games Image Remix API — Python example (async: submit a job, poll for the result).

    pip install requests
    IMGEN_KEY=ef_xxx python remix.py my_pet.png "make it a knight in golden armor"
"""
import os, sys, time, requests

BASE = os.environ.get("IMGEN_BASE", "https://imgen.pentagon.games")
KEY  = os.environ["IMGEN_KEY"]          # export IMGEN_KEY=ef_...
H    = {"x-api-key": KEY}

def remix(image_path, prompt, out="derivative.png", poll=10, **params):
    # 1) submit the job
    with open(image_path, "rb") as f:
        r = requests.post(f"{BASE}/v1/edit", headers=H,
                          files={"image": f}, data={"prompt": prompt, **params})
    r.raise_for_status()
    job = r.json()["job_id"]
    print("job", job)
    # 2) poll until the PNG is ready (202 = still working)
    while True:
        rr = requests.get(f"{BASE}/v1/result/{job}", headers=H)
        if rr.status_code == 200:
            with open(out, "wb") as g:
                g.write(rr.content)
            print("saved", out); return out
        if rr.status_code == 202:
            print("...", rr.json().get("status")); time.sleep(poll); continue
        rr.raise_for_status()   # 404/500

if __name__ == "__main__":
    img, prompt = sys.argv[1], sys.argv[2]
    # keep_creature guardrail baked into the example
    remix(img, prompt + ", keep it a creature with its animal head and body, not human",
          negative_prompt="blurry, low quality, deformed, human face, human person",
          steps=35, cfg=4.0, seed=7)
