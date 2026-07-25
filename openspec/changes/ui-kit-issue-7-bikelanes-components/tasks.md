## 1. Form controls

- [ ] 1.1 `ga-checkbox`: form-associated (`ElementInternals`), attributes `checked`, `indeterminate`, `disabled`, `label`, `name`, `value`; `change` with `{ checked }`; label click toggles; keyboard parity with the native control.
- [ ] 1.2 `ga-button` icon affordance: `size="icon"` — square footprint, centred glyph, no text padding — and a console warning when neither `aria-label` nor `title` is present, so an unlabelled icon button is caught in development.
- [ ] 1.3 `ga-slider` end labels: `label-start`, `label-end`, `hide-value`; existing single-`label` behaviour untouched when they are absent.
- [ ] 1.4 `ga-input` adornments: `prefix` / `suffix` slots inside the field frame, and `readonly` presentation that keeps the field's shape while making it non-editable; focus ring still tracks the input.
- [ ] 1.5 `ga-file-button`: a compact button that opens the file dialog; attributes `accept`, `multiple`, `label`; emits the same `files` event as `ga-file-drop`.
- [ ] 1.6 `ga-combobox`: an input with an asynchronous suggestion list — `options` set by the host, a debounced `filter` event, `role="combobox"`/`listbox` semantics, keyboard navigation, "no results" state. Built on `ga-select`'s popup and listbox groundwork (ui-kit#6), not a second implementation.

## 2. Data display

- [ ] 2.1 `ga-stat`: `value`, `caption`, optional `unit` and `tone`; sized so a row of them aligns without per-app CSS.
- [ ] 2.2 `ga-status`: single-line status with `tone` (`neutral` | `ok` | `error`), `role="status"` so changes are announced, and an empty state that occupies its line rather than collapsing the layout.

## 3. Overlays

- [ ] 3.1 `ga-panel` overlay mode: `overlay` attribute — fixed positioning above page content, backdrop blur, an explicit stacking token so a map canvas cannot paint over it.
- [ ] 3.2 `ga-bottom-sheet`: the same overlay treatment plus the mobile form (drag/`Escape` to dismiss); documented breakpoint at which a panel becomes a sheet.
- [ ] 3.3 Document the composition for a full-bleed canvas app: canvas at the bottom, overlay panel above, sheet on narrow viewports.

## 4. Registration, types, docs

- [ ] 4.1 Import the new components in `src/index.js`; add tags to `index.d.ts` and `react.d.ts`.
- [ ] 4.2 `npm run types`; commit the regenerated declarations.
- [ ] 4.3 `site/registry.js`: a page per new component, and updated pages for `ga-button`, `ga-slider`, `ga-input`, `ga-panel`, `ga-bottom-sheet`.
- [ ] 4.4 Update the component list in `README.md`.

## 5. Verify and release

- [ ] 5.1 `npm run build` and `npm run bundle`; exercise every new and widened component in the docs site, including keyboard-only paths.
- [ ] 5.2 Screen-reader smoke test (VoiceOver): checkbox state, icon-button labels, combobox announcements, status-line announcements.
- [ ] 5.3 Check both themes (`data-theme="dark"` / `"light"`).
- [ ] 5.4 Confirm the additive claims: an existing `ga-slider`, `ga-input` and `ga-panel` usage renders exactly as before.
- [ ] 5.5 Cut a release and note the version on ui-kit#7 so bikelanes#4 can pin it.
