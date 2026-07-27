## 1. `core/popup.js` — widen it before anything depends on it

Sequenced first because three shipped components already use it, so a
regression here is a regression in `ga-select`, `ga-date-input` and
`ga-combobox` rather than in new code.

- [ ] 1.1 Horizontal placement (`left` / `right`) with a flip to the opposite side when there is no room, alongside the existing vertical flip.
- [ ] 1.2 An opt-out of `panel.style.minWidth = rect.width` — right under a field, wrong for a six-word label over a 40px button.
- [ ] 1.3 **Prove the three existing consumers are unaffected.** Assert it, do not assume it: each still matches its trigger's width and flips vertically exactly as before.

## 2. `ga-tooltip`

- [ ] 2.1 New `src/components/tooltip/tooltip.js`, built on `createPopup` — hover **and** keyboard focus, a short show delay, hide on blur/leave/Escape, never a tab stop.
- [ ] 2.2 Adopt the trigger's `title` as the tooltip text and remove the attribute from the trigger, so the native tooltip does not double up — **without** disturbing the accessible name.
- [ ] 2.3 **Do not touch `ga-button`'s `_warnIfUnnamed()`** (design D2). Document in the tooltip's JSDoc why a tooltip cannot supply the name: `aria-labelledby`/`describedby` are IDREFs and do not cross the shadow boundary.

## 3. `ga-dialog`

- [ ] 3.1 New `src/components/dialog/dialog.js` — centred, content-sized, scrim, Escape and scrim-click dismissal, `show()`/`close()`, header/body/footer slots matching `ga-panel`'s vocabulary.
- [ ] 3.2 Reuse `core/focus-trap.js` **unchanged**; always traps (a dialog is modal by definition — no attribute).
- [ ] 3.3 **Background inertness**, which the kit has never had: `inert` on the background, body scroll lock, and the top layer. Restore all of it on close, and survive nested/sequential dialogs without stranding the page.
- [ ] 3.4 **Fix `ga-panel`'s modality bug** rather than inheriting it: `template()` hardcodes `aria-modal="true"` while `_syncModality()` only corrects it under `if (this.overlay)`, so a plain drawer claims modality with no trap installed. Modality must track the trap in every mode.

## 4. `ga-step-list`

- [ ] 4.1 New `src/components/step-list/step-list.js` — an `<ol>` of selectable rows, per-row status, secondary metadata line, optional trailing badge.
- [ ] 4.2 **Two independent cursors**: `current` (what is playing) and `selected` (what the reader chose), rendered distinctly and simultaneously.
- [ ] 4.3 Roving tabindex — one tab stop for the list, arrows between rows, Home/End to the ends.
- [ ] 4.4 Status distinguishable by more than colour (glyph or text), and announced.

## 5. `ga-scrubber`

- [ ] 5.1 New `src/components/scrubber/scrubber.js` — a custom-drawn track implementing the slider ARIA pattern by hand (`role="slider"`, `aria-valuemin/max/now/text`, arrows, Home/End).
- [ ] 5.2 `segments` (start, duration, status, label) rendered as proportional, individually activatable regions; an independent playhead driven by `position`.
- [ ] 5.3 **The two-level hit behaviour**: activating a segment seeks to *its start*; activating the bare track seeks to the clicked point.
- [ ] 5.4 `aria-valuetext` as a human-readable time, not a raw millisecond count.
- [ ] 5.5 **`ga-slider` is not modified.** Confirm it, and document on both pages which to reach for.

## 6. `ga-comment` and `ga-comment-thread`

- [ ] 6.1 New `src/components/comment/comment.js` — author, `<time>`, body, `resolved`, `anchor`; uniform alignment for every author.
- [ ] 6.2 Resolve/reopen control emitting the new state; resolved is conveyed to assistive technology, not by opacity alone.
- [ ] 6.3 New `src/components/comment-thread/comment-thread.js` — a **list**, not a live log, and **no scroll-follow** (design D3).
- [ ] 6.4 A composer above the list: target line, submit control, Cmd/Ctrl+Enter, emitting the text and **not** clearing until the host accepts.
- [ ] 6.5 Empty state that still offers the composer.
- [ ] 6.6 **`ga-chat` / `ga-chat-message` are not touched.** Confirm they render exactly as before.

## 7. Registration, types, docs

- [ ] 7.1 Import and export the six new components in `src/index.js`; add tags to `index.d.ts`, `global.d.ts`, `react.d.ts` — **including the `Ga*Attrs` interface bodies**, not only the tag-map entries (the omission that shipped from #6).
- [ ] 7.2 `npm run types`; commit the regenerated declarations. The `tsconfig.check.json` guard added in #7 must stay green.
- [ ] 7.3 `site/registry.js`: a page per new component. The dialog page documents inertness; the tooltip page documents why it does not supply an accessible name; the comment-thread and chat pages each say when to reach for the other; the scrubber and slider pages likewise.
- [ ] 7.4 **The split-pane recipe** (design D6) — a docs page section composing `ga-panel side="left"` with `ga-tabs`, rather than a container component.
- [ ] 7.5 `README.md` component list.

## 8. Verify and release

- [ ] 8.1 `npm run build`, `npm run bundle`, `npm run types`; exercise every new component in the docs site including keyboard-only paths.
- [ ] 8.2 Screen-reader pass (VoiceOver): dialog modality and inertness, tooltip on focus, step-list positions and statuses, scrubber `aria-valuetext`, comment resolution state.
- [ ] 8.3 Both themes.
- [ ] 8.4 Confirm the additive claims: `ga-select`, `ga-date-input`, `ga-combobox`, `ga-slider`, `ga-chat` and `ga-panel`'s drawer all render exactly as before — except `ga-panel`'s corrected modality, which is the one intended behaviour change.
- [ ] 8.5 Cut a release and note the version on ui-kit#10 so e2e-review#7 can pin it.
