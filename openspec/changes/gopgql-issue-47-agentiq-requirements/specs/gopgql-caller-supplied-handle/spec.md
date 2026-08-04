## ADDED Requirements

### Requirement: Execution runs against a handle the caller supplies

The system SHALL execute both queries and function calls against a connection
handle passed in by the caller, so that a caller running inside its own
transaction can have gopgql's statements participate in that transaction.

The handle SHALL be an interface narrow enough that a connection pool, a single
connection and a transaction all satisfy it without adaptation.

#### Scenario: A query runs inside the caller's transaction
- **WHEN** a caller begins a transaction, inserts rows without committing, and
  executes a compiled query through that transaction
- **THEN** the query returns the uncommitted rows, because it ran inside the
  same transaction

#### Scenario: A function call runs inside the caller's transaction
- **WHEN** a caller executes a compiled function call through its own
  transaction
- **THEN** the function's writes and the caller's own writes commit or roll back
  together

#### Scenario: A pool, a connection and a transaction are all accepted
- **WHEN** the library is built
- **THEN** the pool type, the connection type and the transaction type are each
  asserted to satisfy the handle interface at compile time, so a driver upgrade
  that changes a signature fails the build rather than a test

#### Scenario: A read needs no write capability
- **WHEN** a caller only executes queries
- **THEN** the narrower read-only interface the library already accepts is still
  accepted, and the caller is not required to supply a handle that can write

#### Scenario: Every method of the handle has a caller
- **WHEN** the handle interface is reviewed
- **THEN** its query method serves reads and scalar-returning calls, and its
  statement method serves void-returning calls — no method exists that nothing
  in the library invokes

### Requirement: The library never opens a writable connection

The system SHALL continue to open exactly one kind of pool — the read-only one
it opens today, whose sessions start with read-only transactions — and SHALL NOT
provide any means of opening a writable one.

Consequently a function call is executable only through a handle the caller
owns.

#### Scenario: The read-only pool is unchanged
- **WHEN** the library opens a pool
- **THEN** every session on it starts read-only, exactly as before this change

#### Scenario: No writable pool constructor exists
- **WHEN** a caller looks for a way to have the library open a writable
  connection
- **THEN** there is none, and the reference states that anything which writes
  runs through a handle the caller supplies

#### Scenario: A call on the read-only pool fails as designed
- **WHEN** a function call is executed against the library's own read-only pool
- **THEN** the database refuses it, and the error carries the read-only
  transaction condition so that the cause reads as the handle's capability
  rather than as an unexplained failure

### Requirement: A failed call carries the database's condition as data

The system SHALL return, for a function call the database refuses or that raises,
a typed error carrying the database's condition code, message, detail, hint and
constraint, together with the schema and function that were called, and SHALL
make it reachable by the standard error-unwrapping mechanism.

The system SHALL NOT construct a GraphQL error envelope: it produces no GraphQL
response, and the condition code is carried as data for the consumer to map into
its own error extensions.

#### Scenario: A raised exception surfaces its condition code
- **WHEN** a called function raises an exception with an explicit condition code
- **THEN** the caller receives a typed error whose condition code is that code
  and whose message is the function's, reachable by unwrapping

#### Scenario: The consumer maps the code into its own errors
- **WHEN** a consumer needs a GraphQL error carrying the condition code
- **THEN** it constructs one from the typed error, because the library answers no
  requests and fabricates no response envelope

#### Scenario: The error type does not cross the database-free boundary
- **WHEN** the packages that compile to WebAssembly are built
- **THEN** none of them imports the error type, because it wraps a driver type
  and the compilation and generation packages must stay free of a database
  dependency

#### Scenario: Branching is on the code, not on the text
- **WHEN** a consumer distinguishes one failure from another
- **THEN** it compares condition codes rather than matching message text
