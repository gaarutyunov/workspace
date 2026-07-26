## Context

`@gaarutyunov/ui-kit` is a **buildless, zero-dependency** Web Components kit:

- `src/components/<name>/<name>.js` — one class per component extending
  `GaElement` (`src/core/base-element.js`), styles as a static template string
  inside Shadow DOM, registered with `define()`.
- `src/index.js` imports every component for its side effect; `src/index.d.ts`
  augments `HTMLElementTagNameMap`; `scripts/types.mjs` regenerates the
  per-component `.d.ts` from JSDoc; `scripts/bundle.mjs` produces the standalone
  release assets consumers pin.
- `site/registry.js` is the docs site's data model — every component has a page
  with live previews, an API table and a playground. There is **no test runner**;
  the docs site is the de-facto verification surface.
- Theming is via `--ga-*` custom properties that pierce the Shadow DOM; every
  component reads tokens with literal fallbacks so it looks right even without
  `tokens.css`.

Consumers (garutyunov.com, workout, bikelanes, site-review's landing, this
workspace's landing) either install from GitHub Packages or vendor a **pinned**
release bundle. Nothing ships until a release is cut.

## Goals / Non-Goals

**Goals**

- Unblock workout#2: `<select>`, calendar/date fields, charts and the chat view
  can be expressed with `<ga-*>` elements.
- Stay zero-dependency and buildless — platform APIs only.
- Keep every new element consistent with the existing ones: Shadow DOM styles,
  `--ga-*` tokens with fallbacks, form association where a value exists, events
  re-dispatched with a `{ value }`-shaped detail.

**Non-Goals**

- Shipping a charting engine. Apps keep recharts (or anything else); the kit
  supplies tokens and a frame.
- A rich-text or markdown renderer inside chat messages — the app slots its own
  rendered content into the bubble.
- Date *range* selection, time pickers, or timezone handling beyond what `Intl`
  gives for free.
- Virtualised lists for very large option sets or transcripts.
- The bikelanes gaps in ui-kit#7 — a separate change.

## Decisions

### D1: `ga-select` is a listbox over an internal option model, form-associated

The element takes options either as an `options` attribute (JSON array of
`{ value, label, disabled? }`) or as slotted `<option>` children mirroring the
native API, and exposes `value` (string, or array when `multiple`). It is
`formAssociated` with `ElementInternals`, matching `ga-input` / `ga-slider` /
`ga-switch`, so it participates in native form submission.

- *Alternative — wrapping a native `<select>` in the shadow root:* free
  accessibility and mobile behaviour, but the option list cannot be styled at all
  in the house style, and multi-select and filtering are unusable. Rejected.
- *Alternative — a headless component that only manages state:* leaves every app
  to build the popup. Rejected; the point is to stop hand-rolling.

Filtering: when `filterable` is set, a text input in the trigger filters options
by substring, case-insensitively. When the app wants server-driven options it
listens for `filter` (debounced, with the typed text) and updates `options` —
this is the hook the async combobox in ui-kit#7 will build on.

### D2: One shared popup primitive for `ga-select` and `ga-date-input`

Both need "a panel anchored under a trigger, above everything, dismissed on
outside click / Escape, closed when the trigger scrolls away". That lands in
`src/core/popup.js` as a small helper (not a custom element): it opens the panel
with the **native Popover API** (`popover="manual"` + `showPopover()`), which
gives top-layer stacking without z-index fights, and positions it with
`getBoundingClientRect` + a flip when the panel would overflow the viewport.

- Anchor positioning (`anchor-name` / `position-area`) is not used as the primary
  mechanism because it is still uneven across browsers; the JS path is
  deterministic. Where the popover API is missing the helper falls back to an
  absolutely-positioned panel inside the host.
- The helper is internal (not exported from `index.js`) so it can change without
  a breaking release.

### D3: `ga-calendar` is built on `Intl`, and `ga-date-input` composes it

`ga-calendar` renders a month grid from `Intl.DateTimeFormat` (weekday names,
month label) and honours `locale` and `first-day` (0–6, defaulting to the
locale's convention). Values are exchanged as `YYYY-MM-DD` strings — no `Date`
objects across the boundary, no timezone ambiguity in the value.

`ga-date-input` is a `ga-input`-shaped text field with a calendar affordance that
opens `ga-calendar` in the D2 popup, and accepts typed input parsed leniently
(`YYYY-MM-DD` always; locale-formatted input best-effort). `min` / `max` bound
both.

- *Alternative — `<input type="date">`:* one line of code, but the picker is
  entirely browser-chrome and cannot carry the house style, which is the whole
  reason workout uses `react-day-picker` today. It stays available to apps that
  don't care; the kit provides the styled path.

### D4: Charts get tokens and a frame, not an engine

`--ga-chart-1 … --ga-chart-8` (an ordered categorical palette derived from the
existing accent hues, distinguishable in both themes), plus `--ga-chart-grid`,
`--ga-chart-axis`, `--ga-chart-label` and a tooltip surface. `ga-chart-frame`
supplies the title/legend/plot layout, a responsive height, and a documented
`--ga-chart-*`-consuming legend so a recharts (or Chart.js, or raw SVG) chart
slotted into it reads as part of the system.

- *Alternative — a real `ga-chart` element:* pulls a charting engine into a
  zero-dependency kit, or re-implements one. Explicitly declined in the issue's
  own terms ("even if a full chart lib stays out of scope, expose the tokens").

### D5: `ga-chat` is a transcript, `ga-chat-message` is a bubble, the composer is a recipe

`ga-chat-message` carries `role` (`user` | `assistant` | `system`), a `state`
(`sent` | `pending` | `streaming` | `error`), an optional author/time header and
slotted body content — the app renders markdown itself and slots the result.
`ga-chat` is the scroll container: it stays pinned to the newest message while
the user is at the bottom, and stops following as soon as they scroll up (so a
streaming answer never yanks the view away from something being read).

The composer is **not** a new element: a documented recipe combining `ga-input`
and `ga-button` in the `footer` slot. Building a bespoke input here would
duplicate form behaviour the kit already has.

### D6: Docs page per component, generated types, one release

Every new element gets a `site/registry.js` page with live examples and an API
table — the docs site is how these are exercised, since the kit has no test
runner. `npm run types` regenerates declarations; `src/index.d.ts` and
`src/react.d.ts` gain the new tags by hand. Shipping ends with a tagged release
(minor bump) whose bundle assets consumers pin; workout#2 stays blocked until
that release exists.

## Risks / Trade-offs

- **[Accessibility of a custom listbox]** — a hand-built select is easy to get
  wrong for screen readers. Mitigation: strict `role="combobox"` /
  `role="listbox"` / `role="option"` wiring with `aria-activedescendant`,
  keyboard parity with the native control (type-ahead, Home/End, PageUp/Down),
  and the docs page documenting the interaction contract.
- **[Popover API support]** — mitigated by the fallback path in D2.
- **[Palette distinguishability]** — eight categorical colours that work on both
  pure black and white are hard. Mitigation: derive from the existing accent
  hues, check contrast against both backgrounds, and keep the count at eight
  rather than inventing more.
- **[Scope creep toward a chart library]** — the frame must stay a layout box; if
  it starts drawing axes, D4 has been violated.
- **[Kit growth]** — six new elements is a large single release. Mitigation: each
  is independently importable (`components/<name>/<name>.js`), so apps that don't
  use them pay only bundle size in the standalone build.

## Migration Plan

Purely additive: no existing element changes behaviour, no token is redefined
(only new `--ga-chart-*` names). Consumers pin versions, so nothing moves until
they bump. Rollback is dropping back to the previous pinned release.

Once released, workout#2 migrates its `<select>`s, calendar, charts and chat view
onto the new elements; bikelanes' migration (#7 → bikelanes#4) follows separately.

## Resolved (owner, gaarutyunov/workspace#20)

- **Multiple-mode trigger: a summary line.** `ga-select multiple` renders
  "N selected" in the trigger, not removable chips. The trigger keeps a single
  line's height at any selection count, which is what made this the leaning.
  Chips remain possible later behind a `chips` attribute — additive, so it needs
  no breaking change.
- **The chart palette is colour-blind-safe by default** (owner's call was mine to
  make). `--ga-chart-1 … --ga-chart-8` are *ordered* so that the earlier a series
  is added, the more distinguishable it stays under deuteranopia and protanopia —
  a two-series chart uses the two most separable hues, and a chart is not required
  to use all eight. An app can still override the tokens, but it never has to
  opt in to accessibility. The alternative — shipping a prettier default and an
  opt-in accessible palette — was rejected: a default nobody changes is the one
  that ships, so the default is the accessible one.
- **`ga-chat` owns "jump to latest".** The affordance is part of the element, not
  the app: every consumer of a transcript needs it, and it depends on scroll state
  the element already tracks internally, which an app would have to reach into the
  shadow root to observe.
