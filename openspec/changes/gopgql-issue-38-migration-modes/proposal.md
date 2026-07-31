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

Separating the two concerns is therefore the point of the change. **How** they
are separated turned out to matter as much as that they are. The version of this
change that was merged gave each half its own directory and its own goose
history, and implementing it showed that gopgql then has to interleave those two
histories itself — otherwise a historical `CREATE PROPERTY GRAPH` is replayed
against tables that have since moved on. That orchestration is reversed here in
favour of goose's own ordering: one directory, one history, and each generation
emitting consecutive migrations that each do one thing. See
[design.md](./design.md) — **Amendment**.

## What Changes

- **Generation emits several single-purpose migrations instead of one mixed
  migration**, into **one** directory, numbered consecutively. No migration ever
  contains both table DDL and property-graph DDL.
- **A generation is a run of consecutive files in dependency order.** With a
  property graph already in the history and table work to do:
  `NNNN_<slug>_graph_down.sql`, `NNNN+1_<slug>_tables.sql`,
  `NNNN+2_<slug>_graph.sql`. The first generation is `tables` then `graph`; a
  graph-only generation is the `graph_down` / `graph` pair.
- **Ordering is goose's, not gopgql's.** `gopgql migrate` is `goose up` over that
  one directory against the one `goose_db_version` table. No per-half version
  table, no lockstep walk between directories, no apply ordering implemented in
  gopgql at all — the order is the file numbering, and the numbering is
  chronological by construction.
- **Either half can be turned off**: `--no-tables` (someone else owns them) or
  `--no-graph` (gopgql manages the tables and the graph comes later, or not at
  all). The flags scope what is **generated**; what is **applied** is always the
  whole directory in version order. A directory's ownership only ever **grows**:
  turning off a half its history owns is an error rather than a silent re-scoping,
  and of the two halves only the **graph** may start being owned later. Turning
  the **tables** half on over a history that never owned tables is an error too,
  because the graph is derivable from the SDL while a table migration is a diff
  with no truthful prior to diff against (design D4a).
- **The tables half is genuinely optional, not degraded.** With `--no-tables`,
  gopgql never looks at tables at all — it does not diff them, does not drop
  what it cannot see, and does not require the SDL to describe every table in
  the database. The SDL is the projection, not the inventory.
- **Existing projects are migrated, not accommodated.** gopgql is in active
  development, so there is no compatibility layer and no detection of an earlier
  layout — neither the original combined migration nor the two directories.

## Capabilities

### New Capabilities

- `gopgql-split-migrations`: table DDL and graph DDL in separate, consecutively
  numbered migrations in one directory, the order a generation emits them in,
  and turning either half off. (The capability keeps the name it was merged
  under; the split is now per migration rather than per directory.)
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
- **`migrate`**: generation returns the **sequence** of migrations for one edit
  of the SDL rather than a single file. Three single-purpose renderers: the
  structural delta (tables and indexes, never the graph), the graph teardown
  (`Up` drops the graph the history last created, `Down` re-creates it), and the
  graph build (`Up` creates the graph the SDL now describes, `Down` drops it).
  Every graph drop is `DROP PROPERTY GRAPH IF EXISTS`.
- **`migrate.Fold`** is *not* unchanged — the merged version of this change said
  it was, and that was wrong. It builds its model *from* the
  `CREATE PROPERTY GRAPH` statement, so a history holding only one half was a
  hard error: a tables-only history has no graph to classify its tables with,
  and a graph over tables the history never created has no columns to resolve
  against. Both are first-class now (design D6). Fold must also replay
  `DROP PROPERTY GRAPH` as clearing the graph, because the history now contains
  drops between the creates.
- **`cmd/gopgql`**: `--no-tables` / `--no-graph` on `generate` and `migrate`, with
  sentinel errors where the flags contradict the folded history (D4a) — either
  half turned **off** over a history that owns it, and the **tables** half left on
  over a history that never owned tables; `migrate`'s apply step is `goose up` on
  the one directory.
- **Deleted relative to the merged design**: the per-half version tables
  (`goose_db_version_tables` / `goose_db_version_graph`), the shared generation
  counter that kept the two halves' numbering aligned, folding a directory only
  up to a given version, listing a directory's applied versions, and the
  lockstep applier that walked the two halves. All of it existed to enforce an
  order that is now structural.
- **`test/`**: an integration suite covering the emitted sequence, replay from
  zero across several generations, the graph-only flow against tables gopgql
  never created, and a database holding tables the SDL does not mention.
- **`examples/*`**: unchanged. `code-graph`, `docs-graph` and `slack-graph` each
  run one `gopgql migrate … --dir /tmp/migrations`, and that one step still
  applies everything in the right order — which is the point of the amendment.
- **`playground`**: shows one combined DDL output; shows the sequence of
  migrations after this.
- **No compatibility layer.** Deliberately — see design D7.
