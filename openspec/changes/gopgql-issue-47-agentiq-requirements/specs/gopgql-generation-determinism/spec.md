## ADDED Requirements

### Requirement: Generation is byte-reproducible from its inputs

The system SHALL produce byte-identical output for identical inputs, across
runs, machines and processes, for every generator it exposes. No iteration over
an unordered collection may reach generated output.

The system SHALL assert this in its own test suite rather than relying on a
consumer's regeneration check to discover a violation.

#### Scenario: Two runs produce identical trees
- **WHEN** a generator runs twice over the same inputs into two separate output
  directories
- **THEN** the two directory trees are byte-identical, file for file

#### Scenario: The check covers every generator
- **WHEN** the reproducibility test runs
- **THEN** it covers migration generation and client generation both, so a new
  generator cannot be added without being covered

#### Scenario: A consumer's regeneration check stays quiet
- **WHEN** a consumer regenerates in continuous integration and compares against
  its committed tree
- **THEN** the comparison is empty, because the property was already asserted
  upstream

### Requirement: Generated output carries no environmental values

The system SHALL NOT write a timestamp, a hostname, a username, an absolute
filesystem path or any other value derived from the machine or the moment into
generated output.

#### Scenario: No environmental value appears in any artifact
- **WHEN** the generated artifacts are scanned
- **THEN** none contains a timestamp, hostname, username or absolute path

#### Scenario: Migration filenames stay sequence-numbered
- **WHEN** a generation emits migration files
- **THEN** their names are sequence-numbered with the generation's slug and are
  not derived from the current time

#### Scenario: The same commit regenerates to the same bytes
- **WHEN** the same inputs are generated from two checkouts made at different
  times
- **THEN** the output is identical

### Requirement: Generation contacts no database

The system SHALL generate migrations and client code without a database
connection, and SHALL NOT read any connection setting during generation.

#### Scenario: Generation succeeds with no database available
- **WHEN** a generator runs with no connection string configured and no database
  reachable
- **THEN** it completes successfully and writes its output

#### Scenario: The purity is structural, not incidental
- **WHEN** the packages that perform parsing, schema modelling, generation,
  migration diffing, compilation and shaping are built
- **THEN** none of them imports a database driver, which is the same boundary
  that lets them compile to WebAssembly
