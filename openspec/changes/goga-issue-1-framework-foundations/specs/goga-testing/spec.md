## ADDED Requirements

### Requirement: Container fixtures with a stated lifecycle

Integration tests SHALL obtain real dependencies through a shared fixture whose
lifecycle and reset strategy are decided once, not per project.

#### Scenario: A dependency is available to a test
- **WHEN** a test asks for a database
- **THEN** it receives the framework's own portable database handle, ready to use,
  so tests exercise the same instrumented path production does

#### Scenario: State is reset between tests
- **WHEN** one test has written data and another begins
- **THEN** the second sees the declared starting state

#### Scenario: Containers are released
- **WHEN** the suite finishes, including on failure
- **THEN** every container it started is torn down, and the strategy avoids
  accumulating containers across a long run

#### Scenario: Fixture ordering is deterministic
- **WHEN** schema and seed data are both supplied
- **THEN** the schema is applied first, regardless of file naming

#### Scenario: Schema comes from the project's own migrations
- **WHEN** a test fixture needs a schema
- **THEN** it is produced by running the project's migrations through the
  framework's migration module, so tests and production share one schema path

#### Scenario: Cleanup does not accumulate across a long run
- **WHEN** many suites run in sequence in one job
- **THEN** containers are released as their own lifetime ends rather than being
  held until the whole run finishes — one existing project rejected the
  library's own cleanup helper for exactly this reason

#### Scenario: The underlying container is reachable
- **WHEN** a test needs something the fixture does not model
- **THEN** the container handle is available

### Requirement: Framework surfaces are testable without infrastructure

The test module SHALL provide harnesses for the framework's own surfaces, so a
project does not build its own.

#### Scenario: A protocol server is testable in-process
- **WHEN** a test exercises a framework protocol server
- **THEN** it obtains a connected client over an in-memory transport, with no
  subprocess and no port

#### Scenario: Emitted telemetry is assertable
- **WHEN** a test needs to verify that an operation was instrumented
- **THEN** the harness records the emitted telemetry and lets the test assert on
  it, so the telemetry invariant is tested rather than trusted

#### Scenario: Test doubles are generated, not hand-written
- **WHEN** a unit test needs a test double for an interface
- **THEN** it uses a generated mock, kept current by the project's generation
  check, rather than a hand-rolled fake

### Requirement: One behavioural-test harness

The behavioural-test bootstrap SHALL be provided once rather than copied into
every suite.

#### Scenario: A suite starts from the shared harness
- **WHEN** a new feature suite is written
- **THEN** it registers its steps against the shared harness without
  re-implementing container setup, scenario reset or the runner options

#### Scenario: The test handle is reachable from a step
- **WHEN** a step needs to fail the test
- **THEN** it can, without each project inventing its own way to smuggle the
  handle in

#### Scenario: Reporting is consistent
- **WHEN** a suite runs in CI
- **THEN** it emits machine-readable results in the same format across projects

#### Scenario: Work in progress can be excluded
- **WHEN** scenarios are marked as in progress
- **THEN** the default run excludes them
