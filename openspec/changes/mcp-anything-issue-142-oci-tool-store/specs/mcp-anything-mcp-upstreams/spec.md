## ADDED Requirements

### Requirement: An MCP server is an upstream type

The proxy SHALL support an upstream of type `mcp` that speaks the Model Context
Protocol to another server and re-exposes that server's tools as its own. The
type SHALL be registered through the existing builder registry, and SHALL be
declarable in configuration, in an `MCPUpstream` CRD, and as a stored artifact.

This reverses SPEC.md §2's documented non-goal *"Aggregating other MCP servers
(HTTP REST upstreams only)"*. The reversal SHALL be recorded in SPEC.md rather
than left as a contradiction between the document and the code.

#### Scenario: A remote MCP server's tools appear in the proxy
- **WHEN** an upstream of type `mcp` names a reachable Streamable HTTP endpoint
- **THEN** every tool that server advertises is listed by the proxy, and calling
  one through the proxy returns that server's result

#### Scenario: The non-goal is struck, not contradicted
- **WHEN** a reader consults SPEC.md §2 after this change
- **THEN** aggregating MCP servers is no longer listed as a non-goal, and the
  section states that it was one and why it changed

#### Scenario: An unreachable MCP upstream degrades the proxy and nothing else
- **WHEN** an `mcp` upstream cannot be reached at load time
- **THEN** the proxy starts, serves every other upstream, and reports the failing
  upstream through the existing readiness surface

### Requirement: Three reference forms, in preference order, and none requires Docker

An `mcp` upstream SHALL be referenceable as a remote Streamable HTTP endpoint
with an outbound-auth reference, as a local stdio command spawned by the proxy,
or as a container image. The proxy SHALL NOT require a container runtime: the
container form SHALL be usable only where a runtime already exists, and the proxy
SHALL NOT shell out to Docker in any deployment.

#### Scenario: A laptop with no container runtime serves MCP upstreams
- **WHEN** the proxy runs with no container runtime installed and declares a
  remote and a stdio MCP upstream
- **THEN** both work, and no container runtime is invoked

#### Scenario: A container-image MCP server in Kubernetes is a declared sidecar
- **WHEN** an MCP upstream references a container image in a cluster deployment
- **THEN** the operator declares it as a sidecar and the proxy connects to it as
  a local endpoint, rather than the proxy launching a container itself

#### Scenario: A stdio server outliving one call is managed
- **WHEN** a stdio MCP upstream is spawned
- **THEN** the process is supervised for the life of the upstream, its stderr is
  captured into the proxy's logs, and it is terminated on shutdown and on
  upstream removal

### Requirement: MCP upstream tools are namespaced and collision-free

Tools re-exposed from an MCP upstream SHALL carry the existing
`{prefix}__{tool}` namespacing, using the upstream's configured tool prefix. Two
MCP upstreams advertising the same tool name SHALL both remain callable.

#### Scenario: Two servers advertising the same tool both stay callable
- **WHEN** two `mcp` upstreams with prefixes `a` and `b` each advertise `search`
- **THEN** the proxy exposes `a__search` and `b__search`, and each dispatches to
  its own server

#### Scenario: A prefix collision is refused at load, not at call time
- **WHEN** two upstreams are declared with the same tool prefix
- **THEN** loading fails with an error naming both upstreams

### Requirement: A stored MCP server artifact is the server descriptor

An MCP server persisted in the tool store SHALL be an OCI manifest with
`artifactType` `application/vnd.epos.tool.mcp.v1+json` carrying one layer whose
content is the MCP Registry `server.json` descriptor, with the manifest annotated
`io.modelcontextprotocol.server.name`. No `Tool` document SHALL be required for
this artifact type.

The proxy SHALL read the reference form from `server.json`'s own `remotes[]` and
`packages[]` fields rather than from a mcp-anything-specific field.

#### Scenario: A stored MCP server round-trips
- **WHEN** an MCP server is added to the store and the proxy is restarted
- **THEN** the server is reconnected and its tools are listed, with no
  configuration change

#### Scenario: The descriptor is the authoritative source
- **WHEN** a stored MCP server artifact's `server.json` names both a remote and
  an npm package
- **THEN** the proxy uses the remote, per the reference preference order, without
  requiring the artifact to say which to prefer

### Requirement: Spawned MCP servers run with the proxy's authority and are off by default

A stdio-spawned MCP server SHALL be treated as an unsandboxed source: disabled
unless explicitly enabled in configuration, and documented as running with the
proxy's filesystem, network, environment and credentials. Remote MCP upstreams
SHALL NOT be subject to this gate, because they run in someone else's process.

#### Scenario: Stdio is refused when not enabled
- **WHEN** a stdio MCP upstream is declared on a proxy that has not enabled the
  stdio source
- **THEN** loading that upstream fails with an error stating the source is
  disabled, and the proxy continues to serve its other upstreams

#### Scenario: Remote MCP needs no such gate
- **WHEN** only remote MCP upstreams are declared and the stdio source is
  disabled
- **THEN** every upstream loads normally
