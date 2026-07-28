## ADDED Requirements

### Requirement: Container fixtures with a stated lifecycle

Integration tests SHALL obtain real dependencies through a shared fixture whose
lifecycle and reset strategy are decided once, not per project.

#### Scenario: A dependency is available to a test
- **WHEN** a test asks for a database
- **THEN** it receives a running one with its connection details

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

#### Scenario: The underlying container is reachable
- **WHEN** a test needs something the fixture does not model
- **THEN** the container handle is available

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
