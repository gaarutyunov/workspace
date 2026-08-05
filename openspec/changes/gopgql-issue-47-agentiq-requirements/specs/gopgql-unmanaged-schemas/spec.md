## ADDED Requirements

### Requirement: A type may be declared as one gopgql does not own

The system SHALL provide a directive marking a type whose table is owned and
migrated elsewhere. For such a type the system SHALL generate the property-graph
definition and the read model, and SHALL emit no table DDL of any kind.

The directive SHALL constrain generation only. It SHALL NOT restrict how the
type is queried.

#### Scenario: No table DDL is emitted for an unowned type
- **WHEN** a generation runs over a schema document containing such a type
- **THEN** the emitted migrations contain no create-table, alter-table,
  create-index, constraint or drop statement for it

#### Scenario: The graph definition is still emitted
- **WHEN** a generation runs over a schema document containing such a type
- **THEN** the property-graph definition includes its vertex element, so it is
  queryable

#### Scenario: A managed and an unowned type coexist in one generation
- **WHEN** a schema document declares one type gopgql owns and one it does not
- **THEN** one generation emits table DDL for the owned type only, and graph DDL
  for both

#### Scenario: Absence from the document says nothing about an unowned table
- **WHEN** a column of an unowned table is not declared in the schema document
- **THEN** nothing is emitted for it — it is neither added nor dropped

#### Scenario: Removing an unowned type removes it from the graph only
- **WHEN** an unowned type is deleted from the schema document
- **THEN** the next generation removes its element from the property graph and
  emits no table DDL

#### Scenario: Querying is unaffected
- **WHEN** a query selects an unowned type
- **THEN** it compiles and executes exactly as it would for an owned type

#### Scenario: The directive's meaning is stated where it is read
- **WHEN** an author reads the directive reference
- **THEN** it states that the directive constrains DDL emission and not query
  access, because its name reads as though it meant the latter

### Requirement: A type's management cannot change between generations

The system SHALL refuse, at generation time, a schema document in which a type
has stopped being unowned or has started being unowned, naming the type.

Prior state is reconstructed by folding the system's own emitted SQL, and nothing
is emitted for an unowned table. A type that stops being unowned would therefore
be reconstructed as absent and emitted as a create — a migration that reads
correctly and fails when it is applied.

#### Scenario: Adopting an existing table is refused
- **WHEN** a schema document removes the unowned marker from a type whose table
  the system has never created
- **THEN** generation fails naming the type and writes nothing, because there is
  no delta that represents adopting a table that already exists

#### Scenario: Disowning a created table is refused
- **WHEN** a schema document adds the unowned marker to a type whose table the
  history shows the system created
- **THEN** generation fails naming the type and writes nothing

#### Scenario: The refusal is at generation, not at application
- **WHEN** either transition is attempted
- **THEN** nothing is written, so the failure is visible in the author's
  terminal rather than in whichever environment applies the migration first

### Requirement: An element may be qualified by its schema

The system SHALL allow a type or relationship to declare the database schema its
table lives in, and SHALL emit every identifier for that element qualified by it.
When no schema is declared the emitted identifier SHALL be exactly what is
emitted today, resolving through the session's search path.

The system SHALL NOT create schemas.

#### Scenario: A qualified element is emitted qualified
- **WHEN** a type declares a schema
- **THEN** its table is named schema-qualified in the table DDL, in the property
  graph definition and in the drift check's reflection

#### Scenario: Unqualified output is unchanged
- **WHEN** no type in a schema document declares a schema
- **THEN** the generated output is byte-identical to what the previous release
  generated for the same input

#### Scenario: A qualified name is read back by the fold
- **WHEN** a generation folds prior migrations that contain qualified names
- **THEN** the prior state is reconstructed with those qualifications intact, so
  the next delta does not treat a qualified table as absent

#### Scenario: The drift check resolves the right table
- **WHEN** the drift check reflects a graph whose elements are in a non-default
  schema
- **THEN** it resolves them by schema rather than by the session's search path

#### Scenario: No schema is created
- **WHEN** a generation runs over a schema document declaring a schema that does
  not exist
- **THEN** no create-schema statement is emitted, and the missing schema is the
  database's error when the migration is applied

#### Scenario: A reserved word as a column name is quoted
- **WHEN** an unowned type maps a field to a column whose name is a reserved SQL
  word
- **THEN** the generated DDL and every compiled query quote it, and the value
  round-trips through generation, application and query
