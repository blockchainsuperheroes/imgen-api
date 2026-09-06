#!/usr/bin/env bash
# Image-compare: is CANDIDATE on-brand vs SOURCE, and is it SFW?
#   VERIFY_KEY=ef_xxx ./verify.sh source.png candidate.png
set -euo pipefail
: "${VERIFY_KEY:?export VERIFY_KEY=ef_...}"
BASE="${VERIFY_BASE:-https://verify.imgen.pentagon.games}"   # or the host you deploy verify_api to
SRC="$1"; CAND="$2"

curl -sS -X POST "$BASE/v1/verify" \
  -H "x-api-key: $VERIFY_KEY" \
  -F "source=@$SRC" \
  -F "candidate=@$CAND"
echo

# Or by URL:
#   curl -sS -X POST "$BASE/v1/verify" -H "x-api-key: $VERIFY_KEY" \
#     -F "source_url=https://.../nft.png" -F "candidate_url=https://.../generated.png"
#
# verdict: "pass" | "review" | "fail"
#   pass   -> same character + on-style + SFW
#   review -> borderline identity, send to a human
#   fail   -> not SFW, or clearly a different character
