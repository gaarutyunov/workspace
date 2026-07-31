## ADDED Requirements

### Requirement: One canonical response, and one encoder for it

The system SHALL define the response as the value both strategies return, and
SHALL provide a single encoding of it. Byte-identity between strategies is
defined as equality of that encoding, and SHALL be stated in those terms
wherever the claim is made.

#### Scenario: Both strategies return the same kind of value
- **WHEN** the same query is executed under each strategy
- **THEN** each returns a response value of the same type, and a caller does not
  branch on which strategy produced it

#### Scenario: The claim is written down accurately
- **WHEN** the byte-identity guarantee is documented
- **THEN** it says that it concerns gopgql's encoding of the response, and
  states that the bytes PostgreSQL returns are *not* the bytes gopgql writes —
  their key order and spacing differ and cannot be made to agree

#### Scenario: The database's serialisation does not reach a caller
- **WHEN** the in-database strategy produces the response
- **THEN** gopgql parses it and re-encodes it, so the database's own key
  ordering and whitespace are not observable in what a caller receives

### Requirement: Deterministic ordering under both strategies

Every list in the response SHALL be in a total, deterministic order that is the
same under both strategies, because two independently ordered results cannot be
identical.

#### Scenario: A fan-out is ordered the same way twice
- **WHEN** a query whose parent has several children is executed under each
  strategy
- **THEN** the children appear in the same order in both responses

#### Scenario: The order is stable across runs
- **WHEN** the same query is executed twice against unchanged data
- **THEN** both responses list the same elements in the same order

#### Scenario: Every level is ordered
- **WHEN** a multi-hop query nests several levels
- **THEN** each level's list is ordered, not only the outermost

#### Scenario: Ordering does not change which rows appear
- **WHEN** ordering is applied
- **THEN** the same parents and children appear as before, deduplicated as
  before

### Requirement: A canonical form for every projected scalar

Each GraphQL scalar a query may project SHALL have one canonical representation
in the response, reachable from a value the driver scanned and from a value
parsed out of the database-built response.

#### Scenario: An exact numeric keeps its digits
- **WHEN** a fixed-scale numeric column is projected under each strategy
- **THEN** both responses carry the database's own digits, trailing zeros
  included, and neither has been rounded through a binary floating-point value

#### Scenario: A timestamp does not depend on the session
- **WHEN** a timestamp column is projected
- **THEN** it is rendered in UTC in both responses, so the same row does not
  encode differently on two connections whose time zone settings differ

#### Scenario: An identifier is text
- **WHEN** an identifier column is projected
- **THEN** it appears in both responses in the canonical hyphenated text form,
  not as an array of bytes

#### Scenario: A null is a null
- **WHEN** a nullable field has no value
- **THEN** both responses carry an explicit null for it, at the same key —
  never an absent key on one side

#### Scenario: A value neither side can encode fails on both
- **WHEN** a floating-point column holds a value JSON cannot represent
- **THEN** both strategies fail, rather than one failing and the other
  substituting a string

#### Scenario: An unmappable scalar is refused at compile time
- **WHEN** a query projects a column whose type has no canonical form
- **THEN** compilation under the in-database strategy fails, naming the field
  and the type, rather than producing a response that could differ from the
  Go-side one

#### Scenario: The refusal can be branched on
- **WHEN** a caller receives that refusal and wants to fall back to Go-side
  shaping
- **THEN** the error carries the cause as a type it can test for, as the
  depth-ceiling refusal already does, without matching on a message

#### Scenario: A response the projection does not describe is an error
- **WHEN** the value returned by the database carries a key the compiled
  projection does not describe
- **THEN** shaping fails naming that key, rather than dropping the field —
  the two having diverged is a defect, and a quietly shorter response would
  hide it

#### Scenario: The Go-side strategy is not narrowed
- **WHEN** the same query is compiled under the Go-side strategy
- **THEN** it compiles, because that strategy makes no cross-strategy promise
  about that column

### Requirement: Parity proven over every prior milestone's query scenarios

Every query scenario the earlier milestones execute SHALL be re-run under both
strategies against a real PostgreSQL 19 container, and the encoded responses
SHALL be byte-equal.

#### Scenario: The two strategies agree
- **WHEN** a catalogued scenario is executed under each strategy
- **THEN** the encoded responses are byte-equal

#### Scenario: Agreeing is not enough on its own
- **WHEN** the two strategies agree on a scenario
- **THEN** the response is also checked against what that milestone's own suite
  asserts, so the two cannot pass by being wrong together

#### Scenario: Order is asserted exactly
- **WHEN** parity is asserted
- **THEN** list order is part of the comparison, not normalised away as the
  milestone suites do

#### Scenario: The catalogue cannot fall behind
- **WHEN** a milestone suite executes a query the parity catalogue does not
  cover
- **THEN** a test fails naming that query, so a later milestone cannot add a
  query that parity silently skips

#### Scenario: The predicted divergences are covered explicitly
- **WHEN** the catalogue is reviewed
- **THEN** it contains a many-child fan-out, an exact numeric, a timestamp, a
  branching selection with an unmatched branch, a query that matches nothing,
  and a null scalar — the cases the design predicts would diverge without this
  change
