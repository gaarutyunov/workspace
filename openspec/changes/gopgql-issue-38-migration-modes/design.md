## Context

This design has been through three shapes, and the two discarded ones are worth
keeping in view because each was discarded for a reason that still constrains the
current one.

**A `mode` marker in the files.** The first version recorded a `mode` enum in a
header comment inside every migration, folded it back when reading a directory,
and raised a sentinel error when a `--mode` flag disagreed with what a directory
had been generated with. The owner's verdict was that it overcomplicated things,
and that the split should simply be the default with either half turnable off.

**A directory per half.** The second version — the one merged as spec PR
gaarutyunov/workspace#33 — made the split structural instead: `<dir>/tables/` and
`<dir>/graph/`, each an independent goose directory, so the answer to "what is
this directory responsible for?" was its path and could not drift, be mistyped,
or contradict a flag. That reasoning was sound as far as it went, but it stopped
at generation. Two independent histories have to be *applied*, and once there is
more than one generation the order is not simply "tables then graph" — see
**Amendment** below.

**One directory, goose's own ordering.** What replaces it, and what the rest of
this document describes: one directory, one `goose_db_version` table, and each
generation emitting consecutive migrations that each do exactly one thing. The
ordering the second version had to implement in Go becomes a property of the file
numbering.

The relevant code: `generator.DDL` (generator.go:243) concatenates the table
blocks and `GraphDDL`; `migrate.Delta` (diff.go:24) decides whether anything
changed with a structural diff plus `GraphDDL(from) != GraphDDL(to)`; and
`migrate.Fold` reconstructs prior state by re-parsing a directory's own
migrations, because gopgql keeps no sidecar state (`SPEC.md` §3, decision 6).

## Amendment (owner, gaarutyunov/gopgql#38)

This change was already merged (spec PR gaarutyunov/workspace#33) and
implemented (code PR gaarutyunov/gopgql#40). Implementation surfaced a defect in
the merged design, and the owner's review directed a different fix from the one
the implementation had reached for:

> Fix what you found. Migrations must be enforced to go in proper order.
> Probably we should just use native goose ordering instead of inventing this
> additional thing. Migrations can go in same folder but go one after another
> instead of having same 1 migration for graph and table.

**The defect.** A graph migration names the columns of *its own* generation. Two
directories replayed one after the other therefore run `graph/0001`'s
`CREATE PROPERTY GRAPH` against tables `tables/0002` has already changed, and
PostgreSQL refuses it — verified during implementation:
`column "salary" does not exist (SQLSTATE 42703)`. The merged design's D4 said
ordering was the operator's and only needed documenting; that is true of *one*
generation and false of every one after it.

**What the implementation did, and what this amendment reverses.** It kept the
two directories and made gopgql interleave them: a separate goose version table
per half (`goose_db_version_tables` / `goose_db_version_graph`), a shared
generation counter so the two halves' numbers meant the same edit of the SDL, a
fold that could stop at a given version, and an applier that walked the halves in
lockstep — graph *n-1* down, tables *n* up, graph *n* up, per generation. It
worked, and it was gopgql re-implementing what a migration tool already does.

All of that is **removed** from this design:

- the two directories become one;
- the two version tables become the one `goose_db_version`;
- the shared generation counter, the fold-up-to-version, the version listing and
  the lockstep applier are deleted — `gopgql migrate` is `goose up`;
- the merged D4 ("ordering is the operator's, and is documented rather than
  enforced") is **withdrawn**, and replaced by D3 below: the order is enforced,
  by the file numbering, for every generation.

**What survives unchanged**, because none of it is what the owner rejected: the
`--no-tables` / `--no-graph` flags, which are issue #38's actual requirement; the
partial-schema guarantee (D5); the two `Fold` defects implementation uncovered
and their fixes (D6); and `DROP PROPERTY GRAPH IF EXISTS` wherever the graph is
dropped.

**Two gaps this amendment opened, and how the owner closed them.** Drafting it
turned up a hole the merged design also had: with the flags scoping generation, a
`--no-graph` run against a history that already creates a graph emits table DDL
that runs against a live graph depending on the columns it alters. The owner's
call was to generalise the fix rather than special-case it — a flag may not take
away a half the directory's history owns, for either half (D4a) — and, on the
second question drafting raised, that a generation carries one slug shared by all
of its files (D2). Both are settled below, as decisions — nothing about either is
left for implementation to choose.

**Correction to D4a (spec review, 2026-07-30).** The paragraph above used to say
the fix was symmetric and that a flag may not change which halves a directory owns
"in either direction". It was not, and D4a's body and its scenarios only ever
covered turning a half *off*. The on direction was left unspecified, so the
implementation settled it unilaterally: it allowed every turn-on and tested only
the safe one. A spec review caught that by running the code. **The rule is
asymmetric**, and D4a below now states it in full — a directory that never owned
the graph half may start owning it, a directory that never owned the tables half
may not. This is a correction to an already-merged change, made so that the rule
lives in the spec rather than in the code that guessed it.

## Goals / Non-Goals

**Goals:**

- Table DDL and graph DDL never in the same migration.
- The correct order **enforced**, for every generation, with no ordering logic in
  gopgql: `goose up` from zero must reproduce the current schema.
- Either half turnable off.
- Support an SDL that describes only part of a database, as a first-class case.
- Add as little machinery as possible — and delete the machinery the merged
  design needed.

**Non-Goals:**

- A mode recorded in migrations. Removed deliberately — see D1.
- Reconciling with another migration tool's state. gopgql reads its own
  migrations and nothing else.
- gopgql owning apply order. goose owns it (D1, D3).
- More than one goose version table.

## Decisions

### D1: One directory, one goose history, and `migrate` is `goose up`

`gopgql generate --dir migrations` writes into `migrations/` itself. No
subdirectories, one `goose_db_version` table, and the apply step is goose's
ordinary `up` over that directory. gopgql contributes nothing to how migrations
are applied — only to what is written, and to the order it is numbered in.

Nothing is recorded inside the files: no mode marker, no half marker, no sidecar
state. A file's suffix (`_tables`, `_graph`, `_graph_down`) is a human-readable
name, not data that anything reads back. What a migration does is what its SQL
does — and that is also the only thing a flag is ever checked against (D4).

- *Rejected — the first design's `-- gopgql:mode=` marker.* It bought the ability
  for one directory to be any concern, which nothing needs, and paid for it with
  a marker hand-editing could lose, a flag that could contradict the marker, and
  an error path for the contradiction.
- *Rejected — the merged design's `tables/` and `graph/` directories.* See
  **Amendment**. Their virtue (the path is the mode) was real; their cost was a
  second history to keep in step, which is the thing goose exists to do.

### D2: A generation emits consecutive single-purpose migrations

One edit of the SDL produces a **run** of files, numbered consecutively, each
holding one kind of statement:

| Situation | Files emitted |
| --- | --- |
| Table work, a graph already in the history | `NNNN_<slug>_graph_down.sql`, `NNNN+1_<slug>_tables.sql`, `NNNN+2_<slug>_graph.sql` |
| First generation (no graph yet) | `NNNN_<slug>_tables.sql`, `NNNN+1_<slug>_graph.sql` |
| Graph-only change, a graph already in the history | `NNNN_<slug>_graph_down.sql`, `NNNN+1_<slug>_graph.sql` |
| Graph-only change, no graph yet | `NNNN_<slug>_graph.sql` |
| `--no-graph` | the `_tables` file only |
| `--no-tables` | the graph file(s) only |

Each file's `Down` is the inverse of its own `Up`, and nothing else:

- `_graph_down` — `Up` is `DROP PROPERTY GRAPH IF EXISTS <name>`; `Down`
  re-creates the definition the history held before this generation.
- `_tables` — `Up` is the structural delta (create / alter / drop tables and
  indexes); `Down` is its inverse.
- `_graph` — `Up` is `CREATE PROPERTY GRAPH` for the definition the SDL now
  describes; `Down` drops it.

So `goose down` three times walks a generation back out in exactly reverse order
— new graph dropped, tables reverted, previous graph restored — which the merged
design's two independent directories could not do at all.

**One slug per generation, shared by all of its files**: `0003_add_email_graph_down.sql`,
`0004_add_email_tables.sql`, `0005_add_email_graph.sql`. The generation is the
readable unit, and `0003` reads correctly as "the graph-teardown step of the
`add_email` generation".

- *Rejected — a slug derived per file from what that file does.* The teardown and
  the rebuild make no schema change of their own, so per-file slugs would have to
  invent names for them, and the run would stop reading as one unit in a directory
  listing.

- *Rejected — folding a graph-only change into one drop-and-create file.* It would
  not mix concerns either, and it would be one file instead of two. But then a
  file's shape depends on what kind of change produced it, and the `Down` of a
  drop-and-create is a create-and-drop — the only place in the layout where a
  `Down` is not the plain inverse of its `Up`. Uniformity is worth the extra file.
- *Rejected — timestamps for versions.* Sequential integers assigned in emission
  order are what make "consecutive" meaningful, and they keep a generation's files
  adjacent and legible in a directory listing.

### D3: Ordering is structural, so replay from zero is correct by construction

This is the whole reason for the amendment, so it is stated as the property to
preserve rather than as a mechanism.

Every migration lives in one directory, numbered in true chronological order, and
each one operates on the schema the migrations before it produced. A
`CREATE PROPERTY GRAPH` is therefore always immediately preceded — in the same
run of files — by the table DDL of *its own* generation, and always preceded by
the drop of the graph the generation before it built. `goose up` against an empty
database replays the whole history correctly because there is no other order in
which it could apply the files.

Contrast the merged design: replaying `graph/` from zero re-runs historical
`CREATE PROPERTY GRAPH` statements against tables that have since moved on, which
is why it needed a lockstep applier. **The constraint that design enforced in Go
code is now a property of where the files are and what they are numbered.** No
code can forget it, and there is no code to test for having forgotten it.

The failure mode this leaves is the ordinary one: if migrations are hand-written
or hand-reordered so that a graph precedes its tables, PostgreSQL refuses to
create a graph over a missing table — loud, immediate, and pointing at the cause.

### D4: Splitting is the default; either half is turned off, not turned on

`--no-tables` — generate nothing about the tables. `--no-graph` — generate nothing
about the graph. Both together is an error: it asks for nothing.

Off means **absent, not empty**: with `--no-tables` gopgql never inspects tables,
so it emits nothing about them and, critically, never concludes anything from
their absence (D5).

The flags scope **generation only**. Applying is always `goose up` over the whole
directory — a flag can never cause part of an existing history to be skipped,
which is precisely the class of bug the per-half version tables created.

Turning a half off is not a way to delete anything. `--no-graph` stops managing
the graph; it does not drop one. Dropping the graph is what happens when the graph
half is *on* and the SDL stops declaring one: that generation emits a
`_graph_down` file and no `_graph` file.

### D4a: A directory never stops owning a half, and only the graph half may start

**The rule, in the sentence the docs should carry: turning a half *off* over a
history that owns it is refused, for either half; turning the *tables* half on
over a history that never owned tables is refused; turning the *graph* half on is
allowed.** A directory's ownership is a ratchet with one tooth — it can gain the
graph half, and it can never lose either half.

Every refusal is a **sentinel error at generate time** — sentinel because the CLI
branches on it to print the guidance below — and nothing is written when one
fires.

**Off, either half — refused.** A flag that disowns a half the folded history owns
contradicts what the directory demonstrably is:

- `--no-graph` against a history that contains a `CREATE PROPERTY GRAPH` → error.
  The alternative is table DDL running against a live graph that may depend on the
  columns it alters.
- `--no-tables` against a history that created tables → error, for the same
  reason read the other way round: subsequent table DDL would silently not be
  emitted, and the graph half would eventually name a column nothing creates.

**The graph half on, over a history that never owned one — allowed.** The graph is
derivable from the SDL alone. gopgql needs nothing out of the history to render a
`CREATE PROPERTY GRAPH`: the definition *is* what the SDL now describes. So the
generation emits a lone `_graph` build — no teardown, because there is no graph in
the history to tear down, and no `_tables` file, because the tables half is still
off. Nothing about the directory's past has to be reconstructed for that to be
correct, so nothing about it can be got wrong. This is the obviously-wanted
transition: a project that used gopgql for its tables alone deciding it now wants
the graph.

**The tables half on, over a history that never owned tables — refused.** The
tables are *not* derivable from the SDL, because a table migration is a **diff**
and a diff needs a prior. A directory that never owned tables folds to a prior
whose vertex and edge tables carry **nil columns** — that is the intended
partial-schema fold of D6, intended precisely because the history does not
describe those tables. `columnDiff` therefore reads every column the SDL declares
as new and emits `ALTER TABLE … ADD COLUMN` for columns that already exist.
Reproduced during the spec review: the apply fails with `column "id" of relation
"documents" already exists`, and by then the same generation's `_graph_down`
migration has already committed — so the database is left with no property graph
*and* a directory that can never be applied forward again. Refusing at generate
time costs nothing; discovering it at apply time costs the graph.

**Why the two on-directions differ**, stated because without the reason the
asymmetry reads as arbitrary and the next reader will "simplify" it back into
symmetry: **the graph is derivable from the SDL and the tables are not.** A graph
build is a rendering of the desired state; a tables migration is a diff against a
prior, and for a half the history never owned there is no truthful prior to diff
against.

The error message must name the deliberate path in each case:

- `--no-graph` on a graph-bearing directory. The one legitimate reason to want it
  is **to drop the graph**, and the way to do that is an ordinary generation whose
  desired schema declares no graph. That emits the `_graph_down` teardown and no
  rebuild — a graph transition the operator asked for, recorded in the history,
  and reviewable in the diff.
- `--no-tables` on a tables-bearing directory. gopgql already owns those tables;
  handing them to something else is a migration out of gopgql, not a flag.
- The tables half on over a history that never owned tables. The way to have
  gopgql own the tables is **a fresh `--dir`**, whose first generation owns both
  halves and emits a full baseline the operator reviews and reconciles against the
  database as it stands — rather than a partial diff that silently assumes the
  columns are not there.

This is **not** the mode-mismatch error of the first design returning (D1). That
one compared a flag against a marker written inside the files, so the marker could
be lost or hand-edited into disagreeing with the SQL beside it. Here there is
nothing recorded and nothing to drift: the evidence is the SQL in the directory,
folded the same way generation folds it anyway.

- *Rejected — allowing the tables half on and letting the apply fail.* This is what
  shipped before this correction, because the merged D4a did not say. It is the
  worst option available: the failure lands at apply time against a live database,
  after the generation's `_graph_down` has committed, leaving a database without
  its property graph and a directory that cannot go forward. It is the same
  argument as the rejected alternative below, with a worse blast radius.
- *Rejected — refusing both on-directions, for symmetry with the off-direction.*
  Symmetry is not a reason on its own. It would forbid the one transition that is
  both safe and obviously wanted, and buy nothing: the graph build reconstructs
  nothing, so there is nothing for it to get wrong.
- *Rejected — `--no-graph` suppresses only the `_graph` build and still emits the
  `_graph_down` teardown.* It makes a flag silently destroy a property graph. The
  principle is this change's own, stated in the spec-approval comment on
  gaarutyunov/gopgql#38 of 2026-07-26 and not objected to — never ratified as an
  owner ruling, and it survives the amendment on its merits: dropping the graph is
  never an implicit consequence of changing what a directory manages, because that
  is far more likely to be a mistake than a request.
- *Rejected — emit the tables file and let the apply fail.* It trades a gopgql
  error at generate time, before anything is written, for a PostgreSQL error at
  apply time against a live database. Strictly worse, and it leaves a migration on
  disk that can never be applied.

### D5: The SDL describes a projection, not an inventory

This is the owner's second point on the issue, and the more important half of the
change: a database may hold much more than the SDL mentions, with the SDL acting
as the source of truth for the read-only slice that is surfaced as a graph.

So **absence in the SDL is not evidence of absence in the database.** A graph
migration must never carry a `DROP TABLE` for a table it does not know about, and
generation must not require the SDL to enumerate every table. With `--no-tables`
no structural diff runs at all, so this falls out of D4 rather than needing
enforcement — but it is stated because it is the guarantee people rely on when
they use gopgql this way, and a future change that "helpfully" widened the graph
half's diff would silently break it.

It also means the tables half is only safe to use when the SDL *is* the whole
story for the tables it describes. That is already true today; the split does not
change it.

### D6: Fold must survive a history that holds only one half

The merged design asserted that `Fold` was unchanged. Implementation proved
otherwise, and the two defects it found are independent of the directory layout,
so they carry over verbatim:

- **A history with no `CREATE PROPERTY GRAPH`** (everything generated with
  `--no-graph`). Fold classifies each table as a vertex or an edge *from* the
  graph statement, so with no graph there is nothing to classify with, and it
  failed outright. A graph-less fold now returns the tables as created, and the
  structural delta classifies them against the desired schema — the only place
  those roles are recorded. The diff's ordering guarantees survive: edges are
  still dropped before the vertices they reference and created after them, and a
  table whose role genuinely changed is dropped and re-created, which is correct.
- **A graph over tables the history never created** (everything generated with
  `--no-tables`). The graph references tables Fold has never seen, and it failed
  resolving their columns. It now folds with nil columns — the partial-schema case
  working as intended (D5), not a corruption. Those nil columns are also the exact
  reason D4a refuses to let the tables half start being owned later: a delta
  against a prior with no columns is a delta that re-adds every column.

One thing is new here: the history now contains `DROP PROPERTY GRAPH` statements
*between* the creates, so Fold has to replay a drop as clearing the graph. Fold
the whole directory and the folded graph is the last one created — which is
exactly what generation needs in order to render the next `_graph_down` file's
`Down`.

### D7: No compatibility layer — this layout is the layout

An early draft kept writing combined migrations into any `--dir` that already
contained them, so that no existing project had to change. The owner's call was to
drop that: gopgql is in active development, there are no external users whose
applied history has to be preserved, and a permanent detection branch is a
permanent cost paid for a temporary problem.

So there is **no detection, no compatibility mode and no flag** for any earlier
layout — not the original single combined migration, and not the `tables/` +
`graph/` pair the merged design described. Generation always emits the sequence of
D2 into the one directory.

The repo's own artefacts need *less* work than the merged design assumed, which is
itself a signal that the amendment is right:

- `examples/code-graph`, `examples/docs-graph` and `examples/slack-graph` each run
  a single `gopgql migrate … --dir /tmp/migrations` in their compose file. That
  stays one step. Under the merged design it had to become two ordered steps —
  and, once there was more than one generation, two steps would not have been
  enough.
- The playground presents one combined DDL output; it presents the sequence of
  migrations after this.

This is the reason the change is cheap. Had there been applied histories to
preserve, re-laying them out would have meant renumbering migrations goose has
already recorded — which is the thing you cannot safely do, and which is exactly
why it is worth doing now rather than later.

## Risks / Trade-offs

- **[The output layout changes for everyone]** — several numbered files where
  there was one, so anything hard-coding `migrations/0001_init.sql` breaks. This
  is accepted rather than mitigated (D7): gopgql is pre-1.0 and in active
  development, and the alternative is a detection branch carried forever. The
  README and SPEC state the new layout.
- **[Three files per generation instead of one]** — the migration log is longer,
  and reviewing a schema change means reading a run of files rather than one.
  Mitigated by naming: one shared slug per generation plus a suffix saying what
  each file does, so a generation reads as a unit in a directory listing. The
  compensation is that each file is separately reversible and separately legible.
- **[A generation is not atomic]** — goose runs each file in its own transaction,
  so an interrupted `goose up` can stop between the `_graph_down` and the `_graph`
  file, leaving a database whose tables have moved and which has no property
  graph. Re-running `goose up` closes the window, and queries against the graph
  fail loudly in the meantime rather than returning wrong rows. This is strictly
  better than the merged design, where the same interruption left two histories at
  different versions with nothing to detect it — but it is not nothing, and
  deployments that read the graph should finish migrating before serving.
- **[The tables half still assumes the SDL is complete for its tables]** — D5's
  guarantee is about the graph half. Someone who turns tables *on* against a
  database holding tables the SDL does not mention is in the same position as
  today, which the docs should say plainly rather than leaving to be discovered.
- **[The tables half cannot be adopted into an existing directory]** — D4a refuses
  it, so a project that started with `--no-tables` and later wants gopgql to own
  its tables has to start a fresh `--dir` rather than flipping a flag. That is a
  real cost, accepted because the alternative is a generation that emits
  `ALTER TABLE … ADD COLUMN` for columns that already exist and takes the property
  graph down on its way to failing. The graph half, which needs no prior, has no
  such restriction.
- **[Hand-editing can still break the order]** — the design makes the correct
  order structural for everything gopgql generates, not for whatever a human
  writes into the directory afterwards. A graph migration renumbered below the
  tables it depends on fails at apply time, not at generation time.

