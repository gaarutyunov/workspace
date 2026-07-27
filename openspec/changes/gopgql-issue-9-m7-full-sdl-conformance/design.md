## Context

The SDL is the single source of truth for both halves of gopgql (`SPEC.md` §1),
so every widening lands in two places at once: the DDL the generator emits, and
the model the compiler queries against. M6 widened the *mapping* surface
(`@column`, `@index`, `@unique`). M7 widens the *constraint* surface and then
adds the check that proves the database still matches.

Three facts about the code as it stands (read at `321a230`) shape every decision
below.

**The surrogate key is load-bearing, not incidental.** `sdl.validateKey` requires
every `@node` type and every interface to declare `id: ID!` — "surrogate uuid
keys only". The compiler depends on that in three separate places:
`compiler.go:344` projects `alias.id` as each level's hidden key column,
`:453` projects it again as the branch join key when M5 splits a multi-pattern
query, and `:586` uses it for the isomorphism guards. `shape.Rows` groups the
flat rows by that one key column to deduplicate parents. `generator.go:214-220`
builds every edge table as `source_id`/`target_id` `REFERENCES <table>(id)`.

**The fold parser rejects renames.** `migrate.Fold` reconstructs prior state by
re-parsing gopgql's own emitted migrations with `internal/ddl`, and that parser
lists `ALTER TABLE … RENAME TO` as an *unsupported action*
(`internal/ddl/parser_test.go:253`).

**`schema.Column` already carries `Default` and `Unique`**, but there is nowhere
to put a check constraint or a natural key.

## Goals / Non-Goals

**Goals:**

- Four directives that let the SDL describe a schema, not just a graph.
- A rename that preserves data, and that the fold can read back.
- A conformance check whose output a program can act on, not just a human.
- Every claim proven against a real `postgres:19beta2` container.

**Non-Goals:**

- Replacing the surrogate key (D1).
- Inferring renames. A rename is only ever a rename because the SDL said so.
- Validating `@check` expressions. gopgql is not going to grow an SQL expression
  parser; PostgreSQL rejects a bad one at migration time, which is the right
  place and the right error.
- Repairing drift. The check reports; deciding what to do about it is the
  operator's.

## Decisions

### D1: `@key(fields:)` is a **natural key alongside** the surrogate id, not a replacement

This is the milestone's central question and the one most likely to be answered
wrongly by reflex. "Composite keys flow into `KEY (...)` clauses and
multi-column `SOURCE KEY`/`DESTINATION KEY`" (`SPEC.md` §7) reads like an
instruction to make composite keys *the* identity. It should not be.

- *Alternative A — `@key` replaces `id` as the physical identity.* Every one of
  the three `id` sites in the compiler becomes a multi-column projection; each
  level's hidden key becomes a tuple; `shape` has to group by a composite key
  rather than a single column; every edge table becomes a multi-column foreign
  key with `SOURCE KEY (a, b)`; and the M5 branch join, which joins on one
  projected id, becomes a multi-column join with the isomorphism guards
  rewritten to match. That is a rewrite of the query half of the library, landed
  in the milestone whose stated purpose is *SDL expressiveness*, and it would
  put M8's shaping benchmark on ground that just moved.
- **Chosen — B: `@key` is a named multi-column uniqueness constraint over
  existing scalar properties.** The surrogate `id` remains the physical identity
  and the thing edges reference. The natural key becomes a `UNIQUE` constraint
  in the table DDL and its columns are listed in the property graph's `KEY (...)`
  clause, so a `MATCH` can select on them and PostgreSQL knows they identify a
  row.

The exit criterion is "a composite-key vertex is **matchable by `MATCH`**", and
B satisfies it exactly: the key's columns are graph properties, and a query
filtering on them compiles and returns the right rows. A takes on the identity
rewrite that criterion never asked for.

If a future milestone genuinely needs keyless vertex tables, A is still open —
and it will be a milestone of its own, with the compiler and the shaper in
scope. Recorded as an open question rather than pretended away.

### D2: A rename is a hint, never an inference

The differ sees "column `email` disappeared, column `contact` appeared". It
cannot know whether that is a rename or a genuine drop-and-add, and guessing
wrong destroys data one way or loses it the other. So `@renamedFrom` is the only
thing that makes it a rename: the field carries `@renamedFrom(name: "email")`,
the differ matches the hint against the prior state, and emits
`ALTER TABLE … RENAME COLUMN`. With no hint, the old behaviour stands.

A hint that names something not present in the prior state is **not** an error —
it is a no-op, because the same SDL has to keep generating cleanly after the
rename has already been applied. A hint that names a field which *still exists*
in the SDL **is** an error: that is a contradiction, not a rename.

### D3: The fold has to learn to read a rename back — the invisible half

Emitting `ALTER TABLE … RENAME` is the easy half and, on its own, actively
harmful. `migrate.Fold` reconstructs prior state by parsing the migrations
gopgql emitted, and `internal/ddl` rejects `RENAME` today. Ship the emitter
alone and the *next* delta is computed against a prior state where the rename
never happened: the differ sees the old column still there and emits a drop, and
the rename's data goes with it.

So `internal/ddl` grows the statements first, and the fold visitor with them:
`ALTER TABLE … RENAME TO`, `ALTER TABLE … RENAME COLUMN … TO`, and
`ADD`/`DROP CONSTRAINT`. `M2`'s fold-correctness scenario — apply the folded
output, apply the same final schema directly, assert the resulting schemas are
identical — is extended to cover a rename, so this cannot regress silently.

This is why the tasks put `internal/ddl` before the differ rather than after.

### D4: Drift is structured, and it is a diff of two models

The reflection reads `pg_propgraph_element`, `pg_propgraph_label` and
`pg_propgraph_property` into the *same* `schema.Schema` shape the generator
produces from SDL. The check is then a comparison of two values of one type,
not a comparison of a model against a database.

That matters for what comes out. A `Report` carries typed `Finding`s — a kind
(`MissingElement`, `UnexpectedElement`, `MissingProperty`, `UnexpectedProperty`,
`LabelMismatch`), the element and property names, and what each side said — so a
caller can branch on the kind. A string diff would force every consumer to parse
English back into structure, and CI would be matching on prose.

- *Alternative — reflect into a bespoke struct and compare field by field.*
  Rejected: it duplicates the schema model, and the two would drift from each
  other, which is a poor look for a drift detector.

### D5: `conform` is a package on the pgx side, and a CLI subcommand

`SPEC.md` §4.1 draws a hard line: `sdl`, `schema`, `generator`, `migrate` and
`compiler` have no database dependency and compile to WASM. Reflection needs a
live connection, so it cannot live in any of them. It gets its own package,
`conform`, alongside `exec`, and nothing WASM-safe imports it.

`gopgql conform --sdl … --dsn …` prints the findings and **exits non-zero when
any are present**, so it works as a CI step without a wrapper. The playground
shows the report's *shape* using a fixture, since a browser has no database —
and the docs say so rather than implying the playground is talking to one.

### D6: `@check` gets a home in the schema model; `@default` mostly already has one

`schema.Column.Default` exists, so `@default` is a generator and differ concern:
emit `DEFAULT <value>`, and treat a changed default as an `ALTER COLUMN … SET/DROP
DEFAULT` rather than a drop-and-add.

`@check` has nowhere to go, so `Column` gains `Check` and `VertexTable` gains a
`Checks` list for the table-level form. Both render as named constraints —
`<table>_<column>_check`, `<table>_check_<n>` — because an anonymous constraint
cannot be dropped by a later delta without reflecting the name PostgreSQL
invented.

The value in `@default(value:)` and the expression in `@check(expr:)` are
**emitted verbatim** into DDL. They are schema-author input, not user input, and
they are already arbitrary SQL by definition; quoting them would make them
useless. The risk is recorded below rather than hidden.

## Risks / Trade-offs

- **[`@check` and `@default` are raw SQL]** — they go into DDL as written. This
  is a deliberate escape hatch (`SPEC.md` §2.3 notes the same pattern in
  `graphql-to-sql`'s `@sql`), and the threat model is that whoever writes the
  SDL already controls the schema. It would be indefensible for *user* input and
  is documented as such.
- **[The rename fold is the risky change]** — it touches the parser that
  reconstructs all prior state, so a bug there corrupts migrations that have
  nothing to do with renames. Mitigated by landing it first, behind the extended
  fold-correctness scenario, and by round-tripping every new statement in
  `internal/ddl`'s own tests before the differ ever emits one.
- **[Conformance is only as good as the catalogs]** — `pg_propgraph_*` exposes
  elements, labels and properties, not check constraints, defaults or indexes.
  So the check covers *graph* drift and is explicit that it does not cover
  table-level drift; claiming otherwise would be worse than the gap.
- **[Natural keys and the surrogate id can disagree]** — nothing stops two rows
  sharing a natural key if the constraint is added to a table that already
  violates it; PostgreSQL rejects the migration, which is the correct failure
  and is left to it.
- **[Playground fidelity]** — the conformance tab shows a fixture-driven report
  rather than a live one, because there is no database in a browser. The risk is
  someone reading it as a live check; the tab says so plainly.

## Open Questions

- Should keyless vertex tables (Alternative A in D1 — a natural key as the *only*
  identity) be a later milestone? It needs the compiler's three `id` sites, the
  shaper's grouping, and edge-table references all to become multi-column. Not
  in M7.
- Should `conform` also check table-level objects (defaults, checks, indexes) by
  reflecting `information_schema` alongside the graph catalogs? It would close
  the gap named above, but it widens the milestone; M7 covers the graph.
