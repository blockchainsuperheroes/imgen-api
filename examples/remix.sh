#!/usr/bin/env bash
# Pentagon Games Image Remix API — curl example.
#   IMGEN_KEY=ef_xxx ./remix.sh my_pet.png "make it a knight in golden armor"
set -euo pipefail
: "${IMGEN_KEY:?export IMGEN_KEY=ef_...}"
BASE="${IMGEN_BASE:-https://imgen.pentagon.games}"
IMAGE="$1"; PROMPT="$2"; OUT="${3:-derivative.png}"

curl -sS -X POST "$BASE/v1/edit" \
  -H "x-api-key: $IMGEN_KEY" \
  -F "image=@$IMAGE" \
  -F "prompt=$PROMPT, keep it a creature with its animal head and body, not human" \
  -F "negative_prompt=blurry, low quality, deformed, human face, human person" \
  -F "steps=35" -F "cfg=4.0" -F "seed=7" \
  -o "$OUT" -w "http %{http_code}, %{size_download} bytes -> $OUT\n"

# Health check:
#   curl -s "$BASE/health"
#
# Remix from a URL instead of a local file:
#   curl -sS -X POST "$BASE/v1/edit" -H "x-api-key: $IMGEN_KEY" \
#     -F "image_url=https://your.cdn/pet.png" -F "prompt=..." -o out.png
