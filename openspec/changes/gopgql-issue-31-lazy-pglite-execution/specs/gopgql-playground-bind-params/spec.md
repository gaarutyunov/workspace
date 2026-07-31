## ADDED Requirements

### Requirement: Compilation exposes the ordered bind values

The playground compile surface SHALL return the compiler's ordered bind values
in a form a caller can bind to a database driver, in addition to the existing
human-readable rendering.

#### Scenario: The values are returned, not only described
- **WHEN** a query carrying variables is compiled
- **THEN** the result carries the ordered bind values themselves, in the order
  the placeholders appear

#### Scenario: The existing rendering is unchanged
- **WHEN** the same query is compiled
- **THEN** the human-readable parameter rendering is exactly what it was before
  this change

#### Scenario: A query with no variables
- **WHEN** a query carrying no variables is compiled
- **THEN** the ordered bind values are empty, and the human-readable rendering
  keeps saying there are none

#### Scenario: Compilation still consults no database
- **WHEN** a query is compiled
- **THEN** no database is contacted, and the values are derived only from the
  supplied variables

#### Scenario: A refusal returns no values
- **WHEN** compilation fails, including refusal for exceeding the
  traversal-depth ceiling
- **THEN** no bind values are returned and the existing error reporting is
  unchanged

### Requirement: The browser surface carries the bind values across explicitly

#### Scenario: Values cross as data, not as display text
- **WHEN** the browser calls the compile entry point
- **THEN** the ordered bind values are available to it as data it can pass to a
  query, distinct from the display rendering

#### Scenario: Value kinds survive the crossing
- **WHEN** variables of differing kinds — text, numbers, booleans, null — are
  bound
- **THEN** each arrives on the browser side as the corresponding value, not as
  its printed form

#### Scenario: The precision limit is documented
- **WHEN** a developer reads the compile entry point's documentation
- **THEN** it states the numeric precision limit imposed by the crossing, so it
  is a known constraint rather than a later surprise

### Requirement: The surface version is raised so a stale module cannot be used silently

The exported API version SHALL be raised by this change, and the page SHALL
require the new version.

#### Scenario: A stale module is refused
- **WHEN** the page is served alongside a generator module built before this
  change
- **THEN** the page reports that the module is out of date and says how to
  rebuild it, rather than running with no bind values

#### Scenario: A stale page is refused
- **WHEN** a page built before this change is served alongside the new module
- **THEN** the version check reports the mismatch

#### Scenario: A matched pair runs
- **WHEN** page and module are built from the same source
- **THEN** the version check passes and execution is available
