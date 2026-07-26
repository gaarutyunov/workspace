## ADDED Requirements

### Requirement: The SDL may describe only part of a database

The SDL SHALL be usable as the description of a subset of a database — the slice
a service surfaces as a graph — rather than as a description of the whole
database. Absence from the SDL SHALL NOT be treated as evidence of absence from
the database.

#### Scenario: Tables the SDL does not mention are left alone
- **WHEN** the graph half is managed against a database containing tables the
  SDL never mentions
- **THEN** no migration drops, alters or otherwise refers to those tables

#### Scenario: The SDL is not required to be exhaustive
- **WHEN** an SDL describing a subset of a database is used with the tables half
  turned off
- **THEN** generation succeeds, and does not require the missing tables to be
  declared

#### Scenario: Columns outside the SDL are untouched
- **WHEN** a table the SDL describes has columns the SDL does not declare, and
  the tables half is turned off
- **THEN** no migration drops or alters those columns

#### Scenario: The graph exposes only what the SDL declares
- **WHEN** the property graph is created from such an SDL
- **THEN** it exposes exactly the elements and properties the SDL declares, and
  nothing else the database happens to hold

#### Scenario: A query returns only the declared slice
- **WHEN** a query runs against a graph built from a partial SDL
- **THEN** it returns data from the declared properties only

### Requirement: Managing tables requires the SDL to be complete for them

Where gopgql *is* managing the tables, it SHALL be documented that the SDL is
the whole truth for the tables it describes, so the difference between the two
uses is not left to be discovered.

#### Scenario: The distinction is documented
- **WHEN** a developer reads the documentation for turning the tables half off
- **THEN** it states that with the tables half on, a column absent from the SDL
  is a column gopgql will remove, and that the partial-description guarantee
  applies to the graph half

#### Scenario: An undeclared column is still dropped when tables are managed
- **WHEN** the tables half is on and a table has a column the SDL does not
  declare
- **THEN** the delta removes that column, as it does today
