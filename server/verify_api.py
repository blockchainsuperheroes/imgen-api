"""Pentagon Games Image-Compare API — is a candidate on-brand vs a source, and is it SFW?

Self-hosted, small models (runs on CPU or a small GPU):
  - DINOv2  -> identity similarity (is it the SAME character as the source)
  - CLIP    -> style similarity (does it match the source's look/brand)
  - Falconsai/nsfw_image_detection -> SFW check

Synchronous (each call is ~1-2s), API-key auth. Pairs with the remix API in this repo.

Run:
    pip install fastapi "uvicorn[standard]" python-multipart pillow torch \
                transformers open_clip_torch
    export VERIFY_API_KEY=ef_your_key
    uvicorn verify_api:app --host 0.0.0.0 --port 8000
"""
import os, io, urllib.request, torch
from fastapi import FastAPI, Header, HTTPException, UploadFile, File, Form
from PIL import Image
import torch.nn.functional as F
from transformers import (AutoImageProcessor, AutoModel,
                          CLIPProcessor, CLIPModel,
                          AutoModelForImageClassification)

API_KEY = os.environ.get("VERIFY_API_KEY", "")
DEV = "cuda" if torch.cuda.is_available() else "cpu"

# thresholds (tune per collection)
IDENTITY_SAME = float(os.environ.get("IDENTITY_SAME", "0.85"))   # DINOv2 cosine >= this => same character
STYLE_OK      = float(os.environ.get("STYLE_OK", "0.80"))        # CLIP cosine >= this => on-style
NSFW_MAX      = float(os.environ.get("NSFW_MAX", "0.50"))        # nsfw prob >= this => unsafe

print("loading verify models ...", flush=True)
dino_proc  = AutoImageProcessor.from_pretrained("facebook/dinov2-base")
dino_model = AutoModel.from_pretrained("facebook/dinov2-base").to(DEV).eval()
clip_proc  = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(DEV).eval()
nsfw_proc  = AutoImageProcessor.from_pretrained("Falconsai/nsfw_image_detection")
nsfw_model = AutoModelForImageClassification.from_pretrained("Falconsai/nsfw_image_detection").to(DEV).eval()
print("verify models ready", flush=True)

@torch.no_grad()
def dino_emb(img):
    x = dino_proc(images=img, return_tensors="pt").to(DEV)
    out = dino_model(**x).last_hidden_state[:, 0]          # CLS token
    return F.normalize(out, dim=-1)

@torch.no_grad()
def clip_emb(img):
    x = clip_proc(images=img, return_tensors="pt").to(DEV)
    return F.normalize(clip_model.get_image_features(**x), dim=-1)

@torch.no_grad()
def nsfw_prob(img):
    x = nsfw_proc(images=img, return_tensors="pt").to(DEV)
    logits = nsfw_model(**x).logits
    probs = logits.softmax(-1)[0]
    id2label = nsfw_model.config.id2label
    return float(sum(probs[i] for i, l in id2label.items() if l.lower() == "nsfw"))

def cos(a, b): return float((a * b).sum().clamp(-1, 1))

app = FastAPI(title="Pentagon Games Image-Compare API", version="0.1")

def check(k):
    if not API_KEY or k != API_KEY:
        raise HTTPException(status_code=401, detail="invalid or missing api key (x-api-key header)")

def load(file, url):
    if file is not None: raw = file.file.read()
    elif url: raw = urllib.request.urlopen(url, timeout=20).read()
    else: raise HTTPException(status_code=400, detail="provide the image as a file or a *_url")
    return Image.open(io.BytesIO(raw)).convert("RGB")

@app.get("/health")
def health():
    return {"status": "ok", "service": "image-compare", "device": DEV}

@app.post("/v1/verify")
def verify(source: UploadFile = File(None), source_url: str = Form(None),
           candidate: UploadFile = File(None), candidate_url: str = Form(None),
           x_api_key: str = Header(None)):
    check(x_api_key)
    src = load(source, source_url)
    cand = load(candidate, candidate_url)

    identity = cos(dino_emb(src), dino_emb(cand))     # same character?
    style    = cos(clip_emb(src), clip_emb(cand))     # same look/brand?
    nsfw     = nsfw_prob(cand)                         # candidate only

    same_character = identity >= IDENTITY_SAME
    on_style = style >= STYLE_OK
    safe = nsfw < NSFW_MAX
    on_brand_score = round(0.7 * identity + 0.3 * style, 4)

    if not safe:
        verdict = "fail"
    elif same_character and on_style:
        verdict = "pass"
    elif identity < 0.65:
        verdict = "fail"           # clearly a different character
    else:
        verdict = "review"         # borderline — send to a human

    return {
        "on_brand": {
            "identity_similarity": round(identity, 4),
            "style_similarity": round(style, 4),
            "same_character": same_character,
            "on_style": on_style,
            "score": on_brand_score,
        },
        "sfw": {"safe": safe, "nsfw_score": round(nsfw, 4)},
        "verdict": verdict,
        "thresholds": {"identity_same": IDENTITY_SAME, "style_ok": STYLE_OK, "nsfw_max": NSFW_MAX},
    }
