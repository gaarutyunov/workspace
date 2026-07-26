## ADDED Requirements

### Requirement: Chart design tokens

The kit SHALL expose documented `--ga-chart-*` design tokens so charts drawn by
an application's own charting library read as part of the design system.

#### Scenario: Ordered categorical series palette
- **WHEN** an application colours chart series from the palette tokens in order
- **THEN** consecutive series are visually distinguishable from each other and
  legible against the page background

#### Scenario: The default ordering is colour-blind-safe
- **WHEN** the palette tokens are used in order and the result is viewed under
  simulated deuteranopia and protanopia
- **THEN** the series remain distinguishable from one another, without the
  application selecting or overriding an alternate palette

#### Scenario: Earlier tokens are the most separable
- **WHEN** a chart uses only the first few tokens of the palette
- **THEN** those series are at least as distinguishable under the same simulations
  as any equally sized selection taken later in the palette

#### Scenario: Colour is not the only channel a legend relies on
- **WHEN** a series is identified in a legend
- **THEN** its label accompanies the colour swatch, so the mapping survives for a
  viewer who cannot separate two hues at all

#### Scenario: Chart chrome tokens
- **WHEN** an application styles chart axes, gridlines, labels and tooltips
- **THEN** tokens are available for each of those surfaces, matching the kit's
  border, muted-text and elevated-surface treatments

#### Scenario: Both themes
- **WHEN** the page is in the dark theme or the light theme
- **THEN** the chart tokens resolve to values appropriate for that theme without
  the application redefining them

#### Scenario: Overridable
- **WHEN** an application overrides a chart token
- **THEN** charts and the kit's chart container both pick up the override

### Requirement: Chart container

The kit SHALL provide a `ga-chart-frame` element that supplies the layout around
a chart — title, optional legend, and a responsive plot area — while the chart
itself is provided by the application.

#### Scenario: Framing an application-rendered chart
- **WHEN** an application slots a chart (from any library, or raw SVG) into the
  frame
- **THEN** the frame renders it inside a titled, house-styled container that
  fills the available width

#### Scenario: Legend from series metadata
- **WHEN** series names and colours are supplied to the frame
- **THEN** it renders a legend using the chart palette tokens

#### Scenario: Empty and loading states
- **WHEN** the frame is marked as loading, or has no data to show
- **THEN** it renders the corresponding state in place of the plot area instead
  of an empty box

### Requirement: No charting engine in the kit

The kit SHALL NOT implement or bundle chart rendering; drawing remains the
application's responsibility.

#### Scenario: Frame draws no data
- **WHEN** the chart container is used
- **THEN** it lays out and themes its slotted content and draws no axes, scales
  or series of its own

#### Scenario: Dependency-free
- **WHEN** the kit is installed or the standalone bundle is loaded
- **THEN** no charting library is pulled in
