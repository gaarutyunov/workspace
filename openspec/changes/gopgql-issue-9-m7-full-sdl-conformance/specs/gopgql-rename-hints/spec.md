## ADDED Requirements

### Requirement: A rename is declared, never inferred

A type or a field SHALL be able to declare the name it previously had. Only that
declaration makes a change a rename; without it, a disappeared field and an
appeared field remain a drop and an add.

#### Scenario: Renaming a field preserves its data
- **WHEN** a field declares its previous name and the delta is generated and
  applied
- **THEN** the column is renamed in place and every existing row keeps its value

#### Scenario: The migration renames rather than recreates
- **WHEN** a rename delta is generated
- **THEN** it alters the table to rename the column, and contains no statement
  dropping the old column or adding a new one for it

#### Scenario: Renaming a type renames its table
- **WHEN** a type declares its previous name
- **THEN** the delta renames the table, and the rows in it survive

#### Scenario: Without a hint, nothing is inferred
- **WHEN** a field is removed and another added, with no rename declared
- **THEN** the delta drops one column and adds the other, as before

#### Scenario: Re-generating after the rename is applied is a no-op
- **WHEN** the same SDL, still carrying the rename hint, is diffed against the
  already-renamed schema
- **THEN** no migration is emitted, because the hint names something that is no
  longer there

#### Scenario: A hint that contradicts the schema is an error
- **WHEN** a field declares a previous name that the same SDL still declares as
  a separate field
- **THEN** parsing fails, because that describes two fields rather than a rename

### Requirement: Renames survive the fold

The migration reader SHALL understand every statement the generator emits, so
that the state reconstructed from prior migrations is correct after a rename.

#### Scenario: A rename statement is read back
- **WHEN** prior migrations containing a table rename and a column rename are
  folded
- **THEN** the reconstructed schema has the new names, and does not have the old
  ones

#### Scenario: The delta after a rename is correct
- **WHEN** a further change is made to a schema whose previous migration renamed
  something
- **THEN** the new delta is computed against the renamed state, and does not
  attempt to drop or re-add the renamed object

#### Scenario: Constraint statements are read back
- **WHEN** prior migrations adding or dropping named constraints are folded
- **THEN** the reconstructed schema carries those constraints, so a later diff
  does not emit them a second time

#### Scenario: Folded state matches a direct apply
- **WHEN** a sequence of migrations including a rename is folded and applied, and
  the same final schema is applied directly to a fresh database
- **THEN** the two resulting database schemas are identical
