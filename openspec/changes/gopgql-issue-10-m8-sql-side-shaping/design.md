## Context

Four facts about the code as it stands (read at `16fd477`, worktree
`.worktrees/issue-10`) and four facts about PostgreSQL 19beta2 (verified by
running them, not by reading the manual) shape every decision below.

**The response is a Go value, not bytes.** `exec.Query` returns
`map[string]any`; `shape.Rows` builds it from flat rows keyed by each level's
projected `id`. Nothing in gopgql currently produces JSON *text* at all — the
integration suites marshal the map themselves to compare it. So "byte-identical
response" has no referent today; this change has to supply one.

**The emitted SQL is not always one `GRAPH_TABLE`.** M5 splits a level that
selects several relationships into one fragment per branch, `LEFT JOIN`ed on
projected ids (`compiler.builder.render`). Any SQL-side shaper has to survive
that, and the flat join is exactly where the row count explodes: two branches of
*m* and *n* children yield *m×n* rows carrying the same parent.

**Nothing orders anything.** `render` emits no `ORDER BY`. `shape.group`
preserves first-seen row order, which is whatever the planner produced. The
M1–M7 suites paper over this with a `canon` helper that sorts arrays before
comparing (`test/m3/m3_test.go:303`) — i.e. the project has never asserted list
order, because it could not.

**`shape` imports `compiler`.** Any type both packages need — such as the
strategy selector — has to live in `compiler`, or the import graph cycles.

And from `postgres:19beta2`:

- `json_build_object` preserves argument order and emits `{"k" : v}`;
  `jsonb_build_object` sorts keys by length-then-bytes and keeps only the last
  of a duplicated key (`'zebra',1,'a',2,'bb',3` → `{"a": 2, "bb": 3, "zebra": 1}`).
- `timestamptz` renders into JSON as `2026-07-30T12:00:00+00:00`, in the
  **session's** `TimeZone`. Go's `time.Time` marshals as `2026-07-30T12:00:00Z`.
- `numeric` keeps its trailing zeros (`19.90` stays `19.90`); a `double
  precision` `NaN` becomes the JSON **string** `"NaN"`, which `json.Marshal`
  would have refused to emit at all.
- A `GRAPH_TABLE` call can be wrapped in a subquery and aggregated bottom-up
  with `GROUP BY` + `json_agg(... ORDER BY ...)`. This was verified end to end
  on a generated `app_graph`, and it is the shape D2 builds on.

## Goals / Non-Goals

**Goals:**

- A second shaping strategy that is genuinely selectable and genuinely a
  different query.
- A byte-identity claim that is *true*, and true by construction rather than by
  a passing test.
- Numbers that say when SQL-side shaping is worth choosing, produced by a
  benchmark that CI keeps alive.
- Every claim proven against a real `postgres:19beta2` container.

**Non-Goals:**

- Choosing a strategy automatically. M8's job is to produce the measurements; a
  heuristic that picks for the caller would hard-code a conclusion before the
  numbers exist (D1, alternative D).
- Changing which rows a query matches. The `MATCH` pattern is byte-identical
  between strategies; only the projection and aggregation differ.
- Executing SQL in the playground. That is gopgql#31, blocked on
  postgres-pglite#28.
- A zero-copy pass-through of the database's JSON bytes to a caller. It is the
  strategy's biggest theoretical win and it is explicitly *not* byte-identical to
  the Go side (Risks, and Open Questions).

## Decisions

### D1: Strategy selection is a **compiler option**, recorded on the compiled query

The two strategies emit different SQL — one projects *k* flat columns, the other
projects a single `response` column. So the choice must be made before
compilation, and nothing downstream can change it after the fact.

```go
type Shaping int
const ( GoSide Shaping = iota; SQLSide )
const DefaultShaping = GoSide

func WithShaping(s Shaping) Option           // mirrors WithMaxDepth
func (c *Compiler) Shaping() Shaping         // mirrors MaxDepth()
type Compiled struct { …; Shaping Shaping }  // additive field
```

`exec.Query` reads `cq.Shaping` and dispatches. Its signature does not change,
so every existing caller — the integration suites, `mcp` — keeps compiling and
inherits whatever its compiler was configured with. A caller that wants both
constructs two `Compiler`s over the same `*sdl.Document`; a `Compiler` holds no
mutable state, so this is free.

The `Shaping` type lives in **`compiler`**, not `shape`, because `shape` already
imports `compiler` and the reverse edge would cycle.

- *Alternative A — a runtime switch on `exec`.* Rejected: `exec` would have to
  recompile to honour it, which breaks compile-once/execute-many and drags a
  database-free contract (`SPEC.md` §6.1) into the execution path.
- *Alternative B — an environment variable or package-level global.* Rejected:
  invisible at the call site, and the parity suite — whose entire job is to run
  both strategies over the same scenarios — would be racing a global.
- *Alternative C — a per-query GraphQL directive, `@shaping(sql: true)`.*
  Rejected: it puts an operational choice in the query language, where the
  person writing it is not the person who cares. The SDL is the mapping model,
  not a settings file.
- *Alternative D — pick automatically from the projection's depth and fan-out.*
  Tempting, and the benchmark is exactly the input such a heuristic would need.
  Rejected **for M8**: the milestone exists to produce those numbers, and
  shipping the heuristic in the same milestone means the heuristic was written
  before the evidence. Recorded as an open question.

### D2: `json`, not `jsonb`, and aggregate **bottom-up per fragment**

The milestone text says "`jsonb_build_object` / `json_agg`". That mixture is
wrong twice over. `jsonb` reorders keys, deduplicates them, and costs a
parse-into-binary plus reserialise for a value whose only destination is text.
`json` does none of that. The strategy uses `json_build_object`, `json_agg` and
`json_build_array` throughout, and the outermost expression is cast `::text` so
the driver hands back a plain string rather than running its own JSON decode
(which would turn `19.90` into a `float64` and lose the digit).

The aggregation walks the projection **bottom-up, one subquery per level, over
the same `GRAPH_TABLE` the Go-side strategy would have used**:

```sql
SELECT (json_build_object('persons', json_agg(
          json_build_object('name', p.name, 'follows', p.follows)
          ORDER BY p.v0_id)))::text AS response
FROM (
  SELECT g.v0_id, g.v0_name AS name,
         json_agg(json_build_object('name', g.v1_name) ORDER BY g.v1_id) AS follows
  FROM GRAPH_TABLE (app_graph
        MATCH (v0 IS person)-[e0 IS follows]->(v1 IS person)
        COLUMNS (v0.id AS v0_id, v0.name AS v0_name,
                 v1.id AS v1_id, v1.name AS v1_name)) AS g
  GROUP BY g.v0_id, g.v0_name
) AS p;
```

Where M5 split the query into fragments, **each fragment is aggregated to a JSON
array before the join**, so the branch cross-product never forms: a parent with
*m* and *n* children joins two single-row aggregates instead of producing *m×n*
rows. That is both the correct result and the clearest reason SQL-side shaping
can win.

Two details of that rendering are load-bearing and easy to get wrong:

- **`json_agg` over an empty set returns SQL `NULL`, not `[]`.** The Go-side
  shaper returns an empty list for the same case, so every aggregate is wrapped
  `COALESCE(json_agg(…), '[]'::json)`. Without it a root field matching nothing
  encodes as `{"persons":null}` on one side and `{"persons":[]}` on the other —
  the parity failure that costs nothing to prevent and is invisible until a
  fixture happens to be empty.
- **The `GROUP BY` lists the level's key *and* its projected scalars.** They are
  functionally dependent on the key, but PostgreSQL only exploits that when
  grouping by a base table's primary key, which a column projected out of
  `GRAPH_TABLE` is not.

- *Alternative — `LEFT JOIN LATERAL` a correlated `GRAPH_TABLE` per parent.*
  Verified to work on 19beta2 (the correlation sits in the subquery's ordinary
  `WHERE` over a projected id, not inside the graph pattern). Rejected anyway:
  it re-executes `GRAPH_TABLE` once per parent row, which is the N+1 that
  `SPEC.md` §6.2 says the compiler avoids by construction, and it would make the
  benchmark measure the wrong thing.
- *Alternative — one flat `GRAPH_TABLE` plus a single outer `GROUP BY` with
  nested `json_agg(DISTINCT …)`.* Rejected: `DISTINCT` inside the aggregate
  cannot express "distinct by the level's key but keeping the level's other
  columns", and it silently collapses two genuinely equal siblings into one.

### D3: "Byte-identical" means **one encoder over one canonical response**

This is the decision the milestone stands on, so it is stated as a definition
rather than a hope.

> The response is the `map[string]any` returned by `exec.Query`. Its canonical
> encoding is `shape.Encode`, which is `encoding/json` over that value. **Two
> strategies produce byte-identical responses when `shape.Encode` of each
> returns equal bytes.**

Under that definition byte-identity holds *by construction*, because the
database's own serialisation never reaches a caller: the SQL-side path decodes
the returned text into the same Go value the Go-side path builds, and one
encoder writes both. PostgreSQL's key order, its `{"k" : v}` spacing, and
`jsonb`'s reordering and deduplication all stop at that boundary. Go's map-key
sort then decides the key order on both sides, identically.

Key **deduplication** — the other `jsonb` hazard — cannot bite regardless:
GraphQL response keys are unique within a selection set by the language's own
rules, and the compiler derives each `Selection`/`ProjectedField` response key
from exactly one selection.

What this definition deliberately does *not* claim: that the bytes on the wire
from PostgreSQL equal the bytes gopgql writes. They do not, they cannot, and
saying so is the honest half of the milestone. It is called out in the docs and
in `shape.Encode`'s doc comment.

- *Alternative A — compare the raw database text against `json.Marshal`.*
  Rejected: impossible, per the three verified disagreements above. Pursuing it
  would mean either teaching PostgreSQL Go's key sort (possible with
  `json_build_object`, since it preserves argument order — but the `{"k" : v}`
  spacing is still unfixable without string-concatenating DDL by hand) or
  teaching Go PostgreSQL's spacing (a custom encoder, and then gopgql's response
  bytes stop being idiomatic JSON for no gain).
- *Alternative B — weaken the claim to "semantically equal", using the existing
  `canon` helper.* Rejected: `canon` sorts arrays before comparing, so it would
  pass even if the two strategies returned lists in different orders — which,
  before D4, they genuinely would. A parity test that cannot see the one
  divergence most likely to occur is not a parity test.
- *Alternative C — make `exec.Query` return `[]byte` under SQL-side shaping and
  `map[string]any` under Go-side.* Rejected: two return types for one function,
  and callers would have to branch on a strategy they did not choose.

### D4: Both strategies get a **total, deterministic order**

Byte-identity forces this. `json_agg` without `ORDER BY` aggregates in whatever
order the plan delivers; `shape.group` preserves whatever order the rows
arrived in. Two different queries, two different plans, two different orders —
and the claim fails on a fan-out of two.

So the compiler emits, under **both** strategies, an order over every level's
key column:

- Go-side: `ORDER BY <v0 key>, <v1 key>, …` on the outer query, outermost level
  first. Every key is a level's `id`, unique within its level, so the order is
  total.
- SQL-side: the same key as the `ORDER BY` inside each level's `json_agg`.

The order is arbitrary (uuids), but it is *the same* arbitrary order, which is
what identity needs. No existing scenario breaks: the M1–M7 suites compare with
array order ignored, so a newly-determined order is still an accepted one.

- *Alternative — leave the SQL unordered and sort in Go after decoding.*
  Rejected: it would make the SQL-side response a Go-side post-process, hiding
  the cost the benchmark exists to measure, and it cannot sort what `json_agg`
  has already flattened into a nested document without walking the whole tree.

### D5: A **scalar contract**, and a compile-time refusal where there is none

With structure and order settled, every remaining divergence is in a leaf. Each
GraphQL scalar gets one canonical Go representation, reached from either side:

| GraphQL | PostgreSQL | Canonical form | Go-side source | SQL-side source |
|---|---|---|---|---|
| `Int` | `integer` | `json.Number` of the integer text | pgx `int32`/`int64` | decoded with `UseNumber` |
| `Float` | `double precision` | `json.Number`; non-finite is an **error** | pgx `float64` | decoded with `UseNumber`; `"NaN"`/`"Infinity"` mapped back to the non-finite float so both paths fail identically |
| `Float` via `@column(type: "numeric(p,s)")` | `numeric` | `json.Number` of the database's own digits, trailing zeros kept | pgx `pgtype.Numeric` | decoded with `UseNumber` |
| `String` | `text` | Go `string` | pgx `string` | decoded string |
| `Boolean` | `boolean` | Go `bool` | pgx `bool` | decoded bool |
| `ID` | `uuid` | canonical 8-4-4-4-12 string | `exec.uuidString` | decoded string |
| `DateTime` | `timestamptz` | RFC3339Nano **in UTC** | `t.UTC()` | parsed, converted to UTC, re-rendered |
| `JSON` | `jsonb` | the value decoded with `UseNumber` | column projected `::text` in the outer `SELECT`, decoded in `shape` | embedded verbatim, decoded with `UseNumber` |
| `[T!]!` of scalar | `T[]` | list of the element scalar's canonical form | pgx slice | decoded array |
| `null` | `NULL` | Go `nil` | `nil` | `null` |

Two of these rows are corrections, not conveniences. **`DateTime` normalises to
UTC**: PostgreSQL renders `timestamptz` in the *session's* `TimeZone`, so
without this the same row is `…+00:00` on one connection and `…+02:00` on
another, and neither matches Go's `…Z`. **`Float` non-finite is an error**:
PostgreSQL turns `NaN` into the JSON string `"NaN"` while `json.Marshal`
refuses the value, so a silent success on one side and a failure on the other is
exactly the divergence the milestone must not have.

`JSON`-typed fields are projected `::text` under **both** strategies. Left to
the driver, a `jsonb` column is decoded through `any` and `19.90` comes back as
`float64` 19.9 — a precision loss on one side only.

**And the safety valve:** a projected scalar with no entry in this table — a
type reached through `@column(type:)` that gopgql has no canonical form for — is
a **compile-time error under SQL-side shaping**, naming the field, its GraphQL
type and its column type. Go-side shaping keeps accepting it, because it makes
no cross-strategy promise about it. Refusing to compile is the only outcome that
cannot quietly break the guarantee.

It is a **typed** error — `*UnshapeableScalarError`, alongside
`*DepthExceededError` — for the reason M7 gave for typed conformance findings:
a caller that wants to fall back to Go-side shaping has to branch on the cause,
and it should not do that by matching English. The same reasoning applies at the
other end: `shape.Decode` meeting a key the projection does not describe is a
typed error too, never a silently dropped field. That case means the emitted SQL
and the projection have diverged, which is a compiler bug, and it should say so
rather than produce a response missing a key the Go-side path would have had.

### D6: Parity is a **catalogue**, and a guard keeps the catalogue complete

The exit criterion is "every prior milestone's query scenarios re-run under
SQL-side shaping". Restating that list in prose would be wrong within one
milestone. Instead:

- `test/parity` owns a **catalogue**: SDL + seed + query + variables, one entry
  per distinct query the M1–M7 suites execute (24 `I compile and execute` steps
  across the M1–M6 feature files, plus the queries `test/m7/m7_test.go` compiles
  through `exec.Query`).
- The suite is table-driven over `{GoSide, SQLSide}` × catalogue, against one
  real `postgres:19beta2` container, and asserts `shape.Encode` of the two
  responses is byte-equal — *and* that each equals the response the milestone
  suite already asserts, so parity cannot be achieved by both sides being wrong
  together.
- A **guard test** scans `test/m*/features/*.feature` for `I compile and execute
  "<q>"` and fails naming any query absent from the catalogue. M7 has no feature
  file, so its entries are registered explicitly and the guard covers M7 by
  asserting the count it expects — a later milestone that adds a query has to
  touch the catalogue to make the build green.

The MCP server (`mcp`) executes through `exec` and therefore inherits its
compiler's strategy; it needs no change and gets no separate parity entry.

### D7: The benchmark measures **rows shipped**, not just nanoseconds

A wall-clock number from a GitHub runner is nearly meaningless. The reason to
choose SQL-side shaping is that a depth-*d*, fan-out-*f* query ships *f^d* flat
rows to the client under Go-side shaping and **one row** under SQL-side, so the
benchmark reports that directly:

- **Axes:** depth ∈ {1, 2, 3} (3 is `DefaultMaxDepth`) × fan-out ∈ {1, 8, 64},
  over a fixture graph generated from a **fixed seed** so two runs are
  comparable.
- **Metrics:** `ns/op`, `B/op`, `allocs/op` from the framework, plus
  `b.ReportMetric` for **rows returned** and **bytes received** — the two
  numbers that are properties of the strategy rather than of the runner.
- **Committed output:** `docs/benchmarks.md`, carrying the machine, the Go
  version, the PostgreSQL image tag and the date that produced it, and saying
  plainly that the timings are from that machine.
- **CI:** `go test -run '^$' -bench . -benchtime 1x ./test/bench/...`. One
  iteration per case proves it compiles, boots a container, and that both
  strategies still return a result. It does not assert timings — a shared runner
  cannot, and a flaky performance gate would be turned off within a month.
- **Anti-rot beyond compiling:** the axes are declared once in Go and
  `docs/benchmarks.md`'s axes table is checked against that declaration by an
  ordinary test. Add an axis and forget the doc, and CI goes red. `make bench`
  regenerates the document.

- *Alternative — assert a performance ratio in CI (e.g. "SQL-side within 2× on
  the depth-3 case").* Rejected: noisy runners, and the first flake gets the
  check disabled. Rows and bytes are deterministic and are asserted instead.
- *Alternative — no CI run at all, just a committed file.* Rejected outright by
  the issue, and correctly: an unbuilt benchmark stops compiling within two
  milestones.

### D8: The playground shows **two SQL texts**, and says so

The playground compiles `sdl` + `generator` + `migrate` + `compiler` to WASM and
runs them for real; it has no database and never has had. Compiling a query
under a strategy is pure compiler work, so a shaping toggle is entirely within
what the playground can honestly do: the same SDL, the same query, the same
variables, compiled twice, both SQL texts shown.

`playground.CompileWithShaping(sdlSrc, query, vars, strategy)` is the entry
point, alongside the existing `Compile` / `CompileWithMaxDepth`. The panel
states that it shows generated SQL and not results, for the same reason the
conformance tab states that its report is a fixture (M7, design D5).

It may also show one thing computed rather than asserted: the **shape of the
result set** each strategy asks for — *k* projected columns assembled in Go
versus a single `response` column assembled in PostgreSQL. That is derivable
from the projection with no database, and it is the point of the whole
milestone made visible.

The panel must **not** show a response, a row count, or a timing. Executing SQL
in the playground is gopgql#31, which is Blocked on postgres-pglite#28.

## Risks / Trade-offs

- **[The claim is about gopgql's response, not PostgreSQL's bytes]** — this is
  the honest reading of "byte-identical", and it is weaker than the milestone
  text sounds. Mitigated by saying so in `SPEC.md`, in the docs, and in
  `shape.Encode`'s doc comment rather than letting a reader assume the stronger
  thing.
- **[Decoding the database's JSON gives back much of what SQL-side shaping
  saved]** — parity requires a Go-side decode, so the strategy's ceiling (hand
  the database's bytes straight to a socket) is not reached. The benchmark
  reports bytes-received alongside timings so the gap is visible rather than
  implied, and the pass-through surface is an open question, not a silent
  omission.
- **[`ORDER BY` is a real cost added to both strategies]** — a sort over every
  level's key that no query needed before. It is the price of a determinism the
  project did not have; the benchmark measures the ordered form, which is the
  form that ships.
- **[The scalar table is the fragile part]** — it is a hand-maintained
  correspondence between two serialisers that neither gopgql nor its tests own.
  Mitigated by the compile-time refusal for anything absent from it, and by unit
  tests over the table itself that do not need a container.
- **[`@column(type:)` can reach types nobody enumerated]** — a `hstore`, an
  `interval`, a domain. Under SQL-side shaping these now fail to compile where
  they previously ran. That is a behaviour change for a strategy nobody has
  opted into yet, and it is the correct direction.
- **[The parity guard reads feature files as text]** — a step phrased slightly
  differently slips past it. Mitigated by the M7-style explicit count, and it
  fails safe in one direction only: a missed query is not *tested*, never
  wrongly *passed*.
- **[CI time]** — every suite boots its own `postgres:19beta2` via
  testcontainers, and this change adds two packages that need one. The test job
  is capped at 25 minutes today. `test/parity` and `test/bench` therefore share
  one container across the package (as the milestone suites already do within
  themselves), the benchmark's fixture is generated once per size rather than
  per iteration, and the CI smoke run is a single iteration. If the job still
  crowds its cap, the benchmark smoke moves to its own job rather than the
  parity suite being thinned — parity is the acceptance criterion.

## Open Questions

- Should `exec` gain a pass-through that returns the database's JSON bytes
  without decoding? It is where the strategy's real win lives, and it is
  explicitly outside the byte-identity guarantee — a different surface with a
  different contract. Not in M8.
- Should the compiler choose a strategy automatically once the M8 numbers exist
  (D1, alternative D)? The benchmark is the input; the heuristic is a later
  milestone's decision.
- `SPEC.md` §3 decision 4 says "Go-side regrouping first; SQL-side `json_agg`
  added in a later milestone and benchmarked against it" — it does not say the
  Go-side strategy remains the default forever. Whether the default flips is a
  question the benchmark answers, and answering it is not M8.
