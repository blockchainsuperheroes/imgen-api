"""Pentagon Games Image Remix API — FastAPI server around Qwen-Image-Edit.

Run:
    pip install "git+https://github.com/huggingface/diffusers" transformers accelerate \
                safetensors pillow sentencepiece fastapi "uvicorn[standard]" python-multipart
    export QWEN_API_KEY=ef_your_key
    uvicorn qwen_api:app --host 0.0.0.0 --port 8000

Needs a GPU. Qwen-Image-Edit is ~20B params; enable_model_cpu_offload() lets it run
on a 48 GB card (e.g. L40S) by keeping only the active module resident.
"""
import os, io, threading, urllib.request, torch
from fastapi import FastAPI, Header, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from PIL import Image
from diffusers import QwenImageEditPipeline

API_KEY = os.environ.get("QWEN_API_KEY", "")

print("loading Qwen-Image-Edit ...", flush=True)
pipe = QwenImageEditPipeline.from_pretrained("Qwen/Qwen-Image-Edit", torch_dtype=torch.bfloat16)
pipe.enable_model_cpu_offload()
LOCK = threading.Lock()  # serialize GPU access; one image at a time
print("model ready", flush=True)


def run_edit(img, prompt, neg, steps, cfg, seed):
    with LOCK:
        return pipe(
            image=img, prompt=prompt, negative_prompt=neg,
            num_inference_steps=int(steps), true_cfg_scale=float(cfg),
            generator=torch.manual_seed(int(seed)),
        ).images[0]


app = FastAPI(title="Pentagon Games Image Remix API", version="0.1")


def check(k):
    if not API_KEY or k != API_KEY:
        raise HTTPException(status_code=401, detail="invalid or missing api key (x-api-key header)")


@app.get("/health")
def health():
    return {"status": "ok", "model": "Qwen-Image-Edit"}


@app.post("/v1/edit")
def edit(
    prompt: str = Form(...),
    image: UploadFile = File(None),
    image_url: str = Form(None),
    negative_prompt: str = Form("blurry, low quality, deformed"),
    steps: int = Form(35), cfg: float = Form(4.0), seed: int = Form(7),
    x_api_key: str = Header(None),
):
    check(x_api_key)
    if image is not None:
        raw = image.file.read()
    elif image_url:
        raw = urllib.request.urlopen(image_url, timeout=20).read()
    else:
        raise HTTPException(status_code=400, detail="provide 'image' file or 'image_url'")
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    out = run_edit(img, prompt, negative_prompt, steps, cfg, seed)
    buf = io.BytesIO(); out.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")
