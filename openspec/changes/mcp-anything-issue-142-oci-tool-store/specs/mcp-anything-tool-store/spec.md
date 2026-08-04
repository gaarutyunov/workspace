## ADDED Requirements

### Requirement: The tool store is an OCI image layout and nothing else is durable

The proxy SHALL persist agent-added tools in an OCI Image Layout — `oci-layout`,
`index.json`, `blobs/sha256/` — at a configured path, defaulting to
`~/.mcp-anything/store`. No relational database, embedded key-value store or
sidecar state file SHALL be required for, or used by, tool storage.

#### Scenario: A tool survives a restart with no database present
- **WHEN** a tool is added, the proxy is stopped, and the proxy is started again
  with no database of any kind available
- **THEN** the tool is present and callable

#### Scenario: The store is a valid OCI layout
- **WHEN** a tool has been added to the store
- **THEN** the store directory validates as an OCI Image Layout, and `oras`
  resolves and pulls the tool's tag without any mcp-anything-specific knowledge

#### Scenario: No store configured leaves behaviour unchanged
- **WHEN** the proxy runs with no tool store configured
- **THEN** it starts, serves every configured and CRD-declared upstream exactly
  as before, and the four store tools are absent

### Requirement: Stored tools use the epos tool artifact format

A stored tool SHALL be an OCI image manifest with `artifactType`
`application/vnd.epos.tool.script.v1+json` (script tools) or
`application/vnd.epos.tool.mcp.v1+json` (MCP servers), the empty config
descriptor `application/vnd.oci.empty.v1+json`, and exactly one layer. Script
tool layers SHALL use `application/vnd.epos.tool.script.layer.v1+tar`. The
payload document SHALL use the `epos.dev/v1alpha1` envelope with `kind: Tool`.
Annotations SHALL use the `dev.epos.*` namespace, and MCP server manifests SHALL
carry `io.modelcontextprotocol.server.name`.

#### Scenario: An artifact written here is readable by epos tooling
- **WHEN** a script tool is packed by the proxy and pushed to a registry
- **THEN** its media types, config descriptor and annotations match the epos tool
  artifact specification, and an epos-conformant client resolves it

#### Scenario: An unknown runtime is carried, not lost
- **WHEN** the store contains a tool whose `spec.runtime` the proxy does not
  recognise
- **THEN** the tool is indexed and listed, `Execute` on it fails with an error
  naming the unsupported runtime, and the artifact is neither rewritten nor
  deleted

### Requirement: The store is safe against concurrent processes

Because the OCI Image Layout specification is silent on concurrency and
`oras-go`'s `content/oci.Store` is single-process only, the proxy SHALL supply
the missing guarantees: advisory file locking, an atomic `index.json` write, and
opening the store inside the lock.

The proxy SHALL take a shared lock for resolve, fetch and index rebuild, and an
exclusive lock for pack, push, tag, untag, delete and retention. It SHALL set
`AutoSaveIndex` to false and write `index.json` via temporary file, `fsync` and
rename. It SHALL close every content reader before any delete.

#### Scenario: Two processes adding tools concurrently lose nothing
- **WHEN** two proxy processes each add a different tool to the same store
  concurrently
- **THEN** both tools are present in `index.json` afterwards, and neither
  process's tag has been lost

#### Scenario: A crash mid-write leaves a readable index
- **WHEN** a process is killed during an index write
- **THEN** the store still resolves every tool that was present before the
  interrupted write, and `index.json` is not truncated

#### Scenario: A non-local filesystem is refused
- **WHEN** the configured store path is on a filesystem where advisory locking is
  unreliable
- **THEN** the proxy fails at startup with an error naming the path, rather than
  starting and corrupting the index later

### Requirement: The searchable index is derived, in-memory and annotation-only

The proxy SHALL build its tool index by walking `index.json` and reading manifest
annotations, and SHALL NOT fetch a layer blob in order to index a tool. The index
SHALL NOT be persisted. It SHALL be rebuilt at startup and refreshed after every
`Add` and `Delete`.

Tool name, description, runtime and the flattened parameter list SHALL be stored
in manifest annotations so that this is possible.

#### Scenario: Indexing reads no blobs
- **WHEN** the proxy starts against a store containing tools
- **THEN** the number of blob fetches performed during index construction is zero

#### Scenario: The index is reconstructible from the layout alone
- **WHEN** the proxy is killed without a clean shutdown and restarted
- **THEN** the index is identical to the one before the kill, and no recovery,
  repair or migration step runs

#### Scenario: A manifest missing required annotations is reported, not fatal
- **WHEN** the store contains a manifest without `dev.epos.name`
- **THEN** the proxy logs a warning naming the digest, skips the manifest, and
  continues indexing the rest

### Requirement: Retention bounds the store without deleting live tools

The proxy SHALL retain the most recent N versions per tool name, with N
configurable and retention disable-able. Retention SHALL run on `Add`, not on a
timer. It SHALL NOT remove any artifact referenced by the live tool registry
snapshot.

Removal SHALL be untag followed by delete with automatic garbage collection,
because a tagged manifest is protected from collection.

#### Scenario: Old versions of one tool are collected
- **WHEN** retention is set to keep 3 and a sixth version of one tool name is
  added
- **THEN** the three most recent versions remain resolvable and the older ones
  are removed from the layout

#### Scenario: Distinct tools are never collected by retention
- **WHEN** retention is set to keep 3 and forty distinct tool names are stored
- **THEN** all forty remain present

#### Scenario: A tool in the live registry is not collected
- **WHEN** retention would remove an artifact that the currently served tool
  registry still references
- **THEN** the artifact is retained and the reason is logged

#### Scenario: Deletion actually reclaims blobs
- **WHEN** a tool version is removed by retention
- **THEN** its manifest and its layer blob are gone from `blobs/sha256/`, and the
  store still validates as an OCI layout

### Requirement: A tool can be promoted to a registry without changing format

The proxy SHALL support copying a stored tool to a configured OCI registry as an
explicit operation, and SHALL NOT push to any registry as a side effect of `Add`.

#### Scenario: Promotion publishes an unmodified artifact
- **WHEN** a stored tool is promoted to a registry
- **THEN** the artifact's digest is unchanged by the copy, and it is pullable by
  any OCI client

#### Scenario: Adding does not publish
- **WHEN** a tool is added without requesting promotion
- **THEN** no request is made to any remote registry

### Requirement: OCI access is confined to one package

All use of `oras.land/oras-go/v2` SHALL be confined to the single store package,
enforced by a linter rule rather than by review, so that adopting a published
epos Go API later is a change to one package.

#### Scenario: An import outside the store package fails the build
- **WHEN** any package other than the store package imports `oras-go`
- **THEN** the lint step fails with a message naming the rule
