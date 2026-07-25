## ADDED Requirements

### Requirement: Schema overview without the whole document

The server SHALL expose a schema tool that, called with no arguments, returns a
compact overview of what can be queried, rather than the full schema document.

#### Scenario: Overview lists what is queryable
- **WHEN** the schema tool is called with no arguments
- **THEN** the result names every queryable root field and every mapped type,
  with a count of that type's scalar fields and relationships

#### Scenario: The overview stays small
- **WHEN** the connected schema declares many types with many fields
- **THEN** the overview does not include the individual field definitions of
  those types

### Requirement: Drill down into one type

The schema tool SHALL return the detail of a single named type on request.

#### Scenario: Type detail
- **WHEN** the schema tool is called with the name of a mapped type
- **THEN** the result lists that type's fields, distinguishing scalar fields from
  relationships, and gives each relationship's target type and direction

#### Scenario: Renamed columns are visible
- **WHEN** a field maps to a differently named column
- **THEN** the type detail reports the column it maps to alongside the field name

#### Scenario: Unknown type
- **WHEN** the schema tool is called with a name that is not a mapped type
- **THEN** the result is an error naming the types that are available

### Requirement: Full document on request

The schema tool SHALL be able to return the complete SDL document when the caller
explicitly asks for it.

#### Scenario: Explicit full fetch
- **WHEN** the schema tool is called asking for the full document
- **THEN** the SDL the server was started with is returned verbatim

### Requirement: Introspection reflects the loaded schema

The introspection results SHALL be derived from the same mapping model the query
tool compiles against.

#### Scenario: No drift between tools
- **WHEN** the schema tool reports a root field or a field of a type
- **THEN** a query selecting it compiles successfully
