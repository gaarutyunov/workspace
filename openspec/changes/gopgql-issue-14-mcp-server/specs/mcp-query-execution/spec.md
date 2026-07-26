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

### Requirement: The result is data, never SQL

The query tool SHALL return only the data the operation selected. The compiled SQL
is an internal detail and SHALL NOT appear in the tool's result.

#### Scenario: A successful call returns data alone
- **WHEN** the query tool executes an operation successfully
- **THEN** the result carries the selected data and no SQL statement

#### Scenario: No option asks for SQL
- **WHEN** a client inspects the query tool's input schema
- **THEN** it declares no argument that would return the emitted SQL

### Requirement: The return format is selectable

The query tool SHALL accept a format argument choosing how the result is
rendered — the response as JSON, or a markdown table — defaulting to JSON.

#### Scenario: JSON by default
- **WHEN** the query tool is called without a format
- **THEN** the result is the JSON response for the operation

#### Scenario: Markdown table for a flat result
- **WHEN** the query tool is called with the markdown format and the operation
  selects only scalar fields
- **THEN** the result is a markdown table whose columns are the selected fields and
  whose rows are the returned records

#### Scenario: Empty flat result
- **WHEN** the markdown format is requested and the operation matches no records
- **THEN** the result is a table header with no data rows, rather than an error

### Requirement: A markdown table is refused for nested results

Because a table has no way to represent nesting, the query tool SHALL reject the
markdown format for an operation that selects a relationship, rather than emit a
misleading table.

#### Scenario: Nested selection with markdown requested
- **WHEN** the markdown format is requested and the operation selects a
  relationship
- **THEN** the tool returns an error naming the nesting field and stating that JSON
  is required for nested results

#### Scenario: The refusal happens before execution
- **WHEN** the markdown format is refused for a nested operation
- **THEN** no statement is sent to the database

#### Scenario: Nesting is always available in JSON
- **WHEN** the same nested operation is called with the JSON format
- **THEN** it executes and returns the nested response
