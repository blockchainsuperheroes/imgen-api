"""Pentagon Games Image Remix API — async FastAPI server around Qwen-Image-Edit.

Submit a job (POST /v1/edit -> job_id), poll for the result (GET /v1/result/{id}).
Async so no request is held open for the ~100-170s generation.

Run:
    pip install "git+https://github.com/huggingface/diffusers" transformers accelerate \
                safetensors pillow sentencepiece fastapi "uvicorn[standard]" python-multipart
    export QWEN_API_KEY=ef_your_key
    uvicorn qwen_api:app --host 0.0.0.0 --port 8000

Needs a GPU (~48 GB via enable_model_cpu_offload()). Front it with Caddy/nginx for TLS.
"""
import os, io, threading, queue, uuid, urllib.request, torch
from fastapi import FastAPI, Header, HTTPException, UploadFile, File, Form
from fastapi.responses import Response, JSONResponse
from PIL import Image
from diffusers import QwenImageEditPipeline

API_KEY = os.environ.get("QWEN_API_KEY", "")

print("loading Qwen-Image-Edit ...", flush=True)
pipe = QwenImageEditPipeline.from_pretrained("Qwen/Qwen-Image-Edit", torch_dtype=torch.bfloat16)
pipe.enable_model_cpu_offload()
print("model ready", flush=True)

JOBS = {}                # job_id -> {"status": queued|processing|done|failed, "png"/"error"}
Q = queue.Queue()

def worker():
    while True:
        jid, img, prompt, neg, steps, cfg, seed = Q.get()
        JOBS[jid] = {"status": "processing"}
        try:
            out = pipe(image=img, prompt=prompt, negative_prompt=neg,
                       num_inference_steps=int(steps), true_cfg_scale=float(cfg),
                       generator=torch.manual_seed(int(seed))).images[0]
            b = io.BytesIO(); out.save(b, format="PNG")
            JOBS[jid] = {"status": "done", "png": b.getvalue()}
        except Exception as e:
            JOBS[jid] = {"status": "failed", "error": repr(e)[:300]}
        Q.task_done()

threading.Thread(target=worker, daemon=True).start()   # single GPU worker (serial)

app = FastAPI(title="Pentagon Games Image Remix API", version="0.2")

def check(k):
    if not API_KEY or k != API_KEY:
        raise HTTPException(status_code=401, detail="invalid or missing api key (x-api-key header)")

@app.get("/health")
def health():
    return {"status": "ok", "model": "Qwen-Image-Edit", "mode": "async"}

@app.post("/v1/edit")
def edit(prompt: str = Form(...),
         image: UploadFile = File(None), image_url: str = Form(None),
         negative_prompt: str = Form("blurry, low quality, deformed"),
         steps: int = Form(35), cfg: float = Form(4.0), seed: int = Form(7),
         x_api_key: str = Header(None)):
    check(x_api_key)
    if image is not None:
        raw = image.file.read()
    elif image_url:
        raw = urllib.request.urlopen(image_url, timeout=20).read()
    else:
        raise HTTPException(status_code=400, detail="provide 'image' file or 'image_url'")
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    jid = uuid.uuid4().hex
    JOBS[jid] = {"status": "queued"}
    Q.put((jid, img, prompt, negative_prompt, steps, cfg, seed))
    return {"job_id": jid, "status": "queued", "result_url": f"/v1/result/{jid}"}

@app.get("/v1/result/{jid}")
def result(jid: str, x_api_key: str = Header(None)):
    check(x_api_key)
    j = JOBS.get(jid)
    if not j:
        raise HTTPException(status_code=404, detail="unknown job_id")
    if j["status"] == "done":
        return Response(content=j["png"], media_type="image/png")
    if j["status"] == "failed":
        raise HTTPException(status_code=500, detail=j.get("error", "generation failed"))
    return JSONResponse(status_code=202, content={"status": j["status"]})
