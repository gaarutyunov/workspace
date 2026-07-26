## ADDED Requirements

### Requirement: Standard GraphQL introspection over the loaded schema

The server SHALL answer the standard GraphQL introspection meta-fields —
`__schema`, `__type(name:)` and `__typename` — over the schema it was started
with, following the introspection system of the GraphQL specification.

#### Scenario: The introspection root is queryable
- **WHEN** an introspection query selects `__schema { queryType { name } }`
- **THEN** the result is the introspection response for that selection, in the
  shape the GraphQL specification defines

#### Scenario: A type is introspectable by name
- **WHEN** an introspection query selects `__type(name: "<MappedType>") { name kind fields { name } }`
- **THEN** the result describes that type, with each field's name and its type
  reference

#### Scenario: Typename on a selected object
- **WHEN** an operation selects `__typename` on a mapped type
- **THEN** the response carries that type's name

#### Scenario: Introspection never reaches the database
- **WHEN** a query selects only introspection meta-fields
- **THEN** the result is served from the loaded schema and no statement is sent to
  the database

#### Scenario: An unknown type introspects to null
- **WHEN** `__type` is called with a name the schema does not declare
- **THEN** the field resolves to null, as the specification requires, rather than
  raising a tool error

### Requirement: An introspection tool an agent can afford to call

The server SHALL expose an introspection tool that issues a standard introspection
query on the caller's behalf and returns its result, defaulting to a selection
small enough to read.

#### Scenario: Default selection stays small
- **WHEN** the introspection tool is called with no arguments
- **THEN** the result names every queryable root field and every mapped type, and
  omits those types' individual field definitions

#### Scenario: Drill down into one type
- **WHEN** the introspection tool is called with the name of a mapped type
- **THEN** the result is that type's `__type` detail — its fields, each field's
  type reference, and which fields resolve to another mapped type

#### Scenario: Full introspection on request
- **WHEN** the introspection tool is called asking for the full schema
- **THEN** the complete introspection result for the schema is returned

#### Scenario: The SDL document remains available
- **WHEN** the introspection tool is called asking for SDL
- **THEN** the schema is returned as an SDL document

### Requirement: Tool descriptions teach the agent how to introspect

Every tool the server exposes SHALL carry a description that states how to
introspect the schema, so an agent learns the introspection surface from the tool
list alone without being told out of band.

#### Scenario: The introspection tool describes its own surface
- **WHEN** a client lists the server's tools
- **THEN** the introspection tool's description names the meta-fields it covers
  (`__schema`, `__type`) and how to narrow the result to one type

#### Scenario: The query tool points at introspection
- **WHEN** a client lists the server's tools
- **THEN** the query tool's description states that introspection meta-fields can
  be selected through it, and gives an introspection query an agent can send
  verbatim to discover what is queryable

#### Scenario: Discovery needs no prior knowledge of the schema
- **WHEN** an agent has only the tool list and no description of the data
- **THEN** the descriptions are sufficient to reach a valid data query: introspect
  the root fields, introspect one type, then select its fields

### Requirement: Introspection reflects the same model queries compile against

The introspection results SHALL be derived from the same mapping model the query
tool compiles against.

#### Scenario: No drift between tools
- **WHEN** introspection reports a root field or a field of a type
- **THEN** a query selecting it compiles successfully

#### Scenario: Renamed columns stay an implementation detail
- **WHEN** a field maps to a differently named column
- **THEN** introspection reports the GraphQL field name, and the column name is
  not part of the introspection result
