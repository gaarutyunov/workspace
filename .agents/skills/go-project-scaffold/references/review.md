# Reviewing or refactoring a Go project

The same standard as the SKILL, turned into things to look for. Use it when
reviewing a PR, auditing an existing service, or deciding what to change first
in a refactor.

Findings are worth ranking: the top section is where real defects hide, the
bottom is housekeeping.

## Generation and drift

- [ ] Is anything **hand-written that should be generated**? HTTP models,
      clients or servers typed out by hand; mocks written as structs; telemetry
      attribute constants declared in Go rather than a Weaver registry. Each one
      is a future silent divergence from its spec.
- [ ] Are generators **tool dependencies in `go.mod`**, or does the README ask
      the reader to `go install` something? The second means CI and a laptop can
      run different versions.
- [ ] Are generated files **committed** and **excluded from `gofmt`/lint**?
- [ ] Has a generated file been **hand-edited**? Check for stray diffs in
      `*.gen.go` / `wire_gen.go` — the next `make generate` will silently revert
      them.

## Configuration

- [ ] **Viper anywhere?** It should be koanf. This is a standing preference, not
      a per-project one.
- [ ] Are sources loaded in an **explicit precedence order** (defaults → file →
      env → flags), or is the order accidental?
- [ ] Is config decoded into a **strongly-typed struct**, or read with
      stringly-typed lookups at the point of use?
- [ ] Are retry/timeout values **configurable**, or hard-coded constants?
- [ ] For interchangeable implementations: is there a **named adapter registry**,
      or is the choice a compile-time import?

## Telemetry

- [ ] Are attributes **official conventions where one exists**? A hand-rolled
      `http_status` next to the standard `http.response.status_code` makes the
      data unjoinable.
- [ ] Are project-specific attributes in the **Weaver registry**, or scattered as
      string literals?
- [ ] Does outbound HTTP emit **all three signals** — spans with propagation,
      client metrics, structured logs on retry/failure?
- [ ] Is **build info** injected via LDFLAGS and reported through `service.*` /
      `vcs.*`, or is the version a hard-coded string?

## Tests

- [ ] Do integration tests **build and run the service as a container**, or do
      they call handlers in-process? In-process is a unit test wearing a costume.
- [ ] **Any mocks in the integration suite?** There should be none.
- [ ] Do unit tests use **generated** mocks, or hand-rolled `stubFoo` structs?
- [ ] **`testify`**, or hand-rolled `if got != want` comparisons?
- [ ] Does the integration suite carry `//go:build integration`, so `go test ./...`
      stays unit-only?
- [ ] Are **error paths** covered, and does the OpenAPI spec define them so they
      can be asserted?
- [ ] Would the tests **fail if the feature were removed**? A test that passes
      against a stub proves nothing.

## Structure

- [ ] Is there **logic in `cmd/`**? Commands define flags and call into the
      application; nothing else.
- [ ] Does the **domain import the framework**? `internal/domain` should import
      neither cobra, nor koanf, nor the HTTP layer.
- [ ] Is DI **generated** (wire), or a hand-written constructor cascade / service
      locator / `init()` side effects?
- [ ] If hexagonal: are ports **small and defined on the consumer side**, or a
      package of fat interfaces mirroring the implementations?
- [ ] If *not* hexagonal: is that fine? Not every service needs it — say so
      rather than adding indirection nobody asked for.

## Style

- [ ] `var _ Interface = (*Impl)(nil)` — **remove it**. The compiler enforces
      satisfaction at the wiring site.
- [ ] Errors wrapped with `%w` and context, never swallowed.
- [ ] Interfaces returned from constructors where a concrete type would do.
- [ ] `RunE` rather than `Run`; no `log.Fatal` inside command bodies, which
      bypasses `defer`.

## Tooling

- [ ] Do `make check` and CI **run the same thing**? If CI has steps the Makefile
      lacks, a contributor cannot reproduce a failure locally.
- [ ] Is `govulncheck` in CI, and is the Go version current? An old patch release
      is an open vulnerability report.
- [ ] Is there a `docker-compose.yml` that brings the whole stack up for hand
      testing?
