---
name: ui-kit
description: "Use the GA UI Kit (@gaarutyunov/ui-kit) web components on pet projects and garutyunov.com. Use when building or styling any personal website / pet-project UI, adding buttons/cards/inputs/etc., or wiring the kit into vanilla HTML, React, Next.js, Astro, Vue, Svelte or Solid. Examples: \"add the ui-kit to this project\", \"use ga-button here\", \"style this pet project with the design system\"."
---

# GA UI Kit usage

`@gaarutyunov/ui-kit` (repo: [gaarutyunov/ui-kit](https://github.com/gaarutyunov/ui-kit),
docs: <https://gaarutyunov.github.io/ui-kit/>) is a **universal, zero-dependency**
UI kit built on native **Web Components**. The same `<ga-*>` custom elements work
in vanilla JS, React, Astro, Vue, Svelte, Solid — or no framework at all. Visual
language: Geist-inspired, pure-black design system shared by garutyunov.com and
stereoscope.

**Always prefer these components over hand-rolled UI** on any pet project or on
garutyunov.com. Only build a bespoke component when the kit has no equivalent —
and consider contributing it back to the ui-kit repo instead.

## Components available

`ga-button` · `ga-radio-group` · `ga-badge` · `ga-card` · `ga-avatar` ·
`ga-input` · `ga-switch` · `ga-spinner` · `ga-alert` · `ga-kbd` · `ga-code` ·
`ga-tabs` · `ga-breadcrumbs` · `ga-table` · `ga-note` · `ga-slider` ·
`ga-file-drop` · `ga-fab` · `ga-panel` · `ga-header` · `ga-bottom-nav` ·
`ga-bottom-sheet` · `ga-icon`

Before using a component, confirm its exact attributes/slots against the live
docs (<https://gaarutyunov.github.io/ui-kit/>) or the component's JSDoc in
`src/` of the ui-kit repo — the kit ships typed declarations generated from that
JSDoc, so `HTMLElementTagNameMap` and the React types entry are always current.

## Choosing an install method

| Situation | Method |
| --- | --- |
| npm/bundler project (Next.js, Vite, Astro, etc.) | GitHub Packages install |
| Buildless static page on GitHub Pages | Standalone `<script>` from the release |
| Need pinned/reproducible version | Pin `releases/download/vX.Y.Z/…` or an exact npm version |

### 1. npm (GitHub Packages)

The package is published to **GitHub Packages** under the `@gaarutyunov` scope.
Point the scope at the GitHub registry once, then install:

```ini
# .npmrc  (commit this)
@gaarutyunov:registry=https://npm.pkg.github.com
```

```bash
npm install @gaarutyunov/ui-kit
```

> GitHub Packages requires auth even for public packages. Add a PAT with
> `read:packages` to `~/.npmrc` (never the repo `.npmrc`):
> `//npm.pkg.github.com/:_authToken=YOUR_TOKEN`. In CI, use
> `${{ secrets.GITHUB_TOKEN }}` or a scoped PAT.

### 2. Standalone `<script>` (no build, no npm)

Every release attaches a self-contained bundle that registers all `<ga-*>`
elements on load — ideal for buildless GitHub Pages pet projects. **Always pin
an explicit version** (`releases/download/vX.Y.Z/…`):

```html
<!-- pin the version — replace vX.Y.Z with the release you tested against -->
<link rel="stylesheet"
  href="https://github.com/gaarutyunov/ui-kit/releases/download/vX.Y.Z/ga-ui-kit.css" />
<script
  src="https://github.com/gaarutyunov/ui-kit/releases/download/vX.Y.Z/ga-ui-kit.min.js"></script>

<ga-button variant="primary">Hello</ga-button>
```

> ⚠️ **Do not use `releases/latest/download/…` on a live site.** A new ui-kit
> release would be picked up automatically and can break the page without any
> change on your side. Pin a version and bump it deliberately after testing.
> (`latest` is fine only for throwaway experiments.)

Find the current version on the [releases page](https://github.com/gaarutyunov/ui-kit/releases)
or with `gh release view --repo gaarutyunov/ui-kit --json tagName`. An ES-module
build (`ga-ui-kit.esm.js`) is attached too, for `<script type="module">import`.

## Usage by framework

### Vanilla HTML / JS (no build — standalone release)

Bare specifiers like `@gaarutyunov/ui-kit` do **not** resolve in a browser
without a bundler or import map, so a true no-build page uses the pinned
standalone release assets from the section above:

```html
<link rel="stylesheet"
  href="https://github.com/gaarutyunov/ui-kit/releases/download/vX.Y.Z/ga-ui-kit.css" />
<script
  src="https://github.com/gaarutyunov/ui-kit/releases/download/vX.Y.Z/ga-ui-kit.min.js"></script>

<ga-button variant="primary">Get started</ga-button>
<ga-alert tone="success" title="Done">Saved your changes.</ga-alert>
```

With a **bundler** (Vite, etc.), import the package specifiers instead:

```js
import "@gaarutyunov/ui-kit";              // registers the elements
import "@gaarutyunov/ui-kit/tokens.css";   // resolved by the bundler
```

### React / Next.js

```jsx
import "@gaarutyunov/ui-kit";          // registers the elements (runtime)
import "@gaarutyunov/ui-kit/tokens.css";

export function Demo() {
  // Custom elements are just DOM — props become attributes, events via ref/onEvent.
  return (
    <ga-card interactive>
      <strong>Hello from React</strong>
      <ga-button variant="primary">Click</ga-button>
    </ga-card>
  );
}
```

React 19 supports custom elements (incl. properties & events) natively. On
React ≤18, attribute props work out of the box; for custom events attach a
listener with a `ref`. In Next.js App Router, import the kit in a Client
Component (or a `useEffect`) since custom elements register in the browser.

For **typed JSX**, reference the opt-in, types-only React entry once:

```tsx
import "@gaarutyunov/ui-kit";        // registers the elements (runtime)
import "@gaarutyunov/ui-kit/react";  // teaches JSX about them (types only)
```

Requires bundler-style `moduleResolution` (`"bundler"`, `"node16"` or
`"nodenext"`). The React entry is deliberately not pulled in by the main entry,
so vanilla/Vue/Svelte/Solid projects are unaffected.

### Astro

```astro
---
import "@gaarutyunov/ui-kit";
import "@gaarutyunov/ui-kit/tokens.css";
---
<ga-tabs tabs='[{"id":"a","label":"One"},{"id":"b","label":"Two"}]'>
  <div slot="a">First panel</div>
  <div slot="b">Second panel</div>
</ga-tabs>
```

### Vue / Svelte / Solid

All three render custom elements directly. In Vue, mark `ga-*` as custom
elements in compiler options: `isCustomElement: tag => tag.startsWith('ga-')`.

## TypeScript

Types ship **inside** the kit — no `@types/…` package. Three things are wired:

1. **Class declarations** — `import { GaButton } from "@gaarutyunov/ui-kit"` is typed.
2. **`HTMLElementTagNameMap`** augmented from the main entry — `document.querySelector("ga-card")` → `GaCard | null`.
3. **Types-only `@gaarutyunov/ui-kit/react`** entry augmenting `React.JSX.IntrinsicElements`.

## Theming

The kit is themed with CSS custom properties that pierce the Shadow DOM
boundary — set them on `:root` or a container. Load `tokens.css` (npm) or
`ga-ui-kit.css` (standalone) for the defaults, then override the **`--ga-`
prefixed** tokens to match the project:

```css
:root {
  --ga-accent: #ac4bff;
  --ga-radius: 10px;
  --ga-font-sans: "Inter", system-ui, sans-serif;
}
```

See `src/tokens/tokens.css` in the kit for the full token set. Style isolation is
via Shadow DOM, so host-page styles cannot leak into components — theme through
tokens, not descendant selectors.

## Checklist when adding the kit to a project

- [ ] Pick install method (npm vs standalone) from the table above.
- [ ] Commit `.npmrc` scope line if using npm; keep the auth token in `~/.npmrc`/CI secrets only.
- [ ] Import the CSS (`tokens.css` / `ga-ui-kit.css`) exactly once.
- [ ] Register the runtime entry once (`import "@gaarutyunov/ui-kit"` or the `<script>`).
- [ ] For React+TS, also import `@gaarutyunov/ui-kit/react` for typed JSX.
- [ ] Verify component attributes/slots against the live docs before use.
- [ ] Override theme tokens as needed; never reach into Shadow DOM.
