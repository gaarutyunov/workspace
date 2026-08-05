## ADDED Requirements

### Requirement: A typed Go client is generated from the schema and named operations

The system SHALL generate a Go package from the schema document plus a directory
of named GraphQL operation documents, exposing one method per operation with
types derived from that operation's variables and selection set.

Every operation SHALL be compiled at generation time by the existing pure
compiler, and its SQL SHALL be emitted as a constant rather than built at run
time.

#### Scenario: One method per named operation
- **WHEN** the client generator runs over a schema document and an operations
  directory
- **THEN** the generated package exposes one method per named operation, with an
  input type derived from its variables and a result type derived from its
  selection set

#### Scenario: The input contract admits one reading
- **WHEN** the generator reads its operations directory
- **THEN** it reads the GraphQL documents in that directory only, without
  descending into subdirectories, in sorted path order; each may hold any number
  of named operations; the operation name is the exported method name

#### Scenario: An anonymous operation is refused
- **WHEN** an operation document contains an operation with no name
- **THEN** generation fails naming the file, because there is no method name to
  derive

#### Scenario: A duplicate operation name is refused
- **WHEN** two operations across the directory share a name
- **THEN** generation fails naming both files, rather than one silently
  overwriting the other

#### Scenario: Results are assigned, not reflected over
- **WHEN** a generated method turns an executed result into its typed result
- **THEN** the assignments are themselves generated from the operation's
  selection set, and nothing at run time inspects a struct tag or a type

#### Scenario: The SQL is in the diff, not in the process
- **WHEN** a generated file is read
- **THEN** the statement each method executes is a constant in that file, and
  nothing compiles a GraphQL operation at run time

#### Scenario: Compile-time failures stay at generation time
- **WHEN** an operation names an unknown root field, exceeds the traversal-depth
  ceiling, or projects a scalar that cannot be mapped
- **THEN** generation fails naming the operation, and no such failure is
  reachable from a request

#### Scenario: Generated code is marked as generated
- **WHEN** a generated file is read by tooling or a reviewer
- **THEN** it carries the standard generated-code header, so hand-editing is
  detectable

#### Scenario: Only what is specified is generated
- **WHEN** the client generator runs
- **THEN** it produces the client package and nothing else, because no other
  output has a specification

### Requirement: Every generated operation takes a caller-supplied handle

The system SHALL give every generated method — query and mutation alike — a
parameter for the caller's connection handle, immediately after the context, so
that an operation can be executed inside a transaction the caller owns.

#### Scenario: A generated query runs in the caller's transaction
- **WHEN** a caller invokes a generated query method passing its own transaction
- **THEN** the query executes inside that transaction and observes its
  uncommitted writes

#### Scenario: A generated mutation runs in the caller's transaction
- **WHEN** a caller invokes a generated mutation method passing its own
  transaction
- **THEN** the function call executes inside that transaction, and commits or
  rolls back with it

#### Scenario: The handle is not optional
- **WHEN** a generated method is called
- **THEN** it requires a handle; the generated client opens no connection of its
  own and holds no pool

#### Scenario: A failing generated mutation carries the condition code
- **WHEN** a called function raises
- **THEN** the generated method returns the typed error carrying the database's
  condition code, unchanged by the generated layer
