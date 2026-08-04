## Context

Read at `060922e` (`origin/main`) and against `agentiq/SPEC.md` at `fe56fd0`.
These facts shape every decision below.

**gopgql refuses non-query operations in two places, with two different
reasons.** `compiler/compiler.go:220` refuses because "SQL/PGQ graphs are
read-only"; `mcp/query.go:70` refuses because "the mapped graph is read-only".
Both are true statements about a *graph*. Neither is a statement about calling a
function, which is what item 1 asks for. Four further sites give a reason that
this change makes false — `mcp/server.go:11–14` ("read-only by construction …
there is no migration or mutation tool"), `mcp/server.go:122`'s
`queryDescription`, which is handed **to a language model**, `exec/exec.go:70`
("so there is no write path to begin with"), and `README.md:41–42`.

**`SPEC.md` §8.6 restated the prohibition last week, in the strongest form it
has ever taken.** Explaining why the playground's Data pane is plain SQL:

> It is SQL and not a GraphQL mutation because §2 is a hard constraint, not an
> omission: a SQL/PGQ property graph is a read-only view, `compiler.CompileQuery`
> refuses any operation that is not a `query`, and the MCP server's introspection
> reports a null `mutationType`. **gopgql has no write path to expose, so the
> playground exposes the database's.**

The last sentence is a factual claim that this change makes false. It is not
reinterpretable; it is edited (D1).

**`exec` already accepts a caller-supplied handle for reads.** `exec.Querier`
is `Query(ctx, sql, args...) (pgx.Rows, error)` and nothing else, and its doc
comment says "`*pgxpool.Pool`, `*pgx.Conn` and `pgx.Tx` all satisfy it." Half of
item 2 is already true.

**gopgql opens exactly one pool, and it is read-only.** `exec.OpenReadOnly`
sets `default_transaction_read_only=on` on every session and documents itself as
"the second belt (`SPEC.md` §3, design D4)".

**The CLI is stdlib `flag`, not Cobra, and its dispatcher cannot express a
two-word subcommand.** `cmd/gopgql/main.go:170–216`: `command, rest := argv[0],
argv[1:]`, one shared `flag.NewFlagSet` for every subcommand, then `switch
command`. `go.mod` has no `spf13/cobra` (only `pflag`, indirect via goose).
Configuration is flags plus `GOPGQL_*` environment variables, flag winning.

**gopgql has no client generator.** `SPEC.md` §4.1: "`compile` is not
implemented yet." `agentiq/SPEC.md` §11 nonetheless lists gopgql as the
generator of `generated/client/` and `generated/gql/`, and §5 specifies
`generated/client` as "All SQL. All pgx usage. Generated. `Tx` interface, typed
query/mutation methods. Hand-editing is forbidden and detected by CI."

**Nothing is schema-qualified.** `schema.Table` carries a `Name`.
`conform/reflect.go:134` notes an unqualified name "resolves through the
session's `search_path`". `dbos.*` cannot be named.

**Every vertex has a surrogate `id uuid`, and exactly three places depend on
it** — `compiler/compiler.go:344` (`b.addColumn(alias, "id", keyCol)`), `:453`
(the fragment join key), and `:586` (`isomorphismGuards`, which emits
`vi."id" <> vj."id"`). `SPEC.md` §5 on `@key(fields:)`: "a **natural key
alongside the surrogate `id`, not a replacement for it** … The surrogate key is
load-bearing in the compiler (three projection sites) and in `shape`'s parent
dedup; making a natural key *the* identity is a different, larger change and is
recorded in §9." The DBOS tables AgentIQ must expose have no such column, and
`@readonly` forbids adding one.

**Four generator invariants stand in the way of mapping tables gopgql does not
own** (`generator/generator.go`):

- `:562`/`:568` — invariant 4 refuses a table name appearing as **both** a
  vertex table and an edge table.
- `:554` — invariant 2 refuses an edge with no index on its destination key.
- `schema.EdgeTable`'s `SourceKey`, `SourceRef`, `DestKey`, `DestRef` are single
  `string`s.
- `:594`/`:635` — `validateLabelAlignment` requires **one type per property name
  across the whole graph**.

**An unsupplied variable is a hard error today.** `compiler/compiler.go:518`:
`"compiler: no value supplied for variable $%s"`. And `CompileQuery` calls
`parser.ParseQuery` only — never a validator — so GraphQL's field-argument
defaults are **not** applied anywhere today.

**`internal/pgident` already quotes `offset`.** It is in the reserved list, and
`@column(name:)` shipped in M6. Item 4 is a scenario, not a feature.

## Goals / Non-Goals

**Goals:**

- Satisfy `agentiq/SPEC.md` §3.2 items 1–4 in a tagged release, with the
  prerequisites the issue does not name — schema qualification, vertex identity,
  four generator invariants, and the client generator — surfaced here rather
  than discovered during implementation.
- Keep the read-only claims that are *true* untouched, and rewrite every one
  that stops being true, by name.
- Keep gopgql from ever opening a writable connection.
- Prove every claim against a real `postgres:19beta2` container (`SPEC.md` §7).

**Non-Goals:**

- A mutation engine. gopgql derives no writes from `@node` types: no generated
  create/update/delete, no inferred input types (D1).
- Mutation through the property graph. PG19 cannot, and §2.2 is untouched.
- A GraphQL server or an error envelope (D6).
- Exposing mutations over MCP (D3).
- Set-returning, output-parameter, variadic or polymorphic functions (D5).
- Making a natural key the identity for tables gopgql *does* own (D9).
- Adopting AgentIQ's `@table`/`@vertex`/`@edge` spelling (D10).
- Migrating the CLI to Cobra (D13).
- Adopting an existing table into gopgql's management (D15).

## Decisions

### D1: `@function` narrows "not a mutation engine"; it leaves "no mutation through the graph" verbatim

The prohibitions collapse two different claims into one word.

**Claim A — a fact about PostgreSQL.** `SPEC.md` §2.2: "**Read-only.** A
property graph is a view-like object; no mutation through it." One of eight
"absolute" limitations of PG19's SQL/PGQ. Not gopgql's to overturn, and untouched
here. A `@function` mutation compiles to

```sql
SELECT dbos.enqueue_workflow(agent_digest => $1, user_id => $2, input => $3, queue => $4)
```

No graph name, no `MATCH`, no `GRAPH_TABLE`, no property. Compare what the
compiler emits today: `render`/`graphTable` produce `SELECT … FROM GRAPH_TABLE
(<graph> MATCH … COLUMNS (…))` and nothing else. Nothing mutates through the
graph, before or after.

**Claim B — a policy of gopgql's.** `SPEC.md` §1.1: "**Not a mutation engine.**
SQL/PGQ property graphs are read-only views; `gopgql` compiles queries only."
The first clause is the policy; the second is Claim A used as its justification.
The policy is **narrowed**, and the new wording says how far:

> **Not a mutation engine.** gopgql derives no writes: it generates no
> create/update/delete field from a `@node` type and infers no input type. A
> mutation exists only where the SDL declares one and names, with
> `@function(schema:, name:)`, a function the database already owns. gopgql
> compiles the call; it does not author the write.

`@function` is on the same footing as `@default` and `@check`, which `SPEC.md`
§5 already calls "a deliberate escape hatch … defensible only because whoever
writes the SDL already owns the schema." `@function` is defensible for the same
reason and no other.

**What is overturned, by name.** Each is edited, not reinterpreted:

1. `compiler/compiler.go:220` — `CompileQuery` keeps refusing anything that is
   not a `query`, but stops giving the graph's read-only-ness as the reason and
   directs a `mutation` to `CompileMutation`.
2. `SPEC.md` §1.1's non-goal, replaced with the wording above.
3. `SPEC.md` §8.6's "gopgql has no write path to expose, so the playground
   exposes the database's."
4. `mcp/server.go:11–14`'s package doc, `mcp/server.go:122`'s `queryDescription`
   — which is text a language model reads and acts on — `mcp/query.go:70`'s
   message, `exec/exec.go:70`'s `OpenReadOnly` doc, and `README.md:41–42`. Each
   states a *reason* that becomes false while its *behaviour* does not; D3's
   principle is that a stale reason is worse than none.

**Alternative rejected: keep the refusal; AgentIQ hand-writes resolvers.**
`agentiq/SPEC.md` §7.4 forbids it — "There are no hand-written resolvers" — and
§1.3's principle is no persistence or commands outside generated code. The
alternative is not a smaller change; it is a decision that AgentIQ M1 does not
ship.

**Alternative rejected: overturn Claim A and derive CRUD from `@node`.** PG19
cannot write through a property graph, so the writes would go to the underlying
tables — a second, structurally different code path, the same shape of thing
`SPEC.md` §3's rationale already rejected for `WITH RECURSIVE`. Nobody asked.

### D2: gopgql still never opens a writable connection

`exec.OpenReadOnly`'s **behaviour** is unchanged. It stays the only pool gopgql
opens; there is no `OpenReadWrite` and this change does not add one. (Its doc
comment does change — see D1 item 4.)

A `@function` call is therefore executable only through a handle the caller
owns. Running one against a pool from `OpenReadOnly` fails with SQLSTATE `25006`
(`read_only_sql_transaction`) — the belt working as designed — and
`*FunctionError` carries that code, so the failure reads as "this handle cannot
write" rather than as a mystery.

This is what makes items 1 and 2 a single decision. The caller must supply the
handle not only because DBOS's `RunAsTransaction` hands one over, but because
gopgql has nothing else to offer.

### D3: the MCP server keeps `mutationType: nil` — for a new reason, which it must state

`mcp/introspection.go:186` reports `"mutationType": constant(nil)` and
`mcp/introspection_test.go` asserts it. Both stay, and the MCP server exposes no
mutation even when its SDL declares one.

The reason changes, and a comment giving a reason that has become false is worse
than no comment. Today: "there are no mutations." From this change: **the MCP
server holds a pool from `OpenReadOnly` and has no caller-supplied handle to run
a call through** (D2), and an agent that can invoke `dbos.enqueue_workflow` is a
different authorization posture from one that can read. This is why
`queryDescription` matters more than an ordinary comment: a model reads it.

**No opt-in flag.** A `WithMutations(handle)` option would be one line and would
be the first place a write is reachable by a language model with no story about
who authorized it. That is an Open Question, not a flag added in advance.

### D4: arguments map by name; omission is decided by the operation document

**Named notation.** The call uses PostgreSQL's `param => value` form, so
argument order in the SDL, in the operation and in the function signature are
mutually independent.

**Parameter names are declared, never derived.** `@column(name:)` widens to
`ARGUMENT_DEFINITION`: `agentDigest: String! @column(name: "agent_digest")`.

*Alternative rejected: derive `agentDigest` → `agent_digest`.* gopgql cannot
verify either spelling without a database, so both are equally unchecked at
generate time — but a wrong *derived* name fails at call time with `42883
undefined_function` and no hint that a naming convention caused it, whereas a
wrong *declared* name is visible in the SDL diff. `SPEC.md` §5 already takes
this position for `@renamedFrom` ("a **hint, never an inference**"), and §9's
third open decision (table-name pluralisation) is the same question, unresolved
after nine milestones. Derivation can be added later over a hint; not the
reverse.

**Omission is a property of the operation document, not of the request.** This
is forced, and it is the correction the first draft of this design got wrong.
An argument is absent from the emitted call **iff the operation document does
not pass it**. gopgql emits no `DEFAULT` keyword and substitutes no value.

The reason it cannot be per-request: a generated client bakes each operation's
SQL as a `const` (D11), so the argument list is fixed before any request exists.
Making omission depend on which variables a request supplied would require one
SQL variant per subset of omittable arguments — 2ⁿ statements — or runtime
compilation, which is exactly what item 6 exists to avoid.

**Three consequences, each of which must be written down because each is a trap:**

1. **`NULL` is not `DEFAULT`.** An argument the document passes as a nullable
   variable is *always* sent; if the request supplies no value it is sent as
   `NULL`. For a parameter whose default is `NULL` these coincide; for any other
   parameter they do not. To reach the function's default, the operation
   document must not pass the argument at all — which usually means a second
   named operation.
2. **A GraphQL-declared default is bound as a value.** `queue: String = "agent"`
   means `"agent"` is sent and `enqueue_workflow`'s own default for `queue` is
   never reached. gopgql must **apply field-argument defaults explicitly**: it
   parses without validating today (`parser.ParseQuery` only), so those defaults
   reach nothing. An SDL author who wants the SQL default must not write a
   GraphQL one.
3. **An unsupplied variable stops being a hard error where the variable is
   nullable.** `compiler/compiler.go:518` currently errors for any unset
   variable. That stays for a non-null variable and becomes `NULL` for a
   nullable one — otherwise every optional argument is unusable.

### D5: scalar returns and void returns are declared, not sniffed

- **A scalar-returning function** is executed with `Query`, read as exactly one
  row of one column, and mapped through `SPEC.md` §5.1's scalar table in
  reverse. Anything else is a clear error, not a panic.
- **A void-returning function is declared** — `@function(schema:, name:, returns: VOID)`,
  an enum argument defaulting to `SCALAR`. It is executed with `Exec`, and a
  successful command tag yields `true` for the field's `Boolean!` type.

**Why declared and not inferred.** `Boolean!` is otherwise ambiguous: a
`RETURNS boolean` function returning `false` and a `RETURNS void` function are
indistinguishable from the SDL, and gopgql has no database at compile time. The
alternatives are sniffing the result column's type OID at run time — behaviour
that depends on the database, in a library whose compilation is pure — or
silently returning `false` for a successful void call, which is what an
implementor following "map through the scalar table" would build. A declared
enum costs one directive argument and removes the ambiguity entirely. It is also
what gives `Handle.Exec` its caller (D2).

- **Set-returning (`SETOF`, `RETURNS TABLE`), output-parameter, variadic and
  polymorphic functions are refused at compile time.** A function returning a set
  would have to flow through the projection and shaping machinery, which is built
  around `GRAPH_TABLE` output. Different feature, different design.

**gopgql cannot check any of this without a database and does not pretend to.**
The *declaration* is what it compiles against; a declaration that disagrees with
the function is PostgreSQL's error at call time, exactly as `@default(value:)`
and `@check(expr:)` already are at migration time (`SPEC.md` §5). The refusals
above are of things the SDL declares, not of things the database contains.

### D6: the SQLSTATE is carried as data, on a typed Go error

**gopgql cannot surface a GraphQL error, because it produces no GraphQL
response.** `SPEC.md` §1.1: "Not a GraphQL server." §8.6, on the playground:
the payload "is deliberately **not** wrapped in a GraphQL `{"data": …}`
envelope … an envelope it does not produce would be the one fabricated panel on
a page whose entire claim is that nothing is."

So item 1's requirement is met one level down, and **this is a narrowing AgentIQ
must be told about**: `*exec.FunctionError` carries `SQLSTATE`, `Message`,
`Detail`, `Hint`, `Constraint`, and the schema and function called, wrapping
`*pgconn.PgError` and reachable through `errors.As`. AgentIQ maps it into its own
GraphQL error `extensions`, which it must do anyway — it owns the server.

The type lives in **`exec`, not `compiler`**: `pgconn` is a database dependency
and `SPEC.md` §4.1 states that `sdl`, `schema`, `generator`, `migrate`,
`compiler` and `shape` "have **no database dependency** … nothing on the WASM
side may import them." This mirrors `conform`'s typed findings and
`*DepthExceededError`: "so a caller branches on a kind rather than parsing
English."

### D7: `@readonly` is the per-type grain of `--no-tables`

`SPEC.md` §3.0 already makes two things representable: "a property graph over
tables gopgql does not manage" and "an SDL that describes **part** of a
database". Its mechanism, `--no-tables`, scopes a whole **directory**.

`@readonly` scopes a **type**, and they compose:

- A generation over a mixed SDL emits table DDL for the managed types only, and
  graph DDL for every type.
- An unmanaged type is never in a table diff: never created, altered or dropped,
  and a column absent from the SDL says nothing — §3.0's "tables half off"
  semantics, per type.
- Removing an unmanaged type from the SDL removes it from the graph and touches
  no table.
- A directory needing both managed and unmanaged tables uses `@readonly`, not
  `--no-tables`. The flag and its history check are untouched.

`@readonly` says nothing about queries: such a type is queried like any other.
The name is AgentIQ's (`agentiq/SPEC.md` §7.3) and reads as though it meant
"read-only at query time", which it does not — the directive's doc comment must
say so.

### D8: schema qualification, absent by default

`@node(schema: String)` and `@relationship(schema: String)`. When declared,
every emitted identifier for that element is `pgident.Quote(schema) + "." +
pgident.Quote(table)`; when absent, emission is byte-identical to today and
resolves through `search_path`. No existing SDL changes shape.

`migrate`'s fold parser must read a qualified name back: the §3.0 fold is over
gopgql's own emitted SQL, so a qualification the parser cannot re-read would
corrupt the next delta — the failure `SPEC.md` §7 → M7 called out for `RENAME`.
`conform`'s reflection joins `pg_namespace` when a schema is declared.

gopgql emits no `CREATE SCHEMA`: a schema it does not own is not its to create.

### D9: a declared natural key is the vertex identity — for unmanaged types, on the read path

The largest and riskiest decision here, and the one the issue does not mention.

`dbos.operation_outputs` is keyed `(workflow_uuid, function_id)`;
`dbos.streams` is keyed `(workflow_uuid, key, offset)`. Neither has an
`id uuid`, and `@readonly` forbids adding one. But `SPEC.md` §5 is explicit that
`@key(fields:)` is a natural key "alongside the surrogate `id`, not a
replacement for it" — verified: `generator.go:483` emits `KEY (…)` from
`vt.NaturalKey.Columns` **and** `:388–390` emits a `UNIQUE` constraint, with
`id uuid PRIMARY KEY` unchanged — and §9 records the alternative as an open
decision that "would be a milestone of its own."

**Resolved here, narrowly:**

- An unmanaged type **must** declare `@key(fields:)`; absence is a parse-time
  error naming the type.
- For such a type the declared key **is** the identity: it fills the element's
  `KEY (...)` clause (already true — `generator.go:483`), it is what the compiler
  projects at that position, and it is what `shape` groups parents by.
- A **managed** type is unchanged. §9's open decision stays open for it.
- **Generated edge tables are untouched**: they keep `source_id`/`target_id`
  referencing `id`, because an unmanaged type never gets a generated edge table
  (D10). Edges *mapped onto existing tables* are a different thing and do carry
  multi-column keys (D10).

**Scope of the code change — larger than "widen a string to a slice":**

- The three `id` sites (`compiler.go:344`, `:453`, `:586`) take the level's
  identity columns, a slice of length one for every type that exists today.
- `compiler.Selection.KeyColumn string` becomes `KeyColumns []string`. It is
  **exported and consumed by `shape`, `playground` and `cmd/wasm`**, so this is a
  source-breaking API change, and `cmd/wasm`'s `apiVersion = 7` and
  `docs/src/main.js`'s `REQUIRED_API_VERSION` must move together —
  `TestAPIVersionsAgree` asserts they match.
- `isomorphismGuards` (`:586`) is a **predicate**, not a projection, and a
  multi-column form must be NULL-safe. `(a,b) <> (c,d)` yields NULL when a
  component is NULL, and a `@key` column is only `UNIQUE`, not `NOT NULL`, so a
  null key column would silently drop rows. The guard becomes a NULL-safe
  disjunction of `IS DISTINCT FROM` per component.
- `shape.keyString` is `fmt.Sprintf("%v", v)` (`shape.go:69`). A tuple formatted
  the same way collides for values containing spaces or brackets, and a dedup
  collision is **silent** — precisely the failure the M13 gate exists to catch.
  The composite encoding must be delimiter-safe.
- **An interface position has no single type.** `sdl.Target.Tables` is a set,
  and two of the three `id` sites walk it: `isomorphismGuards` emits a guard for
  every pair of positions whose table sets intersect, and `addPosition` does the
  same across fragments. So all implementors of an interface must share identity
  columns; a schema document where they do not is a parse-time error, naming
  both.

**Merge-order hazard.** gopgql#10 (M8) is open, `needs:review`, and rewrites
`shape` — adding `Decode`, `Encode` and a leaf normaliser, and changing how
levels are grouped. This lands **after** #10 merges, or rebases onto it.

### D10: relationships over tables gopgql does not own

`agentiq/SPEC.md` §7.3 declares relationships as foreign-key joins between
existing tables: `steps: [Step!]! @edge(from: "workflow_uuid", to: "workflow_uuid", label: "HAS_STEP")`.
gopgql's `@relationship` always means a generated edge table with
`source_id`/`target_id`. `dbos.operation_outputs` is both a row queried as a
`Step` and the join connecting a `Workflow` to it.

**`@relationship` gains `sourceKey: [String!]` and `destKey: [String!]`** — and
`schema:` per D8 — naming columns of an **existing** table. They are **lists**,
not single columns, because SQL/PGQ's `SOURCE KEY (…) REFERENCES tbl (…)` must
reference the destination vertex's key, and D9 makes that key multi-column.
`schema.EdgeTable`'s `SourceKey`, `SourceRef`, `DestKey` and `DestRef` widen
from `string` to `[]string` for the same reason.

When they are absent, everything behaves exactly as today and gopgql generates
the edge table. When present, `table:` is **required** and names an existing
table; gopgql generates no table and emits only the graph element.

**Three generator invariants must be amended, by name, or generation refuses
this before PostgreSQL ever sees it:**

- **`SPEC.md` §5.3 invariant 4** (`generator.go:562`/`:568`) refuses a table name
  appearing as both a vertex table and an edge table. That is exactly the
  `operation_outputs` shape. Narrowed to: *distinct* elements may share a table
  when at most one of them is a vertex element.
- **Invariant 2** (`generator.go:554`) refuses an edge with no index on its
  destination key. gopgql cannot emit `CREATE INDEX` on a table it does not own
  (D7). Narrowed to generated edge tables. Nothing replaces it for unmanaged
  edges: the index is the schema owner's, and inventing a warning gopgql cannot
  act on would be noise.
- **`validateLabelAlignment`** (`generator.go:594`, `:635`) requires one type per
  property name across the whole graph. Unchanged — it encodes a PostgreSQL rule
  — but it is now much easier to violate, because two schemas meet in one graph
  (see the AgentIQ list below).

**Alternative rejected: adopt `@edge(from:, to:, label:)`.** A second spelling
for a directive gopgql already has. `SPEC.md` §5 is a single directive
vocabulary. AgentIQ restates §7.3.

**A relationship touching an unmanaged type without key columns is a parse-time
error**, naming the field. The alternative — emitting a graph whose edge is
silently missing, so traversals return nothing — is a silent fallback, which
`SPEC.md` §10 forbids.

### D11: item 2 needs a generator, not a parameter

`agentiq/SPEC.md` §5: `generated/client` is "All SQL. All pgx usage. Generated.
`Tx` interface, typed query/mutation methods. Hand-editing is forbidden and
detected by CI." §11 names gopgql as its generator. gopgql has none, and
`exec.Querier` — which already accepts a `pgx.Tx` — is reached by hand-written
code today. Item 2 cannot be satisfied by widening an interface.

**Inputs.** The SDL, plus a directory of `*.graphql` operation documents. Any
number of **named** operations per file; an anonymous operation is an error. The
operation name is the exported method name; a duplicate name across the
directory is an error naming both files. Files are read in sorted path order and
no subdirectory is traversed — determinism (D12) depends on the order being
stated rather than being whatever the filesystem returned.

**Outputs, per operation:**

```go
const appendEventSQL = `SELECT …`
var appendEventProjection = compiler.Projection{ /* … */ }

func (c *Client) AppendEvent(ctx context.Context, h exec.Handle, in AppendEventInput) (AppendEventResult, error)
```

**Results are assigned field by field, not decoded by reflection.**
`exec.Query` returns `map[string]any` whose nested values are `[]any` of
`map[string]any`. The generator knows the selection set exactly, so it emits the
assignments; nothing at run time inspects a struct tag or a type. This also
keeps the generated client **independent of gopgql#10**, whose `shape.Decode` is
for the SQL-side strategy.

Three properties follow from compiling **at generate time**:

- **`exec.Handle` is the second parameter of every method**, query and mutation
  alike. That *is* item 2, in the place item 2 asked for it.
- **Determinism is structural** (D12): no run-time compilation, so no map
  iteration reaches output, and the SQL is a `const` in a reviewable diff.
- **Generation is hermetic**: the compiler already contacts no database
  (`SPEC.md` §6.1), satisfying `agentiq/SPEC.md` §11 rule 3 for free.

*Alternative rejected: a runtime client compiling each operation on call.* It
re-introduces the map-ordering exposure item 6 exists to close, costs a parse per
request, and moves every compile-time error to production.

**`generated/gql/` is not produced.** `agentiq/SPEC.md` §11 lists it as a gopgql
output and no document says what it contains. Open Question.

### D12: determinism is asserted upstream, not discovered downstream

Item 6 restates an existing expectation: `go generate ./... && git diff --exit-code`
runs in AgentIQ's CI. That check is downstream, and its failure mode is an
AgentIQ build going red for a gopgql bug. gopgql owes three ordinary tests:

- Generate twice from one input into two directories; assert byte-identical
  trees. This is what catches map iteration reaching output.
- Assert no artifact contains a timestamp, hostname, username or absolute path.
  Migration filenames are already `NNNN_slug.sql` — a sequence, not a timestamp
  (`SPEC.md` §3.0) — so this asserts a property the design already has.
- Assert both commands succeed with no `GOPGQL_DSN` and no reachable database.

### D13: the CLI grows a two-word subcommand; it does not grow Cobra

`cmd/gopgql/main.go:170–216` reads `command, rest := argv[0], argv[1:]`, builds
**one** `flag.NewFlagSet` shared by every subcommand, and dispatches with
`switch command`. Two consequences:

- `gopgql generate client --sdl x` parses **zero** flags today. Go's `flag`
  stops at the first non-flag argument, so `client` terminates parsing and the
  command falls into `generate` with an empty `--sdl`.
- The new flags (`--operations`, `--out`, `--package`) cannot join the shared
  set without also appearing on `migrate` and `conform`.

**`run()` is restructured into one flag set per subcommand**, with the shared
flags registered by a helper so `--sdl`/`--dsn`/`--dir` keep their spellings,
their `GOPGQL_*` fallbacks and their flag-wins-over-env precedence exactly.
Dispatch reads a second word only for `generate`.

**Cobra is not adopted here.** `AGENTS.md` makes Cobra the house standard for
*scaffolding a Go service*; gopgql is an existing library whose CLI is a thin
stdlib-`flag` front end, and `go.mod` has no Cobra. Adding a dependency and
rewriting three working subcommands is a change with its own justification and
its own risk, and bundling it inside a change that already spans five milestones
would make both harder to review. If it is ever adopted, configuration stays
flags plus environment — and if a config *file* is ever added it is koanf, never
Viper (`.claude/rules/go-cli-koanf.md`).

### D14: unmanaged means unmanaged — a table is never adopted

The fold reconstructs prior state from gopgql's own emitted SQL (`SPEC.md`
§3.0), and nothing is emitted for an unmanaged table. So if a type stops being
`@readonly`, the fold sees no table, the differ sees a new one, and the
generation emits `CREATE TABLE` for a table that already exists — a migration
that fails at apply, discovered in whatever environment applies it first.

**Removing `@readonly` from a type is refused at generate time**, naming the
type. Adopting an existing table into gopgql's management has no representation
as a delta and would need one deliberately (a baseline migration, a `@renamedFrom`-
style adoption hint) — a separate change. Refusing is the honest answer; the
alternative is a migration that looks fine in review and fails in production.

The reverse direction — *adding* `@readonly` to a type gopgql created — is the
same problem mirrored and is refused for the same reason.

## Milestones

`SPEC.md` §7 numbers milestones; M9 is the last shipped (M8 is gopgql#10, open).
This change is **M10–M14**, each ending in godog scenarios that execute real SQL
against a real `postgres:19beta2` container — never SQL-text assertions alone.

| | Milestone | Gate |
|---|---|---|
| M10 | Caller-supplied handle | A query runs inside a caller's `pgx.Tx` and sees that transaction's uncommitted rows; `OpenReadOnly` still refuses a write. |
| M11 | `@function` mutations | A real PL/pgSQL function is called and its scalar returned; a `VOID`-declared function yields `true` and its side effect is visible; an argument absent from the operation document takes the function's `DEFAULT`; `RAISE EXCEPTION … USING ERRCODE` surfaces as `*FunctionError` carrying that SQLSTATE. |
| M12 | Unmanaged tables and schemas | Externally applied DDL in a second schema + a graph-only migration → a query returns rows; no table DDL is emitted for a `@readonly` type; a column named `offset` round-trips. **The M12 fixture table carries an `id`**, so M12 proves DDL suppression and schema qualification and does *not* yet prove the `dbos.*` case. |
| M13 | Identity without a surrogate key | A vertex over a table with a two-column key and **no `id`** is matched and deduplicated correctly; a traversal runs over an edge mapped onto an existing table; one table serves as both vertex and edge. |
| M14 | Generated Go client and determinism | The generated client runs M11–M13's scenarios through a caller's transaction; regeneration is byte-identical; generation succeeds with no database. |

M10 precedes M11 because M11's gate executes a mutation, which needs a writable
handle. **M12 precedes M13 and its gate is deliberately weaker than the AgentIQ
case**: `compiler.go:344` hardcodes `id` until M13 lands, so a query over a
table without one cannot pass before then. Stating that here is the point — the
first draft of this design claimed M12 demonstrated `dbos.*`, and it cannot.
M14 is last because it generates code for everything before it.

**The release is part of "done".** `agentiq/SPEC.md` §3.2 blocks AgentIQ M1 on
"a tagged release", not a merged branch. `SPEC.md` §8.5 defines it: a semver tag
push runs goreleaser, publishes both binaries and the GHCR image, and the gate
is "green CI on `main`, then the tag."

## Risks / Trade-offs

- **[The read-only reputation is the product]** — gopgql's positioning is
  read-only in six documents and three strings, one of which a language model
  reads. A `@function` directive will be read as "gopgql does mutations now"
  regardless of D1's care. Mitigated by putting the narrowing in §1.1 itself,
  where a reader meets it.
- **[D9 touches `compiler` and `shape`, which every milestone depends on]** —
  and gopgql#10 is rewriting `shape` right now. Mitigated by ordering M13 after
  #10 and by the identity slice defaulting to length one. Not mitigated away:
  `Selection.KeyColumn` is exported and its widening is a source break that also
  moves `cmd/wasm`'s API version.
- **[Three generator invariants are narrowed at once]** — §5.3 invariants 2 and
  4 and the edge-key arity. Each exists because a real failure motivated it, and
  narrowing three guards in one milestone is how a regression gets in.
  Mitigated by keeping every narrowing conditional on "gopgql did not generate
  this table", so the managed path keeps the guard verbatim.
- **[This change is five milestones and a code generator behind one issue]** —
  the honest estimate, not the small one. The natural split, if the owner wants
  one, is **M10+M11 (the mutation surface — items 1, 2 and the `offset`
  regression) against M12+M13+M14 (the unmanaged-schema surface and the
  generator)**. That is the real dependency line: M11 needs nothing from M12–M14,
  whereas M12's gate is only meaningful once M13 lands. It is left as one change
  under the one-issue-one-deliverable rule; the split is the owner's call.
- **[Named notation raises the floor on what the SDL must declare]** — every
  function argument needs a `@column(name:)` unless the parameter is already
  lower-snake-case and matches. Deliberate price of not inferring (D4).
- **[`NULL` versus `DEFAULT` is a trap the SDL cannot warn about]** — an author
  who wants the function's default and passes a nullable variable gets `NULL`
  silently, and for a parameter defaulting to anything but `NULL` that is a
  different call. Mitigated only by documentation, which is a weak mitigation and
  is named as such.
- **[A `@function` call inside a caller's transaction can roll that transaction
  back]** — `RAISE EXCEPTION` aborts the whole transaction, not just the call.
  The error carries the SQLSTATE precisely so the caller can tell an aborted
  transaction from a rejected argument.
- **[`@readonly` is a name that means something other than what it says]** — it
  constrains DDL emission, not query access. Not renamed: it is AgentIQ's word,
  and two names for one thing across two repos is worse.
- **[Two schemas in one graph is unproven, and label alignment is the likelier
  failure]** — `validateLabelAlignment` requires one type per property name
  across the whole graph, and AgentIQ's SDL gives `workflow_uuid` as `String` on
  `Session`/`Event` and `ID!` on `Workflow`. That is `text` versus `uuid` for one
  property name in one graph, which PostgreSQL itself rejects. It is on the
  AgentIQ list below, and M12/M13's container gates are what turn "expected to
  work" into "verified".
- **[CI time]** — five new container-backed godog packages on a job already
  carrying eight, capped at 25 minutes. Each new package shares one container; if
  the cap is reached, milestone suites split across jobs rather than being
  thinned.

## Changes AgentIQ must make

Conclusions of this design, not tasks of this change. `agentiq/SPEC.md` needs a
follow-up in its own repo:

1. **§7.3's directive vocabulary.** `@table(name:, schema:)` → `@node(label:, table:, schema:)`;
   `@vertex(key:)` → `@key(fields:)`; `@edge(from:, to:, label:)` →
   `@relationship(type:, direction:, table:, schema:, sourceKey:, destKey:)`,
   with `table:` naming the existing table (D10).
2. **Function-argument names.** §7.4's `agentDigest: String!` needs
   `@column(name: "agent_digest")`; there is no camelCase derivation (D4).
3. **`queue: String = "agent"`** always sends `"agent"` and never reaches
   `enqueue_workflow`'s own default; and `deduplicationId` omitted from a request
   is sent as `NULL`, not omitted from the call, unless a second operation
   document leaves it out (D4).
4. **A `VOID` function must be declared.** §7.4's `approve` over
   `dbos.send_message` needs `returns: VOID` if that function returns void (D5).
5. **§3.2 item 1's "GraphQL errors with the SQLSTATE."** gopgql returns a typed
   Go error carrying the SQLSTATE; the envelope is AgentIQ's (D6).
6. **`workflow_uuid` has two types in one graph.** §7.1 declares it `String` on
   `Session`/`Event`; §7.3 declares it `ID!` on `Workflow`. `ID` maps to `uuid`
   and `String` to `text` (`SPEC.md` §5.1), and PostgreSQL rejects a property
   graph with one property name at two types. One of them has to move.
7. **§11's `generated/gql/`** is unspecified in both repos (D11).
8. **`JSONB` as a scalar name.** §7.3 uses both `JSON` and `JSONB`; `SPEC.md`
   §5.1 defines `JSON` → `jsonb` and knows no `JSONB` scalar.

## Open Questions

- **Should `@function` be callable from a `query` operation?** A read-only
  function is a legitimate want and nothing in D1 argues against it. Excluded
  here because every consumer requirement is a mutation, and because it raises a
  question this change need not answer: whether a function result composes with
  a `GRAPH_TABLE` projection.
- **Does `mutationType` ever become non-null over MCP?** D3 says no here. It
  needs an authorization story, not a flag.
- **What is `generated/gql/`?** `agentiq/SPEC.md` §11 lists it and no document
  says what it holds.
- **Should the CLI move to Cobra?** D13 says not in this change. Once there are
  two-word subcommands and per-subcommand flags, the argument for it is
  stronger than it is today.
- **Should `--no-tables` survive `@readonly`?** D7 keeps both. If `@readonly`
  proves sufficient the flag is a removal candidate — but §3.0's history check
  is built around it and it shipped one release ago.
- **Which tag?** `v0.1.0` is the only tag. `v0.2.0` is the recommendation;
  `v1.0.0` would claim a stability §9's remaining open decisions do not support.
