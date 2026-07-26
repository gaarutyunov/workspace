## Context

`@gaarutyunov/ui-kit` is a buildless, zero-dependency Web Components kit: one
class per component under `src/components/<name>/`, Shadow DOM styles read from
`--ga-*` tokens with literal fallbacks, `src/index.js` registering everything,
`scripts/types.mjs` generating declarations from JSDoc, and `site/registry.js`
driving a docs site that doubles as the only test surface (there is no test
runner).

bikelanes is the forcing case: a full-bleed map with a floating control panel, a
dense toolbar, nine numeric readouts and a one-line status. ui-kit#6 is doing the
same exercise for the workout app and proposes `ga-select`, a calendar, chart
tokens and chat; the two issues overlap in exactly one place, the combobox.

## Goals / Non-Goals

**Goals**

- Every bikelanes control has a `<ga-*>` equivalent, so bikelanes#4 is a markup
  and wiring change rather than a design exercise.
- Widenings are **additive**: existing usages render unchanged.
- The additions are general. A checkbox, a stat tile and a status line are not
  map furniture.

**Non-Goals**

- Map-specific components. Nothing here knows what a route is.
- Re-implementing the listbox: the combobox builds on ui-kit#6's `ga-select`.
- A layout system for overlays beyond the panel/sheet pair.
- Theming beyond the existing tokens.

## Decisions

### D1: `size="icon"` on `ga-button`, not a separate `ga-icon-button`

The visual variants (`ghost`, `secondary`, `danger`) all apply to icon buttons
too. A separate element would duplicate every one of them and force callers to
switch elements when a button gains a label.

- The accessible name is **required**: with neither `aria-label` nor `title`, the
  component warns in the console. A silent unlabelled icon button is the most
  common accessibility defect in exactly this shape, and the kit is where it can
  be caught once.

### D2: Slider end labels are attributes, not slots

`label-start` / `label-end` / `hide-value` keep the common case one line of
markup and leave the existing `label` behaviour untouched when they are absent.
Slots would allow richer content, at the price of making the simple case verbose
and the "which label wins" rules harder to state.

### D3: Adornments live inside the field frame

`prefix` / `suffix` slots render *inside* `ga-input`'s border, so a status dot or
a trailing action button reads as part of the field rather than as siblings the
app has to align. `readonly` keeps the field's shape while making it
non-editable — bikelanes' start/destination rows are display surfaces that must
still look like inputs.

- *Alternative — leave it to the app's CSS:* what bikelanes does today, and the
  reason its inputs drift from the kit whenever either changes.

### D4: `ga-status` is a line, `ga-alert` is a box

Tone-coloured single line with `role="status"` so a screen reader announces
changes, occupying its line even when empty so the layout does not jump. Not an
`inline` variant of `ga-alert`: alerts carry a title, an icon and a dismiss
affordance, none of which apply, and folding them together would make both
harder to read.

### D5: Overlay is a mode on the existing panel, not a new component

`ga-panel[overlay]` switches to fixed positioning, a backdrop blur and an
explicit stacking token; `ga-bottom-sheet` gains the same treatment plus the
mobile dismissal gestures. A map canvas is the adversary here — the stacking
value is a documented token so an app can position around it instead of guessing
z-indexes.

### D5a: `ga-stat` is one metric with its caption — not a table row

*(Raised by the owner on the spec PR: "I don't understand the stat component at
all. What is it? If it's a table then no need for a separate component. Just use
the table component.")*

`ga-stat` renders **one number with the word for it underneath** — the shape
bikelanes writes by hand nine times:

```html
<div class="hud-main"><strong id="h-speed">0.0</strong><small>km/h now</small></div>
<div><strong id="h-avg">0.0</strong><small>avg km/h</small></div>
<div><strong id="h-eta">–</strong><small>ETA</small></div>
```

It is **not** tabular data, and `ga-table` is the wrong element for it on three
counts:

- **There are no columns.** `ga-table` takes a `columns` JSON attribute and
  slotted rows that share one grid template — a header plus *homogeneous* rows.
  The HUD is six *heterogeneous* metrics (km/h, a clock time, a distance, an
  elapsed duration) laid out 3×2. "km/h now" is a caption under a number, not a
  column header shared by other rows.
- **One tile is deliberately bigger.** Current speed is the primary readout
  (`.hud-main`); the other five are subordinate. A table row cannot express that,
  and shouldn't.
- **A table announces itself as a table.** A screen reader would read a grid of
  independent metrics as rows and columns with navigation semantics that do not
  apply.

The alternative — *drop `ga-stat` and let apps keep writing
`<strong>`+`<small>`* — is what bikelanes does today, and is why its readouts
drift from the kit. The component earns its place by owning three things an app
otherwise re-derives every time: **shared baselines** so a row of differently
sized values lines up, a **placeholder that holds the tile's footprint** so the
layout does not jump when the first value arrives mid-ride, and the
value/caption type scale coming from tokens rather than from each app's CSS.

Consequently there is **no `ga-stat-row`**: a set of tiles is laid out by the app
with a documented CSS grid recipe. The owner's push here is toward *fewer*
components, and a wrapper whose whole job is `display: grid` does not clear that
bar.

### D6: The combobox is `ga-select`'s sibling, and lands after it

ui-kit#6 proposes `ga-select` with a popup, listbox semantics, keyboard handling
and a debounced `filter` event. `ga-combobox` is the same machinery with
free-text entry and host-supplied options. Implementing it first would mean
building that machinery twice, so it is sequenced after #6's `ga-select` — the
only ordering constraint between the two issues.

### D7: Everything is verified in the docs site

The kit has no test runner, so each component ships a `site/registry.js` page
with live examples and an API table, and those pages are how the interaction and
keyboard contracts are exercised — including a page composing the overlay panel
over a stand-in canvas.

## Risks / Trade-offs

- **[Widening five existing components]** — the risk is a regression in something
  already shipped. Mitigated by keeping every new behaviour behind a new
  attribute and by an explicit verification step that existing usages render
  unchanged.
- **[`size="icon"`'s warning]** — a console warning is advice, not enforcement;
  it will be ignored sometimes. The alternative, refusing to render, is worse.
- **[Overlay stacking]** — an app can still out-z-index the panel. A token makes
  the contract visible rather than guessed.
- **[Two ui-kit changes in flight]** — #6 and #7 both touch `src/index.js`, the
  docs registry and the release. Conflict is textual, not semantic; whichever
  lands second rebases.

## Migration Plan

Additive. No existing attribute changes meaning, no token is redefined, and
consumers pin versions. Rollback is the previous pinned release.

Once released, bikelanes#4 migrates its markup; the same components are then
available to the other pet projects (the stat tile and status line in particular
recur).

## Open Questions

None outstanding — see *Resolved* below.

## Resolved (owner, gaarutyunov/workspace#22)

- **What is `ga-stat`, and why not `ga-table`?** It is one metric with its
  caption, not tabular data; the readouts it replaces have no columns, no shared
  header, and one deliberately emphasised member. `ga-table` stays for tabular
  data. Full reasoning in D5a.
- **Does `ga-stat` own a row container?** No. Alignment is the app's job, with a
  documented grid recipe in the docs page — one fewer component, which is the
  direction the owner pushed.
- **Does `ga-checkbox` need `indeterminate` in v1?** Yes — "select all" is a
  common scenario, so the tri-state ships in v1 rather than waiting for a
  consumer to need it. Toggling a mixed checkbox resolves to checked, matching
  the native control.
- **Should overlay mode trap focus?** Neither default is right for both a modal
  sheet and a persistent control panel, so it is a **configurable attribute**:
  containment is off unless asked for, and the bottom sheet — which is modal —
  asks for it.
