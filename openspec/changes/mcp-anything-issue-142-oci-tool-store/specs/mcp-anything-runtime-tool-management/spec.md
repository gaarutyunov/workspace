## ADDED Requirements

### Requirement: The proxy exposes Search, Execute, Add and Delete

When a tool store is configured, the proxy SHALL expose four MCP tools —
`Search`, `Execute`, `Add` and `Delete` — through which an agent discovers, runs,
creates and removes tools at runtime without restarting the proxy and without any
change to a declaration outside the proxy.

#### Scenario: An added tool is callable without a restart
- **WHEN** an agent calls `Add` with a valid tool definition and then calls
  `Execute` naming that tool
- **THEN** the tool runs and returns its result, with no proxy restart and no
  configuration reload

#### Scenario: A deleted tool stops being callable
- **WHEN** an agent calls `Delete` on a stored tool and then calls `Execute` on it
- **THEN** `Execute` returns an error stating the tool does not exist

#### Scenario: The four tools are absent without a store
- **WHEN** no tool store is configured
- **THEN** `Search`, `Execute`, `Add` and `Delete` are not present in
  `tools/list`

### Requirement: Search results are bounded and never carry a full input schema

A `Search` result SHALL carry the fully-qualified tool name, a description
truncated to a configured budget, and a flattened list of top-level parameters as
name, type and whether each is required. It SHALL NOT carry the tool's
`inputSchema`, nested property schemas, per-property descriptions, enums or
examples.

A `Search` response SHALL be bounded by a configured maximum size, SHALL truncate
its result list to fit, and SHALL report how many results were elided.

#### Scenario: A hit costs a predictable number of tokens
- **WHEN** `Search` returns a tool whose `inputSchema` is large
- **THEN** the response contains no part of that schema, and its size is
  independent of the schema's size

#### Scenario: An over-budget response is truncated and says so
- **WHEN** the number of matches would exceed the configured response budget
- **THEN** the response contains as many results as fit and states the number
  omitted

#### Scenario: Parameters are still discoverable
- **WHEN** `Search` returns a tool taking three parameters, one of them required
- **THEN** the result names all three, gives each a type, and marks which is
  required

### Requirement: Execute validates arguments and returns actionable errors

`Execute` SHALL validate the supplied arguments server-side against the tool's
full input schema and, on failure, SHALL return an error naming the offending
parameter and what was wrong with it — so that an agent never needs the full
schema in order to call a tool correctly.

#### Scenario: A missing required argument is named
- **WHEN** `Execute` is called without a required parameter
- **THEN** the error names that parameter and states that it is required

#### Scenario: A wrong argument type is named
- **WHEN** `Execute` is called with a string where a number is required
- **THEN** the error names the parameter, the expected type and the received type

### Requirement: Search works without an embedding provider

`Search` SHALL fall back to lexical matching over the derived index — name,
description and parameter names — when no embedding provider is configured, and
SHALL report which mode produced the results. Semantic search SHALL NOT be a
prerequisite for `Search` to function.

#### Scenario: A laptop with no API key can search
- **WHEN** the proxy runs with a tool store and no embedding provider configured
- **THEN** `Search` returns matching tools and no outbound network request is
  made in order to serve the query

#### Scenario: The mode is reported
- **WHEN** `Search` returns results
- **THEN** the response states whether they came from semantic or lexical
  matching

### Requirement: Add accepts all supported tool sources

`Add` SHALL accept a JavaScript, Lua, Bash or OpenAPI-operation tool definition,
and an MCP server reference, and SHALL persist each as an artifact in the tool
store. An `Add` of an OpenAPI source SHALL store one artifact per selected
operation rather than one artifact per document.

#### Scenario: A script tool round-trips
- **WHEN** a JavaScript tool is added and the proxy is restarted
- **THEN** the tool is present, its source is byte-identical to what was
  supplied, and it executes

#### Scenario: One OpenAPI operation becomes one tool
- **WHEN** an OpenAPI document with twelve operations is added selecting one
- **THEN** exactly one artifact is stored, and `Search` returns exactly one tool
  for it

#### Scenario: An invalid definition is rejected before anything is written
- **WHEN** `Add` is called with a definition whose input schema is not valid JSON
  Schema
- **THEN** the call fails with an error naming the problem and no artifact is
  written to the store

### Requirement: Adding is not publishing

`Add` SHALL write only to the store the proxy reads from. Publishing to a
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
- **WHEN** `Add` is called with a Bash tool on a proxy that has not enabled the
  bash source
- **THEN** the call fails with an error stating that the source is disabled, and
  no artifact is written

#### Scenario: Enabling is deliberate and documented
- **WHEN** a developer reads the configuration reference for the bash source
- **THEN** it states that a Bash tool runs with the proxy's filesystem, network,
  environment and credentials, and that anyone able to call `Add` on such a proxy
  can execute arbitrary commands in it

#### Scenario: Sandboxed runtimes are unaffected
- **WHEN** the bash and stdio sources are disabled
- **THEN** JavaScript, Lua and OpenAPI tools can still be added and executed

### Requirement: Declared tools take precedence over stored tools

Store-added tools SHALL carry their own tool prefix, defaulting to `scratch`.
Where a stored tool's fully-qualified name nonetheless collides with a
configuration- or CRD-declared tool, the declared tool SHALL win: the stored tool
is shadowed, the collision is logged, and `Search` marks it as shadowed. `Add` of
a name that would be shadowed SHALL fail rather than write an uncallable
artifact.

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
- **WHEN** `Add` is called with a name that would be shadowed by a declared tool
- **THEN** the call fails with an error naming the declared tool that wins, and
  no artifact is written
