## Why

gopgql#47 records six requirements AgentIQ places on gopgql, stated as
requirements *on gopgql* rather than as AgentIQ implementation details:
"They belong in gopgql's own spec increment." This is that increment.
`agentiq/SPEC.md` §3.2 lists four of them as **blocking**:

> **gopgql** must ship before M1:
>
> 1. **`@function` mutation directive.** Maps a GraphQL mutation field to a
>    PL/pgSQL function call with typed argument mapping. Required because
>    `dbos.enqueue_workflow` and `dbos.send_message` are the command surface.
> 1. **Tx-scoped execution.** Generated client operations must accept a
>    caller-supplied transaction handle so they run inside `RunAsTransaction`.
> 1. **Read-only exposure of an externally-owned schema.** gopgql must generate
>    the property-graph definition and read model over `dbos.*` without emitting
>    DDL for those tables.
> 1. **Rename hints.** `dbos.streams.offset` is a reserved word.

"AgentIQ M1 cannot ship until items 1–5 are in a tagged release," so a
**tagged release** — not a merged branch — is what finishes this change.

### The tension this change has to resolve first

gopgql says it is read-only, in four places, one of them added last week:

| Where | What it says |
|---|---|
| `SPEC.md` §1.1 | "**Not a mutation engine.** SQL/PGQ property graphs are read-only views; `gopgql` compiles queries only." |
| `SPEC.md` §2.2 | "**Read-only.** A property graph is a view-like object; no mutation through it." |
| `compiler/compiler.go:220` | `"compiler: only query operations are supported (SQL/PGQ graphs are read-only)"` |
| `mcp/introspection.go:186` | `"mutationType": constant(nil)`, asserted by `mcp/introspection_test.go` |
| `mcp/query.go:70` | `"gopgql/mcp: only query operations are supported (the mapped graph is read-only)"` |
| `SPEC.md` §8.6 | "§2 is a hard constraint, not an omission … **gopgql has no write path to expose, so the playground exposes the database's.**" |

Item 1 asks for a **mutation** directive. This change does not paper over that.
It separates two claims that the text above runs together (design D1):

- **"No mutation through the graph" is a fact about PostgreSQL**, not a gopgql
  policy. PG19 cannot write through `GRAPH_TABLE`. `@function` compiles to
  `SELECT dbos.enqueue_workflow(…)` — an ordinary function call over ordinary
  tables, with no graph name, no `MATCH` and no `GRAPH_TABLE` in it. §2.2
  survives **verbatim and untouched**.
- **"Not a mutation engine" is a gopgql policy**, and it is **narrowed by
  name**. gopgql still derives no writes from `@node` types — no generated
  `createPerson`/`updatePerson`/`deletePerson`, which is what "mutation engine"
  means in the Neo4j-GraphQL and PostGraphile sense. It gains the ability to
  *call* a function the SDL explicitly names and the database already owns.

Three statements do become false and are **overturned explicitly**, not
reinterpreted: the `compiler.CompileQuery` refusal, §1.1's non-goal as worded,
and §8.6's "gopgql has no write path to expose". Each is rewritten in this
change. The MCP server's `mutationType: nil` is **kept** — deliberately, for a
new reason, which its doc comment must now state (design D3).

### What the issue does not say, and this change had to find

- **Item 4 is already done.** `internal/pgident`'s reserved-word list already
  contains `offset`, and `@column(name:)` has shipped since M6. `dbos.streams.offset`
  needs a regression scenario, not a feature.
- **Item 3 needs schema qualification, which nothing in gopgql has.**
  `schema.Table` has a `Name` and no schema; every identifier resolves through
  `search_path` (`conform/reflect.go:134`). `dbos.*` cannot be addressed at all
  today.
- **Item 3 needs a vertex identity gopgql has not got.** `dbos.operation_outputs`
  has no `id uuid`, and gopgql cannot add one to a table it must not touch.
  `SPEC.md` §5 says `@key(fields:)` is "a natural key **alongside** the
  surrogate `id`, not a replacement for it", and §9 records making it the
  identity as an open decision that "would be a milestone of its own". Item 3
  cannot land without resolving it for the read path (design D9).
- **Item 2 is not a signature change.** `agentiq/SPEC.md` §5 and §11 require
  gopgql to generate `generated/client/` — "All SQL. All pgx usage. Generated.
  `Tx` interface, typed query/mutation methods." gopgql has **no client
  generator**, no milestone for one, and `cmd/gopgql`'s `compile` "is not
  implemented yet" (`SPEC.md` §4.1). `exec.Querier` already accepts a `pgx.Tx`;
  the generator it must be reached through does not exist (design D11).
- **Two generator invariants refuse item 3's shape before PostgreSQL sees it.**
  `generator.go:562`/`:568` (§5.3 invariant 4) refuses a table appearing as both
  a vertex table and an edge table — exactly `dbos.operation_outputs`; `:554`
  (invariant 2) demands an index on every edge's destination key, which gopgql
  may not create on a table it does not own.
- **The CLI cannot express `generate client`.** `cmd/gopgql/main.go:170–216`
  uses one shared `flag.NewFlagSet` and `switch command`, and Go's `flag` stops
  at the first non-flag argument, so the two-word form parses zero flags
  (design D13).
- **`agentiq/SPEC.md` §7.3 is written in a directive vocabulary that is not
  gopgql's** — `@table(name:, schema:)`, `@vertex(key:)`, `@edge(from:, to:, label:)`.
  gopgql has `@node`, `@relationship`, `@column` and `@key`. gopgql will not
  grow a second spelling; AgentIQ restates its SDL. AgentIQ's SDL also declares
  `workflow_uuid` as `String` in §7.1 and `ID!` in §7.3 — `text` and `uuid` for
  one property name in one graph, which `validateLabelAlignment` and PostgreSQL
  both reject (design D10, "Changes AgentIQ must make").

## What Changes

- **A `@function(schema:, name:, returns:)` directive on mutation fields**, and
  mutation operations become compilable. Arguments map to function parameters
  **by name** using PostgreSQL's named notation, so ordering is not positional.
  An argument the **operation document** does not pass is absent from the call,
  so the function's own `DEFAULT` applies and gopgql never invents a value.
  Omission is a property of the document and not of a request, because a
  generated client bakes the SQL as a `const` — and **`NULL` is not `DEFAULT`**,
  which is the one trap here that no compiler can catch (design D4).
- **Scalar returns, and void returns declared rather than sniffed.** A
  scalar-returning function is read as one row of one column; `returns: VOID`
  executes as a statement and yields `true` on success. Declaring it is what
  stops a successful void call returning `false`, since `Boolean!` is otherwise
  ambiguous and gopgql has no database at compile time. Set-returning,
  output-parameter, variadic and polymorphic functions are rejected (design D5).
- **A typed error carrying the SQLSTATE** — `*exec.FunctionError`, wrapping
  `*pgconn.PgError`, so a consumer branches on a code rather than parsing
  English. gopgql produces no GraphQL error envelope and this change does not
  add one; item 1's "surface as GraphQL errors" is met by carrying the SQLSTATE
  as data the consumer maps (design D6 — a narrowing AgentIQ must be told about).
- **A caller-supplied execution handle** with `Query` *and* `Exec`, which
  `*pgxpool.Pool`, `*pgx.Conn` and `pgx.Tx` all satisfy. **`exec.OpenReadOnly`
  is unchanged and remains the only pool gopgql ever opens**: a `@function`
  call is executable *only* through a handle the caller supplies. That is what
  keeps items 1 and 2 one decision instead of two, and it is why gopgql still
  never opens a writable connection (design D2).
- **`@readonly` on a type**: gopgql emits the property-graph definition and the
  read model for it, and **no `CREATE TABLE`, no `ALTER TABLE`, no `DROP`, ever**.
  It is the per-type grain of the per-directory `--no-tables` that `SPEC.md`
  §3.0 already defines; the two compose (design D7).
- **Schema qualification** — `@node(schema:)` and `@relationship(schema:)`.
  Absent, nothing changes and identifiers resolve through `search_path` as they
  do today (design D8).
- **A declared natural key becomes the vertex identity, for `@readonly` types.**
  The compiler's three `id` sites (`compiler.go:344`, `:453`, `:586`) and
  `shape`'s parent dedup become the type's key columns. This resolves `SPEC.md`
  §9's second open decision **for the read path only**; *generated* edge tables
  keep referencing `id`, because a `@readonly` type gets no generated edge table.
  It is more than a widening: `Selection.KeyColumn` is exported and its change
  moves `cmd/wasm`'s API version, the isomorphism guard is a predicate that must
  become NULL-safe, `shape.keyString`'s `%v` formatting must stop colliding, and
  all implementors of an interface must agree on identity (design D9).
- **Relationships over tables gopgql does not own** — `@relationship(table:, sourceKey:, destKey:)`
  names an existing table and the **lists** of columns to use as `SOURCE KEY` /
  `DESTINATION KEY`, which is how `dbos.operation_outputs` becomes both a vertex
  table and an edge table. **Two `SPEC.md` §5.3 invariants are narrowed by name**
  — invariant 4 (`generator.go:562`/`:568`) currently refuses a table appearing
  as both, and invariant 2 (`:554`) demands an index gopgql may not create on a
  table it does not own (design D10).
- **A type's management cannot change.** Removing `@readonly` from a type would
  make the fold reconstruct its table as absent and emit `CREATE TABLE` for a
  table that already exists — a migration that reads correctly and fails at
  apply. Both directions are refused at generate time (design D14).
- **A generated typed Go client.** `gopgql generate client` reads the SDL plus
  a directory of named GraphQL operation documents, compiles each **at generate
  time** through the existing pure compiler, and emits one method per operation
  with the SQL as a `const` and the projection as a package-level `var`. Results
  are assigned field by field by generated code, never decoded by reflection,
  which also keeps the client independent of gopgql#10. Every method takes the
  handle as its second parameter (design D11).
- **The CLI grows a two-word subcommand, and does not grow Cobra.**
  `cmd/gopgql/main.go:170–216` builds one shared `flag.NewFlagSet` for every
  subcommand, so `gopgql generate client --sdl x` parses **zero** flags today —
  Go's `flag` stops at the first non-flag argument. `run()` is restructured into
  one flag set per subcommand, preserving every flag spelling, its `GOPGQL_*`
  fallback and its flag-wins-over-env precedence. Adopting Cobra is a separate
  change with its own justification (design D13).
- **Determinism proven upstream, not just downstream.** Generating twice from
  one input produces byte-identical output; generation succeeds with no
  reachable database. Asserted in gopgql's own CI rather than discovered in
  AgentIQ's (design D12).
- **A tagged release.** `agentiq/SPEC.md` §3.2 blocks on a tag, so the change is
  not done at merge.

## Capabilities

### New Capabilities

- `gopgql-function-mutations`: the `@function` directive, mutation-operation
  compilation, named-argument mapping, return mapping, and the narrowed non-goal.
- `gopgql-caller-supplied-handle`: execution against a handle the caller owns,
  the read-only pool that is left alone, and the SQLSTATE-carrying error.
- `gopgql-unmanaged-schemas`: `@readonly`, schema qualification, and what a
  generation emits for a table gopgql does not own.
- `gopgql-external-identity`: a declared natural key as vertex identity, and
  relationships over existing tables.
- `gopgql-generated-go-client`: the typed Go client — its inputs, its shape,
  and what is baked at generate time.
- `gopgql-generation-determinism`: byte-identical regeneration, no timestamps
  or hostnames, no database at generate time.

### Modified Capabilities

<!-- The gopgql specs (M1-M9) predate OpenSpec and are not in openspec/specs/,
     so there are no existing capability specs to amend. M7 (gopgql#9) and M8
     (gopgql#10) recorded the same note. SPEC.md §1.1, §2.2, §3.0, §4.1, §5,
     §7, §8.5, §8.6 and §9 are the project's own reference and are amended by
     this change; each amendment is a named task. -->

## Impact

- **`sdl`**: `@function` (with a `FunctionReturn` enum) and `@readonly` in the
  prelude; `schema:` on `@node` and `@relationship`; `sourceKey:`/`destKey:` on
  `@relationship`; `@column` widened to `ARGUMENT_DEFINITION`; a mutation-field
  model alongside the type model; validation that a mutation root field carries
  `@function`, that a `@readonly` type carries `@key(fields:)`, and that an
  interface's implementors agree on identity. Still no database dependency.
- **`compiler`**: `CompileMutation` returning a new `*CompiledCall`;
  `CompileQuery`'s operation-kind refusal rewritten; GraphQL field-argument
  defaults applied for the first time (`parser.ParseQuery` never validated);
  an unset *nullable* variable binding `NULL` where `:518` errors today; the
  three `id` sites parameterised by identity columns; `Selection.KeyColumn` →
  `KeyColumns` (exported, source-breaking); a NULL-safe isomorphism guard.
  Still pure and WASM-safe.
- **`shape`**: parent dedup keyed by a level's identity tuple, with a
  collision-safe encoding replacing `keyString`'s `fmt.Sprintf("%v", v)`.
- **`schema`**: `Table` and the graph elements gain a schema qualifier and an
  `Unmanaged` flag; identity becomes a column slice; `EdgeTable`'s `SourceKey`,
  `SourceRef`, `DestKey` and `DestRef` widen from `string` to `[]string`.
- **`generator`**: schema-qualified identifiers; graph-only emission for
  unmanaged types; existing-table edge elements; §5.3 invariants 2 and 4
  narrowed.
- **`migrate`**: an unmanaged table is never diffed, altered or dropped; a
  change of management is refused; the fold parser reads schema-qualified names
  back.
- **`exec`**: the handle interface (`Query` + `Exec`), `Call`, `*FunctionError`.
  `OpenReadOnly`'s behaviour is untouched; its doc comment is corrected.
- **`conform`**: reflection joins `pg_namespace` when a schema is declared;
  unmanaged elements are still compared (they are in the graph), their tables
  still are not (they never were — `SPEC.md` §7 → M7).
- **`mcp`**: `mutationType` stays `nil` and its test is untouched; the package
  doc, `queryDescription` (**text a language model reads**) and one error
  message are reworded, because their stated reason becomes false even though
  their behaviour does not (design D3).
- **`cmd/wasm` / `docs/src/main.js`**: `apiVersion` and `REQUIRED_API_VERSION`
  bumped together, since `Selection`'s shape changes and `TestAPIVersionsAgree`
  asserts they match.
- **`generator/client`** (new) and **`cmd/gopgql`**: a `generate client`
  subcommand, and `run()` restructured into per-subcommand flag sets.
- **`test/m10`…`test/m14`** (new): one godog package per milestone, each against
  a real `postgres:19beta2`.
- **Backwards compatibility**: additive **for generated output**, breaking for
  one exported Go type. An SDL with no `@function`, no `@readonly` and no
  `schema:` produces the same SQL and the same migrations as before — asserted
  against the existing generator and compiler golden files, unchanged. Two
  deliberate behaviour changes: a mutation operation stops being refused for an
  SDL that declares one, and an unset *nullable* variable binds `NULL` where it
  errors today. `compiler.Selection.KeyColumn` → `KeyColumns` is a **source-
  breaking** API change for anything importing `compiler` or `shape`, and moves
  the WASM playground's API version with it.
- **Merge order**: gopgql#10 (M8) is open and `needs:review` and rewrites
  `shape` substantially. The identity work (design D9, M13) touches the same
  code; it lands after #10 or rebases onto it. M14 does **not** depend on #10 —
  the generated client assigns results rather than going through `shape.Decode`.
