## ADDED Requirements

**Milestone: M4 (`goga/database`, with `driver`, `pgxdb` and `sqldb`) — the
owner's *"postgres which could land to gopgql and codiq"*. Adopter: gopgql; codiq
when it exists. The last scenario, *Generated query code runs on the portable
handle*, depends on the sqlc seam and lands at M12 with the generators.**

### Requirement: Database access goes through a portable API with pluggable adapters

Database access SHALL be provided as a portable API whose backend is a
replaceable adapter, so replacing the backend does not change the calling code.

#### Scenario: A caller opens a database by connection URL
- **WHEN** a caller supplies a connection URL and options
- **THEN** the adapter matching the URL's scheme is used, and the caller receives
  the portable handle

#### Scenario: PostgreSQL is served by the pgx adapter
- **WHEN** a PostgreSQL URL is opened
- **THEN** pgx is the adapter behind it

#### Scenario: A second backend needs no caller changes
- **WHEN** a different backend is introduced
- **THEN** it is added as an adapter, and callers of the portable API compile and
  behave unchanged

#### Scenario: A second adapter exists before the split is relied on
- **WHEN** the portable API is first released
- **THEN** more than one adapter implements it, so the claim that the interface
  is portable has been exercised rather than assumed

#### Scenario: The adapter surface is narrow
- **WHEN** a new adapter is written
- **THEN** it implements query, execute, transaction and close, and implements no
  cross-cutting concern — no tracing, no metrics, no timeouts

#### Scenario: A missing adapter fails clearly at startup
- **WHEN** a URL scheme has no registered adapter
- **THEN** opening fails naming the registered schemes and the likely missing
  import, rather than yielding an unusable handle

### Requirement: The portable handle owns the instrumentation

Instrumentation SHALL belong to the portable database handle rather than to any
adapter.

#### Scenario: Every operation is traced and measured
- **WHEN** a query, an execute or a transaction runs
- **THEN** it produces a span with the official database attributes, records its
  duration, and on failure records the error type

#### Scenario: A new adapter is instrumented on the day it is written
- **WHEN** an adapter is added
- **THEN** its operations are traced and measured without the adapter's author
  adding instrumentation

#### Scenario: The handle cannot be constructed uninstrumented
- **WHEN** an adapter returns its result
- **THEN** it returns the adapter-level type, and only the module's open entry
  point can produce the portable handle — so no code path yields an
  uninstrumented one

#### Scenario: Backend-level detail is not lost
- **WHEN** the adapter can report backend-level timing or statistics
- **THEN** those are recorded too, nested within the logical operation rather
  than replacing it

### Requirement: Transactions are correct by default

The portable API SHALL provide a transaction helper that commits on success and
rolls back on failure.

#### Scenario: A successful transaction commits
- **WHEN** the transaction body returns without error
- **THEN** the transaction commits

#### Scenario: A failed transaction rolls back
- **WHEN** the transaction body returns an error
- **THEN** the transaction rolls back and the error reaches the caller

#### Scenario: A panicking transaction rolls back
- **WHEN** the transaction body panics
- **THEN** the transaction rolls back before the panic continues

#### Scenario: A query timeout is applied
- **WHEN** a query runs with a configured timeout
- **THEN** it is bounded by that timeout rather than running indefinitely

#### Scenario: A transaction's timeout covers the whole transaction
- **WHEN** a transaction body runs several statements
- **THEN** the configured bound applies to the transaction as a whole, so it
  cannot outlive its budget one statement at a time

### Requirement: A streaming result outlives the call that returned it

A query that returns rows SHALL keep those rows usable until the caller closes
them.

#### Scenario: Returned rows are readable
- **WHEN** a caller receives rows and begins reading them
- **THEN** they read successfully, because neither the timeout nor the
  instrumentation for that query was released when the call returned

#### Scenario: The recorded duration covers the read
- **WHEN** the rows are closed
- **THEN** the operation's recorded duration covers fetching and reading them,
  not only issuing the statement

#### Scenario: Closing releases everything, once
- **WHEN** rows are closed, whether after a full read or an abandoned one
- **THEN** the timeout and the recording are released exactly once, and closing
  again is harmless

#### Scenario: A failed read is recorded as a failure
- **WHEN** an error occurs partway through reading rows
- **THEN** the operation is recorded as failed rather than as the success it
  appeared to be when the call returned

### Requirement: The backend and the standard interface both stay reachable

The module SHALL expose both the native backend handle and a standard-library
database handle.

#### Scenario: Backend-specific features remain available
- **WHEN** a caller needs a capability the portable API does not model, such as
  bulk copy, batching or asynchronous notifications
- **THEN** the native handle is available for it

#### Scenario: A tool requiring the standard interface is supported
- **WHEN** a tool requires a standard-library database handle — the migration
  engine does
- **THEN** the module provides one, so no caller has to construct the bridge

#### Scenario: An adapter without a standard handle says so
- **WHEN** an adapter cannot provide a standard-library handle
- **THEN** the request fails with a distinguishable error rather than a nil handle

#### Scenario: Generated query code runs on the portable handle
- **WHEN** a project uses generated type-safe query code
- **THEN** that code compiles against the portable handle and inherits its
  instrumentation without any generated line changing

#### Scenario: The generated-query seam states which adapter it requires
- **WHEN** the generator's own interface is expressed in one backend driver's
  types, as the house query generator's is
- **THEN** the seam requires that adapter and fails with a distinguishable error
  under any other, rather than being described as adapter-neutral
