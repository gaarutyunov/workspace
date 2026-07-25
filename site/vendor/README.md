# Vendored UI kit

These files are the pinned standalone bundle of
[`@gaarutyunov/ui-kit`](https://github.com/gaarutyunov/ui-kit) — the same design
system that powers [garutyunov.com](https://garutyunov.com) and every pet
project. Vendoring the release assets keeps this landing **buildless and
self-contained**: no npm install, no CDN fetch at runtime, and a reproducible
deploy on GitHub Pages (including PR previews under `/pr-preview/pr-N/`).

| File | Source |
| --- | --- |
| `ga-ui-kit.css` | design tokens (palette, Geist typography, spacing, radii) |
| `ga-ui-kit.min.js` | all `<ga-*>` custom elements, self-registering |

**Pinned version:** `v0.2.0`

Per the `ui-kit` skill, never point a live page at
`releases/latest/download/…` — a new kit release would be picked up without any
change here and could break the page. Bump deliberately:

```bash
gh release download vX.Y.Z --repo gaarutyunov/ui-kit \
  --pattern 'ga-ui-kit.css' --pattern 'ga-ui-kit.min.js' \
  --dir site/vendor --clobber
```

Then re-render the social card (`site/og-image.png`) so it matches:

```bash
python3 -m http.server 8099 --directory site &
node .agents/skills/social-image/scripts/social-image.mjs \
  --url http://127.0.0.1:8099/index.html --selector "[data-hero]" \
  --out site/og-image.png
```
