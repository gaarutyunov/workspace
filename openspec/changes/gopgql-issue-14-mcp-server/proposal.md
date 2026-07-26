## Why

gopgql compiles GraphQL against a PostgreSQL 19 property graph, but the only way
to use it today is to write Go or open the WASM playground, which has no
database behind it. An AI agent that wants to *ask questions of the data* has
nothing to call.

An MCP server closes that gap: it wraps one SDL document and one database and
exposes the two things an agent actually needs — find out what can be asked, and
ask it (gaarutyunov/gopgql#14). The design follows `blurrah/mcp-graphql`'s two-tool
shape, and the discovery half is **standard GraphQL introspection** — the
`__schema` / `__type` meta-field surface every GraphQL client already knows how to
walk. Progressive reading falls out of that for free: introspection is a query, so
an agent asks for root fields first and drills into one type at a time.

## What Changes

- Add an **`exec` package** — the thin `pgx` execution helper SPEC.md §4.1
  already reserves: run a compiled query with its bind parameters, scan the flat
  rows, and shape them into the nested response. It is the only package besides
  the future CLI that touches a database, keeping `sdl`/`generator`/`migrate`/
  `compiler` WASM-clean.
- Add an **`mcp` package** exposing two tools over the official
  `modelcontextprotocol/go-sdk`:
  - **`introspect`** — runs a **standard GraphQL introspection query** against the
    loaded schema and returns its result. With no arguments it returns the root
    fields and the type names (the `__schema` shape, field definitions omitted);
    with a type name it returns that type's full `__type` detail. Its tool
    description tells the agent how to introspect — the meta-fields available and
    the introspection query to send through `query` for anything this tool does not
    surface directly.
  - **`query`** — takes a GraphQL operation and optional variables, compiles it,
    executes it against the connected database, and returns the JSON response.
    Introspection meta-fields (`__schema`, `__type`, `__typename`) are answerable
    here too, so an agent that already speaks GraphQL needs no second tool. A
    `format` argument selects the return shape: `json` (default) or a `markdown`
    table for flat result sets.
- Add **`cmd/gopgql-mcp`** — the server binary: reads the SDL path and the
  database DSN from flags/environment and serves MCP over stdio.
- The server **never migrates and never writes**: it exposes no migration tool,
  and the compiler only ever emits `SELECT … FROM GRAPH_TABLE`.
- Add an **integration suite** that drives a real MCP client against the real
  server against a real `postgres:19beta2` container, in the same godog style as
  the milestone suites.

## Capabilities

### New Capabilities

- `mcp-schema-introspection`: standard GraphQL introspection over the loaded
  schema — the `__schema` / `__type` meta-fields, an overview an agent can afford
  to read, drill-down by type, and tool descriptions that teach the agent how to
  introspect.
- `mcp-query-execution`: the `query` tool — GraphQL in, JSON (or a markdown table)
  out, executed against PostgreSQL with bind parameters, with compile and database
  errors reported in a form an agent can act on.
- `mcp-server-runtime`: how the server is configured, what it connects to, and
  the guarantees it makes — read-only, no migrations, one SDL per process.

### Modified Capabilities

<!-- gopgql has no pre-existing OpenSpec specs; the milestones live in SPEC.md. -->

## Impact

- **New packages**: `exec` (pgx execution + shaping), `mcp` (tool definitions and
  handlers), `cmd/gopgql-mcp` (binary). No existing package changes shape.
- **New dependency**: `github.com/modelcontextprotocol/go-sdk`. `pgx` is already
  a dependency (tests use it); `exec` makes it a runtime one for the first time —
  which is why it is a separate package the WASM build never imports.
- **Tests**: a new `test/mcp` suite. It is the first suite that boots a server
  and a client rather than calling library functions, so it establishes that
  pattern for the repo.
- **Docs**: README section on running the server and wiring it into an agent
  (`claude mcp add …`), mirroring the existing MCP instructions style.
- **CI**: the new suite joins the existing integration job; the new binary joins
  the build matrix.
- **Not in scope**: migrations through MCP, mutations of any kind, multi-schema
  or multi-database servers, an HTTP/SSE transport, and schema hot-reload.
