## Context

The issue was written while `postgres-pglite#6` was still open and says "Blocked
by B8 (wasm32 spike). Do not start until B8 resolves positively." B8 resolved
positively on 2026-07-28 — but a GO verdict is a feasibility answer, not a file.
It produced no downloadable artifact, and `postgres-pglite` has no releases.

### The artifact does not exist yet — `postgres-pglite#28` produces it

This change **consumes** a build that is being produced under
`postgres-pglite#28`, and gopgql#31 is formally blocked on it. Everything below
about *how* the playground obtains and runs that build is independent of when
#28 lands; only the concrete pin has to wait for it (D1).

#28's own acceptance test is a PR preview that loads the bundle in a browser and
runs a real `GRAPH_TABLE` query against it with visible results. That is exactly
the guarantee this change needs and would otherwise have had to establish for
itself, so this spec does not duplicate it — it depends on it.

### What the release has to contain for this design to hold

This list is a **requirement on #28**, not a description of something that
exists. It is what "consumable by the playground" means:

- **The wasm plus its FS bundle** — the compiled PostgreSQL and the `initdb`
  template that a fresh database is created from. The SQL/PGQ catalogs must be
  in *both*: compiled into the engine, and bootstrapped into the template, or
  `CREATE PROPERTY GRAPH` has no catalogs to write to.
- **The JS runtime that instantiates them.** Raw `.wasm` + FS data is not
  loadable on its own; something has to own the Emscripten instantiation, the
  wire protocol and the result decoding. Publishing the PGlite package built
  against the fork gives this for free and keeps
  `import { PGlite } from '@electric-sql/pglite'` working unchanged.
- **A browser and Web Worker entry point**, and an in-memory filesystem. OPFS
  and IndexedDB backends are unnecessary here (D3).
- **Built `-sUSE_PTHREADS=0`**, so `SharedArrayBuffer` is unused and consumers
  need no COOP/COEP headers and no `coi-serviceworker`.
- **Anonymous download over plain HTTPS**, with a published checksum, so a
  static site build can fetch it with no credentials and pin it by hash (D1).
- **Release notes stating the PostgreSQL version, the ref built from, the
  SQL/PGQ support level and the emscripten flags** — enough that a consumer
  knows what it pinned, and that `postgres-pglite#10` knows what to re-cut at
  PG19 GA.

### Prior art #28 should not have to rediscover

There is an **unproven prerelease** in the sibling repo `gaarutyunov/pglite`,
tag `pglite-v0.5.4-pg19.1`, packaging `@electric-sql/pglite@0.5.4-pg19.1` built
from `postgres-pglite` at `f13a3a5` (tip of `REL_19_BETA2-pglite`, which is
where PG19 + SQL/PGQ is fully ported — the default branch `REL_18_3-pglite` has
none of it). It is **not** what this spec pins, and it does not satisfy the
requirements above, because:

- It was packed by a **local run** of `scripts/pack-pg19-release.sh`. The repo's
  `publish-pg19-release.yml` — which builds from source and gates publication on
  a `GRAPH_TABLE` smoke test — has **never executed**, nor has the monthly
  `fork-rot-check.yml`. Reproducibility, which #28 requires, is absent.
- Its own notes list what was verified under Node — `select version()`, DDL/DML,
  aggregates — and **SQL/PGQ execution is not on that list**, nor are browser
  targets, workers, extensions, `pg_dump` or persistence.

Two things in it are still worth reusing rather than re-deriving: the packaging
shape (an npm tarball of the unchanged package name, so the import is a drop-in)
and the measured footprint below, which is the best available estimate of what
#28 will publish.

One trap it already documents: `select version()` on a fork build carries **no**
`PGlite x.y.z` suffix. Nothing may assert that pattern.

### Measured footprint (from the prerelease; expect #28 to be close)

`pglite.wasm` 9,379,167 B and `pglite.data` 5,434,131 B — **14.8 MB on disk,
~4.7 MB gzipped** (3,126,403 + 1,560,207). The issue's "roughly 6 MB" is the
wire figure at best and understates disk by about 2.5x. D8 depends on these
numbers, so they should be re-measured against #28's actual release.

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
"@electric-sql/pglite": "<the release asset URL that postgres-pglite#28 publishes>"
```

**The URL and its checksum cannot be written until #28 publishes.** Do not
hard-code a guessed tag, a guessed filename, or a checksum copied from anywhere
else — a pin that resolves to bytes nobody verified is worse than no pin. The
version pinned here must be the version #28 ships, and the implementer's first
act is to read #28's release notes and copy the URL and the published checksum
from them. Two consequences worth stating because they are easy to miss:

- If #28 ships **raw `.wasm` + FS assets rather than a package**, this decision
  changes shape: there is then no npm dependency to pin, and the assets have to
  be fetched and instantiated by hand. That is strictly more work here and is
  why the "JS runtime included" bullet is on the requirements list above. Settle
  the published shape with #28 before implementing.
- If #28 publishes under a different package name, the drop-in
  `import { PGlite } from '@electric-sql/pglite'` no longer holds and every
  import site in this design changes with it.

Given a package tarball URL, the mechanism is: `npm install` records the
resolved URL *and* an integrity hash in `package-lock.json`; `npm ci` then
reproduces exactly those bytes and fails loudly if the asset ever changes. This
requires that #28 never replace an asset in place — a new build must get a new
tag — so that the URL is immutable by convention and the lockfile enforces it by
hash.

`deploy-docs.yml` and `pr-preview.yml` already run `npm ci` in `docs/` with the
lockfile cached. **No workflow change is needed.** That is the main reason to
prefer this over the alternatives.

*Rejected — vendoring `dist/` into the repo.* Tens of MB of build output
committed to `main` forever, with a hand-rolled integrity story strictly worse
than npm's.

*Rejected — building the fork in CI here.* Requires emscripten plus a full
PostgreSQL wasm build, in the wrong repo. #28 exists precisely so that no
downstream site has to do this.

*Rejected — publishing to npm under a scope.* Needs registry credentials in CI
and a package name divergent from `@electric-sql/pglite`, which would break the
drop-in import.

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
The measurements say otherwise, in both directions. They are taken from the
prerelease named in the Context and should be re-checked against #28's release —
but the *shape* of the conclusion does not depend on the exact figures, and it
applies equally to the preview infrastructure #28 is building for its own
acceptance demo:

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

- **The artifact does not exist yet.** This is the blocking risk and it is not
  mitigable from here: nothing in this change can be implemented until
  `postgres-pglite#28` publishes. The design is written so the wait costs
  nothing — every decision except D1's concrete pin is settled independently.
- **#28 may publish a different shape than assumed.** D1 assumes a package
  tarball carrying the JS runtime. Raw `.wasm` + FS assets would require hand
  instantiation and would change D1 and every import site. Settle this with #28
  before implementing, not after.
- **SQL/PGQ execution in a browser is unproven.** #28's acceptance test is
  exactly this, so it should be proven before this change starts. Task 1 repeats
  it against the pinned build anyway — cheap, and it catches a pin that differs
  from what #28 validated.
- **PostgreSQL 19beta2 is a beta.** `postgres-pglite#10` will re-pin the fork to
  `REL_19_0` at GA, which will produce a new release. The upgrade is then a
  one-line pin bump plus `npm install`, which is the point of pinning by URL.
- **A ~4.7 MB download on first Run.** Deliberate and bounded to people who
  asked for it. The Run button states the cost before it is paid.
- **Vite could regress the laziness on upgrade.** Asserted by the build-output
  check in D2.
