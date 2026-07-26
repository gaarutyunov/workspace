## Context

A first version of this design introduced a `mode` enum recorded in a header
comment inside every migration, a fold that read it back, and a sentinel error
for when a `--mode` flag disagreed with what a directory had been generated
with. The owner's verdict was that it overcomplicated things, and that the split
should simply be the default with either half turnable off.

That is right, and it is worth being precise about *why*, because the machinery
was solving a problem the simpler design does not have.

The marker existed to answer "what is this directory responsible for?" when one
directory might be asked to be different things at different times. If the split
is structural — `tables/` and `graph/` are separate directories, always — then
the answer is the path, and it cannot drift, cannot be mistyped, and cannot
disagree with a flag. **The directory is the mode.** Everything the marker,
the mismatch check and the sentinel error were protecting against becomes
unrepresentable.

The relevant code is unchanged from that analysis: `generator.DDL`
(generator.go:243) concatenates the table blocks and `GraphDDL`; `migrate.Delta`
(diff.go:24) decides whether anything changed with a structural diff plus
`GraphDDL(from) != GraphDDL(to)`; and `migrate.Fold` reconstructs prior state by
re-parsing a directory's own migrations, because gopgql keeps no sidecar state
(`SPEC.md` §3, decision 6).

## Goals / Non-Goals

**Goals:**

- Split by default, with either half turnable off.
- Support an SDL that describes only part of a database, as a first-class case.
- Migrate the repo's own examples and demo to the split, rather than carrying a
  compatibility branch for the old layout.
- Add as little machinery as possible.

**Non-Goals:**

- A mode recorded in migrations. Removed deliberately — see D1.
- Reconciling with another migration tool's state. gopgql reads its own
  migrations and nothing else.
- Managing apply order across directories (D4).

## Decisions

### D1: The directory is the unit of ownership — nothing is recorded in the files

`<dir>/tables/` owns the tables and their indexes. `<dir>/graph/` owns the
property graph. `Fold` is pointed at one of them and reconstructs what that
directory created; `Delta` runs only the comparison that directory is
responsible for:

- a `tables/` directory runs the structural diff and never looks at the graph;
- a `graph/` directory compares the graph and never looks at the tables.

No marker is written, no flag needs to match a previous run, and there is no
disagreement to detect — so there is no mismatch error and no sentinel. A
directory cannot be re-scoped because its identity is its path.

- *Rejected — the previous design's `-- gopgql:mode=` marker.* It bought the
  ability for one directory to be any concern, which nothing needs, and paid for
  it with a marker that hand-editing could lose, a flag that could contradict
  the marker, and an error path for the contradiction.

### D2: Splitting is the default; either half is turned off, not turned on

`gopgql generate --dir migrations` writes `migrations/tables/0001_init.sql` and
`migrations/graph/0001_init.sql`.

- `--no-tables` — do not generate or diff the tables half at all.
- `--no-graph` — do not generate or diff the graph half at all.

Off means **absent, not empty**: with `--no-tables` gopgql never inspects tables,
so it emits nothing about them and, critically, never concludes anything from
their absence (D3).

Turning off is not a way to delete anything. `--no-graph` stops managing the
graph; it does not drop one. Dropping the graph is what happens when the graph
half is *on* and the SDL stops declaring a graph — the ordinary diff of a
`graph/` directory against a graphless desired state.

### D3: The SDL describes a projection, not an inventory

This is the owner's second point and the more important half of the change: a
database may hold much more than the SDL mentions, with the SDL acting as the
source of truth for the read-only slice that is surfaced as a graph.

So **absence in the SDL is not evidence of absence in the database.** A `graph/`
directory must never emit `DROP TABLE` for a table it does not know about, and
must not require the SDL to enumerate every table. This falls out of D1 rather
than needing enforcement — a graph directory has no structural diff — but it is
stated because it is the guarantee people are relying on when they use gopgql
this way, and a future change that "helpfully" widened the graph directory's
diff would silently break it.

It also means a `tables/` directory is only safe to use when the SDL *is* the
whole story for the tables it describes. That is already true today; the split
does not change it.

### D4: Ordering is the operator's, and is documented rather than enforced

Tables must exist before a graph that references them. gopgql cannot know
whether the tables are about to be applied by another tool a second later, so it
applies the directory it is given and the docs and help text state the order. The
failure when they are applied out of order is PostgreSQL refusing to create a
graph over a missing table — loud, immediate, and pointing at the cause.

### D5: No compatibility layer — the split is the layout, and existing artefacts move

An earlier draft kept writing combined migrations into any `--dir` that already
contained them, so that no existing project had to change. The owner's call was
to drop that: gopgql is in active development, there are no external users whose
applied history has to be preserved, and a permanent detection branch is a
permanent cost paid for a temporary problem.

So there is **no detection, no compatibility mode and no flag** for the old
layout. Generation always splits (unless a half is turned off), and the repo's
own artefacts are migrated as part of this change rather than grandfathered:

- `examples/code-graph`, `examples/docs-graph`, `examples/slack-graph` each run a
  single `gopgql migrate … --dir /tmp/migrations` in their compose file, which
  applies both halves in one step. Each becomes two steps — tables, then graph —
  so the examples demonstrate the ordering they describe rather than hiding it.
- The playground presents one combined DDL output; it presents both halves after
  this.

This is the reason the change is cheap. Had there been applied histories to
preserve, splitting them would have meant renaming migrations goose has already
recorded — which is the thing you cannot safely do, and which is exactly why it
is worth doing now rather than later.

## Risks / Trade-offs

- **[The output layout changes for everyone]** — two directories where there was
  one, so anything hard-coding `migrations/0001_init.sql` breaks. This is
  accepted rather than mitigated (D5): gopgql is pre-1.0 and in active
  development, and the alternative is a detection branch carried forever. The
  repo's own examples and playground are updated in this change, and the README
  and SPEC state the new layout.
- **[Two directories, two goose histories]** — each has its own version table
  scope, so a partial apply can leave tables ahead of the graph. That is
  inherent to wanting them separately releasable, and it is the reason the
  ordering is documented (D4).
- **[A `tables/` directory still assumes the SDL is complete for its tables]** —
  D3's guarantee is about the graph half. Someone who turns tables *on* against
  a database with tables the SDL does not mention is in the same position as
  today, which the docs should say plainly rather than leaving to be discovered.
- **[Nothing detects a half-applied split]** — gopgql will not warn that the
  graph directory is ahead of the tables one. Detecting that is what M7's
  conformance check (gopgql#9) is for, and it should not be duplicated here.
