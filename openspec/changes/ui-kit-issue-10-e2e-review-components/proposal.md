## Why

ui-kit#10 lists six component gaps found while restyling **e2e-review**. Before
specifying them, each was checked against the code rather than against the
issue's description — and **three of its premises do not survive that check**.
Saying so first, because two of them change what should be built:

- **"the app uses `@radix-ui/react-dialog` for its comment and settings
  modals"** — it does not. The package is a dependency and
  `components/ui/dialog.tsx` exists, but **nothing imports it**; there are no
  comment modals and no settings surface. The comment composer is inline.
- **"#7 asks for a generic `ga-steps`"** — stale. `ga-steps` was #7's item 10,
  marked *nice to have*, and was **dropped from its scope**: the merged spec
  contains the string zero times, and the identifier exists nowhere in either
  branch. There is no overlap to resolve; the run timeline is greenfield.
- **"navigator | scenario | comments, resizable, collapsing to tabs"** —
  describes a layout the app does not have. The aside is fixed-width and
  off-canvas below `lg`; nothing is resizable and nothing collapses to tabs.
  That item is a **feature request for e2e-review**, not a description of what
  is being restyled.

What remains after that correction is four components worth building, one worth
building for a different reason than the issue gives, and one worth declining.

## What Changes

- **`ga-dialog`** — a centred modal. A **new component**, not a third `ga-panel`
  mode (design D1), reusing `core/focus-trap.js` unchanged. It also brings the
  first background-inertness in the kit: nothing currently sets `inert`, locks
  body scroll, or uses the top layer for a modal.
- **`ga-tooltip`** — built on the existing `core/popup.js`, with two small
  widenings to it (horizontal placement, and opting out of the min-width match
  that suits a listbox and not a six-word label). **`ga-button`'s unlabelled
  warning is deliberately left alone** — a tooltip cannot supply an accessible
  name across a shadow boundary (design D2).
- **`ga-step-list`** — a selectable list of status-bearing rows with two
  independent cursors (playing vs selected). Not a wizard progress indicator,
  and with no `ga-steps` to share a design with.
- **`ga-scrubber`** — a custom-drawn media timeline with **status-coloured,
  individually-clickable segments**. Not a `ga-slider` widening: `<input
  type="range">` structurally cannot render per-segment regions (design D4).
- **`ga-comment` / `ga-comment-thread`** — a review thread. **Separate from
  `ga-chat`, not a widening of it** (design D3). This is the overlap the issue
  asked us to confirm, and the answer is that one design does not cover both.
- **A fix, not a new feature:** `ga-panel` hardcodes `aria-modal="true"` in its
  template while only correcting it for overlay mode, so a plain drawer claims
  modality with no focus trap installed. Whatever ships as `ga-dialog` must fix
  this rather than inherit it.
- **Declined: the split pane.** A documented layout recipe instead, per the
  kit's own precedent (#7 declined a `ga-metric-row` on the same grounds).

## Capabilities

### New Capabilities

- `ui-kit-modality`: `ga-dialog`, background inertness, and the `ga-panel`
  modality fix.
- `ui-kit-tooltip`: `ga-tooltip` and the `core/popup.js` widenings it needs.
- `ui-kit-run-timeline`: `ga-step-list` and `ga-scrubber` — the two components
  that display a run.
- `ui-kit-comment-thread`: `ga-comment` and `ga-comment-thread`.

### Modified Capabilities

<!-- ui-kit's components predate OpenSpec and have no capability specs under
     openspec/specs/, so there is nothing to amend. The `ga-panel` modality fix
     is covered by ui-kit-modality above. -->

## Impact

- **New**: `src/components/{dialog,tooltip,step-list,scrubber,comment,comment-thread}/`.
- **`src/core/popup.js`**: horizontal placement and an opt-out of forced
  min-width. Additive — existing consumers (`ga-select`, `ga-date-input`,
  `ga-combobox`) must be unaffected, asserted not assumed.
- **`src/core/focus-trap.js`**: reused unchanged. It is already shadow-aware and
  factored out precisely so a third consumer costs one import.
- **`src/components/panel/panel.js`**: the `aria-modal` fix only.
- **Registration, types, docs**: `src/index.js`, `index.d.ts`, `global.d.ts`,
  `react.d.ts`, `site/registry.js`, `README.md`.
- **Not touched**: `ga-chat` / `ga-chat-message`. Their `role` attribute is a
  latent defect (it collides with the ARIA global) but fixing it belongs to its
  own issue, not here — see design D3.
- **Backwards compatibility**: everything is additive except the `ga-panel`
  `aria-modal` fix, which corrects a bug rather than changing an intended
  behaviour.
