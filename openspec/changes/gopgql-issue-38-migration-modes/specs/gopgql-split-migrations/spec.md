## ADDED Requirements

### Requirement: The two halves can be generated and applied separately

The command line SHALL let each half be generated into its own directory and
applied independently, so a project can own the tables elsewhere, or release the
two halves on different schedules.

#### Scenario: Generating each half into its own directory
- **WHEN** the schema is generated once in tables mode into one directory and
  once in graph mode into another
- **THEN** each directory contains only its own half, and together they describe
  the whole schema

#### Scenario: Applying them in order works
- **WHEN** the tables directory is applied to an empty database and the graph
  directory is applied afterwards
- **THEN** the database ends up with the same tables, indexes and property graph
  as applying a single combined migration would have produced

#### Scenario: A query works across the split
- **WHEN** the two halves have been applied and rows are present
- **THEN** a query compiles and returns the same rows it would have against a
  combined migration

#### Scenario: Applying the graph first fails loudly
- **WHEN** the graph directory is applied to a database whose tables do not
  exist
- **THEN** the database refuses the migration, naming the missing table, rather
  than the system creating the tables itself

### Requirement: Only the graph half may be given up

A project SHALL be able to stop managing the property graph while keeping its
tables and their data, and SHALL NOT be able to do so implicitly by changing a
directory's mode.

#### Scenario: Dropping the graph
- **WHEN** a graph-mode directory is generated against a schema that no longer
  declares a property graph
- **THEN** the migration drops the graph and contains no statement touching any
  table

#### Scenario: The data survives
- **WHEN** that migration is applied to a database holding rows
- **THEN** the graph is gone and every row remains

#### Scenario: Re-adding the graph later
- **WHEN** a graph is declared again afterwards
- **THEN** the next migration recreates it, against the tables that were never
  dropped

#### Scenario: Changing a directory's mode is not a way to drop anything
- **WHEN** a directory previously generated with both halves is asked to
  generate in tables mode
- **THEN** generation fails as a mode disagreement, rather than emitting a drop
  of the property graph

### Requirement: The split is documented as ordered

Because one half references the other, the ordering constraint SHALL be stated
where someone choosing the split will read it.

#### Scenario: The constraint is discoverable
- **WHEN** a developer reads the command-line help for the mode option or the
  project's documentation
- **THEN** it states that tables must be applied before the graph that
  references them

#### Scenario: Ordering is not enforced by the tool
- **WHEN** migrations are applied
- **THEN** the system applies the directory it was given without checking
  whether the other half has been applied, because it cannot know what another
  tool is about to do
