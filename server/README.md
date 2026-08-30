# Self-hosting

A minimal FastAPI wrapper around [Qwen-Image-Edit](https://huggingface.co/Qwen/Qwen-Image-Edit).

## Requirements
- One GPU with ~48 GB VRAM (e.g. NVIDIA L40S / A100). Smaller cards work with more offload / quantization.
- Python 3.10+, CUDA-enabled PyTorch.

## Run
```bash
pip install "git+https://github.com/huggingface/diffusers" transformers accelerate \
            safetensors pillow sentencepiece fastapi "uvicorn[standard]" python-multipart

export QWEN_API_KEY=ef_your_key           # clients send this as the x-api-key header
uvicorn qwen_api:app --host 0.0.0.0 --port 8000
```
First start downloads the model (~40 GB) from Hugging Face.

## HTTPS + custom domain (recommended)
Put [Caddy](https://caddyserver.com/) in front for automatic Let's Encrypt TLS:

```
# /etc/caddy/Caddyfile
imgen.example.com {
    reverse_proxy localhost:8000
}
```
Point `imgen.example.com`'s DNS at the server, then `caddy run`. Caddy provisions the
certificate automatically and terminates TLS, proxying to uvicorn on :8000.

## Notes
- A global lock serializes GPU work — one image at a time. For throughput, run several
  workers behind a queue/load balancer.
- Add rate-limiting, quotas, and an ownership check in front of `/v1/edit` before exposing it publicly.
