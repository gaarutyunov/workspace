## ADDED Requirements

### Requirement: Column defaults

A scalar field SHALL be able to declare a default value, which the generator
emits as the column's DDL default.

#### Scenario: Default on a new column
- **WHEN** a field declares a default and the schema is generated
- **THEN** the column's definition carries that default

#### Scenario: A row omitting the column gets the default
- **WHEN** a row is inserted without a value for a defaulted column
- **THEN** the database stores the declared default

#### Scenario: Default added to an existing column
- **WHEN** a default is added to a field that already exists in the applied
  schema
- **THEN** the delta alters the existing column to set the default, rather than
  dropping and re-adding the column

#### Scenario: Default removed
- **WHEN** a field's default is removed from the SDL
- **THEN** the delta drops the default and leaves the column and its data in
  place

### Requirement: Check constraints enforced by the database

A field or a type SHALL be able to declare a check expression, which becomes a
constraint the database enforces — not a validation the application performs.

#### Scenario: Column-level check rejects invalid data
- **WHEN** a field declares a check and a row violating it is inserted
- **THEN** the database rejects the write

#### Scenario: Valid data is unaffected
- **WHEN** a row satisfying the check is inserted
- **THEN** it is stored normally

#### Scenario: Type-level check spanning columns
- **WHEN** a type declares a check referring to more than one of its fields
- **THEN** the constraint is emitted at table level and the database enforces it
  across those columns

#### Scenario: Constraints are named
- **WHEN** a check constraint is emitted
- **THEN** it carries a deterministic name derived from the table and the field,
  so a later migration can drop it by name

#### Scenario: Check added to an existing table
- **WHEN** a check is added to a field that already exists in the applied schema
- **THEN** the delta adds the constraint without dropping the column

#### Scenario: An invalid expression fails at migration time
- **WHEN** a check expression is not valid SQL
- **THEN** the failure comes from the database when the migration is applied,
  naming the expression — the generator does not attempt to parse it

### Requirement: Constraint directives are additive

Adding these directives SHALL NOT change the output for a schema that does not
use them.

#### Scenario: An untouched schema is unchanged
- **WHEN** a schema declaring no defaults and no checks is generated
- **THEN** its DDL is identical to the DDL produced before this capability
  existed
