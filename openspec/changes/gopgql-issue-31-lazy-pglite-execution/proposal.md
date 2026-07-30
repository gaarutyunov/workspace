## Why

The playground generates DDL and compiles GRAPH_TABLE SQL, and then stops. Every
pane is a *claim* about what PostgreSQL would do, and a reader has no way to
check it. That is the weakest part of the whole demo: the one thing gopgql is
for — turning a GraphQL query into SQL/PGQ that a real server executes — is the
one thing the page cannot show.

The obstacle was that no PostgreSQL with SQL/PGQ ran in a browser. That is no
longer true. `gaarutyunov/pglite` release `pglite-v0.5.4-pg19.1` ships
`@electric-sql/pglite@0.5.4-pg19.1` built against PostgreSQL 19beta2 from the
`gaarutyunov/postgres-pglite` fork, and the SQL/PGQ catalogs
(`pg_propgraph_element`, `pg_propgraph_label`, `pg_propgraph_property`) are
present both in the compiled `pglite.wasm` and in the bootstrapped `pglite.data`
template. The blocking spike (`postgres-pglite#6`) closed GO, and the artifact it
implied exists and is downloadable.

So the playground can stop claiming and start executing.

## What Changes

- **A Run action per query scenario.** Separate from Generate: Generate stays
  instant and pure, Run executes. Nothing about first paint changes until
  someone presses Run.
- **The forked PGlite build is a pinned URL dependency.** `docs/package.json`
  depends on the release tarball over plain HTTPS; `npm ci` reproduces exactly
  those bytes from the lockfile integrity hash on every build. No registry
  credentials, no vendored binaries in git, no build step to reproduce.
- **PGlite loads lazily, in a dedicated Web Worker, in memory only.** A dynamic
  `import()` inside the Run handler, so the ~4.7 MB (gzipped) of `pglite.wasm`
  plus `pglite.data` is never fetched by a visitor who does not press Run. No
  IndexedDB, no OPFS, no persistence of any kind.
- **The compiler's bind parameters become machine-readable.** Today
  `playground.Compiled.Params` is a display string (`"$1 = Alice"`) and the
  ordered values are discarded. Executing needs the values. `Compiled` gains
  `Args`, the WASM surface gains an `args` field, and `apiVersion` goes 5 → 6.
- **Example schemas gain seed data.** A GRAPH_TABLE query against an empty
  database returns zero rows, which demonstrates nothing. Each example SDL gets
  a fixture of `INSERT`s so Run produces rows a reader can read.
- **Results render as a table**, with the failing step named when a step fails.
  A PostgreSQL error is a result, not a page error: seeing what PostgreSQL says
  about generated SQL is part of the point.

## Capabilities

### New Capabilities

- `gopgql-pglite-runtime`: where the forked PostgreSQL-in-WASM build comes from,
  how it is pinned and verified, and what it is required to contain.
- `gopgql-playground-execution`: the Run action — lazy load, worker isolation,
  in-memory-only execution, the DDL → seed → query sequence, and rendering.
- `gopgql-playground-bind-params`: the Go-side change that makes ordered bind
  values available to a caller that intends to execute them.
- `gopgql-preview-asset-budget`: what the site is allowed to cost on `gh-pages`,
  and the rule that keeps PR previews honest.

### Modified Capabilities

<!-- The playground's Phase-A behaviour predates OpenSpec and has no capability
     spec under openspec/specs/. SPEC.md §8 is the project's own reference and is
     updated by this change. -->

## Impact

- **`playground`**: `Compiled` gains `Args []any`. New exported fixtures — one
  seed document per example SDL. `Compile` / `CompileWithMaxDepth` return the
  args they already have instead of dropping them.
- **`cmd/wasm`**: `compile` returns `args` as a JSON array string; `apiVersion`
  5 → 6; new `gopgqlExample*Seed` globals.
- **`docs/`**: `package.json` gains the pinned PGlite dependency;
  `vite.config.js` gains `optimizeDeps.exclude`; a new worker module; `main.js`
  gains the Run wiring; `index.html` gains a Run button and a result panel per
  query scenario.
- **`.github/workflows/`**: unchanged. Both `deploy-docs.yml` and
  `pr-preview.yml` already run `npm ci` in `docs/`, which is the whole install
  story.
- **Out of scope, and worth a separate issue**: `gh-pages` currently holds
  `pr-preview/` directories for five *merged* PRs (35, 37, 39, 40, 41). The
  preview cleanup is not running. This change does not fix that, and does not
  depend on it being fixed.
