## 1. `exec` — the execution helper SPEC.md §4.1 reserves

- [ ] 1.1 Add `exec/exec.go`: `Query(ctx, pool *pgxpool.Pool, cq *compiler.Compiled) (map[string]any, error)` — run the SQL with its ordered bind parameters, scan rows into `[]map[string]any` keyed by output column, and return `shape.Rows(cq.Projection, rows)`.
- [ ] 1.2 Add `Rows(ctx, pool, sql, args…)` for the flat form, so a caller that wants raw rows (or a future SQL-side shaper) does not go through the projection.
- [ ] 1.3 Unit-test the scanning against a fake row source; the real path is covered by the integration suite.

## 2. `mcp` — tool definitions and handlers

- [ ] 2.1 Add the `modelcontextprotocol/go-sdk` dependency and `mcp/server.go`: `New(doc *sdl.Document, sdlSource string, pool *pgxpool.Pool, opts…) *Server` registering both tools.
- [ ] 2.2 Implement the **schema** tool: no arguments → overview (root fields; per type: name, scalar-field count, relationship count); `type: "<Name>"` → that type's fields with GraphQL type, mapped column (including an `@column(name:)` rename), and for relationships the target type and direction; `format: "sdl"` → the verbatim document. Unknown type → an error listing the available types.
- [ ] 2.3 Implement the **query** tool: arguments `query`, optional `variables` (object), optional `includeSql` (bool). Compile, execute through `exec`, return the nested response; with `includeSql` also return the statement.
- [ ] 2.4 Map failures to tool errors carrying the underlying message: compile errors (unknown field, `*compiler.DepthExceededError` with its ceiling, missing variable) and database errors with their SQLSTATE. No failure terminates the server.
- [ ] 2.5 Declare input schemas and descriptions for both tools so a client can call them without guessing.

## 3. `cmd/gopgql-mcp` — the binary

- [ ] 3.1 Flags `--sdl` and `--dsn`, with `GOPGQL_SDL` / `GOPGQL_DSN` as environment fallbacks; flags win.
- [ ] 3.2 Parse and validate the SDL before connecting; exit non-zero with the parse error rather than serving a half-loaded schema.
- [ ] 3.3 Open the pool with `default_transaction_read_only=on` in the connection config, and ping it at startup; exit non-zero if the database is unreachable (design D4).
- [ ] 3.4 Serve MCP over stdio; shut the pool down cleanly on signal.

## 4. Integration suite (`test/mcp`)

- [ ] 4.1 Boot `postgres:19beta2`, generate and apply the migration for the suite's SDL, seed rows — the existing suite pattern.
- [ ] 4.2 Start the server in-process against an in-memory transport pair and connect a **real** SDK client; assert `tools/list` returns both tools with input schemas.
- [ ] 4.3 Scenarios for the schema tool: the overview names the root fields and omits field definitions; a type drill-down lists fields, relationships and a renamed column; an unknown type errors usefully; the full-document form returns the SDL verbatim.
- [ ] 4.4 Scenarios for the query tool: a scalar query returns shaped rows; a traversal nests without duplicating parents; a variable is bound (assert the returned SQL carries a placeholder, not the value); an unknown field and a too-deep selection both error without reaching the database; a database error is reported and the server still answers the next call.
- [ ] 4.5 One scenario spawning the **built binary** over stdio, so `cmd/gopgql-mcp`'s wiring is covered rather than only the library.
- [ ] 4.6 A scenario proving the connection is read-only: an attempted write on the server's pool is refused by the database.

## 5. Docs, CI and verification

- [ ] 5.1 README: a "Connect an AI agent (MCP)" section — building the binary, the two tools, the flags/environment, and a `claude mcp add gopgql -- gopgql-mcp --sdl … --dsn …` example.
- [ ] 5.2 SPEC.md §4.1: add `exec` (now implemented) and `cmd/gopgql-mcp` to the package table.
- [ ] 5.3 CI: the new suite runs with the other integration suites; the new binary builds in the build job.
- [ ] 5.4 Run `go build ./...`, `go vet ./...`, the full `go test ./...` against containers, `golangci-lint run ./...`, and `govulncheck ./...`; all green.
