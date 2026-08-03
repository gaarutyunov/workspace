**Sequencing rule (design D16), on the owner's instruction:** *"We shouldn't
deliver everything at once. Split the spec into clear milestones. Each milestone
we will deliver one package. I will carefully review it. We will migrate gopgql
and some other project to it and then continue to the next."*

So this file is ordered by **milestone**, not by module.

**The definition of done, which applies to every milestone below** (design D18,
the owner's words): *"Splitting functionality and enforcement is not allowed."*
Every milestone from M1 lands with **all six** of:

| # | part | what it means here |
|---|---|---|
| 1 | **implementation** | the package |
| 2 | **tests** | including this module's own telemetry assertions and its entry in `TestEveryModuleIsInstrumented` |
| 3 | **skill reference** | this module's routing-table row and enforcement-matrix row, written as the module lands |
| 4 | **linter** | at least one rule enforcing *this* module's conventions — custom analyzer where nothing off the shelf fits — plus the `depguard` entry banning direct use of the dependency this module wraps |
| 5 | **CI action** | a composite action wherever this milestone introduces a tool that must run in CI; milestones that introduce none say so |
| 6 | **migration** | a real project adopts it. **A separate task that blocks this milestone's merge** — not follow-up work |

Each milestone below is laid out in those terms, with parts 3–6 called out
explicitly so a missing one is visible rather than implied.

Three further rules:

- **One package per milestone.** Where a milestone carries a second directory it
  is something the package cannot be used without and nobody adopts separately —
  generated constants, an adapter sub-package — and the milestone says so.
- **A named adopter.** Not "a project could use this": a repo, named, with the
  reason it is the right one.
- **Adoption is the gate.** A milestone closes when the adopting project's
  migration PR is merged, not when the package builds. The next milestone does
  not start until then. Each milestone ends with an explicit **Gate** line.

Scope is unchanged from design D4 — the issue's whole tool list. What a
milestone changes is *when*, and the rule that a module with no project to adopt
it does not get a slot at all.

**M11 and M13 have dissolved.** The previous revision collected every lint rule
into M11 and the whole skill into M13; D18 forbids that, so each module now ships
its own rules and its own skill section. What is left of M11 is the three generic
actions that belong to no module; what is left of M13 is a closing audit.

**One thing is deferred rather than scheduled**, recorded at the end:
`goga/components` (design D12, D16 — no consumer exists). **`goga/registry` is no
longer deferred** — Go 1.27 ships generic methods, the spike confirmed the shape,
and it lands in M0 (design D8).

---

## M0. Repo foundations — *not a package; nobody adopts this*

goga is empty: one commit, a one-line README. Nothing can be delivered from it
until this exists. It is deliberately the only milestone with no external
adopter, and it is small.

- [ ] 0.1 `go mod init github.com/gaarutyunov/goga`; **`go 1.27rc2`** (design D17), dropping the `rc2` suffix when 1.27.0 ships. The RC is the owner's accepted cost — *"even if it's alpha or beta version"* — and M0 is where its consequences are absorbed rather than discovered: record in the README that `GOTOOLCHAIN=auto` will silently switch a 1.26 developer onto the RC, and that `GOTOOLCHAIN=local` fails hard.
- [ ] 0.2 Package layout **flat, no `pkg/`, no `internal/`** for goga's own code, per the issue. Adapters are sub-packages of their module (`database/pgxdb`) so an adapter's dependency stays optional.
- [ ] 0.3 The root `goga` package: `goga.Option[S]` and `goga.Apply` (design D14). It holds **only** these and imports nothing but the standard library. The composition root is `goga/app` and arrives at M9 — every module imports the root, and the composition root imports every module, so the two cannot be one package.
- [ ] 0.4 `.golangci.yml`, `Makefile`, `.goreleaser.yaml` — these double as the templates goga ships (design D3's carve-out).
- [ ] 0.4a **`goga/registry`** (design D8): `Table[P]` — `Register` panicking on a duplicate, `New` returning the port, `Keys()`, and the Go 1.27 generic method `Get[A any](key) (A, error)` returning the adapter's concrete type. It is a **leaf**: standard library only, no `Instrumentation`, so `registry` → `telemetry` → `registry` cannot form. Tests cover the duplicate panic, the unknown key, a successful concrete cast, and the mismatched-`A` runtime error — the last because `A` cannot be constrained to `P` (*"cannot use a type parameter as constraint"*) and the runtime check is therefore load-bearing rather than defensive.
- [ ] 0.4b **`goga/lint` scaffold** (design D18): the golangci-lint plugin module, the `analysistest` harness, and **one worked analyzer end to end** so M1 has a pattern to copy rather than a mechanism to invent. `mcp-anything` already depends on `golangci/plugin-module-register`, so this is assembly, not research.
- [ ] 0.4c **The skill skeleton** (design D18): the routing table and enforcement-matrix headings, with no rows. Every milestone from M1 adds its own; nothing is written here that a module has not yet delivered.
- [ ] 0.4d **The linter must be built from source against a bumped `golang.org/x/tools`** (design D17). Verified: golangci-lint v2.7.2 as shipped refuses to run on a Go 1.27 target, and rebuilt on go1.27rc2 it still fails with *"export data version 4 is greater than maximum supported version 2"* because it pins x/tools v0.39.0; rebuilt against **v0.48.0** it reports `0 issues` on generic-method code. So `go-lint` builds golangci-lint rather than using the upstream prebuilt action, with a TODO to revert the day upstream ships a release on a new enough x/tools.
- [ ] 0.5 `go.mod` `tool` directive block for the whole generator set — wire (`goforj/wire`), oapi-codegen, mockgen, sqlc, buf, OTel Weaver, goose — following `skill-test/go-service`, which already does this.
- [ ] 0.6 The three composite actions goga's own CI needs now: `setup-go` (Go version defaults to what `go.mod` says), `go-lint` (gofmt gate, `go vet`, golangci-lint **built from source per 0.4d**, not the official prebuilt action, because the released binary cannot lint a Go 1.27 target at all — D17), `go-test` (race, atomic coverage, summary and artifact). Actions SHA-pinned internally; projects pin **goga** and nothing else.
- [ ] 0.7 The cross-cutting Go conventions of design D15, written down once here and applied by every milestone that follows: named result parameters on any method that opens a span; `Instrumentation.Start` returns the closer, never a `(span, start)` pair; a method returning a streaming result never cancels that result's context; one signal handler per process, owned by `cli`; errors wrapped `fmt.Errorf("goga/<module>: <op>: %w", err)` with a typed error wherever a caller must branch.
- [ ] 0.8 The house settings shape, also once (design D5, D14): each module declares an **unexported** `settings` struct plus `type Option = goga.Option[settings]`; where the module has adapters it also exports a `Settings` **interface** of accessors for them to read. **No exported struct anywhere in the option surface, and no goga entry point takes a settings value.**
- [ ] 0.9 **Read Yokai's module decomposition and `gocloud.dev/blob`'s portable/driver split before fixing package boundaries** (design D7, Risks).

**Six parts.** M0 is the one milestone that does not carry all six, and
deliberately: it *is* parts 3, 4 and 5's mechanism, and it has no package for a
project to adopt. Implementation and tests are 0.1–0.9; the skill and lint
**scaffolds** are 0.4b–0.4c; the actions are 0.6 and 0.4d. **Part 6 does not
apply** — there is nothing here to migrate a project onto, which is the same
reason D16 already called M0 the only milestone with no external adopter.

**Gate:** goga's own CI is green on an empty-but-buildable module, with the
plugin harness running its one worked analyzer and the linter build pinned per
0.4d. No external adoption to wait for; this is the only milestone where that is
true.

---

## M1. `goga/telemetry` — *adopters: gopgql, then epos*

The owner: *"Telemetry first, every project needs it."* The survey agrees and
says why: three of five projects import the OTel SDK and only two configure all
three signals. `gopgql` has none at all, so every one of its MCP tools, pgx
queries and goose migrations is currently unobserved; `epos` has metrics only and
never calls `otel.SetMeterProvider`. It is also the module every other module
needs, because design D6 makes instrumentation an invariant.

**Second directory:** `goga/semconv`. The generated attribute constants are what
`Instrumentation` consumes, and a telemetry module emitting string-literal
attribute keys would violate its own capability on day one. It is generated, not
adopted, and it ships here.

- [ ] 1.1 `Setup` establishing tracer, meter **and** structured logger — all three or none — installed globally *and* returned.
- [ ] 1.2 Exporter tables, name-keyed, **this module's own `registry.Table[P]`** (design D8): `RegisterTraceExporter` / `RegisterMetricExporter` / `RegisterLogExporter`, each panicking on a duplicate name, with no exported lookup. Standard names delegate to `contrib/exporters/autoexport`, which mcp-anything already depends on; house names are additive. An unknown name fails at startup naming the supported values rather than silently disabling telemetry.
- [ ] 1.3 Official semantic conventions for resource attributes, from generated `goga/semconv` constants — never string literals.
- [ ] 1.4 Ordered shutdown flushing every provider, errors **joined** rather than first-wins.
- [ ] 1.5 Prometheus reader attached by default; a push exporter additive. Propagators via `contrib/propagators/autoprop`.
- [ ] 1.6 `otel.SetMeterProvider` is always called — epos omits it today and the wrapper must make that unreachable.
- [ ] 1.7 **`Instrumentation`** — the per-module handle: `For(module)`, `Start` returning `(ctx, func(error))` which records span status, the duration histogram and `error.type`, and `Logger()`. **`Start` returns the closer rather than a span the caller ends with a start time it captured itself** (design D15): the earlier three-argument `End(ctx, span, err, start)` was already mis-called in this design's own `migrate.Up`, recording zero duration for every migration.
- [ ] 1.8 `For` resolves through OTel's **global delegating providers** (`otel.Tracer` / `otel.Meter`), never by snapshotting a concrete one, and creates its instruments lazily. Before `Setup` those globals are no-ops, so a *library* (gopgql) can use goga modules without configuring telemetry and telemetry appears the moment the consuming binary calls `Setup`. This is load-bearing: every module's adapter table is a package-level `var` and adapters self-register from `init()`, both **before** `Setup`, and a snapshot would leave exactly those paths permanently unobserved while every test passed.
- [ ] 1.9 `Setup`'s cleanup return is `func()` — the only cleanup shape wire recognises (design D9) — calling `(*Telemetry).Shutdown(ctx)` under the configured timeout. It matters here even though wire arrives at M9: getting the shape wrong now means every later module inherits a shutdown nothing calls.
- [ ] 1.10 `goga/semconv`: the OTel Weaver registry for goga's own attributes, generated into the package. The *project-facing* half — the documented pattern for a project to keep its own registry — waits for M12 with the other generators.
- [ ] 1.11 `TestEveryModuleIsInstrumented` in its first form: the set of modules that called `telemetry.For` versus the module list, with the exempt set `{semconv, lint, di, registry, goga (root), app, gogatest}` and its per-entry justification (design D6). The module list is computed from the repo's exported packages, never hand-maintained. It has one instrumented entry today and grows with every milestone; failing in both directions is the point, so a later milestone cannot quietly add an eighth exempt name.
- [ ] 1.12 **Adopt in gopgql**: `telemetry.Setup` in its binary, and its MCP tools, pgx queries and goose runs go from unobserved to traced without any of those modules existing yet.
- [ ] 1.13 **Adopt in epos**: replace its metrics-only setup, which is the sharper test — epos wants a subset, so this is where design D2's "adoptable one package at a time" claim is first checked against a project that does not want the rest.

**The six parts (D18).** *Implementation:* 1.1–1.10. *Tests:* 1.11, plus
in-module span assertions written by hand until M7's fixture replaces them.

- [ ] 1.14 **Skill section**: the telemetry row of the routing table — *"needs
  traces, metrics or logs → `telemetry.Setup`, then `telemetry.For(module)`"* —
  and the enforcement-matrix rows for the two conventions this module introduces
  (attributes come from generated constants; every module resolves through the
  global providers).
- [ ] 1.15 **Linter**: `gogasemconv`, reporting a string-literal attribute key
  where a generated `goga/semconv` constant exists. Plus the `depguard` entry that
  makes the general rule real for this module — `go.opentelemetry.io/otel/sdk/*`
  is importable **only** from `goga/telemetry`, so a project cannot build its own
  provider stack beside goga's. This is the first use of M0's plugin scaffold.
- [ ] 1.16 **CI action**: none new. `setup-go`, `go-lint` and `go-test` shipped at
  M0 and cover this milestone; stated rather than left blank.

**Gate:** gopgql's and epos's telemetry PRs merged, and the owner's review passed.

---

## M2. `goga/serve` — *adopters: epos, then gopgql*

The owner: *"Http with telemetry for gopgql and epos."* The survey's strongest
seam evidence is here: `sysgo` requires gin directly and generates gin handlers,
`skill-test/go-service` serves the *same generator's* output on the standard
library, and `mcp-anything` uses chi — three router positions across three
projects, two of them generated by one tool.

**Same milestone, same package tree:** `muxrouter`, `chirouter`, `ginrouter`.
They are sub-packages so that a project pays for no router dependency it did not
ask for, and there is no useful version of this milestone with one router.

- [ ] 2.1 `Server` with bounded graceful shutdown on context cancellation, and header/read/write timeouts **set** rather than left unbounded.
- [ ] 2.2 **It installs no signal handling of its own** — it takes a `context.Context` and returns when cancelled. See the note under the Gate: the *"exactly one handler in the process"* half of this rule is M8's, and until then the adopting project keeps its own.
- [ ] 2.3 **Probe and metrics endpoints registered on a mux outside the `otelhttp` wrapper** so they never pollute request traces, with **no option that can move them inside**. go-service discovered this by hand; encoding it is the point of the wrapper.
- [ ] 2.4 `WithHealthCheck` / `WithReadinessCheck`. `migrate.Pending` becomes a supported readiness input at M5; the option shape must already admit it.
- [ ] 2.5 `Router` interface — `http.Handler` + `Handle` + `Use` + `Unwrap` — narrow enough that oapi-codegen's generated server needs nothing more. Two things are **normative**, not adapter detail: the pattern syntax is the framework's (`/users/{id}`) and each adapter translates it; and `Use` must be called before the first `Handle`, with adapters panicking otherwise. Unspecified, the same middleware silently covers all routes on mux, only later routes on gin, and panics on chi — three coverages from one program, which is the failure the seam exists to prevent.
- [ ] 2.6 The router table: `RegisterRouter(name, opener)`, name-keyed, **this module's own** (design D8). There is no URL here, so there is no scheme to get wrong — the earlier revision's `"router://"+name`, which resolved the scheme `router` and could never have found the gin adapter, is not expressible.
- [ ] 2.7 `RouterOpener.Open` takes **no settings**: gin, chi and mux each build an engine and read nothing the caller configured — `serve.New` applies the middleware, the handlers and the timeouts itself. So there is no `serve.Settings`, per design D5's rule that a module passes settings to an opener only where an adapter reads them. An opener parameter nothing reads is an abstraction with no user, and a shared registry was the only thing that would have forced one. *(The first milestone that actually exercises the settings-across-a-package-boundary shape is M4, where `pgxdb` reads pool sizing through `driver.Settings`.)*
- [ ] 2.8 Three adapters: **`muxrouter`** (standard library, the default), **`chirouter`** (mcp-anything's current router), **`ginrouter`** (sysgo's current router and the owner's target for skill-test). `ginrouter` translates `{id}` to gin's `:id`, uses `gin.Recovery()` and **omits `gin.Logger()`** — slog is the house logger.
- [ ] 2.9 **No router adapter carries instrumentation**: `serve.New` wraps whatever `Router` it gets in `otelhttp` exactly once, so all three are instrumented identically and no adapter author can forget (design D6).
- [ ] 2.10 Resolution is instrumented — `goga.serve.resolve` names the adapter that was selected (design D6). The span belongs to the **module**, not to `registry.Table`, which is a leaf carrying no `Instrumentation` (design D8).
- [ ] 2.11 **Adopt in epos**: its registry server moves onto `serve`, with the probes off the traced router.
- [ ] 2.12 **Adopt in gopgql**: its HTTP surface, still without `goga/mcp`, which is M6.

**The six parts (D18).** *Implementation:* 2.1–2.10. *Tests:* the three
adapters against one conformance suite, so `Router`'s normative claims — pattern
syntax, `Use`-before-`Handle` — are asserted identically for mux, gin and chi.

- [ ] 2.13 **Skill section**: the router row — *"needs an HTTP server →
  `serve.New`; needs a different router → blank-import an adapter"* — and the
  enforcement-matrix row for probes-off-the-traced-router.
- [ ] 2.14 **Linter**: `gogaserve`, reporting a direct `http.Server` literal or
  `http.ListenAndServe` in project code. Plus `depguard`: `gin-gonic/gin` and
  `go-chi/chi` importable only from their adapter packages, so a project that
  wants gin gets it by blank import rather than by depending on it directly —
  which is the owner's *"we don't use direct dependencies in code"* in its most
  literal form.
- [ ] 2.15 **CI action**: none new.

**Gate:** epos's and gopgql's server PRs merged. **Known incompleteness to state
in the review rather than discover:** design D15 requires exactly one signal
handler per process, owned by `goga/cli`. `cli` is M8. Between M2 and M8 an
adopting project installs its own handler and passes the context in; the
requirement that *only* `cli` does it is delivered at M8, and
`goga-service-lifecycle`'s delta spec marks which requirement lands where.

---

## M3. `goga/config` — *adopters: epos, then skill-test/go-service, then mcp-anything*

The owner: *"Config for all of them too."* Three projects use koanf with three
incompatible source arrangements, and all three authors had to explain precedence
in prose because koanf has none of its own.

- [ ] 3.1 `Load[T]` with the source order **fixed inside `Load`** — defaults → file → env → flags — *not* derived from the order options are passed. epos's posflag callback inverts its apparent precedence today; an option-ordered API would preserve that hazard.
- [ ] 3.2 Typed unmarshalling with duration and slice decoding; `WithDecodeHook` for the rest.
- [ ] 3.3 **Return the raw `*koanf.Koanf` alongside the typed value**, plus `Cut(path)` — go-service's subtree pattern breaks without it.
- [ ] 3.4 One documented env-key convention: prefix upper-snake, `__` separates path segments, `_` literal within a segment. Three projects chose three; this picks one and states it at the call site.
- [ ] 3.5 A missing file is non-fatal unless declared required; a missing required key fails naming the key.
- [ ] 3.6 `WithWatch` for reload — mcp-anything uses fsnotify today.
- [ ] 3.7 Instrumented (design D6): a span per load carrying which sources were used.
- [ ] 3.8 `Load[T]` is generic, so wire will not be able to provide it (design D9). The project writes the one-line instantiation. Recorded now, enforced at M9.
- [ ] 3.9 **Adopt in epos** — the flag-precedence inversion is the bug this milestone exists to remove, so epos goes first.
- [ ] 3.10 **Adopt in skill-test/go-service** (file→env with `__`, mapstructure hooks, `k.Cut()` subtrees) and **mcp-anything** (yaml + fsnotify reload). Between them they exercise every source arrangement the survey found.

**The six parts (D18).** *Implementation:* 3.1–3.8. *Tests:* the precedence
order asserted as a table, since three projects got it wrong three ways.

- [ ] 3.11 **Skill section**: the config row, and the enforcement-matrix row for
  fixed precedence — the one convention a reader is most likely to assume is
  option-ordered.
- [ ] 3.12 **Linter**: `depguard` banning `spf13/viper` outright (the house rule
  that has never had a mechanism) and restricting `knadh/koanf` to `goga/config`.
  Plus `gogaconfig`, reporting `os.Getenv` in project code outside `main`, which
  is how config precedence gets bypassed in practice.
- [ ] 3.13 **CI action**: none new.

**Gate:** epos merged and reviewed; go-service and mcp-anything merged.

---

## M4. `goga/database` — *adopter: gopgql; codiq when it exists*

The owner: *"For example postgres which could land to gopgql and codiq."* pgx has
three current consumers (gopgql, go-service, mcp-anything) and appears in no
house guidance. Design D7 follows `gocloud.dev`'s portable-API/driver split.

**Same milestone:** `goga/database/driver` (the interfaces), `pgxdb`, `sqldb`.
The second adapter is not optional — see 4.8.

- [ ] 4.1 `driver.DB`, `driver.Tx`, `driver.Rows` — narrow, and carrying **no** telemetry, exactly as `gocloud.dev/blob` keeps the tracer on `Bucket` and not on `s3blob`.
- [ ] 4.2 `driver.Settings` and `driver.Opener` — the accessor interface an adapter reads and the opener it implements, both declared by this module rather than by a shared generic (design D8). This is what keeps `database`'s settings struct unexported (design D5).
- [ ] 4.3 Portable `*database.DB` with unexported fields and `Open` as its **only** constructor — so no code path can produce an uninstrumented `*DB`. This is design D6 enforced structurally.
- [ ] 4.4 The driver table: `database.Register(scheme, opener)` for third-party adapters, `Schemes()` for diagnostics, and **no exported lookup** — nothing outside the module needs a raw `driver.DB`, and not exporting one closes the last goga-owned path around design D6.
- [ ] 4.5 `UnknownSchemeError` names the registered schemes **and** hints at the missing blank import, so a typo is self-diagnosing. Adapters self-register from `init()` and are selected by blank import, as in `gocloud.dev`.
- [ ] 4.6 Portable methods `Query`, `Exec`, `Tx`, `Close` — each a span (`goga.database.query`) plus duration and `error.type`, with the query timeout applied from settings. Resolution gets its own span (`goga.database.resolve`).
- [ ] 4.7 **`Query` returns a streaming result, so the portable `Rows` owns the cancel and the span** and closes both — once, idempotently — in `Rows.Close`. A `defer cancel()` in `Query` hands the caller rows that fail on the first `Next()` with `context canceled`, and a `defer end(err)` records a query duration that excludes the query (design D15). `Exec` is non-streaming and keeps the plain deferred shape; `Tx`'s timeout bounds the whole callback rather than each statement in it.
- [ ] 4.8 `Tx` commits on nil, rolls back on error **and on panic**. Three projects would otherwise each write this.
- [ ] 4.9 `SQLDB()` — the `database/sql` bridge, `stdlib.OpenDBFromPool` for pgx, so no caller learns that goose needs it. Returns `ErrNoSQLDB` for an adapter with no such handle.
- [ ] 4.10 `Unwrap()` returning the native handle (`*pgxpool.Pool`), because pgx's `CopyFrom`, `Batch` and `LISTEN/NOTIFY` must stay reachable.
- [ ] 4.11 **A second adapter in the same milestone: `goga/database/sqldb`**, over any `database/sql` driver (`sqlite://` for tests, `mysql://`). ~100 lines, and the only way to learn whether `driver.DB` is portable before three projects depend on it — a portable API with one implementation is an untested claim. It also gives M7's fixtures a container-free path.
- [ ] 4.12 `pgxdb` registering `postgres://` and `pgx://`, using **`exaring/otelpgx`** for wire-level spans plus `otelpgx.RecordStats` — already the house choice in mcp-anything. Two span levels on purpose; check they nest rather than double-count (Risks).
- [ ] 4.13 `WithSQLCommenter` injecting trace context into SQL comments.
- [ ] 4.14 Read gopgql's `migrate/` package (`diff.go`, `fold.go`, `rename.go`) before finalising the surface — it is the most PostgreSQL-specific code in the house.
- [ ] 4.15 **Adopt in gopgql**: its pgx usage moves behind the portable handle and inherits M1's telemetry.

**The six parts (D18).** *Implementation:* 4.1–4.14. *Tests:* the portable
conformance suite run against **both** `pgxdb` and `sqldb` — 4.11 exists so that
suite has a second implementation to be meaningful.

- [ ] 4.16 **Skill section**: the database row, the URL-scheme selection rule, and
  the enforcement-matrix row for "no exported lookup returns a raw `driver.DB`".
- [ ] 4.17 **Linter**: `gogatelemetry` — a type embedding a goga *driver*
  interface directly, bypassing the portable type, which is the one remaining path
  around design D6. Plus `depguard`: `jackc/pgx` importable only from
  `goga/database/*`, by **import path** and not by module (design D11's note).
- [ ] 4.18 **CI action**: **`go-test-integration` ships here, not at M7.**
  Applying D18 surfaced this: M4 is the first milestone whose tests need a
  container, so it is the first milestone with a tool that has to run in CI, and
  the previous revision left those tests running under `go-test` until M7 — three
  milestones of integration tests with no timeout, no tagged run and no artefact
  upload on failure. Tagged run, timeout, **artefacts uploaded even on failure**;
  no container-runtime setup step, which no project needed. M7 extends it rather
  than introducing it.

**Gate:** gopgql's database PR merged and reviewed. codiq does not exist
(checked 2026-07-30), so it is a later adopter, not a gate.

---

## M5. `goga/migrate` — *adopter: gopgql*

Pinned as the house migration engine (design D10). `gopgql` already requires
`pressly/goose/v3 v3.26.0` and ships its own `migrate/` package. It follows M4
because it takes the portable handle.

- [ ] 5.1 Wrap `goose.Provider`; goose's own API already takes variadic `ProviderOption`, consistent with design D14.
- [ ] 5.2 **Embedded migrations by default** (`WithFS(embed.FS)`), so a binary carries its own schema.
- [ ] 5.3 **A boot-time PostgreSQL session advisory lock** with a timeout, so two replicas starting together do not both migrate. Released on failure too, so a later attempt is not blocked.
- [ ] 5.4 `Pending()` as a readiness input, wired into M2's `/readyz`, so a service with a behind schema refuses traffic instead of erroring per request. This is the first cross-milestone seam, and it is why 2.4 shipped the option shape early.
- [ ] 5.5 Version table named once: `goga_db_version`.
- [ ] 5.6 A span per migration carrying its version and name (design D6) — this is how the 40-second migration gets found. The per-migration closer holds that migration's own start time; passing `time.Now()` as the start, as an earlier revision did, records zero for every one of them.
- [ ] 5.7 Errors name the version and file: `migration 20260714120000 (add_index.sql): ...`.
- [ ] 5.8 `Provider()` escape hatch.
- [ ] 5.9 **Adopt in gopgql**: its goose usage moves onto `goga/migrate`, and its migrations become observable.

**The six parts (D18).** *Implementation:* 5.1–5.8. *Tests:* two concurrent
`Up()` calls against one database, asserting the advisory lock serialises them —
the failure this module exists to prevent and the one nobody tests by hand.

- [ ] 5.10 **Skill section**: the migrations row, and the enforcement-matrix row
  for embedded-by-default.
- [ ] 5.11 **Linter**: `depguard` restricting `pressly/goose/v3` to
  `goga/migrate`, and banning the migration engines the house has ruled against
  (`golang-migrate/migrate`, `rubenv/sql-migrate`) so "goose is the house engine"
  is a build failure rather than a sentence in a skill.
- [ ] 5.12 **CI action**: none new; `go-test-integration` from M4 covers the
  container-backed migration tests.

**Gate:** gopgql's migration PR merged and reviewed.

---

## M6. `goga/mcp` — *adopters: gopgql, then mcp-anything*

Two current consumers at two SDK versions, neither instrumented: gopgql
(`go-sdk v1.6.1`, hand-rolled `mcp/server.go`, `mcp/query.go`,
`mcp/introspection.go`) and mcp-anything (`v1.4.1`). sysgo will be a third.

- [ ] 6.1 `Server` wrapping `sdkmcp.Server` with unexported fields and `New` as the only constructor.
- [ ] 6.2 `AddTool[In, Out]` as a free generic function (Go methods cannot carry type parameters) and **the only path to the wrapped SDK server** — which is what makes the instrumentation below unavoidable.
- [ ] 6.3 A span per tool call, resource read and prompt render, with duration and `error.type`, added by the wrapper and **not** by the tool author (design D6).
- [ ] 6.4 Tool failures returned in-band as `IsError` results, since that is what MCP specifies — not as protocol errors.
- [ ] 6.5 A per-tool timeout from settings, and the wrapper **recovers a panicking tool** into an in-band error result. Deferred, so the span still ends and the timeout context is still released on the panic path. Without it one tool's nil dereference takes down a server serving every other tool — and the wrapper is the only place that can be fixed once for every project.
- [ ] 6.6 Trace-context propagation: MCP defines no header, so the house convention is `traceparent` in the request `_meta`, extracted on the server and injected on the client. State it once here.
- [ ] 6.7 The transport table, name-keyed and this module's own (design D8): `stdio` (default), streamable `http`, `sse`.
- [ ] 6.8 `Handler()` so an MCP server mounts on M2's `serve.Server` — one port for HTTP and MCP, the sysgo case.
- [ ] 6.9 `Client` / `Connect` for the consumer side, instrumented symmetrically.
- [ ] 6.10 `SDK()` escape hatch.
- [ ] 6.11 **Adopt in gopgql**: port `mcp/server.go`, `mcp/query.go` and `mcp/introspection.go` onto `goga/mcp`. Its tools gain telemetry they do not have today.
- [ ] 6.12 **Adopt in mcp-anything**, which also settles the two-SDK-versions drift.

**The six parts (D18).** *Implementation:* 6.1–6.10. *Tests:* a panicking tool
asserted to come back as an in-band `IsError` with its span still ended — 6.5's
guarantee, which is worth a test precisely because it is invisible when it works.

- [ ] 6.13 **Skill section**: the MCP row, the `traceparent`-in-`_meta`
  convention, and the enforcement-matrix row for "`AddTool` is the only path to
  the wrapped server".
- [ ] 6.14 **Linter**: `gogamcp`, reporting a call on the result of `SDK()` that
  adds a tool, resource or prompt — the one route around the wrapper's
  instrumentation. Plus `depguard`: `modelcontextprotocol/go-sdk` importable only
  from `goga/mcp`, which also ends the two-versions drift structurally rather than
  by asking two repos to agree.
- [ ] 6.15 **CI action**: none new.

**Gate:** gopgql's MCP PR merged and reviewed; mcp-anything merged.

---

## M7. `goga/gogatest` — *adopters: gopgql, then epos*

Where the knowledge is most expensive and most duplicated: three incompatible
testcontainers strategies, and a godog bootstrap copy-pasted 5× in gopgql and 8×
in epos. It follows the modules it has to provide fixtures for.

- [ ] 7.1 `Postgres(t, ...opts)` returning a ready portable `*database.DB`, with **one** decided lifecycle and reset strategy, documenting why — weighing gopgql's snapshot/restore, epos's rejection of `CleanupContainer`, and go-service's shared-network stack.
- [ ] 7.2 Cleanup registered on the container's own lifetime, **not** the suite's `*T` — epos rejected `testcontainers.CleanupContainer` because that fills the disk across a long run, and the fixture must encode that conclusion.
- [ ] 7.3 Deterministic ordering: migrations before seed data, regardless of file naming (go-service had to rename scripts `01-`/`02-`/`03-` to force it). `WithMigrations` runs through M5's `goga/migrate`, so tests and production share one migration path.
- [ ] 7.4 Teardown that runs on failure and does not accumulate containers.
- [ ] 7.5 `Container(db)` escape hatch for anything the fixture does not model.
- [ ] 7.6 **`MCP(t, server, ...)`** — an in-memory transport pair, so an M6 server is testable without a subprocess or a port.
- [ ] 7.7 **`Telemetry(t, ...)`** — in-memory exporters plus `RequireSpan`, which is what makes design D6 assertable in every module's own tests. Every milestone from M1 on has been asserting its spans by hand until now; this is where that becomes a shared fixture, and the earlier modules' tests move onto it.
- [ ] 7.8 `Features(t, ...)` — the godog harness owning scenario reset, runner options and reporting, so a suite only registers steps; `@wip` excluded by default.
- [ ] 7.9 `T(ctx)` — the supported way for a step to reach the test handle. Both projects invented their own.
- [ ] 7.10 **Adopt in gopgql**: replace the 5× duplicated godog bootstrap and the `Snapshot`/`Restore` strategy. gopgql also has **172** hand-rolled `t.Errorf`/`t.Fatalf` against the workspace's own testify rule; migrating them belongs here rather than to the lint milestone that will later enforce it.
- [ ] 7.11 **Adopt in epos**: the 8× duplicated bootstrap, and its `track()` cleanup replaced by the fixture that encodes the same conclusion.
- [ ] 7.12 *(moved to M4 by D18 — see 4.18.)* `go-test-integration` shipped with the first milestone whose tests need a container, which is M4, not this one. What remains here is the extension in 7.15.

**The six parts (D18).** *Implementation:* 7.1–7.9. *Tests:* the fixtures have
their own — a fixture that leaks containers or reuses a dirty database is the
failure mode, and it only shows up under repetition, so the suite runs them twice.

- [ ] 7.13 **Skill section**: the testing row, and the enforcement-matrix rows for
  testify-over-`t.Errorf` and for the single container lifecycle.
- [ ] 7.14 **Linter**: `testifylint` and `usetesting` enabled in the template
  (this is where gopgql's **172** hand-rolled `t.Errorf`/`t.Fatalf` stop being a
  survey statistic and become a red build), plus `depguard` restricting
  `testcontainers-go` to `goga/gogatest` and `cucumber/godog` to the harness.
- [ ] 7.15 **CI action**: extend `go-test-integration` (shipped at M4) with the
  godog reporting artefacts; no new action.

**Gate:** gopgql's and epos's test-harness PRs merged and reviewed.

---

## M8. `goga/cli` — *adopters: epos, then gopgql*

- [ ] 8.1 `New` + `Run`, with `--config` wired into M3's `config.WithFile` and telemetry flags added by default.
- [ ] 8.2 `Run` always uses `ExecuteContext` with a signal-aware context. **epos calls `Execute()` today and has no signal handling at all**; there must be no path through goga to the plain `Execute`.
- [ ] 8.3 **This is the milestone that closes design D15's signal rule.** `cli.App.Run` is the only place in goga that calls `signal.NotifyContext`; `serve`, `mcp` and `grpc` take a context and stop when it is cancelled. Until now an adopting project owned its own handler (see M2's gate); from here the framework owns it, and the `goga-service-lifecycle` requirement that *exactly one* exists becomes satisfiable.
- [ ] 8.4 Non-zero exit status on failure.
- [ ] 8.5 `Cobra()` escape hatch; instrumented per design D6.
- [ ] 8.6 **Adopt in epos** — it is the project with no signal handling, so it is where the milestone's value is measurable.
- [ ] 8.7 **Adopt in gopgql**.

**The six parts (D18).** *Implementation:* 8.1–8.5. *Tests:* `Run` under a
delivered signal, asserting the context cancels and shutdown completes — epos has
no signal handling at all today, so this is the milestone's whole point.

- [ ] 8.8 **Skill section**: the CLI row, and the enforcement-matrix row for
  design D15's one-signal-handler-per-process rule, which becomes satisfiable
  here (see M2's gate).
- [ ] 8.9 **Linter**: `gogacli`, reporting `cobra.Command.Execute()` (rather than
  `ExecuteContext`) and any `signal.Notify` / `signal.NotifyContext` outside
  `goga/cli` — the mechanical form of D15's rule. Plus `depguard` restricting
  `spf13/cobra` to `goga/cli`.
- [ ] 8.10 **CI action**: none new.

**Gate:** epos's CLI PR merged and reviewed.

---

## M9. `goga/di` + `goga/app` — *adopters: skill-test/go-service, then sysgo*

The owner: *"I don't see di with wire. It's very important. I really like it and
it's not enforced."* Design D9.

**Two directories, one deliverable, and the reason is structural:** `di`'s
provider sets exist to build an `app.App`, and `app.App`'s unexported fields are
what makes a generated injector the only practical route. Either alone is
inert. The `go-generate-check` action ships with them because it is the
enforcement, not an extra.

- [ ] 9.1 Pin **`github.com/goforj/wire`**, not the archived `google/wire`, as a `tool` directive — `skill-test/go-service` already pins the fork at v1.2.0.
- [ ] 9.2 Every module shipped so far exports a `ProviderSet`; each module's set attaches its own telemetry provider, so importing a module cannot mean importing it uninstrumented. Modules that arrive later ship theirs with themselves.
- [ ] 9.3 `di.Core`, `di.Service`, `di.Data`, `di.MCP` unions.
- [ ] 9.4 `app.App` with **unexported fields and no exported constructor**, so the practical way to build one is a generated injector. `app.Run` runs the surfaces under an errgroup and shuts down in reverse construction order — surfaces drain, then the database closes, then telemetry flushes last so the shutdown itself is observable.
- [ ] 9.5 The four wire mechanics, settled so no project discovers them late (design D9): cleanups are `func()`, never `func(context.Context) error` — a shutdown of the wrong shape is a value wire provides and nothing calls, so a service silently stops flushing spans on exit; wire cannot supply variadic options, so module sets provide the constructor and `di.Defaults` binds an empty `[]Option` per module; providers take named types (`database.URL`, `serve.Addr`), never bare `string`, because wire's graph is keyed by type; and `config.Load[T]` is generic, so the project writes its own one-line instantiation.
- [ ] 9.6 One `//go:generate go tool wire ./...` line in the project template; `wire_gen.go` committed.
- [ ] 9.7 **`go-generate-check`** — `go generate ./... && git diff --exit-code`. **No repo has this today**, and it is the single enforcement point for wire now and for sqlc, buf, oapi-codegen, OTel Weaver and mockgen at M12. A stale or missing `wire_gen.go` is a red build. **This is the actual enforcement**; the rest is convention.
- [ ] 9.8 **Adopt in skill-test/go-service**, which already uses the fork and is the only project with a working wire setup to compare against.
- [ ] 9.9 **Retarget sysgo's templates to emit `goga.*`** (design D3): `main.go.tmpl` collapses from a TODO-riddled cobra skeleton to roughly `app.Run(ctx, a)`, and `providers.go.tmpl` to a `wire.Build` over goga's ProviderSets. This is a *reduction* in what sysgo generates. It needs M1, M2, M8 and M9 to be real, which is why it is here and not earlier.

**The six parts (D18).** *Implementation:* 9.1–9.6. *Tests:* the generated
injector compiles and `app.Run` shuts down in reverse construction order, with
telemetry flushed last — 9.4's claim, asserted rather than described.

- [ ] 9.10 **Skill section**: the DI row, the four wire mechanics from 9.5, and
  the enforcement-matrix row for generation freshness.
- [ ] 9.11 **Linter**: `gogawire` — goga providers constructed outside a
  `wireinject` injector. Plus `depguard` banning the **archived**
  `github.com/google/wire` outright, so "which wire" is answered by the build
  rather than by remembering.
- [ ] 9.12 **CI action**: `go-generate-check` (9.7) — this milestone's own, and
  the one D18 part that was already in the right place.

**Gate:** go-service's wiring PR merged and reviewed; sysgo's template PR merged.

---

## M10. `goga/client` — *adopters: skill-test/go-service, then mcp-anything*

- [ ] 10.1 `client.New` — retries with backoff over `retryablehttp` (already in go-service), `otelhttp` transport underneath for client spans, context propagation and client metrics, plus `gobreaker` (mcp-anything's choice).
- [ ] 10.2 Retries are **logged, not silently absorbed**, through the module logger.
- [ ] 10.3 Retry counts and backoff configurable, never hardcoded.
- [ ] 10.4 `HTTP()` returns the underlying client, so any library taking one can be used.
- [ ] 10.5 **No adapter table.** `goga/client` has one transport and no second candidate, so it gets none until it does — an adapter table with a single entry is the abstraction design D7 warns about, and design D8's table lists the five modules that do have one precisely so this absence is deliberate rather than an omission.
- [ ] 10.6 **Adopt in skill-test/go-service** (retryablehttp today) and **mcp-anything** (gobreaker today).

**The six parts (D18).** *Implementation:* 10.1–10.5. *Tests:* a retry storm
asserted to be logged and bounded, and the breaker asserted to open — 10.2 exists
because silent retries are how latency becomes unexplainable.

- [ ] 10.7 **Skill section**: the client row, and the enforcement-matrix row for
  "retries are logged, never absorbed".
- [ ] 10.8 **Linter**: `gogaclient`, reporting `http.DefaultClient` or an
  `http.Client` literal in project code — a client with no timeout is the single
  most common Go production defect and `goga/client` exists to make it
  unreachable. Plus `depguard` restricting `hashicorp/go-retryablehttp` and
  `sony/gobreaker` to `goga/client`.
- [ ] 10.9 **CI action**: none new.

**Gate:** go-service's client PR merged and reviewed.

---

## M11. The remaining shared actions — *adopters: gopgql, then epos*

**This milestone has been dissolved by D18 and what is left is small.** It used
to be `goga/lint`: one milestone holding every rule for every module, arriving
after eleven milestones had already shipped unenforced. The owner has forbidden
exactly that — *"splitting functionality and enforcement is not allowed"* — so
the rules moved to the milestones they enforce (1.15, 2.14, 3.12, 4.17, 5.11,
6.14, 7.14, 8.9, 9.11, 10.8) and the plugin mechanism moved to M0 (0.4b), which
is where it has to be for M1 to have anything to build on.

Two rules genuinely belong to no single module, and they stay here with the
actions:

- [ ] 11.1 `gogaparamstruct` — an exported constructor whose final **non-variadic** parameter is a struct (or pointer to one) declared in the same package with at least one exported field, and which takes no variadic option parameter. The looser "final parameter is a struct" fires on `New(t *testing.T)` and on `migrate.New(db *database.DB, …)`; a lint rule that cries wolf gets disabled. *(In goga itself this rule has nothing to find, because the settings structs are unexported — design D5, and D14 confirms this now holds for adapter settings too. Its job is project code.)* It is cross-cutting by construction: it is the one rule that is about the *shape* of every goga surface rather than about one module's dependency.
- [ ] 11.2 `gogalayout` — run against goga itself: flat, no `pkg/`, no `internal/`. Also cross-cutting, and also not attributable to a module.
- [ ] 11.3 The remaining composite actions, which have no Go dependency and belong to no module: `go-vuln` (one action replacing three mechanisms), `go-release` (goreleaser, with a `docker` flag covering the only real divergence), `pages-deploy` / `pr-preview` carrying the `keep_files` fix so the third repo does not learn it the hard way. `gopgql` and `epos` share a docs-workflow bug fixed by copy-paste today (*"same bug, same fix as gopgql#24"*).
- [ ] 11.4 **Revisit 0.4d**: if golangci-lint has shipped a release built on a new enough `golang.org/x/tools` by now, drop goga's build-from-source step and return to the upstream prebuilt action (design D17).
- [ ] 11.5 **Skill section**: the two cross-cutting rules' enforcement-matrix rows.
- [ ] 11.6 **Adopt in gopgql and epos**: the shared actions replace four golangci-lint invocations at three versions.

**Gate:** gopgql's and epos's CI PRs merged and reviewed.

---

## M12. `goga/codegen` + `goga/grpc` — *adopter: skill-test/go-service; codiq for sqlc and buf*

sqlc, buf, oapi-codegen and OTel Weaver produce code, so goga owns the
invocation, the config and the runtime seam — not the generator (design D11).
**This is the one milestone whose main tools have no current consumer**, which is
why it is late and why its parts are gated separately below.

- [ ] 12.1 One `//go:generate` entry point per project, so `go generate ./...` is the whole generation story and M9's check has a single thing to run.
- [ ] 12.2 `oapi-codegen.yaml` template; mount the generated `StrictServerInterface` through M2's `serve.Router` so one generated server runs on stdlib, gin or chi. *(Current consumers: go-service, sysgo — this half can land now.)*
- [ ] 12.3 `mockgen` `tool` directive and `//go:generate` lines; freshness enforced by M9's check, never by review.
- [ ] 12.4 `goga/semconv`'s project-facing half: the documented pattern for a project to keep its own registry and generate into its own package, while goga's own attributes stay in goga.
- [ ] 12.5 `sqlc.yaml` template — engine postgresql, `sql_package: pgx/v5`, `emit_pointers_for_null_types`. *(Anticipated consumer: codiq.)*
- [ ] 12.6 **`goga/database/sqlcdb`** — satisfy sqlc's generated `DBTX` interface (`Exec`, `Query`, `QueryRow`, `CopyFrom`, `SendBatch`) from M4's portable `*database.DB`, so generated sqlc code inherits design D6's telemetry with no generated line changing. **`DBTX`'s signatures are pgx types, so this seam is pgx-only**: `New` returns `ErrNotPgx` for any other adapter rather than being documented as adapter-neutral. *(Anticipated consumer: codiq.)*
- [ ] 12.7 `buf.yaml` + `buf.gen.yaml` templates — lint plus breaking-change detection against `main`, `protoc-gen-go` and `protoc-gen-go-grpc`. *(Anticipated consumer: codiq.)*
- [ ] 12.8 **`goga/grpc`** — server and client constructors for buf-generated stubs with `otelgrpc` stats handlers, reflection and health service on by default, `Register(func(grpc.ServiceRegistrar))` so the generated output is untouched. gRPC gets the same treatment HTTP gets. The client constructor is `NewClient`, not `Dial`: `grpc.Dial` is deprecated upstream, and a house wrapper that ships it teaches it to every adopter. *(Anticipated consumer: codiq.)*

**The six parts (D18).** *Implementation:* 12.1–12.8. *Tests:* generated output
compiles against the runtime seams and `go generate ./...` is idempotent.

- [ ] 12.9 **Skill section**: the codegen and gRPC rows, and the
  enforcement-matrix row for generation freshness — pointing at M9's
  `go-generate-check` rather than restating it.
- [ ] 12.10 **Linter**: `depguard` restricting `google.golang.org/grpc` to
  `goga/grpc`, and `gogagrpc` reporting `grpc.Dial` (deprecated upstream) in
  favour of `NewClient`. The generated-code paths are excluded by path, since a
  generator's output is not project code to be enforced against.
- [ ] 12.11 **CI action**: none new — `go-generate-check` shipped at M9 (9.7) and
  is the enforcement point for every generator added here.

**Gate, in two parts.** 12.1–12.4 gate on go-service's generation PR being
merged. **12.5–12.8 do not start until `codiq` exists** — it did not on
2026-07-30. Building sqlc, buf and gRPC surfaces with no project to adopt them is
exactly what the milestone rule is for.

---

## M13. The skill's closing audit — *adopter: every project that has adopted a milestone*

**Also dissolved by D18.** The skill used to be written here, once, against
fourteen modules delivered over months — which is both the "splitting" the owner
forbade and the worst possible moment to write documentation. Its **skeleton**
now ships at M0 (0.4c) and every milestone adds its own rows as it lands (1.14,
2.13, 3.11, 4.16, 5.10, 6.13, 7.13, 8.8, 9.10, 10.7, 11.5). What is left is the
audit that can only be done once everything is in.

Per the issue, only the skill's **pseudo structure** is fixed by this spec —
section headings and the routing table, not its prose.

- [ ] 13.1 Audit the routing table for completeness and staleness: one row per delivered module, no row for a module that has no milestone. Entries for undelivered modules are absent, not aspirational.
- [ ] 13.2 Confirm it does **not** re-teach cobra, koanf, otel, pgx, goose or the MCP SDK — that is the library's job now, and duplicating it is how guidance drifts. This is an audit rather than a writing task because each milestone wrote its own section and the drift, if any, is between them.
- [ ] 13.3 Audit the **enforcement matrix**: every house convention paired with the mechanism that enforces it (compile, lint, or merge), and **no row whose mechanism is empty**. Per design D5 an unenforced convention is a goga defect; under D18 it is also evidence that some milestone shipped incomplete, so a gap here is a bug report against a specific milestone, not a caveat to publish.
- [ ] 13.4 Confirm the escape hatch is named per module (`Unwrap()`, `Config.K`, `Server.HTTP()`, `Migrator.Provider()`, `mcp.Server.SDK()`).
- [ ] 13.5 State the milestone status of each module, so an agent reading it mid-programme does not route a project to a package that does not exist yet. **`goga/components` in particular has no milestone** (D12, D16).
- [ ] 13.6 Record the **Go version requirement** prominently (D17): adopting any goga package moves the project to Go 1.27, and until 1.27.0 ships that is a release candidate.

**Gate:** the skill is in use on the next adoption PR without the agent reaching
past it into the wrapped libraries.

---

## Workspace guidance — *runs alongside; not a goga package*

Design D13's contradiction is live in **merged** guidance and is not gated on any
milestone. It should be fixed early, because every milestone's adoption PR is
written by an agent reading it.

- [ ] G.1 **Fix the live layout contradiction** (design D13). Both skills are **on `main`** — the spf13 `go` skill landed in `37bd574` (workspace#31) — so this is repairing guidance already in force, not getting ahead of a merge. The conflict is over `internal/` **as the default home**: `go-project-scaffold` prescribes `internal/app` / `internal/config` / `internal/server` / `internal/<feature>` plus `pkg/`, while the spf13 skill calls `internal/`-by-default an anti-pattern and prescribes top-level packages one level deep. Not the hexagonal question — `go-project-scaffold` explicitly declines to decide that one.
- [ ] G.2 State the part the widened scope already settles, so the remaining question is small: adapter organisation is decided by design D7 — driver interface adjacent to its portable type, technology-named adapter leaves, **no `port/` or `adapter/` layer directory** — and `go-project-scaffold` already names **sysgo** as the eventual enforcement point, which design D3 confirms.
- [ ] G.3 Take the remaining decision to the owner: the default home for a service's own non-adapter code (top-level / `internal/` / `pkg/`). Recommend the spf13 position for services, since it is the side goga's own adapter shape lands on, and amend `go-project-scaffold` accordingly. goga stays layout-agnostic either way (design D1); goga's own flat tree follows the issue and is a statement about a *library*, not the house answer for services.
- [ ] G.4 Raise separately on **skill-test** that its `AGENTS.md` contradicts itself — line 64 asks for consumer-side ports, line 70 prescribes a centralised `internal/port`. That is skill-test's to fix, not the workspace's.
- [ ] G.5 After M13, re-measure the compliance numbers from the proposal and record them, so the claim is checkable rather than rhetorical.

---

## Deferred — no milestone

*(`goga/registry` was here in the previous revision. It is no longer deferred:
Go 1.27 ships generic methods, the spike the owner asked for confirmed the shape
compiles, and it lands in **M0** as task 0.4a. Design D8 records what was proven
and the one part of the owner's formulation that does not compile.)*

### `goga/components` — until a consumer exists

In scope on the owner's instruction (*"Weaver it's important"*), with no project
to adopt it: no current consumer, an archived upstream (`ServiceWeaver/weaver`,
checked 2026-07-30), and the largest invented surface in the design. Design D12
and D16.

- [ ] C.1 **Does not start until a consumer exists.** The owner's milestone rule gates on a real adoption, and this module has none; the two instructions pull against each other here, and the resolution is a schedule rather than a scope change.
- [ ] C.2 When it does start: `Component`, `Ref[T]`, `Deployer`, and the module's own name-keyed deployer table. **`Ref[T]`'s `T` is constrained to an interface, enforced by the local deployer at registration** — a distributing deployer returns a generated stub, never the concrete struct the local one stored, so `Ref[*myComponent]` is a reference that passes tests and fails in production. `Get` is a checked assertion returning a typed error; the type parameter saves the caller writing the assertion, it does not remove it.
- [ ] C.3 Portable `Graph` owning the telemetry, so a component graph is traceable regardless of deployer (design D6).
- [ ] C.4 `local` deployer first — in-process, the default, and what tests use. Then `k8s`. The `weaver` deployer is written with its first consumer, not against an archived dependency with nobody to use it.
