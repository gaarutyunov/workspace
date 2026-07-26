## 1. Split the generator

- [ ] 1.1 `generator.TablesDDL(m)` — the vertex and edge table blocks with their indexes, in today's order.
- [ ] 1.2 `generator.GraphDDL(m)` already exists and is unchanged.
- [ ] 1.3 `generator.DDL(m)` stays as it is — `TablesDDL` + `GraphDDL` — so the combined path (existing directories, D5) is literally the same code producing byte-identical output.
- [ ] 1.4 Test: `TablesDDL(m) + "\n\n" + GraphDDL(m)` equals `DDL(m)` exactly.

## 2. Per-concern migrations

- [ ] 2.1 `migrate.InitTables(m)` / `migrate.InitGraph(m)`, each with a down section undoing only its own half (tables in reverse creation order; the graph drop alone).
- [ ] 2.2 `migrate.DeltaTables(from, to)` — the structural diff only; never touches the graph.
- [ ] 2.3 `migrate.DeltaGraph(from, to)` — the `GraphDDL` comparison only; never emits a table statement.
- [ ] 2.4 `migrate.Delta` keeps its current combined behaviour for existing directories.
- [ ] 2.5 Unit tests: each delta emits nothing when its own half is unchanged, including when the *other* half changed.

## 3. Directory layout

- [ ] 3.1 `<dir>/tables/` and `<dir>/graph/`, each an independent goose directory with its own `0001_init.sql` and numbering.
- [ ] 3.2 Fold is per-directory and needs no change — point it at `<dir>/graph/` and it reconstructs what that directory created (design D1).
- [ ] 3.3 **Layout detection (D5):** if `<dir>` contains migration files directly, write combined into `<dir>` as today; if it is empty or already contains `tables/` / `graph/`, use the split. One check on directory contents — no marker, no config.
- [ ] 3.4 Tests: an existing combined directory keeps receiving combined migrations and its files are not moved; an empty directory gets the split.

## 4. CLI

- [ ] 4.1 `--no-tables` and `--no-graph` on `generate` and `migrate`, defaulting to both halves on.
- [ ] 4.2 Both flags together is an error — that asks for nothing to be generated.
- [ ] 4.3 Help text states that tables are applied before the graph (design D4).
- [ ] 4.4 `migrate` applies the half or halves it was asked for, in goose order within each directory.

## 5. The partial-schema guarantee

The point of the change, per the issue: the SDL as the source of truth for a
read-only projection of a larger database.

- [ ] 5.1 With `--no-tables`, no code path inspects, diffs or emits anything about tables. Assert this rather than assuming it — it is the guarantee people rely on.
- [ ] 5.2 An SDL describing a subset of a database generates a graph over exactly that subset, with no complaint about what it does not mention.
- [ ] 5.3 Document the asymmetry plainly: with the tables half **on**, a column absent from the SDL is a column gopgql removes; the partial-description guarantee is about the graph half.

## 6. Integration suite

Against a real `postgres:19beta2` container.

- [ ] 6.1 Split generation, applied tables-then-graph, produces the same database as a combined migration applied to a fresh database.
- [ ] 6.2 A query returns the same rows across the split as against a combined migration.
- [ ] 6.3 Applying the graph directory first fails, and the error names the missing table.
- [ ] 6.4 **Graph over foreign tables:** create tables by hand (not via gopgql), generate with `--no-tables`, apply, and query successfully.
- [ ] 6.5 **Partial projection:** a database with extra tables *and* extra columns the SDL never mentions — assert no migration refers to them, and that they still exist after applying.
- [ ] 6.6 The SDL stops declaring a graph → the graph directory drops it and every row survives.
- [ ] 6.7 Regenerating against an unchanged schema emits nothing, in both directories.
- [ ] 6.8 An existing combined directory keeps working: apply `0001`, change the schema, regenerate, and confirm the delta lands in the same directory in combined form.

## 7. Docs and verification

- [ ] 7.1 `SPEC.md`: the split default, turning either half off, and the partial-schema guarantee with its asymmetry.
- [ ] 7.2 `README.md`: the two motivating cases — someone else owns the tables, and the SDL as a read-only projection — with the ordering constraint.
- [ ] 7.3 Playground: show both migrations generated from one SDL.
- [ ] 7.4 Full CI green — build, vet, WASM build, the godog suites against containers, `golangci-lint`, `govulncheck`.
