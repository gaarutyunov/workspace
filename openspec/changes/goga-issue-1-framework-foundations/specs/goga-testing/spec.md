## ADDED Requirements

**Milestone: M7 (`goga/gogatest`). Adopters: gopgql (godog bootstrap copied 5×),
then epos (copied 8×). It follows the modules it provides fixtures for; the
scenario about generated test doubles depends on the generation check that lands
at M9.**

### Requirement: Container fixtures with a stated lifecycle

Integration tests SHALL obtain real dependencies through a shared fixture whose
lifecycle and reset strategy are decided once, not per project.

#### Scenario: A dependency is available to a test
- **WHEN** a test asks for a database
- **THEN** it receives an instrumented database handle from the framework, ready to use,
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

### Requirement: Adapters behind a multi-implementation port pass a shared conformance suite

Where a port has more than one implementation, the framework SHALL provide one
test suite that every adapter for that port runs, and adapters SHALL NOT rely on
their own tests for the port's core semantics.

#### Scenario: An adapter proves it is interchangeable
- **WHEN** an adapter for a multi-implementation port is published
- **THEN** it runs the port's conformance suite and passes, so the claim that
  adapters are interchangeable has been exercised rather than asserted

#### Scenario: Opting in is small
- **WHEN** an adapter author adds the suite
- **THEN** they supply only a harness that constructs the adapter and cleans up
  after it, and the suite provides everything else

#### Scenario: The suite replaces per-adapter semantics tests
- **WHEN** an adapter is tested
- **THEN** the conformance suite is comprehensive enough that the adapter needs no
  further tests of the port's core semantics, which is what makes the trade worth
  making

#### Scenario: A fixed defect stays fixed for every adapter
- **WHEN** a defect is found in one adapter's behaviour
- **THEN** the regression test is added to the shared suite rather than to that
  adapter's own tests, so no other adapter can reintroduce it

#### Scenario: The escape hatch is conformance-tested too
- **WHEN** an adapter supports reaching its underlying implementation
- **THEN** the suite exercises that path, so the escape hatch is covered rather
  than being the one untested part of the adapter

#### Scenario: Baseline invariants are asserted whether the adapter opted in or not
- **WHEN** the suite runs against any adapter
- **THEN** it adds its own baseline checks to whatever the adapter supplied — so
  an adapter cannot skip an invariant by declining to declare it

#### Scenario: A port with one implementation has no suite, deliberately
- **WHEN** a module has a single implementation and no second one is planned
- **THEN** no conformance suite is written for it, because a conformance suite for
  one implementation is cost without the property it exists to establish

#### Scenario: Conformance runs against real dependencies, not recorded traffic
- **WHEN** a conformance suite needs a backing service
- **THEN** it uses a disposable real instance rather than recorded and replayed
  traffic, so the suite does not accumulate recorded fixtures that no reviewer
  can read

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
