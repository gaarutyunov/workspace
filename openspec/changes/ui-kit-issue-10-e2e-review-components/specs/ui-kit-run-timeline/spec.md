## ADDED Requirements

### Requirement: A selectable list of status-bearing steps

The kit SHALL provide a vertical list of steps where each row carries a status
and is individually selectable — a navigator, not a read-only progress
indicator.

#### Scenario: Rows are selectable
- **WHEN** a row is activated by pointer or keyboard
- **THEN** the component emits a selection event naming that row

#### Scenario: A status per row
- **WHEN** a row declares a status
- **THEN** it renders a distinct indicator for that status, distinguishable by
  more than colour alone

#### Scenario: Two independent cursors
- **WHEN** one row is marked as current and a different row is selected
- **THEN** both are shown distinctly and at the same time — what is playing and
  what the reader chose are different questions

#### Scenario: Keyboard navigation
- **WHEN** the list has focus
- **THEN** arrow keys move between rows and Home/End reach the ends, with a
  single tab stop for the list

#### Scenario: Secondary metadata
- **WHEN** a row supplies secondary text such as an offset or a duration
- **THEN** it is rendered subordinate to the row's title

#### Scenario: It is a list to assistive technology
- **WHEN** the list is read by assistive technology
- **THEN** it is announced as a list of items with their positions and statuses

### Requirement: A media scrubber with status-bearing segments

The kit SHALL provide a media timeline whose track is divided into segments,
each with its own extent and status, and each individually activatable.

#### Scenario: Segments span their own extents
- **WHEN** segments are supplied with start and duration
- **THEN** each occupies its proportional span of the track

#### Scenario: A segment seeks to its own start
- **WHEN** a segment is activated
- **THEN** the reported position is that segment's start, not the point that was
  clicked

#### Scenario: The track itself seeks to the clicked point
- **WHEN** the track is activated away from any segment
- **THEN** the reported position corresponds to where it was clicked

#### Scenario: A playhead independent of the segments
- **WHEN** the current position changes
- **THEN** the playhead moves accordingly, without altering segment rendering

#### Scenario: Keyboard operation
- **WHEN** the scrubber has focus
- **THEN** arrow keys step the position and Home/End reach the ends, and the
  current position is announced as a human-readable time rather than a raw
  number

#### Scenario: Status is not carried by colour alone
- **WHEN** segments carry differing statuses
- **THEN** they are distinguishable without relying on colour perception

### Requirement: The existing slider is unchanged

Adding the scrubber SHALL NOT alter the existing slider component.

#### Scenario: The slider keeps its native foundation
- **WHEN** the slider is used after this change
- **THEN** it behaves exactly as before, retaining its native range input and
  form participation

#### Scenario: The documentation says which to reach for
- **WHEN** a developer reads either component's page
- **THEN** it states that a plain value uses the slider and a segmented media
  timeline uses the scrubber
