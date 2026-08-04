Milestone-ordered. Each milestone ends with a **gate**: godog scenarios that
execute real SQL against a real `postgres:19beta2` container and assert on
returned data (`SPEC.md` §7). Golden-file SQL assertions are an inner-loop check
only and never satisfy a gate.

Line references are to `origin/main` at `060922e`.

## 0. Before anything — the spec amendments

Sequenced first because it is what the owner is approving. If D1 is not
accepted, nothing below should be written.

- [ ] 0.1 `SPEC.md` §1.1: replace the "Not a mutation engine" non-goal with the narrowed wording (design D1) — gopgql derives no writes, generates no create/update/delete from a `@node` type, infers no input type, and calls only a function the SDL names.
- [ ] 0.2 `SPEC.md` §2.2: **unchanged**. State in the PR description that "no mutation through it" is untouched and why: a `@function` call contains no graph name, no `MATCH` and no `GRAPH_TABLE`, where `compiler.render`/`graphTable` emit nothing else.
- [ ] 0.3 `SPEC.md` §8.6: correct "gopgql has no write path to expose, so the playground exposes the database's." The Data pane's rationale stands — the *graph* has no write path — but the sentence as written becomes false.
- [ ] 0.4 `SPEC.md` §5: add `@function(schema:, name:, returns:)`, `@readonly`, `schema:`, `sourceKey:`/`destKey:` and `@column` on `ARGUMENT_DEFINITION`, each with the semantics paragraph the M7 directives got. Include the `NULL`-is-not-`DEFAULT` trap (design D4) — it is the one thing here that cannot be caught by a compiler.
- [ ] 0.5 `SPEC.md` §5.3: **invariant 4** narrowed — distinct graph elements may share a table when at most one is a vertex element (design D10). **Invariant 2** narrowed to generated edge tables; an unmanaged edge's destination index belongs to the schema's owner.
- [ ] 0.6 `SPEC.md` §7: add M10–M14 with their gates, including the note that M12's gate deliberately uses a fixture carrying an `id` and does not yet demonstrate the `dbos.*` case. §9 open decision 2 marked **resolved for the read path over unmanaged tables**, still open for managed ones.
- [ ] 0.7 `SPEC.md` §4.1: `exec`'s row gains the call path; a `generator/client` row; `cmd/gopgql`'s row gains `generate client`.
- [ ] 0.8 Every other site stating a reason this change falsifies (design D1 item 4): `mcp/server.go:11–14` (package doc), `mcp/server.go:122` (`queryDescription` — **text a language model reads and acts on**), `mcp/query.go:70`, `exec/exec.go:70` (`OpenReadOnly`'s doc: "there is no write path to begin with"), `mcp/introspection_test.go:105`, `test/seed/seed_test.go:289`, `README.md:41–42`. Behaviour unchanged in every case; only the stated reason moves.

## 1. M10 — a handle the caller owns

- [ ] 1.1 `exec.Handle`: `Query(ctx, sql, args…) (pgx.Rows, error)` **and** `Exec(ctx, sql, args…) (pgconn.CommandTag, error)`. `Exec` has a caller from 2.14 (the void path); if that decision changes, `Handle` collapses back into `Querier` rather than carrying a dead method.
- [ ] 1.2 Compile-time `var _ Handle = (*pgxpool.Pool)(nil)` / `(*pgx.Conn)(nil)` / `(pgx.Tx)(nil)` assertions, so a pgx upgrade that changes a signature fails the build rather than a test.
- [ ] 1.3 `exec.Querier` stays and `exec.Query` keeps taking it: a read needs no `Exec`, and a smaller interface asks less of a caller. `Handle` satisfies `Querier`.
- [ ] 1.4 `exec.OpenReadOnly`'s **behaviour** is not touched and no `OpenReadWrite` is added (design D2). Its **doc comment** is corrected per 0.8 — freezing a comment that has become false is the mistake D3 exists to avoid.
- [ ] 1.5 Package doc: gopgql opens one pool and it is read-only; anything that writes runs through a handle the caller owns.

### Gate — M10

- [ ] 1.6 `test/m10`: a query compiled by gopgql, executed through a caller's `pgx.Tx`, returns rows the same transaction inserted and has not committed. This is the exactly-once property `agentiq/SPEC.md` §3.2 item 2 needs, and a pool cannot fake it.
- [ ] 1.7 The same query through a pool from `OpenReadOnly` returns the same rows — the read path is unaffected.
- [ ] 1.8 A write attempted on an `OpenReadOnly` pool fails with SQLSTATE `25006`.

## 2. M11 — `@function` mutations

### 2a. `sdl`

- [ ] 2.1 Prelude: `enum FunctionReturn { SCALAR VOID }` and `directive @function(schema: String!, name: String!, returns: FunctionReturn = SCALAR) on FIELD_DEFINITION`; `@column` widened to `FIELD_DEFINITION | ARGUMENT_DEFINITION`.
- [ ] 2.2 A `Mutation` type is read into the mapping model: one entry per field, its `@function` target and return kind, and its arguments with declared parameter names, GraphQL types, nullability and any GraphQL default.
- [ ] 2.3 A mutation field **without** `@function` is a parse-time error naming the field. No default target, no inference.
- [ ] 2.4 `@function` on anything but a `Mutation` field is a parse-time error.
- [ ] 2.5 An argument whose GraphQL name is not a valid unquoted lower-snake-case identifier and carries no `@column(name:)` is a parse-time error naming the argument — rather than a call that fails at run time with `42883` and no hint that a naming convention caused it (design D4).
- [ ] 2.6 A declared `returns: VOID` field whose GraphQL type is not `Boolean!` is a parse-time error. A set-returning, output-parameter, variadic or polymorphic declaration is refused with a message naming what is unsupported (design D5).

### 2b. `compiler`

- [ ] 2.7 `CompileMutation(op string, vars map[string]any) (*CompiledCall, error)`. `*CompiledCall` carries `SQL`, ordered `Args` and the return kind; it is **not** `*Compiled` — a call has no projection and no shaping, and an `if kind ==` in `exec` would be the cost of pretending otherwise.
- [ ] 2.8 Emit named notation: `SELECT <schema>.<name>(<param> => $n, …)`, identifiers through `pgident.Quote`, values as bind parameters only (`SPEC.md` §6.2: "Values are bind parameters. Never interpolated." / "Identifiers are never parameters.").
- [ ] 2.9 **Omission is a property of the operation document** (design D4): an argument the document does not pass is absent from the emitted list. gopgql emits no `DEFAULT` keyword and no placeholder. This is forced by the generated client baking SQL as a `const` (D11) — a per-request decision would need 2ⁿ statements or run-time compilation.
- [ ] 2.10 **Apply GraphQL field-argument defaults explicitly.** `CompileQuery` calls `parser.ParseQuery` only and never validates, so `queue: String = "agent"` currently reaches nothing. Applied, it is bound as a value and the function's own default for that parameter is never reached. A compiler unit test asserts this, because it is the trap in the issue's own example.
- [ ] 2.11 An unset **nullable** variable binds `NULL` instead of failing. `compiler/compiler.go:518` (`"no value supplied for variable $%s"`) keeps failing for a **non-null** variable. Without this every optional argument is unusable; with it, `NULL` and `DEFAULT` are different things and 0.4 says so.
- [ ] 2.12 `CompileQuery`'s refusal message is rewritten: still `query`-only, no longer citing the graph's read-only-ness, and a `mutation` reaching it is directed to `CompileMutation` by name (design D1).
- [ ] 2.13 Exactly one root field per mutation operation, matching the query rule.
- [ ] 2.14 `compiler` stays pure and WASM-safe. Assert with the existing `GOOS=js GOARCH=wasm` build.

### 2c. `exec`

- [ ] 2.15 `exec.Call(ctx, h Handle, cc *compiler.CompiledCall) (any, error)`. `SCALAR` → `Query`, exactly one row of one column, mapped back through `SPEC.md` §5.1's scalar table; anything else is a clear error, not a panic. **`VOID` → `Exec`**, and a successful command tag yields `true` (design D5). This is what gives `Handle.Exec` its caller.
- [ ] 2.16 No type-OID sniffing and no run-time inspection of the function: the declaration decides, so compilation stays pure and a successful void call can never return `false`.
- [ ] 2.17 `*exec.FunctionError`: `SQLSTATE`, `Message`, `Detail`, `Hint`, `Constraint`, plus the schema and function called; wraps `*pgconn.PgError` and satisfies `errors.As`. In `exec`, not `compiler` — `pgconn` is a database dependency and `SPEC.md` §4.1 forbids one on the WASM side (design D6).
- [ ] 2.18 Its doc comment states what item 1 actually gets: gopgql produces no GraphQL error envelope (`SPEC.md` §1.1, §8.6); the SQLSTATE is data for the consumer to map into `extensions`.

### 2d. `mcp`

- [ ] 2.19 `mcp/introspection.go:186`'s `"mutationType": constant(nil)` and its test are **unchanged**. The reasons in 0.8 change: the MCP server holds an `OpenReadOnly` pool and has no caller-supplied handle, not that mutations cannot exist (design D3).
- [ ] 2.20 A test asserting that an SDL declaring a `Mutation` type still introspects to a null `mutationType` — the omission is deliberate and should fail loudly if it stops being.

### Gate — M11

- [ ] 2.21 `test/m11`, against a real container, with hand-written PL/pgSQL functions in the fixture: a scalar-returning function called through a caller's transaction, its value asserted.
- [ ] 2.22 A function declared `returns: VOID` with GraphQL type `Boolean!` returns `true`, and its side effect is visible in the same transaction.
- [ ] 2.23 An argument absent from the **operation document** takes the function's declared `DEFAULT` — asserted by the *value the function wrote*, not by the emitted SQL.
- [ ] 2.24 An argument passed as an unset **nullable** variable arrives as `NULL`, and the scenario asserts that this differs from the `DEFAULT` case for a parameter whose default is not `NULL`. This is the D4 trap, proven rather than described.
- [ ] 2.25 Arguments supplied in a different order than the function declares produce the same result: named notation, not positional.
- [ ] 2.26 `RAISE EXCEPTION … USING ERRCODE = 'P0001'` surfaces as `*FunctionError` with `SQLSTATE == "P0001"` and the message intact, reachable through `errors.As`.
- [ ] 2.27 A call attempted on an `OpenReadOnly` pool fails with `*FunctionError` carrying `25006` — the D2 belt, with an error that explains itself.

## 3. M12 — tables and schemas gopgql does not own

**The M12 fixture table carries an `id` column.** `compiler/compiler.go:344`
hardcodes `b.addColumn(alias, "id", keyCol)` until 4.4 lands, so a query over a
table without one cannot pass a gate before M13. M12 therefore proves DDL
suppression and schema qualification; M13 proves the `dbos.*` case.

- [ ] 3.1 `sdl`: `directive @readonly on OBJECT`; `schema: String` on `@node` and `@relationship`.
- [ ] 3.2 `@readonly`'s doc comment states what it constrains — DDL emission, **not** query access (design D7, Risks). It is AgentIQ's word and it reads as though it meant the other thing.
- [ ] 3.3 `schema`: `Table` and the graph elements carry a schema qualifier and an `Unmanaged` flag.
- [ ] 3.4 `generator`: a qualified identifier is `Quote(schema) + "." + Quote(table)`; unqualified emission is **byte-identical to today** — assert against the existing generator golden files, unchanged.
- [ ] 3.5 `generator`: an unmanaged type contributes graph elements and **no** table DDL, index DDL or constraint DDL.
- [ ] 3.6 `migrate`: an unmanaged table never appears in a table diff — never created, altered or dropped. A column absent from the SDL on such a type produces nothing (`SPEC.md` §3.0's "tables half off" semantics, per type).
- [ ] 3.7 `migrate`: removing an unmanaged type from the SDL removes it from the graph and emits no table DDL.
- [ ] 3.8 **Changing a type's management is refused at generate time** (design D14), naming the type — in both directions. The fold sees no table for an unmanaged type, so dropping `@readonly` would emit `CREATE TABLE` for a table that already exists: a migration that passes review and fails at apply. Adoption has no delta representation and is a separate change.
- [ ] 3.9 `internal/ddl`: the fold parser reads a schema-qualified name back. Emitting a qualification the fold cannot re-read would corrupt the *next* delta — the failure `SPEC.md` §7 → M7 called out for `RENAME`.
- [ ] 3.10 `conform`: reflection joins `pg_namespace` when a schema is declared. Unmanaged elements are still compared — they are in the graph; their tables still are not, which was already true.
- [ ] 3.11 gopgql emits no `CREATE SCHEMA` (design D8).
- [ ] 3.12 `--no-tables` and its history check are **untouched**. `@readonly` is the finer grain; both keep their meaning (design D7).

### Gate — M12

- [ ] 3.13 `test/m12`: a second schema and its tables applied by a hand-written init script (standing in for `dbos migrate`); gopgql generates a graph-only migration over them; `goose up`; a compiled query returns the seeded rows. The fixture table carries an `id` (see the note above).
- [ ] 3.14 The generated migration contains no `CREATE TABLE`, `ALTER TABLE`, `CREATE INDEX` or `DROP` for any unmanaged type — asserted over the emitted files.
- [ ] 3.15 A mixed SDL — one managed type, one unmanaged — emits table DDL for the managed one only, and graph DDL for both, in one generation.
- [ ] 3.16 Dropping a column from an unmanaged type's SDL emits nothing; dropping one from a managed type still emits the `ALTER TABLE … DROP COLUMN` M2 asserts.
- [ ] 3.17 **Item 4**: an unmanaged type with `seq: Int! @column(name: "offset")` generates, applies and queries correctly against a real column named `offset`. `internal/pgident` already lists `offset` as reserved; this is the regression scenario that keeps it quoted. It needs no `@readonly` — it is asserted here because this is where the `dbos.streams` shape appears.
- [ ] 3.18 A property graph spanning two schemas is created and queried on `postgres:19beta2`. If PG19beta2 refuses it, that is a design-changing finding and the milestone stops rather than routing around it (Risks).
- [ ] 3.19 A scenario asserting `validateLabelAlignment` still rejects one property name at two types across two schemas — the failure the AgentIQ SDL currently walks into (design, AgentIQ list item 6).

## 4. M13 — identity without a surrogate key

Lands **after** gopgql#10 (M8) merges, or rebases onto it: #10 rewrites `shape`
and this touches the same grouping code (design D9, Risks).

- [ ] 4.1 `sdl`: an unmanaged type **must** declare `@key(fields:)`. Without a surrogate `id` there is no other identity; absence is a parse-time error naming the type.
- [ ] 4.2 `sdl`: every implementor of an interface must share identity columns; a schema document where they do not is a parse-time error naming both. `sdl.Target.Tables` is a set at an interface position, and two of the three `id` sites walk it (design D9).
- [ ] 4.3 `schema`: a type's identity is a **slice** of columns — length one and named `id` for every type that exists today.
- [ ] 4.4 `compiler`: the three `id` sites (`compiler.go:344`, `:453`, `:586`) take the level's identity columns. A single-column identity emits exactly what it emits today — assert against the existing compiler golden files, unchanged.
- [ ] 4.5 `compiler.Selection.KeyColumn string` → `KeyColumns []string`. It is **exported and consumed by `shape`, `playground` and `cmd/wasm`**: a source-breaking change, not an internal one.
- [ ] 4.6 `cmd/wasm`: bump `apiVersion` (currently `7`) and `docs/src/main.js`'s `REQUIRED_API_VERSION` together — `TestAPIVersionsAgree` asserts they match, and the doc comment requires a bump "whenever an exported function's … result shape change[s]".
- [ ] 4.7 `compiler.isomorphismGuards` (`:586`) is a **predicate** and its multi-column form must be **NULL-safe**: `(a,b) <> (c,d)` yields NULL when a component is NULL, and a `@key` column is only `UNIQUE`, not `NOT NULL`, so a null key column would silently drop rows. Emit a disjunction of `IS DISTINCT FROM` per component.
- [ ] 4.8 `shape`: parent dedup groups by the level's identity **tuple**. `keyString` is `fmt.Sprintf("%v", v)` (`shape.go:69`); a tuple formatted the same way collides for values containing spaces or brackets, and a dedup collision is **silent**. Use a delimiter-safe encoding (length-prefixed, or `%q` per component) and unit-test the collision case directly.
- [ ] 4.9 The one-column case is byte-identical to today's behaviour, in both the compiler and the shaper.
- [ ] 4.10 A **managed** type is unchanged: `id uuid PRIMARY KEY` stays, `@key` stays a `UNIQUE` constraint alongside it (`generator.go:388–390`), and `SPEC.md` §9's open decision stays open for managed tables (design D9).
- [ ] 4.11 **Regression check, not new work:** `generator.go:483` already emits `KEY (…)` from `vt.NaturalKey.Columns`, and `validateInvariants` already binds those columns into `PROPERTIES` (§5.3 invariant 1). Assert it still holds for an unmanaged element; do not re-implement it.

### Edges over existing tables

- [ ] 4.12 `sdl`: `sourceKey: [String!]` / `destKey: [String!]` on `@relationship`. Present ⇒ `table:` is **required** and names an existing table, gopgql generates no edge table and emits only the graph element. Absent ⇒ today's behaviour exactly (design D10).
- [ ] 4.13 `schema.EdgeTable`'s `SourceKey`, `SourceRef`, `DestKey`, `DestRef` widen from `string` to `[]string`: `SOURCE KEY (…) REFERENCES tbl (…)` must reference the destination vertex's key, which 4.3 makes multi-column.
- [ ] 4.14 `generator`: **invariant 4** (`generator.go:562`/`:568`, "duplicate table name … in graph") narrowed so distinct elements may share a table when at most one is a vertex element. This is the `dbos.operation_outputs` shape, and today it fails generation before PostgreSQL sees it.
- [ ] 4.15 `generator`: **invariant 2** (`generator.go:554`, `hasDestIndex`) narrowed to generated edge tables. gopgql cannot emit `CREATE INDEX` on a table it does not own (3.5), and nothing replaces the check for unmanaged edges — the index is the schema owner's, and a warning gopgql cannot act on is noise.
- [ ] 4.16 A relationship touching an unmanaged type **without** `sourceKey:`/`destKey:` is a parse-time error naming the field. Emitting a graph whose edge is silently missing, so traversals return nothing, is a silent fallback and `SPEC.md` §10 forbids one.
- [ ] 4.17 An unmanaged type never gets a generated edge table, so generated edge tables keep referencing `id` and the write path stays out of scope.

### Gate — M13

- [ ] 4.18 `test/m13`: a vertex over an externally-owned table with a two-column key and **no `id` column** — the `dbos.operation_outputs` shape — matched by `MATCH` and correctly deduplicated across a one-to-many fan-out. Dedup is what a wrong identity breaks silently, so it is asserted on returned data.
- [ ] 4.19 A scenario with a **NULL** in one key column, asserting rows are not silently dropped by the isomorphism guard (4.7).
- [ ] 4.20 A scenario whose key values contain a space and a bracket, asserting no dedup collision (4.8).
- [ ] 4.21 A traversal over an edge declared on an existing table with `sourceKey:`/`destKey:` returns the correct rows.
- [ ] 4.22 One table serving as **both** a vertex table and an edge table in the same graph, matched from both roles. If PG19beta2 refuses it, the milestone stops and the design is revisited (Risks).
- [ ] 4.23 Every M1–M9 scenario still passes with no change to its expectations: the identity widening is a no-op for a type with a surrogate `id`.

## 5. M14 — the generated client, and determinism

- [ ] 5.1 `generator/client`: SDL + a directory of operation documents → a Go package. Every operation is compiled **at generate time** through the existing pure compiler (design D11).
- [ ] 5.2 The input contract, stated precisely because two implementors would otherwise diverge: `*.graphql` files in the directory, **no subdirectory traversal**, files read in sorted path order; any number of **named** operations per file; an anonymous operation is an error; the operation name is the exported method name; a duplicate operation name across the directory is an error naming both files.
- [ ] 5.3 Per query operation: an input struct from the operation's variables, a result type from its selection set, the SQL as a `const`, the `compiler.Projection` as a package-level `var`, and a method `(ctx, h exec.Handle, in In) (Out, error)`.
- [ ] 5.4 **Results are assigned field by field from `exec.Query`'s `map[string]any`, generated — not decoded by reflection.** The generator knows the selection set exactly, so nothing at run time inspects a struct tag or a type. This also keeps M14 **independent of gopgql#10**, whose `shape.Decode` serves the SQL-side strategy.
- [ ] 5.5 Per mutation operation: the same shape over `exec.Call`, returning the mapped scalar or `bool`.
- [ ] 5.6 **`exec.Handle` is the second parameter of every generated method**, query and mutation alike. That is `agentiq/SPEC.md` §3.2 item 2, in the place it asked for it. The generated client opens no connection and holds no pool.
- [ ] 5.7 `cmd/gopgql`: restructure `run()` into **one flag set per subcommand** (design D13). `cmd/gopgql/main.go:170–216` builds one shared `flag.NewFlagSet` and dispatches with `switch command`, so `gopgql generate client --sdl x` parses **zero** flags today — Go's `flag` stops at the first non-flag argument. `--sdl`/`--dsn`/`--dir` keep their spellings, their `GOPGQL_*` fallbacks and their flag-wins-over-env precedence, registered by a shared helper.
- [ ] 5.8 `generate client` takes `--operations`, `--out` and `--package`; they exist on that subcommand only and never appear on `migrate` or `conform`. No Cobra is added (design D13); if a config *file* is ever added it is koanf, never Viper (`.claude/rules/go-cli-koanf.md`).
- [ ] 5.9 `--out` resolving to the same path as `--operations` or `--sdl` is refused before anything is written.
- [ ] 5.10 A `// Code generated by gopgql. DO NOT EDIT.` header on every emitted file, matching Go's convention so tooling and reviewers both recognise it (`agentiq/SPEC.md` §5: hand-editing is forbidden and CI-detected).
- [ ] 5.11 Compile-time errors stay at generate time: an unknown root field, a depth violation or an unmapped scalar fails `gopgql generate client`, never a request.
- [ ] 5.12 `generated/gql/` is **not** produced. `agentiq/SPEC.md` §11 lists it and no document says what it contains (design D11, Open Questions).

### Determinism (item 6)

- [ ] 5.13 Generate twice from one input into two directories; assert byte-identical trees. This is the check that catches map iteration reaching output.
- [ ] 5.14 Assert no generated artifact contains a timestamp, hostname, username or absolute path — over `generate` and `generate client` both.
- [ ] 5.15 Assert both succeed with no `GOPGQL_DSN` and no reachable database (`agentiq/SPEC.md` §11 rule 3; `SPEC.md` §6.1).
- [ ] 5.16 Migration filenames stay sequence-numbered `NNNN_slug.sql`, never timestamped (`SPEC.md` §3.0) — asserted, not assumed.

### Gate — M14

- [ ] 5.17 `test/m14`: a generated client compiled and run against a real container, executing M11's mutation and M12/M13's queries through a caller's `pgx.Tx`, asserting the same data the hand-written suites assert.
- [ ] 5.18 A generated mutation method's failure surfaces `*exec.FunctionError` with the SQLSTATE intact through the generated layer.
- [ ] 5.19 The determinism tests run in CI as ordinary tests, needing no container.

## 6. Docs, playground and CI

- [ ] 6.1 `README.md`: the `@function` narrowing in D1's terms — what gopgql now does and what it still does not — plus `@readonly`, `schema:` and `generate client`. `README.md:41–42`'s read-only claim is corrected here (0.8).
- [ ] 6.2 `docs/`: directive reference entries for `@function`, `@readonly`, `schema:`, `sourceKey:`/`destKey:` and `@column` on arguments, generated from the godog fixtures as §7 → M9 requires so the docs cannot drift.
- [ ] 6.3 Playground: `@function` compilation is pure and WASM-safe, so the emitted call **can** be shown. Showing it is optional; **executing** it is not — the playground's PGlite database is the reader's, and D2's rule has no meaning in a tab where the reader owns everything. If a tab is added it shows generated SQL only, and §8.6's Data pane rationale is updated to match §1.1's new wording. The `apiVersion` bump is 4.6's, not this task's.
- [ ] 6.4 `.github/workflows/ci.yml`: the five new godog packages. Each shares one container across its scenarios; if the 25-minute cap is reached, milestone suites split across jobs rather than being thinned.
- [ ] 6.5 Full CI green — `go build ./...`, `go vet ./...`, the `GOOS=js GOARCH=wasm` build, the whole godog suite against containers, `golangci-lint run ./...`, `govulncheck ./...`, the docs and playground build, and `goreleaser check`.

## 7. Release — the change is not done at merge

`agentiq/SPEC.md` §3.2: "AgentIQ M1 cannot ship until items 1–5 are in a tagged
release." A merged branch unblocks nothing.

- [ ] 7.1 Confirm items 1–4 are on `main` and item 5 (the PGlite PG19 fork) is already delivered and pinned (`SPEC.md` §8.6) — recorded in the issue "only so the dependency is visible", not this change's work.
- [ ] 7.2 CI green on `main` — the release gate is ordering, not a re-run (`SPEC.md` §8.5).
- [ ] 7.3 Tag `v0.2.0` (§8.5's trigger is `v[0-9]+.[0-9]+.[0-9]+*`). `v1.0.0` would claim a stability §9's remaining open decisions do not support.
- [ ] 7.4 Verify the release published both binaries for all four platforms and the multi-arch GHCR image, and that the floating tags moved.
- [ ] 7.5 Report the tag on gopgql#47 and on the two AgentIQ issues it blocks (`gaarutyunov/agentiq#2`, `#3`), together with the eight `agentiq/SPEC.md` edits the design lists — AgentIQ's current SDL does not compile against the delivered directives, and a tag alone does not unblock it.
