## Context

Three restyle issues now point at the kit — #6 (workout, merged), #7
(bikelanes, in review) and this one. The issue's own framing is that the
overlapping items should be designed once rather than three times. That is the
right instinct, and checking it against the code is what this design does.

The relevant state, verified rather than assumed:

- **`core/popup.js`** (merged with #6) — top-layer `popover="manual"`,
  viewport-rect positioning, flip-above, outside-pointerdown / Escape / scroll
  dismissal, `composedPath()` shadow-aware hit testing. Used by `ga-select`,
  `ga-date-input`, `ga-combobox`. It flips **vertically only** and forces
  `panel.style.minWidth = rect.width`.
- **`core/focus-trap.js`** (on #7's branch) — shadow-aware: splices
  `slot.assignedElements({flatten: true})` in rendering order, treats
  `delegatesFocus` hosts as one stop, captures the opener on `activate()` and
  restores only if still `isConnected`.
- **`ga-panel`** — `role="dialog"`, a scrim, Escape close, header/body/footer,
  `show()/close()`, and `trap-focus`. Overlay mode deletes the scrim on purpose.
- **`ga-chat` / `ga-chat-message`** (merged with #6) — a chat transcript with
  left/right alignment by `role`, `role="log"` + `aria-live="polite"`, and
  conditional scroll-follow.

## Goals / Non-Goals

**Goals:**

- Build what the restyle actually needs, on evidence rather than on the issue's
  description of the app.
- Reuse `core/popup.js` and `core/focus-trap.js` rather than growing second
  implementations.
- Resolve the two overlaps the issue flagged, in writing, either way.

**Non-Goals:**

- Widening `ga-chat` into a review thread (D3).
- Widening `ga-slider` into a segmented scrubber (D4).
- A split-pane *container* (D6) — the divider alone ships, as `ga-splitter`.
- Any change to `ga-chat`'s or `ga-chat-message`'s behaviour. The only edit
  there is the `role` → `from` rename (D3); the components keep their
  vocabulary and their layout.

## Decisions

### D1: `ga-dialog` is a new component, not a third `ga-panel` mode

#7's design D5 justified overlay-as-a-mode because a floating control surface
and a drawer "differ only in where they sit and what they let through". A modal
differs on the axis D5 said was **shared**: it is a different modality.

Concretely, every geometry rule in `ga-panel` is edge-anchored — `position:
fixed; top: 0; right: 0; height: 100%; transform: translateX(100%)` — and
overlay mode re-anchors to a corner with a horizontal slide. A dialog is
centred, fits its content, and scales rather than slides. Overlay mode also
*deletes* the scrim (`:host([overlay]) .scrim { display: none }`), which a
dialog needs back. A third mode would mean a third gated branch in the
positioning, the transform and the scrim rules, plus a third policy in
`_syncModality` — making selector arithmetic the dominant cost of the file.

The expensive part is the focus trap, and it is already in `core/` precisely so
a third consumer costs one import.

**What genuinely remains beyond the trap**, none of which exists in the kit
today: centring and content-sized geometry, the scrim restored, **background
inertness** (no `inert`, no `<dialog>`/`showModal`, no body scroll lock anywhere
in the kit — the trap handles Tab but not pointer or screen-reader traversal,
and the page still scrolls underneath), and the top layer.

**A bug to fix rather than inherit:** `panel.js` hardcodes `aria-modal="true"`
in `template()` (line 160) and `_syncModality()` only corrects it inside `if
(this.overlay)` (line 207). So a plain drawer announces itself as modal while
`trapFocus` is false and no trap is installed.

### D2: A tooltip does not satisfy the accessible-name requirement

`ga-button size="icon"` warns when it has neither `aria-label` nor `title`. The
tempting change is to teach that warning about tooltips. **It must not learn**,
for a reason that is structural rather than stylistic:

`GaElement` attaches its shadow root with `delegatesFocus: true`, so the
focusable element is the `<button>` *inside* `ga-button`'s shadow root. An
external `<ga-tooltip>` renders in *its own* tree, and `aria-labelledby` /
`aria-describedby` are IDREFs that **do not cross shadow roots**. A tooltip is
therefore decoration; the name still has to arrive via `aria-label` or `title`
on the host.

The coupling that *is* worth specifying is the opposite one: when a tooltip
wraps a trigger carrying `title`, the native browser tooltip and the styled one
would both appear. So `ga-tooltip` adopts its trigger's `title` as its text and
removes the attribute from the trigger — keeping the accessible name intact.

**`core/popup.js` needs two small widenings**: horizontal placement (it flips
vertically only), and an opt-out of `minWidth = rect.width` — sensible under a
field, wrong for a six-word label over a 40px button.

### D3: The review thread is a separate component from `ga-chat`

This is the overlap the issue asked us to confirm. **One design does not cover
both**, on six specific points:

1. **Alignment is the whole design of chat.** `:host([role="user"]) .row {
   align-items: flex-end }` and an inverse-filled bubble — a "me vs them" axis.
   A review thread is a flat list of uniformly-aligned cards; there is no such
   axis in code review, and none in the app's data.
2. **`role` is the wrong attribute name and widening it is the moment the
   collision bites.** `ga-chat-message` observes `role`, so the host literally
   carries `role="user"` — the ARIA global. Today `user`/`assistant` are invalid
   tokens, so browsers ignore them and it is silently harmless. But `comment`
   **is** a real ARIA role, so extending the vocabulary would make the host
   start claiming one by accident.
3. **`role="log"` + `aria-live="polite"` is wrong for comments.** A log is a
   live, time-ordered stream; a review thread is a static list you read and
   navigate.
4. **Scroll-follow is actively wrong.** Chat pins to the newest message and
   watches `characterData` for streaming tokens. Adding a comment must not yank
   the reader to the bottom.
5. **The composer is not provided** — chat's footer is a bare slot. A review
   composer sits *above* the list, carries a "commenting on …" target line, and
   submits on Cmd/Ctrl+Enter.
6. **Three axes have no home**: resolve/reopen, a resolved dimmed state, and an
   anchor target. `state` is `sent|pending|streaming|error` — delivery, not
   triage.

What genuinely deserves sharing is one level down — a card surface and an
author+time meta row — and that is `ga-card` plus a few lines of CSS.

**The rename is folded in here rather than raised separately** (owner's call:
no additional issue). `ga-chat-message`'s `role` becomes **`from`**, keeping the
`user | assistant | system` vocabulary. The values do not change; only the
attribute name does.

This is a **breaking change**: v0.3.0 shipped `role`, so anyone pinning it must
update. It is still worth doing now — the only consumer is the workout restyle,
and the collision gets worse the longer the vocabulary lives, since `comment`
and other real ARIA roles make an accidental claim possible the moment anyone
extends it.

### D4: The scrubber is custom-drawn, not a widened `ga-slider`

The issue asks for "range + tick marks". What the app has is **not** that: a
`role="slider"` track containing one absolutely-positioned button *per step*,
each with `left`/`width` as percentages and a **status colour**, plus an
independent playhead, where clicking a segment seeks to *its own start* rather
than to the click position.

`<input type="range">` cannot render that at any price — no per-region children,
no way to colour intervals, one movable mark. So `ga-scrubber` implements the
slider ARIA pattern by hand over a custom track.

**The cheap-vs-real fork, stated because the issue's words describe the cheap
one:** mere tick marks genuinely *would* be a `ga-slider` widening — `list=` +
`<datalist>` gets native tick rendering free. That would satisfy the issue's
sentence and none of the app's needs. We build the real one; ticks-only is not
worth a release.

### D5: `ga-step-list`, with no sibling to design with

`ga-steps` does not exist — not shipped, not specified, not planned. What the
app needs is a **selectable** list, not a read-only progress indicator: an
`<ol>` of buttons, a per-row status glyph, a secondary metadata line, and **two
independent cursors** — what is playing versus what the user clicked.

A wizard-style `ga-steps` and this share a vertical rail and little else. Should
a turn-by-turn list ever be built, it is a degenerate case of this component
rather than the other way round.

### D6: Ship the divider alone as `ga-splitter`, not a split-pane container

The premise is not real — the app has no split pane and nothing resizable. The
kit's own precedent is against speculative containers: #7's D5a declined a
`ga-metric-row` because "a wrapper whose whole job is `display: grid` does not
clear that bar". A split pane is that argument with a drag handle attached.

The reusable half is already in the kit: a side region collapsing off-canvas
with a scrim *is* `ga-panel side="left"`, and `ga-tabs` covers collapse-to-tabs.
What is left is drag-to-resize — pointer capture, clamping, persistence,
keyboard resizing, RTL — with one consumer and a high cost, which an app can do
in ~40 lines of CSS grid.

**So the decision is: build only the divider**, as `ga-splitter` — a
keyboard-accessible `role="separator"` that writes a CSS custom property,
leaving the grid to the app. That owns the part apps get wrong and matches how
`ga-metric` was scoped: the primitive, not the container.

**On the name**, since it was considered and rejected: `ga-divider` reads
better until you remember that in most kits a divider is a *static* rule — the
`<hr>` equivalent — and this one is a drag handle. Taking that name would leave
nothing sensible for the decorative separator the kit will eventually want.

## Risks / Trade-offs

- **[`ga-dialog`'s premise is false]** — nothing in e2e-review is blocked on it,
  because there are no modals. It is kept because it is the one *general* gap of
  the six and the trap already exists, **not** because the restyle needs it. If
  the owner would rather ship only what unblocks the restyle, this is the first
  thing to cut and the split pane the second.
- **[Background inertness is new ground for the kit]** — `inert`, scroll lock
  and the top layer have no precedent here, so `ga-dialog` carries more novel
  risk than its component count suggests.
- **[Widening `core/popup.js` touches three shipped consumers]** — additive, but
  `ga-select`, `ga-date-input` and `ga-combobox` must be proven unaffected, not
  assumed.
- **[Two components serve one app]** — `ga-step-list` and `ga-scrubber` are
  shaped by e2e-review's run view. The generic core is real, but they should be
  reviewed for over-fitting.

## Open Questions

- None outstanding. Both questions this spec originally raised were answered by
  the owner: the `ga-chat-message` rename is folded in here rather than filed
  separately, and the split pane ships as the `ga-splitter` divider alone.
