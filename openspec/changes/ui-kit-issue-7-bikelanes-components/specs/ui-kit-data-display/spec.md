## ADDED Requirements

### Requirement: Stat tile

The kit SHALL provide a tile that presents one value with its caption.

#### Scenario: Value and caption
- **WHEN** a value and a caption are supplied
- **THEN** the tile renders the value prominently with the caption subordinate to
  it

#### Scenario: Unit
- **WHEN** a unit is supplied
- **THEN** it is rendered with the value without competing with it for emphasis

#### Scenario: A row of tiles aligns
- **WHEN** several tiles with differently sized values sit in a row
- **THEN** their values and captions align on shared baselines

#### Scenario: Missing value
- **WHEN** a tile has no value yet
- **THEN** it renders a placeholder and keeps its footprint, so a row does not
  reflow when values arrive

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
