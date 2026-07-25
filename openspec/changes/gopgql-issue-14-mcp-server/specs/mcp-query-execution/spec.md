## ADDED Requirements

### Requirement: Execute a GraphQL query against the database

The server SHALL expose a query tool that compiles a GraphQL operation, executes
it against the connected PostgreSQL database, and returns the nested response.

#### Scenario: Query returns shaped data
- **WHEN** the query tool is called with a valid operation over the connected
  schema
- **THEN** the result is the nested JSON response for that operation, shaped the
  same way the library shapes it

#### Scenario: Traversal
- **WHEN** the operation selects a relationship
- **THEN** the response nests the related objects under their parent, with no
  duplicated parents

### Requirement: Variables are bound, never interpolated

The query tool SHALL accept GraphQL variables and pass their values to the
database as bind parameters.

#### Scenario: Variables supplied
- **WHEN** the query tool is called with an operation using a variable and a
  value for it
- **THEN** the query executes with that value bound and returns the matching rows

#### Scenario: Values never appear in the SQL text
- **WHEN** a variable value is supplied
- **THEN** the executed statement carries a placeholder for it rather than the
  literal value

#### Scenario: Missing variable
- **WHEN** an operation references a variable that was not supplied and has no
  default
- **THEN** the tool reports an error naming the missing variable and executes
  nothing

### Requirement: Errors an agent can act on

The query tool SHALL report compilation and database failures as tool errors
carrying the underlying message, without terminating the server.

#### Scenario: Unknown field
- **WHEN** the operation selects a field the schema does not have
- **THEN** the tool returns an error naming the offending field, and no statement
  reaches the database

#### Scenario: Too deep
- **WHEN** the operation nests deeper than the compiler's depth ceiling
- **THEN** the tool returns an error reporting the ceiling, and no statement
  reaches the database

#### Scenario: Database error
- **WHEN** the database rejects the executed statement
- **THEN** the tool returns an error carrying the database's message, and the
  server continues to serve subsequent calls

### Requirement: Optional visibility of the emitted SQL

The query tool SHALL be able to return the SQL it executed alongside the data.

#### Scenario: SQL requested
- **WHEN** the caller asks for the emitted SQL
- **THEN** the result includes the compiled statement it executed

#### Scenario: SQL not requested
- **WHEN** the caller does not ask for it
- **THEN** the result carries the data alone
