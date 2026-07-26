## Why

gopgql's SDL is expressive enough to describe a graph but not enough to describe
a *schema*: there is no way to say a column has a default, no way to constrain
what it may hold, no way to identify a row by anything but the surrogate `id`,
and no way to rename anything without the differ reading it as drop-and-add and
destroying the data. M7 is the milestone that closes those four gaps
(`SPEC.md` §7).

It also closes the assumption the whole design rests on. `SPEC.md` §3.1 is
explicit that folding migrations is only sound because **"no one hand-edits a
generated migration or alters the database out of band"** — and names the
conformance check as the guard for exactly that. Until it exists, that
assumption is unguarded, and the further the SDL widens the more there is to
drift.

## What Changes

- **`@default(value:)`** on a field — the column's DDL default, emitted on
  create and on add-column, and diffed when it changes.
- **`@check(expr:)`** on a field or a type — a `CHECK` constraint, column-level
  or table-level, enforced by the database rather than by the application.
- **`@key(fields: [String!]!)`** on a type — a **natural key**: a named,
  multi-column uniqueness constraint over existing scalar properties, matchable
  in a query. It does **not** replace the surrogate `id` (design D1); this is
  the one place the milestone deliberately narrows what "composite key" could
  have meant, and the reasoning is written down rather than assumed.
- **`@renamedFrom(name:)`** on a type or a field — a rename hint, so the differ
  emits `ALTER TABLE … RENAME` instead of dropping a column and adding another.
  **This requires extending `internal/ddl`**: the fold parser today rejects
  `ALTER TABLE … RENAME` as an unsupported action, so emitting one without
  teaching the parser to read it back would corrupt the *next* delta.
- **A conformance check** — reflect `pg_propgraph_element`,
  `pg_propgraph_label` and `pg_propgraph_property` from a live database and
  compare against the schema the SDL describes, reporting **structured drift**
  (typed findings a caller can branch on) rather than a text diff.
- **`gopgql conform`** — the CLI subcommand that runs it against a DSN and exits
  non-zero on drift, so it can sit in someone's CI.
- **Playground**: a full-expressiveness tab showing the widened DDL, and a
  conformance-report tab showing the structured shape, both running the real
  compiled Go.

No breaking changes: every directive is additive, and a schema that uses none of
them generates byte-identical DDL to today.

## Capabilities

### New Capabilities

- `gopgql-sdl-constraints`: the `@default` and `@check` directives — column
  defaults and database-enforced constraints, column-level and table-level.
- `gopgql-natural-keys`: the `@key(fields:)` directive — a multi-column natural
  key alongside the surrogate id, its DDL, and its queryability.
- `gopgql-rename-hints`: the `@renamedFrom` directive — rename-preserving
  migrations, including the fold that has to read them back.
- `gopgql-conformance`: reflecting the live property graph and reporting
  structured drift against the SDL model, plus the CLI that runs it.

### Modified Capabilities

<!-- The gopgql specs (M1–M6) predate OpenSpec and are not in openspec/specs/,
     so there are no existing capability specs to amend. The surfaces this
     change widens are covered by the new capabilities above; SPEC.md §5 and §7
     remain the project's own reference and are updated by this change. -->

## Impact

- **`sdl`**: four new directives in the prelude, parsed into the mapping model;
  `Field` gains a default and a check, `Node` gains checks and a natural key,
  and both gain a rename hint. Validation grows: a `@key` must name real scalar
  properties, a `@check` must be non-empty, and a `@renamedFrom` must not name a
  field that still exists.
- **`schema`**: `Column` already carries `Default`; new is a `Check` on the
  column, a table-level `Checks` list, and a `NaturalKey` on `VertexTable`.
- **`generator`**: emits `DEFAULT`, `CHECK` and the natural-key constraint;
  the property graph gains the natural key's columns as a `KEY (...)`.
- **`migrate`**: the differ learns renames (guided by the hint, never inferred)
  and constraint add/drop; `Fold` must round-trip both.
- **`internal/ddl`**: the lexer, parser and AST learn `ALTER TABLE … RENAME
  TO`, `RENAME COLUMN … TO`, and `ADD`/`DROP CONSTRAINT` — without which the
  fold silently reconstructs the wrong prior state.
- **`conform`** (new package): reflection + structured drift. It needs a
  database, so it sits on the `pgx` side of the WASM boundary
  (`SPEC.md` §4.1) and nothing WASM-safe may import it.
- **`cmd/gopgql`**: a third subcommand, `conform`.
- **`test/m7`** (new suite) and the playground/docs.
- **Backwards compatibility**: additive. Existing SDL parses unchanged, existing
  migrations fold unchanged, and the surrogate `id` contract the compiler and
  shaper depend on is untouched.
