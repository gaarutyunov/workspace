## Context

The issue lists the house tool set explicitly: cobra, koanf, **wire**, **gin**,
otel + prometheus + slog, testcontainers, godog, testify, gomock, golangci-lint,
goreleaser, oapi-codegen, **buf**, **weaver**, **sqlc**, and **pgx**. It also
states two hard requirements that shape this document: *"it's important to use
pseudocode to define the program design and go interfaces for the libraries"*,
and *"start all the packages from source without pkg, internal, etc."*

An earlier revision of this design narrowed that list to the tools with a
visible consumer. The owner overruled it: the consumer set is forward-looking,
not a snapshot. This revision restores the full list and adds what the extra
survey turned up.

### Survey

Six projects. `codiq` **does not exist yet** as a repository (checked
2026-07-30) — it is named here because the owner has assigned sqlc and buf to
it, and the design must not assume those tools are unowned.

| | gopgql | epos | skill-test/go-service | sysgo | mcp-anything | codiq |
|---|---|---|---|---|---|---|
| status | current | current | current (PR #2) | current | current | **anticipated, no repo** |
| shape | library + WASM playground + MCP server | CLI + registry server | PDF microservice | SysML→Go generator | MCP gateway | code-intelligence (owner) |
| direct deps | 8 | 21 | ~35 | 8 | ~55 | — |
| layout | flat root packages | `cmd/` + flat `internal/<domain>` | hexagonal | `cmd/` + `internal/` + `engine/` | flat + `internal/` | — |

**Corrections to the earlier survey, from re-reading the manifests.** These
matter because the earlier exclusion rested on them being otherwise:

- **pgx already has two current consumers.** `gopgql` requires
  `github.com/jackc/pgx/v5 v5.10.0`; `skill-test/go-service` requires
  `v5.10.0`; `mcp-anything` requires `v5.7.4` **plus
  `github.com/exaring/otelpgx v0.10.0`** — the OTel tracer for pgx. So the house
  already has a chosen pgx instrumentation, and it is not in the design yet.
- **The MCP SDK already has two current consumers.** `gopgql` requires
  `github.com/modelcontextprotocol/go-sdk v1.6.1` and ships `mcp/server.go`,
  `mcp/query.go`, `mcp/introspection.go`. `mcp-anything` requires `v1.4.1`. Two
  live copies at two versions, neither instrumented — the exact drift shape the
  framework exists to remove.
- **goose already has a current consumer.** `gopgql` requires
  `github.com/pressly/goose/v3 v3.26.0` and ships a `migrate/` package
  (`diff.go`, `fold.go`, `rename.go`, `constraints_test.go`).
- **`google/wire` is archived** (last push 2025-08-22). The live fork is
  `github.com/goforj/wire`, and `skill-test/go-service` already pins
  `goforj/wire v1.2.0` **as a `tool` directive**. Any spec that says "wire"
  without saying which one is telling a project to add an archived dependency.
- **gin already has a current consumer, and the previous revision missed it.**
  `sysgo` requires `github.com/gin-gonic/gin v1.12.0` **directly**, alongside
  `oapi-codegen` — so the house code generator emits gin handlers today.
  Meanwhile `skill-test/go-service` serves the *same generator's* output on the
  standard library, and `mcp-anything` uses `github.com/go-chi/chi/v5`. That is
  **three router positions across three projects, for two of which the HTTP layer
  is generated from the same tool** — which is the strongest single argument in
  the survey for the router seam in D8, and it was invisible while the exclusion
  rule was in force. The owner's instruction that gin belongs in skill-test adds a
  fourth data point in the same direction.
- **`sysgo` also requires `go.temporal.io/sdk` directly**, which is on no house
  tool list. It is flagged, not folded in: goga should not acquire a workflow
  engine by accident. If Temporal is a house tool it belongs in a later issue
  with its own decision.
- **`ServiceWeaver/weaver` is archived** (`isArchived: true`, last push
  2025-11-20). It is in scope per the owner; the archived upstream is handled by
  D12, not by exclusion.

**What `mcp-anything` adds to the survey** (its ~55 direct requires are the
widest sample in the house):

- `github.com/modelcontextprotocol/go-sdk v1.4.1` — MCP SDK, second consumer.
- `github.com/jackc/pgx/v5` + `github.com/exaring/otelpgx` — pgx *with* OTel.
- `github.com/go-chi/chi/v5` — a third router position.
- `github.com/knadh/koanf/v2` + `parsers/yaml` + `providers/file` — a **third**
  koanf consumer, with a third source arrangement.
- The most complete OTel stack in the house: `contrib/exporters/autoexport`,
  `contrib/propagators/autoprop`, otlp exporters for traces, metrics **and
  logs**, `exporters/prometheus`, `sdk/log`. `autoexport` already solves
  "exporters selected by config name" upstream — goga should delegate to it
  rather than reimplement it.
- `github.com/redis/go-redis/v9` + `extra/redisotel` — instrumented cache.
- `github.com/sony/gobreaker/v2` — circuit breaker, an outbound-client concern.
- `github.com/ulule/limiter/v3` — rate limiting.
- `github.com/golangci/golangci-lint/v2` **and
  `github.com/golangci/plugin-module-register`** — golangci-lint as a *module*
  dependency, i.e. a **custom linter plugin**. The house already builds custom
  lint rules. This is the mechanism that makes "enforce everything with goga"
  achievable rather than aspirational (D5).
- `github.com/testcontainers/testcontainers-go` + `modules/k3s`.
- `github.com/spf13/viper v1.12.0` appears **indirect** (pulled in by the
  golangci-lint module). Worth knowing so a `depguard` rule bans the import path,
  not the module.
- Notably absent: gin, sqlc, buf, goose, wire, Service Weaver, `gocloud.dev`.

### The findings that still drive the design

- **koanf diverges most, now across three projects.** epos: env → posflag, with a
  callback returning `("", nil)` to skip unchanged flags — which inverts the
  apparent precedence; no file provider, no `Unmarshal`, no `koanf:` tags, five
  bare getters. go-service: file(yaml) → env with `__` as the path separator and
  `_` literal, a typed struct, mapstructure hooks, and `k.Cut()` to hand adapter
  subtrees to factories. mcp-anything: file(yaml) + fsnotify reload. All three
  authors had to explain precedence in prose, because koanf has none of its own.
- **Telemetry is where the complaint is measurable.** Three of the five existing
  projects import the OTel SDK, but only two (`go-service`, `mcp-anything`)
  configure traces, metrics and logs together. `epos` has metrics only and never
  calls `otel.SetMeterProvider`. `gopgql` and `sysgo` have none — so every one of
  `gopgql`'s MCP tools, pgx queries and goose migrations is currently unobserved,
  and so is every handler `sysgo` generates. This is the evidence behind the
  owner's rule in D6.
- **`go-service` keeps `/livez /readyz /healthz /metrics` on the root mux
  *outside* the otelhttp wrapper** so probes don't pollute traces. That detail is
  exactly what never survives a document.
- **The test tooling holds the most hard-won knowledge**, in three incompatible
  copies: gopgql's `Snapshot`/`Restore` per scenario; epos's hand-rolled
  `track()` explicitly rejecting `testcontainers.CleanupContainer` because
  hanging cleanup off the suite's `T` fills the disk; go-service's init scripts
  renamed `01-`/`02-`/`03-` because `WithInitScripts` keeps basenames and would
  otherwise sort fixtures before the schema.
- **CI is drift, not judgement.** golangci-lint is invoked four ways at three
  versions. gopgql and epos carry near-identical docs workflows, and epos's
  `keep_files: true` carries the comment *"Same bug, same fix as
  gaarutyunov/gopgql#24"* — a production bug that propagated by copy-paste.

## Goals / Non-Goals

**Goals:**

- Cover **every tool in the issue's list**, each behind a goga surface, so
  replacing a tool is an adapter change and not an interface change.
- Make the house choices the path of least resistance, at compile time; and where
  the compiler cannot reach, at lint time and merge time (D5).
- Give every part of the framework telemetry, with no exemptions (D6).
- Wrap the *test* tooling, where the knowledge is most expensive and most duplicated.
- Be adoptable **one package at a time**, because the projects that most need
  goga are the ones that need the least of it.

**Non-Goals:**

- Imposing a project layout (D1).
- Migrating the existing projects. That is per-project work, per-issue.
- Replacing sysgo's code generation (D3).
- Owning the *content* of generated code. For sqlc, buf, oapi-codegen and OTel
  Weaver goga owns the invocation, the config template and the runtime seam the
  generated code compiles against — not the generator (D11).

## Decisions

### D1: goga is layout-agnostic

Four positions on layout are live simultaneously: hexagonal (skill-test, the one
project built under a mandatory `AGENTS.md`), flat (three of five repos), the
spf13 `go` skill's rejection of `internal/` as a default home, and the issue's own
"no `pkg`, no `internal`" for goga itself. Two of those four are merged workspace
guidance that contradict each other today — see D13, which also says how much of
the disagreement the widened scope settles and what is left for the owner.

Layout is the most per-project axis in the survey, and `go-project-scaffold`
already declines to decide it on the owner's behalf. Baking one into the library
would collide with sysgo (D3) and would make goga un-adoptable by exactly the
projects that diverge. **goga ships libraries; directories are the project's.**

goga's own tree is flat, per the issue — `goga/config`, `goga/telemetry`,
`goga/database`, one level deep, no `pkg/`, no `internal/`. Adapters are
sub-packages of their module (`goga/database/pgxdb`) because Go's import graph
gives no other way to make an adapter's dependency optional.

- *Rejected — hexagonal-first.* go-service's config-driven adapter registry is
  genuinely good and is generalised here as D7's per-module tables, but shipping the
  *directory structure* as mandatory makes goga an all-or-nothing adoption, which
  D2 rejects for stronger reasons.

### D2: independent packages, not a framework object

Modules: `goga/config`, `goga/telemetry`, `goga/serve`, `goga/client`,
`goga/database`, `goga/migrate`, `goga/mcp`, `goga/cli`, `goga/grpc`,
`goga/components`, `goga/semconv`, `goga/di`, `goga/lint`, `goga/gogatest`. Plus
exported wire ProviderSets per module (D9), plus a thin `goga/app` that composes
them — separate from the root `goga` package, which holds only `Option` and
`Apply` and must stay a leaf (see the pseudocode's opening note). Plus
`goga/registry`, a fifteenth — the shared adapter table, restored to v1 now that
Go 1.27 has generic methods (D8). It is a leaf too: it imports nothing but the
standard library, so every module can hold one.

**Independence is also the unit of delivery.** D16 makes each module a milestone
of its own, delivered and adopted before the next one starts, which is only
possible because the modules are independent packages. A framework object would
have made the owner's sequencing rule unimplementable.

The evidence: `sysgo` needs none of the runtime wrappers. `epos` needs config and
a metrics-only telemetry subset. `gopgql` is a library that needs database,
migrate, mcp and gogatest but no server. A `goga.New()` App object as the *only*
door would exclude the projects with the worst compliance — the ones goga most
needs to reach.

**Every wrapper exposes its underlying object**, through a method named
`Unwrap()` where the type is opaque and a named accessor otherwise
(`Config.K`, `Server.HTTP()`, `Migrator.Provider()`, `mcp.Server.SDK()`). This is
the cheap mitigation for a wrapper leaking the moment a project needs something
unanticipated. It is an *escape hatch*, not an unenforced convention — see D5.

- *Rejected — a framework object as the only entry point (the Yokai/Kratos
  shape).* Good when a service is the unit of adoption; wrong when two of six
  consumers are a library and a generator.

### D3: sysgo stays the only Go-code generator; goga owns everything else

sysgo already emits `main.go` (cobra), `providers.go` (`wire.NewSet` +
`wire.Bind`), `wire.go` and a handler — and its CI asserts the generated project
builds with a `go.mod` containing **zero requires**. That zero-dependency goal is
exactly what goga inverts, so the two will collide on `main.go` unless this is
settled now.

**goga = library + composite actions + config templates + one skill. sysgo = the
only Go-code generator, retargeted to emit `goga.*` calls.** That makes sysgo's
`main.go.tmpl` collapse from a TODO-riddled cobra skeleton to roughly
`app.Run(...)`, and its `providers.go.tmpl` to a `wire.Build` over goga's
exported ProviderSets (D9).

**The carve-out that matters:** goga owns the GitHub Actions, `.golangci.yml`,
`.goreleaser.yaml`, `Makefile` and `go.mod` tool-directive templates
**regardless** — because gopgql, epos and mcp-anything need those *today* and
none will ever be generated from a SysML model.

### D4: v1 covers the whole tool list — consumers may be anticipated

**Reversed from the previous revision, on the owner's instruction.** The previous
rule was "wrap only what has a consumer today", which excluded gin, sqlc, buf and
Service Weaver. That rule is withdrawn: a framework whose scope is set by
today's `go.mod` files can never be ready for the project that is about to need
it, and it dropped four tools from the owner's own list.

The replacement rule: **scope comes from the issue's tool list; the survey
records who the consumer is and whether that consumer is current or
anticipated.** Being anticipated changes *sequencing*, never *scope*.

| tool | goga surface | consumer | status |
|---|---|---|---|
| cobra | `goga/cli` | epos, sysgo, go-service, gopgql | current |
| koanf | `goga/config` | epos, go-service, mcp-anything | current |
| wire (`goforj/wire`) | `goga/di` | go-service, sysgo (generated) | current |
| **gin** | `goga/serve/ginrouter` | **sysgo**; skill-test | **current + anticipated** (owner) |
| chi | `goga/serve/chirouter` | mcp-anything | current |
| stdlib mux | `goga/serve/muxrouter` | go-service | current (default) |
| otel + prometheus + slog | `goga/telemetry` | go-service, mcp-anything | current |
| **pgx** | `goga/database/pgxdb` | gopgql, go-service, mcp-anything | **current** |
| **goose** | `goga/migrate` | gopgql | **current** (D10) |
| **MCP SDK** | `goga/mcp` | gopgql, mcp-anything; sysgo | **current + anticipated** |
| testcontainers / godog / testify / gomock | `goga/gogatest` | all five | current |
| golangci-lint / goreleaser | composite actions + `goga/lint` | all five | current |
| oapi-codegen | `goga/codegen` + `goga/serve` | go-service, sysgo | current |
| **sqlc** | `goga/codegen` + `goga/database/sqlcdb` | **codiq** | **anticipated** (owner) |
| **buf** | `goga/codegen` + `goga/grpc` | **codiq** | **anticipated** (owner) |
| **OTel Weaver** | `goga/semconv` | go-service | **current** |
| **Service Weaver** | `goga/components` | — | **anticipated** (owner); upstream archived (D12) |

Sequencing follows the consumer. Under D16 that is now sharper than "later":
scope still comes from the tool list, but a module gets a **milestone** only when
a named project can adopt it, so an anticipated tool waits for its consumer
rather than shipping a surface nobody exercises. `goga/components` and the
sqlc/buf halves of `goga/codegen` are the cases; `tasks.md` records where each
sits.

### D5: every house convention is enforced by goga; there is no "not enforced" list

The previous revision asked the skill to *state which conventions goga does not
enforce*. That is withdrawn. If a convention cannot be enforced, the gap is a
goga defect to fix, not a caveat to document.

Enforcement has three mechanisms, in order of preference:

1. **Compile time — the API leaves no other shape available.** Two techniques do
   most of the work.
   - *Settings structs are unexported, and unspellable outside their module.*
     Each module declares `type settings struct{…}` — **unexported**, so no
     other package can name it, construct it, or embed it — plus
     `type Option = goga.Option[settings]`, an exported alias over that
     unexported type. A caller can hold and pass a `database.Option`; it cannot
     write the type the option mutates. Every exported goga entry point takes
     `...Option` and none takes a settings value, so `goga.Apply` over the
     caller's options is the only way a populated `settings` ever comes into
     existence. **There is no exported struct anywhere in goga's option
     surface**, which is what makes D14 a compile-time property rather than a
     review one.

     *What an adapter names instead.* An adapter lives in its own package
     (`goga/database/pgxdb`) and may need the caller's resolved values — pool
     size, timeouts. It reads them through an exported **read-only interface**
     carrying nothing but accessors. The unexported `settings` struct implements
     it. So the house rule is one line: **`Settings` is always an interface;
     `settings` is always the unexported struct.** An adapter names the
     interface, never the struct, and cannot construct a populated one; it could
     write its own implementation of the interface, but no goga entry point
     accepts a `Settings`, so there is nowhere to pass it.

     Two placement rules, so an adapter author never has to guess. **Where:** the
     `Settings` interface is declared in the same package as the port interface
     the adapter implements — `driver.Settings` beside `driver.DB`,
     `mcp.Settings` beside `mcp.Transport` — which is a package the adapter
     already imports. **Whether:** a module's opener takes a `Settings` **only if
     an adapter reads one.** `goga/database` does (pool sizing, timeouts);
     `goga/mcp` does (the HTTP transport needs its endpoint); `goga/components`
     does (the deployer's config path). `goga/serve` and `goga/telemetry` do
     **not** — a router adapter builds an engine and a trace exporter delegates
     to `autoexport`, and neither reads a single setting, so their openers take
     `(ctx)` alone. An opener parameter that no adapter reads is an abstraction
     with no user: each module declares its own opener, so nothing forces one
     signature on every module.

     *The registry's return does not cost the unexported form, and this was
     checked with a compiler rather than argued.* A previous revision shipped an
     **exported opaque `Settings` struct**, on the reasoning that a shared
     generic registry made the module's concrete settings type a type parameter
     that adapter packages had to name. That reasoning does not survive D8's
     shape. The adapter's settings type is a **method type parameter inferred at
     the call site** — `Open[A Adapter[S], S any]` infers `S` from the options
     passed, and infers it from `A`'s own constraint when no options are passed
     at all — so no caller ever names it. The spike proves the strong form: an
     adapter package whose `settings` struct is **unexported** is configured
     correctly from a package that cannot spell that type. So the claim that the
     compiler makes a parameter struct unspellable holds with the registry in
     place, and it is the *stronger* claim, not a restored one.

     *One correction owed to the record, now settled.* An earlier revision said
     the unexported form and the generic registry were "not jointly satisfiable
     in Go". That was false, and the spike says so directly: they are jointly
     satisfiable, and neither a read-only `Settings` interface nor an exported
     struct is needed to get there. The interface seam below survives for the
     different reason that an adapter sometimes needs the *module's* resolved
     values (pool sizing, timeouts) rather than its own — which is a separate
     seam from the adapter's own settings type, and the two should not be
     confused again.
   - *Portable types have no exported constructor and unexported fields.* An
     adapter returns a `driver.X`; only the module's `Open`/`New` can wrap one
     into the portable type, and it always attaches instrumentation. So D6 holds
     for every object goga hands a caller: **no exported goga constructor
     produces an uninstrumented portable object.** The shared registry does not
     open a hole here, because `registry.Table[P]` stores and returns *adapters*
     — `driver.DB` values — and never portable types. Each module exports
     `Register`, so a project can still supply its own adapter, but it exports
     **no lookup** —
     there is no `Drivers.Open` returning a raw `driver.DB`, because nothing
     outside the module needs one. What remains is a project calling the opener
     it wrote itself, which is its own code rather than a goga entry point, and
     which `goga/lint`'s `gogatelemetry` reports.
2. **Lint time — `goga/lint`, a golangci-lint plugin module.** `mcp-anything`
   already depends on `golangci/plugin-module-register`, so the mechanism is
   proven in-house. Rules: `gogaparamstruct` (an exported constructor whose final
   *non-variadic* parameter is a same-package struct with exported fields, and
   which takes no variadic options — the looser "final parameter is a struct"
   fires on `New(t *testing.T)`), `gogawire` (goga providers constructed outside a
   `//go:build wireinject` injector), `gogatelemetry` (a type embedding a goga
   driver interface directly, bypassing the portable type), `gogaviper` (a
   `depguard` entry banning the `spf13/viper` *import path*, since it appears as
   an indirect module and a module-level ban would be wrong).
3. **Merge time — the composite actions.** `go-generate-check` runs
   `go generate ./... && git diff --exit-code`, which is what makes wire's
   generated injectors, sqlc's queries, buf's stubs, oapi-codegen's server and
   Weaver's semconv all *required* rather than optional: skip one and CI is red.

**Honest limit, stated rather than hidden:** a determined author can hand-write
what `wire` would generate, or import `pgx` directly and never call
`goga/database`. Mechanism 2 catches the first; the second is caught only if the
project enables `goga/lint`'s `depguard` set, which the `.golangci.yml` template
does by default. Enforcement is *compile error, lint error, or red CI* — not
physical impossibility. The enforcement matrix below has a row per convention and
names which of the three applies; a convention with no mechanism is a bug.

### D6: every part of the framework has telemetry — invariant, not a feature

The owner's rule, verbatim: *"Every part of the framework must have telemetry."*
It is an invariant of this spec: **every goga module that performs a runtime
operation is instrumented, no such module is exempt, and no goga module offers a
way to turn telemetry off.** `WithTelemetry(*telemetry.Instrumentation)`
*replaces* the instrumentation; there is no `WithoutTelemetry`.

*The qualifier is not an exemption clause; it is the boundary of what the words
can mean.* Three of the fourteen modules perform no runtime operation at all:
`goga/semconv` is generated constants, `goga/lint` is a set of
`analysis.Analyzer`s that run inside golangci-lint, and `goga/di` is
`wire.ProviderSet` values consumed at generation time. There is nothing in them
to start a span around, and inventing one would be exactly the API contortion
the invariant exists to avoid. So the invariant is stated over *operations*, and
made checkable rather than asserted: `telemetry.For` records each module name it
is called with, and `TestEveryModuleIsInstrumented` asserts that the recorded set
is **exactly** the list of modules **shipped so far** minus the exempt set
`{semconv, lint, di, registry, goga (root), app, gogatest}`

**The exempt set, justified per entry, because the test fails in both directions
and a wrong entry is a false red or a silent hole.** `semconv` is generated
constants; `lint` is analysers; `di` is provider sets; **`registry` is a leaf
that deliberately carries no `Instrumentation`, since giving it one recreates the
`registry` → `telemetry` → `registry` cycle (D8)**; root `goga` is `Option` and
`Apply` and must stay a leaf; `app` composes instrumented modules and starts no
span of its own; `gogatest` runs only under `go test`, where its operations are
the test's, not the service's. Everything else instruments. **The module list the
test compares against is the exported package list of the goga module**, computed
from the repo rather than hand-maintained, so a new module is instrumented or
exempt by explicit decision and never by omission.

The reconciliation with the shipped-so-far rule
— a new module with runtime behaviour and no instrumentation fails the test, and
so does an attempt to quietly add a fourth name to the exclusion list. "Shipped
so far" is load-bearing under D16: the test lands at M1 with one entry and each
milestone adds its own, so it is a live check from the first package rather than
a red test waiting fourteen milestones for the list to be complete.

The pattern is taken from `gocloud.dev` (D7): **instrumentation lives in the
portable type, never in the adapter.** In `gocloud.dev/blob`, `Bucket` holds the
`gcdkotel.Tracer` and every driver (`s3blob`, `gcsblob`, `fileblob`) holds none —
so a new driver is instrumented the day it is written, without its author doing
anything. goga copies that arrangement exactly, for every module.

Concretely, per module: a span per operation named `goga.<module>.<op>`, a
`goga.<module>.duration` histogram, an `error.type` attribute from the official
conventions on failure, and a module-scoped `*slog.Logger`. `goga/mcp` is
included — it gets a span per tool call, per resource read and per prompt render
(see the pseudocode). **Adapter resolution is an operation too**: each module
that has adapters emits `goga.<module>.resolve` when it selects one, because
"which adapter did this process actually resolve" is an operational question. The
span belongs to the **module**, not to `registry.Table[P]` (D8): the shared table
is a leaf that imports only the standard library, and giving it an
`Instrumentation` would create the `registry` → `telemetry` → `registry` import
cycle the Go review found in an earlier revision. Each module emits the span from
its own opener, where its `Instrumentation` already is.

**`telemetry.For` must resolve through OTel's global delegating providers**
(`otel.Tracer`, `otel.Meter`, `global.Logger`), never by snapshotting a concrete
provider, and its instruments are created on the handle's first use. This is
load-bearing rather than an implementation note: adapter tables are package-level
`var`s and adapters self-register from `init()`, both **before** `Setup` runs, so
a handle that snapshotted a no-op provider at init would leave exactly those code
paths permanently unobserved while every test passed. OTel's global providers are
designed to delegate once the real provider is installed; goga depends on that.

### D7: `goga/database` is a portable API plus drivers, after `gocloud.dev`

The owner asked for pgx inside a database module with multiple adapters, and
pointed at go-cloud. Reading `gocloud.dev/blob/blob.go` at HEAD, the pattern is:

- A **portable type** (`blob.Bucket`) with the whole public surface, holding
  `tracer *gcdkotel.Tracer` and the metric instruments (`bytesReadCounter`,
  `bytesWrittenCounter`), starting a span in every method
  (`b.tracer.Start(ctx, "ListPage")` … `b.tracer.End(ctx, span, err)`).
- A **narrow driver interface** in a sibling package (`blob/driver.Bucket`) that
  each backend implements and that carries no cross-cutting concerns.
- A **URL-keyed registry** (`blob.URLMux`) with `RegisterBucket(scheme, opener)`,
  `OpenBucket(ctx, urlstr)`, `BucketSchemes()`, `ValidBucketScheme(scheme)`,
  where drivers self-register from `init()` and are selected by a blank import.
- `RegisterBucket` **panics** on a duplicate scheme, because a duplicate is a
  programming error in an `init()`, not a runtime condition.

goga mirrors all four, with one deliberate divergence that Go 1.27 makes cheap.
`blob.URLMux` is **per portable type** and lives in the module it serves, backed
by `gocloud.dev/internal/openurl`. goga keeps the *per-module table* — each
module owns a `registry.Table[P]` for its own port, keyed its own way — but the
table's **implementation** is shared rather than copied five times (D8). The
divergence is confined to where the storage lives; the observable arrangement —
one table per module, self-registration from `init()`, blank-import selection,
panic on duplicate — is `gocloud.dev`'s exactly. What goga adds on top is the
generic cast `gocloud.dev` cannot express in Go 1.18: `Get[A any]` returns the
adapter's concrete type, so pgx's `CopyFrom` is reachable without the assertion
`gocloud.dev` users write by hand.

pgx is the first driver, `goga/database/pgxdb`, registering `postgres://` and
`pgx://`. It uses `github.com/exaring/otelpgx` for wire-level spans — already the
house choice in `mcp-anything` — while the portable layer's span is the *logical*
operation. Two levels, deliberately: `goga.database.query` tells you the app made
a query; otelpgx's tells you what the connection did.

- *Rejected — `database/sql` as the portable surface.* It would make every
  adapter free, but it throws away pgx's `CopyFrom`, `Batch`, `LISTEN/NOTIFY` and
  native types, and gopgql needs pgx's PostgreSQL-specific behaviour.
  `database/sql` is instead available *through* the module, because goose needs
  it (D10).

### D8: `goga/registry` is in v1, built on Go 1.27 generic methods

**Reversed twice, and this revision is the second reversal — on evidence the
owner asked for.** The history matters because the spec has argued both sides.

The owner's first comment refined the registry's shape:

> *"Registry is generic with interface not concrete type. Because an adapter is
> for a port which is the generic for the registry and the adapter satisfies the
> interface."*

The second, three minutes later, withdrew it:

> *"I think we should skip the registry because go doesn't ship generic methods
> yet. Once it does — which is proposed and the proposal seems to be approved —
> we will add registry that will stores structs satisfying interfaces and
> returning concrete types."*

The third restores it, with a condition attached:

> *"Also in go 1.27 generic methods are implemented. So let's use it even if it's
> alpha or beta version. And use it for registry. […] This is exactly what we
> need! Registry is a structure that can cast interfaces (ports) into adapters."*

and, separately: *"This needs to be proven with a spike. Download the new go
version and check what types of code you can write with it."*

**The spike was run.** Toolchain: **go1.27rc2**, obtained with
`go install golang.org/dl/go1.27rc2@latest && go1.27rc2 download`
(GOROOT `~/sdk/go1.27rc2`). Every claim below is a compiler result, not a
reading of the release notes. The code is at
`projects/goga-spike-go127/` in the workspace (gitignored), one directory per
question, and the negative cases are compiled and asserted to fail.

**Generic methods are real.** Go 1.27's spec says *"If the method declaration
specifies type parameters (possibly in addition to type parameters declared by
the receiver specification), the method name denotes a generic method
[Go 1.27]"*, and the compiler agrees. What compiled:

- a method type parameter on a generic receiver — `func (l List[E]) Apply[F any](f func(E) F) List[F]`;
- a method type parameter on a **non-generic** receiver;
- type inference at the call site, explicit instantiation, and instantiated
  method values.

**The owner's exact formulation does not compile, and this is the one finding
that changes the design.** *"the adapter is for a port which is the generic for
the registry"* asks the method's type parameter to be constrained **by the
registry's own type parameter**. Both spellings are rejected:

```go
func (r Registry[P]) Get[A P](name string) (A, bool)              // cannot use a type parameter as constraint
func (r Registry[P]) Get[A interface{ P }](name string) (A, bool) // term cannot be a type parameter
```

The restriction is not specific to methods — the same shape fails as a plain
generic function (`func Get[P any, A P](…)`), so it is a property of Go's
constraint system rather than something generic methods were going to fix. Three
further limits, each verified: an **interface cannot declare a generic method**
(*"interface method must have no type parameters"*), so the registry can never be
hidden behind an interface and a **port must never declare one**; a generic
method is not in the method set reachable through an interface value; and a
generic method value must be instantiated before it is taken.

**So the cast is expressible, but the port check has to be bought separately.**
Two shapes work, and v1 ships both because they answer different questions.

*The shared table, port-generic, runtime-checked.* `registry.Table[P]` stores
adapters for the port `P` and carries the generic method the owner described:

```go
func (t *Table[P]) Get[A any](name string) (A, error)
```

`Get[*pgxdb.DB]("postgres")` returns the concrete adapter and its
pgx-only surface — `CopyFrom`, `Batch`, `LISTEN/NOTIFY` — is reachable without a
call-site assertion. Because `A` is unconstrained, asking for a type that is not
a `P` **compiles** and fails at run time with a typed error naming both types.
That is the residual cost of the restriction above, and it is bounded:
`Register` takes a `P`, so what is *in* the table is compile-time correct, and
only a wrong `Get` is deferred to run time.

*The module's own opener, port-checked at compile time.* Where the port has a
name — which is every goga module — the module declares the constraint itself and
the check moves back to the compiler:

```go
type Adapter[S any] interface {
    DB                 // this module's port, named concretely
    Init(S) error
}
func Open[A Adapter[S], S any](name string, opts ...Option[S]) (A, error)
```

Constraining `A` by a **generic interface instantiated with the method's other
type parameter** is legal — this is the load-bearing discovery — and it ties the
concrete adapter, the port and the adapter's settings type together in one
signature. The negative tests compile-fail exactly as intended:

```
in call to Open[*NotADB], A (type *NotADB) does not satisfy Adapter[S] (missing method Init)
type Option[HTTPSettings] of WithEndpoint("b") does not match inferred type Option[PgxSettings] for Option[S]
```

**What v1 ships.** `goga/registry` is a leaf package holding `Table[P]` —
storage, the duplicate-registration panic, `Keys()`, and the `Get[A any]`
generic method. Each adapter-bearing module keeps a package-level `Table[P]` for
its own port. Verified across real package boundaries (`registry` → `database` →
`pgxdb` → consumer), with adapters self-registering from `init()`.

**How this coexists with D6, which is the seam that matters most.** D6 says no
exported goga entry point returns an uninstrumented object, and the concrete
adapter *is* the uninstrumented object. So the concrete type is an **input**, not
the return, on every primary path. Three entry points, and the distinction is
load-bearing:

- `Open(ctx, u, opts ...Option) (*DB, error)` — the **primary** path. URL-keyed,
  adapter-agnostic, module options, and it returns the **portable instrumented**
  type. A project that blank-imports `pgxdb` and passes `postgres://…` never
  names an adapter type, which is what keeps adapters interchangeable. Unchanged
  from the previous revision, and D6 holds exactly as before.
- `OpenAs[A Adapter[S], S any](ctx, u, opts ...AdapterOption[S]) (*DB, error)` —
  the **typed** path, for a caller that knowingly wants one adapter and wants to
  configure it with that adapter's own options. `A` selects and constrains; the
  return is still `*DB`. This is where the compile-time port check and the typed
  per-adapter options live.
- `Unwrap[A](db *DB) (A, error)` — the **typed escape hatch**, and the place the
  concrete adapter is finally handed over. It is an escape hatch by construction,
  which D2 already blesses and D6 already exempts: the caller has the portable
  object and is asking to leave it.

So *"a structure that can cast interfaces (ports) into adapters"* is delivered by
`Table[P].Get[A]` and by `Unwrap[A]`, and neither is a path by which an ordinary
`Open` quietly returns something uninstrumented. All four signatures are compiled
in the spike.

| module | key | adapters in scope |
|---|---|---|
| `goga/database` | URL scheme | `pgxdb` (`postgres`, `pgx`), `sqldb` |
| `goga/serve` | plain name | `muxrouter` (default), `ginrouter`, `chirouter` |
| `goga/telemetry` | plain name | standard names via `autoexport`; house names additive |
| `goga/mcp` | plain name | `stdio` (default), `http`, `sse` |
| `goga/components` | plain name | `local` (default), `weaver`, `k8s` |

`goga/client` still has no table: one transport, no second candidate, and a
one-entry table is the abstraction D7 warns about.

**Two claims the previous revision made are now withdrawn, and one is
strengthened.** Withdrawn: that the registry forced an *exported* settings struct
(D5/D14), and that it forced an opener signature on modules whose adapters read
nothing. Neither follows from the shape above — the settings type is a type
parameter inferred at the call site, so it can stay unexported (proven: an
adapter package whose `settings` struct is unexported still configures cleanly
from a package that cannot name it), and each module still declares its own
opener. Strengthened: the URL-versus-name split that produced a real bug in an
earlier revision stays fixed, because each module owns its own `Table[P]` and
its own key, and no shared `Open`/`OpenNamed` pair exists to confuse them.

**The honest caveat about what Go 1.27 actually buys.** Everything above except
the `Table[P].Get` *method* compiles on **Go 1.26**, verified with
`GOTOOLCHAIN=local`: `Open[A Adapter[S], S any]` is a generic *function*, and
generic functions have carried multiple type parameters since 1.18. The 1.27
dependency buys the registry-as-a-value form — a `*Table[P]` held, passed and
injected, with the cast as a method on it — which is what the owner asked for and
what a wire-provided registry needs. It does not buy the adapter configuration or
the typed options; those are available today. D17 records what depending on the
RC costs.

### D9: wire is the house DI mechanism, and it is enforced

The owner: *"I don't see di with wire. It's very important. I really like it and
it's not enforced."* Both halves are addressed.

**Which wire.** `github.com/goforj/wire`. `google/wire` is archived;
`skill-test/go-service` already pins the fork at v1.2.0 as a `tool` directive.
The spec names the fork so nobody adds an archived dependency.

**The shape.** Every goga module exports a `ProviderSet`, and `goga/di` exports
the unions:

```go
package di

// Core is the minimum any goga service needs. Every module's Set attaches its
// own telemetry provider, so importing a module can never mean importing it
// uninstrumented.
var Core = wire.NewSet(config.Set, telemetry.Set, cli.Set)

// Service adds the HTTP surface.
var Service = wire.NewSet(Core, serve.Set, client.Set)

// Data adds persistence. database.Set requires a driver blank-import; the
// missing-driver failure is a clear unknown-scheme error at startup, not a nil pool.
var Data = wire.NewSet(database.Set, migrate.Set)

// MCP is additive to either, because a project may be MCP-only (gopgql).
var MCP = wire.NewSet(Core, mcp.Set)
```

**Four mechanics wire imposes, settled here so no project discovers them late.**
Each is a shape a provider must have, not a preference:

- *Cleanups are `func()`.* wire recognises a provider returning
  `(T, func(), error)` and calls the middle value on teardown. A provider
  returning `func(context.Context) error` — which is what `telemetry.Setup`'s
  shutdown naturally is — is not a cleanup to wire; it is an ordinary provided
  value that nothing ever calls, so a service silently stops flushing spans on
  exit. Every goga provider therefore exposes shutdown as a method on its own
  type (`(*Telemetry).Shutdown(ctx) error`, `(*DB).Close()`) and returns a
  `func()` cleanup that calls it under the module's shutdown timeout.
- *Variadic options cannot be supplied by wire.* `serve.New(opts ...Option)` is
  a provider requiring `[]serve.Option` in the graph. Each module's `Set`
  provides the constructor only; `di.Defaults` binds an empty slice per module,
  so a project that wants to configure one module uses that module's constructor
  set without `di.Defaults`' binding for it, rather than fighting a duplicate
  provider.
- *Providers take named types, never bare `string`.* wire's graph is keyed by
  type, so `database.Open(ctx, rawURL string, …)` would collide with every other
  string in the graph. `database.URL`, `serve.Addr`, `mcp.Name` — named types
  the config struct's fields carry.
- *Generic constructors are instantiated by the project.* `config.Load[T]` has
  no single instantiation for wire to provide; the project writes
  `func provideConfig(ctx context.Context) (*config.Config[MyConfig], error)`
  and puts that in its own set. `config.Set` provides everything downstream of
  it.

**How it is enforced** — four layers, weakest first, per D5:

1. *Convention:* the only documented way to build an `*app.App` is a
   wire-generated injector; `app.Run` takes an `*app.App` whose fields are
   unexported.
2. *Generation:* the house `Makefile` and a single `//go:generate go tool wire
   ./...` line in every project; `wire_gen.go` is committed.
3. *Merge time:* the `go-generate-check` composite action runs
   `go generate ./... && git diff --exit-code`. A stale or missing `wire_gen.go`
   is a red build. **This is the actual enforcement.**
4. *Lint time:* `goga/lint`'s `gogawire` rule reports a goga provider function
   called outside a `//go:build wireinject` file.

- *Rejected — `uber/fx` or a hand-rolled container.* Runtime DI moves wiring
  errors from `go build` to first request, and the issue names wire.

### D10: goose is the migration engine

Pinned as a house decision on the owner's instruction. `github.com/pressly/goose/v3`,
already at v3.26.0 in gopgql, which also carries a `migrate/` package worth
reading before finalising the surface.

`goga/migrate` wraps `goose.Provider` (goose's own library API, which already
takes variadic `ProviderOption` — consistent with D14) and adds four things goose
leaves to the caller and that a service gets wrong once:

- **Embedded migrations by default** (`WithFS(embed.FS)`), so a binary carries
  its own schema and there is no "the migrations directory wasn't in the image".
- **A boot lock.** Two replicas starting together both run `Up`. goga takes a
  PostgreSQL session-level advisory lock around the run, with a timeout.
- **`Pending()` as a readiness input**, so a service can refuse traffic while its
  schema is behind instead of erroring per request.
- **Telemetry** (D6): a span per migration with its version and name, which is
  how you find out that one migration takes 40 seconds.

goose needs a `*sql.DB`; pgx gives a `*pgxpool.Pool`. The bridge is
`github.com/jackc/pgx/v5/stdlib.OpenDBFromPool`, held by `goga/database` so no
caller has to know. Version table: `goga_db_version`, named once so three
projects don't pick three names.

- *Rejected — golang-migrate, atlas, sqlc's own versioning.* goose is already
  in-house, is a library and not only a CLI, and takes `fs.FS` — which the
  embedded-by-default decision needs.

### D11: for the code generators, goga owns the invocation, the config and the runtime seam

sqlc, buf, oapi-codegen and OTel Weaver produce code. There is nothing to wrap as
a Go API. What drifts is *how they are invoked* and *what their output compiles
against*, so that is what goga owns:

- **The `tool` directive block** for `go.mod`, so versions are pinned by the
  module graph — `skill-test/go-service` already does exactly this for wire,
  oapi-codegen and mockgen, and it is the house pattern.
- **The config templates**: `sqlc.yaml` (engine postgresql, `sql_package: pgx/v5`,
  `emit_pointers_for_null_types`), `buf.yaml` + `buf.gen.yaml` (lint + breaking
  against `main`, `protoc-gen-go` and `protoc-gen-go-grpc`),
  `oapi-codegen.yaml`, and the OTel Weaver semconv registry layout.
- **One `//go:generate` entry point** per project, so `go generate ./...` is the
  whole generation story and D5's merge-time check has a single thing to run.
- **The runtime seam**, which is the part that is actually library work:
  - `goga/database/sqlcdb` — sqlc's pgx/v5 mode generates against a `DBTX`
    interface (`Exec`, `Query`, `QueryRow`, `CopyFrom`, `SendBatch`).
    `goga/database` satisfies it, so generated sqlc code runs on the portable
    `*database.DB` and inherits D6's telemetry without a generated line changing.
    **This seam is pgx-only, and says so.** `DBTX`'s signatures are pgx types
    (`pgx.Rows`, `pgconn.CommandTag`, `pgx.Batch`) — they are sqlc's, not goga's,
    and no non-pgx adapter can satisfy them. `sqlcdb.New(db)` therefore returns
    `ErrNotPgx` when the resolved driver is not `pgxdb`, rather than being
    described as working on any adapter. The portable API stays adapter-neutral;
    the *generated-sqlc* path is a PostgreSQL-and-pgx path by sqlc's own design.
  - `goga/grpc` — server and client constructors for buf-generated stubs, with
    `otelgrpc` stats handlers, so gRPC gets the same treatment HTTP gets.
  - `goga/semconv` — the OTel Weaver output for goga's own attributes, and the
    documented pattern for a project to keep its own registry and generate into
    its own package. `telemetry.Instrumentation` uses the generated constants,
    which is what stops hand-written attribute keys.
  - oapi-codegen's `StrictServerInterface` is mounted through `serve.Router`
    (D8), so the same generated server runs on stdlib, gin or chi.

### D12: Service Weaver is in scope as one deployer behind `goga/components`

The owner: *"Weaver it's important. The problem is you never added it, although I
asked to."* Two distinct tools have been called "weaver" in this repo, and both
are now in scope, separately:

- **OTel Weaver** (`open-telemetry/weaver`, active) — the semantic-convention
  generator. It is what the issue's *Code generation* heading means alongside
  oapi-codegen, buf and sqlc, and what `skill-test`'s `AGENTS.md` means by
  "Weaver → semconv". It lands as `goga/semconv` (D11).
- **Service Weaver** (`ServiceWeaver/weaver`) — the distributed-application
  framework. It lands as `goga/components`.

`goga/components` gives a component interface, a `Ref[T]` for typed references,
and a **deployer table** of its own (D8) with three adapters: `local`
(in-process, the default and what tests use), `weaver` (Service Weaver), `k8s`.

This shape is the answer to the risk that Service Weaver is **archived upstream**
(verified 2026-07-30, last push 2025-11-20). Putting the interface in goga and
Weaver behind an adapter is precisely the framework property the issue asks for —
*"If we replace a tool we would just replace it inside goga but not change the
interface."* If Weaver stays archived, `weaver` is replaced by another deployer
and no consumer changes. **The fact is flagged, not used as an exclusion.** See
Open Questions.

**Sequencing, and a tension worth naming.** D16 gates every milestone on a real
project adopting it, and `goga/components` has no project to adopt it — no
current consumer, an archived upstream, and the largest invented surface in the
design. So it is the **last** milestone and, unlike every other, it does not
start on a date: it starts when a consumer exists. That keeps both of the owner's
instructions intact — Weaver stays in scope, and nothing ships unvalidated — but
they do pull against each other here, and the resolution is a schedule rather
than a design change.

### D13: the skill shrinks; and the guidance contradiction is now live on `main`

Today's skills teach *how to use* cobra, koanf and otel. Once goga exists, that
is the library's job, and a skill repeating it is the "nonsense and details
leaking" the issue wants gone. The goga skill says: **which entry point to reach
for, and where the escape hatches are.** Per D5 it does **not** carry a list of
conventions goga leaves to the reader — there is no such list. It carries the
**enforcement matrix** instead: convention → mechanism.

The issue also asks for the skill as *"some pseudo structure kind of like
pseudocode for skills"*, so the spec fixes the skill's section structure and
routing table, not its prose.

#### The layout contradiction is live in merged guidance

**Present state, verified 2026-07-30.** `.agents/skills/go/SKILL.md` and
`.agents/skills/go-project-scaffold/SKILL.md` are **both on `main`** — the spf13
skill landed in `37bd574` (workspace#31). This is no longer a merge to get ahead
of; it is a defect in guidance that is already in force, and every model reading
both today picks a side arbitrarily. Two earlier revisions of this design
described #31 as unmerged and asked for the question to be settled *before* it
merged; that framing is withdrawn.

**The contradiction, stated precisely** — and it is *not* the one the earlier
revisions named. `go-project-scaffold` does **not** prescribe hexagonal layers;
it explicitly declines to (*"Hexagonal … is valuable but optional"*, *"Do not
decide this on the owner's behalf"*, defaulting to flat `internal/<feature>`), so
on layers the two skills agree. What they contradict each other about is
**`internal/` as the default home**:

- `go-project-scaffold` prescribes `internal/app`, `internal/config`,
  `internal/server`, `internal/<feature>`, plus `pkg/` for importable code.
- the spf13 `go` skill calls *"relying heavily on an `internal/` folder by
  default"* an **anti-pattern** (line 65), says *"For Applications: … Using
  `internal/` here is usually just adding unnecessary path depth"* (line 75), and
  prescribes top-level domain packages *"one level deep — no `internal/`
  nesting"* (line 92).

Both apply to the same artefact — a Go service — and are opposed on the default.
That is the live defect.

Two adjacent findings, recorded because they change who fixes what:

- **`skill-test`'s `AGENTS.md` contradicts itself.** Line 64 asks for *"small,
  composable interfaces defined at the consumer (port) side"*, while line 70
  prescribes a single centralised `internal/port` package — which is the opposite
  of consumer-side. This one is skill-test's to fix, not the workspace's.
- **`go-project-scaffold` already names the enforcement point:** *"This will
  eventually be enforced by `sysgo` rather than by judgement; until then, ask on
  the issue rather than guessing."* It also already pins
  `github.com/goforj/wire`, which independently corroborates D9.

#### What the widened scope does and does not settle

The owner's widening resolves part of this, and the part it resolves is worth
saying out loud rather than leaving implicit:

1. **Adapter organisation is settled, against layer-named directories.** D7
   commits goga to `gocloud.dev`'s shape: the driver interface lives *adjacent to
   the portable type it serves* (`goga/database` + `goga/database/driver`), and
   each adapter is its own leaf package named for its technology
   (`goga/database/pgxdb`, `goga/serve/ginrouter`). Repeated across six
   adapter-bearing modules by D8, that is a decided position: **ports sit next to
   what they serve, adapters are technology-named leaves, and there is no `port/`
   or `adapter/` layer directory.** A project adopting goga inherits that shape
   for everything it registers into a goga adapter table, which is a direct answer to
   the sub-question `internal/port` / `internal/adapter` was trying to answer —
   and it happens to land on the spf13 skill's side, by concern rather than by
   layer.
2. **The enforcement point is settled.** `go-project-scaffold` says layout will
   eventually be enforced by sysgo; D3 makes sysgo the only Go-code generator and
   retargets it to emit `goga.*`. So the layout decision belongs in **sysgo's
   templates** — not in goga (D1), and not in a skill, since a skill is exactly
   the mechanism D5 says fails on reach.
3. **What remains genuinely open is the default home for a project's own
   non-adapter code**: flat top-level domain packages, or `internal/`, or `pkg/`.
   Nothing in the widened scope touches it. goga ships no directory structure
   (D1) and its own tree is flat because the *issue* says so — which is a
   statement about a library, not about a service, and must not be mistaken for
   the house answer for services.

So: partial resolution, and the remainder is the owner's. It is framed in
`tasks.md` as a fix to merged guidance rather than as a merge to pre-empt.

### D14: variadic functional options everywhere; no parameter structs

The owner: *"I like variadic option functions. I don't like param structs."* This
is a house API convention with no exceptions in goga's public surface.

```go
package goga

// Option mutates a module's private settings. Every exported goga constructor
// takes `...Option[S]` for its own unexported settings type S. Returning an
// error lets an option validate its own input, so a bad value fails at the call
// site rather than at first use.
type Option[S any] func(*S) error

// Apply folds options over a module's defaults. It is the only way an S is ever
// produced, which is what keeps S unexported and D14 enforced by the compiler.
// S stays unexported WITH the shared registry in place (D8): an adapter's
// settings type is a method type parameter inferred at the call site, so no
// caller ever names it. The previous revision exported it on the belief that a
// generic registry forced that; the spike disproves the belief.
func Apply[S any](defaults S, opts ...Option[S]) (S, error) {
	for _, opt := range opts {
		if err := opt(&defaults); err != nil {
			return defaults, fmt.Errorf("goga: applying option: %w", err)
		}
	}
	return defaults, nil
}
```

Each module then writes:

```go
package database

// settings is UNEXPORTED, so no other package can name it, construct it or
// embed it. Option is an exported alias over it: a caller can hold and pass a
// database.Option and cannot write the type it mutates. Every exported entry
// point in this package takes ...Option and none takes a settings, so
// goga.Apply over the caller's options is the only way a populated one exists.
type settings struct{ maxConns int; queryTimeout time.Duration /* … */ }

type Option = goga.Option[settings]

func WithMaxConns(n int) Option {
	return func(s *settings) error {
		if n < 1 {
			return fmt.Errorf("goga/database: max conns must be >= 1, got %d", n)
		}
		s.maxConns = n
		return nil
	}
}

// settings satisfies driver.Settings, the read-only accessor interface an
// adapter in its own package reads (D5). The interface is exported; the struct
// behind it is not.
func (s *settings) MaxConns() int               { return s.maxConns }
func (s *settings) QueryTimeout() time.Duration { return s.queryTimeout }
```

**The house rule this establishes, once, for every module: `Settings` is always
an interface — accessors only, no way to construct a populated one that goga will
accept — and `settings` is always the unexported struct behind it.** There is no
exported struct anywhere in goga's option surface.

Naming rules, so options read the same across modules: `With<Noun>` sets,
`With<Noun>s(...T)` appends, `Without<Noun>` removes — and `WithoutTelemetry`
does not exist, by D6.

- *Rejected — a config struct per constructor.* Compact, but every added field is
  a potential breaking change for positional literals, zero values are
  indistinguishable from "unset", and the owner has ruled against it.

**The struct-params question the owner left open is now answered: no struct
params are needed, anywhere, including the dynamic adapter case.** The owner:

> *"the adapter will need a struct params. We will allow this for such dynamic
> cases where variadic options are not feasible. Unless we use some kind of way
> where variadic options are also part of generic, since each adapter option is
> also a function with some type. If it's allowed."*

It is allowed, and the spike compiles it. Each adapter's option **is** a
function with its own type — `Option[S]` for that adapter's own settings type —
and the module's opener takes them variadically while the registry constraint
ties `S` to the adapter:

```go
type Adapter[S any] interface {
	driver.DB
	Init(S) error
}

func Open[A Adapter[S], S any](name string, opts ...Option[S]) (A, error)
```

Three things this buys, each verified against go1.27rc2 rather than assumed:

- **`S` is inferred, never written.** `database.Open[*pgxdb.DB]("postgres",
  pgxdb.WithDSN(…), pgxdb.WithMaxConns(20))` names only the adapter type; `S`
  comes from the options. With **no** options at all it is still inferred, from
  `A`'s own constraint — so the zero-configuration call needs no type argument
  either.
- **The adapter's settings struct can stay unexported.** Because no caller names
  `S`, `pgxdb` can declare `type settings struct{…}` and export only its
  `Option[settings]` constructors. A consumer package configures the adapter
  correctly while being unable to spell, construct or embed the struct — which is
  D5's strongest claim, now holding for adapter settings and not just module
  settings.
- **Mismatches are compile errors.** Passing another adapter's option, mixing two
  adapters' options in one call, or asking for a type that does not satisfy the
  port all fail to build, with errors that name the types:

  ```
  type Option[HTTPSettings] of WithEndpoint("b") does not match inferred type Option[PgxSettings] for Option[S]
  A (type *NotADB) does not satisfy Adapter[S] (missing method Init)
  ```

So D14 has **no exception for adapters**, and the permission the owner granted —
struct params where variadic options are not feasible — is not needed and is not
taken. If a case is ever found where they genuinely are not feasible, that is a
new decision with evidence attached, not a standing carve-out.

**Adapter configuration follows the same seam** (the owner's 17:01 comment:
*"The method should get settings and marshal it to the type that the adapter
expects and use it to initialize the adapter"*). The opener decodes the raw
config subtree for that adapter into `S` — koanf's `Unmarshal` into the type the
adapter declared — then applies the caller's options **on top**, then calls
`Init(s)`. Precedence is config first, options second, because options are the
explicit form and the more specific one. Adapter-side validation stays ordinary:
`Init` returns an error and the module wraps it
(`goga/database: init "postgres": pgx: dsn is required`). Proven end-to-end in
the spike, including defaults, config-only, and option-overrides-config.

### D15: five cross-cutting Go conventions, decided once

These are not style preferences. Each is a defect the review found in this
document's own pseudocode, which is evidence that stating them once is cheaper
than catching them fifteen times.

**Instrumented methods use named result parameters.** The house shape is
`defer func() { end(err) }()`, and a deferred closure observes the *variable*
`err`, not the value a `return` expression computed. With unnamed results,
`return nil, &UnknownSchemeError{…}` never assigns to the local `err`, so the
deferred call records success on every failure — silently inverting the one
signal D6 exists to produce. Every goga method that opens a span declares named
results.

**`Instrumentation.Start` returns the closure that ends the span.**
`Start(ctx, op, attrs…) (context.Context, func(error))`, not a `(ctx, span)` pair
that the caller must later pass back to `End` along with a start time it captured
itself. The earlier three-argument `End(ctx, span, err, start)` was already
mis-called in this document: `migrate.Up`'s inner loop passed `time.Now()` as the
*start*, recording a duration of zero for every migration — the exact metric D10
introduces to find the forty-second migration. An API where the duration is
capturable only by the type that started it cannot be mis-called that way. The
span stays reachable through `trace.SpanFromContext(ctx)` for a caller adding
attributes mid-operation.

**Cancellation is owned by whatever outlives the call.** A method that returns a
*streaming* result must not cancel that result's context when it returns. `Query`
returns `Rows`; a `defer cancel()` in `Query` kills the rows before the caller
reads the first one, and a `defer end(err)` closes the span before the query has
actually done its work. The portable `Rows` therefore owns both: `Rows.Close()`
cancels the timeout context and ends the span, and the recorded duration covers
the whole read. Non-streaming methods (`Exec`, `Up`, `CallTool`) keep the defer.

**One process, one signal handler.** Signal handling belongs to the composition
root — `cli.App.Run`, and `app.Run` beneath it — and nowhere else. `serve.Server`
and `mcp.Server` take a `context.Context` and return when it is cancelled; they
do not call `signal.NotifyContext` themselves. Otherwise a process serving HTTP
and MCP together (the sysgo case this design explicitly supports) installs three
handlers whose shutdowns race, with no ordering between draining connections,
closing the pool and flushing telemetry — and the service-lifecycle requirement
that *every surface stops together* is unimplementable. `app.Run` runs the
surfaces under an `errgroup`, and on cancellation shuts down in reverse
construction order: surfaces drain, then database, then telemetry flushes last so
the shutdown itself is observable.

**Errors are wrapped with the module path and typed where callers branch.**
`fmt.Errorf("goga/database: open %q: %w", scheme, err)` — the module prefix, the
operation, `%w`. Where a caller must branch, the error is a type with an `Is`
(`UnknownSchemeError`, `MissingKeysError`, `ErrNoSQLDB`, `ErrNotPgx`). Adapters
return errors and never log; the portable type owns both the log and the span.

### D16: delivery is by milestone — one package, one adopter, one review

The owner:

> *"We shouldn't deliver everything at once. Split the spec into clear
> milestones. Each milestone we will deliver one package. I will carefully review
> it. We will migrate gopgql and some other project to it and then continue to the
> next."*

and, on ordering:

> *"For example postgres which could land to gopgql and codiq. Telemetry first,
> every project needs it. Http with telemetry for gopgql and epos. Config for all
> of them too."*

This is a decision about delivery, not about design: no module changes shape, no
capability is dropped. What changes is that **`tasks.md` is ordered by milestone
rather than by module**, and that each milestone carries the name of the project
that adopts it.

**The rule, in three parts.**

1. **One package per milestone.** The unit of review is a package, because a
   package is what a project can adopt on its own (D2). Where a milestone carries
   more than one directory, the extra is something the package cannot be used
   without and nobody adopts separately — `goga/semconv`'s generated constants
   under `goga/telemetry`, the adapter sub-packages under their module — and the
   milestone table says so.
2. **A named adopter per milestone.** Not "a project could use this" but a repo,
   named, with the reason it is the right one. A milestone with no adopter does
   not get a slot.
3. **Adoption is the gate.** A milestone is not finished when the package
   compiles and its tests pass. It is finished when the adopting project's
   migration is merged, and the next milestone does not start until then. That is
   the owner's sentence — *"We will migrate gopgql and some other project to it
   and then continue to the next"* — read literally, because read any other way
   it enforces nothing.

**The order, and where it comes from.** Telemetry first is the owner's, stated
with its reason (*"every project needs it"*), and it is also the module every
other module depends on for D6. HTTP-with-telemetry, config and postgres are the
owner's, in the owner's sequence. The rest are ordered by consumer evidence from
the survey: a module with a current consumer outranks one with an anticipated
consumer, and a module with neither goes last or waits.

| # | package | adopter, then second | why this one |
|---|---|---|---|
| M0 | *(repo, not a package)* — `go.mod` on Go 1.27 (D17), flat layout, root `goga` (`Option`/`Apply`), **`goga/registry`** (D8), the **`goga/lint` plugin scaffold** and the **skill skeleton** (D18), `.golangci.yml` / `Makefile` / `.goreleaser.yaml`, and the actions goga's own CI needs | goga itself | nothing can be delivered from an empty repo; and D18's six parts mean M1 cannot ship a linter rule or a skill section unless the mechanism for both exists first |
| M1 | `goga/telemetry` (+ generated `goga/semconv`) | **gopgql**, then **epos** | the owner's *"telemetry first"*; gopgql has none at all, epos has metrics only and never installs its meter provider |
| M2 | `goga/serve` (+ `muxrouter`, `ginrouter`, `chirouter`) | **epos**, then **gopgql** | the owner's *"http with telemetry for gopgql and epos"*; three router positions across three projects is the survey's strongest seam evidence |
| M3 | `goga/config` | **epos**, then **skill-test/go-service**, then **mcp-anything** | the owner's *"config for all of them too"*; three koanf consumers with three incompatible arrangements, and epos's flag callback inverts its own precedence |
| M4 | `goga/database` (+ `driver`, `pgxdb`, `sqldb`) | **gopgql**; **codiq** when it exists | the owner's *"postgres which could land to gopgql and codiq"* |
| M5 | `goga/migrate` | **gopgql** | already requires goose v3.26.0 and ships its own `migrate/` package |
| M6 | `goga/mcp` | **gopgql**, then **mcp-anything** | two hand-rolled servers at two SDK versions, neither instrumented |
| M7 | `goga/gogatest` | **gopgql**, then **epos** | the godog bootstrap is copy-pasted 5× and 8×; three incompatible container strategies |
| M8 | `goga/cli` | **epos**, then **gopgql** | epos calls `Execute()` and has no signal handling at all |
| M9 | `goga/di` + `goga/app` (+ the `go-generate-check` action) | **skill-test/go-service**, then **sysgo** | the pair is one deliverable: `di`'s sets exist to build `app.App`, and the action is what enforces them |
| M10 | `goga/client` | **skill-test/go-service**, then **mcp-anything** | retryablehttp in one, gobreaker in the other, neither shared |
| M11 | *(dissolved by D18)* — the remaining generic actions `go-vuln`, `go-release`, `pages-deploy` | **gopgql**, then **epos** | every module's lint rules now ship with that module (D18); what is left here is the actions that belong to no module |
| M12 | `goga/codegen` templates + `goga/grpc` | **skill-test/go-service** (oapi-codegen); **codiq** for sqlc and buf | the only milestone whose main tools have no current consumer |
| M13 | *(dissolved by D18)* — the skill's final pass: re-measure the compliance numbers, prune stale rows | every adopting project | each module shipped its own routing-table and enforcement-matrix rows as it landed; only the closing audit is left |
| — | `goga/components` | **none today** | last, and it does not start until a consumer exists (D12) |
| — | `goga/registry` | *(ships in M0)* | a leaf with no adopter of its own; every adapter-bearing module from M1 on uses it (D8) |

**D18 changes what each row contains, not the order.** The sequence above is
still the owner's, and still consumer-evidence-ordered after the four they named.
What D18 adds is that every row from M1 on now carries six parts rather than one
— implementation, tests, skill section, linter rule, CI action where a tool needs
one, and a merged adoption PR — which is why the M11 and M13 rows are struck
through above rather than reordered. They were collection points for work that
had been deferred out of the other rows, and the owner has forbidden the
deferral that created them.

**This was already the review's conclusion, reached independently.** The
`go-spec-reviewer` pass that ran before these comments recommended approving the
spec and **not building it as one unit**, on the ground that *seven of the fifteen
module surfaces have no consumer that can validate them*, while it found five
defects — three compile-level, two runtime-level — in the eight that do, which are
the surfaces that got the most design attention. Its expectation was that the
defect rate in the unvalidated half would not be lower. The owner arrived at the
same place from the other direction, and this design records the agreement rather
than presenting milestones as its own idea. Where the two differ, the owner's is
finer: the review proposed one gopgql-shaped slice of eight packages, the owner
one package at a time.

**What the milestones cost, so it is not discovered later.** A module adopted
before its neighbours exists in a project that does not yet have the rest of goga,
so some invariants are only reachable later. The sharpest case: D15 puts the
process's single signal handler in `goga/cli`, which is M8, while `goga/serve`
lands at M2 — so between M2 and M8 an adopting project keeps its own signal
handling and `serve.Run` merely takes the context it is given. The requirement
that *exactly one* handler exists is delivered with `cli`, not with `serve`. Every
capability that spans milestones this way names the milestone per requirement in
its delta spec.

### D17: goga requires Go 1.27, and it is an RC — stated plainly

The owner accepted this cost explicitly — *"let's use it even if it's alpha or
beta version"* — so this decision is not a re-litigation. It records what the
cost actually is, measured, because every consumer inherits it and the spec
should not let a reviewer discover it in CI.

**The version.** `go.mod` says `go 1.27rc2` until 1.27.0 ships, then `go 1.27`.
D8's `Table[P].Get` generic method is the only thing in goga that needs it;
everything else in the design compiles on 1.26.

**What it does to a consumer, measured on go1.26.4.** Go's module rule is that a
module cannot require a lower Go version than a module it depends on, so `go >=
1.27` propagates into gopgql, epos, skill-test/go-service, mcp-anything and
sysgo the moment they adopt any goga package — including the ones that do not
use the registry.

- With the default `GOTOOLCHAIN=auto`, a developer on 1.26.4 building a
  goga consumer **silently downloads and switches to 1.27rc2**, and the build
  succeeds. No manual install, and no warning that a release candidate is now
  compiling production code.
- With `GOTOOLCHAIN=local` — hermetic CI, distribution packaging, an air-gapped
  or proxy-restricted builder — it is a hard failure:
  `go: go.mod requires go >= 1.27rc2 (running go 1.26.4; GOTOOLCHAIN=local)`.

Both behaviours are correct and neither is a defect; the point is that the first
one hides the decision and the second one blocks a build, so the adoption PR for
M1 must state the requirement rather than let it arrive as a toolchain switch.

**What it does to the linters, which is the sharp edge.** The definition of done
in D18 requires a linter with every milestone, and the current linter release
cannot read Go 1.27 code at all:

- `golangci-lint v2.7.2` as shipped refuses outright — *"the Go language version
  (go1.26) used to build golangci-lint is lower than the targeted Go version
  (1.27rc2)"*.
- Rebuilt from source **with go1.27rc2 it still fails**, because it pins
  `golang.org/x/tools v0.39.0`, whose export-data reader tops out below Go
  1.27's format: *"cannot decode `internal/goarch`, export data version 4 is
  greater than maximum supported version 2"*. `staticcheck v0.6.1` fails the same
  way.
- **The fix is one line and it is available today.** golangci-lint v2.7.2 built
  from source against `golang.org/x/tools v0.48.0` lints the spike's
  generic-method packages cleanly — `0 issues`. A custom
  `golang.org/x/tools/go/analysis` analyzer on v0.48.0 also parses *and fully
  type-checks* a generic method, reporting its signature
  (`func[A Adapter[S], S any](name string, opts ...Option[S]) (A, error)`), which
  is what `goga/lint`'s own rules need.

So the enforcement pillar is not blocked, but it is **not free**: until
golangci-lint ships a release on a new enough x/tools, goga's `go-lint` composite
action must build golangci-lint from source with the `x/tools` bump instead of
using the upstream prebuilt action. That is a real, stated cost of the RC
dependency, and it is the one place where the Go 1.27 decision and the
"every milestone ships a linter" rule pull against each other. M0 owns it.

**The exit.** When 1.27.0 ships, `go.mod` drops the `rc2` suffix and the pinned
linter build reverts to the upstream action. Neither is a code change. If the
owner later decides the RC is too expensive for adopters, the fallback is
narrow and known: `Table[P]` loses its `Get` method and the modules keep the
free-function `Open`, which is Go 1.26 code — the rest of the design is
unaffected.

### D18: the definition of done — six parts, every milestone, no splitting

The owner, in full:

> *"Splitting functionality and enforcement is not allowed. Every milestone lands
> with: implementation; tests; skill reference; linter for enforcement even if we
> need to write a custom linter for that. We enforce that we don't use direct
> dependencies in code and wrap everything through goga; action if this tool
> needs to run in CI; migration of a project to it. A separate task but it blocks
> merge of this one because we need to be sure its actually usable."*

**This supersedes the previous revision's structure, which did exactly the thing
the first sentence forbids.** Linting was collected into M11, the skill into M13,
and CI actions were spread across M0, M9 and M11 — so eleven of fourteen
milestones shipped a package whose conventions nothing checked, and the
enforcement arrived up to ten milestones later. That is not a scheduling
preference; it is the failure mode the whole proposal is written against. The
proposal's own argument is that *"an API constrains at compile time, a linter at
edit time, CI at merge time, and a document constrains only where it is
physically present"* — a milestone that ships an API and defers the linter is a
milestone that ships one of the four.

**So `goga/lint` and the skill stop being milestones and become columns.** Every
milestone from M1 on carries all six parts, and a milestone is not done until all
six are:

1. **Implementation** — the package.
2. **Tests** — including the module's own instrumentation assertions (D6) and
   its entry in `TestEveryModuleIsInstrumented`.
3. **Skill reference** — this module's row in the routing table and its row in
   the enforcement matrix (D5), added to the skill as the module lands. The skill
   grows a section per milestone instead of being written once at the end against
   fourteen modules nobody has read in months.
4. **Linter** — at least one rule that enforces *this* module's conventions,
   written as a custom analyzer where no off-the-shelf rule exists. The owner
   names the general rule it must serve: **no direct use of a wrapped dependency
   in project code — everything goes through goga.** Concretely that is a
   `depguard` entry per module banning the import path the module wraps, plus
   whatever module-specific analyzer the conventions need. A convention with no
   rule is a D5 defect, and now it is a defect that blocks the milestone rather
   than one deferred to M11.
5. **CI action** — a composite action wherever the milestone introduces a tool
   that has to run in CI. Milestones that introduce no such tool say so
   explicitly rather than leaving the part unmentioned.
6. **Migration** — a real project adopts it. **This is a separate task that
   blocks the milestone's merge**, which is the subtlety in the owner's wording:
   it is not follow-up work and it is not part of the package's PR. It is its own
   PR in the adopting project's repo, and the milestone does not merge until that
   PR is merged. A milestone whose package is perfect and whose adoption has not
   landed is not a milestone that is nearly done; it is one that has not
   demonstrated the only thing it was for.

**The lint mechanism therefore moves to M0.** A rule cannot ship with M1 unless
the plugin module, its test harness and the `go-lint` action exist first, so M0
grows the `goga/lint` scaffold — the golangci-lint plugin module, one worked
analyzer with a test, and the `x/tools`-bumped linter build D17 requires.
`mcp-anything` already depends on `golangci/plugin-module-register`, so the
mechanism is proven in-house; what M0 adds is the harness, not the invention.
The same applies to the skill: M0 ships its skeleton — the routing table and
enforcement-matrix headings with no rows — so that M1 has somewhere to write.

**What this costs, stated.** Each milestone grows: a linter rule and its tests,
a skill section, and sometimes an action. Milestones get bigger and there are
fewer of them, because M11 and M13 dissolve into the others. The trade is
deliberate and it is the owner's: a slower milestone that lands enforced, against
a faster one that lands as a convention nobody checks. The previous revision's
M11 and M13 are the evidence for which failure is more expensive — they existed
because the enforcement had been deferred, and deferring it is what the owner has
now forbidden.

## Package surfaces: Go interfaces and pseudocode

The issue requires this and the review requires it again: *"I also don't see any
pseudocode for actual implementation and go interfaces. I need this to see how
you will create the wrappers. You MUST ADD THEM."* Every module in scope has its
surface below. Bodies are elided except where the body *is* the design — that is,
where telemetry is attached (D6) or where an option lands (D14).

Import aliases used throughout: `sdkmcp` for
`github.com/modelcontextprotocol/go-sdk/mcp`, `sdktrace`/`sdkmetric`/`sdklog` for
the OTel SDK packages, `wire` for `github.com/goforj/wire`.

**The root package is a leaf, and the composition root is `goga/app`.** Every
module writes `type Option = goga.Option[settings]` and calls `goga.Apply`, so
every module imports the root package. The composition root holds fields of type
`*serve.Server`, `*database.DB`, `*mcp.Server`, so it imports every module. Those
two cannot be the same package — that is an import cycle across the whole
framework, and an earlier revision had exactly that. Root `goga` therefore
contains `Option` and `Apply` and imports nothing but the standard library;
`goga/app` contains `App` and `Run`. sysgo's `main.go.tmpl` (D3) emits
`app.Run(ctx, a)`.

### `goga/registry` and the module tables (D8)

`goga/registry` holds the storage once; each adapter-bearing module holds a
`Table[P]` for its own port and declares its own typed opener over it. The
package is a **leaf** — standard library only — so every module can import it and
no import cycle is possible.

```go
package registry

// Table stores adapters for one port P. It is generic over the PORT, per the
// owner: "an adapter is for a port which is the generic for the registry".
type Table[P any] struct {
	mu      sync.RWMutex
	factory map[string]func() P
}

func NewTable[P any]() *Table[P]

// Register PANICS on a duplicate key, following gocloud.dev's URLMux: a
// duplicate registration is a programming error in an init(), not a runtime
// condition. Adapters call it from init() and are selected by blank import.
func (t *Table[P]) Register(key string, new func() P)

// New returns the adapter as the PORT. No type parameter; this is the path
// every module's opener takes.
func (t *Table[P]) New(key string) (P, error)

func (t *Table[P]) Keys() []string

// Get is the Go 1.27 generic METHOD — "a structure that can cast interfaces
// (ports) into adapters". It returns the adapter's CONCRETE type, so an
// adapter's own surface (pgx's CopyFrom, Batch, LISTEN/NOTIFY) is reachable
// with no assertion at the call site.
//
// A is `any`, NOT constrained to P: `Get[A P]` does not compile ("cannot use a
// type parameter as constraint") and neither does `interface{ P }` ("term
// cannot be a type parameter"). So a mismatched A is a RUNTIME error, not a
// compile error, and it names both types. What is *in* the table is still
// compile-checked, because Register takes a P.
//
// This method is the only part of goga that requires Go 1.27 (D17).
func (t *Table[P]) Get[A any](key string) (A, error)
```

Each module then declares its own port, its own key convention and its own
typed opener. The shape is given once here, for `goga/database`; `serve`,
`telemetry`, `mcp` and `components` repeat it with their own port and key.

```go
package database

// Adapter ties a concrete adapter type to (a) THIS module's port and (b) the
// settings type that adapter consumes. Constraining A by a generic interface
// instantiated with the method's other type parameter is legal, and it is what
// buys back the compile-time port check Table.Get cannot give.
type Adapter[S any] interface {
	driver.DB
	Init(S) error
}

// P is the OPENER for a URL-keyed module, because opening needs the URL and the
// module's settings. Name-keyed modules whose adapters need neither store the
// adapter directly, and it is their tables that use Table.Get. Either way the
// stored value is a factory, so every resolution constructs a fresh adapter and
// two Opens never share one.
var drivers = registry.NewTable[driver.Opener]()

// Register adds an adapter. Adapters call it from init() and are selected by
// blank import, as in gocloud.dev:
//
//	import _ "github.com/gaarutyunov/goga/database/pgxdb"
//
// The factory shape is normative and identical in every module: registry.Table
// stores func() P, never a P, so an adapter registered once cannot become shared
// mutable state across two callers.
func Register(scheme string, o func() driver.Opener) { drivers.Register(scheme, o) }

// Schemes reports what is registered, for diagnostics and for the error below.
func Schemes() []string { return drivers.Keys() }

// There is no exported lookup returning a raw driver.DB — that would be a goga
// entry point handing back an uninstrumented object (D5, D6). Open returns the
// portable *DB, which owns the telemetry.
//
// resolve is unexported and instrumented: "which adapter did this process
// actually resolve" is an operational question (D6). The span belongs here and
// not to registry.Table, which is a leaf with no Instrumentation (D8).
// Named results, because the deferred end() must observe the error the return
// statement produced (D15).
//
// The error on an unknown scheme names the registered ones and points at the
// likely cause, so a typo is self-diagnosing rather than a silent no-op:
//
//	goga/database: no adapter for scheme "mysql" (registered: pgx, postgres);
//	did you forget a blank import of github.com/gaarutyunov/goga/database/pgxdb?
func resolve(ctx context.Context, u *url.URL, s *settings) (db driver.DB, err error) {
	ctx, end := s.instr.Start(ctx, "resolve", semconv.AdapterScheme(u.Scheme))
	defer func() { end(err) }()

	o, err := drivers.New(u.Scheme)
	if err != nil {
		return nil, &UnknownSchemeError{Module: "goga/database", Scheme: u.Scheme, Known: Schemes()}
	}
	return o.Open(ctx, u, s)
}
```

Two keys, two shapes, and neither module knows the other exists — the shared
storage does not merge them, because each module instantiates its own `Table[P]`
with its own key convention (D8). `database` and `client` are **URL-keyed**: they
`url.Parse` the caller's connection string and use its scheme. `serve`,
`telemetry`, `mcp` and `components` are **name-keyed**: their tables are keyed on
a plain adapter name (`"gin"`, `"otlp"`, `"stdio"`, `"local"`) with no URL
anywhere. There is no shared `Open`/`OpenNamed` pair to confuse, so the earlier
revision's `Routers.Open(ctx, "router://"+name)` — which resolved the scheme
`router` and could never have found the gin adapter — is still not expressible.

### `goga/telemetry` — the module every other module depends on (D6)

```go
package telemetry

type settings struct{ /* unexported (D5); Settings below is the read-only view */ }
type Option = goga.Option[settings]

func WithServiceName(name string) Option
func WithServiceVersion(v string) Option
func WithResourceAttributes(kv ...attribute.KeyValue) Option
func WithTraceExporter(name string) Option   // resolved via TraceExporters
func WithMetricExporter(name string) Option
func WithLogExporter(name string) Option
func WithPrometheus(enabled bool) Option     // reader attached by default
func WithShutdownTimeout(d time.Duration) Option
func WithPropagators(names ...string) Option // delegates to contrib/autoprop

// Exporter tables — this module's own, name-keyed (D8). The standard names
// delegate to contrib/exporters/autoexport, which mcp-anything already depends
// on; house names are additive. Each Register panics on a duplicate name, and
// there is no exported lookup.
//
// The tables live in the package whose Instrumentation they use, which is where
// an import cycle went: registry.Table is a leaf and carries no telemetry, so
// registry -> telemetry -> registry cannot form (D8).
func RegisterTraceExporter(name string, o TraceExporterOpener)
func RegisterMetricExporter(name string, o MetricExporterOpener)
func RegisterLogExporter(name string, o LogExporterOpener)

func TraceExporters() []string  // registered names, for diagnostics
func MetricExporters() []string
func LogExporters() []string

// No settings parameter: an exporter reads its endpoint, headers and protocol
// from the environment through autoexport, and the resource is built by Setup
// and attached to the provider, not to the exporter. There is no
// telemetry.Settings, per D5's rule that a module passes settings to an opener
// only where an adapter reads them.
type TraceExporterOpener interface {
	Open(ctx context.Context) (sdktrace.SpanExporter, error)
}

// Telemetry is returned as well as installed globally, because epos needs a
// metrics-only subset and go-service passes providers into libraries.
type Telemetry struct {
	Tracer trace.Tracer
	Meter  metric.Meter
	Logger *slog.Logger

	TracerProvider *sdktrace.TracerProvider
	MeterProvider  *sdkmetric.MeterProvider
	LoggerProvider *sdklog.LoggerProvider
}

// Shutdown flushes every provider and joins the errors, so the first failure
// cannot mask the rest. It is a method rather than a returned closure because
// wire only recognises a cleanup of type func() (D9); Setup's third return is
// that func(), and it calls Shutdown under the configured timeout.
func (t *Telemetry) Shutdown(ctx context.Context) error

// Setup establishes all three signals or none.
func Setup(ctx context.Context, opts ...Option) (*Telemetry, func(), error) {
	s, err := goga.Apply(defaults(), opts...)
	...
	res, err := resource.New(ctx, resource.WithAttributes(semconv.ServiceName(s.serviceName), ...))
	tp, err := s.traceProvider(ctx, res)   // unknown exporter name → UnknownSchemeError
	mp, err := s.metricProvider(ctx, res)
	lp, err := s.logProvider(ctx, res)
	otel.SetTracerProvider(tp)
	otel.SetMeterProvider(mp)              // epos omits this today; the wrapper cannot
	otel.SetTextMapPropagator(autoprop.NewTextMapPropagator())
	global.SetLoggerProvider(lp)
	slog.SetDefault(slog.New(otelslog.NewHandler(...)))
	t := &Telemetry{...}
	return t, func() {
		ctx, cancel := context.WithTimeout(context.Background(), s.shutdownTimeout)
		defer cancel()
		_ = t.Shutdown(ctx)
	}, nil
}

// Instrumentation is the per-module handle. Every goga module that performs a
// runtime operation holds one, and there is no constructor that produces such a
// module without one (D6).
type Instrumentation struct {
	module string
	tracer trace.Tracer
	meter  metric.Meter
	logger *slog.Logger
	dur    metric.Float64Histogram
	errs   metric.Int64Counter
}

// For returns the instrumentation for a module. It resolves through OTel's
// GLOBAL delegating providers (otel.Tracer / otel.Meter), never by snapshotting
// a concrete provider — every module's adapter table is a package-level var and
// adapters self-register from init(), both before Setup runs, and a snapshot
// would leave those paths permanently no-op while every test passed (D6). It
// never fails: before Setup the globals
// are no-ops, so a library like gopgql can call goga/database without
// configuring telemetry, and telemetry appears the moment the consuming binary
// calls Setup.
//
// For also records `module` in the package-level set that
// TestEveryModuleIsInstrumented asserts against.
func For(module string) *Instrumentation

// Start opens the span and returns the function that closes it. Returning the
// closer rather than a (span, start) pair the caller must hand back is the whole
// point: the duration belongs to the type that started it, so it cannot be
// mis-measured at the call site (D15). The span stays reachable through
// trace.SpanFromContext(ctx) for a caller that adds attributes mid-operation.
//
// The returned func is called exactly once, normally as `defer func() { end(err) }()`
// over a NAMED result — a deferred closure over an unnamed result sees a stale
// nil (D15).
func (i *Instrumentation) Start(ctx context.Context, op string, attrs ...attribute.KeyValue) (context.Context, func(error)) {
	start := time.Now()
	ctx, span := i.tracer.Start(ctx, "goga."+i.module+"."+op, trace.WithAttributes(attrs...))
	return ctx, func(err error) {
		attrs := []attribute.KeyValue{semconv.OperationName(op)}
		if err != nil {
			span.RecordError(err)
			span.SetStatus(codes.Error, err.Error())
			attrs = append(attrs, semconv.ErrorTypeKey.String(errorType(err)))
			i.errs.Add(ctx, 1, metric.WithAttributes(attrs...))
		}
		i.dur.Record(ctx, time.Since(start).Seconds(), metric.WithAttributes(attrs...))
		span.End()
	}
}

func (i *Instrumentation) Logger() *slog.Logger

var Set = wire.NewSet(Setup, wire.Bind(...))
```

### `goga/config`

```go
package config

type settings struct{ /* unexported, unnameable outside this package (D5) */ }
type Option = goga.Option[settings]

func WithDefaults(m map[string]any) Option
func WithFile(path string) Option          // absent file is not an error
func WithRequiredFile(path string) Option
func WithEnv(prefix string) Option         // house convention, see below
func WithFlags(fs *pflag.FlagSet) Option
func WithRequiredKeys(keys ...string) Option
func WithDecodeHook(h mapstructure.DecodeHookFunc) Option
func WithWatch(fn func(Event)) Option      // fsnotify; mcp-anything reloads today

// Config carries the typed value and the raw koanf handle, because
// go-service's k.Cut() subtree pattern cannot be expressed without it.
type Config[T any] struct {
	Value T
	K     *koanf.Koanf
}

// Cut returns a subtree handle for an adapter factory.
func (c *Config[T]) Cut(path string) *koanf.Koanf

// Load applies sources in the fixed house order — defaults, file, env, flags —
// which is a property of Load and NOT of the order the options are passed. That
// is deliberate: epos's posflag callback inverts its apparent precedence today,
// and an option-ordered API would preserve that hazard.
//
// House env convention, chosen once because three projects chose three: prefix
// upper-snake, "__" separates path segments, "_" is a literal underscore within
// a segment. GOGA__DATABASE__MAX_CONNS → database.max_conns.
//
// Named results: the deferred end() must see the error the return statement
// produced, not the one the last := happened to leave behind (D15).
func Load[T any](ctx context.Context, opts ...Option) (cfg *Config[T], err error) {
	s, err := goga.Apply(defaults(), opts...)
	if err != nil {
		return nil, err
	}
	ctx, end := telemetry.For("config").Start(ctx, "load", semconv.ConfigSources(s.sourceNames()))
	defer func() { end(err) }()

	k := koanf.New(".")
	for _, src := range s.sourcesInHouseOrder() {   // not s.sources
		if err := src.load(k); err != nil && src.required {
			return nil, fmt.Errorf("goga/config: loading %s: %w", src.name, err)
		}
	}
	// A missing required key fails naming the key, rather than yielding a zero.
	if missing := s.missingRequired(k); len(missing) > 0 {
		return nil, &MissingKeysError{Keys: missing}
	}
	var v T
	if err := k.UnmarshalWithConf("", &v, s.unmarshalConf()); err != nil {
		return nil, fmt.Errorf("goga/config: unmarshalling into %T: %w", v, err)
	}
	return &Config[T]{Value: v, K: k}, nil
}

// Load is generic, so wire cannot provide it (D9): the project writes the
// one-line instantiation for its own config type and puts that in its own set.
// config.Set provides what is downstream of the loaded value.
var Set = wire.NewSet(...)
```

### `goga/cli` — cobra

```go
package cli

type settings struct{ /* unexported, unnameable outside this package (D5) */ }
type Option = goga.Option[settings]

func WithName(name string) Option
func WithVersion(v string) Option
func WithConfigFlag(defaultPath string) Option // wires --config into config.WithFile
func WithTelemetryFlags() Option               // --otel-exporter etc., added by default
func WithSubcommands(cmds ...*cobra.Command) Option

type App struct {
	root  *cobra.Command
	instr *telemetry.Instrumentation
}

func New(opts ...Option) (*App, error)

// Run always uses ExecuteContext with a signal-aware context and returns a
// non-zero-mapping error. epos calls Execute() today and has no signal handling
// at all; there is no way to reach the plain Execute path through goga.
//
// This is the ONLY place in goga that calls signal.NotifyContext (D15). Every
// other runnable surface takes the ctx and stops when it is cancelled, so a
// process serving HTTP and MCP together has one shutdown with one ordering
// rather than three racing ones.
func (a *App) Run(ctx context.Context) error

func (a *App) Cobra() *cobra.Command // escape hatch

var Set = wire.NewSet(New)
```

### `goga/database` and `goga/database/driver` (D7)

```go
package driver // goga/database/driver

// DB is what an adapter implements. Deliberately narrow, and carrying no
// telemetry: instrumentation lives in the portable type, exactly as
// gocloud.dev/blob keeps the tracer on Bucket and not on s3blob (D6).
type DB interface {
	QueryContext(ctx context.Context, sql string, args []any) (Rows, error)
	ExecContext(ctx context.Context, sql string, args []any) (Result, error)
	BeginTx(ctx context.Context, opts TxOptions) (Tx, error)
	// SQLDB exposes a database/sql handle for tools that require one — goose
	// does (D10). An adapter that cannot provide one returns ErrNoSQLDB.
	SQLDB() (*sql.DB, error)
	Close() error
	// Unwrap returns the native handle (*pgxpool.Pool for pgxdb).
	Unwrap() any
}

type Tx interface {
	QueryContext(ctx context.Context, sql string, args []any) (Rows, error)
	ExecContext(ctx context.Context, sql string, args []any) (Result, error)
	Commit(ctx context.Context) error
	Rollback(ctx context.Context) error
}

type Rows interface {
	Next() bool
	Scan(dest ...any) error
	Err() error
	Close()
}

// Settings is the read-only view of goga/database's resolved settings that an
// adapter reads. It lives here because an adapter imports this package anyway
// for driver.DB, and because it is the whole reason database's own settings
// struct can stay unexported (D5): the adapter names this interface, never the
// struct. Accessors only — there is nothing here that populates one, and no goga
// entry point accepts one.
type Settings interface {
	MaxConns() int
	MinConns() int
	ConnMaxLifetime() time.Duration
	QueryTimeout() time.Duration
	SQLCommenter() bool
}

// Opener is what an adapter implements — declared by the module it serves, not
// by goga/registry (D8). registry.Table stores adapters; it never dictates an
// opener signature, which is what lets Settings be an interface of this
// module's choosing.
type Opener interface {
	Open(ctx context.Context, u *url.URL, s Settings) (DB, error)
}
```

**Does this split admit a second adapter?** Every method above is expressible on
`database/sql`, so yes in principle — but "in principle" is how one-implementation
abstractions get shipped. v1 therefore includes a second adapter,
`goga/database/sqldb`, wrapping any `database/sql` driver (`sqlite://` for tests,
`mysql://`). It is roughly a hundred lines, it is the only way to find out
whether `driver.DB` is actually portable before three projects depend on it, and
it gives `gogatest` a container-free path. `SQLDB()` is trivially satisfied
there and returns `ErrNoSQLDB` for any future adapter that has no such handle.

```go
package database

type settings struct{ /* unexported, unnameable outside this package (D5) */ }
type Option = goga.Option[settings]

// URL is a named type so wire's type-keyed graph can supply it (D9).
type URL string

func WithMaxConns(n int) Option
func WithMinConns(n int) Option
func WithConnMaxLifetime(d time.Duration) Option
func WithQueryTimeout(d time.Duration) Option
func WithSQLCommenter(on bool) Option // injects trace context into SQL comments
func WithTelemetry(i *telemetry.Instrumentation) Option // replaces; never disables

// Register and Schemes are this module's adapter table, shown in full above
// (D8). Register exists so a project can add an adapter goga does not ship;
// there is deliberately no exported lookup, so no goga entry point hands back a
// raw driver.DB. The parameter is a FACTORY, matching registry.Table.Register.
func Register(scheme string, o func() driver.Opener)
func Schemes() []string

// DB is the portable type. Its fields are unexported and Open is its only
// exported constructor, so no exported goga entry point produces an
// uninstrumented *DB. That is how D6 is enforced structurally rather than by
// review.
type DB struct {
	drv   driver.DB
	instr *telemetry.Instrumentation
	s     *settings
}

// Open resolves the URL's scheme against this module's table. Adapters are
// selected by blank import, as in gocloud.dev:
//
//	import _ "github.com/gaarutyunov/goga/database/pgxdb"
//	db, err := database.Open(ctx, cfg.Value.DatabaseURL, database.WithMaxConns(20))
func Open(ctx context.Context, u URL, opts ...Option) (*DB, error) {
	s, err := goga.Apply(defaults(), opts...) // defaults sets s.instr = telemetry.For("database")
	if err != nil {
		return nil, err
	}
	parsed, err := url.Parse(string(u))
	if err != nil {
		return nil, fmt.Errorf("goga/database: parsing %s: %w", redact(u), err)
	}
	// resolve passes s — the unexported struct — where the adapter sees only
	// driver.Settings, the accessor interface it satisfies (D5).
	drv, err := resolve(ctx, parsed, &s) // adapter returns driver.DB, never *DB
	if err != nil {
		return nil, fmt.Errorf("goga/database: opening %s: %w", redact(u), err)
	}
	return &DB{drv: drv, instr: s.instr, s: &s}, nil
}

// OpenAs is the TYPED path (D8). The caller names the adapter it wants and
// configures it with THAT adapter's own options; A is constrained by this
// module's port, so a type that does not implement driver.DB does not compile.
// The return is still the portable *DB — the concrete type is an input here,
// never the output, which is what keeps D6 intact.
//
//	db, err := database.OpenAs[*pgxdb.DB](ctx, cfg.Value.DatabaseURL,
//	        pgxdb.WithMaxConns(20))
//
// Configuration for the adapter is decoded into S first and the options are
// applied over it, so an explicit option always beats a config file (D14).
func OpenAs[A driver.Adapter[S], S any](ctx context.Context, u URL, opts ...driver.AdapterOption[S]) (*DB, error)

// Unwrap is the TYPED ESCAPE HATCH, and the point at which the concrete adapter
// is finally handed over. The caller already holds the portable object and is
// asking to leave it, which is what D2 documents and D6 exempts. It replaces the
// untyped accessor an earlier revision had, so pgx's CopyFrom, Batch and
// LISTEN/NOTIFY are reached without an assertion written at the call site.
//
//	pool, err := database.Unwrap[*pgxpool.Pool](db)
func Unwrap[A any](db *DB) (A, error)

// Query returns a STREAMING result, so neither the timeout nor the span may be
// released when Query returns — the rows have not been read yet. The portable
// Rows owns both: Close cancels the timeout context and ends the span, so the
// recorded duration covers the whole read and the caller does not receive rows
// whose context is already cancelled (D15).
//
// An earlier revision deferred cancel() and the span-end inside Query. That
// returns rows that fail on the first Next() with "context canceled", and
// records a query duration that excludes the query.
func (db *DB) Query(ctx context.Context, sql string, args ...any) (Rows, error) {
	ctx, end := db.instr.Start(ctx, "query", semconv.DBQueryText(sql), semconv.DBSystemPostgreSQL)
	ctx, cancel := context.WithTimeout(ctx, db.s.queryTimeout)

	dr, err := db.drv.QueryContext(ctx, db.s.comment(ctx, sql), args)
	if err != nil {
		cancel()
		end(err)
		return nil, fmt.Errorf("goga/database: query: %w", err)
	}
	return &rows{Rows: dr, cancel: cancel, end: end}, nil
}

// rows closes the operation exactly once, whether the caller ranges to
// completion or abandons the read. Close is idempotent.
type rows struct {
	driver.Rows
	cancel context.CancelFunc
	end    func(error)
	once   sync.Once
}

func (r *rows) Close() {
	r.once.Do(func() {
		r.Rows.Close()
		r.end(r.Rows.Err())
		r.cancel()
	})
}

// Exec is non-streaming, so it keeps the plain deferred shape. Named results,
// per D15.
func (db *DB) Exec(ctx context.Context, sql string, args ...any) (res Result, err error) {
	ctx, end := db.instr.Start(ctx, "exec", semconv.DBQueryText(sql), semconv.DBSystemPostgreSQL)
	defer func() { end(err) }()

	ctx, cancel := context.WithTimeout(ctx, db.s.queryTimeout)
	defer cancel()
	return db.drv.ExecContext(ctx, db.s.comment(ctx, sql), args)
}

// Tx runs fn in a transaction, committing on nil and rolling back on error or
// panic. Three projects would otherwise each write this. The timeout bounds the
// whole callback, not each statement in it, so a transaction cannot outlive its
// own budget one query at a time.
func (db *DB) Tx(ctx context.Context, fn func(context.Context, Tx) error, opts ...TxOption) error

// SQLDB is the database/sql bridge goose needs (D10). For pgxdb it is
// stdlib.OpenDBFromPool(pool), so no caller has to know that.
func (db *DB) SQLDB() (*sql.DB, error)

func (db *DB) Close() error
func (db *DB) Unwrap() any // *pgxpool.Pool for pgxdb

// Open's cleanup is a func(), which is the only cleanup shape wire recognises
// (D9); it calls Close.
var Set = wire.NewSet(openWithCleanup)
```

```go
package pgxdb // goga/database/pgxdb

func init() {
	database.Register("postgres", opener{})
	database.Register("pgx", opener{})
}

type opener struct{}

// The type named here is driver.Settings — an INTERFACE of accessors, not the
// module's settings struct, which stays unexported and unnameable from this
// package (D5). goga/registry does not change this: it stores adapters and
// dictates no opener signature, so the opener is still declared by
// goga/database and what it passes is that module's choice (D8).
func (opener) Open(ctx context.Context, u *url.URL, s driver.Settings) (driver.DB, error) {
	cfg, err := pgxpool.ParseConfig(u.String())
	if err != nil {
		return nil, fmt.Errorf("goga/database/pgxdb: parsing config: %w", err)
	}
	cfg.MaxConns = int32(s.MaxConns())
	// otelpgx is already the house choice (mcp-anything). Two span levels on
	// purpose: goga.database.query is the logical operation, otelpgx's is the
	// wire-level one.
	cfg.ConnConfig.Tracer = otelpgx.NewTracer(otelpgx.WithTrimSQLInSpanName())
	pool, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		return nil, err
	}
	return &pgxDB{pool: pool}, otelpgx.RecordStats(pool)
}
```

```go
package sqlcdb // goga/database/sqlcdb — the sqlc runtime seam (D11)

// DBTX is the interface sqlc's pgx/v5 mode generates against. Satisfying it here
// means generated sqlc queries run on the portable *database.DB and inherit its
// telemetry, with no generated line changing.
//
// Note the types: pgx.Rows, pgconn.CommandTag, pgx.Batch. They are sqlc's
// choice, not goga's, and no non-pgx adapter can satisfy them — so New returns
// ErrNotPgx rather than pretending this seam is adapter-neutral (D11).
type DBTX interface {
	Exec(context.Context, string, ...any) (pgconn.CommandTag, error)
	Query(context.Context, string, ...any) (pgx.Rows, error)
	QueryRow(context.Context, string, ...any) pgx.Row
	CopyFrom(context.Context, pgx.Identifier, []string, pgx.CopyFromSource) (int64, error)
	SendBatch(context.Context, *pgx.Batch) pgx.BatchResults
}

// ErrNotPgx is returned when db resolved to an adapter other than pgxdb.
var ErrNotPgx = errors.New("goga/database/sqlcdb: generated sqlc code requires the pgx adapter")

func New(db *database.DB) (DBTX, error)
```

### `goga/migrate` — goose (D10)

```go
package migrate

type settings struct{ /* unexported, unnameable outside this package (D5) */ }
type Option = goga.Option[settings]

func WithFS(fsys fs.FS) Option              // embedded is the house default
func WithDir(dir string) Option
func WithTable(name string) Option          // default: goga_db_version
func WithDialect(d string) Option           // default: postgres
func WithAllowMissing(on bool) Option
func WithLockTimeout(d time.Duration) Option // advisory lock; default 30s
func WithSessionLocker(l lock.SessionLocker) Option

type Migrator struct {
	provider *goose.Provider
	instr    *telemetry.Instrumentation
}

// New bridges to database/sql because goose requires it; the bridge lives in
// goga/database so no caller writes stdlib.OpenDBFromPool by hand.
func New(db *database.DB, opts ...Option) (*Migrator, error)

// Up takes a session-level advisory lock first, so two replicas booting together
// do not both migrate. A span per migration carries its version and name, which
// is how you discover the migration that takes 40 seconds.
func (m *Migrator) Up(ctx context.Context) (applied []Applied, err error) {
	ctx, end := m.instr.Start(ctx, "up")
	defer func() { end(err) }()

	release, err := m.lock(ctx) // advisory lock, m.s.LockTimeout()
	if err != nil {
		return nil, fmt.Errorf("goga/migrate: acquiring lock: %w", err)
	}
	defer release() // released on failure too, so a later attempt is not blocked

	pending, err := m.Pending(ctx)
	if err != nil {
		return nil, err
	}
	for _, src := range pending {
		mctx, mend := m.instr.Start(ctx, "apply",
			semconv.MigrationVersion(src.Version), semconv.MigrationName(src.Path))
		res, aerr := m.provider.ApplyVersion(mctx, src.Version, true)
		mend(aerr) // the closure holds this migration's start time (D15)
		if aerr != nil {
			return applied, fmt.Errorf("goga/migrate: migration %d (%s): %w", src.Version, src.Path, aerr)
		}
		applied = append(applied, Applied(res))
	}
	return applied, nil
}

func (m *Migrator) UpTo(ctx context.Context, version int64) ([]Applied, error)
func (m *Migrator) Down(ctx context.Context) (Applied, error)
func (m *Migrator) Status(ctx context.Context) ([]Status, error)

// Pending feeds a readiness check, so a service with a behind schema refuses
// traffic instead of erroring per request.
func (m *Migrator) Pending(ctx context.Context) ([]Status, error)

func (m *Migrator) Provider() *goose.Provider // escape hatch

var Set = wire.NewSet(New)
```

### `goga/serve` and the router adapters (D8)

```go
package serve

type settings struct{ /* unexported, unnameable outside this package (D5) */ }
type Option = goga.Option[settings]

// Addr is a named type so wire can supply it unambiguously (D9).
type Addr string

func WithAddr(addr string) Option
func WithOpsAddr(addr string) Option    // ops listener; default: same port, separate mux
func WithRouter(name string) Option     // "mux" (default) | "gin" | "chi"
func WithReadHeaderTimeout(d time.Duration) Option
func WithReadTimeout(d time.Duration) Option
func WithWriteTimeout(d time.Duration) Option
func WithShutdownGrace(d time.Duration) Option
func WithHealthCheck(name string, fn func(context.Context) error) Option
func WithReadinessCheck(name string, fn func(context.Context) error) Option
func WithMiddleware(mw ...func(http.Handler) http.Handler) Option
func WithHandler(pattern string, h http.Handler) Option

// Router is the seam gin, chi and the standard library sit behind. Narrow on
// purpose: oapi-codegen's generated server needs only Handle and Use.
//
// Pattern syntax is the framework's, not the adapter's: "/users/{id}", which
// each adapter translates (gin: ":id"). Stating it here is what makes "changing
// router does not change handlers" true rather than aspirational.
//
// Use MUST be called before the first Handle, and an adapter MUST panic if it is
// not. This is a portability requirement, not a nicety: chi already panics,
// gin silently applies middleware only to routes registered afterwards, and a
// stdlib wrapper applies it to everything. Left unspecified, the same code on
// three adapters gets three different middleware coverages, silently — the exact
// failure a seam exists to prevent. serve.New applies the configured middleware
// at construction, before any handler is registered.
type Router interface {
	http.Handler
	Handle(method, pattern string, h http.Handler)
	Use(mw ...func(http.Handler) http.Handler)
	Unwrap() any // *gin.Engine, *chi.Mux, *http.ServeMux
}

// RouterOpener is what a router adapter implements. Declared here, by the module
// it serves (D8), and taking NO settings: gin, chi and mux each build an engine
// and read nothing the caller configured — serve.New applies the middleware, the
// handlers and the timeouts itself. There is no serve.Settings, because an
// opener parameter no adapter reads is an abstraction with no user (D5).
// goga/registry stores func() RouterOpener values and imposes no signature of
// its own, so this stays a per-module decision (D8).
type RouterOpener interface {
	Open(ctx context.Context) (Router, error)
}

// RegisterRouter adds a router adapter under a plain NAME — "gin", "chi", "mux"
// — because there is no URL here to carry a scheme. This module's table is
// name-keyed; goga/database's is URL-keyed; neither knows about the other (D8).
// Panics on a duplicate name; no exported lookup.
func RegisterRouter(name string, o RouterOpener)
func RouterNames() []string

// Server is the portable type; app and ops are deliberately different muxes.
type Server struct {
	app   Router
	ops   *http.ServeMux // /livez /readyz /healthz /metrics — NEVER traced
	http  *http.Server
	instr *telemetry.Instrumentation
}

// New wraps the app router — once — in otelhttp, and registers the operational
// endpoints on a mux that is outside that wrapper. go-service discovered this by
// hand; encoding it is the point of the wrapper.
func New(ctx context.Context, opts ...Option) (*Server, error) {
	s, err := goga.Apply(defaults(), opts...)
	...
	// A plain name lookup: "gin" is a name, not a URL scheme. An earlier
	// revision passed "router://"+s.router to a registry with both a URL and a
	// name path, which resolved the scheme "router" and could never have found
	// the gin adapter. This module's Table[RouterOpener] is keyed on the name
	// alone and there is no URL path to fall into (D8).
	app, err := resolveRouter(ctx, s.router)
	...
	app.Use(s.middleware...) // before any Handle — the Router contract requires it
	for _, h := range s.handlers {
		app.Handle(h.method, h.pattern, h.handler)
	}
	traced := otelhttp.NewHandler(app, "", otelhttp.WithSpanNameFormatter(routePattern))

	ops := http.NewServeMux()
	ops.Handle("/metrics", promhttp.Handler())
	ops.HandleFunc("/livez", live(s.healthChecks))
	ops.HandleFunc("/readyz", ready(s.readinessChecks)) // migrate.Pending plugs in here
	ops.HandleFunc("/healthz", health(s.healthChecks))

	root := http.NewServeMux()
	root.Handle("/", traced)
	for _, p := range opsPaths {
		root.Handle(p, ops) // registered on root, outside otelhttp
	}
	return &Server{app: app, ops: ops, http: &http.Server{
		Handler:           root,
		ReadHeaderTimeout: s.readHeaderTimeout, // never left unbounded
		ReadTimeout:       s.readTimeout,
		WriteTimeout:      s.writeTimeout,
	}, instr: telemetry.For("serve")}, nil
}

// Run serves until ctx is cancelled, then drains within a bounded grace period.
// It does NOT install signal handling: cli.App.Run owns that, so a process
// serving HTTP and MCP together drains once, in one order (D15). An earlier
// revision called signal.NotifyContext here, which gave such a process three
// independent shutdowns with no ordering between draining connections, closing
// the pool and flushing telemetry.
func (s *Server) Run(ctx context.Context) error {
	errc := make(chan error, 1) // buffered: the goroutine never blocks after we return
	go func() { errc <- s.http.ListenAndServe() }()
	select {
	case err := <-errc:
		if errors.Is(err, http.ErrServerClosed) {
			return nil
		}
		return fmt.Errorf("goga/serve: %w", err)
	case <-ctx.Done():
		sctx, cancel := context.WithTimeout(context.WithoutCancel(ctx), s.s.ShutdownGrace())
		defer cancel()
		return s.http.Shutdown(sctx) // in-flight work finishes, or the grace expires
	}
}

func (s *Server) Router() Router
func (s *Server) Ops() *http.ServeMux
func (s *Server) HTTP() *http.Server

var Set = wire.NewSet(New)
```

```go
package ginrouter // goga/serve/ginrouter — sysgo's current router; the owner's target for skill-test

func init() { serve.RegisterRouter("gin", opener{}) }

type opener struct{}

// No settings parameter: this adapter reads nothing the caller configured, and
// serve's settings struct is unexported and unnameable here anyway (D5).
//
// The adapter holds no telemetry: serve.Server wraps whatever Router it gets in
// otelhttp exactly once, so gin, chi and mux are instrumented identically and no
// adapter author can forget (D6).
func (opener) Open(ctx context.Context) (serve.Router, error) {
	gin.SetMode(gin.ReleaseMode)
	e := gin.New()
	e.Use(gin.Recovery()) // gin's own logger is omitted: slog is the house logger
	return &ginRouter{e: e}, nil
}

type ginRouter struct {
	e       *gin.Engine
	handled bool
}

func (r *ginRouter) Handle(method, pattern string, h http.Handler) {
	r.handled = true
	r.e.Handle(method, ginPattern(pattern), gin.WrapH(h)) // {id} → :id
}

// Use panics after the first Handle, because gin would otherwise apply the
// middleware only to later routes — silently, and differently from chi and mux.
// The Router contract makes that a programming error rather than a surprise.
func (r *ginRouter) Use(mw ...func(http.Handler) http.Handler)
func (r *ginRouter) ServeHTTP(w http.ResponseWriter, req *http.Request) { r.e.ServeHTTP(w, req) }
func (r *ginRouter) Unwrap() any                                        { return r.e }
```

`chirouter` and `muxrouter` are the same shape; `muxrouter` is the default so a
project pays for no router dependency it did not ask for.

### `goga/client`

```go
package client

type settings struct{ /* unexported, unnameable outside this package (D5) */ }
type Option = goga.Option[settings]

func WithBaseURL(u string) Option
func WithTimeout(d time.Duration) Option
func WithRetries(n int) Option                       // 0 disables; configurable, not hardcoded
func WithBackoff(min, max time.Duration) Option
func WithRetryOn(fn func(*http.Response, error) bool) Option
func WithBreaker(failures int, reset time.Duration) Option // gobreaker (mcp-anything)
func WithHeader(k, v string) Option

type Client struct {
	http  *http.Client
	instr *telemetry.Instrumentation
}

// New layers, innermost first: otelhttp.NewTransport (client span + W3C context
// propagation + client metrics) → retryablehttp (already in go-service) → the
// breaker. Retries are logged through the module logger rather than silently
// absorbed, which is the failure mode a bare retryablehttp has.
func New(opts ...Option) (*Client, error)

func (c *Client) Do(req *http.Request) (*http.Response, error)
func (c *Client) HTTP() *http.Client // any library taking an *http.Client can be used

var Set = wire.NewSet(New)
```

### `goga/mcp` — the MCP SDK wrapper (owner: gopgql and sysgo both need it)

```go
package mcp

type settings struct{ /* unexported, unnameable outside this package (D5) */ }
type Option = goga.Option[settings]

func WithName(name string) Option
func WithVersion(v string) Option
func WithInstructions(text string) Option
func WithTransport(name string) Option        // "stdio" (default) | "http" | "sse"
func WithToolTimeout(d time.Duration) Option
func WithAuthenticator(a Authenticator) Option
func WithTelemetry(i *telemetry.Instrumentation) Option

// This module's own name-keyed transport table (D8): "stdio", "http", "sse".
//
// Settings is declared beside Transport, the port these adapters implement, and
// carries only what a transport actually reads — the HTTP and SSE transports
// need an endpoint, stdio needs nothing. mcp's settings struct stays unexported
// and implements this (D5).
type Settings interface {
	Endpoint() string
}

type TransportOpener interface {
	Open(ctx context.Context, s Settings) (Transport, error)
}

func RegisterTransport(name string, o TransportOpener)
func TransportNames() []string

// Server is the portable type. srv is unexported and New is its only
// constructor, so a tool cannot be registered on an uninstrumented server.
type Server struct {
	srv   *sdkmcp.Server
	instr *telemetry.Instrumentation
	s     *settings // resolved settings; AddTool reads the tool timeout from it
}

func New(opts ...Option) (*Server, error) {
	s, err := goga.Apply(defaults(), opts...) // defaults: instr = telemetry.For("mcp")
	...
	return &Server{
		srv:   sdkmcp.NewServer(&sdkmcp.Implementation{Name: s.Name(), Version: s.Version()}, s.serverOptions()),
		instr: s.instr,
		s:     s,
	}, nil
}

// ToolFunc is what a project writes: no SDK types, no telemetry, no timeout.
// In and Out are ordinary structs; the SDK derives their JSON schema.
type ToolFunc[In, Out any] func(ctx context.Context, in In) (Out, error)

// AddTool is a free generic function because Go methods cannot carry type
// parameters. It is the ONLY way to reach s.srv, which is what makes the
// telemetry below unavoidable — the owner's rule that every part of the
// framework has telemetry, applied to MCP.
func AddTool[In, Out any](s *Server, name, desc string, fn ToolFunc[In, Out], opts ...ToolOption) {
	sdkmcp.AddTool(s.srv, &sdkmcp.Tool{Name: name, Description: desc},
		func(ctx context.Context, req *sdkmcp.CallToolRequest, in In) (res *sdkmcp.CallToolResult, out Out, _ error) {
			// MCP defines no trace-context header, so goga's house convention is
			// traceparent in the request _meta; extract it if the caller sent one.
			ctx = extractTraceContext(ctx, req.Params.Meta)
			ctx, end := s.instr.Start(ctx, "tool",
				semconv.MCPToolName(name), semconv.MCPSessionID(req.Session.ID()))

			ctx, cancel := context.WithTimeout(ctx, s.s.ToolTimeout())
			defer cancel()

			// The wrapper is the only place a panicking tool can be contained
			// once for every project. Without it, one tool's nil dereference
			// takes down a server serving every other tool, leaves its span
			// open and its timeout context leaked. Deferred, so the span ends
			// on the panic path too.
			var err error
			defer func() {
				if p := recover(); p != nil {
					err = fmt.Errorf("goga/mcp: tool %q panicked: %v", name, p)
					s.instr.Logger().ErrorContext(ctx, "tool panicked",
						"tool", name, "panic", p, "stack", string(debug.Stack()))
					res, out = errorResult[Out](err)
				}
				end(err)
			}()

			out, err = fn(ctx, in)
			if err != nil {
				// MCP reports tool failures in-band, not as protocol errors.
				res, out = errorResult[Out](err)
			}
			return res, out, nil
		})
}

func errorResult[Out any](err error) (*sdkmcp.CallToolResult, Out) {
	var zero Out
	return &sdkmcp.CallToolResult{
		IsError: true,
		Content: []sdkmcp.Content{&sdkmcp.TextContent{Text: err.Error()}},
	}, zero
}

type ResourceFunc func(ctx context.Context, uri string) ([]byte, string, error)
type PromptFunc[In any] func(ctx context.Context, in In) ([]sdkmcp.PromptMessage, error)

// Both are instrumented by the same wrapping as AddTool — resource reads and
// prompt renders are operations too.
func AddResource(s *Server, uri, name string, fn ResourceFunc, opts ...ResourceOption)
func AddPrompt[In any](s *Server, name, desc string, fn PromptFunc[In], opts ...PromptOption)

// Run serves over the configured transport until ctx is cancelled. Like
// serve.Server.Run it installs no signal handling of its own — cli.App.Run owns
// that, which is what lets one process serve HTTP and MCP and stop once (D15).
func (s *Server) Run(ctx context.Context) error

// Handler lets an MCP server be mounted on a goga/serve Server, which is how a
// service exposes HTTP and MCP on one port — the sysgo case.
func (s *Server) Handler() http.Handler

func (s *Server) SDK() *sdkmcp.Server // escape hatch

// Client is the consumer side, instrumented symmetrically: a span per call, with
// traceparent injected into _meta.
type Client struct {
	c     *sdkmcp.Client
	instr *telemetry.Instrumentation
}

func Connect(ctx context.Context, opts ...ClientOption) (*Client, error)
func (c *Client) CallTool(ctx context.Context, name string, args any) (*sdkmcp.CallToolResult, error)

var Set = wire.NewSet(New)
```

Adoption note, answering the review: **gopgql adopts this.** It already imports
`modelcontextprotocol/go-sdk v1.6.1` and hand-rolls `mcp/server.go`,
`mcp/query.go` and `mcp/introspection.go`. Porting them to `goga/mcp` gives its
tools telemetry they do not have today and is the migration that proves the
module.

### `goga/grpc` — the buf runtime seam (D11)

```go
package grpc

type settings struct{ /* unexported, unnameable outside this package (D5) */ }
type Option = goga.Option[settings]

func WithAddr(addr string) Option
func WithReflection(on bool) Option        // on by default; grpcurl against any service
func WithHealthService(on bool) Option
func WithUnaryInterceptors(is ...grpc.UnaryServerInterceptor) Option
func WithMaxRecvMsgSize(n int) Option

type Server struct {
	srv   *grpc.Server
	instr *telemetry.Instrumentation
}

// New installs otelgrpc's stats handler, so buf-generated services get the same
// treatment HTTP gets and no service can register without it.
func New(opts ...Option) (*Server, error)

// Register takes the generated ServiceRegistrar closure, so the buf output is
// untouched.
func (s *Server) Register(fn func(grpc.ServiceRegistrar))

// Run serves until ctx is cancelled, then GracefulStop within the grace period.
// No signal handling here either (D15).
func (s *Server) Run(ctx context.Context) error
func (s *Server) GRPC() *grpc.Server

// NewClient, not Dial: grpc.Dial is deprecated upstream, and a house wrapper
// that ships the deprecated call teaches it to every project that adopts it.
func NewClient(target string, opts ...DialOption) (*grpc.ClientConn, error)

var Set = wire.NewSet(New)
```

### `goga/components` — Service Weaver behind a deployer table (D12)

```go
package components

// Component is the unit of deployment. The interface is goga's, so Service
// Weaver is one implementation of the deployer and not the shape of the API —
// which is what makes its archived upstream survivable.
type Component interface {
	Init(ctx context.Context) error
	Shutdown(ctx context.Context) error
}

// Ref is a typed reference resolved by the deployer. Under the "local" deployer
// it is a direct call; under "weaver" it may cross a process boundary.
//
// T must be an INTERFACE, and the local deployer enforces it at registration
// rather than leaving it to be discovered under the distributed one: a
// distributing deployer hands back a generated stub, never the concrete struct
// the local deployer stored, so a Ref[*myComponent] is a reference that works in
// tests and fails in production. The type parameter is otherwise honest about
// what it buys — Deployer.Resolve returns Component, so Get is a checked
// assertion returning a typed error, not a compile-time guarantee. It saves the
// caller writing the assertion; it does not remove it.
type Ref[T Component] struct{ name string; d Deployer }

func (r Ref[T]) Get(ctx context.Context) (T, error)

// Deployer is the adapter interface. Adapters: local (default, in-process, what
// tests use), weaver (ServiceWeaver), k8s.
type Deployer interface {
	Register(name string, c Component) error
	Resolve(ctx context.Context, name string) (Component, error)
	Start(ctx context.Context) error
	Unwrap() any
}

// This module's own name-keyed deployer table (D8): "local", "weaver", "k8s".
// Settings is the accessor interface a deployer adapter reads.
type Settings interface {
	ConfigPath() string
}

type DeployerOpener interface {
	Open(ctx context.Context, s Settings) (Deployer, error)
}

func RegisterDeployer(name string, o DeployerOpener)
func DeployerNames() []string

type settings struct{ /* unexported, unnameable outside this package (D5) */ }
type Option = goga.Option[settings]

func WithDeployer(name string) Option // "local" (default) | "weaver" | "k8s"
func WithConfig(path string) Option   // weaver.toml for the weaver deployer

// Graph is the portable type; every cross-component call is a span, so a
// component graph is traceable regardless of which deployer is in use (D6).
type Graph struct {
	d     Deployer
	instr *telemetry.Instrumentation
}

func New(ctx context.Context, opts ...Option) (*Graph, error)
func Register[T Component](g *Graph, name string, c T) Ref[T]
func (g *Graph) Run(ctx context.Context) error
```

### `goga/gogatest`

```go
package gogatest

// Fixtures take testing.TB, not *testing.T, so a benchmark or a shared helper
// can use them.
type postgresSettings struct{ /* unexported, per D5 */ }
type PostgresOption = goga.Option[postgresSettings]

func WithMigrations(fsys fs.FS) PostgresOption
func WithSeed(fsys fs.FS) PostgresOption         // always after migrations, by construction
func WithSnapshotReset() PostgresOption          // gopgql's strategy
func WithTruncateReset(except ...string) PostgresOption
func WithImage(ref string) PostgresOption
func WithSharedNetwork(n *testcontainers.DockerNetwork) PostgresOption

// Postgres returns a ready portable *database.DB, migrated and seeded in that
// order regardless of file naming — go-service had to rename its init scripts
// 01-/02-/03- to force it; the fixture removes the hazard.
//
// Cleanup is registered on the container's own lifetime, not on the suite's *T:
// epos rejected testcontainers.CleanupContainer for exactly that reason (it
// fills the disk across a long run), and the fixture encodes epos's conclusion.
func Postgres(t testing.TB, opts ...PostgresOption) *database.DB

// Reset applies the declared reset strategy between tests.
func Reset(t testing.TB, db *database.DB)

// Container is the escape hatch for anything the fixture does not model.
func Container(db *database.DB) testcontainers.Container

// MCP wires an in-memory transport pair, so an MCP server is testable without a
// subprocess or a port.
func MCP(t testing.TB, s *mcp.Server, opts ...MCPOption) *mcp.Client

// Telemetry installs in-memory exporters and returns them, which is what makes
// D6 assertable: a test can require that an operation produced its span.
func Telemetry(t testing.TB, opts ...TelemetryOption) *RecordedTelemetry

func (r *RecordedTelemetry) Spans() []sdktrace.ReadOnlySpan
func (r *RecordedTelemetry) RequireSpan(t testing.TB, name string) sdktrace.ReadOnlySpan

type featureSettings struct{ /* unexported, per D5 */ }
type FeatureOption = goga.Option[featureSettings]

func WithFeaturePaths(paths ...string) FeatureOption
func WithTags(expr string) FeatureOption          // default excludes @wip
func WithScenarioReset(fn func(context.Context) error) FeatureOption
func WithSteps(fn func(*godog.ScenarioContext)) FeatureOption

// Features owns the godog bootstrap that is copy-pasted 5x in gopgql and 8x in
// epos: runner options, scenario reset, machine-readable reporting, and the
// supported way for a step to reach the test handle (both projects invented
// their own).
func Features(t testing.TB, opts ...FeatureOption)

// T returns the test handle from inside a step, replacing both projects'
// hand-rolled smuggling.
func T(ctx context.Context) testing.TB
```

### `goga/semconv` — generated attribute constants (D11)

Not hand-written. OTel Weaver reads a registry of YAML models and emits this
package; the surface below is what the generator produces and what
`Instrumentation` consumes, which is what makes string-literal attribute keys a
lint error rather than a habit.

```go
// Code generated by weaver. DO NOT EDIT.
package semconv

// Official conventions are re-exported, so callers have one import rather than
// two and cannot accidentally invent a key that already exists upstream.
const (
	ServiceNameKey    = otelsemconv.ServiceNameKey
	ErrorTypeKey      = otelsemconv.ErrorTypeKey
	DBQueryTextKey    = otelsemconv.DBQueryTextKey
	HTTPRequestMethodKey = otelsemconv.HTTPRequestMethodKey
)

// goga-specific attributes exist only where no official convention does.
func OperationName(v string) attribute.KeyValue     // goga.operation
func ModuleName(v string) attribute.KeyValue        // goga.module
func AdapterScheme(v string) attribute.KeyValue     // goga.adapter.scheme
func MigrationVersion(v int64) attribute.KeyValue   // goga.migration.version
func MigrationName(v string) attribute.KeyValue     // goga.migration.name
func MCPToolName(v string) attribute.KeyValue       // goga.mcp.tool.name
func MCPSessionID(v string) attribute.KeyValue      // goga.mcp.session.id
func ConfigSources(v []string) attribute.KeyValue   // goga.config.sources
func ComponentName(v string) attribute.KeyValue     // goga.component.name
```

### `goga/lint` — the enforcement analyzers (D5)

```go
package lint

// New is the entry point golangci-lint's plugin-module-register calls. The
// mechanism is already proven in-house: mcp-anything depends on
// golangci/plugin-module-register today.
func New(conf any) ([]*analysis.Analyzer, error) {
	return []*analysis.Analyzer{
		ParamStruct,  // gogaparamstruct: exported constructor whose last param is a struct
		Wire,         // gogawire: goga provider called outside a wireinject file
		Telemetry,    // gogatelemetry: a type embedding a goga driver interface directly
		Semconv,      // gogasemconv: attribute.String("k", v) where a generated constant exists
		Layout,       // gogalayout: pkg/ or internal/ in goga's own tree
	}, nil
}

var ParamStruct = &analysis.Analyzer{
	Name: "gogaparamstruct",
	// The predicate has to be this narrow or the rule is noise. "Final parameter
	// is a struct" fires on New(t *testing.T), on migrate.New(db *database.DB)
	// and on sqlcdb.New(db *database.DB) — none of which is a parameter struct.
	// A parameter struct is: the final NON-VARIADIC parameter, whose type is a
	// struct (or pointer to one) declared in the same package, with at least one
	// exported field, on a constructor that takes no variadic option parameter.
	Doc: "reports an exported constructor that takes a same-package settings struct instead of variadic options",
	Run: runParamStruct,
}
```

The import bans are `depguard` configuration in the shipped `.golangci.yml`
rather than analyzers, because `depguard` already does it well:

```yaml
linters-settings:
  depguard:
    rules:
      house:
        deny:
          - pkg: github.com/spf13/viper        # koanf is the house choice
            desc: use goga/config
          - pkg: github.com/google/wire        # archived; the fork is goforj/wire
            desc: use github.com/goforj/wire
          - pkg: github.com/golang-migrate/migrate
            desc: goose is the house migration engine — use goga/migrate
      pgx-only-in-goga:
        files: ["!**/goga/database/**"]
        deny:
          - pkg: github.com/jackc/pgx
            desc: reach pgx through goga/database
```

Import paths, not modules, deliberately: `spf13/viper` appears as an *indirect*
module via golangci-lint in `mcp-anything`, so a module-level ban would be wrong.

### `goga/app` — the composition root

Separate from the root `goga` package, which every module imports for `Option`
and `Apply`; the composition root imports every module, so the two cannot be one
package without an import cycle across the whole framework.

```go
package app

// App's fields are unexported and there is no exported constructor, so the only
// practical way to build one is a wire-generated injector over di.Service or
// di.MCP. That is the compile-time half of D9.
type App struct {
	cfg   any
	tel   *telemetry.Telemetry
	cli   *cli.App
	srv   *serve.Server
	mcp   *mcp.Server
	db    *database.DB
	mig   *migrate.Migrator
}

// Run migrates if a Migrator is present, then serves every surface that is
// present under one errgroup, and on cancellation shuts them down in reverse
// construction order: surfaces drain first, then the database closes, then
// telemetry flushes last so the shutdown itself is observable. Shutdown errors
// are joined, not first-wins.
//
// Run receives an already-signal-aware ctx from cli.App.Run, which is the only
// place goga installs a signal handler (D15) — that is what makes "every surface
// stops together" implementable rather than three surfaces racing.
//
// sysgo's main.go.tmpl collapses to a call to this (D3).
func Run(ctx context.Context, a *App) error
```

## Enforcement matrix (D5)

Every convention in the issue's list, and the mechanism that enforces it. There
is no "not enforced" column, by decision.

| Convention | Mechanism | Kind |
|---|---|---|
| Variadic options, no param structs | the settings struct is **unexported**, so no other package can name it; `Settings` is an accessor interface with no way to produce one goga accepts; every goga entry point takes `...Option`; `goga/lint` `gogaparamstruct` for project code | compile + lint |
| Every module with runtime operations has telemetry | portable types have unexported fields and no exported constructor; no module exports an adapter lookup, so there is no goga call returning a raw driver type; no `WithoutTelemetry`; `TestEveryModuleIsInstrumented` asserts the instrumented set is exactly the module list minus `{semconv, lint, di, registry, goga (root), app, gogatest}` | compile + test |
| Delivery is one package per milestone, gated on adoption | `tasks.md` is milestone-ordered and each milestone names its adopter; a milestone closes on a merged adoption PR, not on a green build | process (D16) |
| DI is wire | `app.App` fields unexported; `go generate` + `go-generate-check`; `goga/lint` `gogawire` | merge + lint |
| A streaming result outlives the call that returned it | `Rows` owns the cancel and the span; `Query` has no `defer cancel()` | compile (API shape) |
| One signal handler per process | only `cli.App.Run` calls `signal.NotifyContext`; `serve`/`mcp`/`grpc` `Run` take a ctx | compile (API shape) |
| wire is `goforj/wire`, not archived `google/wire` | `go.mod` `tool` directive in the template; `depguard` bans `github.com/google/wire` | merge + lint |
| koanf, never Viper | `goga/config` is the only config entry point; `depguard` bans the `spf13/viper` import path | lint |
| Config precedence is defaults→file→env→flags | fixed inside `config.Load`, not derived from option order | compile |
| Probes and `/metrics` are untraced | `serve.New` builds the ops mux outside `otelhttp`; no option can move them in | compile |
| pgx is reached through `goga/database` | `depguard` allows `jackc/pgx` only under `goga/database/*` | lint |
| goose is the migration engine | `goga/migrate` is the only migration entry point; `depguard` bans other engines | lint |
| Generated code is committed and current | `go-generate-check`: `go generate ./... && git diff --exit-code` | merge |
| Semantic conventions over invented attributes | `telemetry.Instrumentation` takes `attribute.KeyValue` from generated `goga/semconv`; `goga/lint` `gogasemconv` flags string-literal attribute keys | lint |
| testify, not hand-rolled `t.Errorf` | `.golangci.yml` template enables `testifylint` + `usetesting`; gopgql has 172 hand-rolled assertions to migrate | lint |
| gomock, not hand-rolled fakes | `mockgen` `tool` directive + `//go:generate`; freshness via `go-generate-check` | merge |
| One golangci-lint version and invocation | the `go-lint` composite action pins it; projects pin goga | merge |
| goga's own layout: flat, no `pkg/`/`internal/` | `goga/lint` `gogalayout` runs on goga itself | lint |

## Risks / Trade-offs

- **[Scope is the full tool list, which is a lot of surface]** — this is the
  owner's decision, and D16 is what manages it: one package per milestone, each
  gated on a named project adopting it. A module whose consumer is anticipated
  rather than current does not get a milestone slot until the consumer exists.
- **[Milestones stretch delivery, and that is the point]** — fourteen gated
  milestones is slower than one branch, and the owner has chosen it knowingly
  (*"I will carefully review it"*). The cost that is not obvious: a module adopted
  before its neighbours ships into a project without the rest of goga, so some
  invariants land later than the module that names them — signal handling is the
  worked example in D16. Each capability that spans milestones says so per
  requirement.
- **[Service Weaver's upstream is archived]** — mitigated by D12's deployer
  table, so replacing it is a driver swap. Still a live question: see below.
- **[A wrapper hides upstream and must track its churn]** — mitigated by D2's
  rule that every wrapper exposes its underlying object, so the escape hatch is
  one call away. The riskiest is `goga/database`, whose driver interface has to
  stay narrow enough to be cheap and wide enough that pgx's `CopyFrom` and
  `SendBatch` are reachable — hence `Unwrap()` and `sqlcdb`'s `DBTX`.
- **[Five adapter tables instead of one generic registry]** — the cost of D8.
  About thirty lines each of `map` + `RWMutex` + `Register` + lookup, and the
  duplicate-registration panic written five times. Accepted on the owner's
  instruction, and cheap at this size: the duplication is mechanical and visible,
  and it collapses into `goga/registry` the day Go ships generic methods. The
  risk worth watching is the five drifting — different panic messages, different
  unknown-adapter errors — which is why the error text and the panic condition
  are specified once in `goga-adapter-resolution` rather than per module.
- **[Two enforcement claims: one restored, one still bounded]** — the previous
  revision gave up both the claim that a parameter struct is unconstructible and
  the claim that an uninstrumented goga object is unreachable. **The first is
  restored** by D8: the settings struct is unexported again, so a caller cannot
  name it, and no goga entry point accepts one. The second is nearly restored —
  no module exports an adapter lookup any more, so goga hands back no raw driver
  type — but it stays bounded rather than absolute, because a project that
  registers its own adapter can call the opener it wrote itself. That path is
  the project's own code, and `goga/lint`'s `gogatelemetry` reports it. Stated
  at its real strength, because a claim a reader can disprove in four lines of Go
  costs more than it buys.
- **[`goga/components` is the least evidenced module in the design]** — no
  current consumer, an archived upstream, and the largest invented surface
  (`Component`, `Ref[T]`, `Deployer`, `Graph`, three adapters). It is in scope on
  the owner's instruction and stays in scope, but under D16 it has **no milestone
  slot until a consumer exists**, because the owner's own gate is a real
  adoption. The constraint that `Ref[T]`'s `T` is an interface still stands, so
  the local deployer cannot certify a shape the distributed one will reject.
- **[Two span levels in the database module could double-count]** — the portable
  span is the logical operation and otelpgx's is the wire call. They nest, so
  latency is not double-counted, but the span count per query rises. Sampling
  configuration should be part of the `goga/telemetry` defaults.
- **[Adoption may simply not happen]** — goga does not migrate anything. Adoption
  is scheduled per project, per issue, and the compliance numbers re-measured.
- **[Yokai already does ~70% of the runtime half]** — 17 opt-in modules, project
  templates and workflows, MIT. Its stack is wrong on every axis the owner cares
  about (fx not wire, Viper not koanf, Echo not stdlib, no cobra, no wrapped test
  tooling), so it is not a substitute — but **its module decomposition should be
  read before finalising goga's package boundaries.**
- **[The unserved half is the valuable half]** — nobody ships wrapped test
  tooling or encapsulated CI invocation. That is also where the owner's own
  projects diverge most.

## Open Questions

Answered by the review, recorded here so the trail is legible:

- *Does the owner accept D4's narrowing?* **No** — D4 is reversed. gin, sqlc, buf
  and Service Weaver are in scope.
- *Which project adopts goga first?* **gopgql**, and it now adopts it one package
  at a time (D16). It is the only project with pgx, goose and the MCP SDK all
  three, all uninstrumented, plus the 5× duplicated godog bootstrap, so it is the
  named adopter for `telemetry`, `database`, `migrate`, `mcp` and `gogatest`.

- **Unconstructible settings versus the generic registry — closed by the owner.**
  This design previously put the question to the owner: the two were not jointly
  satisfiable in the shape chosen, and it recommended keeping an opaque exported
  `Settings` while noting that literal unconstructibility would cost the registry.
  **The owner chose to drop the registry** (D8), for an unrelated and better
  reason — Go has no generic methods yet. The consequence is recorded in D5:
  settings structs are unexported again, and the compile-time claim holds. The
  question is closed; nothing here is waiting on an answer.

- **Service Weaver's archived upstream — closed by D16.** The question was
  whether to build the `weaver` deployer in v1 against an archived dependency.
  Under the owner's milestone rule it does not arise: `goga/components` has no
  adopting project, so it has no milestone, and the deployer is written when a
  consumer for it exists. The interface is still designed (D12) so that whichever
  deployer arrives first is an adapter and not a rewrite.

Still open:

- **The default home for a service's own non-adapter code** — the surviving half
  of the layout contradiction (D13), now live in merged guidance on `main` rather
  than pending in workspace#31. The widened scope settles adapter organisation
  (ports adjacent to what they serve, technology-named adapter leaves, no layer
  directories) and settles that sysgo's templates are the enforcement point. It
  does **not** settle whether a service's domain and use-case code sits in
  top-level packages, under `internal/`, or under `pkg/` — `go-project-scaffold`
  prescribes `internal/` plus `pkg/`, the spf13 `go` skill calls `internal/`-by-
  default an anti-pattern, and both are in force. goga cannot decide it (D1); the
  owner has to, and then sysgo enforces it. **Recommendation:** adopt the spf13
  position for services — top-level, concern-named, one level deep — because it is
  the side the framework's own adapter shape already lands on, and amend
  `go-project-scaffold` rather than the reverse.
- *Separately, and not the workspace's to fix:* `skill-test`'s `AGENTS.md`
  contradicts itself, asking for consumer-side ports while prescribing a
  centralised `internal/port` (D13).
