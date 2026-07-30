## ADDED Requirements

### Requirement: The PostgreSQL runtime is a pinned, immutable, verifiable build

The playground SHALL obtain its in-browser PostgreSQL from one named, immutable
build artifact, pinned so that every machine and every CI run resolves the same
bytes or fails.

#### Scenario: The build is named, not floating
- **WHEN** the docs dependency manifest is read
- **THEN** it names an exact published build of the fork, not a version range
  and not a branch

#### Scenario: A clean install reproduces exact bytes
- **WHEN** a clean install is performed from the committed lockfile
- **THEN** it resolves the same artifact and verifies it against a recorded
  integrity hash

#### Scenario: A substituted artifact fails the build
- **WHEN** the bytes behind the pinned location differ from the recorded hash
- **THEN** the install fails, and no site is produced from unverified bytes

#### Scenario: No credentials are required
- **WHEN** the site is built in CI or on a fresh developer machine
- **THEN** the runtime is obtained without any registry credential or secret

#### Scenario: Moving to a newer build is an explicit edit
- **WHEN** a newer build of the fork is adopted
- **THEN** the pin and the lockfile change together in a reviewable commit, and
  nothing about the site changes until they do

### Requirement: The runtime provides SQL/PGQ

The pinned build SHALL be able to create a property graph and evaluate a
`GRAPH_TABLE` query. This SHALL be demonstrated by execution against the pinned
build, not inferred from its provenance.

#### Scenario: A property graph can be created
- **WHEN** the generated schema, including its `CREATE PROPERTY GRAPH`
  statement, is applied to a fresh database on the pinned build
- **THEN** it succeeds

#### Scenario: A GRAPH_TABLE query returns rows
- **WHEN** a compiled `GRAPH_TABLE` query with bind parameters is executed over
  seeded data on the pinned build
- **THEN** it returns the rows the query selects

#### Scenario: The capability is proven before it is depended on
- **WHEN** the change is implemented
- **THEN** an automated check exercises property-graph creation and
  `GRAPH_TABLE` evaluation against the pinned build in the same environment the
  playground uses, and fails the build if either stops working

#### Scenario: A future build that loses SQL/PGQ is caught
- **WHEN** the pin is moved to a build without working SQL/PGQ
- **THEN** that check fails rather than the playground failing for readers

### Requirement: The runtime needs no cross-origin isolation

Serving the playground SHALL NOT require COOP/COEP response headers, a
cross-origin-isolation service worker, or `SharedArrayBuffer`.

#### Scenario: The site works on plain static hosting
- **WHEN** the site is served from static hosting that sets no isolation
  headers
- **THEN** the runtime loads and executes queries

#### Scenario: No shared memory is introduced
- **WHEN** the runtime and the generator exchange data
- **THEN** they do so without any shared memory buffer between them

### Requirement: The runtime's provenance is recorded where a reader can find it

#### Scenario: The page states what it is running
- **WHEN** a reader has run a query
- **THEN** the page states which PostgreSQL version and which fork build
  produced the result

#### Scenario: No assumption about the version string's shape
- **WHEN** anything reads the server version
- **THEN** it does not require the version string to carry a PGlite version
  suffix, which this build does not emit
