#!/usr/bin/env bash
# Pentagon Games Image Remix API — curl example (async: submit, then poll).
#   IMGEN_KEY=ef_xxx ./remix.sh my_pet.png "make it a knight in golden armor"
set -euo pipefail
: "${IMGEN_KEY:?export IMGEN_KEY=ef_...}"
BASE="${IMGEN_BASE:-https://imgen.pentagon.games}"
IMAGE="$1"; PROMPT="$2"; OUT="${3:-derivative.png}"

# 1) submit the job -> job_id
JOB=$(curl -s -X POST "$BASE/v1/edit" \
  -H "x-api-key: $IMGEN_KEY" \
  -F "image=@$IMAGE" \
  -F "prompt=$PROMPT, keep it a creature with its animal head and body, not human" \
  -F "negative_prompt=blurry, low quality, deformed, human face, human person" \
  -F "steps=35" \
  | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)
echo "job $JOB"

# 2) poll until the PNG comes back (curl -f fails on the 202-not-ready responses, so we loop)
until curl -sf -o "$OUT" -H "x-api-key: $IMGEN_KEY" "$BASE/v1/result/$JOB"; do
  echo "...still generating"; sleep 10
done
echo "saved $OUT"

# Submit from a URL instead of a local file: replace -F "image=@$IMAGE" with:
#   -F "image_url=https://your.cdn/pet.png"
