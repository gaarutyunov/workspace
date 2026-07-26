## 1. `exec` — the execution helper SPEC.md §4.1 reserves

- [ ] 1.1 Add `exec/exec.go`: `Query(ctx, pool *pgxpool.Pool, cq *compiler.Compiled) (map[string]any, error)` — run the SQL with its ordered bind parameters, scan rows into `[]map[string]any` keyed by output column, and return `shape.Rows(cq.Projection, rows)`.
- [ ] 1.2 Add `Rows(ctx, pool, sql, args…)` for the flat form, so a caller that wants raw rows (or a future SQL-side shaper) does not go through the projection.
- [ ] 1.3 Unit-test the scanning against a fake row source; the real path is covered by the integration suite.

## 2. `mcp` — tool definitions and handlers

- [ ] 2.1 Add the `modelcontextprotocol/go-sdk` dependency and `mcp/server.go`: `New(doc *sdl.Document, sdlSource string, pool *pgxpool.Pool, opts…) *Server` registering both tools.
- [ ] 2.2 Add `mcp/introspection.go`: build a **standard GraphQL introspection result** from `*sdl.Document` — `__schema` (`queryType`, `types`, and the directives it declares) and `__type(name:)`, with `__Type`/`__Field`/`__InputValue` shaped per the GraphQL specification, including the `ofType` wrapper chain for non-null and list types. Answer `__typename` on any mapped type. Introspection is served from the document and never touches the database.
- [ ] 2.3 Implement the **introspect** tool over 2.2: no arguments → the `__schema` overview (root fields + type names, field definitions omitted); `type: "<Name>"` → that type's `__type` detail; `full: true` → the complete introspection result; `format: "sdl"` → the verbatim document. An unknown type name resolves to null, per the specification.
- [ ] 2.4 Implement the **query** tool: arguments `query`, optional `variables` (object), optional `format` (`"json"` default | `"markdown"`). Compile, execute through `exec`, return the response. Introspection meta-fields are answered from 2.2 without hitting the database. **No SQL in the result** and no argument that would return it.
- [ ] 2.5 Implement markdown rendering for `format: "markdown"`: columns from the selected scalar fields, one row per record, empty result → header only. **Reject before execution** when the operation selects a relationship, with an error naming the nesting field and saying JSON is required for nested results.
- [ ] 2.6 Map failures to tool errors carrying the underlying message: compile errors (unknown field, `*compiler.DepthExceededError` with its ceiling, missing variable) and database errors with their SQLSTATE. No failure terminates the server.
- [ ] 2.7 Declare input schemas and descriptions for both tools so a client can call them without guessing. **Both descriptions state how to introspect** — the meta-fields available, how to narrow to one type, and (on `query`) an introspection query the agent can send verbatim.

## 3. `cmd/gopgql-mcp` — the binary

- [ ] 3.1 Flags `--sdl` and `--dsn`, with `GOPGQL_SDL` / `GOPGQL_DSN` as environment fallbacks; flags win.
- [ ] 3.2 Parse and validate the SDL before connecting; exit non-zero with the parse error rather than serving a half-loaded schema.
- [ ] 3.3 Open the pool with `default_transaction_read_only=on` in the connection config, and ping it at startup; exit non-zero if the database is unreachable (design D4).
- [ ] 3.4 Serve MCP over stdio; shut the pool down cleanly on signal.

## 4. Integration suite (`test/mcp`)

- [ ] 4.1 Boot `postgres:19beta2`, generate and apply the migration for the suite's SDL, seed rows — the existing suite pattern.
- [ ] 4.2 Start the server in-process against an in-memory transport pair and connect a **real** SDK client; assert `tools/list` returns both tools with input schemas.
- [ ] 4.3 Scenarios for introspection: send the **introspection query a real GraphQL client sends** (the full `IntrospectionQuery`) and assert the result is well-formed, including the `ofType` chain for a non-null list field; `__type(name:)` on a mapped type lists its fields; `__type` on an unknown name is null; `__typename` resolves on a selected object; an introspection-only query issues no statement. Plus the `introspect` tool's four modes (default overview, `type:`, `full:`, `format: "sdl"`).
- [ ] 4.4 Scenarios for the query tool: a scalar query returns shaped rows; a traversal nests without duplicating parents; a variable is bound (assert the *executed* statement carries a placeholder rather than the value — captured through the pool, since the tool no longer returns SQL); the result carries no SQL; an unknown field and a too-deep selection both error without reaching the database; a database error is reported and the server still answers the next call.
- [ ] 4.4a Scenarios for `format`: markdown on a flat query returns a table whose columns are the selected fields; an empty flat result returns a header with no rows; markdown on a nested query errors naming the nesting field **and sends no statement**; the same nested query in JSON succeeds.
- [ ] 4.4b A scenario asserting `tools/list` descriptions contain the introspection instructions — an agent with only the tool list can reach a valid data query.
- [ ] 4.5 One scenario spawning the **built binary** over stdio, so `cmd/gopgql-mcp`'s wiring is covered rather than only the library.
- [ ] 4.6 A scenario proving the connection is read-only: an attempted write on the server's pool is refused by the database.

## 5. Docs, CI and verification

- [ ] 5.1 README: a "Connect an AI agent (MCP)" section — building the binary, the two tools (`introspect` and `query`), the flags/environment, and a `claude mcp add gopgql -- gopgql-mcp --sdl … --dsn …` example.
- [ ] 5.2 SPEC.md §4.1: add `exec` (now implemented) and `cmd/gopgql-mcp` to the package table.
- [ ] 5.3 CI: the new suite runs with the other integration suites; the new binary builds in the build job.
- [ ] 5.4 Run `go build ./...`, `go vet ./...`, the full `go test ./...` against containers, `golangci-lint run ./...`, and `govulncheck ./...`; all green.
