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

### What this revision reversed, and on what evidence

Five positions in this document changed in this round. They are collected here
because a reviewer should not have to reconstruct them from fourteen decision
sections, and because three of them reverse something the owner has already been
shown.

| # | Was | Is now | Evidence |
|---|---|---|---|
| D7 | `goga/database/driver.DB`, a six-method port, with `pgxdb` and `sqldb` behind it | **No port.** `goga/database` returns an otelsql-wrapped `*sql.DB`; `goga/database/pgxdb` returns an instrumented `*pgxpool.Pool` | `gocloud.dev` builds driver ports for blobs, queues, documents, secrets and config, and **declined to build one for SQL** — `postgres/postgres.go` returns `*sql.DB` and instruments by wrapping the sql driver |
| D8 | Registry deferred out of v1 *because Go had no generic methods*; then restored *because Go 1.27 has them* | **Registry in v1, as generic methods on `*Registry`, on the Go 1.27 floor.** Name-keyed, typed constructor, `r.Open[P](ctx, name, raw)` | The owner decided D8-A on 2026-08-04. The method form compiles on `go1.27rc2` with both type parameters still inferred from the constructor; `go.mod` is `go 1.27` + `toolchain go1.27rc2` |
| D8 | Adapters keyed by URL scheme, after `blob.URLMux` | **Keyed by plain adapter name.** URL/DSN retained only as *content* for `database` and `client` | URL openers solve twelve-factor late binding; goga picks adapters at build time in the composition root. `s3blob.go:150-219` is what the URL key degenerates into |
| D14 | "No exported struct anywhere in goga's option surface" | **Unexported caller-facing settings; exported driver-facing option structs.** Two sides of the port, two rules | The conformance suite (D21) lives in a third package and must construct them; go-cloud exports all of `driver.ReaderOptions`, `WriterOptions`, `ListOptions` |
| D8 | Registry ownership left ambiguous — the normative code was a value, the prose said "adapter tables are package-level `var`s" | **An injected value; no package-level default.** Adapters attach via `Provide(r)`; blank imports are gone | go-cloud calls its global mux *"the single sanctioned exception"* to minimize-global-state and justifies it by needing to work **without** wire (`internal/docs/design.md:108-121`). goga mandates wire (D9), so the justification does not transfer |
| D8 | Constructor shape fixed at `func(S) (P, error)`, with ctx *"taken at Open time"* — a mechanism that did not exist | **`func(context.Context, S) (P, error)`**, and ctx threaded through both `Open`s | The first spike's "works *because* the shape is `func(S)…`" was too strong: inference is unaffected by a leading ctx, re-tested. Construction is I/O in every adapter-bearing module, and the superseded `DeployerOpener.Open(ctx, …)` already had one |
| D22 | `goga/serve` exposes a `Router` port — `Handle(method, pattern, h)`, `Use(mw)`, framework-owned pattern syntax translated per adapter | **The port is `http.Handler`.** gin, chi and mux are handlers and need no goga adapter; the adapter seam is the *listener* | The previous revision's own text: gin applies middleware only to later routes, chi panics, stdlib applies it to everything — three behaviours the port had to paper over before a handler existed |

Two of these change what the owner was previously shown in a way he may want to
push back on, and neither is buried: **D7** removes a database abstraction he
asked for by name, and **D22** narrows a router seam the survey called its
strongest evidence. Both sections argue the change in full and state what is
lost. A third, **D8-A**, was put to the owner rather than taken unilaterally, and
he answered it on 2026-08-04: **Go 1.27, generic methods.** It is no longer an
open question — see D8 and D17, which are now written that way.


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
`goga/registry`, a fifteenth — the shared adapter registry, restored to v1 (D8)
for a better reason than the one it was dropped for: it never needed generic
methods. It is very nearly a leaf — the standard library, `reflect`, and the root
`goga` package alone, the last only so that `registry.Option` can be an alias of
`goga.Option` rather than a second, incompatible declaration (D8). Root `goga` is
itself a leaf, so no cycle is possible and every module can use it.

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
(`Config.K`, `Migrator.Provider()`, `mcp.Server.SDK()`). This is the cheap
mitigation for a wrapper leaking the moment a project needs something
unanticipated. It is an *escape hatch*, not an unenforced convention — see D5.

**This is a different hatch from D20's `As`, and the two do not compete.** A
named accessor answers *"give me the tool this wraps"*, where there is exactly
one and its type is known at compile time — `Config.K` is always a
`*koanf.Koanf`. `As` answers *"which adapter is behind this port, and can I have
it as its own type"*, where the answer varies by adapter and is only knowable at
run time. Modules with a port use `As` (`serve.Server`); modules that wrap a
single tool use a named accessor. `goga/serve` therefore has `As` and no
`HTTP()`, which is a change from the previous revision, where the router seam
D22 removed had made it a single-tool wrapper.

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
| **gin** | `goga/serve` (passed to `New` as an `http.Handler`; no goga adapter — D22) | **sysgo**; skill-test | **current + anticipated** (owner) |
| chi | `goga/serve`, same | mcp-anything | current |
| stdlib mux | `goga/serve`, same | go-service | current (default) |
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
     the adapter implements — `serve/driver.Options` beside `serve/driver.Server`,
     `mcp.Settings` beside `mcp.Transport` — which is a package the adapter
     already imports, and which is why those types are **exported** while the
     module's own settings struct is not (D14). **Whether:** a module's opener
     takes one **only if an adapter reads one.**
     `goga/mcp` does (the HTTP transport needs its endpoint); `goga/components`
     does (the deployer's config path). `goga/serve` and `goga/telemetry` do
     **not** — a listener adapter wraps a server and a trace exporter delegates
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
     open a hole here, because what it stores is a constructor for an *adapter*
     — a `driver.Server`, an `mcp.Transport` — and never a portable type; the
     portable type is built by the module's own `New`, which attaches
     instrumentation on the way through. A project can register its own adapter,
     and what it gets back is still the portable type. What remains is a project
     calling a constructor it wrote itself and never handing it to goga, which is
     its own code rather than a goga entry point, and which `goga/lint`'s
     `gogatelemetry` reports.
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

**And this is the *mechanism* by which "no opt-out" is a type-system guarantee
rather than a review rule** — which is the part the previous revision asserted
but did not explain. Three details from go-cloud make it structural, and goga
adopts all three:

- **The instrumentation package is `internal`.** `gocloud.dev/internal/otel` is
  not importable by a driver package, so an adapter *cannot* reach the tracer
  even if its author wanted to. goga's instrumentation core is likewise internal;
  `goga/telemetry` exports only what a *consumer* configures (`Setup`, the
  exported views), never the per-operation instruments.
- **The provider label is derived by reflection, so an adapter cannot forget
  it.** `internal/otel/trace.go:55` is `ProviderName(driver any) string`, which
  returns `reflect.TypeOf(driver).Elem().PkgPath()` — e.g.
  `"gocloud.dev/blob/s3blob"`. A new adapter is labelled correctly the moment it
  exists: nothing to register, no constant to declare, no field to forget. goga
  does the same, so `goga.mcp.resolve` carries the adapter's package path
  without `httptransport` containing a single telemetry line.
- **The error taxonomy and the metric label are the same value.**
  `Tracer.End(ctx, span, err)` (`internal/otel/trace.go:95`) sets the span status,
  records the error, *and* records the latency histogram keyed on
  `gcerrors.Code(err)`. An adapter that classifies its errors correctly gets
  correct metrics for free, and there is no second place to keep in sync.

Put together: an application can only obtain the portable type; the portable
type's only constructor instruments it; therefore an adapter has no way to hand
the application an uninstrumented object, because it has no way to produce the
portable type at all. That is stronger than "every module must have telemetry" as
a documented rule, and it costs nothing.

**The corollary is a hard constraint on `goga/telemetry`'s own dependencies: it
may import OpenTelemetry and the standard library, and nothing else.** This is
not hygiene, it is load-bearing, and go-cloud is the cautionary evidence. Its
shared error package pulls **gRPC** into every consumer — `go mod why` traces
`google.golang.org/grpc` ← `gocloud.dev/internal/gcerr` ← `grpc/codes`, for a
single `GRPCCode` switch — and its retry helper pulls in
`github.com/googleapis/gax-go/v2` the same way. A telemetry package that every
goga module imports is the single worst place in the design to acquire a
dependency, because the moment it imports something a project does not want,
"no opt-out" becomes "no adoption". See D19.

Concretely, per module: a span per operation named `goga.<module>.<op>`, a
`goga.<module>.duration` histogram, an `error.type` attribute from the official
conventions on failure, and a module-scoped `*slog.Logger`. `goga/mcp` is
included — it gets a span per tool call, per resource read and per prompt render
(see the pseudocode). **Adapter resolution is an operation too**: each module
that has adapters emits `goga.<module>.resolve` when it selects one, because
"which adapter did this process actually resolve" is an operational question. The
span belongs to the **module**, not to `goga/registry` (D8): the shared registry
is a leaf that imports only the standard library, and giving it an
`Instrumentation` would create the `registry` → `telemetry` → `registry` import
cycle the Go review found in an earlier revision. Each module emits the span from
its own opener, where its `Instrumentation` already is.

**`telemetry.For` must resolve through OTel's global delegating providers**
(`otel.Tracer`, `otel.Meter`, `global.Logger`), never by snapshotting a concrete
provider, and its instruments are created on the handle's first use. This is
load-bearing rather than an implementation note, and the reason survives the move
to an injected registry (D8) even though the original wording did not. Modules
obtain their `Instrumentation` handle when they are **constructed**, and a
composition root routinely constructs some of them — a registry, an adapter, a
config loader — **before** `Setup` installs the real providers. A handle that
snapshotted a no-op provider at construction would leave exactly those code paths
permanently unobserved while every test passed. OTel's global providers are
designed to delegate once the real provider is installed; goga depends on that.
*(The previous revision justified this by adapter tables being package-level
`var`s populated from `init()`. That premise is gone with the global registry;
the conclusion is unchanged and now rests on construction order instead.)*

### D7: the portable-type/driver split, and why `goga/database` is the one module that does not get it

The owner asked for pgx inside a database module with multiple adapters, and
pointed at go-cloud. go-cloud was then read properly, at commit `35f55f24`
(2026-08-04). The study confirmed the pattern this design already had — and
reversed the database module, which is the one place go-cloud does the opposite
of what this spec assumed.

**The pattern, from `gocloud.dev/blob/blob.go` at HEAD.**

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

goga adopts the first, second and fourth for every module that has a genuine
second implementation. It **diverges on the third**: one shared registry rather
than a table per module, an injected value rather than a package-level default,
adapters attached by an explicit `Provide(r)` rather than self-registration from
`init()`, and a plain name rather than a URL scheme (D8). The
duplicate-registration panic is kept as-is. Below, the database module diverges
further still.

Two further rules come out of the same reading and were not in this design
before, both load-bearing:

- **Cross-cutting behaviour belongs to the portable type, and the driver
  interface is made as narrow as it can be.** `blob.Bucket.NewWriter` sniffs the
  content type and the driver only ever sees `NewTypedWriter(ctx, key,
  contentType string, …)`. `pubsub` keeps retry *and* batching in the portable
  type — `retry.Call(ctx, gax.Backoff{}, dt.IsRetryable, …)` at
  `pubsub/pubsub.go:331` — and the driver contributes the single predicate
  `IsRetryable(err) bool`, whose doc says outright *"this method should not retry
  … The concrete API takes care of retry logic."* Every goga port is held to
  this: if two adapters would both have to implement it, it belongs upstairs.
- **Driver interfaces evolve by additive option-struct fields and by new
  *optional* interfaces — never by adding a method.** go-cloud's own statement
  (`internal/docs/design.md:92`), and its instances are `driver.Downloader`,
  `driver.Uploader` and `server/driver.TLSServer`, each type-asserted only in the
  portable layer (`blob/blob.go:264`, `:527`, `server/server.go:154`). This is
  the mechanism behind D22's stability promise.

**Now the reversal. `goga/database` does not get a port.**

The previous revision specified `goga/database/driver.DB` — a six-method port
with `pgxdb` and `sqldb` behind it — and defended it against the obvious
objection by adding `sqldb`, a hundred-line adapter whose stated purpose was *"the
only way to find out whether `driver.DB` is actually portable."* An adapter that
exists to validate an abstraction is the abstraction asking to be questioned.

go-cloud answers it. It is an eight-year-old portability library that ships
driver-based ports for blobs, queues, documents, secrets and runtime config —
and it **declined to build one for SQL**. `postgres/postgres.go` and
`mysql/mysql.go` return `*sql.DB` directly. There is no `driver.DB` anywhere in
the repository. Instrumentation is achieved by wrapping the *sql driver*, not by
wrapping the API: `postgres/postgres.go:60` is
`otelsql.WrapDriver(&pq.Driver{}, c.traceOpts...)`. The only port is
`database/sql`, which is already written, already documented, and already
conformance-tested by the standard library.

The reason is the same one that makes the port attractive and then hollow: pgx's
value over `database/sql` **is** the part a common interface erases — `CopyFrom`,
`SendBatch`, `LISTEN/NOTIFY`, native types, scanning without a `driver.Value`
round-trip. A port that spans pgx and `database/sql` either drops those or routes
them through an escape hatch, and gopgql is named in this document as needing
exactly them. The previous revision's own `driver.DB` conceded the point twice in
its own signature, with `SQLDB() (*sql.DB, error)` and `Unwrap() any`.

So v1 ships **two honest types instead of one lossy union**:

- `goga/database` — a thin opener returning an **otelsql-wrapped `*sql.DB`**, for
  everything that wants the standard interface, and for goose (D10), sqlc and
  every tool that already speaks it.
- `goga/database/pgxdb` — a separate package returning an **instrumented
  `*pgxpool.Pool`**, using `github.com/exaring/otelpgx`, already the house choice
  in `mcp-anything`. Full pgx surface, nothing erased, nothing to unwrap.

Both are instrumented at construction. **But D6's guarantee is genuinely weaker
here than elsewhere, and that has to be said rather than glossed.**

Everywhere else in goga the invariant is enforced by the type system: an
application can only obtain the portable type, and the portable type's only
constructor instruments it, so an uninstrumented one cannot exist. `*sql.DB` and
`*pgxpool.Pool` are not goga's types. The handles this module returns *are*
instrumented — otelsql wraps the driver, otelpgx the pool — but **holding a
`*sql.DB` no longer proves that**, because any caller can `sql.Open` and get the
identical type with no instrumentation at all. For this one module the
enforcement drops from **compile-time to lint-time**: `depguard` confines
`database/sql` and `jackc/pgx` imports to `goga/database` and
`goga/database/pgxdb`, and a project that goes around them is reported rather
than prevented. The enforcement matrix records this row as `lint`, and it is the
only runtime module where it is not `compile`.

That is the price of D7, and it is the right price: the alternative is a port
that erases `CopyFrom`, `SendBatch` and `LISTEN/NOTIFY` — the capabilities gopgql
is named in this document as needing — in exchange for a guarantee about a type
nobody would then want to hold. go-cloud makes the identical trade for the
identical reason.

One consequence to note: `database.Tx` takes a `*sql.DB` and will accept an
uninstrumented one handed to it. It cannot tell the difference, and it does not
try to; the depguard rule is what keeps one from existing.

What also disappears is the pretence that a project can swap one for the other
without noticing.
`goga/database` therefore has **no adapter table at all** — which also removes
the design's only URL-scheme-keyed table and leaves the registry uniformly
name-keyed (D8).

- *Rejected — keeping `driver.DB` with `sqldb` as the second adapter.* Held for
  three revisions; reversed here. The evidence is that the one library this
  design is modelled on, having built five such ports, did not build this one.
- *Rejected — pgx only, no `database/sql` path.* goose needs `*sql.DB` (D10) and
  sqlc's generated code takes a `DBTX`. Both paths are real; the error was
  merging them.

### D8: `goga/registry` is in v1, name-keyed, and ships as generic methods on Go 1.27

**Reversed twice before this revision, and refined again here.** The history
matters because the spec has argued every side of it.

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

**Two spikes have now been run against `go1.27rc2`**, plus a reading of go-cloud's
registry at `35f55f24`. Everything below is a compiler result or a cited file, not
a reading of release notes.

#### The shape v1 ships

`Register`, `Open`, `Provide` and `Names` are **generic methods on `*Registry`**,
per the owner's decision on D8-A. The toolchain floor that buys this is `go 1.27`
plus `toolchain go1.27rc2` (D17).

```go
package registry

// Registry maps an adapter NAME to a constructor. Not a URL scheme: see below.
type Registry struct{ m map[string]entry }

type entry struct {
	open     func(context.Context, Settings, func(any) error) (any, error)
	settings reflect.Type
	port     reflect.Type
}

// Settings is the raw config subtree for one adapter (koanf's node, in goga).
type Settings map[string]any

// Option is generic over the ADAPTER's settings type, so an option for one
// adapter cannot be passed to another. It is a generic type ALIAS of the root
// package's Option, NOT a second declaration — two identical declarations would
// be distinct types and an adapter's option would then be unusable with
// goga.Apply. This is why registry imports the root goga package.
//
// Its own language gate is go1.23, measured — at `go 1.22` the compiler says
// "generic type alias requires go1.23 or later". It is far below the floor the
// module actually sets, which is 1.27 and is set by the generic methods below;
// see D17.
type Option[S any] = goga.Option[S]

// Register records a constructor. BOTH type parameters are inferred from ctor —
// the caller never writes either, and the method form does not change that:
// `r.Register("pgx", newPool)` needs no explicit instantiation. S is baked into
// the closure and recorded with reflect.TypeFor[S](), which is what lets S stay
// UNEXPORTED in the adapter's own package. Verified on go1.27rc2: inference is
// unaffected either by the leading context or by the receiver.
func (r *Registry) Register[P any, S any](name string, ctor func(context.Context, S) (P, error)) error

// Open is the CONFIG-DRIVEN path. The caller names only the port; the adapter is
// chosen by a runtime string, so P is result-only and must be instantiated
// explicitly. The settings blob is decoded into the adapter's own S inside.
func (r *Registry) Open[P any](ctx context.Context, name string, raw Settings) (P, error)

// Adapter[P,S] is the TYPED HANDLE returned by registration. It is what keeps
// variadic options statically checked on the path that does not need a string.
type Adapter[P any, S any] struct{ /* name, reg */ }

func (r *Registry) Provide[P any, S any](name string, ctor func(context.Context, S) (P, error)) (Adapter[P, S], error)

// Both P and S are static here: there is nothing to instantiate at the call
// site, and a foreign adapter's option is a COMPILE error. This method is
// UNCHANGED by D8-A — Adapter's type parameters belong to the type, not to the
// method, so it was already a method in the package-level-function form.
func (a Adapter[P, S]) Open(ctx context.Context, raw Settings, opts ...Option[S]) (P, error)
```

An adapter package, whose settings type is unexported and never named outside it:

```go
package pgxdb

type settings struct {
	DSN      string `koanf:"dsn"`
	MaxConns int    `koanf:"max_conns"`
}

func newPool(ctx context.Context, s settings) (*pgxpool.Pool, error) { … }

func WithMaxConns(n int) registry.Option[settings] {
	return func(s *settings) error { … }
}

// Every adapter package exports this alias, so a wire provider downstream can
// NAME the handle without `settings` being exported. See the worked
// httptransport example in Package surfaces for why it is not optional.
type Adapter = registry.Adapter[*pgxpool.Pool, settings]

func Provide(r *registry.Registry) (Adapter, error) {
	return r.Provide("pgx", newPool)
}
```

and the two call sites:

```go
pool, err := r.Open[*pgxpool.Pool](ctx, "pgx", cfg.Sub("database"))       // config-driven
pool, err := pgx.Open(ctx, cfg.Sub("database"), pgxdb.WithMaxConns(32))   // typed handle
```

**Why `any` is the right constraint here, stated once so it is not re-flagged.**
The house `go` skill warns against generic base types and against `any` as a
constraint meaning *"I don't know the type yet"*. `Registry` and `Adapter[P, S]`
are neither. This is one algorithm — decode a settings node, apply options,
construct — applied to many unrelated concrete types, which is the sanctioned use
of generics; `P` and `S` are unconstrained because there is genuinely no
operation the registry performs *on* them beyond storing and returning them, and
any narrower constraint would be a lie. The type safety is bought at the two ends
instead: `Register` takes a typed constructor, and `Adapter[P, S]` keeps both
parameters static at the call site.

#### The decoder is injected, because the registry cannot choose it

**Found by the audit; neither the review nor the revision caught it.** The
registry decodes a raw configuration node into the adapter's settings type. This
document also constrains `goga/registry` to the standard library. Those two
requirements are in direct conflict, and the conflict is silent:

- the only struct-tag decoder in the standard library is `encoding/json`;
- **every adapter settings struct in this document is tagged `koanf:`**, because
  koanf is the house configuration library (D-config).

Decoding `{"endpoint": "...", "idle_timeout": 5}` into a struct tagged
`koanf:"idle_timeout"` with `encoding/json` yields `IdleTimeout == 0`, **with no
error**. `Endpoint` survives only by `encoding/json`'s case-insensitive fallback.
A configured adapter would come up misconfigured, silently, with no diagnostic —
measured, not reasoned:

```
decoded: Endpoint="http://x" IdleTimeout=0  (err=nil)
```

The fix is to stop having the registry choose:

```go
// Decode is supplied by the caller; goga/config provides the koanf-backed one.
type Decode func(raw Settings, dst any) error

func New(decode Decode) *Registry   // panics if decode is nil
```

The registry stays dependency-light, the seam becomes explicit instead of
smuggled, and a decoder that rejects unknown keys — rather than dropping them —
becomes a property `goga/config` can offer and the conformance tests can assert.

#### What the spike settled, including one thing that cannot be done

- **The registry works, across real package boundaries.** No assertion at the
  call site, adapters in their own packages, selected by name.
- **Adapter configuration works without the caller ever naming the settings
  type** — the owner's second comment. `Register[P, S]` infers `S` from the
  constructor, decodes the raw config node into it, applies the caller's options
  on top, then calls the constructor. Precedence is **config first, options
  second**, because options are the explicit and more specific form.
- **What is impossible: recovering `S` into a type parameter at the `Open` call
  site**, because the adapter is chosen by a runtime string and a type parameter
  is a compile-time thing. The owner's literal `OpenWith[P, S](name, settings S)`
  *compiles*, but it is strictly worse: `S` is then asserted by the caller,
  unchecked against `name`, and wrong only at run time. It is not specified.
- **Variadic options survive on the typed path**, which answers the owner's third
  comment — see D14. Struct params are needed only on the dynamic string-keyed
  path, which already takes a settings blob by construction. **So the answer is
  both, split by path**, and the permission the owner granted is not needed.
- **An interface cannot declare a generic method** (*"interface method must have
  no type parameters"*), and a generic method cannot satisfy a non-generic
  interface method (*"impl does not implement Port (wrong type for method Do) —
  have Do[T any](context.Context) error, want Do(context.Context) error"*).
  **Ports therefore stay ordinary interfaces**, and per-call generics live on
  concrete types only. This is a hard constraint on the whole design and every
  port in this document has been checked against it. **Go 1.27 does not relax
  it** — re-measured on `go1.27rc2` after the D8-A decision, with the same two
  errors. This is the boundary of what generic methods buy: `*Registry` is a
  concrete type, so its methods may carry type parameters; no port may.
- **`reflect.TypeFor[P]()` in error messages, never `%T` on a zero value** — `%T`
  on a nil interface prints `<nil>`, which is the least useful thing an
  unknown-adapter error could say.
- **The fixed constructor signature is `func(context.Context, S) (P, error)`,
  and goga holds it.** The first spike reported that `Register` worked *because*
  the shape was `func(S) (P, error)`; that was too strong, and it was re-tested
  for this revision. Type inference is unaffected by a leading
  `context.Context` — `r.Provide("http", newTransport)` still needs no explicit
  instantiation, and a foreign adapter's option is still a compile error; both
  re-verified on `go1.27rc2` in the method form. The context is not ceremonial:
  an OTLP exporter dials, an MCP HTTP or
  SSE transport binds, and a listener opens a socket, all at construction. The
  alternative — keeping `func(S) (P, error)` and passing ctx "through the
  closure" — cannot work, because the constructor then has no parameter to
  receive it; the only escapes are a `context.Context` field inside the settings
  struct or a package-level one, and both are rejected.

#### Why the key is a name and not a URL scheme

The previous revision keyed `goga/database` and `goga/client` on the URL scheme,
following `blob.URLMux`. The go-cloud study says that indirection is solving a
problem goga does not have.

`blob.OpenBucket(ctx, "s3://bucket")` exists to serve the twelve-factor
backing-services principle (`internal/docs/design.md:230`): *the same binary*
points at S3 in production and a local directory in development, decided by an
environment variable read at startup. goga's adapters are chosen **at build time
by the composition root** — that is what "a project not using gin does not
compile gin in" means. Encoding a compile-time fact as a runtime string costs:

- compile-time checking of adapter config. `blob/s3blob/s3blob.go:150-219` is
  seventy lines parsing `ssetype`, `kmskeyid`, `accelerate`, `use_path_style`,
  `s3ForcePathStyle` (a legacy alias) and `disable_https` out of a query string
  with hand-rolled `strconv.ParseBool` and one bespoke error message each;
- the ability to pass a live object. A `*gin.Engine`, a `*pgxpool.Pool` or an
  `slog.Handler` cannot go in a URL, which is why go-cloud needs `URLOpener`
  struct fields *in addition to* the URL (`internal/docs/design.md:303-312`) —
  two configuration paths for one adapter;
- discoverability: `no driver registered for "s3"` is a runtime error whose fix
  is remembering a blank import.

So the registry key is a plain adapter name — `"gin"`, `"pgx"`, `"stdio"`,
`"local"`. **URL and DSN parsing is retained only where the URL is genuinely the
configuration the user already has**: `goga/database`'s DSN and `goga/client`'s
base URL. In both, the URL is *content* handed to one known adapter, never the
thing that selects it. Note that go-cloud's own `postgres` package does exactly
this — `postgres.go:47` passes the URL straight through as a DSN.

With D7 removing `goga/database`'s table entirely, every remaining table is
name-keyed, and the URL-versus-name split that produced a real bug in an earlier
revision cannot recur because there is no longer a second key convention.

| module | adapters in scope |
|---|---|
| `goga/serve` | alternative *listeners* only — the stdlib `*http.Server` (default), h2c, unix socket. gin, chi and mux are `http.Handler`s and need no adapter (D22) |
| `goga/telemetry` | standard names via `autoexport`; house names additive |
| `goga/mcp` | `stdio` (default), `http`, `sse` |
| `goga/components` | `local` (default), `weaver`, `k8s` |

`goga/database` has no table (D7). `goga/client` has none: one transport, no
second candidate, and a one-entry table is the abstraction D7 warns about.

#### The registry is the mechanism *under* each module's surface, not a replacement for it

**Corrected here after an independent audit.** An earlier pass of this revision
rewrote `telemetry`, `mcp` and `components` to call the registry's `Provide` and
`Open` directly, deleting their own typed registration surfaces. That
went too far in the other direction, and the audit was right that the
module-owned surfaces were the better of the two: they take a `context.Context`,
and they take a module-owned `Settings` accessor interface rather than an
untyped `map[string]any`.

So both survive, at different levels:

- **Each adapter-bearing module keeps its own typed surface** — its port, its
  `Settings` accessor interface, and a registration function named for what it
  registers (`mcp.RegisterTransport`, not a bare `r.Register`). This is
  what an adapter author and a composition root actually touch.
- **`goga/registry` is what those surfaces are implemented over** — one copy of
  the storage, the name→constructor mapping, the settings decode, the duplicate
  check, the port check and the diagnostics, rather than five copies.

That is the arrangement the owner asked for — a registry that maps ports to
adapters — without the contradiction the audit found, where `goga/mcp` specified
`TransportOpener` and D8's own worked example specified something incompatible
seven hundred lines earlier.

#### The registry is a value, not a global

**Decided here, because the previous revision's text pointed both ways.** There
is **no package-level default registry**. A registry is created by
`registry.New()`, adapters are attached to it by calling their `Provide(r)`, and
it reaches the modules that need it by injection — `WithExporterRegistry`,
`WithTransportRegistry`, `WithDeployerRegistry`.

The argument is go-cloud's own. Its `DefaultURLMux` is a global, and
`internal/docs/design.md:108-121` names it **the single sanctioned exception** to
"minimize global state", justified explicitly: *"We want the Go CDK to be usable
both with and without Wire. A global registry is acceptable as long as its use is
not mandatory."* **goga mandates wire (D9), so the justification does not
transfer.** A wire-provided `*Registry` is also what the owner described — a
structure that is held and passed.

Three consequences, all deliberate:

- **Blank imports are gone.** An adapter is selected by calling its `Provide(r)`
  in the composition root, not by importing it for its side effect. The
  dependency-pruning result in D19 is unaffected — a project that does not want
  gin still does not import it — and the failure mode improves, because a
  forgotten `Provide` is a visibly absent line rather than a missing underscore.
- **The unknown-adapter error changes its hint** from *"did you forget a blank
  import?"* to *"did you call `httptransport.Provide(r)`?"*.
- **Duplicate-registration detection is now per-registry** — and, for the same
  reason, a returned error rather than a panic (see `Register`'s doc below), so a
  test that builds its own registry cannot collide with another test's.

#### The registry is not the only way to bind a port, and often not the best one

go-cloud binds ports to adapters under wire with **no registry at all**:

```go
// server/server.go:39
var Set = wire.NewSet(New,
	wire.Struct(new(Options), "RequestLogger", "HealthChecks", …),
	wire.Value(&DefaultDriver{}),
	wire.Bind(new(driver.Server), new(*DefaultDriver)))   // port → adapter
```

and its own sample composition roots use the **constructor** form, never the URL
form: `samples/guestbook/inject_gcp.go:59` calls `gcsblob.OpenBucket(ctx, client,
flags.bucket, nil)` inside a `//go:build wireinject` injector.

Since goga *mandates* wire (D9), goga is nearly always in the constructor case.
The rule is therefore:

- **`wire.Bind(port, adapter)` is the default** when the adapter is known at
  build time — which is most of the time. It needs no registry and no name
  string at all.
- **The registry is for the config-driven case**: an adapter named in
  configuration, or a set of adapters a project wants to select among at startup
  without recompiling. `goga/telemetry`'s exporters are the clearest example.

Both exist because both cases are real. The registry is not the house default; it
is the escape from static binding when configuration has to choose.

#### "A structure that can cast interfaces (ports) into adapters"

The owner's phrase describes two different operations and they have different
answers, so it is worth separating them plainly:

- **Choosing an adapter for a port by name, returning it as the port.** That is
  `Open[P]` above. **Registration is checked by construction; retrieval had to be
  made so.** `Register` takes a typed constructor, so what goes *in* is correct —
  but the audit found that the stored entry recorded only the settings type, so
  `Open[P]` was a bare structural assertion that accepted any interface the
  adapter happened to satisfy. An adapter registered for `mcp.Transport` could be
  retrieved as an unrelated `Dialer` with the same method set, and it succeeded.
  The entry now records `reflect.TypeFor[P]()` as well, `Open` compares it, and
  the mismatch is a named error — a case this document previously specified
  nowhere:

  ```
  goga: adapter "http" was registered for mcp.Transport, not mcp.Dialer
  ```
- **Going from the port back down to the concrete adapter type** — a `*DB` in
  hand and pgx's `CopyFrom` wanted. That is a **downcast, and it is a runtime
  assertion by necessity, not by choice.** No amount of generics changes it: the
  value's dynamic type is not known to the compiler at that point. Generic
  methods do not help; they only move where the assertion is written.

go-cloud's name for the second operation is `As(i any) bool`, and goga adopts it
(D20). Calling it a cast does not make it static. Saying so plainly here is
cheaper than a reviewer discovering it in the first adapter.

#### D8-A: generic methods on Go 1.27 — decided by the owner

**This was the one question the design put to the owner rather than answering.
He answered it, and this section records the decision and the evidence that was
weighed to reach it.**

The owner instructed originally: use Go 1.27's generic methods for the registry,
RC or not. Two independent investigations found the feature was not what unlocked
the design, and the spec was written on a Go 1.24 floor with the trade-off put to
him explicitly. His answer, on the spec PR, 2026-08-04:

> *"I don't care, use 1.27. Build dependencies from source if necessary."*

**So the normative form is generic methods on `go 1.27`** (`toolchain
go1.27rc2`), and the from-source golangci-lint build is scheduled work rather
than a hypothetical cost. That is a reaffirmation after the concern was raised in
full, and it is settled; the rest of this section is the rationale on the record,
not an argument against it.

**What the decision buys.** `r.Open[DB](ctx, "pgx", cfg)` instead of
`registry.Open[DB](ctx, r, "pgx", cfg)`. A registry that is a value with methods
is the shape the owner described — *"a structure that can cast interfaces (ports)
into adapters"* — and the shape a wire-provided registry wants. 1.27 GA is close;
adopting at the RC avoids a second migration later, and the owner has accepted RC
risk in writing twice.

**What it costs, measured, so the trade is on the record.** The spike wrote the
normative registry twice: once with `Register`, `Open`, `Provide` and `Names` as
generic **methods** on `*Registry` (`go1.27rc2`), and once as package-level
generic **functions** (`go 1.22` language version). The two files differ in
exactly four lines:

```go
// Normative — Go 1.27 method form        // superseded package-level form
r.Register(name, ctor)                    registry.Register(r, name, ctor)
r.Provide(name, ctor)                     registry.Provide(r, name, ctor)
r.Open[DB](ctx, "pgx", cfg)               registry.Open[DB](ctx, r, "pgx", cfg)
r.Names()                                 registry.Names(r)
```

Everything else is byte-identical, **including `Adapter[P, S].Open` — the call
site users actually spend their time on.** `pgx.Open(ctx, cfg,
pgxdb.WithMaxConns(32))` is the same in both, because `Adapter`'s type parameters
belong to the type rather than to the method. Three consequences follow, and all
three were measured before the decision was taken:

- **The floor propagates.** Go's module rule means `go >= 1.27` reaches gopgql,
  epos, skill-test/go-service, mcp-anything and sysgo the moment any one of them
  adopts *any* goga package — including packages that never touch the registry.
  With the default `GOTOOLCHAIN=auto` a developer on 1.26.4 silently switches to
  the RC compiler; with `GOTOOLCHAIN=local` (hermetic CI, packaging, air-gapped
  builders) it is a hard failure. The API-conventions capability requires this to
  be *stated* in goga's docs and skill rather than discovered (13.6).
- **The linter is built from source, which is what the owner authorised.**
  `golangci-lint v2.7.2` as shipped refuses to run against a Go 1.27 target;
  rebuilt on `go1.27rc2` it still fails (*"export data version 4 is greater than
  maximum supported version 2"*) because it pins `golang.org/x/tools v0.39.0`.
  Only a rebuild against `x/tools v0.48.0` reports `0 issues`. D18 makes the
  linter non-negotiable per milestone, so `go-lint` builds golangci-lint from
  source with that bump for as long as the RC lasts — task 0.4d, reverted by 11.4
  when upstream ships a release on a new enough `x/tools`.
- **It buys call syntax, not capability.** The adapter configuration, the typed
  options and the port check are all the `Adapter[P, S]` half and were never
  gated on 1.27. That is the reason the earlier revision recommended against it;
  it is not a reason to revisit a decision the owner has made, and the goal the
  original instruction named — a registry that maps ports to adapters with the
  settings marshalled into the adapter's own type — is delivered either way.

**What did not change.** Generic methods are still forbidden on interfaces, and a
generic method still cannot satisfy an interface method, re-measured on
`go1.27rc2`. Ports stay ordinary interfaces; only concrete types — `*Registry`
here — carry per-call type parameters.

#### What this reverses

- **The previous revision deferred the registry out of v1 entirely**, on the
  grounds that Go had no generic methods. That reasoning is superseded twice
  over: the registry did not need them, and Go 1.27 has them and goga now
  requires it. It returns to v1 — but not in the `Table[P].Get[A any]` form the
  2026-07-31 round specified. `Get[A any]` was an unconstrained downcast that
  compiled for any `A` and failed at run time; it is replaced by `Open[P]`
  (checked by construction) plus `As` (D20, honestly a runtime assertion).
- **The package-level generic-function form is withdrawn** by the owner's answer
  to D8-A. It remains in this document only as the measured alternative that was
  weighed, never as a fallback the implementation may choose.
- **URL-scheme keys are withdrawn** for adapter selection (above).
- **The claim that the registry forces an exported settings struct stays
  withdrawn**, and is now proven twice: `S` is inferred from the constructor and
  never named by a caller.

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

// Data adds persistence. database.Set has no adapter to select (D7): the module
// returns an instrumented *sql.DB and pgxdb.Set returns an instrumented pool, so
// the choice is which provider set is in the graph, checked by the compiler.
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
  - oapi-codegen's generated server is an `http.Handler`, so it is passed
    straight to `serve.New` and runs on stdlib, gin or chi with no goga adapter
    in between (D22).

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
   the portable type it serves* (`goga/serve` + `goga/serve/driver`), and
   each adapter is its own leaf package named for its technology
   (`goga/database/pgxdb`, `goga/mcp/httptransport`). Repeated across the
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
package serve

// settings is UNEXPORTED, so no other package can name it, construct it or
// embed it. Option is an exported alias over it: a caller can hold and pass a
// serve.Option and cannot write the type it mutates. Every exported entry
// point in this package takes ...Option and none takes a settings, so
// goga.Apply over the caller's options is the only way a populated one exists.
type settings struct{ readHeaderTimeout time.Duration; shutdownGrace time.Duration /* … */ }

type Option = goga.Option[settings]

func WithReadHeaderTimeout(d time.Duration) Option {
	return func(s *settings) error {
		if d <= 0 {
			return fmt.Errorf("goga/serve: read header timeout must be > 0, got %s", d)
		}
		s.readHeaderTimeout = d
		return nil
	}
}

// What an ADAPTER receives is driver.Options — a different, exported type in the
// driver package, carrying only what an adapter can act on. serve copies the
// fields across at construction. The two do not alias and are allowed to
// diverge, which is gocloud.dev's rule (internal/docs/design.md:189-195):
// duplicate rather than embed, so each type's godoc addresses its own audience.
func (s *settings) driverOptions() driver.Options {
	return driver.Options{ReadHeaderTimeout: s.readHeaderTimeout /* … */}
}
```

**The house rule this establishes, once, for every module: a module's own
`settings` is always the unexported struct, and what crosses the port to an
adapter is a separate, exported, accessor-or-plain-data type that carries only
what an adapter can act on.** There is no exported struct anywhere in goga's
*caller-facing* option surface; the driver-facing side is exported by necessity,
and the table at the end of this decision says which is which.

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

It is allowed, and both spikes compile it. Each adapter's option **is** a
function with its own type — `registry.Option[S]` for that adapter's own settings
type — and the typed handle `Adapter[P, S]` carries `S` so the options are
checked against it (D8):

```go
type Option[S any] func(*S) error

func (a Adapter[P, S]) Open(raw Settings, opts ...Option[S]) (P, error)
```

Three things this buys, each a compiler result rather than an assumption:

- **`S` is inferred, never written.** `pgx.Open(ctx, cfg, pgxdb.WithMaxConns(32))`
  names no type at all: `S` was fixed when `r.Provide` inferred it from
  the constructor. With **no** options it is still inferred, so the
  zero-configuration call needs no type argument either.
- **The adapter's settings struct can stay unexported.** Because no caller ever
  names `S`, `pgxdb` declares `type settings struct{…}` and exports only its
  `Option[settings]` constructors. A consumer package configures the adapter
  correctly while being unable to spell, construct or embed the struct — which is
  D5's strongest claim, holding for adapter settings as well as module settings.
- **Mismatches are compile errors.** Passing another adapter's option, or mixing
  two adapters' options in one call, fails to build with an error naming the
  types:

  ```
  type Option[otherSettings] of WithX(1) does not match inferred type Option[settings] for Option[S]
  ```

**So the answer to the owner's question is "both, split by path", not "no struct
params anywhere".** Being precise about this matters, because the two paths have
genuinely different capabilities:

- On the **typed path** — the adapter known at build time — variadic options are
  fully static and no struct param is needed. This is the common case and the
  house default.
- On the **config-driven path** — the adapter named by a runtime string — the
  settings arrive as a decoded blob by construction, because the caller cannot
  name a type that is only known at run time. That *is* the "struct params for
  dynamic cases" the owner said he would allow, and it is unavoidable rather than
  a design choice: the spike confirmed that recovering `S` into a type parameter
  at that call site is impossible. The owner's literal
  `OpenWith[P, S](name, settings S)` compiles, but it makes `S` a caller
  assertion that is never checked against `name`, so it is strictly worse than
  decoding into the type the constructor already declared.

**The one place goga does export a struct, and why it is not an exception.**
`Settings`-style types on the **driver side** — `serve/driver.Options` — are
exported, because an adapter in another package has to name them in its method
signatures to implement the port at all, and because the conformance suite (D21)
lives in a third package and has to construct them. go-cloud does the same
throughout: `driver.ReaderOptions`, `driver.WriterOptions`, `driver.ListOptions`
and per-adapter `s3blob.Options` are all exported, defended by nothing more than
a doc comment (*"intended for use by drivers only"*).

That is safe for the same reason it is safe there: **constructing one buys the
caller nothing.** There is no goga entry point that accepts one, and the only way
to obtain the portable type is the module's own constructor, which instruments.
The driver-side struct is not an alternative entry point; it is the vocabulary of
a boundary the application never reaches. So the rule is stated by side of the
port rather than as a blanket:

| side | shape | visibility |
|---|---|---|
| caller-facing (module and adapter settings) | variadic `Option[S]` over an unexported struct | **unexported** |
| driver-facing (per-call options a port hands an adapter) | plain struct, additive fields only (D7) | **exported** |

**This closes a tension that consumed two prior revision rounds** — "unexported
settings" versus "a registry needs to name the type" — by observing that the two
requirements were never about the same type.

**Adapter configuration follows the same seam** (the owner's comment:
*"The method should get settings and marshal it to the type that the adapter
expects and use it to initialize the adapter"*). `(*Registry).Register` bakes the
decode into the closure: the raw config subtree is unmarshalled into the
adapter's `S` — koanf into the type the adapter declared — then the caller's
options are applied **on top**, then the constructor runs. Precedence is config
first, options second, because options are the explicit form and the more
specific one. Adapter-side validation stays ordinary: the constructor returns an
error and the module wraps it (`goga/database/pgxdb: dsn is required`). Proven
end-to-end in the spike, including defaults, config-only, and
option-overrides-config.

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
*streaming* result must not cancel that result's context when it returns. A
`defer cancel()` in such a method kills the stream before the caller reads the
first item, and a `defer end(err)` closes the span before the operation has
actually done its work. The returned value therefore owns both: its `Close`
cancels the timeout context and ends the span, so the recorded duration covers
the whole read and closing twice is harmless. Non-streaming methods (`Exec`,
`Up`, `CallTool`) keep the defer.

*This rule was found as a defect in this document's own pseudocode, where
`database.Query` returned `Rows` and cancelled them on the way out. D7 has since
removed that method along with the port, so the worked example is gone — but the
rule is not tied to it and applies to every goga API that returns something the
caller reads incrementally. It is carried as a testable requirement in
`specs/goga-api-conventions/spec.md` ("A streaming result outlives the call that
returned it"), which is where an implementor should look for the scenarios.*

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
| M0 | *(repo, not a package)* — `go.mod` on Go 1.27 + `toolchain go1.27rc2` (D17), flat layout, root `goga` (`Option`/`Apply`), **`goga/registry`** (D8), the **`goga/lint` plugin scaffold** and the **skill skeleton** (D18), `.golangci.yml` / `Makefile` / `.goreleaser.yaml`, the **from-source golangci-lint build**, and the actions goga's own CI needs | goga itself | nothing can be delivered from an empty repo; and D18's six parts mean M1 cannot ship a linter rule or a skill section unless the mechanism for both exists first |
| M1 | `goga/telemetry` (+ generated `goga/semconv`) | **gopgql**, then **epos** | the owner's *"telemetry first"*; gopgql has none at all, epos has metrics only and never installs its meter provider |
| M2 | `goga/serve` (+ `driver`, the stdlib listener, `servetest` **as helpers, not a conformance suite** — D21) | **epos**, then **gopgql** | the owner's *"http with telemetry for gopgql and epos"*; three router positions across three projects is what makes uniform *serving* valuable — it is not what justifies replacing their routing APIs (D22). **This is the thinnest milestone in the plan**: with the router seam gone the module is the otelhttp wrap, the untraced ops mux, bounded timeouts and one drain, over a port with a single implementation. That is real, duplicated-everywhere value and epos needs it — but if any milestone is a candidate for merging into another, it is this one |
| M3 | `goga/config` | **epos**, then **skill-test/go-service**, then **mcp-anything** | the owner's *"config for all of them too"*; three koanf consumers with three incompatible arrangements, and epos's flag callback inverts its own precedence |
| M4 | `goga/database` (+ `pgxdb`, `sqlcdb`) | **gopgql**; **codiq** when it exists | the owner's *"postgres which could land to gopgql and codiq"* |
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

### D17: goga's Go floor is 1.27, on the owner's decision, and the cost is scheduled

**Decided by the owner on 2026-08-04**, answering D8-A: *"I don't care, use 1.27.
Build dependencies from source if necessary."* The 2026-07-31 round had specified
`go 1.27rc2`; an intervening revision reversed it to 1.24 on the grounds that the
capability the risk was being taken for did not need it (D8), and put the choice
to the owner. He has taken the 1.27 side with the costs in front of him, so this
section is now the *implementation* of that answer: what the floor is, exactly how
it is written, and what it obliges M0 to build.

**The floor, and the exact form.** `go.mod` says:

```
go 1.27

toolchain go1.27rc2
```

**Both lines, and the `toolchain` line is not optional.** A bare `go 1.27` breaks
under the default `GOTOOLCHAIN=auto`, because the toolchain tries to fetch a GA
release that does not exist — measured: `go: downloading go1.27.0 … download
go1.27.0 for darwin/amd64: toolchain not available`. With `toolchain go1.27rc2`
present the same build succeeds. Only rc1 and rc2 are published, and the
`toolchain` line moves to each successive RC and is dropped at GA.

What sets the floor is the registry's generic methods (D8). Nothing else in the
design needs anything newer than **Go 1.22** (`reflect.TypeFor`) or **1.23** (the
generic type alias), so if the registry's four methods were ever reverted to
package-level functions the floor would fall with them — which is the shape of the
GA migration, not an option the implementation may take.

**What the floor does to a consumer, measured on go1.26.4.** Go's module rule is
that a module cannot require a lower Go version than a module it depends on, so
`go >= 1.27` propagates into gopgql, epos, skill-test/go-service, mcp-anything and
sysgo the moment they adopt any goga package — including the ones that never touch
the registry. This is a consequence to **document**, per the API-conventions
capability, not one to mitigate:

- With the default `GOTOOLCHAIN=auto`, a developer on 1.26.4 building a goga
  consumer **silently downloads and switches to 1.27rc2**, and the build
  succeeds. No manual install, and no warning that a release candidate is now
  compiling production code. goga's README and skill say so (13.6).
- With `GOTOOLCHAIN=local` — hermetic CI, distribution packaging, an air-gapped
  or proxy-restricted builder — it is a hard failure:
  `go: go.mod requires go >= 1.27rc2 (running go 1.26.4; GOTOOLCHAIN=local)`.
  An adopting project on a pinned toolchain installs `go1.27rc2` before it can
  adopt anything.

**What it does to the linters, which is the sharp edge and is now M0 work.** D18
requires a linter with every milestone, and the current linter release cannot read
Go 1.27 code at all:

- `golangci-lint v2.7.2` as shipped refuses outright — *"the Go language version
  (go1.26) used to build golangci-lint is lower than the targeted Go version
  (1.27rc2)"*.
- Rebuilt from source **with go1.27rc2 it still fails**, because it pins
  `golang.org/x/tools v0.39.0`, whose export-data reader tops out below Go 1.27's
  format: *"cannot decode `internal/goarch`, export data version 4 is greater
  than maximum supported version 2"*. `staticcheck v0.6.1` fails the same way.
- The fix exists and is one line: golangci-lint v2.7.2 built from source against
  `golang.org/x/tools v0.48.0` lints generic-method packages cleanly — `0
  issues` — and a custom `x/tools/go/analysis` analyzer on v0.48.0 parses *and
  fully type-checks* a generic method.

So the 1.27 floor does not block the enforcement pillar, but it does mean goga's
`go-lint` composite action **builds golangci-lint from source with the `x/tools`
bump** instead of using the upstream prebuilt action, for as long as the RC lasts.
That is the *"build dependencies from source if necessary"* half of the owner's
answer, and it is scheduled: task **0.4d** builds it in M0, and task **11.4**
drops it once upstream ships a release on a new enough `x/tools`.

**The path at 1.27 GA.** Delete the `toolchain go1.27rc2` line, and revert
`go-lint` to the upstream prebuilt action once golangci-lint ships against a GA
1.27. `goga/registry` does not change at all — generic methods are the same
feature at GA that they are at rc2 — and there is no consumer-visible API change
on the typed `Adapter[P, S].Open` path at any point, which is where consumers
actually are.

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

### D19: one Go module, and three rules that keep an unused adapter out of a consumer's build

goga is **one module**, `github.com/gaarutyunov/goga`, with one package per
module and one package per adapter. Not one module per adapter.

This was measured rather than assumed. `gocloud.dev` is a single module holding
`blob`, `pubsub`, `docstore` *and* the AWS, GCP and Azure adapters — its root
`go.mod` directly requires eleven `aws-sdk-go-v2` packages, five Azure SDK
packages and `cloud.google.com/go/storage`, 124 requires in total. A minimal
consumer was built for this spec — a program importing only `gocloud.dev/blob`
and `_ "gocloud.dev/blob/memblob"`, the pure in-memory driver — and `go mod tidy`
run against it:

- **19 indirect requires in `go.mod`, and zero AWS or Azure SDK.** Go's module
  graph pruning works, and it works the same whether an adapter is attached by a
  blank import (as in go-cloud) or by an explicit `Provide(r)` call (as in goga,
  D8) — in both cases the deciding fact is simply whether the package is imported
  at all. **A project that does not import
  `goga/mcp/httptransport` does not compile its HTTP stack, and does not carry it
  in its build list** — the owner's constraint is satisfied by one module.
- **77 unique modules in `go.sum`, of which 25 are cloud SDKs.** Checksums only,
  nothing compiled — but they are in the file that dependency and vulnerability
  tooling reads.

Three leaks *did* reach that minimal consumer's build list, and each was an
accident rather than a decision. They become goga's rules:

1. **No shared or internal goga package may import anything heavier than
   OpenTelemetry and the standard library.** go-cloud's errors package drags in
   gRPC (`internal/gcerr` → `grpc/codes`) and its retry helper drags in
   `gax-go/v2`. If goga ever needs gRPC status codes, that mapping lives in
   `goga/grpc`, never in `goga/errors` or `goga/telemetry` (D6).
2. **No `_test.go` file in a portable package may import an adapter.**
   `gocloud.dev/blob/example_test.go` — the godoc examples for `As` — imports
   `gcsblob` and `s3blob`, and because `go mod tidy` follows the test
   dependencies of imported packages, `google.golang.org/api` and
   `cloud.google.com/go/storage` land in every consumer's `go.mod`. This one is
   invisible until somebody else runs `go mod tidy` and finds gin in their graph.
   Adapter examples live in the adapter's own package.
3. **Split a module out only for a genuinely toxic dependency** — cgo, a
   conflicting transitive version, or an SDK on the scale go-cloud split out for
   mongo, kafka, nats, rabbit, etcd and hashivault. The tax is real and
   measurable: go-cloud carries `internal/releasehelper/releasehelper.go`, 262
   lines whose entire job is stripping and restoring `replace gocloud.dev =>
   ../..` around releases, plus a tag-every-module script and a force-merged PR
   every release cycle (`internal/docs/release.md:30`).

**Rule 1 and rule 2 are enforced, not documented** (D5, D18). M0 ships a CI job —
about fifteen lines — that creates a throwaway module importing `goga/mcp` plus
exactly one transport (`httptransport`, which is the case with a real optional
dependency now that D22 has left `goga/serve` with no third-party adapters),
runs `go mod tidy`, and fails if the resulting `go.mod` gains a require outside
an allowlist. It would have caught all three of
go-cloud's leaks. `goga/lint` carries the companion rule for rule 2: a portable
package's test files may not import a sibling adapter package.

### D20: `As` is the escape hatch, it is kept deliberately small, and it is honest about being a runtime assertion

D2 already requires every wrapper to expose its underlying object. This decision
fixes the shape, because "expose the underlying object" has a good version and
several bad ones.

**The shape is go-cloud's `As`**, one method on the portable type:

```go
// As converts i to an adapter-specific type. It returns false if the adapter
// does not support the requested type. Callers must degrade gracefully.
func (s *Server) As(i any) bool
```

and the adapter's implementation is the whole of it (`blob/s3blob/s3blob.go:567`
is five lines):

```go
func (s *server) As(i any) bool {
	p, ok := i.(**gin.Engine)
	if !ok { return false }
	*p = s.engine
	return true
}
```

**Why a framework whose point is "projects do not touch the tool" has an escape
hatch at all.** The alternative to `As` is not purity; it is the port growing a
leaky union of every adapter's surface. go-cloud's own design document has an
open section titled *Enforcing Portability* that has been unresolved for years
(`internal/docs/design.md:490-551`). Without a hatch, the first project that
needs a gin middleware goga does not expose either forks goga or drops it.

**Three rules, and the third is where goga is narrower than go-cloud.**

- **`As` returning false is not an error.** Callers skip the adapter-specific
  tweak and carry on, so the same code still runs against the in-memory or test
  adapter (`concepts/structure/index.md:86-92`). A caller that errors on `false`
  has written adapter-locked code without saying so.
- **Every adapter documents what it supports**, in an `# As` section in its
  package doc, including "this adapter supports no types for `As`".
- **goga does *not* adopt go-cloud's `BeforeX(asFunc)` callbacks.** go-cloud
  threads `BeforeRead`, `BeforeWrite`, `BeforeCopy`, `BeforeDelete`,
  `BeforeList` and `BeforeSign` — each `func(asFunc func(any) bool) error` —
  through its driver option structs, so a caller can mutate the provider's
  request object in flight. Six of them in `blob/driver/driver.go` alone, and
  they are the single biggest reason that file is hard to read. A framework can
  afford "reach the underlying object" without also offering "mutate every
  request in flight". If a case for one appears, it is a new decision.

**And it is a runtime assertion.** `As` is exactly the *downcast* half of the
owner's "cast interfaces into adapters" (D8), and no generic form makes it
static: the compiler does not know the dynamic type behind the port. This is
stated in the doc comment, not just here.

`As` usage is also the signal the skill teaches the model to flag: reaching past
a port means either goga should grow that capability, or the project should
record why not.

### D21: a conformance suite for the ports that have more than one implementation, and for no others

Where goga has a real port with real alternatives, adapters must be
interchangeable, and "interchangeable" is a claim only a shared test suite can
make. The pattern is `gocloud.dev/blob/drivertest` and goga copies it
structurally.

```go
package servetest // goga/serve/servetest

// Harness is what an adapter supplies. Everything else is the suite's.
type Harness interface {
	MakeDriver(ctx context.Context) (driver.Server, error)
	Close()
}
type HarnessMaker func(ctx context.Context, t *testing.T) (Harness, error)

func RunConformanceTests(t *testing.T, newHarness HarnessMaker, asTests []AsTest)
```

An adapter opts in with roughly thirty lines — `blob/memblob/memblob_test.go` is
the reference — ending in:

```go
func TestConformance(t *testing.T) { servetest.RunConformanceTests(t, newHarness, nil) }
```

Four properties are normative, each taken from a specific thing go-cloud does:

- **The suite is comprehensive enough to replace per-adapter semantics tests.**
  go-cloud states it outright (`internal/docs/design.md:740-748`): *"drivers
  should not need additional unit tests for the core driver semantics."* That is
  the trade — one large suite, ~30 lines per adapter.
- **Regressions are pinned in the suite, not in one adapter's tests.**
  `drivertest.go:253` carries `TestDirsWithCharactersBeforeDelimiter`, tied to a
  specific upstream issue. The suite is where bugs go to stay dead.
- **The escape hatch is itself conformance-tested.** `AsTest`
  (`drivertest.go:96-130`) is an interface the adapter implements so the suite can
  drive its `As` implementations through a full operation cycle.
- **The suite injects its own invariants regardless of what the adapter opted
  into.** `drivertest.go:295` is `asTests = append(asTests, verifyAsFailsOnNil{})`
  — every adapter is checked for `As(nil) == false` whether it asked or not. That
  is how a rule is made unskippable.

**Which ports get one, and which explicitly do not.** The cost only pays back
where the port is genuinely multi-implementation:

| module | suite? | why |
|---|---|---|
| `goga/serve` | **not yet** | its port is the *listener*, and v1 ships one implementation. The three-router evidence justified serving them uniformly, not a suite — D22 removed the seam that argument was for. A suite arrives with the second listener |
| `goga/migrate` | **yes** | goose, atlas and golang-migrate are real alternatives |
| `goga/mcp` | yes, when a second transport ships | `stdio` alone does not need one |
| `goga/components` | yes, when a second deployer ships | see D12 |
| `goga/database` | **no** | no port (D7); `database/sql` conformance is the standard library's |
| `goga/config`, `goga/cli`, `goga/client`, `goga/codegen`, `goga/grpc` | **no** | one implementation each; a conformance suite for one implementation is pure cost |

**What goga does not copy: record/replay.** go-cloud provisions cloud resources
with Terraform, records HTTP traffic in `-record` mode, and commits replay files;
it then explicitly gave up on scrubbing them, so *"massive diffs in the replay
files are expected and fine"* (`internal/docs/design.md:806-826`). goga's answer
is already chosen and is strictly better: testcontainers (D-gogatest). Real
Postgres, no replay files, no scrubbing, no Terraform.

### D8b: a recommendation to the owner about `goga/registry` — not a decision

**Flagged rather than acted on, because the owner asked for the registry by name
twice.** An independent audit of D8 made a case for deleting `goga/registry`
outright, and it is strong enough that he should see it rather than have it
resolved here.

The evidence, all of it from this document:

- **Before this revision, not one module used it.** D8's table assigned registry
  tables to `serve`, `telemetry`, `mcp` and `components`; all four specified
  something else, and `serve` had no table at all. The registry's only appearance
  outside D8 was a worked example that **directly contradicted `goga/mcp`'s own
  `TransportOpener`** seven hundred lines later — two incompatible registration
  APIs for the same adapter in one document.
- **The module-owned surfaces were the better of the two.** They took a
  `context.Context` and a module-owned `Settings` accessor interface; the
  registry took neither, and both had to be added to it above.
- **The document's own surfaces had independently converged** on the shape that
  does not need it.

The counter-case, which is why this revision keeps it:

- The owner asked for it explicitly, twice, and *"a structure that can cast
  interfaces (ports) into adapters"* is a direct description of it.
- With this pass it is no longer duplicated: the module surfaces are implemented
  over it, so the storage, decode, duplicate check, port check and diagnostics
  exist once rather than four times.
- Without it, the config-driven path — an adapter named in configuration and
  resolved at startup — has to be written per module.

Two options for the owner:

- **(a) Keep it as now specified**: shared mechanism, typed module surfaces on
  top. *This is what the spec says.*
- **(b) Delete `goga/registry`**, and let each module own its table outright.
  Smaller spec, less indirection, and where the document had already arrived on
  its own — at the cost of four copies of the same thirty lines, and of dropping
  something the owner asked for by name.

### D21a: a recommendation to the owner about `goga/components` — not a decision

**Flagged, not acted on, because the owner put this module in scope by name.**
The review that produced the rest of this revision found `goga/components` in an
odd position, and the evidence is worth putting in front of him rather than
resolving quietly:

- It has **no milestone slot at all.** D16's table runs M0 through M13 and
  contains no `components` row, because D16 gates every milestone on a named
  adopting project and this module has none.
- It nevertheless carries **the largest invented surface in the document** —
  `Component`, `Ref[T]`, `Deployer`, `Graph` and three adapters — plus a
  three-requirement, fourteen-scenario delta spec.
- Its upstream, `ServiceWeaver/weaver`, is **archived** (`isArchived: true`, last
  push 2025-11-20).

So it is fully specified and, by the plan's own rules, unbuildable. Nothing is
broken by that — D16 already prevents it being built prematurely, which is the
outcome the gate exists for — but it is a large amount of specification that no
consumer will validate, written against a dependency that is no longer
maintained.

Three options, and this is the owner's call:

- **(a) Cut the package surface to a paragraph, keep the delta spec.** D12's
  interface decision — the one that makes whichever deployer arrives first an
  adapter rather than a rewrite — is the part worth keeping, and it survives at a
  fraction of the length. *Recommended.*
- **(b) Lift `goga-components` out of this change entirely**, and let it return
  as its own change when a consumer exists.
- **(c) Leave it as written**, accepting that it is specified but ungated.

### D22: what v1 freezes, what churns, and the capability problem goga inherits

**The cautionary evidence.** `gocloud.dev` is eight years old, has ~9.9k stars,
is actively maintained (last commit 2026-08-03, quarterly releases, v0.46.0 on
2026-06-02) — and is **still v0.x**. Its README says, today, *"The APIs are still
in alpha, but we think they are production-ready."* Its only compatibility
commitment is that it will give *"a heads-up before making any breaking
changes."* A design this one is modelled on, with this much care behind it, never
committed to interface stability. goga's whole premise is stable interfaces that
outlive the tools behind them, so it has to say what it actually promises.

**What v1 freezes:**

- Every **portable type** and its exported methods — `serve.Server`,
  `telemetry.Instrumentation`, `mcp.Server`, and the `Option` surface of each.
- The **root `goga` package** (`Option`, `Apply`).
- `goga/registry`'s exported surface.
- The `As` contract (D20).

**What is explicitly not frozen, and says so in its package doc:**

- **`goga/*/driver` packages.** These are the extension point, and they evolve —
  by the two channels D7 fixes: additive option-struct fields, and new *optional*
  interfaces. Adding a method to an existing driver interface is a breaking
  change and requires a major version. go-cloud gets away with breaking its
  driver interfaces only because every driver lives in its repository
  (`allmodules` lists eleven modules, all in-tree; `contrib/` holds one shell
  script) so it can fix them all in one commit. **goga's adapters are in-tree
  too, for the same reason** — and the day an out-of-tree adapter exists, that is
  the day the `driver` packages need their own compatibility promise.

**The capability problem, recorded as the largest inherited risk.** go-cloud
never solved it: its *Enforcing Portability* section considers three approaches —
documentation, restricting to the intersection, and enforced `FeatureCode` enums
declared by drivers and requested by users — and concludes *"Design discussions
regarding enforcing portability are ongoing."* Unresolved after eight years. In
practice its answer is a runtime `Unimplemented` error, which is third on its own
best-to-worst list (compile time > startup > runtime error > panic).

**goga has this problem worse, and sooner.** S3 and GCS are ninety percent the
same service. gin, echo, chi and `http.ServeMux` differ in routing syntax,
middleware signature, binding, validation and error handling; goose and atlas
differ in migration file format. goga hits this at M2, not in year three. Two
mitigations, both cheap now and expensive to retrofit:

- **Keep every port at the narrowest genuinely-common denominator.** For
  `goga/serve` that means the port is `http.Handler` and nothing richer — see the
  package surface. A port that is a routing DSL does not survive its second
  adapter.
- **If a capability-declaration mechanism is ever wanted, it goes in at
  construction time from the start** — an adapter declares what it supports, the
  caller declares what it needs, and the mismatch is an error when the object is
  built rather than when the feature is touched. Retrofitting this is precisely
  what go-cloud has failed to do for eight years. v1 does **not** build it; v1
  keeps ports narrow enough not to need it, and this decision is the record of
  why that is a deliberate bet rather than an oversight.

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

### `goga/registry` (D8)

Imports the standard library, `reflect`, and the root `goga` package — nothing
else, and in particular no `telemetry`. Root `goga` is a leaf, so no cycle is
possible. The single framework import exists only so `Option` can be an alias
rather than a second declaration (below). The registry carries no
`Instrumentation`: the resolve span belongs to the module that owns the port,
where its instrumentation already is (D6).

Normative form is generic **methods** on `*Registry`, per the owner's answer to
D8-A. This is what sets the module's `go 1.27` floor (D17); the superseded
package-level-function form is the same file with four lines changed and is
recorded in D8 as the alternative that was weighed, not as a fallback.

```go
package registry

// Settings is one adapter's raw configuration subtree — koanf's node, decoded
// into the adapter's own type inside Register's closure.
type Settings map[string]any

// Option is a generic type ALIAS of goga.Option. It must be an alias, not a
// second identical declaration: distinct named types would make an adapter's
// option unusable with goga.Apply, which the compiler confirms. This is the one
// framework package goga/registry imports.
//
// DIRECTION, and it was contested. The audit proposed the reverse — declare
// Option in registry and alias it from root goga — to keep registry importing
// nothing. This design keeps root goga as the home, because Option is used by
// EVERY module for its own settings, including the ones with no adapters at all
// (config, cli, client, migrate). If registry owned it, `goga/config` would
// depend on the adapter registry in order to name its own option type, which is
// backwards. The cost is one import of a package that is itself standard-library
// only, so the property the leaf rule protects — no cycles, no heavy
// dependencies — is untouched; the depguard rule is written to permit exactly
// this one edge and nothing else.
//
// Its own language gate is go1.23, measured against the compiler, which rejects
// it at `go 1.22` with "generic type alias requires go1.23 or later". That is
// far below the module's actual floor of 1.27, which the generic methods below
// set (D17). Noted anyway, because it is what the floor would fall to if those
// methods ever became package-level functions again.
type Option[S any] = goga.Option[S]

type entry struct {
	open     func(context.Context, Settings, func(any) error) (any, error)
	settings reflect.Type // recorded for diagnostics; S is otherwise invisible
	port     reflect.Type // recorded so Open can check P against registration
}

type Registry struct {
	mu sync.RWMutex
	m  map[string]entry
}

// New takes the DECODER (see D8): the registry must not choose it, because
// adapter settings are tagged `koanf:` and the only stdlib struct-tag decoder is
// encoding/json, which drops those fields silently. goga/config supplies it.
// Panics if decode is nil — that is a wiring error, not a runtime condition.
func New(decode Decode) *Registry

// Decode is the injected seam. A decoder SHOULD reject unknown keys rather than
// ignore them, so a mistyped setting is a startup error and not a zero value.
type Decode func(raw Settings, dst any) error

// Register records a constructor under a plain adapter NAME. BOTH type
// parameters are inferred from ctor, so no caller — and no other package — ever
// writes S. That is what lets an adapter keep its settings struct unexported
// (D14). Verified on go1.27rc2 that the method form does not disturb this:
// `r.Register("pgx", newPool)` needs no explicit instantiation of either.
//
// Register RETURNS AN ERROR on a duplicate name rather than panicking. The
// previous revision panicked, following gocloud.dev — but that was justified by
// a duplicate being a programming error inside an init() against a package-level
// table. With the registry an injected value (D8) there is no init(), the
// duplicate is detected while ordinary startup code is running, and a panic
// there is worse than a returned error. `New` still panics on a nil decoder,
// because that is a wiring mistake with no sensible recovery.
//
// It records BOTH type parameters: the settings type, and the PORT — the latter
// so that Open can check what a caller asks for against what was registered.
//
// The constructor signature is FIXED at func(context.Context, S) (P, error) and
// goga holds it. What is load-bearing is that ONE shape is fixed and held: a
// different shape per adapter would break inference. *Which* shape is free, and
// ctx is the better choice, because adapter construction is I/O in every
// adapter-bearing module. (The first spike reported the ctx-less shape as
// necessary; re-measured, inference is unaffected by a leading context.)
func (r *Registry) Register[P any, S any](name string, ctor func(context.Context, S) (P, error)) error

// Open is the CONFIG-DRIVEN path: the adapter is named by a runtime string, so
// P is result-only and must be instantiated explicitly. Decodes raw into the
// adapter's S, then constructs.
//
// The unknown-name error names what IS registered and points at the likely
// cause, so a typo is self-diagnosing:
//
//	goga/mcp: no adapter "htp" (registered: http, sse, stdio); did you forget
//	httptransport.Provide(r) in the composition root?
//
// reflect.TypeFor[P]() is used in these messages, never %T on the zero value —
// %T on a nil interface prints "<nil>".
// Open checks the recorded port against P before constructing, so an adapter
// registered for one port cannot be retrieved as an unrelated interface that
// happens to have the same method set.
func (r *Registry) Open[P any](ctx context.Context, name string, raw Settings) (P, error)

// Names carries no type parameters of its own and needs no 1.27 feature; it is a
// method for symmetry with Register/Open/Provide, which are methods because the
// owner's answer to D8-A puts the registry on generic methods. Keeping all four
// in one form means the GA migration, if the floor ever moves, is a uniform edit
// rather than a partial one.
//
// It TAKES THE READ LOCK. This looks read-only enough to skip and is not:
// -race flags it immediately against a concurrent Register.
func (r *Registry) Names() []string

// Adapter[P,S] is the TYPED HANDLE. Both type parameters are static, so there
// is nothing to instantiate at the call site and a foreign adapter's option is
// a compile error. Its type parameters belong to the TYPE, not to its methods,
// so nothing on this half of the surface was touched by D8-A.
type Adapter[P any, S any] struct {
	name string
	reg  *Registry
}

// Provide registers and returns the handle in one call, so it returns Register's
// duplicate-name error rather than swallowing it.
func (r *Registry) Provide[P any, S any](name string, ctor func(context.Context, S) (P, error)) (Adapter[P, S], error)

// Open applies raw config first, then the caller's options ON TOP. Precedence
// is deliberate: options are the explicit, more specific form (D14). An option
// returning an error is wrapped as "goga: applying option: %w", the same shape
// goga.Apply uses, so the two paths report the same failure the same way.
func (a Adapter[P, S]) Open(ctx context.Context, raw Settings, opts ...Option[S]) (P, error)

func (a Adapter[P, S]) Name() string
```

An adapter package. Note `settings` is unexported and never leaves:

```go
package httptransport // goga/mcp/httptransport

type settings struct {
	Endpoint    string        `koanf:"endpoint"`
	IdleTimeout time.Duration `koanf:"idle_timeout"`
}

func newTransport(ctx context.Context, s settings) (mcp.Transport, error) { … }

func WithIdleTimeout(d time.Duration) registry.Option[settings] {
	return func(s *settings) error {
		if d <= 0 {
			return fmt.Errorf("goga/mcp/httptransport: idle timeout must be > 0")
		}
		s.IdleTimeout = d
		return nil
	}
}

// Adapter is an EXPORTED ALIAS of the instantiated handle, and every adapter
// package declares one. Without it the handle is unusable under D9: a
// downstream wire provider that takes it as a parameter, or a composition root
// that holds it as a field, cannot NAME the type — `settings` is unexported, and
// the compiler says "name settings not exported by package httptransport". The
// handle would work only as a local `:=` inside one function, so
// `wire.NewSet(Provide)` would contribute a node nothing could depend on.
//
// The alias fixes that without exporting `settings`: the alias name is exported,
// the type argument is not, and a consumer names the alias. Verified as a
// provider parameter, a struct field and a second provider's input.
//
// Note this is an alias to an ALREADY-INSTANTIATED generic type, which is not
// the version-gated feature — it compiles at go1.22. Only aliases carrying their
// own type parameters need go1.23, and neither is what sets goga's 1.27 floor
// (D17).
type Adapter = registry.Adapter[mcp.Transport, settings]

// Provide is the wire-facing entry point and the typed handle in one. It calls
// the METHOD form of registry.Provide (D8-A) and returns its error.
func Provide(r *registry.Registry) (Adapter, error) {
	return r.Provide("http", newTransport)
}

var Set = wire.NewSet(Provide)
```

Note what the consumer package can and cannot do: it calls
`httptransport.WithIdleTimeout(30*time.Second)` and gets full type checking, and
it **cannot name, construct or embed `settings`** — the type is unexported and
`S` was fixed by inference when `Provide` ran (D14).

All three ways to bind a port to an adapter, and when each applies (D8):

```go
// 1. Static binding — the DEFAULT under wire, no registry involved at all:
wire.Bind(new(mcp.Transport), new(*stdiotransport.Transport))

// 2. Typed handle — adapter known at build time, options statically checked:
tr, err := httpTr.Open(ctx, cfg.Cut("mcp"), httptransport.WithIdleTimeout(30*time.Second))

// 3. Config-driven — adapter named in configuration, chosen at startup:
tr, err := r.Open[mcp.Transport](ctx, cfg.String("mcp.transport"), cfg.Cut("mcp"))
```

The third form is the only one that needs the string, and it is the only one
where a mismatch is a runtime error rather than a compile error. That is the
inherent cost of letting configuration choose, and it is why it is not the
default.

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

// Exporters go through the SHARED registry (D8) — this module declares no table
// of its own. The standard names delegate to contrib/exporters/autoexport, which
// mcp-anything already depends on and which needs no registry at all; the
// registry exists for the house/custom names that are additive to it.
//
// The registry is an injected value, not a package-level default (D8), so it is
// supplied by an option and is absent for the common case:
func WithExporterRegistry(r *registry.Registry) Option

// This module's typed surfaces, implemented over goga/registry (D8). Unlike
// goga/mcp there is no module-owned Settings accessor, because an exporter reads
// its endpoint, headers and protocol from the environment through autoexport and
// the resource is attached to the provider rather than the exporter — D5's rule
// that a module passes settings to an adapter only where an adapter reads them.
func RegisterTraceExporter[S any](r *registry.Registry, name string,
	ctor func(ctx context.Context, s S) (sdktrace.SpanExporter, error)) error
func RegisterMetricExporter[S any](r *registry.Registry, name string,
	ctor func(ctx context.Context, s S) (sdkmetric.Exporter, error)) error
func RegisterLogExporter[S any](r *registry.Registry, name string,
	ctor func(ctx context.Context, s S) (sdklog.Exporter, error)) error
//
// Setup resolves a configured name that autoexport does not recognise through
// the registry's Open METHOD (D8-A), passing the ctx it was called with — an
// exporter dials at construction, which is exactly why the ctor takes one (D8):
//
//	exp, err := r.Open[sdktrace.SpanExporter](ctx, name, cfg.Cut("telemetry.traces"))
//
// goga/registry is a leaf that carries no Instrumentation, so
// registry -> telemetry -> registry cannot form (D6, D8).

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
// a concrete provider — a composition root constructs some modules, registries
// and adapters BEFORE Setup installs the real providers, and a snapshot taken at
// construction would leave those paths permanently no-op while every test
// passed (D6). It
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

### `goga/database` and `goga/database/pgxdb` (D7)

**There is no `goga/database/driver` package and no portable `DB` type.** D7
reverses the previous revision here; what follows is what replaces roughly two
hundred lines of port, adapter table and portable wrapper.

Two packages, two honest return types, both instrumented at construction:

```go
package database // goga/database

// DSN is a named type so wire's type-keyed graph can supply it (D9). It is
// CONTENT handed to one known driver — never an adapter selector (D8).
type DSN string

type settings struct{ /* unexported (D14) */ }
type Option = goga.Option[settings]

func WithMaxOpenConns(n int) Option
func WithMaxIdleConns(n int) Option
func WithConnMaxLifetime(d time.Duration) Option
func WithSQLCommenter(on bool) Option                   // trace context into SQL comments
func WithTelemetry(i *telemetry.Instrumentation) Option // replaces; never disables

// Open returns the STANDARD LIBRARY's *sql.DB, instrumented. Not a goga type:
// there is nothing for a goga type to add here that otelsql and database/sql do
// not already do, and a wrapper would only make goose, sqlc and every existing
// helper take an unwrap step.
//
// Instrumentation is applied by wrapping the sql DRIVER, which is exactly what
// gocloud.dev/postgres does (postgres.go:60, otelsql.WrapDriver). So no
// UNINSTRUMENTED handle leaves this package — though, unlike every other goga
// module, that is a property of this constructor rather than of the type, since
// *sql.DB is the standard library's and anyone can sql.Open one (D7). D6 holds
// without a portable type: there is no exported way to get an uninstrumented
// handle out of this package.
func Open(ctx context.Context, dsn DSN, opts ...Option) (*sql.DB, error)

// Tx runs fn in a transaction, committing on nil and rolling back on error or
// panic. A free function over *sql.DB rather than a method on a wrapper, so the
// type flowing through the application stays *sql.DB. Three projects would
// otherwise each write this, which is the D2 justification — and it is the only
// one that survived the reversal.
func Tx(ctx context.Context, db *sql.DB, fn func(context.Context, *sql.Tx) error, opts ...TxOption) error

var Set = wire.NewSet(openWithCleanup) // cleanup is func(), the only shape wire takes (D9)
```

```go
package pgxdb // goga/database/pgxdb

// A SEPARATE package returning pgx's own type. Nothing is erased: CopyFrom,
// SendBatch, LISTEN/NOTIFY and native types are all directly available, because
// there is no interface in between pretending they are portable.
type settings struct{ /* unexported */ }
type Option = goga.Option[settings]

func WithMaxConns(n int) Option
func WithMinConns(n int) Option
func WithTelemetry(i *telemetry.Instrumentation) Option

// Open returns *pgxpool.Pool, instrumented with otelpgx — already the house
// choice in mcp-anything. The tracer is installed on the pool config here, so a
// caller cannot obtain an uninstrumented pool from this package (D6).
func Open(ctx context.Context, dsn database.DSN, opts ...Option) (*pgxpool.Pool, error) {
	cfg, err := pgxpool.ParseConfig(string(dsn))
	if err != nil {
		return nil, fmt.Errorf("goga/database/pgxdb: parsing dsn: %w", err)
	}
	// … apply settings …
	cfg.ConnConfig.Tracer = otelpgx.NewTracer(otelpgx.WithTrimSQLInSpanName())
	pool, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		return nil, err
	}
	return pool, otelpgx.RecordStats(pool)
}

// SQLDB bridges to database/sql for the tools that need it — goose does (D10).
// stdlib.OpenDBFromPool, so no caller has to know that.
func SQLDB(pool *pgxpool.Pool) *sql.DB

// Tx is pgx's transaction helper, and it exists for the same reason
// database.Tx does: three projects would otherwise each write it. It is a
// SEPARATE function rather than a shared one because pgx's transaction type is
// pgx.Tx and the standard library's is *sql.Tx, and the whole point of D7 is to
// stop pretending those are one thing. The commit/rollback/panic semantics and
// the whole-transaction timeout are identical, and gogatest asserts that they
// stay identical.
func Tx(ctx context.Context, pool *pgxpool.Pool, fn func(context.Context, pgx.Tx) error, opts ...TxOption) error

var Set = wire.NewSet(Open)
```

**What this costs, stated.** A project cannot swap pgx for `database/sql` by
changing a config string; it changes an import and a type. That is the honest
position — those two were never interchangeable — and it is the whole content of
the reversal. What a project gains is that neither path is lossy: gopgql keeps
`CopyFrom` without an `Unwrap`, and goose keeps `*sql.DB` without a bridge
method on a wrapper.

**What was deleted and where its lesson went.** The previous revision's portable
`*DB` carried a streaming-`Rows` discipline — the timeout context and the span
had to outlive `Query` and be closed exactly once by `Rows.Close`, because
deferring them inside `Query` returns rows that fail on the first `Next()` with
*"context canceled"* and records a duration that excludes the query. That code
is gone with the port, but **the rule is not**: it is a real defect this document
found in its own pseudocode, it still applies to every goga module that returns
a stream, and it stays in D15 where it belongs rather than in a database module
that no longer has a stream of its own.

```go
package sqlcdb // goga/database/sqlcdb — the sqlc runtime seam (D11)

// DBTX is the interface sqlc's pgx/v5 mode generates against. Under D7 this
// seam gets simpler rather than harder: *pgxpool.Pool satisfies DBTX directly,
// so generated sqlc queries run on the instrumented pool with no adapter check,
// no ErrNotPgx, and no goga type in the way.
//
// The previous revision needed a New(*database.DB) (DBTX, error) that could
// fail at run time when the resolved adapter was not pgx. With the port gone,
// that failure mode does not exist: the caller either has a *pgxpool.Pool or
// does not, and the compiler knows which.
type DBTX interface {
	Exec(context.Context, string, ...any) (pgconn.CommandTag, error)
	Query(context.Context, string, ...any) (pgx.Rows, error)
	QueryRow(context.Context, string, ...any) pgx.Row
	CopyFrom(context.Context, pgx.Identifier, []string, pgx.CopyFromSource) (int64, error)
	SendBatch(context.Context, *pgx.Batch) pgx.BatchResults
}

var _ DBTX = (*pgxpool.Pool)(nil) // the whole seam
```

For sqlc's `database/sql` mode the same applies against `*sql.DB`, which is why
this package holds an assertion and not an adapter.

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

### `goga/serve` — the port is `http.Handler` (D7, D22)

**This section is narrowed in this revision.** The previous one specified a
`Router` port — `Handle(method, pattern string, h http.Handler)`, `Use(mw …)`,
plus framework-owned pattern syntax that each adapter translated (`{id}` → gin's
`:id`) and a `Use`-before-`Handle` rule each adapter had to enforce by panicking.
That is a routing DSL, and it is exactly the abstraction D22 says will not
survive its second adapter. The evidence was already in the previous revision's
own comments: gin applies middleware only to routes registered afterwards, chi
panics, a stdlib wrapper applies it to everything — three behaviours the port had
to paper over, before anyone had written a single handler.

**The survey evidence is kept but read correctly.** Three router positions across
three projects justifies goga *serving* all three uniformly. It does not justify
goga *replacing* their routing APIs. `http.Handler` is what all three already
agree on, it is lossless, and every one of `goga/serve`'s actual value-adds —
otelhttp wrapping, the ops mux outside the trace, health and readiness, bounded
timeouts, single-owner graceful drain — is expressible on it alone.

The port is therefore go-cloud's, verbatim (`server/driver/driver.go`):

```go
package driver // goga/serve/driver

// Server dispatches requests to an http.Handler. Two methods, and neither of
// them knows what a route is.
type Server interface {
	ListenAndServe(addr string, h http.Handler) error
	Shutdown(ctx context.Context) error
}

// TLSServer is an OPTIONAL interface (D7): a new capability arrives as a new
// interface, never as a method on Server. serve.Server type-asserts it, so no
// adapter that does not serve TLS has to grow a stub.
type TLSServer interface {
	ListenAndServeTLS(addr, certFile, keyFile string, h http.Handler) error
}

// Options is EXPORTED, because adapters in other packages name it in their
// method signatures and the conformance suite (D21) constructs it. This is the
// driver-facing side of the split in D14: exported here, unexported upstairs.
// New fields may be added; an adapter may ignore any field it does not support.
type Options struct {
	ReadHeaderTimeout time.Duration
	ReadTimeout       time.Duration
	WriteTimeout      time.Duration
}
```

```go
package serve

type settings struct{ /* unexported (D14) */ }
type Option = goga.Option[settings]

// Addr is a named type so wire can supply it unambiguously (D9).
type Addr string

func WithAddr(addr string) Option
func WithOpsAddr(addr string) Option // ops listener; default: same port, separate mux
func WithReadHeaderTimeout(d time.Duration) Option
func WithReadTimeout(d time.Duration) Option
func WithWriteTimeout(d time.Duration) Option
func WithShutdownGrace(d time.Duration) Option
func WithHealthCheck(name string, fn func(context.Context) error) Option
func WithReadinessCheck(name string, fn func(context.Context) error) Option
func WithMiddleware(mw ...func(http.Handler) http.Handler) Option
func WithDriver(d driver.Server) Option // default: the standard library

// New takes the application's handler. A *gin.Engine, a *chi.Mux, an
// *http.ServeMux and oapi-codegen's generated server are all http.Handler
// already, so all four work with no adapter, no pattern translation and no
// middleware-ordering rule. The router is the application's choice, which is
// where it was always going to end up.
func New(ctx context.Context, h http.Handler, opts ...Option) (*Server, error)

// Server is the portable type. `root` is what is actually served: the traced
// application handler at "/", plus the untraced ops mux at its fixed paths.
//
// There is no *http.Server field. The previous revision had one alongside the
// driver, which left it ambiguous which of the two listened and where the
// timeouts were applied. The driver listens; the timeouts are carried across to
// it in driver.Options at construction, and the stdlib driver is the thing that
// owns an *http.Server internally.
type Server struct {
	app           http.Handler   // the application's handler, after middleware + otelhttp
	ops           *http.ServeMux // /livez /readyz /healthz /metrics — NEVER traced
	root          http.Handler   // app + ops, the handler handed to the driver
	d             driver.Server
	addr          Addr
	shutdownGrace time.Duration
	instr         *telemetry.Instrumentation
}

func (s *Server) Run(ctx context.Context) error
func (s *Server) Ops() *http.ServeMux
func (s *Server) As(i any) bool // D20; *http.Server, or the adapter's own type

var Set = wire.NewSet(New)
```

`New`'s body keeps the two things the survey said never survive a document — the
otelhttp wrap applied exactly once, and the operational endpoints registered
*outside* it, which `go-service` discovered by hand:

```go
	traced := otelhttp.NewHandler(applyMiddleware(h, s.middleware), "",
		otelhttp.WithSpanNameFormatter(routePattern))

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
```

and `Run` keeps the single-owner drain, unchanged and still load-bearing:

```go
// Run serves until ctx is cancelled, then drains within a bounded grace period.
// It does NOT install signal handling: cli.App.Run owns that, so a process
// serving HTTP and MCP together drains once, in one order (D15). An earlier
// revision called signal.NotifyContext here, which gave such a process three
// independent shutdowns with no ordering between draining connections, closing
// the pool and flushing telemetry.
func (s *Server) Run(ctx context.Context) error {
	errc := make(chan error, 1) // buffered: the goroutine never blocks after we return
	go func() { errc <- s.d.ListenAndServe(string(s.addr), s.root) }()
	select {
	case err := <-errc:
		if errors.Is(err, http.ErrServerClosed) {
			return nil
		}
		return fmt.Errorf("goga/serve: %w", err)
	case <-ctx.Done():
		sctx, cancel := context.WithTimeout(context.WithoutCancel(ctx), s.shutdownGrace)
		defer cancel()
		return s.d.Shutdown(sctx) // in-flight work finishes, or the grace expires
	}
}
```

**What the adapters become.** `goga/serve/driver`'s default implementation is
`*http.Server` and ships in v1. gin, chi and mux need **no goga adapter at all**
— they are handlers, and a project passes one to `New`. The adapter seam that
remains is the one go-cloud actually kept: an alternative *listener* (h2c, a unix
socket, a test harness, `httptest`), which is what `driver.Server` abstracts.

**What a project loses, stated.** Nothing that was real. It never became possible
to change routers without touching handlers — the previous design's own pattern
translation and `Use` panic are the proof that it was not. What a project gains
is that gin's, chi's and the standard library's own routing APIs are available
undiminished, and `goga/lint`'s rule for this module changes accordingly: it no
longer bans importing gin, it requires that the handler reach the process through
`serve.New` so that nothing is served untraced.

**`goga/serve/servetest` ships, but it is not a conformance suite** (D21). The
listener port has one implementation in v1, and D21's own rule is that a suite
for one implementation is cost without the property it establishes. What ships
instead is a set of **test helpers for the projects adopting the module**: an
in-process listener, and assertions a project runs against *its own* handler —
that a request is traced once, that `/livez`, `/readyz`, `/healthz` and
`/metrics` are not, that a configured timeout is enforced, and that an in-flight
request survives a drain. Those are properties of `serve.Server`, not of a
listener, which is the other reason they do not belong in a conformance suite.
When a second listener ships, the drain and timeout assertions are what the
conformance suite is built from.

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

// Settings is this module's accessor interface — the values the caller gave the
// MODULE, which a transport reads. Distinct from the transport's OWN settings
// type, which the registry decodes from configuration and which stays
// unexported in the transport's package (D14).
type Settings interface {
	ToolTimeout() time.Duration
	ServerName() string
}

// RegisterTransport is this module's typed surface. It is IMPLEMENTED OVER
// goga/registry (D8) — the storage, decode, duplicate check, port check and
// diagnostics are the registry's, and this signature is what an adapter author
// and a composition root actually touch. The ctx is load-bearing rather than
// ceremonial: the HTTP and SSE transports bind a listener at construction.
func RegisterTransport[S any](r *registry.Registry, name string,
	ctor func(ctx context.Context, ms Settings, as S) (Transport, error)) error

func WithTransportRegistry(r *registry.Registry) Option
func WithTransport(name string) Option // resolved through the registry above

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

// Settings is this module's accessor interface, as in goga/mcp. RegisterDeployer
// is this module's typed surface, implemented over goga/registry (D8).
type Settings interface {
	ConfigPath() string
}

func RegisterDeployer[S any](r *registry.Registry, name string,
	ctor func(ctx context.Context, ms Settings, as S) (Deployer, error)) error

func WithDeployerRegistry(r *registry.Registry) Option

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
| Variadic options, no param structs (caller-facing) | the settings struct is **unexported**, so no other package can name it; an adapter's `S` is inferred from its constructor and never written; every goga entry point takes `...Option`; `goga/lint` `gogaparamstruct` for project code. Driver-facing option structs are exported by necessity and are not an exception (D14) | compile + lint |
| No uninstrumented database handle exists in a project | **lint, not compile — the one exception, and D7 says why**: `depguard` confines `database/sql` to `goga/database` and `jackc/pgx` to `goga/database/pgxdb`, because `*sql.DB` is the standard library's type and goga cannot make holding one prove anything | lint |
| Every module with runtime operations has telemetry | portable types have unexported fields and no exported constructor; no module exports an adapter lookup, so there is no goga call returning a raw driver type; no `WithoutTelemetry`; `TestEveryModuleIsInstrumented` asserts the instrumented set is exactly the module list minus `{semconv, lint, di, registry, goga (root), app, gogatest}` | compile + test |
| Delivery is one package per milestone, gated on adoption | `tasks.md` is milestone-ordered and each milestone names its adopter; a milestone closes on a merged adoption PR, not on a green build | process (D16) |
| DI is wire | `app.App` fields unexported; `go generate` + `go-generate-check`; `goga/lint` `gogawire` | merge + lint |
| A streaming result outlives the call that returned it | any goga type returning a stream owns the cancel and the span and ends both in `Close`; the returning call has no `defer cancel()`. `goga/lint` `gogastream` flags a `defer cancel()` in a function returning an interface with a `Close` (D15) | compile (API shape) + lint |
| One signal handler per process | only `cli.App.Run` calls `signal.NotifyContext`; `serve`/`mcp`/`grpc` `Run` take a ctx | compile (API shape) |
| wire is `goforj/wire`, not archived `google/wire` | `go.mod` `tool` directive in the template; `depguard` bans `github.com/google/wire` | merge + lint |
| koanf, never Viper | `goga/config` is the only config entry point; `depguard` bans the `spf13/viper` import path | lint |
| Config precedence is defaults→file→env→flags | fixed inside `config.Load`, not derived from option order | compile |
| Probes and `/metrics` are untraced | `serve.New` builds the ops mux outside `otelhttp`; no option can move them in | compile |
| pgx is reached through `goga/database/pgxdb`, and `database/sql` through `goga/database` | `depguard` allows `jackc/pgx` only under `goga/database/pgxdb`; both openers instrument before returning, so neither hands back an uninstrumented handle (D7) | lint |
| goose is the migration engine | `goga/migrate` is the only migration entry point; `depguard` bans other engines | lint |
| Generated code is committed and current | `go-generate-check`: `go generate ./... && git diff --exit-code` | merge |
| Semantic conventions over invented attributes | `telemetry.Instrumentation` takes `attribute.KeyValue` from generated `goga/semconv`; `goga/lint` `gogasemconv` flags string-literal attribute keys | lint |
| testify, not hand-rolled `t.Errorf` | `.golangci.yml` template enables `testifylint` + `usetesting`; gopgql has 172 hand-rolled assertions to migrate | lint |
| gomock, not hand-rolled fakes | `mockgen` `tool` directive + `//go:generate`; freshness via `go-generate-check` | merge |
| One golangci-lint version and invocation | the `go-lint` composite action pins it; projects pin goga | merge |
| goga's own layout: flat, no `pkg/`/`internal/` | `goga/lint` `gogalayout` runs on goga itself | lint |
| An unused adapter never reaches a consumer's build list | M0's minimal-consumer CI job builds a throwaway module importing one module plus one adapter, runs `go mod tidy`, and fails on any require outside an allowlist; `goga/lint` `gogatestimport` bans a portable package's test files importing a sibling adapter (D19) | merge + lint |
| Shared and internal goga packages stay dependency-light | the same CI job; `depguard` limits `goga/telemetry` and `goga/registry` to OpenTelemetry and the standard library (D6, D19) | merge + lint |
| Reaching past a port is visible and degrades gracefully | `As(any) bool` is the only escape hatch and returning `false` is not an error; the conformance suite asserts `As(nil) == false` for every adapter whether it opted in or not (D20, D21) | test |
| Adapters behind a multi-implementation port are interchangeable | `<module>test.RunConformanceTests` — an adapter that does not pass does not ship; ports with one implementation deliberately have no suite (D21) | test |

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
- **[A wrapper hides upstream and must track its churn]** — mitigated by D20's
  `As`, so the escape hatch is one call away and conformance-tested. The module
  this used to be riskiest for, `goga/database`, is no longer exposed to it at
  all: D7 removes the port, so there is no narrow-versus-wide interface to
  balance and `CopyFrom` and `SendBatch` are simply present.
- **[Ports will meet capabilities their adapters do not share, and goga has this
  worse than go-cloud]** — the largest inherited risk, argued in full in D22.
  go-cloud has not solved it in eight years and falls back to a runtime
  `Unimplemented`. gin, chi and `http.ServeMux` differ far more than S3 and GCS
  do, so goga meets it at M2. The mitigation is structural rather than a
  mechanism: every port is held to the narrowest genuinely-common denominator —
  which is why `goga/serve`'s port is `http.Handler` and the routing DSL was
  withdrawn — and a capability-declaration mechanism, if ever needed, goes in at
  construction time rather than being retrofitted.
- **[The config-driven registry path is the one place a wrong adapter name is a
  runtime error]** — the residual cost of D8. Static binding (`wire.Bind`) and
  the typed handle are both compile-checked; only `r.Open[P](ctx, name, …)`
  can fail at startup, and only because configuration is allowed to choose. It is
  bounded — `Register` takes a typed constructor and records the port, so both
  what is *in* the registry and what comes *out* of it are checked — and it is
  mitigated by the error naming every registered adapter and the likely missing
  `Provide(r)` call. The risk worth watching
  is projects reaching for the string path when they meant the typed one, which
  is why D8 states the default explicitly and `goga/lint` flags a
  `(*registry.Registry).Open` whose name argument is a string literal: a literal means the
  adapter *was* known at build time and the typed handle was the right call.
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

- **Unconstructible settings versus the generic registry — closed, and the
  premise was wrong.** This design twice put the question to the owner as a
  trade-off: unexported settings *or* a generic registry, not both. It is now
  proven that they were never in conflict, because they are not about the same
  type. A module's and an adapter's own settings stay **unexported** — `S` is
  inferred from the constructor and no caller ever names it — while the
  driver-facing per-call options are **exported**, because an adapter in another
  package must name them to implement the port. D14 carries the table. Nothing
  here is waiting on an answer, and the two previous rounds spent on this
  question were spent on a false dilemma.

- **Service Weaver's archived upstream — closed by D16.** The question was
  whether to build the `weaver` deployer in v1 against an archived dependency.
  Under the owner's milestone rule it does not arise: `goga/components` has no
  adopting project, so it has no milestone, and the deployer is written when a
  consumer for it exists. The interface is still designed (D12) so that whichever
  deployer arrives first is an adapter and not a rewrite.

- **D8-A: the Go version floor — answered by the owner on 2026-08-04.** The
  design had specified a Go 1.24 floor with package-level generic functions, and
  put the alternative to him rather than absorbing it, because two independent
  investigations found that generic methods change call syntax
  (`r.Open[DB](…)` versus `registry.Open[DB](r, …)`) rather than capability. His
  answer: *"I don't care, use 1.27. Build dependencies from source if
  necessary."* **The spec is now written that way**: `go 1.27` plus
  `toolchain go1.27rc2`, generic methods on `*Registry`, and the from-source
  golangci-lint build as scheduled M0 work (task 0.4d) rather than a
  hypothetical. D8 and D17 carry the decision and the measurements that were
  weighed to reach it.

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
