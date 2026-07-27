## ADDED Requirements

### Requirement: A centred modal dialog

The kit SHALL provide a centred modal dialog, distinct from the drawer and the
floating overlay panel.

#### Scenario: Centred and sized to its content
- **WHEN** a dialog is opened
- **THEN** it is centred in the viewport and sized to its content, rather than
  anchored to an edge or a corner

#### Scenario: A scrim is present
- **WHEN** a dialog is open
- **THEN** a scrim covers the page beneath it — unlike the overlay panel, which
  deliberately has none

#### Scenario: Focus is confined without being asked
- **WHEN** a dialog opens
- **THEN** focus moves into it and is confined to it, with no attribute needed —
  a dialog is modal by definition

#### Scenario: Focus returns to the opener
- **WHEN** a dialog closes
- **THEN** focus returns to the element that opened it, provided that element is
  still in the document

#### Scenario: Dismissal
- **WHEN** Escape is pressed or the scrim is activated
- **THEN** the dialog closes and emits a close event

#### Scenario: It reuses the existing focus trap
- **WHEN** the dialog confines focus
- **THEN** it uses the kit's existing shared focus-trap implementation rather
  than a second one

### Requirement: The page behind a modal is inert

While a modal is open, the rest of the page SHALL be unreachable — not merely
un-tabbable.

#### Scenario: Pointer interaction is blocked
- **WHEN** a dialog is open and a control behind it is clicked
- **THEN** that control does not activate

#### Scenario: Assistive technology cannot traverse the background
- **WHEN** a dialog is open
- **THEN** content outside it is hidden from assistive technology, not just
  skipped by the Tab key

#### Scenario: The page does not scroll underneath
- **WHEN** a dialog is open and the user scrolls
- **THEN** the page behind does not scroll

#### Scenario: Everything is restored on close
- **WHEN** the dialog closes
- **THEN** background interactivity, assistive-technology visibility and
  scrolling are all restored to what they were

#### Scenario: Nested or sequential modals do not strand the page
- **WHEN** more than one modal is opened and closed in sequence
- **THEN** the background is restored exactly once everything is closed, and
  never left permanently inert

### Requirement: A non-modal panel does not claim to be modal

An element SHALL NOT announce itself as modal unless it is actually confining
focus.

#### Scenario: A drawer that traps nothing
- **WHEN** the drawer panel is open without focus trapping
- **THEN** it does not advertise itself as a modal dialog to assistive
  technology

#### Scenario: Modality tracks the trap
- **WHEN** focus trapping is enabled or disabled on a panel
- **THEN** its advertised modality follows that setting, in every mode rather
  than only in overlay mode

#### Scenario: The dialog is always modal
- **WHEN** the dialog is open
- **THEN** it advertises modality, because it always traps
