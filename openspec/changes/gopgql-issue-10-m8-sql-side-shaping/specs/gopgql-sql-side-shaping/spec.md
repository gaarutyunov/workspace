## ADDED Requirements

### Requirement: A second shaping strategy that builds the response in-database

The system SHALL provide a shaping strategy that assembles the nested GraphQL
response inside PostgreSQL and returns it as a single value, alongside the
existing strategy that regroups flat rows in Go.

#### Scenario: The SQL-side query returns one row of one column
- **WHEN** a query is compiled under the SQL-side strategy and executed
- **THEN** the statement returns exactly one row carrying one column, holding
  the whole nested response

#### Scenario: The Go-side query is unchanged
- **WHEN** a query is compiled under the Go-side strategy
- **THEN** it projects the flat columns it projected before, and is shaped in Go
  as before

#### Scenario: The matched rows do not depend on the strategy
- **WHEN** the same query is compiled under each strategy
- **THEN** the graph pattern, its predicates, its bind parameters and their
  order are identical between the two, so which rows match is not a function of
  the strategy

#### Scenario: A branching selection aggregates before it joins
- **WHEN** a level selects several relationships, which the compiler splits into
  separate graph queries joined on projected identifiers
- **THEN** each branch is aggregated into a nested list before the join, so the
  join produces one row per parent rather than the product of the branches'
  fan-outs

#### Scenario: A branch with no matches is an empty list
- **WHEN** a parent matches on one branch and not another
- **THEN** the parent appears with the matched branch populated and the
  unmatched branch an empty list, as under Go-side shaping

#### Scenario: A query matching nothing is an empty list, not a null
- **WHEN** a query matches no rows at all
- **THEN** the response carries an empty list for the root field, as under
  Go-side shaping, and not a null — aggregating an empty set in the database
  yields no value, and the strategy is responsible for turning that into the
  empty list the response contract requires

### Requirement: Ordered, non-deduplicating JSON construction

The in-database construction SHALL use a JSON representation that preserves the
order in which the response is built and does not merge keys, because the
alternative reorders object keys and silently discards duplicates.

#### Scenario: Keys are not reordered by the database
- **WHEN** the response is constructed in the database
- **THEN** the construction preserves the order the compiler emitted, rather
  than a database-imposed ordering

#### Scenario: The response value is read as text
- **WHEN** the single response value is read from the result
- **THEN** it is read as text and parsed by gopgql, rather than decoded by the
  driver's generic JSON handling, which would lose the exact digits of an exact
  numeric value

### Requirement: The strategy is chosen when a query is compiled

Because the two strategies emit different SQL, the strategy SHALL be a property
of the compiler and SHALL be recorded on the compiled query, so that execution
needs no separate configuration and cannot contradict compilation.

#### Scenario: Configuring a compiler
- **WHEN** a caller constructs a compiler with a shaping strategy
- **THEN** every query that compiler compiles carries that strategy

#### Scenario: The default is unchanged behaviour
- **WHEN** a caller constructs a compiler without naming a strategy
- **THEN** queries compile under Go-side shaping, exactly as before this change

#### Scenario: Execution follows the compiled query
- **WHEN** a compiled query is executed
- **THEN** the executor shapes the result according to the strategy recorded on
  that query, and the caller passes no additional configuration

#### Scenario: Both strategies from one schema
- **WHEN** a caller wants both strategies over the same SDL
- **THEN** it constructs a compiler per strategy over the same parsed document,
  and the two compile independently

#### Scenario: No global or ambient selection
- **WHEN** two queries compiled under different strategies are executed
  concurrently
- **THEN** each is shaped by its own strategy, because the selection travels
  with the query rather than in process-wide state

### Requirement: The selector stays on the database-free side

The strategy selector SHALL live in a package that compiles to WebAssembly, so
the playground can compile a query under either strategy without a database.

#### Scenario: The WASM build still succeeds
- **WHEN** the WebAssembly target is built
- **THEN** it builds, because the selector introduces no database dependency
  into the packages it lives in

#### Scenario: No import cycle
- **WHEN** the shaping package needs to know which strategy produced a compiled
  query
- **THEN** it reads the strategy from the compiler package it already imports,
  rather than the compiler importing it back
