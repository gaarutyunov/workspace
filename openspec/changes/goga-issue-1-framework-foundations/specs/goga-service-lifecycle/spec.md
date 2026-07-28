## ADDED Requirements

### Requirement: A server starts and stops on a signal, gracefully

Running a service SHALL install signal handling and shut down in-flight work
within a bounded grace period.

#### Scenario: A termination signal starts shutdown
- **WHEN** the process receives an interrupt or termination signal
- **THEN** the server stops accepting new connections and begins draining

#### Scenario: In-flight requests are allowed to finish
- **WHEN** shutdown begins while a request is in flight
- **THEN** it is allowed to complete, within the grace period

#### Scenario: The grace period is bounded
- **WHEN** work does not finish within the grace period
- **THEN** shutdown completes anyway and the outcome is reported

#### Scenario: Timeouts are set
- **WHEN** a server is constructed
- **THEN** it has header, read and write timeouts set rather than left unbounded

#### Scenario: The exit status reflects the outcome
- **WHEN** the process exits after a failure
- **THEN** its status is non-zero

### Requirement: An outbound client carries retries and instrumentation

The HTTP client SHALL be constructed with retry behaviour and instrumentation
rather than each project assembling its own.

#### Scenario: Retries are configurable, not hardcoded
- **WHEN** retry counts and backoff are supplied by configuration
- **THEN** the client honours them

#### Scenario: Outbound calls are traced and measured
- **WHEN** a request is made
- **THEN** it produces a client span, propagates trace context, and records
  client metrics

#### Scenario: Retries are visible
- **WHEN** an attempt fails and is retried
- **THEN** the retry is logged rather than silently absorbed

#### Scenario: The underlying client is reachable
- **WHEN** a caller needs the standard client
- **THEN** it is returned, so any library taking one can be used
