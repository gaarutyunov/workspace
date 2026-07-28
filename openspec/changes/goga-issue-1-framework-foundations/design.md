## Context

Four Go projects, surveyed against the issue's tool list. Their **divergences**
are the design input, because they separate what a wrapper must absorb from what
is genuinely per-project.

| | gopgql | epos | skill-test/go-service | sysgo |
|---|---|---|---|---|
| shape | library + WASM playground | CLI + registry server | PDF microservice | SysML→Go generator |
| direct deps | 6 | 24 | ~30 | 3 |
| layout | flat root packages | `cmd/` + flat `internal/<domain>` | hexagonal | `cmd/` + `internal/` + public `engine/` |

The findings that drive the decisions below:

- **koanf diverges most.** epos: env → posflag, a callback that returns `("", nil)`
  to skip unchanged flags (inverting apparent precedence), **no file provider, no
  `Unmarshal`, no `koanf:` tags** — five bare getters. go-service: file(yaml) →
  env with `__` as the path separator and `_` literal, a typed struct, mapstructure
  hooks, and `k.Cut()` to hand adapter subtrees to factories. Both authors wrote a
  paragraph explaining precedence, because koanf has none of its own.
- **Telemetry is where the complaint is measurable.** 2 of 4 have none. epos has
  metrics only, and never calls `otel.SetMeterProvider`. go-service has the full
  stack — and keeps `/livez /readyz /healthz /metrics` on the **root** mux
  *outside* the otelhttp wrapper so probes don't pollute traces. That detail is
  exactly what never survives a document.
- **The test tooling holds the most hard-won knowledge**, in three incompatible
  copies: gopgql's `Snapshot`/`Restore` per scenario; epos's hand-rolled `track()`
  explicitly rejecting `testcontainers.CleanupContainer` because hanging cleanup
  off the suite's `T` fills the disk; go-service's init scripts renamed
  `01-`/`02-`/`03-` because `WithInitScripts` keeps basenames and would sort
  fixtures before the schema.
- **CI is drift, not judgement.** golangci-lint is invoked four ways at three
  versions. gopgql and epos carry near-identical docs workflows, and epos's
  `keep_files: true` carries the comment *"Same bug, same fix as
  gaarutyunov/gopgql#24"* — a production bug that propagated by copy-paste.

## Goals / Non-Goals

**Goals:**

- Make the house choices the path of least resistance, at compile time.
- Absorb the CI invocation drift.
- Wrap the *test* tooling, where the knowledge is most expensive and most duplicated.
- Be adoptable **one package at a time**, because the projects that most need
  goga are the ones that need the least of it.

**Non-Goals:**

- Imposing a project layout (D1).
- Wrapping tools with no consumer — gin, sqlc, buf, Service Weaver (D4).
- Migrating the existing projects. That is per-project work, per-issue.
- Replacing sysgo's code generation (D3).

## Decisions

### D1: goga is layout-agnostic

Four positions on layout are live simultaneously: hexagonal (skill-test, the one
project built under a mandatory `AGENTS.md`), flat (three of four repos), the
spf13 skill's explicit rejection of layered packages, and the issue's own "no
`pkg`, no `internal`" for goga itself.

Layout is the most per-project axis in the survey, and `go-project-scaffold`
already declines to decide it on the owner's behalf. Baking one into the library
would collide with sysgo (D3) and would make goga un-adoptable by exactly the
projects that diverge. **goga ships libraries; directories are the project's.**

- *Rejected — hexagonal-first.* go-service's config-driven adapter registry is
  genuinely good and would be reusable, but shipping it as *the* structure makes
  goga an all-or-nothing adoption, which D2 rejects for stronger reasons.

### D2: independent packages, not a framework object

`goga/config`, `goga/telemetry`, `goga/serve`, `goga/client`, `goga/gogatest`,
plus exported **wire ProviderSets** for projects that use wire, plus a thin
optional `goga.Run` that composes them.

The evidence is decisive: **gopgql needs only the test wrappers** — no server, no
config, no telemetry. **sysgo needs none of the runtime wrappers.** **epos needs
config and a metrics-only telemetry subset and has no DI at all.** A `goga.New()`
App object would exclude the two projects with the worst compliance — the ones
goga most needs to reach.

**Every wrapper exposes its underlying object.** `config.Load` returns the
`*koanf.Koanf` alongside the typed struct, because go-service's `k.Cut()` pattern
needs it; the telemetry wrapper returns the providers. This is the cheap
mitigation for the real risk that a wrapper leaks the moment a project needs
something unanticipated.

- *Rejected — a framework object (the Yokai/Kratos shape).* Good when a service
  is the unit of adoption; wrong when two of four consumers are a library and a
  generator.

### D3: sysgo stays the only Go-code generator; goga owns everything else

sysgo already emits `main.go` (cobra), `providers.go` (`wire.NewSet` +
`wire.Bind`), `wire.go` and a handler — and its CI asserts the generated project
builds with a `go.mod` containing **zero requires**. That zero-dependency goal is
exactly what goga inverts, so the two will collide on `main.go` unless this is
settled now.

**goga = library + composite actions + config templates + one skill. sysgo = the
only Go-code generator, retargeted to emit `goga.*` calls.** That makes sysgo's
`main.go.tmpl` collapse from a TODO-riddled cobra skeleton to roughly
`goga.Run(...)`.

**The carve-out that matters:** goga owns the **GitHub Actions,
`.golangci.yml`, `.goreleaser.yaml`, `Makefile` and `go.mod` tool-directive
templates regardless** — because gopgql and epos need those *today* and neither
will ever be generated from a SysML model.

### D4: v1 wraps only what has a consumer

`gin`, `sqlc`, `buf` and Service Weaver appear in **zero `go.mod` files** across
all four projects — verified, not inferred. (The "weaver" in the reference
project is **OTel Weaver**, a Docker-invoked semconv generator, which is a
different tool entirely.)

Building wrappers for tools with no consumer is how a wrapper library acquires
the maintenance burden and the leaks without the payoff. v1 covers config,
telemetry + logging, server/client lifecycle, testcontainers, godog, and the CI
actions. The rest is added when a project asks.

**This narrows the owner's stated list, so it is called out rather than assumed.**

### D5: the skill shrinks, and a contradiction must be resolved first

Today's skills teach *how to use* cobra, koanf and otel. Once goga exists, that
is the library's job, and a skill repeating it is the "nonsense and details
leaking" the issue wants gone. The goga skill says: **which entry point to reach
for, what goga does not enforce, and where the escape hatches are.**

Separately and more urgently: **the workspace's own material contradicts itself.**
The spf13 `go` skill — sitting in the *unmerged* PR #31 — says (verbatim, line
120) *"Anti-pattern to reject: Clean Architecture / DDD layers"* and *"no
`internal/` nesting"*, while `go-project-scaffold` on `main` prescribes
`internal/domain`, `internal/port`, `internal/usecase`, `internal/adapter`. A
model reading both picks one arbitrarily.

**That should be resolved before #31 merges**, and it is not goga's to fix.

### D6: composite actions, not reusable workflows

This follows the owner's own framing — *"workflows can change depending on the
project. But how we launch the tooling can be encapsulated."* A `workflow_call`
reusable workflow owns triggers, jobs and permissions, which are the per-project
part; a composite action owns steps, which are the shared part.

`setup-go` defaults its version to **whatever `go.mod` says**, which kills the
four-Go-versions problem at the root. `go-generate-check` runs
`go generate ./... && git diff --exit-code` — **no repo has this today**, and it
is the check that makes "generated files are committed" true rather than hoped.

Per-project and deliberately not absorbed: triggers, path filters, `permissions`,
`concurrency`, OS matrices, and the genuinely bespoke jobs (sysgo's SysML/Java
pipeline, epos's OCI conformance job, gopgql's WASM smoke build).

## Risks / Trade-offs

- **[A wrapper hides upstream and must track its churn]** — mitigated by D2's
  rule that every wrapper exposes its underlying object, so the escape hatch is
  always one call away.
- **[Adoption may simply not happen]** — goga does not migrate anything. If no
  project adopts it, the compliance numbers do not move. Adoption should be
  scheduled per project, per issue, and the numbers re-measured.
- **[Yokai already does ~70% of the runtime half]** — 17 opt-in modules, project
  templates and workflows, MIT. Its stack is wrong on every axis the owner cares
  about (fx not wire, Viper not koanf, Echo not stdlib, no cobra, no wrapped test
  tooling), so it is not a substitute — but **its module decomposition should be
  read before finalising goga's package boundaries.**
- **[The unserved half is the valuable half]** — nobody ships wrapped test
  tooling or encapsulated CI invocation. That is also where the owner's own
  projects diverge most. If v1 has to be cut, cut the runtime wrappers, not
  these.

## Open Questions

- Does the owner accept D4's narrowing (dropping gin/sqlc/buf/Service Weaver
  from v1)?
- Which project adopts goga first? gopgql needs only `gogatest` and would be the
  cheapest proof; epos would exercise config + partial telemetry and is the
  better test of D2.
