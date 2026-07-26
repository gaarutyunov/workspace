## ADDED Requirements

### Requirement: Quantity

The kit SHALL provide an element presenting a **quantity** — a single measured
value with its unit. It expresses one value, not a summary of a distribution.

#### Scenario: Value and unit
- **WHEN** a value and a unit are supplied
- **THEN** both are rendered together, with the unit subordinate to the value
  rather than competing with it for emphasis

#### Scenario: Unitless quantity
- **WHEN** no unit is supplied
- **THEN** the value is rendered alone, with no leftover spacing where a unit
  would have been

#### Scenario: Missing value
- **WHEN** the quantity has no value yet
- **THEN** a placeholder is rendered in the value's place

#### Scenario: Usable inline
- **WHEN** a quantity is placed inside a line of text or a table cell
- **THEN** it flows with the surrounding content rather than imposing a block of
  its own

### Requirement: Metric

The kit SHALL provide a **metric** — a quantity that carries the label naming
what was measured — built on the quantity element rather than re-implementing
it.

A group of metrics is not a tabular presentation: it has no header row and no
shared columns, its members may carry different units, and one of them may be
emphasised over the others. Tabular data remains the table element's job.

#### Scenario: Label and quantity
- **WHEN** a label, a value and an optional unit are supplied
- **THEN** the metric renders the quantity prominently with the label subordinate
  to it

#### Scenario: A group of metrics aligns
- **WHEN** several metrics with differently sized values sit beside each other
- **THEN** their values and labels align on shared baselines, without the
  application restating the type scale

#### Scenario: A primary metric among subordinate ones
- **WHEN** one metric in a group is marked as the primary readout
- **THEN** it is rendered at a larger scale than its neighbours while still
  aligning with them

#### Scenario: Missing value
- **WHEN** a metric has no value yet
- **THEN** it renders a placeholder and keeps its footprint, so a group does not
  reflow when values arrive

#### Scenario: Layout stays with the application
- **WHEN** a developer arranges a group of metrics
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
