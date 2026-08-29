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

## Decisions  *(all four answered by the owner, 2026-08-29)*

Recorded on gaarutyunov/workspace#51 and checked off in `tasks.md` §0.

### D-Q1. codiq sits beside gortex — and **gortex is repaired first**

> *"We need to compare so we need to fix gortex."*

The comparison stands, so it needs a baseline worth comparing against. gortex's
index is not one today, measured against the running daemon: the `codiq` entry
holds **only `.worktrees/*` copies of stale branches** and no canonical source
(its base checkout is 2 files, 16 commits behind); worktrees are indexed twice,
so symbols appear 7–9×; and eight base repos are untracked. A comparison run
against that would measure gortex's misconfiguration and hand codiq an
unearned win.

**`tasks.md` gains M0 — repair gortex tracking — and it blocks M5.** This is the
one milestone here that pays off whether or not codiq ever ships, because it
fixes a tool in daily use.

### D-Q2. All projects, with their worktrees — **77 trees, not eight**

> *"We need all projects with their worktrees tracked."*

The recommendation of a curated eight is **overruled**. Measured 2026-08-29:
**20 base repos + 57 worktrees = 77 trees.** `postgres-pglite` (1.1 GB) and
`pglite` (1.4 GB) are **in**, not deferred to a second run.

The owner's reason is the one that matters, and it changes the character of the
whole change:

> *"Indexing the projects is a way to test and fix all the functionality."*

The run is codiq's **acceptance test**, not merely corpus preparation. A defect
surfaced while indexing is fixed under this issue. Excluding the awkward
repositories would therefore defeat the exercise — they are precisely where the
defects are. `pglite` and `postgres-pglite` stop being a scale risk to avoid and
become the point.

This also sharpens M1 rather than complicating it. 57 of the 77 trees share
every repo-relative path with their base repo, and six trees resolve no manifest
at all — `agentiq`, `bikelanes`, `workout`, `qonnect`, `skill-test`, `goga`,
with `/Users/germanarutyunov/package.json` verified present as the first
manifest above them. Corpus isolation is load-bearing for the **majority** of
the corpus instead of an edge case, and **each worktree is its own corpus**
(`<repo>@<branch>`).

### D-Q3. `postgres:19beta2`, the published Docker image

> *"Postgres has a docker image for pg19 with beta 2."*

codiq's own `deploy/docker-compose.yml`, unmodified, which already pins exactly
that image. The earlier framing of this as doubtful was wrong on two counts:
the image is published and is the intended answer, and **the disk gate is
clear** — re-measured 2026-08-29 at **49 GiB free / 78% used**, against the
490 MiB / 100% the change was written under. The gate stays in `tasks.md` only
because the corpus grew almost tenfold.

### D-Q4. The corpus lands under this issue

> *"Corpus is necessary in 51."*

As recommended: its own PR in `gaarutyunov/codiq`, referenced from #51, not a
separate codiq issue with #51 parked in `Blocked`.

