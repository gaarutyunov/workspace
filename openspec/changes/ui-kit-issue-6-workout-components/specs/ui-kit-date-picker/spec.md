## ADDED Requirements

### Requirement: Calendar month grid

The kit SHALL provide a `ga-calendar` element that renders a month of dates in
the house style and lets the user select a day.

#### Scenario: Selecting a day
- **WHEN** the user activates a day in the grid
- **THEN** the calendar's value becomes that date and a change event carrying the
  date is dispatched

#### Scenario: Moving between months
- **WHEN** the user moves to the previous or next month
- **THEN** the grid shows that month, and the selected date stays selected when
  it is displayed again

#### Scenario: Today and selection are distinguishable
- **WHEN** the grid includes today's date
- **THEN** today is visually distinct from both unselected days and the selected
  day

### Requirement: Locale-aware presentation with a stable value format

`ga-calendar` and `ga-date-input` SHALL present dates according to a configurable
locale while exchanging values in an unambiguous `YYYY-MM-DD` form.

#### Scenario: Localised weekday and month labels
- **WHEN** a locale is configured
- **THEN** weekday and month labels are rendered for that locale

#### Scenario: First day of the week
- **WHEN** the first day of the week is configured
- **THEN** the grid's columns start on that day; otherwise the locale's
  convention is used

#### Scenario: Value format is independent of locale
- **WHEN** a date is selected in any locale
- **THEN** the exposed value is the `YYYY-MM-DD` string for that calendar date

### Requirement: Date bounds

Both elements SHALL support minimum and maximum selectable dates.

#### Scenario: Out-of-range days are not selectable
- **WHEN** a minimum and/or maximum is configured
- **THEN** days outside the range are shown as unavailable and cannot be selected

#### Scenario: Out-of-range typed input
- **WHEN** the user types a date outside the range into the date input
- **THEN** the input reports the value as invalid and does not adopt it

### Requirement: Date input with a calendar popup

The kit SHALL provide a `ga-date-input` element: a labelled text field whose
value can be typed or picked from a `ga-calendar` shown in a popup.

#### Scenario: Picking from the popup
- **WHEN** the user opens the popup and selects a day
- **THEN** the field shows that date, the popup closes, and a change event
  carrying the value is dispatched

#### Scenario: Typing a date
- **WHEN** the user types a date the element can parse
- **THEN** the value updates and the popup, when opened, shows that date's month

#### Scenario: Unparseable input
- **WHEN** the typed text cannot be parsed as a date
- **THEN** the field reports an invalid state rather than silently discarding the
  text

#### Scenario: Keyboard operation and dismissal
- **WHEN** the field has focus
- **THEN** the popup can be opened, a date chosen, and the popup dismissed from
  the keyboard, with focus returning to the field

### Requirement: Form participation

`ga-date-input` SHALL participate in native form submission like the kit's other
value-bearing elements.

#### Scenario: Submitted with a form
- **WHEN** a named date input inside a form holds a valid date and the form is
  submitted
- **THEN** the form data contains that name with the `YYYY-MM-DD` value

### Requirement: No third-party date dependency

The calendar and date input SHALL be implemented using platform APIs only,
keeping the kit dependency-free.

#### Scenario: Dependency-free build
- **WHEN** the kit is installed or the standalone bundle is loaded
- **THEN** no third-party date or calendar library is pulled in
