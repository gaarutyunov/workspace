## Context

gopgql is a single Go module whose core — `sdl`, `schema`, `generator`,
`migrate`, `compiler`, `shape` — has **no database dependency** and compiles to
WASM (SPEC.md §4.1). A query today is: `compiler.CompileQuery` → SQL + ordered
bind parameters → execute with `pgx` → `shape.Rows` into the nested response.
That last chain is written out by hand in every integration suite; SPEC.md
already reserves an `exec` package for it.

Every milestone proves itself against a real `postgres:19beta2` container driven
by godog (SPEC.md §10, §7). The issue asks for the MCP server to be tested the
same way, with a real client and a real server.

`blurrah/mcp-graphql` is the reference point: it exposes `introspect-schema` and
`query-graphql` over a remote GraphQL endpoint. gopgql's situation differs in two
ways — there is no GraphQL server, only a compiler plus a database; and the SDL
is the source of truth, so introspection can read the document rather than
issuing an introspection query.

## Goals / Non-Goals

**Goals**

- An agent can discover what is queryable without reading the whole schema.
- An agent can run a GraphQL query and get the same nested JSON the library
  produces, with the same compile-time guarantees (depth limit, bind parameters,
  no interpolation).
- The server is read-only by construction, not by convention.
- The execution chain stops being copy-pasted: one `exec` package, used by the
  MCP server and by the integration suites.

**Non-Goals**

- Migrations or any DDL through MCP. The issue is explicit; the server exposes no
  such tool.
- Mutations. The compiler only emits `SELECT`; there is nothing to expose.
- Multi-tenant serving: one SDL and one DSN per process.
- HTTP/SSE transport, schema hot-reload, and a resource surface — stdio and two
  tools first.

## Decisions

### D1: Two tools, `schema` and `query` — the issue's shape, not a wider one

An agent's loop is *what can I ask → ask it*. `blurrah/mcp-graphql` proves two
tools are enough, and extra tools cost context in every conversation. Anything
diagnostic (the emitted SQL) rides as an optional field on `query`'s result
rather than as a third tool.

### D2: Progressive introspection, because a real schema does not fit

`schema` takes an optional `type` argument and an optional `format`:

- **no arguments** → an overview: the queryable root fields, each type's name,
  its scalar field count and its relationship count. Tens of lines for a schema
  that would be thousands.
- **`type: "Person"`** → that type's fields with their GraphQL types, which are
  scalars (and the column they map to, since `@column(name:)` may rename it) and
  which are relationships, with the target type and direction.
- **`format: "sdl"`** → the raw SDL document, for when an agent really does want
  everything.

- *Alternative — always return the full SDL:* simplest, and what a naive port of
  mcp-graphql would do. Rejected: the issue calls it out, and a large schema
  would consume the agent's context before it asked anything.
- *Alternative — a separate `describe-type` tool:* same information, one more
  tool in every prompt. Rejected under D1.

### D3: `exec` is a package, not code inside `mcp`

`exec.Query(ctx, pool, compiled)` runs the SQL with its bind parameters, scans
rows into `[]map[string]any` by column name, and returns `shape.Rows(...)`. It is
what four integration suites already do inline, and it is the seam where a future
SQL-side shaping strategy (M8) can be selected. `mcp` then holds only tool
definitions and their handlers.

### D4: Read-only by construction, and one more belt

The compiler cannot emit anything but a `SELECT` over `GRAPH_TABLE`, so the tool
surface has no write path. On top of that the server opens its pool with
`default_transaction_read_only=on` in the connection config, so even a bug that
someday emitted a write would be refused by the database. Documented as the
reason a read-only database role is *recommended but not required*.

### D5: Errors are answers, not failures

A compile error (unknown field, depth exceeded, malformed operation) is returned
as a tool error carrying the compiler's message — those messages already name the
offending field and the ceiling, which is exactly what an agent needs to correct
itself. A database error is returned with its SQLSTATE. Neither kills the server.

### D6: stdio transport, configured by flag or environment

`gopgql-mcp --sdl schema.graphql --dsn postgres://…`, with `GOPGQL_SDL` and
`GOPGQL_DSN` as the environment equivalents (DSN preferred there — an agent's MCP
config is not a good place for a password). stdio is how agents launch MCP
servers locally; an HTTP transport can be added later without changing the tools.

### D7: The test suite drives a real client against a real server

A godog suite starts the container, applies a generated migration, seeds rows,
starts the MCP server **in-process over an in-memory transport pair** with a real
client from the SDK, and asserts on tool results — plus one scenario that spawns
the actual built binary over stdio, so the wiring in `cmd/gopgql-mcp` is covered
too. Mocking the client would test nothing the SDK doesn't already test.

## Risks / Trade-offs

- **[SDK maturity]** — `modelcontextprotocol/go-sdk` is young; its API may move.
  Mitigation: the tool handlers depend on gopgql types and take plain arguments,
  so an SDK change touches only the thin registration layer.
- **[Schema overview drifting from the real schema]** — the overview is derived
  from the same `sdl.Document` the compiler uses, never a hand-written summary,
  so it cannot describe something the compiler would reject.
- **[An agent sending expensive queries]** — the depth ceiling bounds traversal,
  but nothing bounds result size. A `limit`-style guard is not in this change;
  noted as a follow-up rather than smuggled in.
- **[Connection lifetime]** — one pool for the process; if the database goes
  away the tools fail until it returns. Acceptable for a locally launched server.

## Migration Plan

Purely additive: new packages, a new binary, a new test suite. No existing API
changes, and the WASM build is untouched because nothing in the core imports
`exec` or `mcp`.

## Open Questions

- Should `query` return the emitted SQL by default, or only when asked? Leaning
  *only when asked* (`includeSql: true`) so the common result stays small.
- Is `format: "sdl"` on the `schema` tool worth the risk of an agent pulling a
  huge document into context, or should the full document be a separate,
  harder-to-reach affordance?
- Should the server expose the schema as an MCP **resource** as well as a tool?
  Resources are the more idiomatic home for "here is a document", but tool-only
  keeps the first version smaller.
