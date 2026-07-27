## ADDED Requirements

### Requirement: A natural key over existing properties

A type SHALL be able to declare a natural key naming one or more of its own
scalar properties. The key identifies a row by its data, **alongside** the
surrogate key — it does not replace it.

#### Scenario: The key becomes a uniqueness constraint
- **WHEN** a type declares a natural key and the schema is generated
- **THEN** the table carries a named uniqueness constraint over exactly those
  columns, in the declared order

#### Scenario: Duplicates are refused by the database
- **WHEN** two rows sharing the same natural-key values are inserted
- **THEN** the database rejects the second

#### Scenario: The surrogate key is untouched
- **WHEN** a type declares a natural key
- **THEN** it still has its surrogate identifier, edges still reference that
  identifier, and queries against the type compile exactly as before

#### Scenario: Single-column keys are allowed
- **WHEN** a natural key names one property
- **THEN** it is emitted the same way, as a named constraint over that column

### Requirement: The natural key is part of the graph

The natural key's columns SHALL be exposed to the property graph, so a query can
select a vertex by them.

#### Scenario: The key appears in the graph definition
- **WHEN** a type with a natural key is generated
- **THEN** the property graph names those columns as the element's key

#### Scenario: Matchable by a query
- **WHEN** a query filters a vertex on its natural-key properties
- **THEN** it compiles, executes, and returns the matching rows

#### Scenario: Values are bound, not interpolated
- **WHEN** a query filters on a natural-key property
- **THEN** the value travels as a bind parameter, as any other property filter
  does

### Requirement: A natural key must name real scalar properties

Declaring a key over something that is not a stored scalar property SHALL be
rejected when the SDL is parsed, not when the migration is applied.

#### Scenario: Unknown field
- **WHEN** a natural key names a field the type does not declare
- **THEN** parsing fails with an error naming the field and the type

#### Scenario: Relationship field
- **WHEN** a natural key names a relationship rather than a scalar property
- **THEN** parsing fails, because a relationship maps to no column on the table

#### Scenario: Ignored field
- **WHEN** a natural key names a field that is excluded from the database
- **THEN** parsing fails, because there is no column to constrain

#### Scenario: Empty key
- **WHEN** a natural key names no fields
- **THEN** parsing fails
