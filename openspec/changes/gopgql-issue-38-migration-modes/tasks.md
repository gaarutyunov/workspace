## 1. The mode type and the marker

The marker comes first because everything else depends on being able to read a
directory's mode back (design D2).

- [ ] 1.1 `migrate.Mode` with `ModeAll` (default, zero value), `ModeTables`, `ModeGraph`; `ParseMode(string)` returning an error naming the supported modes.
- [ ] 1.2 Emit `-- gopgql:mode=<mode>` immediately after `-- +goose Up` for any mode other than `all`. `all` emits no marker, so existing output stays byte-identical.
- [ ] 1.3 `migrate.FoldContent` reads the marker and returns the mode alongside the schema; a migration with no marker is `ModeAll`.
- [ ] 1.4 Mixed markers within one directory are an error — a directory has one mode.
- [ ] 1.5 Unit tests: round-trip each mode, a marker-less migration folding as `all`, and the mixed-marker error.

## 2. Generation

- [ ] 2.1 `generator.DDL(m, mode)` — table blocks with their indexes, the graph block, or both. `VertexTableDDL`, `EdgeTableDDL`, `IndexDDL` and `GraphDDL` are untouched; the mode selects between existing pieces.
- [ ] 2.2 `migrate.downDDL(m, mode)` — the exact inverse of what the same mode emitted: `tables` drops the tables in reverse order and nothing else, `graph` drops only the graph.
- [ ] 2.3 `migrate.Init(m, mode)` and `WriteInit(dir, m, mode)`.
- [ ] 2.4 Assert byte-identical output for `ModeAll` against the current generator — the backwards-compatibility claim, tested rather than asserted.

## 3. The differ — the part that is easy to get wrong

Design D1: a directory must not keep trying to create the half it does not own.

- [ ] 3.1 `migrate.Delta(from, to, mode)`: `tables` runs the structural diff and **skips** the `GraphDDL(from) != GraphDDL(to)` comparison; `graph` runs the graph comparison and **skips** the structural diff; `all` runs both, as today.
- [ ] 3.2 `migrate.Generate(dir, desired, name)` reads the directory's mode via Fold and uses it, rather than taking it as an argument that could disagree.
- [ ] 3.3 A requested mode that disagrees with the folded mode is `migrate.ErrModeMismatch`, wrapped with both modes named (design D2). A **sentinel**, not a formatted string, because the CLI must branch on it (5.3). **This is the safety property of the change** — the mismatch is what would otherwise emit `CREATE TABLE` into a graph-only directory.
- [ ] 3.4 Unit tests: generating twice against an unchanged schema emits nothing, in each mode; a change confined to the other half emits nothing; the disagreement satisfies `errors.Is(err, migrate.ErrModeMismatch)`; an empty graph-mode directory with no graph declared emits nothing.

## 4. Dropping the graph

- [ ] 4.1 In `graph` mode, a desired schema with no graph against a folded prior that has one emits `DROP PROPERTY GRAPH` and no table statement (design D4).
- [ ] 4.2 Declaring a graph again afterwards recreates it.
- [ ] 4.3 Confirm `all` → `tables` does **not** silently drop the graph: it is a mode disagreement (3.3), not a drop.

## 5. CLI

- [ ] 5.1 `--mode` on `generate` and `migrate`, default `all`, env `GOPGQL_MODE`.
- [ ] 5.2 The help text states that tables must be applied before the graph (design D5).
- [ ] 5.3 A disagreement between `--mode` and the directory exits non-zero with the explanation, not a diff — detected with `errors.Is(err, migrate.ErrModeMismatch)` so it reads differently from a parse or I/O failure.

## 6. Integration suite

Against a real `postgres:19beta2` container, because the ordering constraint and
the failure mode are both database behaviour.

- [ ] 6.1 Generate into two directories (`tables`, `graph`), apply in order, and assert the resulting schema matches a single combined migration applied to a fresh database.
- [ ] 6.2 A query compiles and returns the same rows across the split as against a combined migration.
- [ ] 6.3 Applying the graph directory first fails, and the error names the missing table — the documented failure, asserted rather than assumed.
- [ ] 6.4 Drop the graph from a seeded database in `graph` mode; assert the graph is gone and every row survives.
- [ ] 6.5 Re-declare the graph; assert it is recreated over the surviving tables.
- [ ] 6.6 Regenerating each directory against an unchanged schema emits nothing.

## 7. Docs and verification

- [ ] 7.1 `SPEC.md`: the modes, and that a directory's mode is recorded in its migrations and may not be changed in place.
- [ ] 7.2 `README.md`: the split-migration flow, with the ordering constraint and the "someone else owns the tables" case that motivates it.
- [ ] 7.3 Playground: show the emitted DDL for each mode from the same SDL.
- [ ] 7.4 Full CI green — build, vet, WASM build, the godog suites against containers, `golangci-lint`, `govulncheck`.
