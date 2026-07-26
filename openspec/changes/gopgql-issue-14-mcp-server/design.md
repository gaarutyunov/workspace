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
`query-graphql` over a remote GraphQL endpoint. gopgql's situation differs in one
way — there is no GraphQL server, only a compiler plus a database. The discovery
surface is nevertheless **standard GraphQL introspection** (`__schema`, `__type`,
`__typename`): gopgql builds the introspection result from the loaded SDL instead
of forwarding an introspection query to an upstream server, but what an agent
sees is the introspection response the GraphQL specification defines, not a
gopgql-specific dialect.

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

### D1: Two tools, `introspect` and `query` — the issue's shape, not a wider one

An agent's loop is *what can I ask → ask it*. `blurrah/mcp-graphql` proves two
tools are enough, and extra tools cost context in every conversation. The SQL is
not part of either tool's result: the server connects to Postgres, executes, and
returns the data (D2a).

Both tool **descriptions** carry the introspection instructions — the meta-fields
available, and an introspection query the agent can send verbatim. An agent that
lists the tools therefore knows how to discover the schema without any out-of-band
documentation, which is the point of preferring introspection to a bespoke
overview.

### D2: Standard GraphQL introspection, not a bespoke schema report

`__schema`, `__type(name:)` and `__typename` are answered from the loaded SDL, and
`introspect` is a convenience wrapper that issues one of those queries for the
caller:

- **no arguments** → the `__schema` overview: queryable root fields and the type
  names, with those types' field definitions omitted. Tens of lines for a schema
  that would be thousands.
- **`type: "Person"`** → that type's `__type` detail: its fields and their type
  references, so an agent can see which fields lead to another type.
- **`full: true`** → the complete introspection result; **`format: "sdl"`** → the
  SDL document, for when an agent really does want everything.

Progressive reading is not a departure from introspection — it *is* introspection,
which is a query like any other and returns exactly what was selected.

- *Alternative — a gopgql-specific schema report* (the earlier draft: overview with
  scalar/relationship counts and mapped column names). Rejected: every GraphQL
  client and agent already knows how to walk an introspection result, and a custom
  shape has to be learned. It also leaked the mapped column name, which is an
  implementation detail an agent cannot use — it queries fields, not columns.
- *Alternative — always return the full SDL:* simplest, and what a naive port of
  mcp-graphql would do. Rejected: the issue calls it out, and a large schema
  would consume the agent's context before it asked anything.
- *Alternative — a separate `describe-type` tool:* same information, one more
  tool in every prompt. Rejected under D1.

### D2a: `query` returns data; `format` chooses JSON or a markdown table

The result is the JSON response by default. `format: "markdown"` renders a table
instead — easier for a human reading the agent's transcript, and cheaper in
tokens.

A table cannot express nesting, so markdown is **refused, before execution**, for
an operation that selects a relationship, with an error naming the nesting field.
The alternative — silently falling back to JSON — was rejected: an agent that
asked for a table and got JSON has no signal that its request was reinterpreted.
Flat result sets (scalars only) are the only ones a table represents faithfully.

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
- **[Introspection drifting from the real schema]** — the introspection result is
  derived from the same `sdl.Document` the compiler uses, never a hand-written
  summary, so it cannot describe something the compiler would reject.
- **[Introspection completeness]** — building a spec-shaped introspection result
  by hand is more surface than a bespoke summary: `__Type`, `__Field`,
  `__InputValue`, `__EnumValue`, `__Directive` and the `ofType` wrapper chain for
  non-null/list types all have to be right, or clients that walk the result
  generically will break. Mitigation: assert against the introspection query that
  GraphQL clients actually send, not a hand-picked selection.
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

- Should the server expose the schema as an MCP **resource** as well as a tool?
  Resources are the more idiomatic home for "here is a document", but tool-only
  keeps the first version smaller.

## Resolved (owner, gaarutyunov/workspace#21)

- **Does `query` return the emitted SQL?** No. The server connects to Postgres,
  executes, and returns the JSON result; SQL is not part of the tool surface
  (D2a). The earlier `includeSql` argument is gone.
- **Discovery is standard GraphQL introspection**, not a gopgql-specific schema
  report, and the **tool descriptions must say how to introspect** (D1, D2).
- **`format` is a parameter of the `query` tool**: JSON or a markdown table, with
  the table refused for nested selections because it cannot represent them (D2a).
