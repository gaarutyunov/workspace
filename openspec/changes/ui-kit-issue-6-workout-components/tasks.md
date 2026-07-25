## 1. Shared plumbing

- [ ] 1.1 Add `src/core/popup.js` — anchor a panel to a trigger using the native Popover API (`popover="manual"`), position with `getBoundingClientRect` + viewport flip, close on outside click / Escape / anchor scrolled out of view, and fall back to an absolutely-positioned panel when `popover` is unsupported. Internal only (not exported from `index.js`).
- [ ] 1.2 Unit-check the fallback path manually in a browser without popover support (or with the API stubbed off) via a docs playground.

## 2. `ga-select`

- [ ] 2.1 Implement `src/components/select/select.js`: options from a JSON `options` attribute or slotted `<option>` children, attributes `value`, `multiple`, `filterable`, `placeholder`, `disabled`, `name`, `label`, `hint`, `error`.
- [ ] 2.2 Form association via `ElementInternals` (`formAssociated`), `value` getter/setter (string, or array when `multiple`), `change` / `input` events with a `{ value }` detail.
- [ ] 2.3 Listbox popup via `core/popup.js`: `role="combobox"` trigger, `role="listbox"` panel, `role="option"` rows, `aria-activedescendant`, `aria-expanded`, `aria-multiselectable`.
- [ ] 2.4 Keyboard: open/close (Enter/Space/Alt+Down/Escape), Up/Down/Home/End/PageUp/PageDown, type-ahead, Tab closes and commits; focus returns to the trigger on dismissal.
- [ ] 2.5 Filtering: case-insensitive substring match over labels, a "no matches" row, and a debounced `filter` event carrying the typed text so an app can supply options itself.
- [ ] 2.6 Multiple mode: toggle selection without closing, summary in the trigger ("N selected"); disabled options are skipped by keyboard and pointer.
- [ ] 2.7 JSDoc header in the house format (attributes, slots, events) — `scripts/types.mjs` generates the declaration from it.

## 3. `ga-calendar` and `ga-date-input`

- [ ] 3.1 Implement `src/components/calendar/calendar.js`: month grid from `Intl.DateTimeFormat`, attributes `value` (`YYYY-MM-DD`), `month`, `locale`, `first-day`, `min`, `max`, `disabled`; `change` event with the date string.
- [ ] 3.2 Mark today, the selected day and out-of-range days distinctly; keyboard grid navigation (arrows, Home/End, PageUp/PageDown for months) with a roving tabindex and `role="grid"` semantics.
- [ ] 3.3 Implement `src/components/date-input/date-input.js`: text field + calendar affordance opening `ga-calendar` in the `core/popup.js` panel; lenient parsing (`YYYY-MM-DD` always, locale format best-effort); invalid and out-of-range input set an error state without adopting the value.
- [ ] 3.4 Form association for `ga-date-input` (`ElementInternals`, `YYYY-MM-DD` submitted value), `change` / `input` events with `{ value }`.
- [ ] 3.5 Confirm no `Date`-parsing ambiguity: value round-trips as the same calendar date across timezones (spot-check with `TZ=Pacific/Kiritimati` and `TZ=Pacific/Niue` in the docs playground).

## 4. Chart theming

- [ ] 4.1 Add `--ga-chart-1 … --ga-chart-8`, `--ga-chart-grid`, `--ga-chart-axis`, `--ga-chart-label`, `--ga-chart-tooltip-bg`, `--ga-chart-tooltip-fg` to `src/tokens/tokens.css`, with light-theme overrides in the existing `[data-theme="light"]` block.
- [ ] 4.2 Check each palette entry for legibility on both `--ga-bg` values and adjacent-pair distinguishability; document the intended series order.
- [ ] 4.3 Implement `src/components/chart-frame/chart-frame.js`: `title`, `legend` (JSON series metadata) , `loading`, `empty-text`; slotted plot content, responsive height, legend swatches from the palette tokens. It draws no data.

## 5. `ga-chat` and `ga-chat-message`

- [ ] 5.1 Implement `src/components/chat-message/chat-message.js`: `role` (`user` | `assistant` | `system`), `state` (`sent` | `pending` | `streaming` | `error`), `author`, `time`; slotted body; pending/streaming indicators; error treatment; `role`-appropriate ARIA.
- [ ] 5.2 Implement `src/components/chat/chat.js`: scrollable transcript with `header` / default / `footer` slots, empty state, and scroll-follow that pins to the newest message only while the user is at the bottom.
- [ ] 5.3 Document the composer recipe (`ga-input` + `ga-button` in the `footer` slot, submit on click and on the keyboard submit gesture) on the docs page.

## 6. Registration, types, docs

- [ ] 6.1 Import every new component in `src/index.js`; add the new tags to `src/index.d.ts` (`HTMLElementTagNameMap`) and `src/react.d.ts`.
- [ ] 6.2 Run `npm run types` and commit the regenerated per-component declarations.
- [ ] 6.3 Add a `site/registry.js` page per component (select, calendar, date input, chart frame, chat) with live examples, API tables and playgrounds; add them to the Components nav.
- [ ] 6.4 Update `README.md`'s component list.

## 7. Verify and release

- [ ] 7.1 `npm run build` and `npm run bundle`; load the docs site (`npm run dev`) and exercise every new component, including keyboard-only paths.
- [ ] 7.2 Screen-reader smoke test of `ga-select` and `ga-calendar` (VoiceOver): announced roles, active option, selected state.
- [ ] 7.3 Verify both themes (`data-theme="dark"` / `"light"`) for every new component and the chart palette.
- [ ] 7.4 Cut a minor release with refreshed `ga-ui-kit.css` / `ga-ui-kit.min.js` / `ga-ui-kit.esm.js` assets; note the version on gaarutyunov/ui-kit#6 so workout#2 can unblock and pin it.
