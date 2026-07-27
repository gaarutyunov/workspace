---
name: go-project-scaffold
description: >
  The house rules for Go projects in this workspace — how a new service is
  scaffolded, and the standard existing code is reviewed and refactored against.
  Covers the non-negotiables: code generation over hand-rolling (oapi-codegen,
  wire, mockgen, Weaver), OpenTelemetry semantic conventions, cobra for CLIs,
  koanf for configuration (never Viper), the api/cmd/internal/pkg/tests layout,
  and the TDD loop with testcontainers. Use it whenever a Go project is being
  started, a Go service is being reviewed or refactored, or a decision about
  Go project structure, configuration, DI, telemetry or code generation comes
  up. Examples: "scaffold a Go service", "review this Go project", "does this
  follow our Go conventions", "add config to this service", "wire up DI".
---

# Go projects: the house standard

These are the conventions every Go project here follows. They are derived from a
worked reference implementation — `gaarutyunov/skill-test` PR #2, a PDF report
microservice — and that repository is the tie-breaker when this document and
reality disagree.

**This is not only a scaffolding guide.** Use it three ways:

- **Scaffolding** a new service — follow it top to bottom.
- **Reviewing** existing code — [`references/review.md`](references/review.md)
  is the checklist.
- **Refactoring** — the same checklist, applied to what is already there.

## Non-negotiable

These are not per-project choices. A Go project here uses all of them:

| | Why it is not optional |
|---|---|
| **Code generation over hand-rolling** | Anything derivable from a spec is generated from it: HTTP models/clients/servers from OpenAPI, DI from Wire, mocks from interfaces, telemetry attributes from a Weaver registry. Hand-written equivalents drift from the spec silently. |
| **OpenTelemetry semantic conventions** | Instrumentation uses the *official* conventions where they exist, and a Weaver registry for what genuinely does not. Inventing an attribute that already has a standard name makes the telemetry unjoinable. |
| **`cobra`** for the command line | One command-construction pattern across every binary. |
| **`koanf`** for configuration | **Never Viper**, in any project. See `.claude/rules/go-cli-koanf.md` for the call-by-call translation. |
| **`wire`** for dependency injection | `github.com/goforj/wire`. The graph is compile-time and generated; no service locator, no `init()` wiring. |

## Hexagonal architecture is a judgement call — and not yours

Hexagonal (`domain` / `port` / `usecase` / `adapter`) is **valuable but optional**.
A project with a narrow scope is made *worse* by it: `gopgql` is a library with
one job and would gain nothing but indirection. A complex service with several
interchangeable backings — `epos` — is where it pays.

**Do not decide this on the owner's behalf.** If the project is new and nobody
has said, scaffold it *flat* (`internal/<feature>`) and say plainly in the PR
that hexagonal was not applied and why. A layout the owner has to unpick is more
expensive than one they have to extend.

This will eventually be enforced by `sysgo` rather than by judgement; until then,
ask on the issue rather than guessing.

## Layout

```text
api/                 # openapi.yaml — the spec code is generated from
cmd/                 # cobra commands: root, serve, version. No logic.
internal/            # everything private to the service
  app/               # wire providers, the composition root, telemetry setup
  config/            # koanf loading + the strongly-typed Config
  server/            # generated HTTP server + hand-written handlers
  …                  # hexagonal: domain/port/usecase/adapter — see above
pkg/                 # importable by other projects
  api/               # generated clients, shared HTTP client construction
  semconv/           # generated telemetry attributes + build info
tests/integration/   # //go:build integration — testcontainers, no mocks
```

`main.go` at the root does one thing: call `cmd.Execute()`.

The integration suite **must** carry `//go:build integration` so `go test ./...`
stays fast and unit-only.

## Code generation

Generators are declared as **module tool dependencies** (Go 1.24+ `tool`
directives in `go.mod`), so every contributor and CI runs the same versions
without a separate install step:

```go.mod
tool (
	github.com/goforj/wire/cmd/wire
	github.com/oapi-codegen/oapi-codegen/v2/cmd/oapi-codegen
	go.uber.org/mock/mockgen
)
```

and invoked from a single `generate.go` at the module root:

```go
//go:generate go tool oapi-codegen -config pkg/api/upstream/cfg.yaml api/openapi.yaml
//go:generate go tool oapi-codegen -config internal/server/cfg.yaml api/openapi.yaml
//go:generate go tool wire gen ./internal/app
//go:generate go tool mockgen -destination internal/port/mock/mock_port.go -package mock <module>/internal/port StudentRepository,ReportGenerator
```

Weaver runs through Docker (`otel/weaver`) rather than as a tool dependency,
because it is not a Go program — `make semconv`.

**Generated files are committed** and never hand-edited. `gofmt` targets exclude
`*.gen.go` and `wire_gen.go`.

## Telemetry

1. **Official conventions first.** Check `go.opentelemetry.io/otel/semconv/<version>`
   and the [semantic-conventions registry](https://github.com/open-telemetry/semantic-conventions/tree/main/model)
   before inventing anything. Use `service.*`, `vcs.*`, `http.*`, `url.*`,
   `server.*`, `error.type`, `code.*` when they fit.
2. **A Weaver registry for what is genuinely project-specific** — `semconv/registry/*.yaml`,
   generated into `pkg/semconv`. Only concepts with no official convention
   (`report.*`, `student.id`, `adapter.*`) belong there.
3. **Build info comes from git via LDFLAGS**, injected into `pkg/semconv`
   (`Version`, `Revision`, `Tag`, `Repository`, `Date`) and reported through the
   official `service.*` / `vcs.*` attributes.
4. Outbound HTTP emits **all three signals** — spans with `traceparent`
   propagation, `http.client.*` metrics, and structured `slog` logs for retries
   and failures.

## Configuration

`koanf`, loaded **in explicit precedence order** — defaults, then file, then
environment — because koanf merges in call order and has no implicit precedence
table. That explicitness is the reason it is preferred over Viper.

```go
k := koanf.New(".")
k.Load(file.Provider(path), yaml.Parser())
k.Load(env.Provider("REPORT_", ".", normalizeEnvKey), nil)
k.Unmarshal("", &cfg)   // into a strongly-typed Config with `koanf:"…"` tags
```

Where a port has interchangeable implementations, select them **by name in
config** through an adapter registry, so switching backing services is a config
edit rather than a rebuild:

```yaml
adapters:
  student_repository:
    type: http
    http: { base_url: "…", retries: { max_retries: 3 } }
```

## Testing

The loop is **TDD, in this order** — see the `tdd` skill for the discipline and
`testcontainers-go` for the container patterns:

1. **Integration tests first**, against real dependencies in containers.
2. **Scaffold the minimum** to make it build — *generated*, not hand-rolled.
3. The tests **must fail first**. A test that passes before the feature exists is
   testing nothing.
4. Implement to green, then refactor with the tests staying green.

Rules that are not negotiable:

- **Integration tests use no mocks.** Real Postgres, real upstream, and the
  service itself **built and run as a container** — not its handlers called
  in-process. If the test can pass without the binary being built, it is not an
  integration test.
- **Unit tests use generated mocks** (`go.uber.org/mock`), never hand-rolled
  doubles. See `.claude/rules/go-test-mocks.md`.
- **Assertions use `testify`**, never hand-rolled comparisons. See
  `.claude/rules/go-test-assertions.md`.
- Arrange / act / assert, with logging at each step, so a CI failure is readable
  without a local repro.
- Validate responses against the OpenAPI spec (`go-openapi/validate`), and make
  the spec define **every error** so failures are testable too.

## Style

- **Never** write `var _ Interface = (*Impl)(nil)`. The compiler enforces
  satisfaction at the wiring site; the assertion is Java-flavoured noise.
- Interfaces are **small and defined at the consumer**, not exported alongside
  their implementation.
- Wrap errors with `%w` and context. Never swallow one.

## Make targets

A project exposes at least these, because CI and a human should run the same
commands:

```text
build             # with LDFLAGS build info
generate          # go generate ./...
semconv           # Weaver → pkg/semconv (docker)
fmt / fmt-check   # excluding generated files
lint              # golangci-lint
test-unit         # -race -covermode=atomic
check             # fmt-check + lint + test-unit — the CI gate
test-integration  # -tags=integration
compose-up        # the full stack locally
```

## CI

Four workflows: **check** (`make check` with coverage), **integration-test**
(testcontainers), **release** (goreleaser → ghcr), **security** (`govulncheck`).

Pin the Go version deliberately and keep it current — an old patch release is a
vulnerability report waiting to happen.

## Further reading

- [`references/scaffold.md`](references/scaffold.md) — the concrete starting
  point, file by file, for a new service.
- [`references/review.md`](references/review.md) — the checklist for reviewing
  or refactoring an existing project against this standard.
