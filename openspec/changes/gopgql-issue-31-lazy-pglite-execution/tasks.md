## 0. Blocked until `postgres-pglite#28` publishes

**Nothing below can start until #28 ships a release.** There is no artifact
today — `postgres-pglite` has no releases, and #6's GO verdict produced nothing
downloadable.

- [ ] 0.1 Wait for #28's release. Do **not** hard-code a guessed tag, filename or checksum in the meantime; a pin that resolves to unverified bytes is worse than no pin (design D1).
- [ ] 0.2 Read #28's release notes and confirm the published shape matches D1's assumption — a package tarball carrying the PGlite JS runtime, not bare `.wasm` + FS assets. If it is bare assets, D1 and every import site in section 5/6 change; raise that before writing code.
- [ ] 0.3 Confirm #28's acceptance demo actually ran `GRAPH_TABLE` in a browser. If it did not, this change is still blocked regardless of a release existing.

## 1. Prove SQL/PGQ executes on the pinned build — before anything else

#28 proves this for its own artifact; task 1 re-proves it for the exact pin this
repo ends up with, which is cheap and catches a pin that differs from what #28
validated. Discharge it before any UI work, so a negative answer costs one task
instead of the whole change.

- [ ] 1.1 Pin the build in `docs/package.json` using the release-asset URL from #28's release notes, verbatim. Run `npm install` and commit the resulting `package-lock.json` with its integrity hash. Record the pinned tag and the published checksum in the PR description.
- [ ] 1.2 Add `optimizeDeps: { exclude: ['@electric-sql/pglite'] }` to `docs/vite.config.js` (required by the fork's `docs/docs/bundler-support.md`; without it Vite's pre-bundling breaks the wasm asset URLs in dev).
- [ ] 1.3 Smoke test, in a **real browser worker**, not Node: fresh in-memory `PGlite`, apply `playground.Schema(ExampleSDL)` output including `CREATE PROPERTY GRAPH`, insert a couple of rows, run the compiled `GRAPH_TABLE` query with bind parameters, assert rows come back.
- [ ] 1.4 Assert no COOP/COEP: the smoke test runs against a static server setting no isolation headers, and `crossOriginIsolated` is false.
- [ ] 1.5 Record `select version()` in the test output. **Do not** assert a `PGlite x.y.z` suffix — this build does not emit one.
- [ ] 1.6 **Stop here if 1.3 fails.** Report the failure against the pinned build rather than working around it; the fix belongs in `postgres-pglite` / `pglite`, not in the playground.

## 2. Ordered bind values on the Go side

- [ ] 2.1 `playground.Compiled` gains `Args []any` — the ordered bind values `compiler.Compile` already returns (`compiler.Compiled.Args`, compiler.go:192) and which `CompileWithMaxDepth` currently discards. Same field name, carried through unconverted. `Params string` is untouched, and its doc comment now says it renders `Args`.
- [ ] 2.2 Unit test: a query with variables yields `Args` in placeholder order; a query without yields empty `Args` and `Params` still reads `(no bind parameters)`.
- [ ] 2.3 Unit test: `Args` is nil on every compile error path, including `*compiler.DepthExceededError`. This falls out of the existing `return Compiled{}, err` — the test is regression protection against someone later populating a partial result.
- [ ] 2.4 `cmd/wasm` `compile` returns `args` as a JSON array string. Surface a `json.Marshal` failure through the existing `error` field; do not discard it.
- [ ] 2.5 Doc-comment the precision limit accurately: a GraphQL `Int` literal is an `int64` (`compiler.value`) and **any** crossing into JS lands it in a float64, so integers past 2^53 lose precision. Do not describe this as a JSON-specific limit — `js.ValueOf` has it too, and an implementor who switches encodings to dodge it will have changed nothing (design D6).
- [ ] 2.6 Bump `apiVersion` 5 → 6 in `cmd/wasm/main.go` and `REQUIRED_API_VERSION` 5 → 6 in `docs/src/main.js`, together. The existing check then refuses a mismatched pair instead of running with no bind values.
- [ ] 2.7 Test the crossing for text, number, boolean and null values — each arrives as the value, not its printed form.

## 3. Seed fixtures

A `GRAPH_TABLE` query against an empty database returns zero rows. There is no
seed data in the repo today; without it the whole feature demonstrates nothing.

- [ ] 3.1 One exported seed document per example SDL, in `playground`, following the package's existing `Example<Scenario><Kind>` naming so the fixture sits beside the SDL it belongs to: `ExampleSeed` (for `ExampleSDL`), `ExampleDirectivesSeed`, `ExampleConstraintsSeed`, `ExampleInterfaceSeed`. Plain `INSERT`s against the generated tables. They live in `playground` and not in `test/` because `cmd/wasm` has to export them to the page.
- [ ] 3.2 Each seed is chosen so the scenario's own default query returns at least one row — including the multi-pattern and interface queries, whose shapes differ.
- [ ] 3.3 Go integration test per SDL: `Schema(sdl)` then the seed then the compiled query with its `Args`, asserting a non-empty result. This is the fixture's contract and it must not drift from the SDL beside it.
- [ ] 3.4 Follow the repo's integration convention: a suite under `test/<name>/` booting a real `postgres:19beta2` testcontainer, with **no skip path** — SPEC.md §10 requires every test to run against a real container, so no `testing.Short()` guard and no env-gated skip.
- [ ] 3.5 Export them through `cmd/wasm` as `gopgqlExampleSeed`, `gopgqlExampleDirectivesSeed`, `gopgqlExampleConstraintsSeed`, `gopgqlExampleInterfaceSeed`, matching the existing global naming.

## 4. The worker

- [ ] 4.1 `docs/src/pglite-worker.js`: a module worker that constructs `new PGlite()` with **no** `dataDir` — in-memory (design D3).
- [ ] 4.2 A three-message protocol — `run` in, `result` / `error` out. Carry only strings, plain arrays and plain values (design D5).
- [ ] 4.3 A `run` applies DDL, then seed, then the query with its bind values, and reports each step's outcome separately so the page can name the failing one.
- [ ] 4.4 A fresh database per `run`; the previous one is closed and discarded. Test: two runs with different schemas, the second unaffected by the first.
- [ ] 4.5 A seed failure does not abort the run — the query still executes and the two outcomes stay distinguishable (design D7).
- [ ] 4.6 **Do not** use `@electric-sql/pglite/worker` / `PGliteWorker` — it exists for leader election across tabs sharing a *persisted* database, which is the wrong semantics here (design D4).
- [ ] 4.7 Instantiate with `new Worker(new URL('./pglite-worker.js', import.meta.url), { type: 'module' })` so Vite emits it correctly under `base: './'` preview subpaths.

## 5. Lazy loading

- [ ] 5.1 The `@electric-sql/pglite` specifier appears in exactly one place: a dynamic `import()` on the Run path. Nothing on the boot path references it.
- [ ] 5.2 The worker is constructed on first Run, not at boot, and is reused for later Runs.
- [ ] 5.3 Build-output check in CI: no entry chunk and no eagerly-imported chunk references `pglite.wasm` or `pglite.data`. Fail the build if one does — laziness that regresses silently on a bundler upgrade is worth nothing (design D2).
- [ ] 5.4 Test: loading the page and generating output issues no request for a runtime asset.

## 6. Page wiring

- [ ] 6.1 A Run control and a result panel per query scenario: traversal, multipattern, directives, constraints, depth, interfaces. Not on rename, delta, migration or conformance — they compile no query.
- [ ] 6.2 Run executes the **`gopgqlSchema` DDL**, not the `gopgqlMigration` document. The latter is goose-annotated across two files and is not executable as-is (design, Context §2).
- [ ] 6.3 Run passes exactly the SQL shown in that scenario's SQL pane, plus the decoded `args`. Test that the executed text and the displayed text are identical.
- [ ] 6.4 Depth tab: when compilation was refused for exceeding the ceiling, Run is unavailable and the refusal keeps reading as the designed outcome.
- [ ] 6.5 Rows render as a table with the result's column names. Zero rows reads as success with no rows, never as an error.
- [ ] 6.6 PostgreSQL's own error message is shown verbatim, prefixed by which step failed.
- [ ] 6.7 In-progress state on the control; a second concurrent Run of the same scenario cannot start.
- [ ] 6.8 The control states, before it is pressed, that pressing it downloads a multi-megabyte PostgreSQL build.
- [ ] 6.9 After a successful run, the panel names the PostgreSQL version and fork build that produced the result.
- [ ] 6.10 A runtime that fails to load reports that execution is unavailable and why; every Phase-A pane keeps working.

## 7. Deployment

- [ ] 7.1 No workflow change. `deploy-docs.yml` and `pr-preview.yml` already run `npm ci` in `docs/`; confirm both still pass with the URL dependency, including the npm cache keyed on `docs/package-lock.json`.
- [ ] 7.2 Verify on the PR's own preview that Run works from a `pr-preview/pr-<N>/` subpath — the worker URL and the wasm/data asset URLs are the two things `base: './'` can get wrong.
- [ ] 7.3 Record the measured numbers in the PR: served (gzipped) and on-disk sizes of `pglite.wasm` and `pglite.data`, and the size delta of the deployed site.
- [ ] 7.4 **Do not** add a production-only asset path. Previews keep parity, because the bytes are identical across builds and git stores one blob for them however many previews exist (design D8).
- [ ] 7.5 Confirm the runtime's emitted asset URLs are content-addressed, so a returning reader gets them from cache.

## 8. Documentation

- [ ] 8.1 `SPEC.md` §8: the playground executes; where the runtime comes from; in-memory only; the lazy-load contract.
- [ ] 8.2 Record the pin — `postgres-pglite#28`'s release tag, the package version, the PostgreSQL version, and the fork ref built from — where a reader updating it can find all four.
- [ ] 8.3 Note the PostgreSQL version's stability (19beta2 at the time of writing) and that `postgres-pglite#10` (re-pin to `REL_19_0` at GA) will produce a newer build; upgrading is then a pin bump plus `npm install`.
- [ ] 8.4 Note what this build has *not* been exercised for — extensions, `pg_dump`, the socket server, persistence — so nobody builds on an untested surface.

## 9. Out of scope — do not do these here

- [ ] 9.1 `gh-pages` holds `pr-preview/` directories for PRs 35, 37, 39, 40 and 41, all merged; preview cleanup is not running. Do not fix it in this PR — raise it separately.
- [ ] 9.2 No persistence, no OPFS, no IndexedDB, no cross-tab sharing, no extension loading.
- [ ] 9.3 Do not move the Go module into the worker (design D5).
