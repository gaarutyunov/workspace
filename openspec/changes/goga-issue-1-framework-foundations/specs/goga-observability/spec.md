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
