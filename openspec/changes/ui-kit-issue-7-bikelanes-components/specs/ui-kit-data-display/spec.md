## ADDED Requirements

### Requirement: Metric tile

The kit SHALL provide a tile that presents **one** metric — a value with the
caption naming it. It is not a tabular presentation: a set of tiles has no
header row and no shared columns, and each tile may carry a different unit.
Tabular data remains the table element's job.

#### Scenario: Value and caption
- **WHEN** a value and a caption are supplied
- **THEN** the tile renders the value prominently with the caption subordinate to
  it

#### Scenario: Unit
- **WHEN** a unit is supplied
- **THEN** it is rendered with the value without competing with it for emphasis

#### Scenario: A group of tiles aligns
- **WHEN** several tiles with differently sized values sit beside each other
- **THEN** their values and captions align on shared baselines, without the
  application restating the type scale

#### Scenario: A primary metric among subordinate ones
- **WHEN** one tile in a group is marked as the primary readout
- **THEN** it is rendered at a larger scale than its neighbours while still
  aligning with them

#### Scenario: Missing value
- **WHEN** a tile has no value yet
- **THEN** it renders a placeholder and keeps its footprint, so a group does not
  reflow when values arrive

#### Scenario: Layout stays with the application
- **WHEN** a developer arranges a group of tiles
- **THEN** the kit documents a layout recipe rather than shipping a container
  element, so no wrapper component has to be adopted to place them

### Requirement: Inline status line

The kit SHALL provide a single-line status message with neutral, success and
error tones.

#### Scenario: Tone
- **WHEN** a status is shown with a tone
- **THEN** it is rendered in that tone's colour from the theme

#### Scenario: Announced
- **WHEN** the status text changes
- **THEN** assistive technology announces the new text without the element taking
  focus

#### Scenario: Empty status holds its place
- **WHEN** the status has no text
- **THEN** it occupies its line rather than collapsing and shifting the
  surrounding layout
