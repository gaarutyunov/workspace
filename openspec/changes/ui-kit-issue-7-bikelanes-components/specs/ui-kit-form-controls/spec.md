## ADDED Requirements

### Requirement: Checkbox

The kit SHALL provide a checkbox element for a single boolean choice, distinct
from the toggle switch.

#### Scenario: Toggling
- **WHEN** the user activates the checkbox or its label
- **THEN** its checked state flips and a change event carrying the new state is
  dispatched

#### Scenario: Form participation
- **WHEN** a named, checked checkbox inside a form is submitted
- **THEN** the form data carries its name and value

#### Scenario: Indeterminate
- **WHEN** the checkbox is set indeterminate
- **THEN** it renders a mixed state and reports that state to assistive
  technology

#### Scenario: Toggling out of the mixed state
- **WHEN** the user activates a checkbox that is in the mixed state
- **THEN** it becomes checked — the behaviour a "select all" over a partial
  selection depends on — and stops reporting the mixed state

#### Scenario: Disabled
- **WHEN** the checkbox is disabled
- **THEN** it cannot be toggled and contributes no value to form submission

### Requirement: Icon-only buttons

The button element SHALL support a glyph-only presentation with a square
footprint, and SHALL require an accessible name for it.

#### Scenario: Square glyph button
- **WHEN** a button is rendered in the icon size with a single glyph
- **THEN** it occupies a square footprint with the glyph centred, in every
  existing visual variant

#### Scenario: Missing accessible name
- **WHEN** an icon-only button is rendered with neither an aria-label nor a title
- **THEN** the component reports the omission to the developer

### Requirement: Slider with labelled ends

The slider SHALL be able to label both ends of its range and to suppress its
numeric readout.

#### Scenario: Both ends labelled
- **WHEN** start and end labels are supplied
- **THEN** the slider renders them at the ends of the track

#### Scenario: Readout suppressed
- **WHEN** the numeric readout is suppressed
- **THEN** no value is displayed while the value is still reported to assistive
  technology and to change events

#### Scenario: Existing usage unchanged
- **WHEN** a slider is used with only its original single label
- **THEN** it renders exactly as before

### Requirement: Input adornments and readonly presentation

The input element SHALL accept leading and trailing content inside the field, and
SHALL support a readonly presentation that keeps the field's appearance.

#### Scenario: Leading and trailing content
- **WHEN** leading and/or trailing content is supplied
- **THEN** it renders inside the field's frame, and the field's focus treatment
  still tracks the text entry

#### Scenario: Trailing action
- **WHEN** the trailing content is an interactive control
- **THEN** it is reachable by keyboard without leaving the field's focus
  treatment inconsistent

#### Scenario: Readonly value row
- **WHEN** the input is readonly
- **THEN** its value is displayed in the field's shape but cannot be edited

#### Scenario: Existing usage unchanged
- **WHEN** an input is used without adornments
- **THEN** it renders exactly as before

### Requirement: Compact file picker

The kit SHALL provide a compact control that opens the file dialog, for places a
drop area is too large.

#### Scenario: Choosing a file
- **WHEN** the user activates the control and chooses one or more files
- **THEN** the same file event the drop area emits is dispatched, carrying the
  chosen files

#### Scenario: Accepted types
- **WHEN** accepted types are configured
- **THEN** the file dialog filters to them

### Requirement: Combobox with asynchronous suggestions

The kit SHALL provide a combobox: a text input with a suggestion list whose
options are supplied by the host application as the user types.

#### Scenario: Suggestions appear as the user types
- **WHEN** the user types and the host supplies matching options
- **THEN** the suggestions are shown in a listbox beneath the field

#### Scenario: Host-driven filtering
- **WHEN** the user types
- **THEN** a debounced filter event carrying the typed text is dispatched so the
  host can fetch results

#### Scenario: Choosing a suggestion
- **WHEN** the user activates a suggestion by pointer or keyboard
- **THEN** the field takes that value and a change event carrying it is
  dispatched

#### Scenario: No results
- **WHEN** the host supplies no options for the typed text
- **THEN** the listbox reports that nothing matched instead of showing an empty
  box

#### Scenario: Announced as a combobox
- **WHEN** a screen reader focuses the control
- **THEN** it is announced as a combobox, and the active suggestion is announced
  as the user moves through the list
