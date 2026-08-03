## 1. Determinism first — the `ORDER BY` both strategies need

Sequenced first on purpose. Byte-identity is impossible while list order is
whatever the planner produced (design D4), and this is the one task that changes
the *existing* Go-side path, so it lands on its own where a regression is
attributable.

- [ ] 1.1 `compiler`: emit `ORDER BY <level key>, …` on the flat query, outermost level first, over every projected level's key column. Total, because each key is a level's unique `id`.
- [ ] 1.2 Confirm the M1–M7 suites still pass unchanged. They compare with array order ignored (`canon`, `test/m3/m3_test.go:303`), so a newly-determined order is still an accepted one — assert this rather than assume it.
- [ ] 1.3 A compiler unit test asserting the emitted `ORDER BY` covers every level of a three-hop query and of an M5 branch split.

## 2. `compiler` — the strategy selector

- [ ] 2.1 `type Shaping int`, `GoSide`/`SQLSide`, `DefaultShaping = GoSide`, `String()`. In `compiler`, **not** `shape` — `shape` imports `compiler` and the reverse edge would cycle (design D1).
- [ ] 2.2 `WithShaping(Shaping) Option` and `(*Compiler).Shaping() Shaping`, mirroring `WithMaxDepth`/`MaxDepth`.
- [ ] 2.3 `Compiled` gains `Shaping`, set from the compiler that produced it.
- [ ] 2.4 `ProjectedField` gains the GraphQL scalar it projects — the named type as the SDL declares it (`Int`, `DateTime`, …) plus whether the field is a list — because `shape` needs it to normalise a leaf and only the compiler knows it.
- [ ] 2.5 The compiler stays pure and WASM-safe: no new import that pulls in a database (`SPEC.md` §4.1, §6.1). Assert with the existing `GOOS=js GOARCH=wasm` build.

## 3. `compiler` — emit the SQL-side query

- [ ] 3.1 Render the aggregation bottom-up, one subquery per projection level over the same `GRAPH_TABLE`, `json_build_object` + `json_agg(... ORDER BY <level key>)`, outermost expression cast `::text` as a single column named `response` (design D2).
- [ ] 3.2 `json`, never `jsonb`: `jsonb_build_object` sorts keys by length-then-bytes and drops duplicates, and costs a parse-and-reserialise for a value going straight out as text.
- [ ] 3.3 M5 branch splits: aggregate **each fragment to a JSON array before the join**, so the *m×n* branch cross-product never forms. A parent with no match on a branch shapes to `[]`, not to a disappeared parent — the M5 semantics, preserved.
- [ ] 3.4 The `MATCH` pattern, its predicates, its bind parameters and their `$n` order are **identical** between strategies. A golden-file test asserts the two emitted SQLs differ only outside `MATCH`.
- [ ] 3.5 `JSON`-typed (`jsonb`) fields are projected `::text` under **both** strategies (design D5) — the driver's generic JSON decode would turn `19.90` into `float64` 19.9 on one side only.
- [ ] 3.6 Every aggregate is wrapped `COALESCE(json_agg(…), '[]'::json)`: `json_agg` over an empty set returns SQL `NULL`, where the Go-side shaper returns an empty list. Without this a root field matching nothing is `{"persons":null}` on one side and `{"persons":[]}` on the other.
- [ ] 3.7 The `GROUP BY` lists the level's key **and** its projected scalars — PostgreSQL only exploits functional dependence when grouping by a base table's primary key, which a column projected out of `GRAPH_TABLE` is not.
- [ ] 3.8 A scalar with no canonical form (design D5's table) is a **compile-time error under `SQLSide` only** — a typed `*UnshapeableScalarError` alongside `*DepthExceededError`, naming the field, its GraphQL type and its column type, so a caller can branch on the cause and fall back rather than match English. `GoSide` keeps accepting it.
- [ ] 3.9 Depth ceiling, isomorphism guards and interface positions behave identically under both strategies — they are pattern concerns, not projection concerns.

## 4. `shape` — one canonical response, one encoder

- [ ] 4.1 `Encode(resp map[string]any) ([]byte, error)` — the canonical encoding, `encoding/json` over the response value. Its doc comment states what byte-identity does and does not claim (design D3).
- [ ] 4.2 The leaf normaliser: one canonical Go representation per GraphQL scalar, reached from either a pgx-scanned value or a decoded JSON value (design D5's table).
- [ ] 4.3 `Rows` normalises its leaves through it — the Go-side half.
- [ ] 4.4 `Decode(proj compiler.Projection, jsonText string) (map[string]any, error)` — decode with `json.Decoder.UseNumber()` so the database's own digits survive, then normalise. The SQL-side half.
- [ ] 4.4a A key the projection does not describe is a typed error, never a silently dropped field: it means the emitted SQL and the projection have diverged, which is a compiler bug and should say so.
- [ ] 4.5 `DateTime` normalises to RFC3339Nano **in UTC** on both paths, so the response stops depending on the session `TimeZone`.
- [ ] 4.6 A non-finite `Float` fails on both paths with the same error — PostgreSQL emits the JSON string `"NaN"` where `json.Marshal` refuses the value.
- [ ] 4.7 Unit tests over the normaliser table, no container needed: for each scalar, a pgx-shaped value and the JSON-decoded value normalise to the same thing and encode to the same bytes.

## 5. `exec` — dispatch

- [ ] 5.1 `Query` reads `cq.Shaping`: `GoSide` → `Rows` as today; `SQLSide` → read the single `response` string and `shape.Decode` it.
- [ ] 5.2 Signature unchanged, so `mcp` and every integration suite keep compiling and inherit their compiler's strategy.
- [ ] 5.3 An SQL-side result that is not exactly one row of one column is a clear error, not a panic.
- [ ] 5.4 The `response` column is scanned as text, never through the driver's JSON codec.

## 6. `test/parity` — the milestone's acceptance criterion

Runs against a real `postgres:19beta2` container. This section *is* the issue's
parity bullet.

- [ ] 6.1 A catalogue: SDL + seed + query + variables, one entry per distinct query the M1–M7 suites execute — the 24 `I compile and execute` steps across `test/m{1..6}/features/*.feature`, plus the queries `test/m7/m7_test.go` runs through `exec.Query`.
- [ ] 6.2 Table-driven over `{GoSide, SQLSide}` × catalogue: `shape.Encode` of the two responses is **byte-equal**.
- [ ] 6.3 Each response also equals what the owning milestone suite already asserts, so parity cannot be satisfied by both strategies being wrong together.
- [ ] 6.4 Order is asserted **exactly** here — no `canon`, no array-order-ignoring. This is the one suite where list order is part of the claim.
- [ ] 6.5 Coverage guard: scan `test/m*/features/*.feature` for `I compile and execute "<q>"` and fail naming any query the catalogue omits; M7's entries are registered explicitly with an expected count, since it has no feature file (design D6).
- [ ] 6.6 Explicit parity cases for the divergences the design predicts: a many-child fan-out (order), a `numeric(10,2)` column (trailing zeros), a `DateTime` column (`Z` versus `+00:00`), an M5 branch split (`[]` for a childless branch), a query matching **nothing** (`[]`, never `null` — the `json_agg` empty-set trap), and a `null` scalar (`null`, never absent).
- [ ] 6.7 One container for the package, shared across the table, as the milestone suites already do internally — the CI test job is capped at 25 minutes and this change adds two container-backed packages (design, Risks).

## 7. `test/bench` — the benchmark

- [ ] 7.1 A fixture generator: a graph of the declared depth and fan-out from a **fixed seed**, so two runs are comparable.
- [ ] 7.2 Benchmarks over depth ∈ {1, 2, 3} × fan-out ∈ {1, 8, 64} × strategy, driving `exec.Query` end to end against the container.
- [ ] 7.3 `b.ReportMetric` for **rows returned** and **bytes received** — the two numbers that are properties of the strategy rather than of the runner (design D7).
- [ ] 7.4 The axes are declared once in Go and are what both the benchmark and the doc check read.
- [ ] 7.5 An ordinary test asserts `docs/benchmarks.md`'s axes table matches that declaration — add an axis, forget the doc, CI goes red.
- [ ] 7.6 An ordinary test asserts the rows-returned counts (`f^d` versus 1), which are deterministic; timings are never asserted.

## 8. CI, docs and the playground

- [ ] 8.1 `.github/workflows/ci.yml`: `go test -run '^$' -bench . -benchtime 1x ./test/bench/...` as a smoke run, so the benchmark cannot silently stop compiling or stop returning results. If it crowds the test job's 25-minute cap, it moves to its own job — the parity suite is never the thing that gets thinned.
- [ ] 8.2 `Makefile`: a `bench` target that runs the real benchmark and regenerates `docs/benchmarks.md`.
- [ ] 8.3 `docs/benchmarks.md`: the committed results, with the machine, Go version, PostgreSQL image tag and date that produced them, and the note that the timings are from that machine.
- [ ] 8.4 `playground.CompileWithShaping(sdlSrc, query, vars, strategy)` alongside `Compile`/`CompileWithMaxDepth`, and the derived result-set shape (*k* columns assembled in Go versus one `response` column assembled in PostgreSQL).
- [ ] 8.5 Playground tab: a Go-side / SQL-side toggle over one SDL, query and variables, showing the SQL each strategy emits, running the real compiled Go. It states that it shows generated SQL and not results, and shows no response, row count or timing — executing SQL in the playground is gopgql#31, Blocked on postgres-pglite#28 (design D8).
- [ ] 8.6 A playground unit test on the host asserting both strategies compile the example query and that the two SQL texts differ (so the toggle cannot silently render the same thing twice).
- [ ] 8.7 `SPEC.md`: §3 decision 4 marked reached and corrected to `json`/`json_agg`; §4.1's `shape` row updated; §7 → M8 marked implemented, with the byte-identity definition (design D3) and the `jsonb`-versus-`json` correction recorded.
- [ ] 8.8 `README.md`: the strategy option, what byte-identity means, and a pointer to `docs/benchmarks.md`.
- [ ] 8.9 Full CI green — `go build ./...`, `go vet ./...`, the `GOOS=js GOARCH=wasm` build, the whole godog suite plus `test/parity` against containers, the benchmark smoke run, `golangci-lint run ./...`, `govulncheck ./...`, and the docs/playground build.
