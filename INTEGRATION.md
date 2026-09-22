# Image Lane — Integration Spec (for Pentagon AI Studio)

Consolidated handoff for the **Image** engine of Pentagon AI Studio (`ai.pentagon.games`).
Self-hosted on our own AWS GPUs. Model: **Qwen-Image-Edit** (Apache-2.0). No third-party image API in the path.

Repo: https://github.com/blockchainsuperheroes/imgen-api

| | Service | Status | Base URL |
|---|---|---|---|
| 1 | **Remix** — owned image → derivative | **LIVE** | `https://imgen.pentagon.games` |
| 2 | **Verify** — on-brand + SFW compare | code-ready, **deploy on pilot start** | TBD (`https://verify.imgen.pentagon.games` proposed) |

Auth on both: `x-api-key: <key>` header. Keys are per-consumer (a dedicated **studio-worker** key is issued by nftprof — do not share across consumers).

---

## 1) Remix — `POST /v1/edit` (async: submit → poll)

Turn a holder's owned character image into a derivative (restyle / add accessory / new scene).

**Submit** — `multipart/form-data`:
| field | req | default | notes |
|---|---|---|---|
| `prompt` | ✅ | — | curated template prompt |
| `image` \| `image_url` | ✅ (one) | — | source (upload or URL) |
| `negative_prompt` | | `blurry, low quality, deformed` | |
| `steps` | | `35` | 20 ≈ ~100s (faster, minor quality cost) |
| `cfg` | | `4.0` | |
| `seed` | | `7` | fix for reproducibility |

```
POST /v1/edit         → 200 { "job_id":"...", "status":"queued", "result_url":"/v1/result/{id}" }
GET  /v1/result/{id}  → 202 { "status":"queued|processing" }     (poll ~every 10s)
                      → 200 image/png                             (done)
                      → 404 unknown job_id · 500 generation failed
GET  /health          → { "status":"ok", "mode":"async" }
```
- **Latency ~100–170 s/image** (35 steps). Async, so no long-held connection / no client-timeout issues.
- **Concurrency = 1 per box** (GPU serial). Scale throughput by running N boxes behind your queue → linear.

## 2) Verify — `POST /v1/verify` (sync) — the universal gate

Score a **candidate** vs a **source**: on-brand? + SFW? Gate EVERY output (images **and** Wan video frames) before delivery.

`multipart/form-data`: `source`|`source_url` + `candidate`|`candidate_url`.
```json
{ "on_brand": {"identity_similarity":0.91,"style_similarity":0.88,"same_character":true,"on_style":true,"score":0.90},
  "sfw":      {"safe":true,"nsfw_score":0.01},
  "verdict":  "pass" }          // pass | review | fail
```
- **verdict:** `pass` (same character + on-style + SFW) · `review` (borderline identity → human) · `fail` (not SFW, or clearly a different character).
- Models: **DINOv2** (identity) + **CLIP** (style) + **Falconsai/nsfw_image_detection** (SFW). Tiny (~1.3 GB) → CPU or a small GPU. ~1–2 s/call, ~$0.001 each.
- Thresholds env-tunable per collection: `IDENTITY_SAME`, `STYLE_OK`, `NSFW_MAX`.
- **Kids lane (Ether Family): the SFW gate is mandatory-before-delivery.**

---

## Integration pattern (your S3 job-queue worker)

```
holder request → enqueue job (S3)
worker claims job → POST /v1/edit → poll /v1/result/{id} → PNG
   → POST /v1/verify(source=canon art, candidate=PNG)
       verdict==pass → upload PNG to CDN out-prefix, mark done
       verdict==review → hold for human
       verdict==fail  → discard + retry/adjust (never deliver)
```
This also gates **video**: send `source` = canon art, `candidate` = a sampled frame of a Wan clip.

## Economics (for pricing)
- **~$0.10–0.12 / image** at full utilization on one g6e.4xlarge (L40S 48 GB), 35 steps; **~$0.07** at 20 steps; spot ≈ −40%. On the AWS grant, marginal ≈ $0 until credits run out.
- **Real cost driver at low volume:** a persistent GPU box is **~$60–72/day idle**. Prefer batch-drain + stop-when-idle (your S3 queue fits this) or autoscale — don't leave a box hot for trickle traffic.
- **Verify** cost is negligible — gate freely.

## Identity guidance (important)
- **Pure AI editing can drift** (it humanized a stylized NFT in testing). For **exact identity**, use the **canon 2D dex art** as reference + our video LoRAs; for **PFP-style stills**, use the **layer-composite** lane (rebuild from the character's trait layers — identity guaranteed). Reserve `/v1/edit` for restyles / novel elements where some reinterpretation is acceptable — and always run `/v1/verify` after.

## Scope boundary
This lane is **image-only** (remix + on-brand/SFW compare). Video generation, pet video-LoRA training, voice/singing/music are other Studio lanes — not this service.

## Open items (owner-gated)
1. **Studio-worker API key** — issued by nftprof (not peer-to-peer).
2. **Verify endpoint deploy** — stand up on pilot start (ping the ImGen session).
