Sequencing rule (design D4): scope is the issue's whole tool list. Modules whose
consumer is **current** are built first; modules whose consumer is **anticipated**
ship their surface, config template and CI half in v1 and their adapter body when
the consumer lands. Being anticipated changes ordering, never scope.

## 1. Repo foundations

goga is empty — one commit, a one-line README.

- [ ] 1.1 `go mod init github.com/gaarutyunov/goga`; Go version matching the newest project (1.26.x).
- [ ] 1.2 Package layout **flat, no `pkg/`, no `internal/`** for goga's own code, per the issue. Adapters are sub-packages of their module (`database/pgxdb`) so an adapter's dependency stays optional.
- [ ] 1.3 `.golangci.yml`, `Makefile`, `.goreleaser.yaml` — these double as the templates goga ships (design D3's carve-out).
- [ ] 1.4 `go.mod` `tool` directive block for the whole generator set — wire (`goforj/wire`), oapi-codegen, mockgen, sqlc, buf, OTel Weaver, goose — following `skill-test/go-service`, which already does this.
- [ ] 1.5 **Read Yokai's module decomposition and `gocloud.dev/blob`'s portable/driver split before fixing package boundaries** (design D7, Risks).

## 2. `goga` — house API conventions

The two spec-wide invariants. Everything below depends on these landing first.

- [ ] 2.1 `goga.Option[S]` and `goga.Apply` (design D14) — variadic options that can validate and fail at the call site.
- [ ] 2.2 Every module declares an **unexported** `settings` struct plus an exported `type Option = goga.Option[settings]`, so a caller cannot construct a parameter struct. **No exported parameter struct anywhere in goga's public surface.**
- [ ] 2.3 Option naming: `With<Noun>` sets, `With<Noun>s(...T)` appends, `Without<Noun>` removes. **`WithoutTelemetry` does not exist** (design D6).
- [ ] 2.4 Every wrapper exposes its underlying object — `Unwrap()` where the type is opaque, a named accessor otherwise (`Config.K`, `Server.HTTP()`, `Migrator.Provider()`, `mcp.Server.SDK()`).
- [ ] 2.5 `TestEveryModuleIsInstrumented` — walks the module list, fails on a module with no registered `Instrumentation`. This is what makes the telemetry invariant checkable rather than asserted.

## 3. `goga/registry` — the generic adapter registry

One generic implementation used by every adapter-bearing module (design D8), not
a hand-rolled map per module.

- [ ] 3.1 `Registry[T, S]` with `Register`, `Open`, `Schemes`, `Has`; `Opener[T, S]` and `OpenerFunc[T, S]`.
- [ ] 3.2 `Register` **panics** on a duplicate scheme, following `gocloud.dev`'s `URLMux` — a duplicate is a programming error in an `init()`, not a runtime condition.
- [ ] 3.3 `UnknownSchemeError` names the registered schemes **and** hints at the missing blank import, so a typo is self-diagnosing.
- [ ] 3.4 `Open` is instrumented (design D6) — "which adapter did this process resolve" is an operational question.
- [ ] 3.5 Adapters are selected by blank import and self-register from `init()`, as in `gocloud.dev`.
- [ ] 3.6 Instantiated by: `database` (drivers), `serve` (routers), `telemetry` (exporters), `mcp` (transports), `components` (deployers), `client` (transports).

## 4. `goga/telemetry`

Three of five projects import the OTel SDK, and only two configure all three
signals. Every one of gopgql's MCP tools, pgx queries and goose migrations is
unobserved today, and so is every handler sysgo generates. That is the argument.

- [ ] 4.1 `Setup` establishing tracer, meter **and** structured logger — all three or none — installed globally *and* returned.
- [ ] 4.2 Exporter registries delegating to `contrib/exporters/autoexport` for the standard names (mcp-anything already depends on it); house names additive. An unknown name fails at startup naming the supported values rather than silently disabling telemetry.
- [ ] 4.3 Official semantic conventions for resource attributes, from generated `goga/semconv` constants — never string literals.
- [ ] 4.4 Ordered shutdown flushing every provider, errors **joined** rather than first-wins.
- [ ] 4.5 Prometheus reader attached by default; a push exporter additive. Propagators via `contrib/propagators/autoprop`.
- [ ] 4.6 `otel.SetMeterProvider` is always called — epos omits it today and the wrapper must make that unreachable.
- [ ] 4.7 **`Instrumentation`** — the per-module handle: `For(module)`, `Start`, `End` (span status + duration histogram + `error.type`), `Logger()`. This is the type every other module holds, and the mechanism behind design D6.
- [ ] 4.8 `For` returns no-op providers when `Setup` was never called, so a *library* (gopgql) can use goga modules without configuring telemetry — while the call sites still exist, so telemetry appears the moment the consuming binary calls `Setup`.

## 5. `goga/config`

Three projects use koanf with three incompatible source arrangements, and all
three authors had to explain precedence in prose because koanf has none.

- [ ] 5.1 `Load[T]` with the source order **fixed inside `Load`** — defaults → file → env → flags — *not* derived from the order options are passed. epos's posflag callback inverts its apparent precedence today; an option-ordered API would preserve that hazard.
- [ ] 5.2 Typed unmarshalling with duration and slice decoding; `WithDecodeHook` for the rest.
- [ ] 5.3 **Return the raw `*koanf.Koanf` alongside the typed value**, plus `Cut(path)` — go-service's subtree pattern breaks without it.
- [ ] 5.4 One documented env-key convention: prefix upper-snake, `__` separates path segments, `_` literal within a segment. Three projects chose three; this picks one and states it at the call site.
- [ ] 5.5 A missing file is non-fatal unless declared required; a missing required key fails naming the key.
- [ ] 5.6 `WithWatch` for reload — mcp-anything uses fsnotify today.
- [ ] 5.7 Instrumented (design D6): a span per load carrying which sources were used.

## 6. `goga/cli` — cobra

- [ ] 6.1 `New` + `Run`, with `--config` wired into `config.WithFile` and telemetry flags added by default.
- [ ] 6.2 `Run` always uses `ExecuteContext` with a signal-aware context. **epos calls `Execute()` today and has no signal handling at all**; there must be no path through goga to the plain `Execute`.
- [ ] 6.3 Non-zero exit status on failure.
- [ ] 6.4 `Cobra()` escape hatch; instrumented per design D6.

## 7. `goga/database` and `goga/database/pgxdb`

pgx has three current consumers (gopgql, go-service, mcp-anything) and appears in
no house guidance. Design D7 follows `gocloud.dev`'s portable-API/driver split.

- [ ] 7.1 `driver.DB`, `driver.Tx`, `driver.Rows` — narrow, and carrying **no** telemetry, exactly as `gocloud.dev/blob` keeps the tracer on `Bucket` and not on `s3blob`.
- [ ] 7.2 Portable `*database.DB` with unexported fields and `Open` as its **only** constructor — so no code path can produce an uninstrumented `*DB`. This is design D6 enforced structurally.
- [ ] 7.3 Adapters return `driver.DB`, never `*DB`; `Drivers = registry.New[driver.DB, settings]("goga/database")`.
- [ ] 7.4 Portable methods `Query`, `Exec`, `Tx`, `Close` — each a span (`goga.database.query`) plus duration and `error.type`, with the query timeout applied from settings.
- [ ] 7.5 `Tx` commits on nil, rolls back on error **and on panic**. Three projects would otherwise each write this.
- [ ] 7.6 `SQLDB()` — the `database/sql` bridge, `stdlib.OpenDBFromPool` for pgx, so no caller learns that goose needs it.
- [ ] 7.7 `Unwrap()` returning the native handle (`*pgxpool.Pool`), because pgx's `CopyFrom`, `Batch` and `LISTEN/NOTIFY` must stay reachable.
- [ ] 7.8 `pgxdb` registering `postgres://` and `pgx://`, using **`exaring/otelpgx`** for wire-level spans plus `otelpgx.RecordStats` — already the house choice in mcp-anything. Two span levels on purpose; check they nest rather than double-count (Risks).
- [ ] 7.9 `WithSQLCommenter` injecting trace context into SQL comments.
- [ ] 7.10 Read gopgql's `migrate/` package (`diff.go`, `fold.go`, `rename.go`) before finalising the surface — it is the most PostgreSQL-specific code in the house.

## 8. `goga/migrate` — goose

Pinned as the house migration engine (design D10). `gopgql` already requires
`pressly/goose/v3 v3.26.0`.

- [ ] 8.1 Wrap `goose.Provider`; goose's own API already takes variadic `ProviderOption`, consistent with design D14.
- [ ] 8.2 **Embedded migrations by default** (`WithFS(embed.FS)`), so a binary carries its own schema.
- [ ] 8.3 **A boot-time PostgreSQL session advisory lock** with a timeout, so two replicas starting together do not both migrate.
- [ ] 8.4 `Pending()` as a readiness input, wired into `serve`'s `/readyz`, so a service with a behind schema refuses traffic instead of erroring per request.
- [ ] 8.5 Version table named once: `goga_db_version`.
- [ ] 8.6 A span per migration carrying its version and name (design D6) — this is how the 40-second migration gets found.
- [ ] 8.7 Errors name the version and file: `migration 20260714120000 (add_index.sql): ...`.
- [ ] 8.8 `Provider()` escape hatch.

## 9. `goga/serve`, the router adapters, and `goga/client`

- [ ] 9.1 `Server` with signal handling, bounded graceful shutdown, and header/read/write timeouts **set** rather than left unbounded.
- [ ] 9.2 **Probe and metrics endpoints registered on a mux outside the `otelhttp` wrapper** so they never pollute request traces, with **no option that can move them inside**. go-service discovered this by hand; encoding it is the point of the wrapper.
- [ ] 9.3 `WithHealthCheck` / `WithReadinessCheck`, with `migrate.Pending` as a supported readiness input.
- [ ] 9.4 `Router` interface — `http.Handler` + `Handle` + `Use` + `Unwrap` — narrow enough that oapi-codegen's generated server needs nothing more.
- [ ] 9.5 `Routers` registry with three adapters: **`muxrouter`** (standard library, default, so no project pays for a router it did not ask for), **`chirouter`** (mcp-anything's current router), **`ginrouter`** (sysgo's current router, and the owner's target for skill-test).
- [ ] 9.6 `ginrouter` translates `{id}` patterns to gin's `:id`, uses `gin.Recovery()` and **omits `gin.Logger()`** — slog is the house logger.
- [ ] 9.7 **No router adapter carries instrumentation**: `serve.New` wraps whatever `Router` it gets in `otelhttp` exactly once, so all three are instrumented identically and no adapter author can forget (design D6).
- [ ] 9.8 `client.New` — retries with backoff over `retryablehttp` (already in go-service), `otelhttp` transport underneath for client spans, context propagation and client metrics, plus `gobreaker` (mcp-anything's choice). **Retries are logged, not silently absorbed.**
- [ ] 9.9 Both `Server` and `Client` return their underlying objects.

## 10. `goga/mcp`

Two current consumers at two SDK versions, neither instrumented: gopgql
(`go-sdk v1.6.1`, hand-rolled `mcp/server.go`, `mcp/query.go`,
`mcp/introspection.go`) and mcp-anything (`v1.4.1`). sysgo will be a third.

- [ ] 10.1 `Server` wrapping `sdkmcp.Server` with unexported fields and `New` as the only constructor.
- [ ] 10.2 `AddTool[In, Out]` as a free generic function (Go methods cannot carry type parameters) and **the only path to the wrapped SDK server** — which is what makes the instrumentation below unavoidable.
- [ ] 10.3 A span per tool call, resource read and prompt render, with duration and `error.type`, added by the wrapper and **not** by the tool author (design D6).
- [ ] 10.4 Tool failures returned in-band as `IsError` results, since that is what MCP specifies — not as protocol errors.
- [ ] 10.5 A per-tool timeout from settings.
- [ ] 10.6 Trace-context propagation: MCP defines no header, so the house convention is `traceparent` in the request `_meta`, extracted on the server and injected on the client. State it once here.
- [ ] 10.7 `Transports` registry: `stdio` (default), streamable `http`, `sse`.
- [ ] 10.8 `Handler()` so an MCP server mounts on a `goga/serve` `Server` — one port for HTTP and MCP, the sysgo case.
- [ ] 10.9 `Client` / `Connect` for the consumer side, instrumented symmetrically.
- [ ] 10.10 `SDK()` escape hatch.

## 11. `goga/di` — wire, enforced

The owner: *"I don't see di with wire. It's very important. I really like it and
it's not enforced."* Design D9.

- [ ] 11.1 Pin **`github.com/goforj/wire`**, not the archived `google/wire`, as a `tool` directive — `skill-test/go-service` already pins the fork at v1.2.0.
- [ ] 11.2 Every module exports a `ProviderSet`; each module's set attaches its own telemetry provider, so importing a module cannot mean importing it uninstrumented.
- [ ] 11.3 `di.Core`, `di.Service`, `di.Data`, `di.MCP` unions.
- [ ] 11.4 `goga.App` with **unexported fields and no exported constructor**, so the practical way to build one is a generated injector.
- [ ] 11.5 One `//go:generate go tool wire ./...` line in the project template; `wire_gen.go` committed.
- [ ] 11.6 **`go-generate-check` is the enforcement**: a stale or missing `wire_gen.go` is a red build (task 16.5).
- [ ] 11.7 `goga/lint`'s `gogawire` rule: a goga provider called outside a `//go:build wireinject` file.
- [ ] 11.8 `depguard` bans `github.com/google/wire` so nobody adds the archived module.

## 12. `goga/lint` — the enforcement linter

The mechanism that makes "enforce everything with goga" real rather than
aspirational. `mcp-anything` already depends on
`golangci/plugin-module-register`, so a custom plugin module is proven in-house.

- [ ] 12.1 A golangci-lint plugin module, wired into the shipped `.golangci.yml` template.
- [ ] 12.2 `gogaparamstruct` — an exported constructor whose final parameter is a struct.
- [ ] 12.3 `gogawire` — goga providers constructed outside a `wireinject` injector.
- [ ] 12.4 `gogatelemetry` — a type embedding a goga *driver* interface directly, bypassing the portable type.
- [ ] 12.5 `gogasemconv` — string-literal attribute keys where a generated constant exists.
- [ ] 12.6 `gogalayout` — run against goga itself: flat, no `pkg/`, no `internal/`.
- [ ] 12.7 `depguard` entries banning the **import paths** `spf13/viper`, `google/wire`, non-goose migration engines, and `jackc/pgx` outside `goga/database/*`. Import paths, not modules — viper appears as an *indirect* module via golangci-lint, and a module-level ban would be wrong.
- [ ] 12.8 `testifylint` and `usetesting` enabled in the template. gopgql has **172** hand-rolled `t.Errorf`/`t.Fatalf` to migrate.

## 13. `goga/codegen`, `goga/semconv`, `goga/grpc` — the generator half

sqlc, buf, oapi-codegen and OTel Weaver produce code, so goga owns the
invocation, the config and the runtime seam — not the generator (design D11).

- [ ] 13.1 One `//go:generate` entry point per project, so `go generate ./...` is the whole generation story and task 16.5 has a single thing to run.
- [ ] 13.2 `sqlc.yaml` template — engine postgresql, `sql_package: pgx/v5`.
- [ ] 13.3 **`goga/database/sqlcdb`** — satisfy sqlc's generated `DBTX` interface (`Exec`, `Query`, `QueryRow`, `CopyFrom`, `SendBatch`) from the portable `*database.DB`, so generated sqlc code inherits design D6's telemetry with no generated line changing. *(Anticipated consumer: codiq.)*
- [ ] 13.4 `buf.yaml` + `buf.gen.yaml` templates — lint plus breaking-change detection against `main`, `protoc-gen-go` and `protoc-gen-go-grpc`. *(Anticipated consumer: codiq.)*
- [ ] 13.5 **`goga/grpc`** — server and client constructors for buf-generated stubs with `otelgrpc` stats handlers, reflection and health service on by default, `Register(func(grpc.ServiceRegistrar))` so the generated output is untouched. gRPC gets the same treatment HTTP gets.
- [ ] 13.6 `oapi-codegen.yaml` template; mount the generated `StrictServerInterface` through `serve.Router` so one generated server runs on stdlib, gin or chi.
- [ ] 13.7 **`goga/semconv`** — the OTel Weaver registry for goga's own attributes, generated into the package, plus the documented pattern for a project to keep its own registry and generate into its own package. `telemetry.Instrumentation` consumes the generated constants, which is what stops hand-written attribute keys.
- [ ] 13.8 `mockgen` `tool` directive and `//go:generate` lines; freshness enforced by task 16.5, never by review.

## 14. `goga/components` — Service Weaver behind a deployer registry

In scope per the owner. `ServiceWeaver/weaver` is **archived** upstream (checked
2026-07-30), which design D12 handles by making Weaver one adapter rather than
the shape of the API.

- [ ] 14.1 `Component`, `Ref[T]`, `Deployer`, and the `Deployers` registry.
- [ ] 14.2 Portable `Graph` owning the telemetry, so a component graph is traceable regardless of deployer (design D6).
- [ ] 14.3 **`local` deployer** — in-process, the default, and what tests use. Build in v1.
- [ ] 14.4 `k8s` deployer.
- [ ] 14.5 **`weaver` deployer — sequencing is an open question** (design, Open Questions). Recommendation: build the interface and `local` in v1, and the `weaver` deployer with its first consumer, rather than writing adapter code against an archived dependency with nobody to use it. Raise this rather than deciding it silently.

## 15. `goga/gogatest`

Where the knowledge is most expensive and most duplicated: three incompatible
testcontainers strategies, and a godog bootstrap copy-pasted 5× in gopgql and 8×
in epos.

- [ ] 15.1 `Postgres(t, ...opts)` returning a ready portable `*database.DB`, with **one** decided lifecycle and reset strategy, documenting why — weighing gopgql's snapshot/restore, epos's rejection of `CleanupContainer`, and go-service's shared-network stack.
- [ ] 15.2 Cleanup registered on the container's own lifetime, **not** the suite's `*T` — epos rejected `testcontainers.CleanupContainer` because that fills the disk across a long run, and the fixture must encode that conclusion.
- [ ] 15.3 Deterministic ordering: migrations before seed data, regardless of file naming (go-service had to rename scripts `01-`/`02-`/`03-` to force it). `WithMigrations` runs through `goga/migrate`, so tests and production share one migration path.
- [ ] 15.4 Teardown that runs on failure and does not accumulate containers.
- [ ] 15.5 `Container(db)` escape hatch for anything the fixture does not model.
- [ ] 15.6 **`MCP(t, server, ...)`** — an in-memory transport pair, so an MCP server is testable without a subprocess or a port.
- [ ] 15.7 **`Telemetry(t, ...)`** — in-memory exporters plus `RequireSpan`, which is what makes design D6 assertable in every module's own tests.
- [ ] 15.8 `Features(t, ...)` — the godog harness owning scenario reset, runner options and reporting, so a suite only registers steps; `@wip` excluded by default.
- [ ] 15.9 `T(ctx)` — the supported way for a step to reach the test handle. Both projects invented their own.

## 16. Composite actions

Today golangci-lint is invoked **four ways at three versions**. `gopgql` and
`epos` share a docs-workflow bug fixed by copy-paste (`keep_files: true`,
"same bug, same fix as gopgql#24").

- [ ] 16.1 `setup-go` — checkout + setup-go + cache; **Go version defaults to what `go.mod` says**.
- [ ] 16.2 `go-lint` — gofmt gate, `go vet`, golangci-lint via the official action at a pinned version, with `goga/lint` loaded as a plugin module.
- [ ] 16.3 `go-test` — race, atomic coverage, coverage summary and artifact.
- [ ] 16.4 `go-test-integration` — tagged run, timeout, **artefacts uploaded even on failure**; no container-runtime setup step, which no project needed.
- [ ] 16.5 **`go-generate-check`** — `go generate ./... && git diff --exit-code`. **No repo has this today**, and it is the single enforcement point for wire, sqlc, buf, oapi-codegen, OTel Weaver and mockgen alike (design D5, D9, D11).
- [ ] 16.6 `go-vuln` — one action replacing three mechanisms.
- [ ] 16.7 `go-release` — goreleaser, with a `docker` flag covering the only real divergence.
- [ ] 16.8 `pages-deploy` / `pr-preview` — carrying the `keep_files` fix so the third repo does not learn it the hard way.
- [ ] 16.9 Actions SHA-pinned internally; projects pin **goga** and nothing else.

## 17. The skill

- [ ] 17.1 One skill, and per the issue only its **pseudo structure** is fixed here — section headings and the routing table, not its prose.
- [ ] 17.2 A routing table: what an agent needs → which goga entry point. Config, telemetry, server, client, router, database, migrations, MCP, gRPC, components, DI, tests.
- [ ] 17.3 It does **not** re-teach cobra, koanf, otel, pgx, goose or the MCP SDK — that is the library's job now, and duplicating it is how guidance drifts.
- [ ] 17.4 It carries the **enforcement matrix** from the design: each house convention paired with the mechanism that enforces it (compile, lint, or merge). Per design D5 there is **no list of conventions goga leaves to the reader** — if a convention has no mechanism, that is a goga defect to fix, not a caveat to publish.
- [ ] 17.5 It names the escape hatch per module (`Unwrap()`, `Config.K`, `Server.HTTP()`, `Migrator.Provider()`, `mcp.Server.SDK()`). Escape hatches are documented; unenforced conventions are not, because there are none.
- [ ] 17.6 **Fix the live layout contradiction in merged guidance** (design D13). Both skills are **on `main`** — the spf13 `go` skill landed in `37bd574` (workspace#31) — so this is repairing guidance already in force, not getting ahead of a merge. The conflict is over `internal/` **as the default home**: `go-project-scaffold` prescribes `internal/app` / `internal/config` / `internal/server` / `internal/<feature>` plus `pkg/`, while the spf13 skill calls `internal/`-by-default an anti-pattern and prescribes top-level packages one level deep. Not the hexagonal question — `go-project-scaffold` explicitly declines to decide that one.
- [ ] 17.7 State the part the widened scope already settles, so the remaining question is small: adapter organisation is decided by D7/D8 — driver interface adjacent to its portable type, technology-named adapter leaves, **no `port/` or `adapter/` layer directory** — and `go-project-scaffold` already names **sysgo** as the eventual enforcement point, which D3 confirms.
- [ ] 17.8 Take the remaining decision to the owner: the default home for a service's own non-adapter code (top-level / `internal/` / `pkg/`). Recommend the spf13 position for services, since it is the side goga's own adapter shape lands on, and amend `go-project-scaffold` accordingly. goga stays layout-agnostic either way (D1); goga's own flat tree follows the issue and is a statement about a *library*, not the house answer for services.
- [ ] 17.9 Raise separately on **skill-test** that its `AGENTS.md` contradicts itself — line 64 asks for consumer-side ports, line 70 prescribes a centralised `internal/port`. That is skill-test's to fix, not the workspace's.

## 18. Prove it on one project

A framework nobody adopts moves no numbers.

- [ ] 18.1 **gopgql is the first adopter**, per the owner. It is the only project with pgx, goose and the MCP SDK all three, all uninstrumented — so one migration exercises `database`, `migrate`, `mcp` and `gogatest` at once and makes design D6 visible rather than asserted.
- [ ] 18.2 Port gopgql's `mcp/server.go`, `mcp/query.go`, `mcp/introspection.go` onto `goga/mcp`; its tools gain telemetry they do not have today.
- [ ] 18.3 Replace gopgql's 5× duplicated godog bootstrap with `gogatest.Features`, and its `Snapshot`/`Restore` with the decided fixture strategy.
- [ ] 18.4 Adopt `config` + a metrics-only `telemetry` subset in **epos** — the better test of D2, since epos wants a subset and has no DI.
- [ ] 18.5 Adopt `ginrouter` in **skill-test/go-service**, per the owner. It serves on the standard library today, so this is the first exercise of the router seam with a real consumer.
- [ ] 18.6 Retarget sysgo's templates to emit `goga.*` (design D3) — `main.go.tmpl` collapses to roughly `goga.Run(...)`, `providers.go.tmpl` to a `wire.Build` over goga's ProviderSets — and add its MCP server on `goga/mcp`.
- [ ] 18.7 Re-measure the compliance numbers afterwards and record them, so the claim in the proposal is checkable rather than rhetorical.
