## ADDED Requirements

### Requirement: Construction is by variadic options, never by a parameter struct

Every exported constructor and every exported entry point SHALL accept a variadic
list of option functions, and the framework SHALL NOT expose a parameter struct
for a caller to populate.

#### Scenario: A caller configures by passing options
- **WHEN** a caller constructs any part of the framework with non-default settings
- **THEN** it passes option functions, and the call site reads as a list of named
  choices rather than as a struct literal

#### Scenario: A parameter struct cannot be constructed
- **WHEN** a caller looks for a settings type to fill in
- **THEN** none is exported, so the option form is the only form that compiles

#### Scenario: An option validates its own input
- **WHEN** an option is given a value outside its permitted range
- **THEN** construction fails naming the option and the offending value, rather
  than accepting it and failing at first use

#### Scenario: Defaults apply when an option is omitted
- **WHEN** a caller omits an option
- **THEN** the documented default applies, and the caller does not have to restate
  it

#### Scenario: Option names follow one pattern
- **WHEN** an option is added to any module
- **THEN** its name follows the house pattern for setting, appending and removing,
  so options read the same way across modules

#### Scenario: Adding an option does not break callers
- **WHEN** a new option is added to a module
- **THEN** existing call sites continue to compile unchanged

### Requirement: Every part of the framework is instrumented

Every module of the framework SHALL emit telemetry for its operations, and no
module SHALL be exempt or offer a way to disable it.

#### Scenario: Each module's operations produce telemetry
- **WHEN** any framework operation runs — loading configuration, resolving an
  adapter, running a query, applying a migration, serving a request, making an
  outbound call, handling a protocol request
- **THEN** it produces a span, records its duration, and on failure records the
  error type using the official conventions

#### Scenario: Telemetry cannot be switched off
- **WHEN** a caller looks for a way to construct a framework object without
  instrumentation
- **THEN** none exists; instrumentation can be replaced but not removed

#### Scenario: Instrumentation lives above the adapter
- **WHEN** a new adapter is written for any pluggable surface
- **THEN** it is instrumented without its author adding anything, because the
  instrumentation belongs to the portable type that wraps it

#### Scenario: An adapter cannot produce a portable object
- **WHEN** an adapter returns its result
- **THEN** it returns the adapter-level type, and only the module's own entry
  point can wrap that into the portable type — so there is no reachable path to
  an uninstrumented object

#### Scenario: Coverage is verified, not asserted
- **WHEN** the framework's own tests run
- **THEN** a test enumerates the modules and fails if any module has no
  instrumentation

#### Scenario: A library consumer without a configured backend still works
- **WHEN** a library uses a framework module in a process that never configures
  telemetry
- **THEN** the operations succeed against no-op providers, and telemetry appears
  as soon as a consuming binary configures it

### Requirement: Every wrapper exposes what it wraps

Each wrapper SHALL provide access to the underlying object it composes.

#### Scenario: The underlying object is reachable
- **WHEN** a caller needs behaviour the wrapper does not model
- **THEN** the wrapper hands back the underlying object rather than trapping the
  caller

#### Scenario: The accessor is discoverable
- **WHEN** a caller looks for the escape hatch
- **THEN** it is named consistently across modules — a generic unwrap where the
  type is opaque, a named accessor where it is not

#### Scenario: An escape hatch is not an unenforced convention
- **WHEN** the guidance describes an escape hatch
- **THEN** it is documented as a supported route, and is not counted among things
  the framework fails to enforce
