## Context

Three functions carry the assumption that gopgql owns everything, and all three
have to change together.

`generator.DDL` (generator.go:243) builds the table blocks with their indexes and
then appends `GraphDDL(m)` — one string, both halves.

`migrate.Init` wraps that in `-- +goose Up` and pairs it with `downDDL`, which
drops the graph, then the edge tables, then the vertex tables.

`migrate.Delta` (diff.go:24) decides whether anything changed with two tests:
the structural diff, and `generator.GraphDDL(from) != generator.GraphDDL(to)`.

And underneath them, `migrate.Fold` reconstructs prior state by re-parsing the
directory's own migrations, because gopgql keeps no sidecar state
(`SPEC.md` §3, decision 6).

## Goals / Non-Goals

**Goals:**

- Emit only the half of the schema a directory is responsible for.
- Keep the differ correct when it can only see half the history.
- Make dropping the graph a generated migration rather than a hand-written one.
- Change nothing for anyone who does not ask for a mode.

**Non-Goals:**

- Reconciling with another migration tool's state. gopgql reads its own
  migrations and nothing else; if Atlas owns the tables, gopgql in `graph` mode
  simply never looks at them.
- Splitting anything finer than tables-versus-graph. Per-table directories are
  not asked for and would multiply the fold problem below by the table count.
- Managing apply order across directories. That is the operator's, and the docs
  say so.

## Decisions

### D1: The mode partitions responsibility, not just output

The tempting implementation is a filter on `generator.DDL` — emit the graph
block or don't. That is half the change, and the missing half is where the bug
would live.

`migrate.Delta` compares a folded prior state against the desired state. In
`tables` mode the folded prior has **no graph**, because no migration in that
directory ever created one — so `GraphDDL(from) != GraphDDL(to)` is true on
every single run, and every delta would try to create a graph the directory does
not own. Symmetrically, a `graph` directory folds to a schema with no tables, so
the structural diff would emit `CREATE TABLE` for every table on every run.

So the mode is carried into the differ:

- `tables` — run the structural diff; **skip the graph comparison entirely**.
- `graph` — run the graph comparison; **skip the structural diff entirely**.
- `all` — both, exactly as today.

The mode answers "what is this directory responsible for?", and the generator
filter falls out of that rather than being the point.

### D2: The mode is recorded in the migration, not passed in every time

A directory generated in `graph` mode and then diffed without `--mode graph`
would produce nonsense — the differ would see no tables in the prior state and
emit `CREATE TABLE` for all of them. Relying on the operator to pass a matching
flag every time makes data loss a typo away.

So the emitted migration records its own mode in a header comment that the fold
reads back:

```sql
-- +goose Up
-- gopgql:mode=graph
CREATE PROPERTY GRAPH …
```

`Fold` returns the mode alongside the schema. Rules:

- A directory whose migrations declare a mode uses it; `--mode` may be omitted.
- `--mode` **disagreeing** with the recorded mode is an **error**, not an
  override. Silently re-scoping a directory is how the tables get dropped. It is
  a **named error** (`migrate.ErrModeMismatch`), not just a formatted string,
  because the CLI has to tell it apart from an ordinary generation failure to
  report it usefully — the operator's next action is different in each case.
- A migration with no marker is `all` — every migration generated before this
  change, which is what keeps existing directories working.

- *Alternative — a `.gopgql.yaml` beside the migrations.* Rejected: a second
  file to keep in sync with the directory, and it can be deleted or copied
  without the migrations noticing. A marker inside the artefact travels with it.

### D3: `graph` mode still needs the whole SDL

A property graph names its tables and their columns, so the graph half cannot be
rendered from a "graph-only" model. This is not a problem: the SDL always
describes the entire schema, and `generator.Build` always produces the whole
`schema.Schema`. The mode filters what is **emitted** and what is **diffed**,
never what is parsed.

That means a `graph` directory does need an SDL that matches the tables somebody
else owns. If it drifts, the graph will reference a column that is not there and
PostgreSQL will reject the migration — which is the right failure, at the right
moment, and is the case M7's conformance check exists to catch earlier.

### D4: Dropping the graph is a mode-level transition, and only `graph` mode may do it

"Or even drop the whole graph table setup but keep the data" is a transition
between desired states within `graph` mode: the SDL no longer wants a graph, the
folded prior has one, so the delta is `DROP PROPERTY GRAPH` and nothing else.

Deliberately **not** supported: `all` → `tables` as an implicit drop. A directory
switching from `all` to `tables` is far more likely to be a mistake than a
request to drop the graph, and D2 already makes a mode change an error. Someone
who genuinely wants the graph gone points a `graph`-mode directory at a
graphless schema, which says so explicitly.

### D5: Ordering between directories is the operator's, and is stated rather than enforced

Tables must exist before the graph that references them. gopgql could try to
enforce this — refuse to apply a `graph` directory when the tables are absent —
but it cannot know whether the tables are about to be applied by another tool a
second later, and a check that is sometimes wrong is worse than a documented
constraint.

So: `migrate` applies the directory it was given, in goose order, and the docs
and the `--mode graph` help text state that tables come first. The failure when
they do not is PostgreSQL refusing to create a graph over a missing table —
loud, immediate, and pointing at the actual cause.

## Risks / Trade-offs

- **[A mismatched flag is the dangerous input]** — running `generate --mode all`
  against a `graph` directory would emit `CREATE TABLE` for everything. D2 turns
  that into an error rather than a diff, which is the single most important
  safety property in this change.
- **[Split directories can drift from each other]** — the `graph` half's SDL
  must agree with tables it does not own. Detecting that early is exactly what
  M7's conformance check does, so the docs point at it rather than duplicating
  it here.
- **[The marker is a comment]** — a hand-edited migration could lose it, and the
  directory would silently become `all`. Mitigated by the mismatch check in D2
  (a `--mode` that disagrees errors) and by the fact that hand-editing generated
  migrations is already out of contract (`SPEC.md` §3.1).
- **[Three modes, three fold behaviours]** — more paths through `Delta`. Kept
  small by making the mode select which of the two *existing* comparisons run,
  rather than introducing new diff logic.

## Open Questions

- Should `gopgql conform` (M7, gopgql#9) be mode-aware — checking only the graph
  when the graph is all gopgql owns? Probably yes, and it is a one-line filter,
  but M7 is unmerged and this change should not pre-empt its shape.
