## ADDED Requirements

### Requirement: One generic registry serves every pluggable surface

There SHALL be a single generic registry implementation, parameterised over the
type an adapter produces, and every pluggable surface in the framework SHALL use
it rather than its own lookup table.

#### Scenario: A module gains a pluggable surface without new lookup code
- **WHEN** a module needs interchangeable adapters
- **THEN** it instantiates the shared registry for its own adapter type, and
  writes no map, no switch and no lookup logic of its own

#### Scenario: Every adapter-bearing module uses it
- **WHEN** the framework's pluggable surfaces are enumerated — database drivers,
  HTTP routers, telemetry exporters, protocol transports, component deployers
- **THEN** each resolves through the shared registry

#### Scenario: Adapters are typed, not asserted
- **WHEN** an adapter is resolved
- **THEN** it comes back as the registry's declared type without a type
  assertion at the call site

#### Scenario: The caller's options reach the adapter
- **WHEN** an adapter needs the caller's settings to construct itself
- **THEN** the registry carries the module's resolved settings through to it,
  and the adapter reads them through accessors — the type is nameable, because
  an adapter in its own package must name it, and remains impossible for a
  caller to populate

### Requirement: Adapters self-register and are selected by name

An adapter SHALL register itself under a scheme, and a caller SHALL select one by
naming that scheme.

#### Scenario: Selection is by scheme
- **WHEN** a caller supplies a connection URL
- **THEN** the adapter registered under that URL's scheme is used

#### Scenario: Selection is by plain name where there is no URL
- **WHEN** a surface selects its adapter by name alone — a router, an exporter, a
  protocol transport, a deployer — with no connection URL to carry it
- **THEN** the registry resolves that name directly, rather than requiring the
  caller to compose a URL whose scheme would not be the adapter's name

#### Scenario: One adapter signature serves both
- **WHEN** an adapter is written
- **THEN** it implements one opener signature regardless of which of the two
  selection forms its module uses

#### Scenario: An adapter's dependency is optional
- **WHEN** a project does not use a given adapter
- **THEN** that adapter's third-party dependency does not enter the project's
  module graph

#### Scenario: A duplicate registration is a programming error
- **WHEN** two adapters register the same scheme
- **THEN** the conflict surfaces immediately at initialisation rather than
  producing an arbitrary winner at first use

#### Scenario: An unknown scheme is self-diagnosing
- **WHEN** a caller names a scheme no adapter registered
- **THEN** the failure names the registered schemes and points at the likely
  cause, a missing adapter import, rather than reporting a generic error

#### Scenario: The registered set is inspectable
- **WHEN** a caller or a diagnostic needs to know what is available
- **THEN** the registry reports its registered schemes

### Requirement: Resolution is observable

Adapter resolution SHALL be instrumented.

#### Scenario: Resolution produces telemetry
- **WHEN** an adapter is resolved
- **THEN** the resolution is recorded with the registry and the scheme, because
  which adapter a process actually selected is an operational question

#### Scenario: A failed resolution is recorded
- **WHEN** resolution fails
- **THEN** the failure is recorded with its error type

#### Scenario: The registry does not depend on the telemetry module
- **WHEN** the registry records a resolution
- **THEN** it does so through an instrumentation interface it declares itself, so
  that the telemetry module — which uses the registry for its own exporters — can
  depend on the registry without the dependency running both ways
