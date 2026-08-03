## ADDED Requirements

### Requirement: The two strategies are benchmarked across depth and fan-out

The system SHALL carry a committed benchmark comparing the two shaping
strategies over traversal depth and fan-out, executed against a real PostgreSQL
19 container.

#### Scenario: Both axes are varied
- **WHEN** the benchmark runs
- **THEN** it covers several traversal depths up to the compiler's default
  ceiling, and several fan-out sizes, with each combination measured under both
  strategies

#### Scenario: The fixture is reproducible
- **WHEN** the benchmark's fixture graph is generated
- **THEN** it is generated deterministically, so two runs measure the same data

#### Scenario: The measurement is the library's own path
- **WHEN** a case is measured
- **THEN** it drives the same compile-execute-shape path a caller uses, not an
  internal shortcut

### Requirement: The benchmark reports strategy-intrinsic numbers, not only timings

The benchmark SHALL report quantities that are properties of the strategy rather
than of the machine, so its conclusions survive being read on a different
computer.

#### Scenario: Result-set size is reported
- **WHEN** a case is measured
- **THEN** the number of rows the database returned and the number of bytes
  received are reported alongside the timing

#### Scenario: The row counts are asserted
- **WHEN** the benchmark's row counts are checked
- **THEN** an ordinary test asserts them, because they are deterministic — the
  flat strategy returns one row per matched path and the in-database strategy
  returns one row

#### Scenario: Timings are not asserted
- **WHEN** the benchmark runs in continuous integration
- **THEN** no timing threshold is asserted, because a shared runner cannot
  support one and a flaky performance gate would be disabled

### Requirement: Results are committed and CI keeps the benchmark alive

The benchmark's results SHALL be recorded in the documentation, and continuous
integration SHALL execute the benchmark so it cannot silently stop working.

#### Scenario: The results are in the docs
- **WHEN** the documentation is read
- **THEN** it carries the benchmark's results together with the machine, the
  language and database versions, and the date that produced them, and states
  that the timings are from that machine

#### Scenario: CI runs the benchmark
- **WHEN** continuous integration runs
- **THEN** it executes the benchmark for a single iteration per case, proving it
  still compiles, still boots a database, and still produces a result under both
  strategies

#### Scenario: The pipeline stays fast
- **WHEN** the benchmark runs in continuous integration
- **THEN** it runs at the smallest iteration count that proves it works, rather
  than for a duration that would produce publishable timings

#### Scenario: The documented axes cannot drift
- **WHEN** an axis is added to or removed from the benchmark
- **THEN** a test fails unless the documented axes are updated to match, because
  both read one declaration

#### Scenario: Regenerating the results is a single command
- **WHEN** someone wants to refresh the committed numbers
- **THEN** one documented command runs the full benchmark and rewrites the
  results document
