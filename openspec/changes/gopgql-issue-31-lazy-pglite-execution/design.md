## Context

The issue was written while `postgres-pglite#6` was still open and says "Blocked
by B8 (wasm32 spike). Do not start until B8 resolves positively." B8 resolved
positively on 2026-07-28, and — this is the part the issue could not know — the
work did not stop at a verdict. A packaged build was published the same day.

### What exists, and the evidence for it

`gaarutyunov/pglite`, release `pglite-v0.5.4-pg19.1` (pre-release, 2026-07-28):

| asset | size |
|---|---|
| `electric-sql-pglite-0.5.4-pg19.1.tgz` | 7,968,775 B |
| `build-info.txt` | 347 B |
| `SHA256SUMS` | 103 B |

`sha256(tgz) = b4d0531251bc90f17e5e113605b6540b9e7585a0265bfd3e8456f7ec7999f9fb`,
matching `SHA256SUMS`, verified against a fresh download. The tarball is
`@electric-sql/pglite@0.5.4-pg19.1` — the package *name* is unchanged, so
`import { PGlite } from '@electric-sql/pglite'` works untouched and the
`-pg19.N` suffix is how an installed copy identifies itself as a fork build.

`build-info.txt` pins the provenance: PostgreSQL 19beta2, wasm32, emcc 3.1.74,
pglite commit `a9ec5f1`, postgres-pglite commit `f13a3a5`. `f13a3a5` is reachable
only from `origin/REL_19_BETA2-pglite` in `gaarutyunov/postgres-pglite` and is
its tip ("Call sigsetjmp, not the undefined pgl_sigsetjmp (#27)").

**SQL/PGQ is in the shipped artifact, not merely in the branch.** The source at
`f13a3a5` carries `src/backend/parser/parse_graphtable.c`, the four
`pg_propgraph_*` catalog headers, and the `GRAPH_TABLE` / `GRAPH` / `PROPERTY`
keywords in `kwlist.h`. More decisively, the *built* files carry it too:
`dist/pglite.wasm` contains `CreatePropGraph`, `AlterPropGraph`,
`pg_get_propgraphdef`, `propgraph_edge_get_ref_keys`; and `dist/pglite.data` —
the bootstrapped template database — contains the system-view SQL that selects
`FROM pg_propgraph_element`, `pg_propgraph_label`, `pg_propgraph_property`. A
database initialised from that template has the SQL/PGQ catalogs.

**The dist is browser- and worker-capable.** `dist/` contains `pglite.js`
(457 KB), `pglite.wasm` (9,379,167 B), `pglite.data` (5,434,131 B),
`initdb.wasm`, `dist/worker/`, and `dist/fs/{base,nodefs,opfs-ahp}`. The package
`exports` map has `.`, `./worker`, `./live`, `./nodefs`, `./opfs-ahp`,
`./basefs`, `./template`, `./contrib/*`.

**No cross-origin isolation is required.** `dist/pglite.js` contains zero
occurrences of `SharedArrayBuffer`, consistent with the issue's claim that the
fork is built `-sUSE_PTHREADS=0`. No COOP/COEP headers, no `coi-serviceworker`.

### What the release does *not* claim

Its own caveats: verified under Node are `select version()`, DDL/DML and
aggregates. **Not** exercised: the PGlite test suite, `CREATE EXTENSION`,
`pg_dump`, the socket server, worker/OPFS/IDBFS backends, browser targets, and
persistence. SQL/PGQ execution is not on the verified list either — the catalogs
are provably present, but nobody has run a `GRAPH_TABLE` against this build.

That is a risk to *discharge with a test*, not a reason to block: the first task
of this change is a smoke test that runs `CREATE PROPERTY GRAPH` and a
`GRAPH_TABLE` query against the pinned build in a real browser worker, and it
runs before any UI work. Also note `select version()` does not carry a
`PGlite x.y.z` suffix on this build — nothing may assert that pattern.

### What Phase A actually gives us

`docs/src/main.js` boots `gopgql.wasm` on the main thread via `wasm_exec.js`,
checks `gopgqlApiVersion` against `REQUIRED_API_VERSION` (currently 5), seeds the
input panes from exported examples, and drives ten scenarios through a
`scenarios` map of `{ render, inputs }`. Each `.run[data-scenario]` button calls
`scenario.render()`. Vite builds with `base: './'` so PR-preview subpaths work.

Two things there are load-bearing for this change and are easy to get wrong:

1. **`gopgqlMigration` output is not executable.** `playground.Migration` returns
   a *document* — `-- migrations/<filename>` headers over goose-annotated files
   (`-- +goose Up`, `StatementBegin`/`End`), two migrations since gopgql#38 split
   tables from the graph. `playground.Schema` returns the same model without the
   goose framing, and its own doc comment calls it "the schema a compiled query
   runs against". `gopgqlSchema` is what Run executes. The issue's phrase
   "execute the generated migrations" is imprecise; executing the goose document
   would require re-implementing goose's annotation parser in the page for no
   gain.

2. **The bind parameters are not available.** `playground.Compiled.Params` is
   `renderParams(args)` — `"$1 = Alice, $2 = ..."`, for a human. `Compile`
   receives `args []any` from the compiler and throws it away. Nothing in the
   WASM surface can bind `$1`. This is the one genuine Go-side gap and it is
   invisible from the issue text.

## Goals / Non-Goals

**Goals:**

- Prove the generated SQL by running it, in the reader's own browser.
- Zero cost to a visitor who does not press Run.
- Reproducible bytes: the same PGlite build on every machine and every CI run,
  or a loud failure.
- Keep Generate exactly as it is — pure, instant, offline.

**Non-Goals:**

- Persistence of any kind. In-memory only, per the issue.
- Sharing one database across tabs. See D4.
- Running the Go module in the worker. It stays on the main thread (D5).
- Building PGlite from source in CI. See D1.
- Fixing the stale `pr-preview/` directories on `gh-pages`. Separate concern.
- Extension loading, `pg_dump`, or the socket server — untested on this build
  and unnecessary here.

## Decisions

### D1: Consume the release tarball as a pinned URL dependency

`docs/package.json` depends on the release asset URL directly:

```
"@electric-sql/pglite":
  "https://github.com/gaarutyunov/pglite/releases/download/pglite-v0.5.4-pg19.1/electric-sql-pglite-0.5.4-pg19.1.tgz"
```

`npm install` records the resolved URL *and* an integrity hash in
`package-lock.json`; `npm ci` then reproduces exactly those bytes and fails
loudly if the asset ever changes. The release's own policy is that assets are
never replaced in place — a new build gets a new tag — so the URL is immutable
by convention and the lockfile enforces it by hash.

`deploy-docs.yml` and `pr-preview.yml` already run `npm ci` in `docs/` with the
lockfile cached. **No workflow change is needed.** That is the main reason to
prefer this over the alternatives.

*Rejected — vendoring `dist/` into the repo.* ~23 MB of build output committed to
`main` forever, with a hand-rolled integrity story strictly worse than npm's.

*Rejected — building the fork in CI.* Requires emscripten plus a full PostgreSQL
wasm build. The release exists precisely so that no downstream site has to do
this.

*Rejected — publishing to npm under a scope.* Needs registry credentials in CI
and a package name divergent from `@electric-sql/pglite`, which would break the
drop-in import. The release notes call this out as the reason for the URL form.

### D2: Lazy means a dynamic `import()` inside the Run handler

The module specifier appears in exactly one place, inside the async Run path.
Vite emits it as its own chunk and the wasm/data assets hang off that chunk, so
the entry graph never references them. `optimizeDeps.exclude:
['@electric-sql/pglite']` is required in `vite.config.js` — this is documented in
the fork's own `docs/docs/bundler-support.md` and is not optional; without it
Vite's dep pre-bundling mangles the wasm asset URLs in dev.

This is asserted, not assumed: a build-output check confirms no entry or
eagerly-imported chunk references `pglite.wasm` or `pglite.data`. "Lazy" that
regresses silently on a bundler upgrade is worth nothing.

### D3: One database per Run, discarded after

`new PGlite()` with no `dataDir` is in-memory. Each Run constructs a fresh
instance, applies DDL, seeds, queries, and closes it. Nothing survives the Run —
which is both what the issue asks for and what makes repeated Runs on an edited
schema behave predictably instead of accumulating half-migrated state.

### D4: A plain dedicated Worker, not `PGliteWorker`

`@electric-sql/pglite/worker` exists and would handle the messaging, but its
purpose is leader election so that *multiple tabs share one persisted database*.
The playground is explicitly ephemeral and in-memory, so sharing across tabs is
the wrong semantics — two tabs would fight over one database that neither of
them should be keeping. A dedicated `new Worker(new URL('./pglite-worker.js',
import.meta.url), { type: 'module' })` with a three-message protocol (`run`,
`result`, `error`) is smaller, has no BroadcastChannel or Web Locks dependency,
and matches what is actually wanted.

The worker exists to keep a multi-second `initdb` off the main thread. That is
the entire reason it is a worker, and the protocol should stay small enough that
this stays obvious.

### D5: The Go module stays on the main thread; data crosses as strings

`wasm_exec.js` is a classic script that installs `globalThis.Go` and the Go
program sets globals synchronously — the existing boot sequence depends on both.
Moving it into the worker would mean re-running that boot per worker for no
benefit, since generation is already fast and pure.

So the two WASM modules never meet. The main thread calls `gopgqlSchema` and
`gopgqlCompile`, and posts *strings and plain arrays* to the worker: the DDL, the
seed SQL, the query SQL, and the bind values. Results come back as plain rows.
`postMessage` structured-clones them; there is no shared memory, and none should
be introduced.

### D6: Ordered bind values become part of the WASM surface, at API v6

`playground.Compiled` gains `Args []any` alongside the existing `Params string`.
`Params` is untouched — the Params pane is a Phase-A feature that proves values
travel as parameters rather than being interpolated, and it should keep saying
exactly what it says today. `Params` becomes documented as the rendering *of*
`Args`, so the two fields read as one fact and its display form rather than as
two overlapping ideas.

The field name is deliberately the same as `compiler.Compiled.Args`
(compiler.go:192), which is where these values come from: `Compile` already
returns `(sql, args, err)` and `CompileWithMaxDepth` currently drops `args` on
the floor. The playground field carries them through unchanged — same name, same
values, no conversion.

`cmd/wasm`'s `compile` returns `args` as a **JSON array string**, decoded with
`JSON.parse` in the page. JSON rather than `js.ValueOf` on `[]any` because the
boundary is then explicit, is symmetric with how variables already cross in the
other direction (`parseVars`), and keeps `compile` free of `js.ValueOf`'s
panic-on-unsupported-type behaviour as the compiler's value set grows.

**The precision limit is the JavaScript number model, not JSON.** A GraphQL `Int`
literal becomes a Go `int64` (`compiler.value`, `ast.IntValue` →
`strconv.ParseInt(..., 64)`), and any crossing into JS — `JSON.parse` or
`js.ValueOf` alike — lands it in a float64. An integer beyond 2^53 loses
precision either way, so switching encodings does not avoid it. The example
schemas use text and small integers, so it does not bite; it belongs in the doc
comment rather than in a future bug report.

`json.Marshal` on the args slice returns an error. It cannot fail for the types
the compiler produces today, but it must be reported through `compile`'s
existing `error` field rather than discarded — a silently empty `args` is
exactly the failure mode the version bump below exists to prevent.

`apiVersion` goes 5 → 6 and `REQUIRED_API_VERSION` in `main.js` follows. The
existing staleness check then does its job: a page paired with a stale
`gopgql.wasm` says so instead of silently running with no bind values.

### D7: DDL → seed → query, each step reported

Run is three steps and the panel names which one failed.

The seed is a fixture bound to an *example* SDL. If the reader has edited the
schema, the seed may no longer apply — that is expected, not an error in the
page. The seed step reports its own failure and Run continues to the query, which
then returns zero rows. That is the honest outcome: the schema really did execute
and the query really did run.

A PostgreSQL error at any step is rendered as PostgreSQL's message, not wrapped
in page chrome. Watching PostgreSQL reject or accept generated SQL is the
feature.

### D8: `gh-pages` cost is not the problem the issue expects

The issue estimates ~6 MB and asks whether the assets should be production-only.
The measurements say otherwise, in both directions:

- The raw figure is bigger than stated: `pglite.wasm` 9,379,167 B +
  `pglite.data` 5,434,131 B = **14.8 MB on disk**, ~4.7 MB gzipped over the wire
  (3,126,403 + 1,560,207).
- The repo cost is far smaller than stated, because **the bytes are identical on
  every build.** They come from an immutable pinned tarball, so git stores one
  blob for the entire history of `gh-pages` no matter how many previews or
  deploys reference it. Contrast `gopgql.wasm`: rebuilt from Go source on every
  commit, so every deploy adds a fresh ~5.5 MB blob. That — 78 gh-pages commits
  each carrying a new Go wasm — is why the repo is already ~30 MB, and this
  change adds nothing of that kind.

So previews keep parity with production. Serving the runtime only from the
production path would mean previews cannot exercise the feature under review,
which defeats the purpose of having previews, in exchange for saving a single
shared blob. The per-visitor download is the cost that actually matters, and D2
already removes it for anyone who does not press Run.

(Separately, and not this change's job: `gh-pages` still holds `pr-preview/`
directories for PRs 35, 37, 39, 40 and 41, all merged. Preview cleanup is not
running. Worth its own issue.)

## Risks / Trade-offs

- **SQL/PGQ has never been executed on this build.** Catalogs are provably
  present; execution is not proven. Mitigated by making the browser smoke test
  task 1, before any UI work, so a negative result costs one task instead of the
  whole change.
- **Browser targets are unexercised by the release.** Same mitigation; the smoke
  test runs in a real browser worker, not Node.
- **PostgreSQL 19beta2 is a beta.** `postgres-pglite#10` will re-pin the fork to
  `REL_19_0` at GA, which will produce a new pglite release tag. The upgrade is
  then a one-line version bump plus `npm install`, which is the point of pinning
  by URL.
- **A ~4.7 MB download on first Run.** Deliberate and bounded to people who
  asked for it. The Run button states the cost before it is paid.
- **Vite could regress the laziness on upgrade.** Asserted by the build-output
  check in D2.
