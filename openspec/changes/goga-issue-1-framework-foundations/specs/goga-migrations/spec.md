## ADDED Requirements

**Milestone: M5 (`goga/migrate`). Adopter: gopgql, which already requires goose
and ships its own migration package. It follows M4 because the migrator takes the
portable database handle, and its readiness reporting plugs into the check shape
M2 shipped.**

### Requirement: One migration engine for the house

Schema migrations SHALL be applied through a single framework module wrapping one
chosen engine, and projects SHALL NOT each select their own.

#### Scenario: Migrations run through the framework
- **WHEN** a project needs to apply schema migrations
- **THEN** it uses the framework's migration module rather than driving an engine
  directly or writing its own runner

#### Scenario: Migrations run on the framework's database handle
- **WHEN** the migrator is constructed
- **THEN** it takes the portable database handle, and the bridge to whatever
  interface the engine requires is the module's concern and not the caller's

#### Scenario: The version table is named once
- **WHEN** migrations are applied
- **THEN** they record state in a table named by the framework, so projects do not
  each pick a name

#### Scenario: The engine remains reachable
- **WHEN** a caller needs engine behaviour the module does not model
- **THEN** the underlying engine handle is available

### Requirement: Migrations travel with the binary

Migration files SHALL be embedded in the binary by default.

#### Scenario: Embedded migrations are the default
- **WHEN** a migrator is constructed without naming a directory
- **THEN** it reads migrations from an embedded filesystem, so a deployed binary
  carries its own schema

#### Scenario: A directory is still supported
- **WHEN** a caller supplies a directory instead
- **THEN** migrations are read from it

### Requirement: Concurrent starts do not both migrate

Applying migrations SHALL be serialised across processes.

#### Scenario: Two replicas starting together
- **WHEN** two instances of a service start at the same time and both would apply
  migrations
- **THEN** one applies them and the other waits, rather than both running the same
  migration

#### Scenario: Waiting is bounded
- **WHEN** the wait for the lock exceeds its timeout
- **THEN** startup fails reporting the timeout, rather than hanging

#### Scenario: The lock is released on failure
- **WHEN** a migration fails partway
- **THEN** the lock is released so a later attempt is not blocked

### Requirement: Pending migrations are reportable

The module SHALL report whether the schema is behind the code.

#### Scenario: A service with a behind schema is not ready
- **WHEN** migrations are pending and readiness is checked
- **THEN** the service reports itself not ready, rather than accepting traffic and
  erroring per request

#### Scenario: Status is inspectable
- **WHEN** an operator asks what has been applied
- **THEN** the module reports the applied and pending sets

### Requirement: Migrations are observable

Migration runs SHALL be instrumented.

#### Scenario: Each migration is individually recorded
- **WHEN** a migration run applies several files
- **THEN** each one produces a span carrying its version and name, so a single
  slow migration is identifiable

#### Scenario: A failing migration names itself
- **WHEN** a migration fails
- **THEN** the error names the version and the file, and the failure is recorded
  with its error type
