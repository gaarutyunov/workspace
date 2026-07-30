## ADDED Requirements

**Milestone: this capability spans four, and each requirement below names its
own. M2 delivers the server and its graceful shutdown; M8 (`goga/cli`) delivers
the single signal handler; M9 (`goga/app`) delivers the ordering across several
surfaces; M10 (`goga/client`) delivers the outbound client. That split is a
consequence of the owner's one-package-per-milestone rule, and it is stated
rather than left to be discovered: between M2 and M8 an adopting project keeps
its own signal handling.**

### Requirement: A server starts and stops on a signal, gracefully

Running a service SHALL install signal handling and shut down in-flight work
within a bounded grace period.

*Delivered across M2, M8 and M9. The scenarios about draining, grace periods and
timeouts are M2's — `goga/serve` takes a context and stops when it is cancelled.
The scenarios about a signal-aware entry point and about exactly one handler
existing are M8's, with `goga/cli`. The scenarios about several surfaces stopping
together and about shutdown order are M9's, with `goga/app`.*

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

#### Scenario: A command-line entry point is always signal-aware
- **WHEN** a service is started through the framework's command-line entry point
- **THEN** it runs with a signal-aware context, and there is no path through the
  framework to a variant without one — one existing project has no signal
  handling at all today

#### Scenario: Readiness can depend on a declared check
- **WHEN** a caller registers a readiness check, such as whether schema
  migrations are outstanding
- **THEN** the readiness endpoint reflects it, so a service that is not ready to
  serve does not accept traffic

#### Scenario: Every surface the process runs stops together
- **WHEN** a process serves more than one surface, such as an HTTP API and a
  protocol server
- **THEN** a termination signal shuts them all down on the same terms, and the
  errors are reported together

#### Scenario: One signal handler exists in the process
- **WHEN** the framework's surfaces are started
- **THEN** signal handling is installed once, by the command-line entry point,
  and no individual surface installs its own — otherwise a process with two
  surfaces has two shutdowns racing with no ordering between them

#### Scenario: A surface stops because its context is cancelled
- **WHEN** a runnable surface is started
- **THEN** it takes a context and stops when that context is cancelled, which is
  what lets one entry point sequence every surface

#### Scenario: Shutdown order is defined
- **WHEN** shutdown runs
- **THEN** the surfaces drain first, then the resources they used are released,
  and telemetry is flushed last, so the shutdown itself is observable

### Requirement: An outbound client carries retries and instrumentation

The HTTP client SHALL be constructed with retry behaviour and instrumentation
rather than each project assembling its own.

*Delivered at M10 (`goga/client`), adopters skill-test/go-service and
mcp-anything.*

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

#### Scenario: A failing dependency can be shed
- **WHEN** a downstream dependency is failing persistently
- **THEN** the client can be configured to stop calling it for a period rather
  than retrying every request into a failure

#### Scenario: The underlying client is reachable
- **WHEN** a caller needs the standard client
- **THEN** it is returned, so any library taking one can be used
