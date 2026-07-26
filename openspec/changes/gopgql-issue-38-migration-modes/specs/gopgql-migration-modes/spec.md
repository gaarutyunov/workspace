## ADDED Requirements

### Requirement: A migration directory has a mode

Migration generation SHALL be governed by a mode naming which halves of the
schema the directory is responsible for: the tables and their indexes, the
property graph, or both.

#### Scenario: Both halves by default
- **WHEN** no mode is chosen
- **THEN** the migration contains the tables, their indexes and the property
  graph, byte-identical to what was generated before modes existed

#### Scenario: Tables only
- **WHEN** the tables mode is chosen
- **THEN** the migration creates the tables and their indexes and contains no
  property-graph statement

#### Scenario: Graph only
- **WHEN** the graph mode is chosen
- **THEN** the migration creates the property graph and contains no table or
  index statement

#### Scenario: The reverse migration matches the mode
- **WHEN** a migration is generated in any mode
- **THEN** its down section undoes exactly what its up section did, and nothing
  belonging to the other half

#### Scenario: An unknown mode is refused
- **WHEN** a mode the system does not implement is requested
- **THEN** generation fails naming the supported modes, rather than falling back
  to a default

### Requirement: The mode is recorded in the migration

A generated migration SHALL record the mode it was generated in, so that reading
the directory back does not depend on being told the mode again.

#### Scenario: The mode round-trips
- **WHEN** a directory's migrations are read back
- **THEN** the mode they were generated in is recovered from the migrations
  themselves

#### Scenario: Older migrations are the default mode
- **WHEN** a migration carries no recorded mode
- **THEN** it is treated as covering both halves, so directories generated
  before modes existed keep working unchanged

#### Scenario: A contradicting mode is an error
- **WHEN** a mode is requested that disagrees with the mode recorded in the
  directory
- **THEN** generation fails and explains the disagreement, rather than
  re-scoping the directory

#### Scenario: The disagreement is distinguishable to a caller
- **WHEN** a caller receives that failure
- **THEN** it can tell the disagreement apart from any other generation failure
  without matching on the message text, because the two call for different
  responses

#### Scenario: A matching mode is accepted
- **WHEN** the requested mode agrees with the recorded one
- **THEN** generation proceeds normally

### Requirement: The mode governs what a directory diffs

Reading prior state back SHALL yield only what the directory's mode covers, and
the difference against the desired schema SHALL be computed over that scope
alone.

#### Scenario: A tables directory ignores the graph
- **WHEN** a delta is generated for a directory that owns only the tables
- **THEN** the absence of a property graph in its history produces no statement,
  on that run or any later one

#### Scenario: A graph directory ignores the tables
- **WHEN** a delta is generated for a directory that owns only the graph
- **THEN** the absence of tables in its history produces no table statement, on
  that run or any later one

#### Scenario: Repeated generation is stable
- **WHEN** generation is run twice against an unchanged schema, in any mode
- **THEN** the second run emits nothing

#### Scenario: Changes outside the mode are ignored
- **WHEN** the schema changes only in the half a directory does not own
- **THEN** that directory emits no migration

#### Scenario: An empty directory in graph mode with no graph declared
- **WHEN** a graph-mode directory has no migrations yet and the schema declares
  no property graph
- **THEN** nothing is emitted — there is neither a graph to create nor one to
  drop
