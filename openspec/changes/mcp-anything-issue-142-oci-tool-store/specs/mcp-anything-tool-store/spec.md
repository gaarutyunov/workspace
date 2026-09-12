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

#### Scenario: A network filesystem is refused
- **WHEN** the configured store path is on a positively identified network
  filesystem, such as NFS or SMB
- **THEN** the proxy fails at startup with an error naming the path, rather than
  starting and corrupting the index later

#### Scenario: An unrecognised filesystem warns and continues
- **WHEN** the filesystem type of the configured store path cannot be determined
- **THEN** the proxy logs a warning naming the path and starts, because refusing
  on "unknown" would break ordinary local filesystems the check has not been
  taught

### Requirement: The searchable index is derived, in-memory and annotation-only

The proxy SHALL build its tool index by walking `index.json` and reading manifest
annotations, and SHALL NOT fetch a layer blob in order to index a tool. The index
SHALL NOT be persisted. It SHALL be rebuilt at startup and refreshed after every
`Add` and `Delete`.

Tool name, description, runtime and the flattened parameter list SHALL be stored
in manifest annotations so that this is possible.

The index SHALL be an immutable value swapped atomically on rebuild, not mutated
in place: a reader SHALL never observe a partially rebuilt index and SHALL never
need a lock.

#### Scenario: Searching during a rebuild is race-free and consistent
- **WHEN** searches run continuously while tools are added and deleted, under the
  race detector
- **THEN** no race is reported, and every search returns a result set consistent
  with some single point in time rather than a mixture of two

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

### Requirement: A shared store is registry-backed, and the unsupported combination refuses to start

A local OCI layout is per-process and, in Kubernetes, per-pod: it does not
coordinate between replicas. The proxy SHALL therefore support a registry-backed
store mode in which a configured OCI registry is the store and the local layout
is a pull-through cache, refreshed on a configured interval and on cache miss. In
this mode `Add` SHALL pack, push to the registry, and invalidate the local cache,
so the tool is live on the writing pod immediately.

The `tool_store` configuration SHALL carry an explicit `shared` flag, defaulting
to false. The proxy SHALL refuse to start when `shared` is true and the store is
local-only, rather than serving an inconsistent tool set silently. The Helm chart
and the operator SHALL set `shared` from the replica count they render, because a
pod cannot read its own replica count.

#### Scenario: The unsupported combination is refused loudly
- **WHEN** the proxy starts with `shared` true and a local-only store
- **THEN** it exits with an error naming both the store mode and the flag, and
  serves no requests

#### Scenario: A chart rendering multiple replicas fails at template time
- **WHEN** the Helm chart is rendered with a replica count above one and a
  local-only tool store
- **THEN** templating fails with the same explanation, rather than producing a
  Deployment whose pods will refuse to start

#### Scenario: The default single-process deployment is unaffected
- **WHEN** the proxy runs with a local-only store and `shared` unset
- **THEN** it starts normally and no registry is contacted

#### Scenario: A registry-backed add is live locally at once
- **WHEN** a tool is added on a proxy in registry-backed mode
- **THEN** it is pushed to the registry and callable on that same proxy
  immediately, without waiting for a refresh interval

#### Scenario: Another replica converges within one interval
- **WHEN** a tool is added through one replica in registry-backed mode
- **THEN** a second replica serves it after at most one refresh interval, and the
  configuration documents that interval as the staleness bound

### Requirement: Registry access is configured, credentialed and bounded

Every remote registry operation — pull, push and promotion copy — SHALL take a
`context.Context` and a configured per-operation timeout, and SHALL obtain
credentials from configuration. Secrets SHALL be referenced with the repository's
`${ENV_VAR}` indirection and SHALL NOT be written literally in a config file. TLS
settings SHALL be configurable per registry host, including an explicit
plain-HTTP opt-in for a local registry.

#### Scenario: No ambient credentials are used unless requested
- **WHEN** the proxy pushes to a registry and no credentials are configured for
  that host
- **THEN** it does not silently fall back to an ambient Docker config file unless
  the deployment has opted into that fallback

#### Scenario: A hung registry does not hang the tool call
- **WHEN** a registry stops responding mid-push
- **THEN** the operation fails within the configured timeout with an error naming
  the registry, and the proxy continues serving every other tool

#### Scenario: A secret is not readable from the rendered config
- **WHEN** a deployment configures registry credentials
- **THEN** the config file contains an `${ENV_VAR}` reference and not the secret

### Requirement: OCI access is confined to one package

All use of `oras.land/oras-go/v2` SHALL be confined to the single store package,
enforced by a linter rule rather than by review, so that adopting a published
epos Go API later is a change to one package.

#### Scenario: An import outside the store package fails the build
- **WHEN** any package other than the store package imports `oras-go`
- **THEN** the lint step fails with a message naming the rule
