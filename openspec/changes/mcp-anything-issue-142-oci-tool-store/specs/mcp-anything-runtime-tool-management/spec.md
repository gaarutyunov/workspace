## ADDED Requirements

### Requirement: The proxy exposes Search, Execute, Add and Delete

When a tool store is configured, the proxy SHALL expose four MCP tools — named on
the wire `store_search`, `store_execute`, `store_add` and `store_delete` —
through which an agent discovers, runs, creates and removes tools at runtime
without restarting the proxy and without any change to a declaration outside the
proxy.

The names SHALL be snake_case, matching every other tool this proxy exposes.
Referring to them as Search, Execute, Add and Delete in prose is not a licence to
put those strings on the wire.

#### Scenario: An added tool is callable without a restart
- **WHEN** an agent calls `store_add` with a valid tool definition and then calls
  `store_execute` naming that tool
- **THEN** the tool runs and returns its result, with no proxy restart and no
  configuration reload

#### Scenario: A deleted tool stops being callable
- **WHEN** an agent calls `store_delete` on a stored tool and then calls
  `store_execute` on it
- **THEN** `store_execute` returns an error stating the tool does not exist

#### Scenario: The four tools are absent without a store
- **WHEN** no tool store is configured
- **THEN** none of the four store tools is present in `tools/list`, and the
  proxy's behaviour is identical to before this change

### Requirement: The four tools survive the tools/list collapse, and stored tools do not appear in it

The proxy's list-tools middleware returns only the search tool when tool search
is enabled for an endpoint. It SHALL additionally return the four store tools
whenever a store is configured, because a store is most useful in exactly the
deployments that enable search, and the four tools would otherwise be
unreachable.

Stored tools themselves SHALL be ordinary registry entries, dispatchable by their
prefixed name, and SHALL be omitted from `tools/list` while a store is
configured — listing them is the per-session token cost the feature exists to
avoid. `store_execute` SHALL be the path an agent uses to call a tool it has just
found, without a `tools/list` round trip.

`store_search` SHALL NOT replace the existing `search_tools` tool, and SHALL NOT
change its response. The two search different sets and coexist.

#### Scenario: Both search and the store tools are listed
- **WHEN** an endpoint has both tool search and a tool store enabled
- **THEN** `tools/list` returns the search tool and the four store tools

#### Scenario: Stored tools stay out of the listing
- **WHEN** forty tools have been added to the store
- **THEN** `tools/list` does not grow by forty entries

#### Scenario: A known stored tool is directly dispatchable
- **WHEN** a client calls a stored tool by its prefixed name without going
  through `store_execute`
- **THEN** the call reaches the same tool and returns the same result

#### Scenario: The existing search tool is unchanged
- **WHEN** a deployment with tool search and no tool store is upgraded to this
  version
- **THEN** `search_tools` returns exactly what it returned before, including each
  hit's full `inputSchema`

### Requirement: Added tools survive a configuration reload

Adding and removing tools SHALL go through the registry-manager seam that
rebuilds and swaps the registry, presenting the store as one synthetic upstream;
the tool registry itself remains immutable after construction.

A configuration reload SHALL re-materialise the store's tools. An edit to the
config file that is unrelated to the tool store SHALL NOT remove tools that were
added at runtime.

#### Scenario: An unrelated config edit does not drop added tools
- **WHEN** a tool is added at runtime and the configuration file is then edited
  in a way that touches no store setting, triggering a reload
- **THEN** the added tool is still listed and still callable

#### Scenario: A reload does not resurrect a deleted tool
- **WHEN** a stored tool is deleted and the configuration is then reloaded
- **THEN** the tool does not come back

### Requirement: Search results are bounded and never carry a full input schema

A `store_search` result SHALL be its own result type, leaving the existing
`search_tools` response untouched. It SHALL carry the fully-qualified tool name, a description
truncated to a configured budget on a rune boundary, and a flattened list of top-level parameters as
name, type and whether each is required. It SHALL NOT carry the tool's
`inputSchema`, nested property schemas, per-property descriptions, enums or
examples.

A `store_search` response SHALL be bounded by a configured maximum size, SHALL truncate
its result list to fit, and SHALL report how many results were elided.

#### Scenario: A hit costs a predictable number of tokens
- **WHEN** `store_search` returns a tool whose `inputSchema` is large
- **THEN** the response contains no part of that schema, and its size is
  independent of the schema's size

#### Scenario: An over-budget response is truncated and says so
- **WHEN** the number of matches would exceed the configured response budget
- **THEN** the response contains as many results as fit and states the number
  omitted

#### Scenario: Parameters are still discoverable
- **WHEN** `store_search` returns a tool taking three parameters, one of them required
- **THEN** the result names all three, gives each a type, and marks which is
  required

### Requirement: Execute validates arguments and returns actionable errors

`store_execute` SHALL validate the supplied arguments server-side against the tool's
full input schema and, on failure, SHALL return an error naming the offending
parameter and what was wrong with it — so that an agent never needs the full
schema in order to call a tool correctly.

#### Scenario: A missing required argument is named
- **WHEN** `store_execute` is called without a required parameter
- **THEN** the error names that parameter and states that it is required

#### Scenario: A wrong argument type is named
- **WHEN** `store_execute` is called with a string where a number is required
- **THEN** the error names the parameter, the expected type and the received type

### Requirement: Search works without an embedding provider

`store_search` SHALL fall back to lexical matching over the derived index — name,
description and parameter names — when no embedding provider is configured, and
SHALL report which mode produced the results. Semantic search SHALL NOT be a
prerequisite for `store_search` to function.

#### Scenario: A laptop with no API key can search
- **WHEN** the proxy runs with a tool store and no embedding provider configured
- **THEN** `store_search` returns matching tools and no outbound network request is
  made in order to serve the query

#### Scenario: The mode is reported
- **WHEN** `store_search` returns results
- **THEN** the response states whether they came from semantic or lexical
  matching

### Requirement: Add accepts all supported tool sources

`store_add` SHALL accept a JavaScript, Lua, Bash or OpenAPI-operation tool definition,
and an MCP server reference, and SHALL persist each as an artifact in the tool
store. A `store_add` of an OpenAPI source SHALL store one artifact per selected
operation rather than one artifact per document.

#### Scenario: A script tool round-trips
- **WHEN** a JavaScript tool is added and the proxy is restarted
- **THEN** the tool is present, its source is byte-identical to what was
  supplied, and it executes

#### Scenario: One OpenAPI operation becomes one tool
- **WHEN** an OpenAPI document with twelve operations is added selecting one
- **THEN** exactly one artifact is stored, and `store_search` returns exactly one tool
  for it

#### Scenario: An invalid definition is rejected before anything is written
- **WHEN** `store_add` is called with a definition whose input schema is not valid JSON
  Schema
- **THEN** the call fails with an error naming the problem and no artifact is
  written to the store

### Requirement: Adding is not publishing

`store_add` SHALL write only to the store the proxy reads from. Publishing to a
different registry SHALL require an explicit promotion request.

#### Scenario: An experiment stays local
- **WHEN** an agent adds a tool on a proxy with a promotion target configured and
  does not request promotion
- **THEN** nothing is pushed to the promotion target

### Requirement: Unsandboxed runtimes are off by default

Each tool source SHALL be individually enable-able. Bash tools and stdio-spawned
MCP servers SHALL be disabled unless explicitly enabled in configuration, because
they run with the full authority of the proxy process.

#### Scenario: Bash is refused when not enabled
- **WHEN** `store_add` is called with a Bash tool on a proxy that has not enabled the
  bash source
- **THEN** the call fails with an error stating that the source is disabled, and
  no artifact is written

#### Scenario: Enabling is deliberate and documented
- **WHEN** a developer reads the configuration reference for the bash source
- **THEN** it states that a Bash tool runs with the proxy's filesystem, network,
  environment and credentials, and that anyone able to call `store_add` on such a proxy
  can execute arbitrary commands in it

#### Scenario: Sandboxed runtimes are unaffected
- **WHEN** the bash and stdio sources are disabled
- **THEN** JavaScript, Lua and OpenAPI tools can still be added and executed

### Requirement: An added tool cannot aim an existing credential at a URL of its choosing

An `store_add`-ed OpenAPI tool MAY reference an existing named outbound-auth
credential **only** when its base URL is the base URL of the upstream that owns
that credential, or is on an explicitly configured allowlist for it. Any other
base URL SHALL be permitted but SHALL be called unauthenticated.

Requesting a credential for a base URL that is neither SHALL fail with an error
naming both the credential and the URL. It SHALL NOT silently drop the credential
and proceed, because an agent would then believe an unauthenticated call was
authenticated.

This closes a path the runtime capability gate does not cover: an agent that can
choose both a base URL and a credential name has asked the proxy to send an
upstream's token to a destination of the agent's choosing.

#### Scenario: A credential cannot be redirected
- **WHEN** `store_add` supplies an OpenAPI operation with base URL
  `https://attacker.example` and names the outbound-auth credential belonging to
  a configured GitHub upstream
- **THEN** the call fails naming both, and no artifact is written

#### Scenario: The matching pairing is allowed
- **WHEN** `store_add` supplies an OpenAPI operation whose base URL is the
  configured GitHub upstream's own base URL and names that upstream's credential
- **THEN** the tool is stored and executes authenticated

#### Scenario: An unauthenticated third-party call is still possible
- **WHEN** `store_add` supplies an operation against an arbitrary public API and
  names no credential
- **THEN** the tool is stored and executes without any credential attached

### Requirement: Declared tools take precedence over stored tools

Store-added tools SHALL carry their own tool prefix, defaulting to `scratch`.
Where a stored tool's fully-qualified name nonetheless collides with a
configuration- or CRD-declared tool, the declared tool SHALL win: the stored tool
is shadowed, the collision is logged, and `store_search` marks it as shadowed.
`store_add` of a name that would be shadowed SHALL fail rather than write an
uncallable artifact.

Shadowing SHALL apply **only** to a store-versus-declared collision, and SHALL be
resolved before the tool registry is constructed. A collision between two
*declared* upstreams — a shared tool prefix, or a duplicate prefixed name —
SHALL remain a fatal construction error as it is today. Weakening those into
warnings is not permitted: a configuration with two upstreams claiming one prefix
is a deployment mistake and must keep failing loudly.

#### Scenario: Two declared upstreams still fail loudly
- **WHEN** two configuration-declared upstreams share a tool prefix, on a proxy
  that also has a tool store configured
- **THEN** the proxy fails to construct its registry with an error naming both
  upstreams, exactly as it does without a store

#### Scenario: The default prefix prevents collisions
- **WHEN** a tool named `create_issue` is added to the store while a configured
  upstream also exposes `create_issue`
- **THEN** the stored tool is exposed as `scratch__create_issue` and both are
  callable

#### Scenario: A deliberate collision resolves to the declaration
- **WHEN** the store prefix is configured to match a declared upstream's prefix
  and a name collides
- **THEN** calls to that name reach the declared tool, and the collision is
  logged with both sources named

#### Scenario: Adding a colliding name fails loudly
- **WHEN** `store_add` is called with a name that would be shadowed by a declared tool
- **THEN** the call fails with an error naming the declared tool that wins, and
  no artifact is written
