## ADDED Requirements

### Requirement: Execution is opt-in and costs nothing until chosen

The PostgreSQL runtime SHALL be loaded only in response to an explicit action by
the reader. Loading the page, editing any input, and generating output SHALL NOT
fetch or instantiate it.

#### Scenario: First paint is unchanged
- **WHEN** the playground is loaded
- **THEN** no PostgreSQL runtime asset is requested, and the page reaches its
  ready state exactly as it did before execution existed

#### Scenario: Generating does not execute
- **WHEN** a schema or query is edited, or generation is triggered
- **THEN** output is regenerated without loading the runtime

#### Scenario: Running loads it
- **WHEN** the reader triggers execution for the first time
- **THEN** the runtime is fetched and initialised, and the page reports that it
  is doing so

#### Scenario: The cost is stated before it is paid
- **WHEN** the reader looks at the control that triggers execution, before
  pressing it
- **THEN** the page states that pressing it downloads a PostgreSQL build of
  several megabytes

#### Scenario: The laziness is enforced, not intended
- **WHEN** the site is built
- **THEN** an automated check confirms that no eagerly-loaded bundle references
  the runtime's binary assets, and fails the build if one does

#### Scenario: A second run reuses what was loaded
- **WHEN** execution is triggered again after a first run
- **THEN** the runtime is not downloaded again

### Requirement: Execution runs in a worker, off the main thread

#### Scenario: The page stays responsive during startup
- **WHEN** the runtime is initialising, which takes seconds
- **THEN** the page remains interactive and its other panes keep working

#### Scenario: The generator stays where it is
- **WHEN** execution runs
- **THEN** the schema/query generator continues to run on the main thread, and
  is not duplicated into the worker

#### Scenario: Only serialisable data crosses
- **WHEN** work is handed to the worker and results come back
- **THEN** what crosses is text, plain arrays and plain values — never a shared
  memory buffer and never a reference into either module's memory

### Requirement: Execution is in-memory only and leaves nothing behind

#### Scenario: Nothing is persisted
- **WHEN** queries are executed
- **THEN** no data is written to IndexedDB, OPFS, or any other browser storage

#### Scenario: A reload starts clean
- **WHEN** the page is reloaded after executing
- **THEN** no database state survives

#### Scenario: Each run starts from an empty database
- **WHEN** execution is triggered twice
- **THEN** the second run applies the schema to a fresh empty database, and is
  unaffected by anything the first run created

#### Scenario: An edited schema does not accumulate
- **WHEN** the schema is edited between two runs
- **THEN** the second run reflects only the edited schema, with no residue of
  the earlier one

### Requirement: A run applies the schema, seeds it, then executes the query

Execution SHALL be an ordered sequence of applying the generated schema,
applying the scenario's seed data, and executing the compiled query with its
bind parameters.

#### Scenario: The executable schema is what runs
- **WHEN** the schema is applied
- **THEN** it is the plain generated DDL — the tables, their indexes and the
  property graph — and not a migration document carrying migration-tool
  annotations

#### Scenario: Parameters are bound, not interpolated
- **WHEN** a compiled query carrying placeholders is executed
- **THEN** the values are passed as bind parameters in the compiler's order, and
  no value is substituted into the SQL text

#### Scenario: A query with no parameters runs
- **WHEN** a compiled query carries no placeholders
- **THEN** it executes with no parameters

#### Scenario: The rendered SQL is the executed SQL
- **WHEN** a run completes
- **THEN** the SQL that was executed is character-for-character the SQL shown in
  the generated-SQL pane

### Requirement: Every example scenario that compiles a query can be run

#### Scenario: Each query scenario is runnable
- **WHEN** a scenario compiles a query
- **THEN** that scenario offers execution and renders its own results, without
  affecting any other scenario

#### Scenario: A scenario that compiles nothing offers nothing
- **WHEN** a scenario has no compiled query
- **THEN** it offers no execution control

#### Scenario: A refused query is never executed
- **WHEN** compilation refused the query, including refusal for exceeding the
  traversal-depth ceiling
- **THEN** execution is not offered or not attempted, and the refusal continues
  to be presented as the designed outcome

### Requirement: Seed data makes results meaningful

Each example schema SHALL have seed data, so that a run against it returns rows
rather than an empty result.

#### Scenario: The default run returns rows
- **WHEN** a scenario is run without any edit to its inputs
- **THEN** the result contains at least one row

#### Scenario: The seed matches the schema it belongs to
- **WHEN** a scenario's seed data is applied to that scenario's generated schema
- **THEN** it succeeds

#### Scenario: An edited schema does not break the run
- **WHEN** the reader edits a schema so its seed data no longer applies
- **THEN** the seed step reports its failure, the query still executes, and the
  page distinguishes "the seed did not apply" from "the query failed"

### Requirement: Results and failures are both rendered as outcomes

#### Scenario: Rows render as a table
- **WHEN** a query returns rows
- **THEN** they are rendered as a table with the result's column names

#### Scenario: Zero rows is a result
- **WHEN** a query returns no rows
- **THEN** the page says the query succeeded and returned no rows, and does not
  present this as an error

#### Scenario: A database error is shown verbatim
- **WHEN** any step fails inside PostgreSQL
- **THEN** PostgreSQL's own message is shown, without being replaced by a
  generic page message

#### Scenario: The failing step is named
- **WHEN** a run fails
- **THEN** the page names which step failed — applying the schema, seeding, or
  executing the query

#### Scenario: A failed run leaves the generated panes alone
- **WHEN** a run fails
- **THEN** the generated schema, SQL and parameter panes still show what was
  generated

#### Scenario: Progress is visible
- **WHEN** a run is in progress
- **THEN** the page indicates it, and the execution control cannot start a
  second concurrent run of the same scenario

#### Scenario: A runtime that fails to load says so
- **WHEN** the runtime cannot be fetched or initialised
- **THEN** the page reports that execution is unavailable and why, and the rest
  of the page keeps working
