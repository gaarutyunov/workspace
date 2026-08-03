## ADDED Requirements

**Milestone: M4 (`goga/database` and `goga/database/pgxdb`) — the owner's
*"postgres which could land to gopgql and codiq"*. Adopter: gopgql; codiq when it
exists. The last two scenarios depend on the sqlc seam and land at M12 with the
generators.**

**This capability was reversed in the current revision (design D7).** The
previous version specified a portable database API with a replaceable adapter
behind it. It no longer does: `gocloud.dev`, which this design follows for every
other module and which ships driver-based ports for object storage, publish and
subscribe, document stores, secrets and runtime configuration, deliberately did
not build one for SQL — it returns the standard library's handle and instruments
the driver underneath it. The requirements below follow that.

### Requirement: Database access is provided as two honest handles, not one portable interface

The framework SHALL provide database access by returning the standard library's
database handle and, separately, the PostgreSQL driver's own handle, and SHALL
NOT introduce an interface that both satisfy.

#### Scenario: A caller wants the standard interface
- **WHEN** a caller opens a database through the module's primary entry point
- **THEN** it receives the standard library's database handle, already
  instrumented, and every tool that speaks that interface works with it
  unmodified

#### Scenario: A caller wants PostgreSQL's own capabilities
- **WHEN** a caller opens a database through the PostgreSQL package
- **THEN** it receives that driver's native pool handle, already instrumented,
  with bulk copy, batching and asynchronous notifications directly available and
  nothing to unwrap

#### Scenario: The two are not presented as interchangeable
- **WHEN** a project moves between the two
- **THEN** it changes an import and a type, and the framework does not offer a
  configuration switch that pretends the change is transparent — because the two
  handles do not have the same capabilities

#### Scenario: The connection string does not select an implementation
- **WHEN** a caller supplies a connection URL or DSN
- **THEN** that string is passed to the driver as configuration, and its scheme
  does not choose between the two packages

#### Scenario: No capability is erased to fit a common shape
- **WHEN** a caller needs bulk copy, batching, asynchronous notifications or
  native types
- **THEN** they are reached directly on the driver's own handle, with no escape
  hatch, no conversion and no capability check

### Requirement: Both handles are instrumented before the caller receives them

Instrumentation SHALL be applied when the handle is constructed, and SHALL NOT be
the responsibility of calling code.

#### Scenario: Every statement is traced and measured
- **WHEN** a query, an execute or a transaction runs on either handle
- **THEN** it produces a span with the official database attributes, records its
  duration, and on failure records the error type

#### Scenario: Instrumentation is applied beneath the standard interface
- **WHEN** the standard library handle is constructed
- **THEN** the instrumentation is installed on the driver beneath it, so the
  returned value is the ordinary standard-library type and not a wrapper the
  caller has to unwrap

#### Scenario: There is no uninstrumented path out of the module
- **WHEN** any exported entry point of either package returns a handle
- **THEN** that handle is instrumented, and neither package exports a way to
  obtain an uninstrumented one

#### Scenario: The guarantee is enforced by lint here, not by the type
- **WHEN** project code obtains a database handle without going through this
  module
- **THEN** the linter reports it — and this is the framework's only runtime
  module where the guarantee is lint-level rather than compile-level, because
  the handles returned are the standard library's and the driver's own types,
  which any caller can construct uninstrumented
- **AND** the framework states this plainly rather than describing the guarantee
  as structural

#### Scenario: Instrumentation cannot be switched off
- **WHEN** a caller configures either package
- **THEN** the instrumentation can be replaced but not disabled, and no option
  exists that removes it

### Requirement: Transactions are correct by default

The module SHALL provide a transaction helper that commits on success and rolls
back on failure, so that projects do not each write one.

#### Scenario: A successful transaction commits
- **WHEN** the transaction body returns without error
- **THEN** the transaction commits

#### Scenario: A failed transaction rolls back
- **WHEN** the transaction body returns an error
- **THEN** the transaction rolls back and the error reaches the caller

#### Scenario: A panicking transaction rolls back
- **WHEN** the transaction body panics
- **THEN** the transaction rolls back before the panic continues

#### Scenario: Each handle gets its own helper, with identical semantics
- **WHEN** a project uses the PostgreSQL driver's handle rather than the standard
  one
- **THEN** it gets a transaction helper for that handle, separate from the
  standard one because the two transaction types are different — and the commit,
  rollback, panic and timeout behaviour of the two is identical and tested to
  stay identical

#### Scenario: The helper does not introduce a wrapper type
- **WHEN** a caller uses the transaction helper
- **THEN** it operates on the standard library's handle and hands the body the
  standard library's transaction, so the types flowing through the application
  are unchanged by using it

#### Scenario: A transaction's timeout covers the whole transaction
- **WHEN** a transaction body runs several statements
- **THEN** the configured bound applies to the transaction as a whole, so it
  cannot outlive its budget one statement at a time

### Requirement: The tools that need a particular handle get it directly

Tools that require a specific database handle SHALL be served without a bridge
the caller has to build.

#### Scenario: The migration engine gets a standard handle
- **WHEN** the migration engine requires a standard-library database handle
- **THEN** it is available — directly from the primary entry point, or from a
  documented conversion on the PostgreSQL pool — so no caller constructs the
  bridge

#### Scenario: Generated query code runs on the handle it was generated for
- **WHEN** a project uses generated type-safe query code
- **THEN** that code compiles against the handle its generator targeted and
  inherits that handle's instrumentation, with no generated line changing

#### Scenario: The generated-query seam is satisfied by the driver handle itself
- **WHEN** the query generator's interface is expressed in one driver's types, as
  the house query generator's is
- **THEN** the driver's own handle satisfies that interface directly, so the seam
  is a compile-time assertion rather than a conversion that can fail at run time
