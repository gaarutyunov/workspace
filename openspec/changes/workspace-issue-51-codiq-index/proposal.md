## Why

`gaarutyunov/workspace#51`, in full:

> Use codiq to index all projects in the repo.
> Expose them with gopgql.
> Add settings and connect to it.
> Test it, compare the results to gortex.

Four sentences, three systems. Most of the work of this change was establishing
which of the four are already true.

### Three of the four are already built

`projects/codiq` at `origin/main` (`c11e46b`) is not a prototype that needs a
Postgres story invented for it. It **is** the story:

| Sentence | State |
|---|---|
| "Use codiq to index" | `cmd/codiq` walks a tree, parses 11 languages with gotreesitter, and loads SCIP-style occurrences into PostgreSQL 19 as vertex/edge tables. M1–M9 merged. |
| "Expose them with gopgql" | `deploy/docker-compose.yml` already runs `gopgql-mcp --sdl schema/codiq.graphql` against that database. gopgql owns the schema, the `CREATE PROPERTY GRAPH` view and the MCP surface, by codiq's `SPEC.md` §8 and Decision 8. |
| "Add settings and connect to it" | Nothing exists. `.mcp.json` registers `gortex` and nothing else. |
| "Test it, compare to gortex" | Nothing exists. |

So the interesting question is not "how do we get codiq's index into a SQL/PGQ
property graph" — it has been there since M1. It is **"what breaks when one
database holds twenty repositories instead of one"**, because that is the one
thing the issue asks for that codiq has never done.

### What breaks: there is no corpus

codiq's `SPEC.md`, its SDL and its compose file all say the same thing, in
their own words, unprompted:

- `schema/codiq.graphql` on `file.path`: *"Indexed rather than UNIQUE on
  purpose: uniqueness of a path is a property of a **corpus**, and the corpus
  boundary is not modelled in M1."*
- `store/sqlc/query.sql`: `FileIDByPath` is `SELECT id FROM file WHERE path =
  @path`. File identity is the repo-relative path and nothing else.
- `deploy/docker-compose.yml`, on why the demo indexes a two-file fixture and
  not codiq's own source: indexing a repo that shares a path with the seeded
  corpus *"replaces that seeded file's rows, and the demo's edge disappears
  (**measured, not assumed**)"*.

Twenty repositories in one database therefore collapse on every shared
repo-relative path — `main.go`, `cmd/root.go`, `src/index.ts` — each index run
deleting the previous repo's facts for that path. That alone would make the
gortex comparison measure a graph that is missing rows for reasons that have
nothing to do with extraction quality.

A second collision sits underneath it and is not fixed by a file column.
`coord.Resolve` walks **upward** from the indexed directory until it finds a
manifest, with no repository bound. Seven of the twenty trees under `projects/`
carry no manifest a codiq resolver reads, and on this machine the first one
above them is `/Users/germanarutyunov/package.json`. Every manifest-less repo
would therefore be stamped with the *same* coordinate and the same `Root`, so
their SCIP descriptors would be byte-identical for same-named symbols — and the
link pass joins on the descriptor and nothing else, so it would materialise
cross-repository `resolves_to` and `calls` edges that do not exist. That is the
exact defect `coord`'s own doc comment says the per-ecosystem `Set` exists to
prevent, reintroduced one level up.

**Corpus isolation has to reach the descriptor, not only the file row.** That is
the technical core of this change.

### And the comparison needs a method, or it is worthless

"Compare the results to gortex" invites a write-up in which the new thing wins.
gortex is a mature daemon with ~40 task-shaped tools; gopgql's MCP surface is
**two** tools (`introspect`, `query`) over hand-written GraphQL, with a default
traversal depth limit of 3. A comparison that picks its questions after seeing
the results can prove anything. This change therefore **pre-registers** the
corpus, the questions, the answer key and the pass/fail thresholds before either
system is run, and commits them.

## What Changes

- **codiq gains a corpus.** A `corpus` identity on `file`, part of file
  identity and of the coordinate prefix; `coord.Resolve` bounded by the
  repository root. One codiq milestone, delivered under this issue.
- **The workspace declares which projects are indexed**, in a committed config
  file, and drives codiq over them repeatably.
- **The workspace connects to the graph** — a `codiq` entry in `.mcp.json` and
  its permission in `.claude/settings.json`, beside `gortex`.
- **A pre-registered comparison** against gortex: pinned commits, a committed
  question set, a hand-authored answer key independent of both systems, stated
  metrics and a stated decision rule; then the run, then the report.

### Capabilities

1. `workspace-codiq-corpus-isolation` — one database, many repositories, no
   cross-repository collision or false edge.
2. `workspace-codiq-index-run` — which projects are indexed, how, and how a
   re-index is made repeatable.
3. `workspace-codiq-mcp-settings` — the settings that connect this workspace to
   the graph.
4. `workspace-code-index-comparison` — the falsifiable gortex comparison.

## Impact

- Affected specs: the four capabilities above.
- Affected code: `projects/codiq` (`coord/`, `store/`, `schema/`, `index/`,
  `cmd/codiq`, `schema/migrations/`) for capability 1; this repository
  (`.mcp.json`, `.claude/settings.json`, and a new `codiq/` directory holding
  the project list, the driver and the comparison fixtures) for 2–4.
- **Not affected: gopgql.** See Open Question 3 and design D10 — this change
  needs nothing gopgql does not already ship, and in particular does **not**
  depend on `gopgql#47`.

## Open Questions

Each carries a recommendation. None is decided here.

### Q1. Does codiq replace gortex, or sit beside it?

The issue does not say, and the whole change reads differently either way. If
codiq is a replacement, the comparison is a go/no-go gate and the settings work
ends with removing `gortex` from `.mcp.json`. If it sits beside, the comparison
is a characterisation and both stay registered.

**Recommendation: beside, and say so in the change.** gortex today supplies
~40 task-shaped tools, LSP integration, dataflow, clone detection, blame
enrichment and session memory; codiq supplies a structural navigation core over
two generic MCP tools. Replacement is not on the table on capability grounds
this year, and framing it as a bake-off makes the comparison's purpose
dishonest. The comparison's stated purpose should be *"is codiq a viable second
source for structural navigation, and where is it already better"* — a question
with a real answer. **Both stay registered; the agent is told which to reach
for.**

### Q2. Which projects?

`projects/` holds twenty trees. They are not comparable: `pglite` is 1.4 GB,
`postgres-pglite` 1.1 GB (a PostgreSQL fork — by far the largest C corpus here,
and it carries no manifest codiq reads), `workout` 766 MB, `agentiq` 248 KB of
documents with no code at all. Seven have no resolvable manifest in their
working tree. "All" is not a well-defined instruction.

**Recommendation: a declared list of eight, committed as config, not "all".**
`codiq`, `gopgql`, `sysgo`, `mcp-anything`, `epos` (Go); `ui-kit`, `boids`,
`site-review` (JS/TS). Rationale: they span the two ecosystems both systems
index well, every one has a resolvable manifest, together they are ~40 MB of
walked source after codiq's `node_modules`/`vendor`/dot-dir pruning, and they
are the repos this workspace actually works in — so a bad answer is one a human
here can spot. `postgres-pglite` and `pglite` are explicitly deferred to a
second run once the eight are green: they are where scale problems will surface,
and they should not be the run that also debugs the corpus column. The list is
config, so extending it is an edit, not a change.

### Q3. Where does Postgres come from?

**This is not academic: `/System/Volumes/Data` has 490 MiB free, 100% used.**
`postgres:19beta2` alone does not fit, before any data.

**Recommendation: codiq's own `deploy/docker-compose.yml`, unmodified, and a
hard disk gate before the milestone that runs it.** Reusing codiq's compose
means the workspace configures nothing about Postgres and inherits the pinned
`postgres:19beta2`, the `codiq_dbos` database and the read-only MCP service
already proven in codiq's CI. PGlite is not an option — SQL/PGQ is a server
feature and gopgql's PGlite work (`gopgql#31`) is itself blocked. An existing
instance is not an option — there is no PostgreSQL 19 on this machine. The gate
is stated in `tasks.md` as a numbered precondition with a measured floor rather
than left as a footnote, because every milestone from M2 on is unrunnable
without it.

### Q4. Does the codiq corpus work land under this issue, or as a codiq issue?

Capability 1 is a change to codiq's data model — its SDL, a migration, file
identity and coordinate resolution. The board forbids splitting an issue into
sub-issues, but this is a different repository, and `Blocked` exists for an
issue waiting on another issue.

**Recommendation: land it under this issue, as M1, as its own PR in
`gaarutyunov/codiq` referenced from #51.** It is not separable work — nothing
else in #51 is correct without it, so filing it separately would park #51 in
`Blocked` behind an issue that exists only because #51 exists. Filing it in
codiq would also be right if codiq wanted a corpus for its own reasons; it does
not — codiq's `SPEC.md` deliberately leaves the corpus unmodelled, and this
change is the first caller that needs one.
