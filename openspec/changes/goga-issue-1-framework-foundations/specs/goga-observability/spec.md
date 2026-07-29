## ADDED Requirements

### Requirement: Telemetry is configured in one call

Tracing, metrics and structured logging SHALL be established together, so that a
service cannot acquire one and silently omit the others.

#### Scenario: All three signals are established
- **WHEN** telemetry is initialised
- **THEN** a tracer provider, a meter provider and a structured logger are all
  configured and installed globally

#### Scenario: Exporters are selected by configuration
- **WHEN** an exporter is named in configuration
- **THEN** it is used, and an unknown name fails at startup naming the supported
  values rather than silently disabling telemetry

#### Scenario: Shutdown is ordered and reported
- **WHEN** the service stops
- **THEN** every provider is flushed and shut down, and the errors are reported
  together rather than the first one masking the rest

#### Scenario: Official conventions are used
- **WHEN** resource attributes are set
- **THEN** they use the official semantic conventions, so telemetry from
  different services is joinable

#### Scenario: The providers remain reachable
- **WHEN** a caller needs the provider directly
- **THEN** it is returned, rather than only installed globally

#### Scenario: The global meter provider is always installed
- **WHEN** metrics are configured
- **THEN** the global meter provider is set, because an existing project
  configures metrics and omits this today, and there must be no path through the
  framework that reproduces it

#### Scenario: Context propagation is configured too
- **WHEN** telemetry is initialised
- **THEN** the trace-context propagators are installed, so a request crossing two
  framework services appears as one trace without either service configuring it

### Requirement: Modules obtain instrumentation from one handle

The framework SHALL provide a single per-module instrumentation handle that every
module uses, so that instrumentation is uniform and its presence is checkable.

#### Scenario: Operations are recorded consistently
- **WHEN** any module records an operation
- **THEN** it produces a span named for its module and operation, records the
  duration in a histogram, and on failure records the error type using the
  official conventions

#### Scenario: Attribute keys come from generated constants
- **WHEN** an attribute is attached to an operation
- **THEN** its key comes from a generated conventions constant rather than a
  string literal

#### Scenario: A library can use the framework without configuring telemetry
- **WHEN** a library uses framework modules in a process that never initialises
  telemetry
- **THEN** the operations succeed against no-op providers, and the recording call
  sites remain, so telemetry appears as soon as a consuming binary initialises it

#### Scenario: Every module's instrumentation is verified to exist
- **WHEN** the framework's own test suite runs
- **THEN** a test enumerates the modules and fails if any module has no
  instrumentation handle

#### Scenario: Tests can assert on emitted telemetry
- **WHEN** a module's tests exercise an operation
- **THEN** they can assert that the expected span was produced, so the invariant
  is tested rather than trusted

### Requirement: Operational endpoints stay out of request traces

Health, readiness and metrics endpoints SHALL NOT be recorded as application
requests.

#### Scenario: Probes do not appear as traced requests
- **WHEN** a liveness or readiness probe is served
- **THEN** no request span is produced for it

#### Scenario: Metric scrapes do not appear either
- **WHEN** the metrics endpoint is scraped
- **THEN** no request span is produced

#### Scenario: Application routes are still traced
- **WHEN** an application route is served
- **THEN** it produces a span with the official HTTP attributes
