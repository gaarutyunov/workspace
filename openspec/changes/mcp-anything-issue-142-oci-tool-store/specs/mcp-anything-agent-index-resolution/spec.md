## ADDED Requirements

These three requirements are the acceptance criteria AgentIQ's SPEC.md §3.2
states on this proxy, quoted rather than restated:

> **mcp-anything** must ship before M4:
> 1. Resolve MCP server and script-tool descriptors from an agent index by digest.
> 1. Expose the resolved closure over Streamable HTTP with CORS.
> 1. Dispatch on `artifactType`: container image vs script artifact.

### Requirement: Descriptors resolve from an agent index by digest

The proxy SHALL accept a reference to an OCI image index — an AgentIQ agent index
— and resolve from it the MCP server and script-tool descriptors it contains,
addressed **by digest**. Resolution SHALL be recursive with cycle detection by
digest and a bounded depth, and SHALL NOT require the index to inline any
referenced content.

A resolved descriptor SHALL be materialised into the store's own artifact format,
so that an index-resolved tool and an `Add`-ed tool are indistinguishable to
`Search` and `Execute`.

#### Scenario: An agent index yields its tools
- **WHEN** the proxy is pointed at an agent index whose `manifests[]` reference
  two script tools and one MCP server
- **THEN** all three are resolved and exposed as tools, and each is addressed by
  the digest the index recorded

#### Scenario: A cycle terminates
- **WHEN** an agent index transitively references itself
- **THEN** resolution terminates with an error naming the repeated digest, rather
  than looping or exhausting memory

#### Scenario: Depth is bounded
- **WHEN** resolution would exceed the configured depth limit
- **THEN** it fails with an error stating the limit and the chain that reached it

#### Scenario: A digest that does not match its content is refused
- **WHEN** a referenced descriptor's content does not hash to the digest the
  index recorded
- **THEN** resolution fails naming the descriptor, and nothing from that index is
  exposed

### Requirement: The resolved closure is served over Streamable HTTP with CORS

The proxy SHALL expose the tools of a resolved closure over the MCP Streamable
HTTP transport, with CORS configured so that a browser-based agent can call it
directly. The allowed origins SHALL be configuration, not a wildcard default.

#### Scenario: A browser agent can call a resolved tool
- **WHEN** a browser-based client on a configured allowed origin issues a
  preflight and then a tool call over Streamable HTTP
- **THEN** the preflight succeeds with that origin, and the tool call returns its
  result

#### Scenario: An unconfigured origin is refused
- **WHEN** a browser client on an origin that is not configured issues a
  preflight
- **THEN** the request is refused, and the default configuration does not permit
  every origin

### Requirement: Dispatch is on artifactType

The proxy SHALL choose how to run a resolved descriptor from its OCI
`artifactType`, distinguishing at least a container-image reference from a script
artifact. It SHALL NOT infer the kind from a tag, a repository name, a file
extension or an annotation that a producer is free to omit.

An unrecognised `artifactType` SHALL be carried through and reported, not guessed
at: the descriptor is listed as unsupported and refuses to execute.

#### Scenario: A script artifact and a container image take different paths
- **WHEN** a closure contains one descriptor whose `artifactType` is the epos
  script tool type and one that is a container image
- **THEN** the first is executed by the script runtime and the second is treated
  as an MCP server reference, with the dispatch decided by `artifactType` alone

#### Scenario: An unknown artifactType is reported, not guessed
- **WHEN** a closure contains a descriptor with an `artifactType` the proxy does
  not recognise
- **THEN** it is listed as unsupported naming the type, executing it fails with
  that same message, and the rest of the closure is unaffected

#### Scenario: Dispatch does not consult the tag
- **WHEN** a script artifact is tagged with a name suggesting a container image
- **THEN** it is still dispatched as a script artifact
