## Context

Pet projects follow the `pet-project-metadata` contract (description, `pet-project`
topic, homepage, README/SPEC, GitHub Pages). garutyunov.com's card crawler reads
`og:image` off each project's live page (`lib/og.ts`), so a social image directly
improves how projects appear on the personal site and in link unfurls.

Skills in this repo are markdown instructions plus optional scripts, sourced in
`.agents/skills/<name>/` with a `.claude/skills/<name>` symlink and a
`skills-lock.json` entry (installed per-repo, never global). The closest existing
skill, `icon-generation`, renders a square app icon via an OpenRouter AI model —
this new skill must be its deterministic, wide-format sibling.

ui-kit ships web-component primitives (`ga-card`, `ga-header`, `ga-icon`, …) and
design tokens (`tokens.css`) but no dedicated hero element, so a hero is composed
from those primitives + tokens in a template.

## Goals / Non-Goals

**Goals:**
- Deterministic, no-AI 1200×630 social image from a project's hero.
- Work for projects with a landing (screenshot its hero) and without one (render a
  throwaway ui-kit hero, never deployed).
- Extend the metadata standard so every pet project ships one.

**Non-Goals:**
- An AI-generated image (explicitly excluded by the issue).
- A permanent hero *component* added to ui-kit (the throwaway hero is a template
  the skill owns, not a shipped element) — can be promoted later if it proves
  reusable.
- Animated/social-video assets; only a static PNG.
- Changing garutyunov.com's crawler (it already reads `og:image`).

## Decisions

### D1: Playwright (headless Chromium) as the deterministic renderer
Screenshot real HTML/CSS/web-components at exactly 1200×630. Playwright renders
ui-kit custom elements and web fonts faithfully, waits for load/fonts
deterministically, and clips to an element or the viewport.
- *Alternative — satori (JSX→SVG) + resvg/sharp:* fast and dependency-light but
  does **not** execute web components or arbitrary CSS, so a ui-kit-styled hero
  wouldn't render. Rejected.
- *Alternative — Puppeteer:* equivalent; Playwright chosen for its simpler
  `npx playwright` install and built-in `waitForLoadState`/font settling.
- Invoked via `npx` at run time (the script `npx playwright install chromium`
  on first use) so no project repo carries a heavy permanent dependency.

### D2: Two input modes behind one script
`scripts/social-image.mjs`:
- `--url <landing-url> [--selector <css>]` → load the landing, wait for load +
  fonts, screenshot the hero element (default selector e.g. `.hero`,
  `[data-hero]`, or `main > header`; documented and overridable) clipped to
  1200×630.
- `--hero` (no landing) → render `scripts/hero-template.html` filled with
  `--title`, `--tagline`, `--icon <path>`, importing ui-kit `tokens.css` (+ the
  bundled `ga-ui-kit.css`), then screenshot the full 1200×630 viewport.
- Output `--out public/og-image.png` (default). Fails loudly if the selector
  matches nothing.

### D3: Throwaway hero template, never deployed
`hero-template.html` lives inside the skill (`.agents/skills/social-image/scripts/`),
not in any project repo. The script copies/serves it from a temp dir (or a
`file://` load with the project's icon inlined), renders, screenshots, and
discards it. Nothing is written into the project except the final PNG. Documented
explicitly so an implementer doesn't commit the hero into the project's deploy
output.

### D4: 1200×630 PNG at `public/og-image.png`, referenced absolutely
Standard OG size. Written to the project's static root (`public/` for Vite,
deploy root for buildless). The project references it via
`<meta property="og:image" content="https://<name>.garutyunov.com/og-image.png">`
and `twitter:image`, `twitter:card=summary_large_image`. Absolute URL because
scrapers require it.

### D5: Extend pet-project-metadata, don't fork it
Add one row to the required-metadata table ("Social image"), one conventions
bullet, and one audit-checklist item, plus a cross-link to the `social-image`
skill. Keeps a single source of truth for the metadata contract.

## Risks / Trade-offs

- **[Playwright/Chromium is heavy to install]** → installed on demand via `npx
  playwright install chromium`, cached by the runner; not a per-project dep.
  Documented as a prerequisite in the SKILL.
- **[Screenshot flakiness / fonts not loaded]** → wait for `networkidle` +
  `document.fonts.ready` before capture; fixed viewport and deviceScaleFactor for
  stable output.
- **[Default hero selector won't match every landing]** → selector is overridable
  and the script fails loudly (not silently blank) when it matches nothing.
- **[ui-kit CSS drift changes the throwaway hero look]** → acceptable; the hero
  pins to ui-kit tokens so it tracks the house style intentionally.
- **[Determinism caveat]** → PNG bytes may differ across Chromium versions; the
  spec's "repeatable" requirement is about layout/content/size, not byte-identity.
  Noted so review doesn't expect bit-exact reproducibility.

## Migration Plan

- Additive: new skill files + a metadata-skill doc edit. No existing behavior
  changes.
- Backfill (follow-up, out of scope for this change): run the skill for existing
  pet projects (boids has an icon and OG tags already; a proper 1200×630 hero
  image would replace the square `icon-512` used as `og:image`).
- Rollback: remove the skill dir + symlink + lock entry and revert the metadata
  edit; no project depends on the skill existing.

## Open Questions

- Default hero selector set — which selectors to try in order before requiring
  `--selector`. To be finalized against the real landings (site-review, stereoscope).
- Whether the throwaway hero should also emit a matching **light**-theme variant,
  or only the dark house style (leaning dark-only to match the sites).
- Whether to promote the throwaway hero into a real `ga-hero` ui-kit component in
  a later change if multiple projects want a live hero, not just a screenshot.
