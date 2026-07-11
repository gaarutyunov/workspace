#!/usr/bin/env bash
# Generate a pet-project app icon in the standard voxel style via OpenRouter.
# Usage: generate-icon.sh "<subject>" [output.png] [model]
#   e.g. generate-icon.sh "a bicycle" ./icon.png
# Requires: OPENROUTER_API_KEY, python3, curl.
set -euo pipefail

SUBJECT="${1:?usage: generate-icon.sh \"<subject>\" [output.png] [model]}"
OUT="${2:-icon.png}"
MODEL="${3:-google/gemini-3.1-flash-image}"

: "${OPENROUTER_API_KEY:?export OPENROUTER_API_KEY first}"

PROMPT="A minimalist 3D app icon featuring ${SUBJECT}. The entire icon is a square image with a black squared background. The subject is designed in a clean, blocky, 3D voxel art style, resembling Lego or pixelated blocks, and is made primarily of solid white material. The subject is shown from an isometric, slightly rotated 3D three-quarter perspective to show depth. Soft, clean 3D shadows and realistic lighting, matte finish, centered composition, high contrast."

BODY=$(python3 -c 'import json,sys; print(json.dumps({"model":sys.argv[2],"messages":[{"role":"user","content":sys.argv[1]}],"modalities":["image","text"]}))' "$PROMPT" "$MODEL")

# The model may return PNG or JPEG regardless of the requested name. Decode the
# raw bytes to a temp file (tagged with its real format), then always emit a PNG
# at $OUT so icons/favicons are lossless with a correct extension.
TMP=$(mktemp -t ga-icon)
FMT=$(curl -s "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer ${OPENROUTER_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$BODY" \
| python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
if 'error' in d:
    sys.exit('OpenRouter API error: ' + json.dumps(d['error'])[:800])
imgs = d['choices'][0]['message'].get('images') or []
if not imgs:
    sys.exit('No image in response: ' + json.dumps(d)[:800])
header, _, b64 = imgs[0]['image_url']['url'].partition(',')
open(sys.argv[1], 'wb').write(base64.b64decode(b64 or header))
mime = header.split(';')[0].split(':')[-1] if header.startswith('data:') else 'image/png'
print({'image/png':'png','image/jpeg':'jpeg','image/webp':'webp'}.get(mime,'png'))
" "$TMP")

if [ "$FMT" = "png" ]; then
  mv "$TMP" "$OUT"
elif command -v sips >/dev/null 2>&1; then
  sips -s format png "$TMP" --out "$OUT" >/dev/null && rm -f "$TMP"
elif python3 -c "import PIL" >/dev/null 2>&1; then
  python3 -c "from PIL import Image;import sys;Image.open(sys.argv[1]).save(sys.argv[2],'PNG')" "$TMP" "$OUT" && rm -f "$TMP"
else
  echo "warning: model returned $FMT and no converter (sips/Pillow) found; wrote raw bytes to $OUT" >&2
  mv "$TMP" "$OUT"
fi
echo "wrote $OUT (png, from $FMT)"
