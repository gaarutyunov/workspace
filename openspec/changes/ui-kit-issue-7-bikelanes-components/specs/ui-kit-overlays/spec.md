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

### Requirement: Focus containment is configurable

Because an overlay may be a modal sheet or a persistent control panel, whether it
confines keyboard focus SHALL be a configuration of the element rather than a
fixed behaviour.

#### Scenario: Persistent panel does not confine focus
- **WHEN** an overlay panel is shown without focus containment configured
- **THEN** keyboard focus moves out of it into the rest of the page as it would
  from any in-flow content

#### Scenario: Modal overlay confines focus
- **WHEN** focus containment is configured on an overlay
- **THEN** keyboard focus cycles within it while it is open, and returns to
  whatever opened it when it closes

#### Scenario: The sheet is modal by default
- **WHEN** the overlay is presented as a bottom sheet
- **THEN** it confines focus without the application configuring it, because it
  covers the content beneath it

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
