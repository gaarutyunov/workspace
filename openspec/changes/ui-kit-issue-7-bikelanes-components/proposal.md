## Why

`gaarutyunov/bikelanes` is restyled to the ui-kit house style at the token level,
but its controls are still hand-rolled: the address search, the start/destination
rows, the glyph buttons, the preference slider, the import row, the route/HUD
tiles, the status line and the floating panels have no `<ga-*>` equivalent
(gaarutyunov/ui-kit#7). **bikelanes#4 is blocked on this.**

None of the gaps are map-specific. A checkbox, a stat tile, an icon-only button,
a compact file picker and an inline status line are the vocabulary every dense UI
reaches for; building them in the kit is what stops each pet project from growing
its own.

## What Changes

- **`ga-checkbox`** — the inline boolean `ga-switch` is too heavy for, and
  semantically different from.
- **`ga-stat`** — a value/caption tile, the shape behind bikelanes' nine route
  and HUD readouts.
- **Icon-only buttons** — a square, glyph-centred affordance on `ga-button` with
  an accessible label that is *required*, not optional.
- **`ga-slider` end labels** — label both ends of the range and suppress the
  numeric readout, for a preference slider that means "this ↔ that".
- **`ga-input` adornments** — leading/trailing slots and a readonly
  "picked value" presentation, so a field can carry a status dot and an action
  button without leaving the field.
- **`ga-file-button`** — a compact file picker; `ga-file-drop` is a drop area and
  is far too large in a toolbar row.
- **`ga-status`** — a single-line status with neutral/ok/error tones, where
  `ga-alert` and `ga-note` are block-level boxes.
- **Overlay mode for `ga-panel` / `ga-bottom-sheet`** — documented behaviour for
  floating above a full-bleed canvas rather than sitting in the flow.
- **`ga-combobox`** — an input with an asynchronous suggestion list, built on the
  `ga-select` groundwork proposed for ui-kit#6 rather than duplicating it.

## Capabilities

### New Capabilities

- `ui-kit-form-controls`: the input-side additions — checkbox, icon-only button
  affordance, slider end labels, input adornments and readonly presentation, the
  compact file button, and the async combobox.
- `ui-kit-data-display`: the read-only additions — the stat tile and the inline
  status line.
- `ui-kit-overlays`: panels and sheets floating above page content, including the
  mobile bottom-sheet form.

### Modified Capabilities

<!-- The kit has no pre-existing OpenSpec specs; the surfaces widened here
     (`ga-button`, `ga-slider`, `ga-input`, `ga-panel`, `ga-bottom-sheet`) are
     covered by the new capabilities above. -->

## Impact

- **`src/components/`**: new `checkbox`, `stat`, `status`, `file-button`,
  `combobox`; widened `button`, `slider`, `input`, `panel`, `bottom-sheet`.
- **`src/index.js` / `index.d.ts` / `react.d.ts`**: registration and types for the
  new elements; `npm run types` regenerates the per-component declarations.
- **`site/registry.js`**: a docs page per new component and updated pages for the
  widened ones — the docs site is the kit's only test surface.
- **Backwards compatibility**: every widening is additive. `ga-slider` keeps its
  single-label behaviour when the new attributes are absent; `ga-input` renders
  unchanged without adornments; `ga-panel` stays in-flow unless overlay is asked
  for.
- **Release**: consumers pin versions, so this ends in a tagged release before
  bikelanes#4 can start.
- **Ordering against ui-kit#6**: `ga-combobox` builds on #6's `ga-select`, so it
  lands after it. The rest is independent of #6 and can ship in either order.
