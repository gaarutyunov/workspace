## Why

gopgql writes one migration containing the tables, the indexes **and** the
property graph, and computes the next one from that combined history. That makes
two ordinary situations impossible:

- **Someone else owns the tables.** An existing database, or one managed by
  Atlas / Flyway / Prisma, wants gopgql only for the `CREATE PROPERTY GRAPH`
  mapping — the part nothing else can do.
- **The SDL describes only part of the database.** A database can hold far more
  than a service needs to expose, and the SDL is the description of the slice
  that gets surfaced as a graph. That is a legitimate and probably common way to
  use gopgql: **the SDL as the source of truth for a read-only projection**, not
  as the description of the whole database.

The second case is the one that matters most, and today it is unrepresentable —
gopgql assumes what it does not see does not exist.

## What Changes

- **Generation splits into two directories by default** — `<dir>/tables/` and
  `<dir>/graph/` — producing two migrations instead of one, applied in that
  order.
- **Either half can be turned off**: `--no-tables` (someone else owns them) or
  `--no-graph` (gopgql manages the tables and the graph comes later, or not at
  all).
- **A directory's path is what tells it what it owns.** No mode is recorded in
  the files, no flag has to match what was generated last time, and nothing can
  disagree with anything: `tables/` diffs tables, `graph/` diffs the graph, and
  that is a property of where the file is, not of what is written inside it.
- **The tables half is genuinely optional, not degraded.** With `--no-tables`,
  gopgql never looks at tables at all — it does not diff them, does not drop
  what it cannot see, and does not require the SDL to describe every table in
  the database. The SDL is the projection, not the inventory.
- **Existing projects are migrated, not accommodated.** gopgql is in active
  development, so there is no compatibility layer and no detection of an old
  layout: the split simply *is* the layout. The repo's own artefacts move with
  it — the three examples and the playground demo ship the two halves together
  today, and are updated to the split as part of this change.

## Capabilities

### New Capabilities

- `gopgql-split-migrations`: the two-directory layout, turning either half off,
  and the ordering between them.
- `gopgql-partial-schema`: the SDL as a description of part of a database —
  what gopgql may and may not conclude from a table's absence.

### Modified Capabilities

<!-- gopgql's M1–M6 specs predate OpenSpec and are not under openspec/specs/, so
     there is no existing capability spec to amend. SPEC.md is the project's own
     reference and is updated by this change. -->

## Impact

- **`generator`**: `DDL` gains a way to render the table blocks and the graph
  block separately. The renderers themselves (`VertexTableDDL`, `EdgeTableDDL`,
  `IndexDDL`, `GraphDDL`) are untouched.
- **`migrate`**: `Init`, `Generate` and `Delta` operate on one concern at a
  time. `Delta`'s `GraphDDL(from) != GraphDDL(to)` check runs only for a graph
  directory; the structural diff runs only for a tables directory.
- **`migrate.Fold`** is unchanged. It already reconstructs exactly what a
  directory's migrations created; it simply gets pointed at a narrower
  directory.
- **`cmd/gopgql`**: `--no-tables` / `--no-graph` on `generate` and `migrate`.
- **`test/`**: an integration suite covering the split, the graph-only flow
  against tables gopgql never created, and a database holding tables the SDL
  does not mention.
- **`examples/*`**: `code-graph`, `docs-graph` and `slack-graph` each run one
  `gopgql migrate` producing a combined migration. Each becomes two steps,
  tables then graph, so the examples demonstrate the layout they document.
- **`playground`**: shows one combined DDL output; shows both halves after this.
- **No compatibility layer.** Deliberately — see design D5.
