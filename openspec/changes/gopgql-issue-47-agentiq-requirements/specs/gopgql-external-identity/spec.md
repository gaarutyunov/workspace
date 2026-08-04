## ADDED Requirements

### Requirement: A declared natural key is the identity of an unowned vertex

The system SHALL require a type it does not own to declare a natural key, and
SHALL use that key as the vertex's identity: it fills the graph element's key
clause, it is what the compiler projects at that position, and it is what the
shaper groups parent rows by.

For a type the system owns, identity SHALL remain the surrogate key, and a
declared natural key SHALL remain a uniqueness constraint alongside it.

#### Scenario: An unowned type must declare a key
- **WHEN** a schema document marks a type as one the system does not own and
  declares no natural key for it
- **THEN** parsing fails naming the type, because without a surrogate key there
  is no other identity available

#### Scenario: A multi-column key identifies a vertex
- **WHEN** an unowned type declares a key of more than one column
- **THEN** the graph element's key clause lists those columns, and every one of
  them also appears in the element's property list

#### Scenario: Parent rows deduplicate on the whole key
- **WHEN** a query traverses from a multi-column-keyed vertex across a
  one-to-many relationship
- **THEN** each parent appears once in the response with its children nested,
  grouped on the full key tuple rather than on any single column of it

#### Scenario: Deduplication does not collide on formatted values
- **WHEN** key values contain characters that a naive rendering of a tuple would
  make ambiguous, such as spaces or brackets
- **THEN** two distinct parents remain distinct, because the identity is encoded
  unambiguously rather than formatted

#### Scenario: A null key column does not silently drop rows
- **WHEN** a vertex position's identity includes a column holding null, and the
  compiler emits a self-match exclusion between two positions
- **THEN** the predicate is null-safe, so the row is excluded only when the two
  positions genuinely bind the same vertex and never merely because a component
  is null

#### Scenario: Implementors of an interface must agree on identity
- **WHEN** an interface is implemented by types whose identity columns differ
- **THEN** parsing fails naming the interface and the disagreeing types, because
  a vertex position over an interface binds any of their tables and has no
  single identity

#### Scenario: An owned type is unchanged
- **WHEN** a query selects a type the system owns
- **THEN** the emitted SQL and the shaped response are identical to what the
  previous release produced, because a single-column identity is the same
  identity it always had

#### Scenario: The exported projection surface moves with the identity
- **WHEN** the identity of a projected level stops being a single column
- **THEN** the type describing it changes accordingly, and every consumer of that
  type — the shaper, the playground and the browser build — moves with it, with
  the browser build's declared interface version raised so a stale page refuses
  to run against a new module

#### Scenario: The open question narrows rather than closes
- **WHEN** the reference records this decision
- **THEN** it states that natural keys are the identity for unowned types on the
  read path only, and that making a natural key the physical identity of an
  owned table — with its consequences for edge tables — remains open

### Requirement: A relationship may be mapped onto a table the system does not own

The system SHALL allow a relationship to name the source and destination key
columns of an existing table, as **lists** of columns, together with that table's
name. When they are named, the system SHALL emit only the graph edge element and
SHALL generate no table. When they are not, the system SHALL generate the edge
table exactly as it does today.

#### Scenario: An existing table becomes an edge element
- **WHEN** a relationship names the source and destination key columns of a
  table that already exists
- **THEN** the property graph declares that table as an edge element over those
  columns, and no create-table statement is emitted for it

#### Scenario: The existing table must be named
- **WHEN** a relationship names key columns but no table
- **THEN** parsing fails naming the field, because a derived table name would
  name a table nobody created

#### Scenario: Edge keys may be multi-column
- **WHEN** an edge's destination vertex is identified by more than one column
- **THEN** the edge element's destination key and its reference both list those
  columns, so the edge can reference a vertex that has no single-column identity

#### Scenario: A traversal over such an edge returns the right rows
- **WHEN** a query traverses a relationship mapped onto an existing table
- **THEN** it returns the rows the underlying foreign-key relationship connects

#### Scenario: One table is both a vertex and an edge
- **WHEN** a table is declared both as a type's vertex element and as another
  type's edge element in the same graph
- **THEN** the graph is generated and created, and queries matching it in either
  role return correct rows — the invariant forbidding a table from appearing
  twice in a graph is narrowed to permit at most one vertex element per table
  rather than at most one element

#### Scenario: No index is demanded on a table the system does not own
- **WHEN** an edge is mapped onto an existing table
- **THEN** the requirement that every edge carry an index on its destination key
  does not apply to it, because the system may emit no index for a table it does
  not own; the requirement is unchanged for generated edge tables

#### Scenario: A relationship to an unowned type without key columns is refused
- **WHEN** a relationship targets an unowned type and names no key columns
- **THEN** parsing fails naming the field, rather than producing a graph whose
  edge is silently absent and whose traversals return nothing

#### Scenario: Generated edge tables are untouched
- **WHEN** a relationship names no key columns
- **THEN** the edge table is generated as before, references the surrogate key
  as before, and carries the index on its destination key that the generator
  invariants require

#### Scenario: An unowned type never gets a generated edge table
- **WHEN** a relationship connects to a type the system does not own
- **THEN** no edge table is generated for it, which is why identity for unowned
  types can change without changing how generated edge tables reference their
  endpoints
