## ADDED Requirements

### Requirement: The project exposes one public Go package

The system SHALL expose a single public Go package under `pkg/`, importable from
another module, and SHALL keep every other package internal.

The format's document and closure types SHALL be **declared in** the public
package, and the internal packages SHALL import them, rather than being mirrored
across a conversion layer that would have to be maintained in both directions.
These types are the wire format, so they change when the format changes, which is
exactly when a consumer needs to know.

The public package SHALL NOT export machinery — store internals, registry
clients, or locking — and SHALL limit third-party types in its exported surface
to the OCI descriptor type, which is what a descriptor already is and which
carries its own compatibility promise.

#### Scenario: The package is importable from another module
- **WHEN** another module imports the public package
- **THEN** it compiles, without any part of the project's internal packages being
  reachable

#### Scenario: An internal type does not leak
- **WHEN** the public package's exported surface is inspected
- **THEN** no exported identifier has a type declared in an internal package in
  its signature

#### Scenario: There is one declaration of each format type
- **WHEN** a document type is looked for
- **THEN** it is found once, in the public package, and the internal code that
  packs and resolves it uses that same declaration

#### Scenario: The binaries do not grow
- **WHEN** the import-hygiene guard for the command binaries runs
- **THEN** the public package has not pulled the catalog, its database driver or
  its Markdown renderer into the CLI binary

### Requirement: The public package exposes resolution and the closure types

The system SHALL export a resolver, the closure types, the maximum depth, and the
depth and cycle errors, so that a consumer can resolve an agent inside its own
process rather than by invoking a subprocess.

A closure SHALL expose the index digest, the definition, the optional instruction
and model, the referenced skills, the referenced tools, and the recursively
resolved sub-agents.

#### Scenario: An agent resolves inside a caller's process
- **WHEN** a consumer calls the resolver with a reference
- **THEN** a closure is returned, with no process spawned and no binary required
  on the caller's path

#### Scenario: The depth and cycle errors are matchable
- **WHEN** resolution exceeds the depth limit
- **THEN** the returned error matches the exported depth error by identity, so a
  caller branches on it rather than on message text

#### Scenario: Skills and tools arrive as descriptors
- **WHEN** a closure is inspected
- **THEN** each skill and each payload-bearing tool is a descriptor with its
  annotations, and fetching its content is a separate, explicit call

### Requirement: Resolution options are explicit, and there is no ambient form

The system SHALL construct a resolver from explicit options — the store root, the
registry credentials, the plain-HTTP switch and a per-operation timeout — because
resolution cannot be performed without them and taking them from ambient process
state makes a caller's behaviour depend on hidden input.

The system SHALL NOT provide a package-level resolution function taking only a
context and a reference. Such a function could work only by reading ambient
state, and a caller expected to be reproducible — a durable workflow step is the
motivating case — must not have a hidden input available to it by default.

Unset options SHALL fall back to the same defaults the command-line tool uses, so
that a zero-valued options value is usable. The defaults SHALL be a documented
fallback rather than an invisible one.

#### Scenario: A caller supplies its own options
- **WHEN** a resolver is constructed with an explicit store root and registry
  configuration
- **THEN** resolution uses them and reads no environment variable

#### Scenario: Unset options fall back to the tool's defaults
- **WHEN** a resolver is constructed with no options set
- **THEN** it resolves against the same store root and the same stored credentials
  the command-line tool would use, and the documentation states that this is what
  happens

#### Scenario: A test drives resolution against a disposable registry
- **WHEN** a test constructs a resolver pointing at a container registry over
  plain HTTP
- **THEN** resolution succeeds without any process-wide environment being set

### Requirement: The public package exposes packing and publishing, not resolution alone

The system SHALL export packing a closure and publishing a closure, in addition
to resolution, so that a consumer that writes artifacts can depend on this
package instead of reimplementing the format.

#### Scenario: A consumer packs a conformant artifact through the API
- **WHEN** a consumer packs a tool through the public package
- **THEN** the resulting artifact carries the media types, config descriptor,
  layer and annotations this specification defines, and epos resolves it

#### Scenario: A consumer publishes a closure through the API
- **WHEN** a consumer publishes a packed closure to a registry through the public
  package
- **THEN** the whole closure is transferred and the index is pushed last

#### Scenario: The artifact is the contract, not the API
- **WHEN** a consumer implements the format without importing this package
- **THEN** its artifacts are accepted, because conformance is defined over the
  published bytes

### Requirement: The public package states what it promises

The system SHALL document the public package's stability: what is covered by
version compatibility, that the package is pre-1.0 while the format is at an
alpha API version, and which identifiers a consumer should pin against.

#### Scenario: The stability promise is discoverable
- **WHEN** the public package's documentation is read
- **THEN** it states the compatibility promise and the version at which the
  promise begins, rather than leaving a consumer to infer it from a tag
</content>
