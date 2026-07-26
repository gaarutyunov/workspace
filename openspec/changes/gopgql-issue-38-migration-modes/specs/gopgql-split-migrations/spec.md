## ADDED Requirements

### Requirement: Migrations are split into two directories by default

Generation SHALL produce a migration for the tables and their indexes and a
separate migration for the property graph, in separate directories under the
target directory, without any flag being passed.

#### Scenario: A new project gets two directories
- **WHEN** a schema is generated into an empty target directory
- **THEN** one directory holds a migration creating the tables and their
  indexes, and another holds a migration creating the property graph

#### Scenario: Neither migration contains the other's statements
- **WHEN** the two migrations are inspected
- **THEN** the tables migration contains no property-graph statement, and the
  graph migration contains no table or index statement

#### Scenario: Together they equal the combined migration
- **WHEN** the tables migration is applied to an empty database and the graph
  migration is applied after it
- **THEN** the resulting database is the same as applying a single combined
  migration for the same schema

#### Scenario: Each reverse migration undoes only its own half
- **WHEN** either migration's down section is applied
- **THEN** it undoes what that migration created and touches nothing belonging
  to the other half

#### Scenario: A query works across the split
- **WHEN** both halves have been applied and rows are present
- **THEN** a query compiles and returns the same rows as against a combined
  migration

### Requirement: A directory's identity determines what it manages

What a directory is responsible for SHALL be determined by which directory it
is, and SHALL NOT be recorded inside the migration files or depend on a flag
matching a previous run.

#### Scenario: The tables directory ignores the graph
- **WHEN** a delta is generated for the tables directory
- **THEN** the absence of a property graph in its history produces no statement,
  on that run or any later one

#### Scenario: The graph directory ignores the tables
- **WHEN** a delta is generated for the graph directory
- **THEN** the absence of tables in its history produces no table statement, on
  that run or any later one

#### Scenario: Repeated generation is stable
- **WHEN** generation is run twice against an unchanged schema
- **THEN** the second run emits nothing, in either directory

#### Scenario: A change confined to one half touches only that directory
- **WHEN** the schema changes in a way that affects only the tables, or only the
  graph
- **THEN** only the corresponding directory receives a migration

### Requirement: Either half can be turned off

Generation SHALL allow the tables half or the graph half to be switched off, so
that a project whose tables are managed elsewhere, or which does not yet want a
graph, can use gopgql for the other half alone.

#### Scenario: Tables off
- **WHEN** the tables half is turned off
- **THEN** no tables directory or migration is produced, and no statement about
  any table is emitted

#### Scenario: Graph off
- **WHEN** the graph half is turned off
- **THEN** no graph directory or migration is produced, and no statement about
  the property graph is emitted

#### Scenario: Turning a half off does not delete anything
- **WHEN** a half that was previously being managed is turned off
- **THEN** nothing already applied to the database is dropped — the half stops
  being managed, it is not torn down

#### Scenario: Dropping the graph is done by the schema, not the flag
- **WHEN** the graph half is on and the schema no longer declares a property
  graph
- **THEN** the graph directory's next migration drops the graph and contains no
  statement touching any table

#### Scenario: The data survives dropping the graph
- **WHEN** that migration is applied to a database holding rows
- **THEN** the graph is gone and every row remains

### Requirement: Existing single-directory projects are unaffected

A target directory that already contains migrations SHALL continue to be written
to exactly as before this change, so that no existing project is required to
reorganise its history.

#### Scenario: An existing combined directory stays combined
- **WHEN** a schema is generated into a directory that already holds migrations
  directly
- **THEN** the new migration is written there in the combined form, and no
  subdirectory is created

#### Scenario: History is not moved
- **WHEN** generating into such a directory
- **THEN** the migrations already there are left where they are, because they
  have already been applied and recorded under their current names

#### Scenario: An empty or already-split directory uses the split
- **WHEN** the target directory is empty, or already contains the split
  subdirectories
- **THEN** the split layout is used

### Requirement: The ordering between the halves is documented

Because the graph references the tables, the required order SHALL be stated
where someone using the split will see it.

#### Scenario: The constraint is discoverable
- **WHEN** a developer reads the command-line help or the project documentation
- **THEN** it states that the tables must be applied before the graph

#### Scenario: Applying the graph first fails loudly
- **WHEN** the graph migration is applied to a database whose tables do not
  exist
- **THEN** the database refuses it, naming the missing table, rather than
  gopgql creating the tables itself

#### Scenario: Order is not enforced by the tool
- **WHEN** migrations are applied
- **THEN** gopgql applies the directory it was given without checking whether
  the other half has been applied
