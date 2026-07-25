## ADDED Requirements

### Requirement: Panel as an overlay

The panel element SHALL support floating above page content instead of sitting in
the document flow.

#### Scenario: Floating above a canvas
- **WHEN** a panel is placed in overlay mode over a full-bleed canvas
- **THEN** it renders above the canvas with the kit's elevated surface treatment,
  without the application setting its own stacking values

#### Scenario: Stacking is documented
- **WHEN** an application needs to place its own content relative to the overlay
- **THEN** the stacking level the overlay uses is exposed as a theme token rather
  than being an internal constant

#### Scenario: In-flow behaviour unchanged
- **WHEN** a panel is used without overlay mode
- **THEN** it renders in the flow exactly as before

### Requirement: Bottom sheet on narrow viewports

The kit SHALL provide the same overlay content as a bottom sheet for narrow
viewports, dismissible by gesture and by keyboard.

#### Scenario: Sheet presentation
- **WHEN** the overlay is presented as a bottom sheet
- **THEN** it is anchored to the bottom of the viewport and can be dismissed by
  dragging it down

#### Scenario: Keyboard dismissal
- **WHEN** the sheet is open and the user presses Escape
- **THEN** it closes and focus returns to whatever opened it

#### Scenario: Documented breakpoint
- **WHEN** a developer follows the documented composition
- **THEN** the viewport width at which a panel becomes a sheet is stated rather
  than left to guesswork
