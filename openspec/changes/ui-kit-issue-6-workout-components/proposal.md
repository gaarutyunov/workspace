## Why

`gaarutyunov/workout` (Fitness Tracker) has been restyled to the ui-kit house
style at the token level, but it cannot finish the `<ga-*>` component migration:
four control families it depends on have no equivalent in the kit
(gaarutyunov/ui-kit#6). Its `<select>` pickers, calendar/date fields, progress
charts and AI-coach chat transcript are all hand-rolled today, so **workout#2 is
blocked** on the kit.

The gaps are not workout-specific — a select, a date picker, chart theming and a
message list are the same primitives every pet project reaches for. Building them
in the kit means every project inherits them; patching them into workout would
fork the design system in the one app that most needs it.

## What Changes

- Add **`ga-select`** — a form-associated single/multi select with a typed
  filter, keyboard navigation and an accessible listbox popup, sized for long
  option lists where `ga-radio-group` does not scale.
- Add **`ga-calendar`** (a month grid) and **`ga-date-input`** (a text field that
  opens `ga-calendar` in a popup), both built on `Intl` with no third-party
  date library, so `react-day-picker` can be dropped.
- Add **chart theming**: a documented `--ga-chart-*` token set (an ordered
  categorical series palette plus axis / grid / tooltip surfaces) and a thin
  **`ga-chart-frame`** container (title, legend, responsive plot box) that wraps
  whichever chart library the consuming app uses. The kit does **not** ship a
  charting engine.
- Add **`ga-chat`** (a scrolling transcript) and **`ga-chat-message`** (a
  role-styled bubble with pending/streaming and error states), plus a documented
  composer recipe built from the existing `ga-input` and `ga-button`.
- Extend the shared plumbing these need: a small popup/positioning primitive
  reused by `ga-select` and `ga-date-input`, docs-site pages for every new
  component, generated type declarations, and a released bundle consumers can
  pin.

## Capabilities

### New Capabilities

- `ui-kit-select`: a form-associated select/combobox element covering single and
  multiple selection, option filtering, keyboard interaction and the listbox
  popup behaviour.
- `ui-kit-date-picker`: a calendar month grid and a date input that pairs with
  it, including locale/first-day handling, min/max bounds and keyboard
  navigation.
- `ui-kit-chart-theming`: the chart token contract and the `ga-chart-frame`
  container that lets an app-provided chart library render as part of the design
  system.
- `ui-kit-chat`: a transcript list and message bubble covering roles, pending /
  streaming / error states, and scroll-follow behaviour.

### Modified Capabilities

<!-- The kit has no pre-existing OpenSpec specs; nothing to modify. -->

## Impact

- **`src/components/`**: four new component families (`select`, `calendar`,
  `date-input`, `chart-frame`, `chat`, `chat-message`) plus a shared popup helper
  under `src/core/`.
- **`src/tokens/tokens.css`**: new `--ga-chart-*` tokens (and their light-theme
  overrides), the first token addition since the kit was extracted.
- **`src/index.js` / `src/index.d.ts` / `src/react.d.ts`**: registration and type
  augmentation for the new elements; `npm run types` regenerates the per-component
  declarations.
- **`site/registry.js`**: a docs page per component — the docs site is the kit's
  only test surface today, so the examples double as the manual verification.
- **Release**: a new tagged release with refreshed `ga-ui-kit.css` /
  `ga-ui-kit.min.js` / `ga-ui-kit.esm.js` assets, since every consumer pins a
  version. workout#2 unblocks only once that release exists.
- **Zero-dependency constraint**: the kit ships no runtime dependencies today and
  must not gain one — the calendar and the select are written against platform
  APIs (`Intl`, `popover`, `ElementInternals`) rather than a library.
- **Not addressed here**: the bikelanes gaps in gaarutyunov/ui-kit#7
  (`ga-checkbox`, `ga-stat`, icon-only buttons, dual-label slider, compact file
  button, overlay panels). `ga-select`'s filtering does cover the async-combobox
  need in #7 once it can accept externally supplied options, which this change
  keeps in mind but does not specify.
