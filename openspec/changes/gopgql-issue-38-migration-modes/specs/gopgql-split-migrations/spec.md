## ADDED Requirements

### Requirement: No migration contains both table DDL and property-graph DDL

Generation SHALL produce separate migrations for the tables and their indexes and
for the property graph, without any flag being passed. No single migration SHALL
contain both a table or index statement and a property-graph statement.

#### Scenario: A new project gets a run of single-purpose migrations
- **WHEN** a schema is generated into an empty target directory
- **THEN** one migration creates the tables and their indexes and a later one
  creates the property graph

#### Scenario: Neither migration contains the other's statements
- **WHEN** the emitted migrations are inspected
- **THEN** no migration contains both a table or index statement and a
  property-graph statement

#### Scenario: Together they equal the combined migration
- **WHEN** the emitted migrations are applied in order to an empty database
- **THEN** the resulting database is the same as applying a single combined
  migration for the same schema

#### Scenario: Each reverse migration undoes only its own migration
- **WHEN** a migration's down section is applied
- **THEN** it undoes what that migration created and touches nothing another
  migration created

#### Scenario: A query works across the split
- **WHEN** every emitted migration has been applied and rows are present
- **THEN** a query compiles and returns the same rows as against a combined
  migration

### Requirement: One migration directory with one migration history

All migrations SHALL be written into the single target directory, in one
sequentially numbered history recorded in one version table. Applying migrations
SHALL be the migration tool's ordinary forward apply over that directory, with no
ordering, interleaving or selective skipping performed by gopgql.

#### Scenario: No subdirectories are created
- **WHEN** a schema is generated into a target directory
- **THEN** every migration is written into that directory itself, and no
  per-concern subdirectory is created

#### Scenario: One version history
- **WHEN** migrations are applied
- **THEN** exactly one version table records them, and it is the migration tool's
  default one

#### Scenario: Applying is a plain forward apply
- **WHEN** migrations are applied
- **THEN** every pending migration in the directory is applied in ascending
  version order, and gopgql neither reorders them nor decides that any of them is
  to be skipped

#### Scenario: Versions are consecutive integers in emission order
- **WHEN** the emitted migrations are inspected
- **THEN** their versions are integers assigned in the order the migrations were
  emitted, each higher than every version already present in the directory

### Requirement: A generation emits its migrations in dependency order

An edit of the schema SHALL emit consecutive migrations ordered so that each one
operates on the state its predecessors produced: where a property graph exists in
the history and table work is required, the graph is dropped, then the tables are
migrated, then the graph is created from the new definition.

#### Scenario: Table work under an existing graph emits three migrations
- **WHEN** the schema changes such that table or index DDL is required and the
  history already creates a property graph
- **THEN** three consecutive migrations are emitted: one whose up section drops
  the property graph, one whose up section carries the table and index DDL, and
  one whose up section creates the property graph from the new definition

#### Scenario: The graph teardown is reversible to the previous definition
- **WHEN** the down section of the migration that drops the property graph is
  applied
- **THEN** it re-creates the property-graph definition the history held before
  that generation

#### Scenario: Dropping the graph tolerates its absence
- **WHEN** a migration that drops the property graph is applied to a database
  that has no property graph
- **THEN** it succeeds rather than failing on the missing graph

#### Scenario: The first generation has nothing to tear down
- **WHEN** a schema is generated into an empty target directory
- **THEN** the tables migration is emitted first and the graph migration second,
  and no migration drops a property graph

#### Scenario: A graph-only change emits the teardown and the rebuild
- **WHEN** the schema changes in a way that affects only the property graph and
  the history already creates one
- **THEN** two consecutive migrations are emitted — the graph drop, then the
  creation of the new definition — and neither contains a table or index
  statement

#### Scenario: A generation is reversed by undoing its migrations in reverse order
- **WHEN** every migration of the most recent generation is rolled back, newest
  first
- **THEN** the database is returned to the state it held before that generation,
  including the property-graph definition it had then

#### Scenario: Repeated generation is stable
- **WHEN** generation is run twice against an unchanged schema
- **THEN** the second run emits no migration at all

### Requirement: Replaying the whole history reproduces the current schema

Because every migration is in one directory in chronological order, a forward
apply of the entire history against an empty database SHALL produce the same
database as applying the same history incrementally as it was generated.

#### Scenario: Replay from zero after several generations
- **WHEN** a schema has been generated three times, each time changing the tables
  and the graph, and the whole directory is then applied to an empty database
- **THEN** every migration applies successfully and the resulting database matches
  the one built by applying each generation as it was produced

#### Scenario: A historical graph definition is never applied to a later schema
- **WHEN** the history is replayed
- **THEN** each property-graph creation is applied to the tables of its own
  generation, and no property-graph creation names a column that does not exist at
  the point it is applied

#### Scenario: Ordering does not depend on gopgql
- **WHEN** the migrations in the directory are applied by the migration tool
  directly, without gopgql
- **THEN** they apply successfully in ascending version order

### Requirement: Either half can be turned off

Generation SHALL allow the tables half or the graph half to be switched off, so
that a project whose tables are managed elsewhere, or which does not yet want a
graph, can use gopgql for the other half alone. Switching a half off SHALL affect
what is generated and never what is applied.

The halves a directory owns SHALL be fixed by its first generation: the flags
scope a directory's first generation, after which the directory's own history
decides, and a flag that contradicts that history SHALL be an error.

#### Scenario: Tables off
- **WHEN** the tables half is turned off
- **THEN** no migration about any table or index is emitted, and no statement
  about any table is emitted

#### Scenario: Graph off
- **WHEN** the graph half is turned off
- **THEN** no migration about the property graph is emitted, and no
  property-graph statement is emitted

#### Scenario: Both halves off is refused
- **WHEN** both halves are turned off
- **THEN** the command fails with an error, rather than generating nothing
  silently

#### Scenario: Turning the graph half off against a graph-bearing history is refused
- **WHEN** the graph half is turned off and the directory's history contains a
  property-graph creation
- **THEN** generation fails with a distinguishable error, writes no migration, and
  the message states that dropping the graph is done by generating from a schema
  that declares no graph

#### Scenario: Turning the tables half off against a tables-bearing history is refused
- **WHEN** the tables half is turned off and the directory's history created tables
- **THEN** generation fails with a distinguishable error and writes no migration,
  rather than silently omitting table DDL the graph half will later depend on

#### Scenario: A directory that never owned a half keeps working
- **WHEN** the tables half was off for the directory's first generation and is off
  again
- **THEN** generation succeeds — the flag agrees with the history, which created no
  tables

#### Scenario: Turning a half off does not skip applied history
- **WHEN** migrations are applied with a half turned off
- **THEN** every pending migration in the directory is still applied, including
  those belonging to the half that is turned off

#### Scenario: Turning a half off does not delete anything
- **WHEN** a half that was previously being managed is turned off
- **THEN** nothing already applied to the database is dropped — the half stops
  being managed, it is not torn down

#### Scenario: Dropping the graph is done by the schema, not the flag
- **WHEN** the graph half is on and the schema no longer declares a property
  graph
- **THEN** the next generation emits a migration dropping the graph, no migration
  creating one, and no statement touching any table

#### Scenario: The data survives dropping the graph
- **WHEN** that migration is applied to a database holding rows
- **THEN** the graph is gone and every row remains

### Requirement: Prior state is reconstructed from a history holding only one half

Generation SHALL reconstruct prior state from the migrations in the directory,
including when those migrations describe only one of the two halves.

#### Scenario: A history with no property graph
- **WHEN** a delta is generated against a history that contains no property-graph
  creation, because every previous generation turned the graph half off
- **THEN** generation succeeds, the prior tables are reconstructed, and the delta
  orders its statements so that dependent tables are created after, and dropped
  before, the tables they reference

#### Scenario: A graph over tables the history never created
- **WHEN** a delta is generated against a history that creates a property graph
  over tables no migration in the directory created
- **THEN** generation succeeds and emits no statement about those tables

#### Scenario: The folded graph is the one last created
- **WHEN** the history contains a property-graph drop followed by a creation
- **THEN** the reconstructed prior state holds the definition that was created
  last, not the one that was dropped

### Requirement: There is no other layout

Generation SHALL always use this layout, with no detection of, and no fallback
to, any earlier one.

#### Scenario: A directory holding migrations from an earlier layout
- **WHEN** a schema is generated into a directory that already contains
  migrations in the previous combined form, or per-concern subdirectories from the
  previous split layout
- **THEN** this layout is used exactly as for an empty directory — the earlier
  layout is neither detected nor preserved

#### Scenario: No flag selects an earlier layout
- **WHEN** the command-line options are inspected
- **THEN** there is no option that produces a single combined migration
  containing both halves, and none that writes the halves into separate
  directories

#### Scenario: The layout is documented
- **WHEN** a developer reads the command-line help or the project documentation
- **THEN** it states that a generation emits consecutive single-purpose
  migrations into one directory, and that they are applied in that order
