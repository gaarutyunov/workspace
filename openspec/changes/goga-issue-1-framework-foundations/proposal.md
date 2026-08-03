## Why

The complaint in the issue is exact: *"you need to always steer the model into
using them and always add skills about them. Otherwise, the model just uses raw
Go."* A survey of the Go projects measures it.

**The house "non-negotiables" hold about a quarter of the time.** Across gopgql,
epos, skill-test/go-service, sysgo and mcp-anything: cobra 3/5, koanf 3/5 *with
three incompatible source arrangements*, wire 1/5, gomock 2/5, testify 3/5
(gopgql has **172** hand-rolled `t.Errorf`/`t.Fatalf`, against the workspace's own
rule). The OpenTelemetry SDK appears in 3/5, but only 2 configure traces, metrics
and logs together — epos has metrics only and never installs its meter provider.

And the experiment has already been run. **`skill-test` is the only project with
its own `AGENTS.md`, and the only project that follows the conventions.**
`gopgql` and `sysgo` have no `CLAUDE.md`, no `AGENTS.md`, no `.claude/` at all.
The rules live in the workspace repo, and `projects/.gitignore` is `*`, so they
can never reach a project checkout. Documentation-as-mechanism fails on **reach**
before it gets a chance to fail on content.

So the owner's instinct is right, and the reason is sharper than "add a
framework": an API constrains at compile time, a linter at edit time, CI at merge
time, and a document constrains only where it is physically present and only when
someone reads it.

The survey also found tools already in use that no guidance covers, which is the
same failure from the other end: **pgx** in three projects, the **MCP SDK** in
two (at two versions, neither instrumented), **goose** in one — all invisible to
the house rules today.

## What Changes

- **`goga` covers the whole tool list in the issue** — cobra, koanf, wire, gin,
  otel + prometheus + slog, testcontainers, godog, testify, gomock,
  golangci-lint, goreleaser, oapi-codegen, buf, weaver, sqlc, pgx — plus goose
  and the MCP SDK, which the survey found already in use. Scope comes from the
  tool list, not from today's `go.mod` files; the survey records for each tool
  whether its consumer is **current** or **anticipated** (design D4).
- **`goga` is a set of independent packages, not a framework object** (design
  D2): `config`, `telemetry`, `serve`, `client`, `database`, `migrate`, `mcp`,
  `cli`, `grpc`, `components`, `semconv`, `di`, `lint`, `gogatest`, plus a thin
  `app` that composes them. The root `goga` package is a leaf holding
  only `Option` and `Apply`: every module imports it and the composition root
  imports every module, so those two cannot be the same package.
  Every wrapper **exposes its underlying object**, so a project that needs the
  raw `*koanf.Koanf`, the `*pgxpool.Pool` or the real SDK server is never
  trapped. Independence is also what makes the milestones below possible: a
  package is the unit of delivery because it is the unit a project can adopt.
- **Delivery is one package per milestone, gated on a real adoption** (design
  D16), which is the owner's instruction: *"We shouldn't deliver everything at
  once… Each milestone we will deliver one package. I will carefully review it.
  We will migrate gopgql and some other project to it and then continue to the
  next."* `tasks.md` is ordered by milestone, not by module, and each milestone
  names the project that adopts it. A milestone closes when that adoption is
  merged — not when the package builds.
- **Every milestone carries all six parts; splitting functionality from
  enforcement is not allowed** (design D18). The owner's definition of done:
  implementation, tests, skill reference, **a linter** — custom-written where
  nothing off the shelf fits, enforcing that project code does not use a wrapped
  dependency directly — a **CI action** where the milestone introduces a tool that
  runs in CI, and a **migration of a real project**, which is a separate task that
  nonetheless **blocks the milestone's merge**. *This reverses the previous
  revision's structure, which collected all linting into M11 and the whole skill
  into M13 — so eleven of fourteen milestones shipped an API whose conventions
  nothing checked, which is the exact failure this proposal is written against.*
  `goga/lint` and the skill stop being milestones and become columns; M0 grows
  the plugin scaffold and the skill skeleton so that M1 has somewhere to write.
- **goga's Go floor is 1.24, and the Go 1.27 question is put to the owner rather
  than decided quietly** (design D17, open question D8-A). The owner instructed
  that the registry use Go 1.27 generic methods — *"even if it's alpha or beta
  version"*. Two independent investigations found the premise does not hold: the
  registry never needed them. The normative implementation compiles **and runs**
  on stock `go1.26.4` at language version `go 1.22`, and the 1.27 form differs in
  exactly four lines — `r.Open[DB](…)` instead of `registry.Open[DB](r, …)` — with
  the call site consumers actually use byte-identical either way. Requiring 1.27
  would propagate a pre-release toolchain into every consumer's `go.mod`
  (silently under `GOTOOLCHAIN=auto`, as a hard failure under
  `GOTOOLCHAIN=local`) and would mean **the current golangci-lint release cannot
  lint the code at all**, forcing a from-source build against a newer
  `golang.org/x/tools` for as long as the RC lasts. This spec therefore specifies
  1.24 and **flags the choice for the owner at the approval gate**; M0 flips it
  in either direction for the cost of that four-line diff.
- **Every module that does anything at runtime has telemetry, with no
  exemptions** (design D6). This is the
  owner's rule — *"Every part of the framework must have telemetry"* — and it is
  an invariant of this spec, not a feature of some modules. It is enforced
  structurally: portable types have unexported fields and no exported
  constructor, so no goga constructor returns an uninstrumented object, and there
  is no `WithoutTelemetry` option anywhere. The invariant is stated over the
  modules that perform a runtime operation; `semconv` (generated constants),
  `lint` (analysers) and `di` (provider sets) have no operation to instrument,
  and a test asserts the instrumented set is exactly the rest.
- **Variadic functional options everywhere; no parameter structs, and no
  exception for adapters** (design D14). Each module declares an **unexported**
  `settings` struct — no other package can name it, construct it or embed it —
  plus an exported `Option` alias over it. An adapter in its own package reads
  the *module's* resolved values through an exported **accessor interface**
  (`serve/driver.Options`, `mcp.Settings`), and only where an adapter reads
  anything at all. An adapter's **own** settings type is inferred from its
  constructor, so that struct stays unexported too — a consumer configures the
  adapter correctly while being unable to name it. *The owner asked whether
  variadic options could themselves be generic per adapter, so that even the
  dynamic adapter case needs no struct param. The answer is **both, split by
  path**: on every path where the adapter is known at build time, options are
  fully static and no struct param appears; on the path where a runtime string
  chooses the adapter, configuration necessarily arrives as data, because a type
  cannot be recovered from a string. That is the case the owner said he would
  allow, and it is unavoidable rather than chosen.* **One exported struct does
  exist, on the driver side** — the per-call options a port hands an adapter —
  because an adapter in another package must name them to implement the port, and
  the conformance suite must construct them. That is a different boundary, not an
  exception: no goga entry point accepts one from a caller.
- **A database module with no port — reversed in this revision** (design D7).
  The previous version specified a portable `*database.DB` over a narrow
  `driver.DB` with two adapters. Reading `gocloud.dev` properly settles it the
  other way: an eight-year portability library that ships driver ports for object
  storage, pub/sub, document stores, secrets and runtime config **declined to
  build one for SQL** — `postgres/postgres.go` returns `*sql.DB` and instruments
  by wrapping the driver underneath. The reason is that pgx's value over
  `database/sql` *is* what a common interface erases, and gopgql is named here as
  needing exactly that. So v1 ships two honest types: `goga/database` returning an
  otelsql-wrapped `*sql.DB` for goose, sqlc and everything that speaks the
  standard interface, and `goga/database/pgxdb` returning an otelpgx-instrumented
  `*pgxpool.Pool` with nothing erased. Both are instrumented at construction, so
  the telemetry invariant is unchanged; what goes away is the pretence that the
  two are swappable.
- **`goga/registry` is back in v1 — and it never needed generic methods**
  (design D8). It was deferred a revision ago *because* Go lacked them; that
  reasoning is superseded rather than merely outdated. `registry.Register` stores
  a typed constructor `func(S) (P, error)` under a **plain adapter name**, with
  both type parameters inferred, so no caller ever names the settings type and it
  can stay unexported. Three ways to bind a port to an adapter, in order of
  preference: `wire.Bind` when the adapter is known at build time — which needs no
  registry at all, and is what `gocloud.dev`'s own composition roots use;
  the typed handle `Adapter[P, S].Open(cfg, opts…)` when the adapter is known but
  its options must be set; and `registry.Open[P](r, name, cfg)` only when
  configuration must choose at run time. **Keys are plain names, not URL schemes**
  — the URL-opener indirection solves twelve-factor late binding, which goga does
  not have, since its adapters are chosen in the composition root at build time.
  **One thing the owner described is not expressible**: recovering the settings
  type into a type parameter at a `name`-keyed call site, because the adapter is
  chosen by a runtime string. And going the other way — from a port down to the
  concrete adapter — is `As`, a runtime assertion by necessity rather than by
  choice. Full evidence in design D8.
- **goose is the migration engine** (design D10), pinned as a house decision,
  with embedded migrations by default, a boot-time advisory lock so two replicas
  cannot both migrate, and `Pending()` as a readiness input.
- **The MCP SDK is a first-class module** (design D12's sibling, `goga/mcp`),
  because gopgql has an MCP server today and sysgo will have one. Every tool
  call, resource read and prompt render is a span, added by `AddTool` rather than
  by the tool author.
- **DI is wire, and it is enforced** (design D9). `github.com/goforj/wire` — the
  live fork; `google/wire` is archived. Every module exports a `ProviderSet`;
  `app.App`'s fields are unexported so the practical way to build one is a
  generated injector; and `go-generate-check` makes a stale `wire_gen.go` a red
  build. The design settles the four wire mechanics that otherwise bite on day
  one — cleanups must be `func()`, wire cannot supply variadic options, providers
  take named types rather than bare `string`, and a generic constructor is
  instantiated by the project.
- **Composite GitHub Actions**, the half nothing in the ecosystem ships:
  `setup-go`, `go-lint`, `go-test`, `go-test-integration`, **`go-generate-check`**,
  `go-vuln`, `go-release`, `pages-deploy`. Today golangci-lint alone is invoked
  **four different ways at three different versions**.
- **The test tooling is wrapped**, where divergence is worst and knowledge most
  expensive: three incompatible testcontainers lifecycle strategies, and a godog
  bootstrap copy-pasted **5× in gopgql and 8× in epos**.
- **`goga` is layout-agnostic** (design D1). It ships no directory structure and
  no opinion about hexagonal.
- **One skill, and a much smaller one**, carrying the routing table and the
  **enforcement matrix** — not a list of conventions goga leaves to the reader.
  There is no such list: if a convention cannot be enforced, that is a goga
  defect (design D5).

## Delivery: the milestones

Design D16 has the reasoning and the full table; this is the order and the
adopter, because that is what the owner has to agree to. Every milestone is one
package, none starts until the previous one's adoption is merged, and every one
from M1 lands with all six parts of D18 — implementation, tests, skill section,
linter rule, CI action where one is needed, and a merged adoption PR.

| # | package | adopter, then second |
|---|---|---|
| M0 | *(the repo itself — `go.mod` on Go 1.24, layout, root `goga`, **`goga/registry`**, the **lint plugin scaffold**, the **skill skeleton**, lint/release config, actions)* | goga |
| M1 | `goga/telemetry` (+ generated `goga/semconv`) | **gopgql**, then **epos** |
| M2 | `goga/serve` (+ `driver`, the stdlib listener, `servetest`) | **epos**, then **gopgql** |
| M3 | `goga/config` | **epos**, then **skill-test/go-service**, **mcp-anything** |
| M4 | `goga/database` (+ `pgxdb`, `sqlcdb`) | **gopgql**; **codiq** later |
| M5 | `goga/migrate` | **gopgql** |
| M6 | `goga/mcp` | **gopgql**, then **mcp-anything** |
| M7 | `goga/gogatest` | **gopgql**, then **epos** |
| M8 | `goga/cli` | **epos**, then **gopgql** |
| M9 | `goga/di` + `goga/app` (+ `go-generate-check`) | **skill-test/go-service**, then **sysgo** |
| M10 | `goga/client` | **skill-test/go-service**, then **mcp-anything** |
| M11 | *(dissolved — `go-vuln`, `go-release`, `pages-deploy` only)* | **gopgql**, then **epos** |
| M12 | `goga/codegen` templates + `goga/grpc` | **skill-test/go-service**; **codiq** for sqlc/buf |
| M13 | *(dissolved — the skill's closing audit only)* | every adopting project |
| — | `goga/components` | **no consumer today** — does not start until there is one |
| — | `goga/registry` | ships in M0; a leaf every adapter-bearing module uses |

Telemetry, HTTP, config and postgres are in the owner's own order, with the
owner's own adopters. The rest follow the survey's consumer evidence.

**The Go spec review reached this independently, before the owner said it.** It
recommended approving the spec but not building it as one unit, because *seven of
the fifteen module surfaces have no consumer that can validate them* while it
found five defects — three compile-level, two runtime-level — in the eight that
do, which are the surfaces that had the most design attention. This proposal
records the agreement rather than claiming the idea; where they differ the
owner's is finer, one package rather than one eight-package slice.

## Capabilities

### New Capabilities

Each capability names the milestone that delivers it, at the top of its delta
spec. Where a capability spans milestones — service lifecycle, code generation,
CI actions, the spec-wide conventions — each requirement names its own.

- `goga-api-conventions` *(spec-wide; each requirement lands with the first
  module that has it)*: variadic functional options with no parameter structs,
  telemetry in every module with no exemptions, and an escape hatch to the
  underlying object from every wrapper.
- `goga-adapter-resolution` *(the shared `goga/registry` at M0; per-module
  resolution with each adapter-bearing module, from M1)*: how a module selects an
  adapter — self-registration, one duplicate rule, one unknown-adapter error,
  optional dependencies, instrumented resolution — plus the generic cast to an
  adapter's concrete type and the typed per-adapter options and configuration
  that ride on the same seam.
- `goga-config` *(M3)*: configuration loading with an explicit, documented
  precedence, returning both a typed struct and the raw koanf.
- `goga-observability` *(M1, and one requirement at M2)*: telemetry and logging
  wired once, plus the per-module instrumentation handle that makes the telemetry
  invariant checkable.
- `goga-service-lifecycle` *(M2, M8, M9, M10)*: the cobra command-line entry
  point, HTTP server and client construction, signal handling, graceful shutdown,
  and the probe/metrics endpoints kept **off** the traced router.
- `goga-http-router` *(M2)*: the serving seam — any standard handler, so gin, chi
  are interchangeable adapters and instrumentation is attached once, above them.
- `goga-database` *(M4)*: two instrumented handles rather than a port — the
  standard `*sql.DB` and pgx's own pool — and the `database/sql` path the migration engine
  needs.
- `goga-migrations` *(M5)*: goose as the house migration engine, with embedded
  migrations, a boot lock, and pending-migration reporting for readiness.
- `goga-mcp` *(M6)*: the MCP server and client wrapper, with every tool call,
  resource read and prompt render instrumented by the wrapper.
- `goga-dependency-injection` *(M9)*: wire as the house DI mechanism, with
  exported ProviderSets per module and a stated enforcement path.
- `goga-code-generation` *(M9 for wiring freshness, M12 for the rest)*: the
  generation contract for oapi-codegen, sqlc, buf and OTel Weaver — pinned tool
  directives, config templates, one `go:generate` entry point, and the runtime
  seams the generated code compiles against.
- `goga-components` *(no milestone yet — starts when a consumer exists)*: the
  component and deployment surface, with Service Weaver as one deployer behind
  the module's own deployer table.
- `goga-testing` *(M7)*: testcontainers fixtures, an MCP test harness, recorded
  telemetry, and a godog harness, replacing the copy-paste.
- `goga-ci-actions` *(M0, M9, M11)*: the composite actions, including the
  generation-freshness check that **no repo has today** and that is the
  enforcement point for wire, sqlc, buf, oapi-codegen, Weaver and mockgen alike.
- `goga-skill` *(M13)*: the single skill — the routing table and the enforcement
  matrix.

### Modified Capabilities

<!-- goga is greenfield (one commit, a one-line README). The workspace's rules
     and skills are affected but live outside openspec/specs/; the guidance
     contradiction they contain is recorded in design D13. -->

## Impact

- **New repo content**: `goga` is currently empty. Everything here is additive.
- **Every adopting project's `go.mod` moves to goga's floor of Go 1.24** (D17),
  because a module cannot require a lower Go version than something it depends
  on. That is gopgql, epos, skill-test/go-service, mcp-anything and sysgo, from
  their first adopted package onward. At 1.24 this is a formality — all five are
  already at or above it. It is called out because the same mechanism is what
  makes the Go 1.27 question (D8-A) consequential: at 1.27 the identical
  propagation would put a pre-release toolchain into all five.
- **Two independent spikes back D8, D14 and D17**, both built with **go1.27rc2**
  and kept outside the repository as evidence rather than shipped code. Each has
  one directory per question and compiles its negative cases to confirm they
  fail — including that an interface cannot declare a generic method, which is a
  hard constraint every port in this design was checked against. The second spike
  additionally rewrote the normative registry with the two generic *methods* as
  package-level generic *functions* and verified it compiles **and runs** on
  stock `go1.26.4` under `GOTOOLCHAIN=local`, which is the evidence behind the
  1.24 floor.
- **The go-cloud study backing D7, D19, D20, D21 and D22** was done against
  `github.com/google/go-cloud` at commit `35f55f24` (2026-08-04), and every claim
  in those decisions cites a file and line so a reviewer can check it. It
  includes a measured minimal-consumer build showing that one module plus
  blank-imported adapters keeps unused adapter dependencies out of a consumer's
  build list — and the three accidental leaks that got past that in go-cloud
  itself, which D19 turns into goga's rules and a CI check.
- **`.github/actions/*`** in the goga repo, referenced as
  `gaarutyunov/goga/.github/actions/<name>@v1`.
- **Existing projects are migrated one package at a time, and that migration is
  the gate** (D16). Each milestone's adoption is its own PR in the adopting
  project's repo, and the next milestone does not start until it is merged. This
  is a change from the previous revision, which scheduled adoption as a final
  section of work after fifteen modules were built.
- **`gopgql` is the first adopter**, per the owner, and the most frequent one. It
  is the only project with pgx, goose and the MCP SDK all three — all
  uninstrumented today — plus the 5× duplicated godog bootstrap, so it is the
  named adopter for `telemetry`, `database`, `migrate`, `mcp` and `gogatest`.
- **`epos` is the second**, and the owner named it for HTTP and config. It has
  metrics-only telemetry with no meter provider installed, calls `Execute()` with
  no signal handling, and its flag callback inverts its own config precedence.
- **`skill-test/go-service`** adopts gin as its router, per the owner — directly, as a standard handler passed to `goga/serve`, since D22 removes the router adapter layer. It
  serves on the standard library today — while **`sysgo` already requires gin
  directly** and generates gin handlers from the same code generator. Two
  projects, one generator, two routers is the clearest case in the survey for the
  router seam.
- **`sysgo` also requires the Temporal SDK directly**, which is on no house tool
  list. It is flagged rather than folded in: goga should not acquire a workflow
  engine by accident.
- **`codiq`** does not exist yet (checked 2026-07-30). It is the anticipated
  consumer for sqlc and buf, which sets their sequencing, not their scope.
- **`sysgo`** stops emitting cobra/wire skeletons and emits `goga.*` calls
  instead (design D3) — a *reduction* in what sysgo generates — and gains an MCP
  server built on `goga/mcp`.
- **`mcp-anything`** is the widest dependency sample in the house and the source
  of several house choices adopted here: `exaring/otelpgx`, OTel `autoexport` /
  `autoprop`, `gobreaker`, and the proof that a custom golangci-lint plugin
  module is buildable in-house — which is what makes D5's lint-time enforcement
  real rather than aspirational.
- **`github.com/google/wire` is archived**; the house pin is
  `github.com/goforj/wire`, already used by `skill-test/go-service`. Any project
  told to "add wire" must be told which one.
- **`ServiceWeaver/weaver` is archived** (checked 2026-07-30). It stays in scope
  behind `goga/components`' deployer table, so replacing it is an adapter swap.
  Under D16 the module has no milestone until a project adopts it, which also
  closes the question of whether to write a deployer against an archived
  dependency with nobody to use it. **This is the one place the owner's two
  instructions pull against each other** — Weaver is in scope by one and gate-less
  by the other — and the resolution is a schedule, not a scope change.
- **The workspace's own Go guidance contradicts itself on `main` right now**
  (design D13). Both skills are merged — the spf13 `go` skill landed in
  `37bd574` (workspace#31) — so this is a defect in guidance already in force,
  not a merge to pre-empt. They disagree over `internal/` **as the default
  home**: `go-project-scaffold` prescribes `internal/app` / `internal/config` /
  `internal/server` / `internal/<feature>` plus `pkg/`; the spf13 skill calls
  relying on `internal/` by default an anti-pattern and prescribes top-level
  packages one level deep. (Not the hexagonal question —
  `go-project-scaffold` explicitly declines to decide that.) The widened scope
  settles two thirds of it: goga's adapter shape decides that ports sit adjacent
  to what they serve and adapters are technology-named leaves with no layer
  directories, and `go-project-scaffold` already names sysgo as the enforcement
  point. What is left for the owner is the default home for a service's own
  non-adapter code. D1 keeps goga itself out of the argument.
