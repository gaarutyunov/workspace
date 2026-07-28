## Why

The complaint in the issue is exact: *"you need to always steer the model into
using them and always add skills about them. Otherwise, the model just uses raw
Go."* A survey of the four Go projects measures it.

**The house "non-negotiables" hold about a quarter of the time.** Across gopgql,
epos, skill-test/go-service and sysgo: cobra 3/4, koanf 2/4 *with incompatible
semantics*, wire 1/4, OpenTelemetry 1/4, testify 2/4 (gopgql has **172**
hand-rolled `t.Errorf`/`t.Fatalf`, against the workspace's own rule).

And the experiment has already been run. **`skill-test` is the only project with
its own `AGENTS.md`, and the only project that follows the conventions.**
`gopgql` and `sysgo` have no `CLAUDE.md`, no `AGENTS.md`, no `.claude/` at all.
The rules live in the workspace repo, and `projects/.gitignore` is `*`, so they
can never reach a project checkout. Documentation-as-mechanism fails on **reach**
before it gets a chance to fail on content.

So the owner's instinct is right, and the reason is sharper than "add a
framework": an API constrains at compile time, CI constrains at merge time, and
a document constrains only where it is physically present and only when someone
reads it.

## What Changes

- **`goga` is a set of independent packages, not a framework object** (design
  D2) — `goga/config`, `goga/telemetry`, `goga/serve`, `goga/client`,
  `goga/gogatest`. Every wrapper **exposes its underlying object**, so a project
  that needs the raw `*koanf.Koanf` or the real provider is never trapped.
- **Composite GitHub Actions**, which is the half nothing in the ecosystem
  ships: `setup-go`, `go-lint`, `go-test`, `go-test-integration`,
  **`go-generate-check`**, `go-vuln`, `go-release`, `pages-deploy`. Today one
  tool — golangci-lint — is invoked **four different ways at three different
  versions** across four repos. That is drift, not per-project judgement.
- **The test tooling is wrapped**, which the survey found is where divergence is
  worst and knowledge most expensive: three incompatible testcontainers
  lifecycle strategies, and a godog bootstrap copy-pasted **5× in gopgql and 8×
  in epos** with no shared helper in either.
- **`goga` is layout-agnostic** (design D1). It ships no directory structure and
  no opinion about hexagonal.
- **One skill, and a much smaller one.** Today's skills teach *how to use cobra,
  koanf, otel*. If goga exists that is the library's job; the skill shrinks to
  which entry point to reach for, what goga does **not** enforce, and where the
  escape hatches are.
- **v1 is scoped to tools that have a consumer.** `gin`, `sqlc`, `buf` and
  Service Weaver appear in **zero** `go.mod` files across all four projects
  (verified). Wrapping them buys the maintenance cost and the leak risk with no
  payoff. They are deferred until a project asks.

## Capabilities

### New Capabilities

- `goga-config`: configuration loading with an explicit, documented precedence,
  returning both a typed struct and the raw koanf.
- `goga-observability`: telemetry and logging wired once — the tools 1 of 4
  projects manages to configure today.
- `goga-service-lifecycle`: HTTP server and client construction, signal
  handling, graceful shutdown, and the probe/metrics endpoints kept **off** the
  traced router.
- `goga-testing`: testcontainers fixtures and a godog harness, replacing the
  copy-paste.
- `goga-ci-actions`: the composite actions, including the generation-freshness
  check that **no repo has today**.
- `goga-skill`: the single skill, and what it deliberately stops saying.

### Modified Capabilities

<!-- goga is greenfield (one commit, a one-line README). The workspace's rules
     and skills are affected but live outside openspec/specs/; the contradiction
     they contain is recorded in design D5. -->

## Impact

- **New repo content**: `goga` is currently empty. Everything here is additive.
- **`.github/actions/*`** in the goga repo, referenced as
  `gaarutyunov/goga/.github/actions/<name>@v1`.
- **Existing projects are not migrated by this change.** Adoption is per-project
  and per-issue; goga must be adoptable one package at a time, which is the main
  argument for D2.
- **`sysgo`** stops emitting cobra/wire skeletons and emits `goga.*` calls
  instead (design D3) — a *reduction* in what sysgo generates.
- **The workspace skills contradict each other today** (design D5): the spf13
  `go` skill about to land in PR #31 calls `internal/`-layered packages an
  anti-pattern, while `go-project-scaffold` prescribes `internal/domain`,
  `internal/port`. **That should be resolved before #31 merges**, independently
  of goga.
