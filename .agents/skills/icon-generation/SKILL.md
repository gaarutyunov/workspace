---
name: icon-generation
description: "Generate a minimalist 3D voxel app icon (white blocky subject on a black background) for a pet project via OpenRouter's image models. Use when asked to create/generate an app icon, project logo, or favicon in the standard style. Examples: \"generate an icon for the bikes app\", \"make an app icon of a guitar\", \"create the project icon\"."
---

# App icon generation

Generates the standard pet-project app icon: a **minimalist 3D voxel** subject in
solid white on a **black square** background, isometric three-quarter view. Uses
**OpenRouter's** image models (default `google/gemini-3.1-flash-image`). The
subject is supplied as the argument (e.g. "a bicycle", "a guitar", "a pair of
dumbbells").

## The fixed prompt

Substitute the subject for `{ARGUMENT}` and send this **verbatim** — the wording
is what produces the consistent house style; do not paraphrase it:

```
A minimalist 3D app icon featuring {ARGUMENT}. The entire icon is a square image with a black squared background. The subject is designed in a clean, blocky, 3D voxel art style, resembling Lego or pixelated blocks, and is made primarily of solid white material. The subject is shown from an isometric, slightly rotated 3D three-quarter perspective to show depth. Soft, clean 3D shadows and realistic lighting, matte finish, centered composition, high contrast.
```

## Prerequisites

- `OPENROUTER_API_KEY` exported (an [OpenRouter](https://openrouter.ai) key with
  credit — image models are paid).
- An image-output model. Default `google/gemini-3.1-flash-image`. Others with
  image output on OpenRouter include `google/gemini-3-pro-image`,
  `google/gemini-3.1-flash-lite-image`, and `openai/gpt-5-image`; pass one as
  the 3rd script arg. Confirm current availability at
  `https://openrouter.ai/api/v1/models` (filter `architecture.output_modalities`
  contains `image`).

## Generate (OpenRouter chat/completions)

OpenRouter returns images through the chat-completions endpoint: request
`modalities: ["image", "text"]`, then read the data-URL from
`choices[0].message.images[0].image_url.url`.

Use the bundled script:

```bash
.claude/skills/icon-generation/scripts/generate-icon.sh "a bicycle" ./icon.png
# 3rd arg overrides the model:
# .claude/skills/icon-generation/scripts/generate-icon.sh "a guitar" ./icon.png google/gemini-3-pro-image
```

> **Output is always PNG.** The image models return PNG *or* JPEG
> non-deterministically and there's no reliable request parameter to force the
> format, so the script converts anything non-PNG to PNG locally (via `sips` on
> macOS, or Pillow if present) and writes it at the path you gave. The inline
> `curl` example below writes the raw bytes as-is — use the script when you need
> a guaranteed `.png`.

Or inline:

```bash
SUBJECT="a bicycle"
OUT="icon.png"
MODEL="google/gemini-3.1-flash-image"
PROMPT="A minimalist 3D app icon featuring ${SUBJECT}. The entire icon is a square image with a black squared background. The subject is designed in a clean, blocky, 3D voxel art style, resembling Lego or pixelated blocks, and is made primarily of solid white material. The subject is shown from an isometric, slightly rotated 3D three-quarter perspective to show depth. Soft, clean 3D shadows and realistic lighting, matte finish, centered composition, high contrast."

curl -s "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c 'import json,sys; print(json.dumps({"model":sys.argv[2],"messages":[{"role":"user","content":sys.argv[1]}],"modalities":["image","text"]}))' "$PROMPT" "$MODEL")" \
  | python3 -c "import sys,json,base64; \
d=json.load(sys.stdin); \
url=d['choices'][0]['message']['images'][0]['image_url']['url']; \
open(sys.argv[1],'wb').write(base64.b64decode(url.split(',',1)[1])); \
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
