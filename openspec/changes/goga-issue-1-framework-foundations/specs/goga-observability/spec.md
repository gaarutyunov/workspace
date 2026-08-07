## ADDED Requirements

**Milestone: M1 (`goga/telemetry`), the first package delivered — the owner's
*"telemetry first, every project needs it"*. Adopters: gopgql, then epos. The
exception is the last requirement below, *Operational endpoints stay out of
request traces*, which is `goga/serve`'s to satisfy and lands at M2.**

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
- **THEN** a test compares the modules that obtained an instrumentation handle
  against the module list, and fails both on a module that performs runtime
  operations without one and on an addition to the set declared to have no
  operations

#### Scenario: A handle obtained before telemetry is configured still records
- **WHEN** a module obtains its instrumentation handle during package
  initialisation, as every module's adapter table does, and telemetry is configured
  later during startup
- **THEN** operations recorded after configuration are exported — the handle
  resolves through the global providers rather than capturing whichever
  providers were installed when it was created

#### Scenario: The duration belongs to the framework, not the call site
- **WHEN** a module records an operation's duration
- **THEN** the elapsed time is measured by the instrumentation handle itself, so
  no call site can supply a wrong start time

#### Scenario: Tests can assert on emitted telemetry
- **WHEN** a module's tests exercise an operation
- **THEN** they can assert that the expected span was produced, so the invariant
  is tested rather than trusted

### Requirement: The instrumentation is unreachable by adapters, so "no opt-out" is structural

The mechanism that makes every module instrumented SHALL be the type system and
the package boundary, rather than a rule adapter authors are asked to follow.

#### Scenario: An adapter cannot reach the instrumentation
- **WHEN** an adapter author looks for the per-operation instrumentation
- **THEN** it is in a package the adapter cannot import, so an adapter cannot
  instrument, re-instrument or bypass it even deliberately

#### Scenario: There is no way to produce an uninstrumented framework object
- **WHEN** an adapter returns its result to the framework
- **THEN** the only thing that can turn it into the type an application receives
  is the module's own constructor, which attaches instrumentation — so an adapter
  has no way to hand an application an uninstrumented object

#### Scenario: The adapter's identity is derived, not declared
- **WHEN** an operation records which adapter performed it
- **THEN** the identity is derived from the adapter value itself rather than from
  a name the adapter declared, so a newly written adapter is labelled correctly
  without its author adding anything

#### Scenario: One value serves as both the error classification and the metric label
- **WHEN** an operation fails
- **THEN** the same classification is used to set the span status and to label the
  duration metric, so the two cannot disagree and an adapter that classifies its
  errors correctly gets correct metrics without further work

#### Scenario: The telemetry module stays importable by everything
- **WHEN** the telemetry module's dependencies are examined
- **THEN** it imports only OpenTelemetry and the standard library, because every
  other module imports it and any dependency it acquires is acquired by every
  consuming project — a module that is mandatory must be cheap enough to be
  mandatory

#### Scenario: A dependency added to a shared module is caught before release
- **WHEN** a change adds a dependency to the telemetry module or the registry
- **THEN** the framework's own continuous integration fails, rather than the
  dependency being discovered by a consuming project

### Requirement: Operational endpoints stay out of request traces

Health, readiness and metrics endpoints SHALL NOT be recorded as application
requests.

*Delivered at M2 with `goga/serve`, not at M1: there is no request to keep out of
a trace until there is a server.*

#### Scenario: Probes do not appear as traced requests
- **WHEN** a liveness or readiness probe is served
- **THEN** no request span is produced for it

#### Scenario: Metric scrapes do not appear either
- **WHEN** the metrics endpoint is scraped
- **THEN** no request span is produced

#### Scenario: Application routes are still traced
- **WHEN** an application route is served
- **THEN** it produces a span with the official HTTP attributes
