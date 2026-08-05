## Context

Line references are to `gaarutyunov/codiq` at `origin/main` `c11e46b` and
`gaarutyunov/gopgql` at `origin/main` `060922e`, read from those refs and not
from the base checkouts, which are stale.

What already exists, established by reading rather than assumed:

- codiq loads a SCIP-style occurrence graph into PostgreSQL 19 vertex/edge
  tables (`store/`, `schema/codiq.graphql`, `schema/migrations/`), links
  cross-file edges by descriptor match (`link/`), orchestrates with DBOS
  (`index/dbos.go`), and spills map-phase facts to protobuf artifacts
  (`artifact/`). Eleven languages: go, ts, py, rs, java, cs, rb, php, c, cpp,
  kt.
- gopgql owns codiq's schema, the `CREATE PROPERTY GRAPH` view and the read
  surface. `deploy/docker-compose.yml` runs `gopgql migrate --dir /migrations`
  and `gopgql-mcp --sdl /schema/codiq.graphql`, the latter on
  `127.0.0.1:8080` with `GOPGQL_PATH` defaulting to `/mcp`.
- `gopgql-mcp` advertises exactly two tools, `introspect` and `query`
  (`mcp/server.go:35-37`), and opens its pool with
  `default_transaction_read_only=on`.
- gopgql is tagged `v0.1.0`; codiq's `deploy/gopgql.Dockerfile` still builds
  from a pinned source commit because no ghcr image was pushed.

What does not exist: any notion of a corpus, any workspace-side settings, any
comparison.

## Goals / Non-Goals

**Goals**

- One PostgreSQL database holding many repositories' facts with no collision
  and no false cross-repository edge.
- A declared, repeatable index run over a named set of this workspace's
  projects.
- This workspace's agents able to query that graph through MCP, configured
  the way `gortex` is configured.
- A comparison against gortex whose result could have come out unfavourable,
  and whose numbers a third party can recompute.

**Non-Goals**

- Replacing gortex (Open Question 1).
- Any change to gopgql. Design D10.
- Corpus-scoped incremental linking, overlays, Kubernetes, or any of codiq's
  own deferred scope (`SPEC.md` §16).
- Indexing worktrees. codiq's `prunedDir` already skips dot-directories, so
  `.worktrees/` is invisible to a base-clone walk; the project list names base
  clones only, and two checkouts of one module would render byte-identical
  descriptors even with a corpus column.

## Decisions

### D1. This change is an integration, plus exactly one codiq capability

The issue reads like a three-system build. It is not. codiq's `SPEC.md` §8 and
Decision 8 already assign the read surface to gopgql, and `deploy/` already
wires it. The only thing #51 asks for that codiq cannot do is hold more than one
repository at a time. Scoping the change to that — plus workspace settings and a
comparison — is what keeps it a change rather than a programme.

### D2. Corpus isolation by a corpus column in one database, not a database or a schema per repository

Three ways to keep twenty repositories apart:

| | Codiq change | Cross-repo queries | gopgql dependency |
|---|---|---|---|
| **A. `corpus` column, one database** | Yes — one milestone | Yes, one query | None |
| **B. One database per repository** | None | No — twenty endpoints | None |
| **C. One schema per repository** | Migration/`search_path` work | Yes | **Yes** — schema qualification, `gopgql#47` item 3 |

**A is chosen.** B is genuinely cheaper today and is the honest fallback if M1
proves harder than sized — but it forfeits the cross-repository question, and
that question is not optional here: gortex answers it (`find_usages` partitioned
by repo, `analyze cross_repo`), so a comparison run on B cannot score category 6
at all and would be scoring codiq on a layout chosen to avoid its weakness.

C is rejected on a second ground beyond cost: it is the only option that makes
this change depend on `gopgql#47`, and paying that dependency to buy an
isolation A gives for free is a bad trade.

### D3. Corpus identity must reach the descriptor, not only the file row

This is the decision the change turns on.

Adding `file.corpus` fixes the *storage* collision — `FileIDByPath`
(`store/sqlc/query.sql`) resolving two repositories' `main.go` to one row.
It does not fix the *linking* collision, because `link/` joins on
`occurrence.descriptor` and on nothing else, and the descriptor's package
coordinate comes from `coord.Resolve`, which walks **upward from the indexed
directory with no repository bound** (`coord/coord.go`, `Resolve`).

Measured on this machine: seven of the twenty trees under `projects/` carry no
manifest any registered resolver reads, and the nearest manifest above them is
`/Users/germanarutyunov/package.json`. All seven would resolve to that one
coordinate, with `Root` set to the home directory — so `Coord.Namespace` would
render each file's directory relative to `/Users/germanarutyunov`, and two
same-named symbols in two different repositories would render byte-identical
descriptors. The link pass would then materialise `resolves_to` and `calls`
edges between unrelated repositories. `coord`'s own doc comment describes this
defect one level down ("a repository holding a go.mod beside a package.json…")
and builds `Set` to prevent it; the repository bound is the same defect one
level up.

So capability 1 is two changes, not one, and the second is the load-bearing one:

1. `corpus` is part of file identity.
2. `coord.Resolve` stops at the directory it is given, and a repository with no
   manifest inside it gets a coordinate **named after its corpus**.

The bound is the argument and not a new `-root` flag, because both callers
(`index/index.go:176`, `index/dbos.go:704`) already pass the resolved
repository root and there is no second candidate for what the boundary would
be — codiq declines to shell out to git (`prunedDir`'s doc comment declines it
for `.gitignore`), so it has no other way to know where a repository ends.

**This is a behaviour change and the change must say so.** `codiq ./subdir`
inside a Go module stops inheriting that module's coordinate — and `cmd/codiq`'s
usage text ("must be inside a module CodiQ can resolve a package coordinate
for") becomes false and is rewritten. The usage being narrowed never produced a
coherent graph: `file.path` was already relative to the indexed subdirectory
while `Coord.Root` was the module root, so paths and namespaces were measured
from different origins. Narrowing it is a correction, not a regression, but it
is the one place where a user-visible behaviour changes.

### D4. The corpus fallback keeps the descriptor four fields wide

`Coord.Prefix` guarantees exactly four space-separated components and the SDL
stores exactly four columns. Adding a fifth would reshape every descriptor, the
`file` table, the proto, and the link join — for a repository-uniqueness
property the existing `Name` field can carry.

So: a repository with a resolvable manifest is unchanged — its module path or
package name already distinguishes it. A repository without one is stamped
`<scheme> <manager> <corpus> .` with `Root` at the repository root, instead of
today's inherited-ancestor coordinate. `Unknown` (`.`) stays exactly what it is
today for a *version*, which is a thing that legitimately cannot be determined;
it stops standing in for a *name*, which now always can be.

### D5. The corpus name is the directory name, overridable by flag

`codiq -corpus <name> [repo]`, defaulting to `filepath.Base` of the resolved
repository root. Not the absolute path: the path is already the DBOS workflow
ID's business (`index.RunIDPrefix`), it is machine-specific, and it would put
`/Users/germanarutyunov/Projects/workspace/projects/` into every descriptor of
every manifest-less repository. Not the git remote: it would make the
`extract/golang/testdata/greeter` fixture — which has no remote — unindexable,
and codiq must not need a git subprocess (`prunedDir`'s doc comment declines one
for `.gitignore` on the same grounds).

`flag`, not cobra/koanf. codiq's `SPEC.md` §12 and `cmd/codiq/main.go`'s package
comment both state the choice deliberately: *"one command with a handful of
flags does not need a command framework, and the spec names none."* This change
adds one flag. The workspace's Go house rules govern Go services scaffolded
here; they are not a mandate to re-litigate another repository's stated CLI
decision in passing.

### D6. The local database is rebuilt, not migrated in place

`file.corpus` is `NOT NULL` and no existing row can supply a value. codiq's
migrations are a generated, reviewed, committed artifact (`gopgql generate
--sdl … --dir schema/migrations`) and the compose comment is explicit that the
container applies exactly what is in the tree; hand-adding a backfill statement
to a generated file is the drift that arrangement exists to prevent.

There is no codiq database anywhere but a developer's Compose volume, so the
answer is `docker compose down -v` and re-index. Stated in `tasks.md` as a step,
not left to be discovered.

### D7. Indexing runs strictly serially, and that is not a temporary shortcut

`cmd/codiq/main.go`'s `start` records, as a measured fact, that two concurrent
indexers race in the link pass — *"a foreign key violation out of
`link.RebuildAll`"* — because rebuilding the derived edges is a whole-graph
operation while the other run is still replacing rows it reads.

With twenty repositories in one database, "whole-graph" means whole-*database*,
so this now applies to two runs over **different** repositories. The driver runs
codiq once per repository, in sequence, and never in parallel.

Making `RebuildAll` corpus-scoped is deliberately **out of scope**. Once D3
lands, a whole-graph rebuild is *correct* — the descriptor join cannot cross a
corpus — it is merely slower than it needs to be. Correctness first; if the
serial run is too slow to live with, that is a codiq performance issue with a
measurement behind it, and `link/incremental.go` (M8) is where it belongs.

### D8. The project list is config in this repository, not a flag in codiq

A committed `codiq/projects.yaml` naming each project's corpus name and path,
read by a driver script in this repository. codiq keeps taking one repository at
a time, which is what its CLI documents (`"one repository at a time, got %d"`).

The alternative — teaching codiq to take a list — puts this workspace's
project layout inside codiq, and makes the serial-execution rule of D7 an
invisible internal property of a tool instead of a visible loop in a script that
a human can read and interrupt.

The driver is python3, matching
`.claude/skills/loop-common/scripts/board-tick.py`: the list is YAML, this
machine has no Node runtime, and python3 is the only interpreter here that reads
YAML without adding a dependency. Every configured value reaches `docker` as its
own argv element rather than through a shell string — a project path is data
this repository reads from a file, and interpolating it into a command line is a
command injection.

Eight projects, per Open Question 2. `postgres-pglite` and `pglite` are named in
the file and commented out with the reason, so the deferral is visible where
someone would go looking to add them.

### D9. Connect over HTTP to codiq's own Compose stack

`.mcp.json` gains:

```json
"codiq": { "type": "http", "url": "http://127.0.0.1:8080/mcp" }
```

which is verbatim the shape `gopgql/examples/code-graph/.mcp.json` uses, against
the endpoint codiq's own compose already publishes (`mcp` service, `:8080`,
`GOPGQL_PATH` default `/mcp`).

The stdio alternative — `gopgql-mcp --sdl … --dsn …` as a `command` — was
considered and rejected for two reasons: it needs `gopgql-mcp` installed on
`$PATH`, and it needs an SDL path, which would point into `projects/`, a
gitignored tree, from a committed config file. HTTP keeps the committed
configuration true for anyone whose stack is up and merely unreachable for
anyone whose stack is down.

The cost is stated rather than hidden: **a session started with the stack down
gets a dead MCP server.** That is acceptable while codiq is a second source
(Open Question 1); it would not be acceptable for a replacement.

`.claude/settings.json` gains `mcp__codiq__*` in `permissions.allow`, beside the
existing `mcp__gortex__*`.

### D10. This change does not depend on `gopgql#47`

`gopgql#47` resolves two things that sound exactly like what querying a foreign
index needs: read-only exposure of an **externally-owned** schema, and vertex
**identity without a surrogate key**. Neither applies here.

codiq does not have a foreign index. gopgql *owns* codiq's schema — it generates
the DDL, the migrations and the property graph from `schema/codiq.graphql`, and
every `@node` type in that SDL declares `id: ID!`, which is exactly the
surrogate key `#47` exists to make optional. The tables `#47` is about are
`dbos.*`, which codiq keeps in a **separate database** (`SPEC.md` §9, §10) that
nothing but DBOS opens.

The one thing that would create the dependency is choosing schema-per-repository
isolation (D2 option C), which needs the schema qualification `#47` adds. D2
does not choose it.

Everything this change asks of gopgql already ships in `v0.1.0`: field arguments
compile to predicates as bind parameters (`SPEC.md` M3, verified in the M1 spike
that bind parameters work inside `GRAPH_TABLE`), and a `corpus` argument on a
root field is an ordinary one.

### D11. The comparison is pre-registered

Four things are written, committed and reviewed **before** either system is run,
in one commit whose message says so:

1. **The corpus** — the eight projects, each pinned to a commit SHA.
2. **The questions** — 30, six per category, five categories scored.
3. **The operationalisation** — for each question, the gortex tool call and the
   codiq GraphQL document, both frozen.
4. **The answer key** — the expected result set per question, hand-authored from
   the pinned sources, in `codiq/compare/key.yaml`.

The key is authored from the source, not from either system's output. That is
what makes the comparison falsifiable rather than self-confirming: every row
cites repository, path and symbol at a pinned SHA, so a reader who disagrees
with a number can open the file and dispute that row specifically, and rerunning
reproduces the same figures.

**Frozen means frozen.** If a GraphQL document turns out to be *wrong* — not
merely worse-scoring — the correction is committed as an amendment with a stated
reason, and the report carries **both** the pre-registered and the amended
number. A document is never edited after seeing its score.

### D12. Metrics, and a decision rule stated in advance

Per question, per system: **expressible** (can the system state the query at
all), **recall** `|returned ∩ key| / |key|`, **precision**
`|returned ∩ key| / |returned|`, **latency** (median of three warm runs), and
**answer cost** in tokens of the request and response — the last because a
system whose every answer is a hand-written GraphQL document over a generic
`query` tool pays a cost gortex's task-shaped tools do not, and reporting it as
a footnote rather than a number would understate it.

Per run: index wall-clock time, on-disk bytes, and files-indexed over
files-present per repository.

**The rule, stated before the run:** codiq is *a viable second source for
structural navigation* iff, over the eight repositories, categories 1–3 each
reach **≥0.90 recall and ≥0.90 precision**, category 5 reaches **≥0.90 recall**,
and category 6 is **expressible**. Otherwise the answer is *not yet*, naming the
failing category. Category 4 is reported and **not** gated — its ceiling is
gopgql's depth limit (D13), which is not a fact about codiq's index.

### D13. The known asymmetries are pre-registered too, so they cannot be spun afterwards

Recorded in the change before the run, and repeated in the report:

- **gopgql's default `MaxDepth` is 3.** Transitive questions deeper than three
  hops are refused at compile time (`*DepthExceededError`). gortex's
  `get_call_chain` has no such bound. This is why category 4 is ungated.
- **Two tools against roughly forty.** gopgql-mcp offers `introspect` and
  `query`; every codiq answer is a GraphQL document the agent must author.
- **Capabilities with no codiq analogue** — dataflow (`flow_between`,
  `taint_paths`), clone detection, blame/ownership/coverage enrichment, LSP
  diagnostics and code actions, session memory. **Listed, not scored.** Scoring
  a system on questions it does not claim to answer is how a comparison
  manufactures its own conclusion.
- **One capability with no gortex analogue** — codiq's graph is an ordinary
  PostgreSQL database, so arbitrary SQL aggregates and joins over it are
  available and gortex has nothing equivalent. One question demonstrates it;
  it is **not** scored either, for the same reason in the other direction.

### D14. Disk is a numbered precondition with a measured floor

`/System/Volumes/Data` had **490 MiB free, 100% used** when this change was
written. `postgres:19beta2` does not fit, and neither does the
`golang:1.25-alpine` layer both of codiq's Dockerfiles pull.

`tasks.md` gates every milestone from M2 on behind a measured **≥15 GiB free on
`/System/Volumes/Data`**, measured with that path — never `df /`, which on macOS
reports the sealed system volume and reads as a healthy percentage regardless.
A milestone that hits `ENOSPC` stops and reports rather than freeing space.

## Risks / Trade-offs

- **M1 is a data-model change to another repository.** If it proves larger than
  sized, D2's option B (a database per repository) delivers the settings and the
  comparison without it, at the cost of category 6. The fallback is named here
  so taking it is a decision rather than a drift.
- **`file.path` still has no unique constraint**, only a btree
  (`schema/codiq.graphql`). `(corpus, path)` uniqueness would let the loader
  drop its advisory lock for an `ON CONFLICT`, but that is a load-path
  optimisation and the SDL comment defers it to when a corpus exists — which is
  now. Out of scope, and recorded so it is not mistaken for an oversight.
- **The comparison will probably say "not yet".** Two generic tools and a
  depth-3 limit against a mature daemon is not a fair fight, and the pre-stated
  thresholds do not flatter codiq. That is the point of stating them first.
- **The HTTP MCP registration fails closed when the stack is down** (D9), which
  is a visible papercut for anyone in this workspace who is not working on
  codiq.

## Migration Plan

1. codiq: SDL, migration, `coord`, `store`, `index`, `cmd` — one PR.
2. Local database rebuilt (`down -v`), not migrated (D6).
3. Workspace: project list, driver, `.mcp.json`, `.claude/settings.json`.
4. Pre-registration committed; then the run; then the report.

Rollback is removing the two settings entries; the codiq change stands on its
own and is not workspace-specific.

## Open Questions

The four in `proposal.md`, unchanged. Q1 (replace or coexist), Q2 (which
projects), Q3 (where Postgres comes from) and Q4 (where the codiq work lands)
are owner decisions, each with a recommendation.
