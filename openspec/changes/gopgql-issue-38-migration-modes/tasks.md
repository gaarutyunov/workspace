> **Amended.** This list replaces the one merged in gaarutyunov/workspace#33.
> The two-directory layout, the per-half version tables and the lockstep applier
> are removed; see design.md — **Amendment**.

## 1. Split the generator

- [ ] 1.1 `generator.TablesDDL(m)` — the vertex and edge table blocks with their indexes, in today's order.
- [ ] 1.2 `generator.GraphDDL(m)` already exists and is unchanged.
- [ ] 1.3 `generator.DDL(m)` is retained as `TablesDDL` + `GraphDDL` for the tests that assert the two halves compose, not as a shipping layout (D7 — there is no combined output any more).
- [ ] 1.4 Test: `TablesDDL(m) + "\n\n" + GraphDDL(m)` equals `DDL(m)` exactly, so the split provably loses nothing.

## 2. Single-purpose migration renderers

Three renderers, each emitting one kind of statement, each with a down section
that is the plain inverse of its own up section (D2).

- [ ] 2.1 `migrate.DeltaTables(from, to)` — the structural diff only; never emits a property-graph statement. Up is the delta, down its inverse.
- [ ] 2.2 A graph-teardown renderer — up is `DROP PROPERTY GRAPH IF EXISTS <from.GraphName>`, down re-creates `from`'s definition. Nothing table-related in either direction.
- [ ] 2.3 A graph-build renderer — up is `CREATE PROPERTY GRAPH` for `to`, down drops it. Nothing table-related in either direction.
- [ ] 2.4 No renderer combines a drop and a create in one file, including for a graph-only change (D2, rejected alternative).
- [ ] 2.5 Unit tests: each renderer emits nothing when its own concern is unchanged, including when the *other* concern changed; and every down section is the exact inverse of its up section.

## 3. Generation emits a sequence, into one directory

- [ ] 3.1 Generation returns the ordered sequence of migrations for one edit of the SDL rather than a single file: graph-down, tables, graph — the graph-down omitted when the folded history has no graph, and each of the other two omitted when it has nothing to say or its half is off (D2's table).
- [ ] 3.2 Versions are consecutive integers assigned in emission order, each above the highest already in the directory. No gaps within a generation, no timestamps.
- [ ] 3.3 File names are `NNNN_<slug>_graph_down.sql`, `NNNN_<slug>_tables.sql`, `NNNN_<slug>_graph.sql`, with **one slug per generation** shared by all of its files (D2). The suffix is for humans — nothing reads it back (D1).
- [ ] 3.4 Everything is written into `--dir` itself. **No subdirectories** — and delete the per-half directory constants, the shared generation counter (`NextVersion`), the fold-up-to-version (`FoldUpTo`), the version listing (`Versions`) and the per-half version table (`VersionTable`). Deleting them is the task; each exists only to enforce an order that is now structural.
- [ ] 3.5 **No layout detection (D7).** Generation always emits the sequence; there is no branch for the combined layout or for the two-directory one, and no flag that restores either.
- [ ] 3.6 Test: generating into a directory that holds old combined migrations, or old `tables/` + `graph/` subdirectories, still produces the sequence, with no special-casing.

## 4. Fold

- [ ] 4.1 A history with no `CREATE PROPERTY GRAPH` folds to the tables as created, and `DeltaTables` classifies them as vertices or edges against the desired schema (D6). Assert the diff's ordering guarantees still hold — edges created after, and dropped before, the vertices they reference.
- [ ] 4.2 A property graph over tables the history never created folds with nil columns rather than failing (D6) — the partial-schema case, not a corruption.
- [ ] 4.3 `DROP PROPERTY GRAPH` in the folded history clears the graph, so folding the directory yields the definition created *last*. That is what the next graph-teardown migration's down section is rendered from.
- [ ] 4.4 Unit tests for all three, driven from migration text rather than from an in-memory model.

## 5. CLI

- [ ] 5.1 `--no-tables` and `--no-graph` on `generate` and `migrate`, defaulting to both halves on.
- [ ] 5.2 Both flags together is an error — that asks for nothing to be generated.
- [ ] 5.3 The flags scope generation only. `migrate`'s apply step is `goose up` over the whole directory against the default `goose_db_version` table — no `SetTableName`, no version walk, no per-half apply. Delete the lockstep applier.
- [ ] 5.4 Help text states that a generation emits consecutive single-purpose migrations into one directory, applied in that order (D3).
- [ ] 5.5 Implement the flags-versus-history check (D4a): a flag contradicting the folded history is a sentinel error at generate time, in both directions — `--no-graph` against a history containing a `CREATE PROPERTY GRAPH`, and `--no-tables` against a history that created tables. Nothing is written when it fires.
- [ ] 5.6 The error message names the deliberate path for the legitimate case: to drop the graph, generate from a desired schema that declares no graph, which emits the `_graph_down` teardown and no rebuild. Test the message, not only the error.
- [ ] 5.7 Test the agreeing case in both directions — a directory whose first generation turned a half off keeps generating with that half off, because the flag and the history agree.

## 6. The partial-schema guarantee

The point of the change, per the issue: the SDL as the source of truth for a
read-only projection of a larger database.

- [ ] 6.1 With `--no-tables`, no code path inspects, diffs or emits anything about tables. Assert this rather than assuming it — it is the guarantee people rely on.
- [ ] 6.2 An SDL describing a subset of a database generates a graph over exactly that subset, with no complaint about what it does not mention.
- [ ] 6.3 Document the asymmetry plainly: with the tables half **on**, a column absent from the SDL is a column gopgql removes; the partial-description guarantee is about the graph half.

## 7. Integration suite

Against a real `postgres:19beta2` container, driving the real CLI binary rather
than a re-implementation of the apply order.

- [ ] 7.1 One generation, applied with `goose up`, produces the same database as a combined migration applied to a fresh database.
- [ ] 7.2 A query returns the same rows across the split as against a combined migration.
- [ ] 7.3 **Replay from zero.** Three generations, each changing the tables *and* the graph — including one that drops a column an earlier graph exposed — then the whole directory applied to an empty database. This is the regression test for the defect that caused this amendment; it fails against the two-directory design.
- [ ] 7.4 **A tables-only generation between two graph generations.** A change no graph statement mentions (an index) must not desynchronise anything, and replay from zero must still succeed.
- [ ] 7.5 **Idempotent re-run.** `gopgql migrate` against an already-migrated database emits nothing, applies nothing, and leaves the property graph in place.
- [ ] 7.6 **Rollback.** Rolling the most recent generation's migrations back, newest first, restores the previous tables and the previous property-graph definition.
- [ ] 7.7 **Graph over foreign tables:** create tables by hand (not via gopgql), generate with `--no-tables`, apply, and query successfully.
- [ ] 7.8 **Partial projection:** a database with extra tables *and* extra columns the SDL never mentions — assert no migration refers to them, and that they still exist after applying.
- [ ] 7.9 The SDL stops declaring a graph → the next generation drops it and every row survives.
- [ ] 7.10 Regenerating against an unchanged schema emits nothing.
- [ ] 7.11 Each example comes up end to end under `docker compose up`, with the graph queryable afterwards.

## 8. The repo's own artefacts

- [ ] 8.1 The examples' single `init` service — `gopgql migrate --sdl … --dir /tmp/migrations` — stays **one step** in `examples/code-graph`, `examples/docs-graph` and `examples/slack-graph`. If the merged design's two-step split was already applied to them, revert it. The comment explaining the ephemeral `--dir` needs no change.
- [ ] 8.2 Each example README describes the sequence a generation emits, and that one `migrate` applies it in order.
- [ ] 8.3 Playground: show the sequence of migrations from one SDL, rather than one combined output.

## 9. Docs and verification

- [ ] 9.1 `SPEC.md`: one directory, one history, the sequence a generation emits, turning either half off, and the partial-schema guarantee with its asymmetry. Remove the per-half version tables and the pairwise apply order — they are withdrawn (design — **Amendment**).
- [ ] 9.2 `README.md`: the two motivating cases — someone else owns the tables, and the SDL as a read-only projection — and that `gopgql migrate` is a plain forward apply.
- [ ] 9.3 Full CI green — build, vet, WASM build, the godog suites against containers, `golangci-lint`, `govulncheck`.
