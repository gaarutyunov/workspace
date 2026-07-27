## ADDED Requirements

### Requirement: A styled tooltip on hover and focus

The kit SHALL provide a tooltip that labels a trigger on hover **and** on
keyboard focus, replacing the browser's native `title` presentation.

#### Scenario: Shown on hover
- **WHEN** the pointer rests on the trigger
- **THEN** the tooltip appears after a short delay and disappears when the
  pointer leaves

#### Scenario: Shown on keyboard focus
- **WHEN** the trigger receives focus from the keyboard
- **THEN** the tooltip appears — a hover-only tooltip is unreachable for a
  keyboard user

#### Scenario: Dismissible while the trigger keeps focus
- **WHEN** Escape is pressed while a tooltip is shown
- **THEN** the tooltip hides and the trigger keeps focus

#### Scenario: It reuses the existing popup primitive
- **WHEN** the tooltip positions itself
- **THEN** it uses the kit's existing anchored-popup implementation rather than
  a second one

#### Scenario: It is not a focus stop
- **WHEN** the user tabs through the page
- **THEN** the tooltip itself never receives focus

### Requirement: A tooltip does not replace an accessible name

A tooltip SHALL be treated as decoration. It SHALL NOT be accepted as a
substitute for a trigger's accessible name.

#### Scenario: An unlabelled icon button still warns
- **WHEN** an icon-only button has no accessible name but is wrapped in a
  tooltip
- **THEN** the development warning about the missing name still fires

#### Scenario: The reason is documented
- **WHEN** a developer reads the tooltip's documentation
- **THEN** it states that the label cannot cross the shadow boundary, so the
  trigger still needs its own accessible name

### Requirement: A tooltip suppresses the native one

Where a trigger carries a native title, the styled tooltip and the browser's own
SHALL NOT both appear.

#### Scenario: The native tooltip does not double up
- **WHEN** a tooltip wraps a trigger that carries a native title
- **THEN** only the styled tooltip is shown on hover

#### Scenario: The accessible name survives suppression
- **WHEN** the native title is suppressed
- **THEN** the trigger's accessible name is unchanged — suppressing the
  presentation must not remove the name

### Requirement: The popup primitive supports a tooltip's geometry

The shared popup implementation SHALL support placements and sizing a tooltip
needs, without changing behaviour for its existing consumers.

#### Scenario: Horizontal placement
- **WHEN** a tooltip is placed to the side of its trigger
- **THEN** the popup positions it there and flips to the opposite side when
  there is no room

#### Scenario: Width is not forced to the trigger's
- **WHEN** a tooltip is narrower or wider than its trigger
- **THEN** it is sized to its own content, not stretched to match the trigger

#### Scenario: Existing consumers are unaffected
- **WHEN** the existing popup consumers are exercised after the change
- **THEN** each behaves exactly as before, including matching the trigger's
  width where it did so previously
