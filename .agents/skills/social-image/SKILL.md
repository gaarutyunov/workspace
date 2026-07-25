---
name: social-image
description: "Generate a 1200x630 social/OG image for a pet project deterministically (NO AI) by screenshotting a landing hero with headless Chrome. Screenshots an existing landing's hero, or renders a throwaway ui-kit-styled hero for projects without a landing (e.g. boids). Use when a project needs an og:image / social preview. Examples: \"generate a social image for boids\", \"make the OG image for this project\", \"create a link-preview card\"."
---

# Social image generation

Produces the standard pet-project **social image**: a **1200×630** PNG (the Open
Graph / Twitter `summary_large_image` size) used as `og:image` / `twitter:image`.
Unlike the sibling `icon-generation` skill, this uses **no AI** — it renders real
HTML/CSS with **headless Chromium (Playwright)** and screenshots it, so output is
deterministic and reproducible.

Every pet project should ship one (see the `pet-project-metadata` skill).

## Two modes

The one script `scripts/social-image.mjs` handles both:

### A. From an existing landing page

Screenshot the hero region of a project's live/local landing at OG dimensions:

```bash
node scripts/social-image.mjs \
  --url https://site-review.garutyunov.com/ \
  --selector ".hero" \
  --out public/og-image.png
```

`--selector` is optional; the script tries a sensible default list
(`[data-hero]`, `.hero`, `header`, `main > header`, `main`) and fails loudly if
none match. The captured element is clipped to 1200×630.

### B. Throwaway hero (project has no landing, e.g. boids)

Render the bundled `scripts/hero-template.html` — a 1200×630 hero styled with the
GA ui-kit tokens — filled with the project's name, tagline and icon, then
screenshot the full viewport. **The hero is never written into the project or
deployed** — it lives only in a temp dir for the duration of the render.

```bash
node scripts/social-image.mjs \
  --hero \
  --title "Pinch-Boids" \
  --tagline "Control a boids flock by pinching your fingers, tracked from your webcam." \
  --icon public/icon-512.png \
  --out public/og-image.png
```

## Prerequisites

- Node ≥ 20.
- **Playwright + Chromium.** Installed on demand — the script runs
  `npx playwright install chromium` on first use if the browser is missing. In CI,
  cache `~/.cache/ms-playwright`.
- No API key, no network dependency beyond fetching the `--url` page (mode A). No
  AI model is ever called.

## Wire it into the project

After generating `public/og-image.png`, reference it from the project's `<head>`
(absolute URL — scrapers require it):

```html
<meta property="og:image" content="https://<name>.garutyunov.com/og-image.png" />
<meta name="twitter:image" content="https://<name>.garutyunov.com/og-image.png" />
<meta name="twitter:card" content="summary_large_image" />
```

For a Vite project put the PNG in `public/` (copied to the deploy root); for a
buildless site put it at the deploy root directly.

## Notes

- **Determinism** is about layout/content/size, not byte-identical PNGs — Chromium
  version changes can shift a few bytes. The script pins the viewport
  (1200×630, `deviceScaleFactor: 1`) and waits for `networkidle` +
  `document.fonts.ready` before capturing so the result is stable in practice.
- If `tree-sitter`/grammar-less: N/A — this skill is plain Node + a browser.
- Related: `pet-project-metadata` (requires this image), `icon-generation` (the
  square app icon, AI-generated), `ui-kit` (the hero's design tokens).
