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
  `cli`, `grpc`, `components`, `semconv`, `registry`, `di`, `lint`, `gogatest`,
  plus a thin `app` that composes them. The root `goga` package is a leaf holding
  only `Option` and `Apply`: every module imports it and the composition root
  imports every module, so those two cannot be the same package.
  Every wrapper **exposes its underlying object**, so a project that needs the
  raw `*koanf.Koanf`, the `*pgxpool.Pool` or the real SDK server is never
  trapped.
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
- **Variadic functional options everywhere; no parameter structs** (design D14).
  Each module declares an **opaque** `Settings` — exported so an adapter in its
  own package can name it in an `Opener` signature, with no exported field and no
  exported constructor — plus an exported `Option` alias. No goga entry point
  accepts a `Settings`, so options are the only form that does anything, and a
  lint rule covers project code.
- **A database module with multiple adapters, built on pgx** (design D7),
  following `gocloud.dev`'s portable-API/driver split: a portable `*database.DB`
  that owns the telemetry, a narrow `driver.DB` that adapters implement, and
  URL-scheme selection by blank import. pgx is the first adapter, using
  `exaring/otelpgx` — already the house choice in mcp-anything — and a
  `database/sql`-backed `sqldb` adapter is the second, in v1, because a portable
  API with one implementation is an untested claim.
- **One generic registry for all adapters** (design D8). `goga/registry` is a
  single generic implementation instantiated per portable type — database
  drivers, HTTP routers, telemetry exporters, MCP transports, component
  deployers — instead of a hand-rolled map per module.
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

## Capabilities

### New Capabilities

- `goga-api-conventions`: the spec-wide invariants — variadic functional options
  with no parameter structs, telemetry in every module with no exemptions, and an
  escape hatch to the underlying object from every wrapper.
- `goga-adapter-registry`: one generic registry implementation used by every
  adapter-bearing module.
- `goga-config`: configuration loading with an explicit, documented precedence,
  returning both a typed struct and the raw koanf.
- `goga-observability`: telemetry and logging wired once, plus the per-module
  instrumentation handle that makes the telemetry invariant checkable.
- `goga-service-lifecycle`: the cobra command-line entry point, HTTP server and
  client construction, signal handling, graceful shutdown, and the probe/metrics
  endpoints kept **off** the traced router.
- `goga-http-router`: the router seam, so the standard library, gin and chi are
  interchangeable adapters and instrumentation is attached once, above them.
- `goga-database`: the portable database API with pluggable adapters, pgx as the
  PostgreSQL adapter, and the `database/sql` bridge the migration engine needs.
- `goga-migrations`: goose as the house migration engine, with embedded
  migrations, a boot lock, and pending-migration reporting for readiness.
- `goga-mcp`: the MCP server and client wrapper, with every tool call, resource
  read and prompt render instrumented by the wrapper.
- `goga-dependency-injection`: wire as the house DI mechanism, with exported
  ProviderSets per module and a stated enforcement path.
- `goga-code-generation`: the generation contract for oapi-codegen, sqlc, buf and
  OTel Weaver — pinned tool directives, config templates, one `go:generate` entry
  point, and the runtime seams the generated code compiles against.
- `goga-components`: the component and deployment surface, with Service Weaver as
  one deployer behind the registry.
- `goga-testing`: testcontainers fixtures, an MCP test harness, recorded
  telemetry, and a godog harness, replacing the copy-paste.
- `goga-ci-actions`: the composite actions, including the generation-freshness
  check that **no repo has today** and that is the enforcement point for wire,
  sqlc, buf, oapi-codegen, Weaver and mockgen alike.
- `goga-skill`: the single skill — the routing table and the enforcement matrix.

### Modified Capabilities

<!-- goga is greenfield (one commit, a one-line README). The workspace's rules
     and skills are affected but live outside openspec/specs/; the guidance
     contradiction they contain is recorded in design D13. -->

## Impact

- **New repo content**: `goga` is currently empty. Everything here is additive.
- **`.github/actions/*`** in the goga repo, referenced as
  `gaarutyunov/goga/.github/actions/<name>@v1`.
- **Existing projects are not migrated by this change.** Adoption is per-project
  and per-issue; goga must be adoptable one package at a time, which is the main
  argument for D2.
- **`gopgql` is the first adopter**, per the owner. It is the only project with
  pgx, goose and the MCP SDK all three — all uninstrumented today — plus the 5×
  duplicated godog bootstrap, so it exercises `database`, `migrate`, `mcp` and
  `gogatest` at once.
- **`skill-test/go-service`** gains gin as its router adapter, per the owner. It
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
  behind `goga/components`' deployer registry, so replacing it is an adapter
  swap; whether the `weaver` deployer is built in v1 is an open question in the
  design.
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
