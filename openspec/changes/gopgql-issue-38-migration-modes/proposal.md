## Why

gopgql assumes it owns the whole database. Every migration it emits creates the
tables, the indexes **and** the property graph in one file, and the differ
computes the next one from that same combined history.

That assumption fails two real cases the issue names:

- **Someone else owns the tables.** A team with an existing database, or one
  already running Atlas / Flyway / Prisma, wants gopgql for the part nothing else
  can do — the `CREATE PROPERTY GRAPH` mapping — and nothing else. Today the
  only way to get it is to let gopgql generate tables it must not touch.
- **The two halves want different release cadences.** Tables and the graph are
  applied by different people, at different times, or into different migration
  directories. Today they are one file, so they land together or not at all.

There is also a third, quieter case: dropping the graph while keeping the data.
Today that is a hand-written migration, which is exactly the out-of-band edit
`SPEC.md` §3.1 says must not happen.

## What Changes

- **A migration *mode*** selecting which halves of the schema a migration
  directory owns:
  - `all` — tables, indexes and the property graph. **The default, and today's
    behaviour byte for byte.**
  - `tables` — tables and indexes only. No `CREATE PROPERTY GRAPH`.
  - `graph` — the property graph only. No `CREATE TABLE`, no indexes.
- **The mode governs the differ as well as the generator.** This is the part
  that is easy to get wrong: a directory in `tables` mode must not notice that
  the graph is missing and try to create it, and a `graph` directory must not
  try to create the tables it references. Mode partitions *what a directory is
  responsible for*, not just what it prints.
- **The mode is recorded in the migration itself**, so folding a directory does
  not have to be told out of band what it is looking at, and a directory cannot
  silently change mode between runs.
- **`--mode` on `gopgql generate` and `gopgql migrate`**, so the two halves can
  be generated into separate directories and applied in order — tables first,
  graph second.
- **Dropping the graph becomes a supported transition**: pointing a `graph`
  directory at a schema that no longer wants one emits `DROP PROPERTY GRAPH` and
  leaves every table alone.

## Capabilities

### New Capabilities

- `gopgql-migration-modes`: the mode itself — what each mode emits, how a
  directory declares one, and what happens when a directory's mode changes.
- `gopgql-split-migrations`: generating and applying the two halves separately,
  including the ordering constraint between them and the drop-the-graph
  transition.

### Modified Capabilities

<!-- gopgql's M1–M6 specs predate OpenSpec and are not under openspec/specs/, so
     there is no existing capability spec to amend. SPEC.md is the project's own
     reference and is updated by this change. -->

## Impact

- **`generator`**: `DDL` gains a mode so it can emit the table blocks, the graph
  block, or both. `GraphDDL` and `VertexTableDDL` are unchanged — the mode
  selects between existing pieces rather than adding new rendering.
- **`migrate`**: `Init`, `Generate` and `Delta` become mode-aware. `Delta`'s
  `GraphDDL(from) != GraphDDL(to)` check must be skipped entirely in `tables`
  mode, and its structural diff skipped in `graph` mode — otherwise each
  directory keeps trying to create the other's half.
- **`migrate.Fold`**: returns the mode it read alongside the schema. It does not
  filter anything — it reconstructs exactly what the directory's migrations
  created, which for a `graph` directory is a schema with a graph and no tables.
  That is correct, not a defect; it is the *differ* that must be told not to read
  the absence as "create them".
- **`cmd/gopgql`**: `--mode` on `generate` and `migrate`, defaulting to `all`.
- **`test/m*`**: a suite covering the split flow end to end against a real
  container — tables applied from one directory, graph from another, and a query
  working afterwards.
- **Backwards compatibility**: `all` is the default and produces byte-identical
  output, so existing migration directories and existing CI keep working with no
  change and no flag.
