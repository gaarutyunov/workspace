#!/usr/bin/env bash
# Generate a pet-project app icon in the standard voxel style via the Gemini image API.
# Usage: generate-icon.sh "<subject>" [output.png] [model]
#   e.g. generate-icon.sh "a bicycle" ./icon.png
# Requires: GEMINI_API_KEY, python3, curl.
set -euo pipefail

SUBJECT="${1:?usage: generate-icon.sh \"<subject>\" [output.png] [model]}"
OUT="${2:-icon.png}"
MODEL="${3:-gemini-3.1-flash-image}"

: "${GEMINI_API_KEY:?export GEMINI_API_KEY first}"

PROMPT="A minimalist 3D app icon featuring ${SUBJECT}. The entire icon is a square image with a black squared background. The subject is designed in a clean, blocky, 3D voxel art style, resembling Lego or pixelated blocks, and is made primarily of solid white material. The subject is shown from an isometric, slightly rotated 3D three-quarter perspective to show depth. Soft, clean 3D shadows and realistic lighting, matte finish, centered composition, high contrast."

BODY=$(python3 -c 'import json,sys; print(json.dumps({"contents":[{"parts":[{"text":sys.argv[1]}]}]}))' "$PROMPT")

curl -s "https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent" \
  -H "x-goog-api-key: ${GEMINI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$BODY" \
| python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
if 'candidates' not in d:
    sys.exit('Gemini API error: ' + json.dumps(d)[:800])
parts = d['candidates'][0]['content']['parts']
try:
    img = next(p['inlineData']['data'] for p in parts if 'inlineData' in p)
except StopIteration:
    sys.exit('No image in response: ' + json.dumps(d)[:800])
open(sys.argv[1], 'wb').write(base64.b64decode(img))
print('wrote', sys.argv[1])
" "$OUT"
