## ADDED Requirements

### Requirement: A draggable, keyboard-operable splitter

The kit SHALL provide a splitter: the divider between two regions, which
reports its position and leaves the layout to the consuming application.

#### Scenario: Dragging moves it
- **WHEN** the splitter is dragged
- **THEN** it reports the new position continuously, and the application's
  layout follows

#### Scenario: The position is published as a CSS custom property
- **WHEN** the splitter moves
- **THEN** it writes the position to a CSS custom property the application's own
  layout can read, so no container component is required

#### Scenario: Keyboard operation
- **WHEN** the splitter has focus
- **THEN** arrow keys move it by a step, Home and End take it to its bounds, and
  it is a single tab stop

#### Scenario: It announces itself correctly
- **WHEN** the splitter is read by assistive technology
- **THEN** it is announced as a separator with its current and permitted values

#### Scenario: Bounds are respected
- **WHEN** a minimum or maximum is declared and the splitter is dragged or
  keyed past it
- **THEN** it stops at the bound rather than passing it

#### Scenario: Pointer capture survives leaving the element
- **WHEN** the pointer moves outside the splitter mid-drag
- **THEN** the drag continues until the pointer is released

### Requirement: The splitter is not a layout container

The splitter SHALL NOT own the regions it divides.

#### Scenario: The application owns the grid
- **WHEN** a developer uses the splitter
- **THEN** they place it between their own elements and write their own layout,
  rather than nesting content inside a kit-provided container

#### Scenario: The collapse behaviour is documented, not built
- **WHEN** a developer needs a region that collapses on a narrow viewport
- **THEN** the documentation directs them to the existing panel and tabs
  components rather than a new one

#### Scenario: The name reflects what it does
- **WHEN** a developer looks for a static decorative rule
- **THEN** the splitter is not it — the name is reserved for the interactive
  handle, leaving the decorative separator its own name
