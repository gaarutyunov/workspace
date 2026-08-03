## Why

gopgql has one way to turn a query result into a GraphQL response: `shape.Rows`
regroups flat rows in Go (M3). `SPEC.md` §3 decision 4 has always said that is
only the *first* strategy — a second one, building the nested response
in-database with `json_agg`, is to be added and benchmarked against it. M8 is
that milestone (`SPEC.md` §7 → M8).

The milestone's whole weight sits on one sentence: **"both must produce
byte-identical responses."** That claim is not free, and it is not true in the
form the milestone is written in. Verified against a real `postgres:19beta2`:

| | emitted text |
|---|---|
| Go `json.Marshal` of the M3 response | `{"follows":[{"name":"Bob"}],"name":"Alice"}` |
| `json_build_object(...)` | `{"name" : "Alice", "follows" : [{"name" : "Bob"}]}` |
| `jsonb_build_object(...)` | `{"name": "Alice", "follows": [{"name": "Bob"}]}` |

Three independent disagreements — key order, whitespace, and (below) scalar
rendering — and `jsonb_build_object` additionally **sorts keys by length then
bytes and drops duplicate keys**: `jsonb_build_object('zebra',1,'a',2,'bb',3)`
returns `{"a": 2, "bb": 3, "zebra": 1}`. So the milestone cannot mean "the bytes
PostgreSQL sends equal the bytes Go writes". This change decides what it *does*
mean, and makes that version true by construction rather than by hope.

## What Changes

- **A second shaping strategy.** The compiler emits either the flat projection
  it emits today (Go-side) or a single-row, single-column query that aggregates
  the same `GRAPH_TABLE` output bottom-up with `json_build_object` / `json_agg`
  (SQL-side). The `MATCH` pattern is **identical** under both, so which rows
  match is not part of what has to be proven.
- **Strategy selection is a compiler option** — `compiler.WithShaping(...)`,
  recorded on the `*Compiled` it produces. It cannot be an execution-time switch:
  the two strategies emit *different SQL* (design D1).
- **`json`, not `jsonb`.** `jsonb` reorders and deduplicates keys and costs a
  parse-and-reserialise round trip for a value that is going straight out as
  text. The milestone text says `jsonb_build_object` / `json_agg`; that mixture
  is wrong and this change corrects it (design D2).
- **One encoder, one canonical response.** Both strategies return the same
  `map[string]any` from `exec.Query`, whose leaves are normalised to one Go
  representation per GraphQL scalar. Byte-identity is then a property of
  `shape.Encode` over that value, and it holds *by construction* — PostgreSQL's
  key order and whitespace never reach a caller (design D3).
- **Deterministic list order.** Neither strategy guarantees one today; the
  M1–M7 suites compare responses with array order *ignored*, which would have
  hidden a real divergence. The compiler starts emitting a total `ORDER BY` over
  every level's key column, and `json_agg` carries the matching `ORDER BY`
  (design D4).
- **A scalar-rendering contract**, because the remaining divergences are in the
  leaves: `timestamptz` renders as `2026-07-30T12:00:00+00:00` in PostgreSQL and
  `2026-07-30T12:00:00Z` in Go, and depends on the session `TimeZone`; a `NaN`
  `double precision` becomes the JSON *string* `"NaN"` in PostgreSQL while
  `json.Marshal` refuses it outright. Every projected scalar gets a defined
  canonical form, and **a scalar with no defined canonical form is a compile-time
  error under SQL-side shaping** — never a silent divergence (design D5).
- **A parity suite** re-running every prior milestone's query scenarios under
  both strategies and asserting the encoded responses are byte-equal, plus a
  guard test that fails when a milestone suite gains a query the catalogue does
  not cover (design D6).
- **A committed benchmark** over depth × fan-out, with CI running it at
  `-benchtime 1x` so it cannot rot, and a generated-and-checked axes table so
  the docs cannot drift from the benchmark (design D7).
- **Playground**: a shaping toggle showing the SQL each strategy emits for the
  same query, side by side, running the real compiled Go. It shows *SQL*, not
  results — the browser has no database, and executing SQL in the playground is
  gopgql#31, which is blocked (design D8).

## Capabilities

### New Capabilities

- `gopgql-sql-side-shaping`: the second strategy — how the strategy is selected,
  what each one emits, and the boundary that keeps the selector WASM-safe.
- `gopgql-response-parity`: the canonical response, the deterministic ordering,
  the scalar contract, and the byte-identity guarantee with the suite that
  proves it.
- `gopgql-shaping-benchmark`: what the benchmark measures, over which axes, what
  is committed, and how CI stops it rotting.
- `gopgql-playground-shaping`: the playground's strategy toggle and what it is
  allowed to claim.

### Modified Capabilities

<!-- The gopgql specs (M1–M8) predate OpenSpec and are not in openspec/specs/,
     so there are no existing capability specs to amend. M7 (gopgql#9) recorded
     the same note. SPEC.md §3 decision 4, §4.1 and §7 are the project's own
     reference and are updated by this change. -->

## Impact

- **`compiler`**: a `Shaping` type and `WithShaping` option; `Compiled` records
  the strategy it was compiled under; `ProjectedField` gains the GraphQL scalar
  it projects (the shaper needs it to normalise leaves); the renderer grows a
  second output form and a deterministic `ORDER BY`. Still pure — no database
  contact, still WASM-safe (`SPEC.md` §6.1).
- **`shape`**: gains `Decode` (database JSON → the canonical response) and
  `Encode` (the canonical response → the canonical bytes), and the leaf
  normaliser both strategies share. `shape` imports `compiler`, so the `Shaping`
  type must live in `compiler` or the two would form an import cycle.
- **`exec`**: `Query` dispatches on `cq.Shaping`. Signature unchanged, so every
  existing caller — including `mcp` — keeps working and inherits whichever
  strategy its compiler was configured with.
- **`test/parity`** (new): the scenario catalogue, the two-strategy table-driven
  run, and the guard that keeps the catalogue complete.
- **`test/bench`** (new): the depth × fan-out benchmark and its deterministic
  fixture generator.
- **`docs/benchmarks.md`** (new), `docs/src/main.js` + `docs/index.html`
  (the shaping tab), `playground` (the toggle entry point).
- **`.github/workflows/ci.yml`**: a benchmark smoke step.
- **Backwards compatibility**: additive. `DefaultShaping` is Go-side, so a
  caller that sets nothing gets exactly today's behaviour — with the single
  intended exception that responses become deterministically ordered, which the
  existing suites already tolerate because they compare with array order
  ignored.
