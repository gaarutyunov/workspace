## ADDED Requirements

### Requirement: Reflect the live property graph

The system SHALL read the property graph as the database actually holds it —
its elements, their labels, and their properties — into the same schema model
the SDL produces, so the two can be compared as values of one type.

#### Scenario: Reflecting a generated graph
- **WHEN** a schema generated from SDL has been applied and is then reflected
- **THEN** the reflected model carries the same elements, labels and properties

#### Scenario: No graph
- **WHEN** the named property graph does not exist
- **THEN** reflection reports that plainly, rather than returning an empty model
  that would look like total drift

### Requirement: Drift is reported as structured findings

The check SHALL compare the reflected model against the model the SDL describes
and return findings a program can act on — each naming what kind of drift it is
and which element or property it concerns — rather than human-readable text.

#### Scenario: A clean database
- **WHEN** the database matches the SDL
- **THEN** the check reports no findings

#### Scenario: A property removed out of band
- **WHEN** a property the SDL declares has been removed from the graph directly
- **THEN** a finding names that property, its element, and that it is missing
  from the database

#### Scenario: A property present that the SDL does not declare
- **WHEN** the graph exposes a property the SDL does not declare
- **THEN** a finding names it as unexpected

#### Scenario: An element removed out of band
- **WHEN** an element the SDL declares is absent from the graph
- **THEN** a finding names the element as missing

#### Scenario: A label that disagrees
- **WHEN** an element's label in the database differs from the one the SDL
  declares
- **THEN** a finding names the element and both labels

#### Scenario: Findings are distinguishable by kind
- **WHEN** a caller receives findings
- **THEN** each carries a kind it can branch on, without parsing a message

#### Scenario: The report says what it does not cover
- **WHEN** the check reports
- **THEN** it is documented that it compares the property graph — elements,
  labels and properties — and not table-level objects such as defaults, check
  constraints or indexes

### Requirement: Runnable as a command that fails on drift

The check SHALL be runnable from the command line against an SDL file and a
database, and SHALL signal drift through its exit status so it can gate a
pipeline without a wrapper.

#### Scenario: Clean database exits zero
- **WHEN** the command runs against a database matching the SDL
- **THEN** it reports no drift and exits zero

#### Scenario: Drift exits non-zero
- **WHEN** the command runs against a database with drift
- **THEN** it prints the findings and exits non-zero

#### Scenario: Unreachable database
- **WHEN** the database cannot be reached
- **THEN** the command reports the connection failure and exits non-zero,
  distinguishably from having found drift

### Requirement: Conformance stays off the WASM side

Reflection requires a database connection, so it SHALL live outside the packages
that compile to WebAssembly, and none of those packages may depend on it.

#### Scenario: The WASM build is unaffected
- **WHEN** the WebAssembly target is built
- **THEN** it builds without the conformance package, because nothing it
  includes imports it

#### Scenario: The playground shows the shape, not a live check
- **WHEN** the browser playground presents a conformance report
- **THEN** it renders a fixture illustrating the report's structure, and states
  that no database is being contacted
