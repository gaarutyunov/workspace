**Sequencing rule (design D16), on the owner's instruction:** *"We shouldn't
deliver everything at once. Split the spec into clear milestones. Each milestone
we will deliver one package. I will carefully review it. We will migrate gopgql
and some other project to it and then continue to the next."*

So this file is ordered by **milestone**, not by module. Three rules apply to
every one of them:

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

**Two things are deferred rather than scheduled**, both recorded at the end:
`goga/registry` (design D8 — Go has no generic methods yet) and
`goga/components` (design D12, D16 — no consumer exists).

---

## M0. Repo foundations — *not a package; nobody adopts this*

goga is empty: one commit, a one-line README. Nothing can be delivered from it
until this exists. It is deliberately the only milestone with no external
adopter, and it is small.

- [ ] 0.1 `go mod init github.com/gaarutyunov/goga`; Go version matching the newest project (1.26.x).
- [ ] 0.2 Package layout **flat, no `pkg/`, no `internal/`** for goga's own code, per the issue. Adapters are sub-packages of their module (`database/pgxdb`) so an adapter's dependency stays optional.
- [ ] 0.3 The root `goga` package: `goga.Option[S]` and `goga.Apply` (design D14). It holds **only** these and imports nothing but the standard library. The composition root is `goga/app` and arrives at M9 — every module imports the root, and the composition root imports every module, so the two cannot be one package.
- [ ] 0.4 `.golangci.yml`, `Makefile`, `.goreleaser.yaml` — these double as the templates goga ships (design D3's carve-out).
- [ ] 0.5 `go.mod` `tool` directive block for the whole generator set — wire (`goforj/wire`), oapi-codegen, mockgen, sqlc, buf, OTel Weaver, goose — following `skill-test/go-service`, which already does this.
- [ ] 0.6 The three composite actions goga's own CI needs now: `setup-go` (Go version defaults to what `go.mod` says), `go-lint` (gofmt gate, `go vet`, golangci-lint via the official action at a pinned version), `go-test` (race, atomic coverage, summary and artifact). Actions SHA-pinned internally; projects pin **goga** and nothing else.
- [ ] 0.7 The cross-cutting Go conventions of design D15, written down once here and applied by every milestone that follows: named result parameters on any method that opens a span; `Instrumentation.Start` returns the closer, never a `(span, start)` pair; a method returning a streaming result never cancels that result's context; one signal handler per process, owned by `cli`; errors wrapped `fmt.Errorf("goga/<module>: <op>: %w", err)` with a typed error wherever a caller must branch.
- [ ] 0.8 The house settings shape, also once (design D5, D14): each module declares an **unexported** `settings` struct plus `type Option = goga.Option[settings]`; where the module has adapters it also exports a `Settings` **interface** of accessors for them to read. **No exported struct anywhere in the option surface, and no goga entry point takes a settings value.**
- [ ] 0.9 **Read Yokai's module decomposition and `gocloud.dev/blob`'s portable/driver split before fixing package boundaries** (design D7, Risks).

**Gate:** goga's own CI is green on an empty-but-buildable module. No external
adoption to wait for; this is the only milestone where that is true.

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
- [ ] 1.2 Exporter tables, name-keyed, **this module's own** (design D8 — there is no shared registry): `RegisterTraceExporter` / `RegisterMetricExporter` / `RegisterLogExporter`, each panicking on a duplicate name, with no exported lookup. Standard names delegate to `contrib/exporters/autoexport`, which mcp-anything already depends on; house names are additive. An unknown name fails at startup naming the supported values rather than silently disabling telemetry.
- [ ] 1.3 Official semantic conventions for resource attributes, from generated `goga/semconv` constants — never string literals.
- [ ] 1.4 Ordered shutdown flushing every provider, errors **joined** rather than first-wins.
- [ ] 1.5 Prometheus reader attached by default; a push exporter additive. Propagators via `contrib/propagators/autoprop`.
- [ ] 1.6 `otel.SetMeterProvider` is always called — epos omits it today and the wrapper must make that unreachable.
- [ ] 1.7 **`Instrumentation`** — the per-module handle: `For(module)`, `Start` returning `(ctx, func(error))` which records span status, the duration histogram and `error.type`, and `Logger()`. **`Start` returns the closer rather than a span the caller ends with a start time it captured itself** (design D15): the earlier three-argument `End(ctx, span, err, start)` was already mis-called in this design's own `migrate.Up`, recording zero duration for every migration.
- [ ] 1.8 `For` resolves through OTel's **global delegating providers** (`otel.Tracer` / `otel.Meter`), never by snapshotting a concrete one, and creates its instruments lazily. Before `Setup` those globals are no-ops, so a *library* (gopgql) can use goga modules without configuring telemetry and telemetry appears the moment the consuming binary calls `Setup`. This is load-bearing: every module's adapter table is a package-level `var` and adapters self-register from `init()`, both **before** `Setup`, and a snapshot would leave exactly those paths permanently unobserved while every test passed.
- [ ] 1.9 `Setup`'s cleanup return is `func()` — the only cleanup shape wire recognises (design D9) — calling `(*Telemetry).Shutdown(ctx)` under the configured timeout. It matters here even though wire arrives at M9: getting the shape wrong now means every later module inherits a shutdown nothing calls.
- [ ] 1.10 `goga/semconv`: the OTel Weaver registry for goga's own attributes, generated into the package. The *project-facing* half — the documented pattern for a project to keep its own registry — waits for M12 with the other generators.
- [ ] 1.11 `TestEveryModuleIsInstrumented` in its first form: the set of modules that called `telemetry.For` versus the module list, with the exempt set `{semconv, lint, di}` (design D6). It has one entry today and grows with every milestone; failing in both directions is the point, so a later milestone cannot quietly add a fourth exempt name.
- [ ] 1.12 **Adopt in gopgql**: `telemetry.Setup` in its binary, and its MCP tools, pgx queries and goose runs go from unobserved to traced without any of those modules existing yet.
- [ ] 1.13 **Adopt in epos**: replace its metrics-only setup, which is the sharper test — epos wants a subset, so this is where design D2's "adoptable one package at a time" claim is first checked against a project that does not want the rest.

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
- [ ] 2.10 Resolution is instrumented — `goga.serve.resolve` names the adapter that was selected (design D6). With no shared registry this span belongs to the module.
- [ ] 2.11 **Adopt in epos**: its registry server moves onto `serve`, with the probes off the traced router.
- [ ] 2.12 **Adopt in gopgql**: its HTTP surface, still without `goga/mcp`, which is M6.

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
- [ ] 7.12 `go-test-integration` composite action — tagged run, timeout, **artefacts uploaded even on failure**; no container-runtime setup step, which no project needed.

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

**Gate:** go-service's wiring PR merged and reviewed; sysgo's template PR merged.

---

## M10. `goga/client` — *adopters: skill-test/go-service, then mcp-anything*

- [ ] 10.1 `client.New` — retries with backoff over `retryablehttp` (already in go-service), `otelhttp` transport underneath for client spans, context propagation and client metrics, plus `gobreaker` (mcp-anything's choice).
- [ ] 10.2 Retries are **logged, not silently absorbed**, through the module logger.
- [ ] 10.3 Retry counts and backoff configurable, never hardcoded.
- [ ] 10.4 `HTTP()` returns the underlying client, so any library taking one can be used.
- [ ] 10.5 **No adapter table.** `goga/client` has one transport and no second candidate, so it gets none until it does — an adapter table with a single entry is the abstraction design D7 warns about, and design D8's table lists the five modules that do have one precisely so this absence is deliberate rather than an omission.
- [ ] 10.6 **Adopt in skill-test/go-service** (retryablehttp today) and **mcp-anything** (gobreaker today).

**Gate:** go-service's client PR merged and reviewed.

---

## M11. `goga/lint` — *adopters: gopgql, then epos*

The mechanism that makes "enforce everything with goga" real rather than
aspirational. `mcp-anything` already depends on
`golangci/plugin-module-register`, so a custom plugin module is proven in-house.
It comes after the modules because a rule needs something to enforce against.

- [ ] 11.1 A golangci-lint plugin module, wired into the shipped `.golangci.yml` template.
- [ ] 11.2 `gogaparamstruct` — an exported constructor whose final **non-variadic** parameter is a struct (or pointer to one) declared in the same package with at least one exported field, and which takes no variadic option parameter. The looser "final parameter is a struct" fires on `New(t *testing.T)` and on `migrate.New(db *database.DB, …)`; a lint rule that cries wolf gets disabled. *(In goga itself this rule now has nothing to find, because the settings structs are unexported — design D5. Its job is project code.)*
- [ ] 11.3 `gogawire` — goga providers constructed outside a `wireinject` injector.
- [ ] 11.4 `gogatelemetry` — a type embedding a goga *driver* interface directly, bypassing the portable type. This is the rule that covers the one remaining path around design D6: a project that registers its own adapter and calls its own opener.
- [ ] 11.5 `gogasemconv` — string-literal attribute keys where a generated constant exists.
- [ ] 11.6 `gogalayout` — run against goga itself: flat, no `pkg/`, no `internal/`.
- [ ] 11.7 `depguard` entries banning the **import paths** `spf13/viper`, `google/wire`, non-goose migration engines, and `jackc/pgx` outside `goga/database/*`. Import paths, not modules — viper appears as an *indirect* module via golangci-lint, and a module-level ban would be wrong.
- [ ] 11.8 `testifylint` and `usetesting` enabled in the template.
- [ ] 11.9 The remaining composite actions, which have no Go dependency and ride along here: `go-vuln` (one action replacing three mechanisms), `go-release` (goreleaser, with a `docker` flag covering the only real divergence), `pages-deploy` / `pr-preview` carrying the `keep_files` fix so the third repo does not learn it the hard way. `gopgql` and `epos` share a docs-workflow bug fixed by copy-paste today (*"same bug, same fix as gopgql#24"*).
- [ ] 11.10 **Adopt in gopgql and epos**: the shared actions replace four golangci-lint invocations at three versions.

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

**Gate, in two parts.** 12.1–12.4 gate on go-service's generation PR being
merged. **12.5–12.8 do not start until `codiq` exists** — it did not on
2026-07-30. Building sqlc, buf and gRPC surfaces with no project to adopt them is
exactly what the milestone rule is for.

---

## M13. The skill — *adopter: every project that has adopted a milestone*

It routes to entry points, so it needs entry points to route to. Per the issue,
only its **pseudo structure** is fixed here — section headings and the routing
table, not its prose.

- [ ] 13.1 A routing table: what an agent needs → which goga entry point. Config, telemetry, server, client, router, database, migrations, MCP, gRPC, DI, tests. Entries for modules that have no milestone yet are absent, not aspirational.
- [ ] 13.2 It does **not** re-teach cobra, koanf, otel, pgx, goose or the MCP SDK — that is the library's job now, and duplicating it is how guidance drifts.
- [ ] 13.3 It carries the **enforcement matrix** from the design: each house convention paired with the mechanism that enforces it (compile, lint, or merge). Per design D5 there is **no list of conventions goga leaves to the reader** — if a convention has no mechanism, that is a goga defect to fix, not a caveat to publish.
- [ ] 13.4 It names the escape hatch per module (`Unwrap()`, `Config.K`, `Server.HTTP()`, `Migrator.Provider()`, `mcp.Server.SDK()`). Escape hatches are documented; unenforced conventions are not, because there are none.
- [ ] 13.5 It states the milestone status of each module, because an agent reading it mid-programme must not route a project to a package that does not exist yet.

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

### `goga/registry` — until Go ships generic methods

The owner: *"I think we should skip the registry because go doesn't ship generic
methods yet. Once it does — which is proposed and the proposal seems to be
approved — we will add registry that will stores structs satisfying interfaces
and returning concrete types."* Design D8.

- [ ] R.1 **Not built.** Each adapter-bearing module keeps its own ~30-line table instead: `Register` panicking on a duplicate, an unexported lookup, `Schemes()`. Six modules, one shape, specified once in `goga-adapter-resolution` so the six cannot drift.
- [ ] R.2 The shape it takes when it returns, recorded now so nothing is designed against a different one: generic over the **port** — the interface an adapter satisfies, `driver.DB` / `serve.Router` / `mcp.Transport` — with adapters as structs satisfying that interface, stored as such and returned as their concrete type. That last half is the method type parameter Go cannot express today.
- [ ] R.3 When it lands, the six tables collapse into it behind unchanged public surfaces. `Register` keeps its signature; nothing outside goga changes.

### `goga/components` — until a consumer exists

In scope on the owner's instruction (*"Weaver it's important"*), with no project
to adopt it: no current consumer, an archived upstream (`ServiceWeaver/weaver`,
checked 2026-07-30), and the largest invented surface in the design. Design D12
and D16.

- [ ] C.1 **Does not start until a consumer exists.** The owner's milestone rule gates on a real adoption, and this module has none; the two instructions pull against each other here, and the resolution is a schedule rather than a scope change.
- [ ] C.2 When it does start: `Component`, `Ref[T]`, `Deployer`, and the module's own name-keyed deployer table. **`Ref[T]`'s `T` is constrained to an interface, enforced by the local deployer at registration** — a distributing deployer returns a generated stub, never the concrete struct the local one stored, so `Ref[*myComponent]` is a reference that passes tests and fails in production. `Get` is a checked assertion returning a typed error; the type parameter saves the caller writing the assertion, it does not remove it.
- [ ] C.3 Portable `Graph` owning the telemetry, so a component graph is traceable regardless of deployer (design D6).
- [ ] C.4 `local` deployer first — in-process, the default, and what tests use. Then `k8s`. The `weaver` deployer is written with its first consumer, not against an archived dependency with nobody to use it.
