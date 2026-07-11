---
name: icon-generation
description: "Generate a minimalist 3D voxel app icon (white blocky subject on a black background) for a pet project via the Gemini image API/CLI. Use when asked to create/generate an app icon, project logo, or favicon in the standard style. Examples: \"generate an icon for the bikes app\", \"make an app icon of a guitar\", \"create the project icon\"."
---

# App icon generation

Generates the standard pet-project app icon: a **minimalist 3D voxel** subject in
solid white on a **black square** background, isometric three-quarter view. Uses
Google **Gemini's image model** (via API or CLI). The subject is supplied as the
argument (e.g. "a bicycle", "a guitar", "a pair of dumbbells").

## The fixed prompt

Substitute the subject for `{ARGUMENT}` and send this **verbatim** — the wording
is what produces the consistent house style; do not paraphrase it:

```
A minimalist 3D app icon featuring {ARGUMENT}. The entire icon is a square image with a black squared background. The subject is designed in a clean, blocky, 3D voxel art style, resembling Lego or pixelated blocks, and is made primarily of solid white material. The subject is shown from an isometric, slightly rotated 3D three-quarter perspective to show depth. Soft, clean 3D shadows and realistic lighting, matte finish, centered composition, high contrast.
```

## Prerequisites

- `GEMINI_API_KEY` exported (a Google AI Studio / Gemini API key).
- An image-capable Gemini model — currently `gemini-3.1-flash-image` (the 2.5
  image model is old). If a newer image model is current, prefer it and pass it
  as the 3rd script arg.
- No `gemini` CLI is installed here — use the REST API via `curl`. If the
  `@google/gemini-cli` is installed, its image flow works too, but the REST
  call below is the reliable default.

## Generate (REST API)

Use the bundled script:

```bash
.claude/skills/icon-generation/scripts/generate-icon.sh "a bicycle" ./icon.png
```

Or inline:

```bash
SUBJECT="a bicycle"
OUT="icon.png"
PROMPT="A minimalist 3D app icon featuring ${SUBJECT}. The entire icon is a square image with a black squared background. The subject is designed in a clean, blocky, 3D voxel art style, resembling Lego or pixelated blocks, and is made primarily of solid white material. The subject is shown from an isometric, slightly rotated 3D three-quarter perspective to show depth. Soft, clean 3D shadows and realistic lighting, matte finish, centered composition, high contrast."

curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c 'import json,sys; print(json.dumps({"contents":[{"parts":[{"text":sys.argv[1]}]}]}))' "$PROMPT")" \
  | python3 -c "import sys,json,base64; \
d=json.load(sys.stdin); \
parts=d['candidates'][0]['content']['parts']; \
img=next(p['inlineData']['data'] for p in parts if 'inlineData' in p); \
open(sys.argv[1],'wb').write(base64.b64decode(img)); \
print('wrote',sys.argv[1])" "$OUT"
```

## After generating

- Review the image; regenerate if the subject isn't clearly readable at small
  sizes (the icon must work as a favicon).
- Save it into the project (e.g. `favicon.png` / `public/icon.png`) per that
  repo's convention.
- For a favicon, also produce the sizes the site needs (e.g. via `sips` on
  macOS: `sips -z 32 32 icon.png --out favicon-32.png`).

## Notes

- Keep the subject phrase short and concrete ("a guitar", not a long sentence) —
  everything else in the prompt is fixed style.
- The style intentionally matches across all pet-project icons; do not alter the
  background, palette, or perspective wording.
