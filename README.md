# Pentagon Games — Image Remix API

Turn an image you own into an **identity-preserving derivative** — restyle it, re-costume it, or drop it into a new scene, while keeping the subject recognizable.

Powered by [Qwen-Image-Edit](https://huggingface.co/Qwen/Qwen-Image-Edit) (Apache-2.0), self-hosted on our own GPUs.

```
Base URL:  https://imgen.pentagon.games
Auth:      x-api-key: <YOUR_API_KEY>
```

> You need an API key to use this. Request one from the Pentagon Games team.

> ⏱️ **This is an async API.** You **submit a job** (`POST /v1/edit` → returns a `job_id` instantly) and
> then **poll for the result** (`GET /v1/result/{job_id}`). Generation takes ~100–170 s; polling every
> ~10 s means no long-held connection and no client-timeout pitfalls. See [How it works](#how-it-works).

---

## Example

| Input | → Knight | → Plush | → Cyberpunk |
|---|---|---|---|
| ![input](examples/sample_input.png) | ![knight](examples/sample_knight.png) | ![plush](examples/sample_plush.png) | ![cyberpunk](examples/sample_cyberpunk.png) |

Same creature — face, ears, markings, colors preserved — across three very different transformations.

---

## How it works

```
1. POST /v1/edit         → { "job_id": "...", "status": "queued", "result_url": "/v1/result/<id>" }
2. GET  /v1/result/<id>  → 202 { "status": "processing" }   (keep polling, ~10s)
                         → 200 image/png                     (done — the derivative)
                         → 500 { "detail": "..." }           (generation failed)
```

## Endpoints

### `GET /health`
No auth. Liveness check → `{ "status": "ok", "model": "Qwen-Image-Edit", "mode": "async" }`

### `POST /v1/edit`  — submit a job
Auth required (`x-api-key` header). `multipart/form-data`. Returns immediately with a `job_id`.

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `prompt` | string | ✅ | — | What to make. Be explicit about *keeping identity*. |
| `image` | file | one of | — | The source image (upload). |
| `image_url` | string | one of | — | …or a URL to fetch the source image from. |
| `negative_prompt` | string | | `blurry, low quality, deformed` | What to avoid. |
| `steps` | int | | `35` | Denoising steps. Higher = slower, more refined. |
| `cfg` | float | | `4.0` | Guidance strength. |
| `seed` | int | | `7` | Fix for reproducible output. |

**Returns:** `{ "job_id", "status": "queued", "result_url" }`. Provide **either** `image` **or** `image_url`.

### `GET /v1/result/{job_id}`  — fetch the result
Auth required. Poll this until it returns the image.
- **200** `image/png` — the finished derivative
- **202** `{ "status": "queued" | "processing" }` — not ready, poll again
- **404** unknown `job_id` · **500** generation failed

---

## Quick start

**curl** (submit, then poll)
```bash
# 1) submit
JOB=$(curl -s -X POST https://imgen.pentagon.games/v1/edit \
  -H "x-api-key: $IMGEN_KEY" \
  -F "image=@my_pet.png" \
  -F "prompt=turn this creature into a heroic knight in golden armor, keep it a creature with its animal head, ears and colors" \
  | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)

# 2) poll until the PNG comes back (202 = still working)
until curl -sf -o derivative.png \
  -H "x-api-key: $IMGEN_KEY" \
  https://imgen.pentagon.games/v1/result/$JOB; do sleep 10; done
echo "saved derivative.png"
```

**Python** — see [`examples/remix.py`](examples/remix.py)
**Node.js** — see [`examples/remix.js`](examples/remix.js)
**Bash** — see [`examples/remix.sh`](examples/remix.sh)

---

## Prompting tips

The model follows your prompt literally, so a few words change the outcome:

- **Keep it a creature.** "Knight" alone can *humanize* an animal subject. Add
  `keep it a creature with its animal head and body, anthropomorphic, not human`
  and put `human face, human person` in `negative_prompt`.
- **Name what to preserve.** "keep its face, ears, colors and markings" anchors identity.
- **Two remix styles:**
  - *Instruction edit* — "put it in armor", "make it a plush toy" (preserves the subject).
  - *Restyle* — "in a neon cyberpunk city", "watercolor storybook style" (keeps subject, changes world/look).
- **Reproducibility:** fix `seed` to get the same result for the same input+prompt.

---

## Latency & polling

- **~100–170 s per image.** The model is 20B params at ~35 steps; this is compute time.
- **Poll `/v1/result/{job_id}` every ~10 s.** Each call is instant — because the work is async, there's no
  long-held connection, so ordinary client defaults are fine (no need for special timeouts).
- **Go faster with fewer steps:** `steps=20` ≈ ~100 s (minor quality cost); `steps=35` (default) = highest quality.
- **One at a time.** A single GPU processes jobs serially — extra jobs queue (their `job_id` stays `queued` until picked up).

## Notes & limits

- **You must have rights to the input image.** This API creates derivatives of whatever you send it — send only images you own or are licensed to modify.
- **Model:** Qwen-Image-Edit, Apache-2.0. Self-hosted; no third-party image API in the path.

## Self-hosting

The server is a small FastAPI app around `diffusers`. See [`server/qwen_api.py`](server/qwen_api.py) and [`server/README.md`](server/README.md) to run your own instance.
