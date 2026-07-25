## ADDED Requirements

### Requirement: Select from a list of options

The kit SHALL provide a `ga-select` element that presents a list of options and
lets the user choose one, styled in the house design system rather than by
browser chrome.

#### Scenario: Choosing an option
- **WHEN** the user opens the select and activates an option
- **THEN** the element's value becomes that option's value, the trigger shows its
  label, and the popup closes

#### Scenario: Options supplied as data or as markup
- **WHEN** options are provided either as a JSON `options` attribute or as
  slotted `<option>` children
- **THEN** the element presents the same list in both cases

#### Scenario: Disabled options
- **WHEN** an option is marked disabled
- **THEN** it is announced as disabled and cannot be chosen

### Requirement: Multiple selection

`ga-select` SHALL support selecting more than one option when configured for it,
exposing the selection as a list of values.

#### Scenario: Selecting several options
- **WHEN** the select is in multiple mode and the user activates two options
- **THEN** both are selected, the value contains both, and the popup stays open

#### Scenario: Deselecting
- **WHEN** the user activates an already-selected option in multiple mode
- **THEN** that option is removed from the value

### Requirement: Filtering long option lists

`ga-select` SHALL let the user narrow the option list by typing when filtering is
enabled, and SHALL let the host application supply the filtered options itself.

#### Scenario: Typed filter narrows the list
- **WHEN** filtering is enabled and the user types text
- **THEN** only options whose label matches the text (case-insensitively) are
  shown

#### Scenario: No option matches
- **WHEN** the typed text matches no option
- **THEN** the popup reports that nothing matched instead of showing an empty box

#### Scenario: Application-driven options
- **WHEN** the user types
- **THEN** the element emits a filter event carrying the typed text, so an
  application can replace the option list with results it fetched

### Requirement: Keyboard and assistive-technology support

`ga-select` SHALL be operable by keyboard alone and SHALL expose combobox /
listbox semantics to assistive technology.

#### Scenario: Keyboard navigation
- **WHEN** the select has focus
- **THEN** the popup can be opened, options moved through, one chosen, and the
  popup dismissed, entirely from the keyboard

#### Scenario: Announced as a combobox
- **WHEN** a screen reader focuses the element
- **THEN** it is announced as a combobox with its current value, and the active
  option is announced as the user moves through the list

#### Scenario: Dismissal
- **WHEN** the popup is open and the user presses Escape or clicks outside it
- **THEN** the popup closes and focus returns to the trigger

### Requirement: Form participation and change events

`ga-select` SHALL participate in native form submission and SHALL emit events
carrying its value, consistent with the kit's other value-bearing elements.

#### Scenario: Submitted with a form
- **WHEN** a named select inside a form has a value and the form is submitted
- **THEN** the form data contains that name and value

#### Scenario: Change event
- **WHEN** the value changes through user interaction
- **THEN** a change event is dispatched whose detail carries the new value

#### Scenario: Disabled select
- **WHEN** the select is disabled
- **THEN** it cannot be opened, and it contributes no value to form submission
