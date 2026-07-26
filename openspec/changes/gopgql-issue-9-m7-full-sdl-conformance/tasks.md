## 1. `internal/ddl` — teach the reader the statements the writer will emit

Sequenced first on purpose. This is the riskiest change in the milestone: it
touches the parser that reconstructs *all* prior state, so a bug here corrupts
migrations that have nothing to do with M7 (design D3). It also has to land
before anything emits a rename, or the next delta after one is computed from a
wrong prior state.

- [ ] 1.1 Lexer/parser/AST: `ALTER TABLE <t> RENAME TO <u>` and `ALTER TABLE <t> RENAME COLUMN <c> TO <d>` — both currently rejected as unsupported actions (`internal/ddl/parser_test.go:253`).
- [ ] 1.2 Lexer/parser/AST: `ALTER TABLE <t> ADD CONSTRAINT <name> …` and `DROP CONSTRAINT <name>`, covering `CHECK (…)` and `UNIQUE (…)` bodies.
- [ ] 1.3 Lexer/parser/AST: `ALTER TABLE <t> ALTER COLUMN <c> SET DEFAULT …` / `DROP DEFAULT`.
- [ ] 1.4 Round-trip tests for each new statement in `internal/ddl`'s own suite, before anything emits one.
- [ ] 1.5 `migrate.Fold`: visit the new nodes — rename the table/column in the reconstructed model, add/drop the constraint, set/drop the default.

## 2. `sdl` — the four directives

- [ ] 2.1 Prelude: `@default(value: String!)`, `@check(expr: String!) on FIELD_DEFINITION | OBJECT`, `@key(fields: [String!]!) on OBJECT`, `@renamedFrom(name: String!) on OBJECT | FIELD_DEFINITION`.
- [ ] 2.2 Model: `Field` gains `Default`, `Check`, `RenamedFrom`; `Node` gains `Checks []string`, `NaturalKey []string`, `RenamedFrom`.
- [ ] 2.3 Validation — `@key(fields:)` must name declared fields that are scalar columns (not relationships, not `@ignore`d), and must be non-empty; error names the field and the type.
- [ ] 2.4 Validation — `@renamedFrom` must not name a field the same SDL still declares (design D2: that is a contradiction, not a rename). A hint naming something absent from prior state is explicitly *not* an error.
- [ ] 2.5 Validation — `@check(expr:)` must be non-empty. Expression validity is PostgreSQL's job, not ours (design, Non-Goals).
- [ ] 2.6 Unit tests for each rule, including the two "not an error" cases, which are the ones a later refactor is most likely to break.

## 3. `schema` + `generator` — emit it

- [ ] 3.1 `schema.Column` gains `Check`; `schema.VertexTable` gains `Checks []string` (table-level) and `NaturalKey *NaturalKey{ Name string; Columns []string }`.
- [ ] 3.2 Generator: `DEFAULT <value>` on column definitions, emitted verbatim (design D6).
- [ ] 3.3 Generator: column-level `CONSTRAINT <table>_<column>_check CHECK (<expr>)` and table-level `CONSTRAINT <table>_check_<n> CHECK (<expr>)` — named, so a later delta can drop them by name.
- [ ] 3.4 Generator: `CONSTRAINT <table>_key UNIQUE (<cols>)` for the natural key.
- [ ] 3.5 Generator: the natural key's columns appear in the property graph's `KEY (...)` clause for that element, and its properties remain exposed so a `MATCH` can filter on them.
- [ ] 3.6 Confirm the surrogate `id` path is byte-identical for a schema using none of the new directives — the additive claim, asserted rather than assumed.

## 4. `migrate` — diff the new surfaces

- [ ] 4.1 Default added / changed / removed → `ALTER COLUMN … SET DEFAULT` / `DROP DEFAULT`, never a drop-and-add of the column.
- [ ] 4.2 Check added / removed → `ADD CONSTRAINT` / `DROP CONSTRAINT` by the deterministic name.
- [ ] 4.3 Natural key added / changed / removed → drop and re-add the named unique constraint, and regenerate the property graph (graphs are metadata and are already always recreated).
- [ ] 4.4 Renames, hint-driven only: match `@renamedFrom` against the folded prior state and emit `ALTER TABLE … RENAME` / `RENAME COLUMN`; suppress the drop+add pair that would otherwise be emitted for the same objects.
- [ ] 4.5 A hint whose old name is absent from prior state emits nothing (the SDL keeps generating cleanly after the rename has landed).
- [ ] 4.6 `-- +goose Down` is the exact inverse for every new statement.

## 5. `conform` — reflection and structured drift

- [ ] 5.1 New package `conform`, on the `pgx` side of the WASM boundary (`SPEC.md` §4.1). Nothing WASM-safe imports it.
- [ ] 5.2 `Reflect(ctx, db, graphName) (*schema.Schema, error)` — read `pg_propgraph_element`, `pg_propgraph_label`, `pg_propgraph_property` into the same model the generator produces (design D4). A missing graph is a distinct, named error.
- [ ] 5.3 `Check(desired, actual *schema.Schema) Report` — `Report{ Findings []Finding }`, `Finding{ Kind, Element, Property, Want, Got }`, with kinds `MissingElement`, `UnexpectedElement`, `MissingProperty`, `UnexpectedProperty`, `LabelMismatch`.
- [ ] 5.4 Unit tests over hand-built schema pairs for every kind — no container needed, so the comparison logic is tested independently of the reflection.
- [ ] 5.5 Doc comment stating what the check does **not** cover: table-level defaults, checks and indexes are not in `pg_propgraph_*` (design, Risks).

## 6. `cmd/gopgql conform`

- [ ] 6.1 `gopgql conform --sdl <file> --dsn <url> [--graph <name>]`, with the same env fallbacks as the other subcommands.
- [ ] 6.2 Print findings readably; exit non-zero when any exist, zero when none.
- [ ] 6.3 A connection failure is distinguishable from drift — different message, both non-zero.
- [ ] 6.4 Update the usage text and the README.

## 7. `test/m7` — the integration suite (the acceptance criteria)

Every one of these runs against a real `postgres:19beta2` container; the issue's
acceptance list is exactly this section.

- [ ] 7.1 `@check` rejects invalid data **at the database**, and accepts valid data.
- [ ] 7.2 A composite-key (natural-key) vertex is **matchable by `MATCH`**: seed rows, query filtering on the key's properties, assert the returned rows.
- [ ] 7.3 A duplicate natural key is refused by the database.
- [ ] 7.4 `@renamedFrom`: apply `0001`, seed rows, generate and apply the rename delta, assert the migration used `ALTER TABLE … RENAME` (and contains no drop of the old column), and assert **the seeded data survived**.
- [ ] 7.5 Fold correctness across a rename: fold-and-apply versus direct-apply of the same final schema produce identical database schemas (extends the M2 scenario).
- [ ] 7.6 Conformance **passes on a clean database**.
- [ ] 7.7 Conformance **detects deliberately injected out-of-band drift** — drop a property from the graph directly, assert the structured finding names it.
- [ ] 7.8 `@default`: a row inserted without the column gets the declared default.

## 8. Playground, docs and release

- [ ] 8.1 Playground tab: full-expressiveness SDL → generated DDL, running the real compiled Go.
- [ ] 8.2 Playground tab: a conformance report's structure from a fixture, labelled plainly as illustrative because a browser has no database (design D5).
- [ ] 8.3 `SPEC.md` §5: mark the M7 directives as implemented; §4.1: add `conform` to the package table and restate the WASM boundary.
- [ ] 8.4 `README.md`: the four directives, the `conform` subcommand, and the status section.
- [ ] 8.5 Full CI green — `go build ./...`, `go vet ./...`, the WASM build, the whole godog suite against containers, `golangci-lint run ./...`, `govulncheck ./...`.
