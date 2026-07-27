# Scaffolding a new Go service

The concrete starting point. Order matters: the spec and the generators come
before any hand-written code, because most of what a service needs is derived
rather than typed.

Reference implementation: `gaarutyunov/skill-test` PR #2 (`go-service/`).

## 0. Before anything

Ask on the issue whether the service is **hexagonal**. Do not decide it yourself
(see the SKILL). Flat is the default.

## 1. Module and tools

```bash
go mod init <module>
```

Add the generators as tool dependencies so nobody installs anything by hand:

```
tool (
	github.com/goforj/wire/cmd/wire
	github.com/oapi-codegen/oapi-codegen/v2/cmd/oapi-codegen
	go.uber.org/mock/mockgen
)
```

## 2. The spec, first

`api/openapi.yaml` — the service's own API **and** any upstream it consumes.
Define **every error response**, not just the happy path: an error the spec does
not describe is an error the integration suite cannot assert on.

## 3. Generation wiring

`generate.go` at the module root, and one `cfg.yaml` per generated artefact:

```
pkg/api/upstream/cfg.yaml     # client for the upstream service
pkg/api/report/cfg.yaml       # client for our own API (used by tests/consumers)
internal/server/cfg.yaml      # strict server for our API
```

Generate the server with the **strict** interface, so handlers take and return
typed values rather than juggling `http.ResponseWriter`.

## 4. Telemetry registry

```
semconv/registry/manifest.yaml     # registry name, schema_url
semconv/registry/<domain>.yaml     # project-specific attribute groups only
semconv/templates/registry/go/     # weaver.yaml + attributes.go.j2
```

Then `make semconv` → `pkg/semconv/attributes.go`.

Add `pkg/semconv/buildinfo.go` with `Version`, `Revision`, `Tag`, `Repository`,
`Date` as package vars, populated by LDFLAGS and surfaced through the official
`service.*` / `vcs.*` attributes.

## 5. Configuration

`internal/config/config.go` — a strongly-typed `Config` with `koanf:"…"` tags,
`LoadKoanf(path)` returning the raw `*koanf.Koanf` (the adapter registry needs
the subtree), and `Parse(k)` decoding with defaults applied.

`configs/config.yaml` — the checked-in default configuration.

Environment overrides use a prefix and a key normaliser
(`REPORT_SERVER__PORT` → `server.port`).

## 6. Composition root

```
internal/app/wire.go        # //go:build wireinject — the provider set
internal/app/wire_gen.go    # generated, committed, never edited
internal/app/app.go         # App struct, Run/Shutdown
internal/app/telemetry.go   # tracer/meter providers, exporters, shutdown
internal/app/server.go      # http.Server construction
```

Every provider is a `Provide*` function. `InitializeApp(ctx, configPath)` returns
the app and a cleanup func.

## 7. Commands

```
cmd/root.go      # root command, persistent flags (--config), no logic
cmd/serve.go     # calls app.InitializeApp then app.Run
cmd/version.go   # prints pkg/semconv build info
main.go          # cmd.Execute()
```

`RunE`, never `Run`. No `log.Fatal` inside commands — return the error.

## 8. HTTP clients

`pkg/api/httpclient.go` — one constructor building an `*http.Client` with
`hashicorp/go-retryablehttp` for retries and `otelhttp` for traces and metrics,
with retry attempts logged through `slog`. Retry settings come from config
(`max_retries`, `wait_min`, `wait_max`), never hard-coded.

## 9. Ports and adapters (if hexagonal)

```
internal/domain/     # models and domain errors. No imports from the rest.
internal/port/       # small interfaces, defined here on the consumer side
internal/usecase/    # one type per use case, depending only on ports
internal/adapter/    # implementations + registry.go
```

`registry.go` maps `name → factory` per port, so `adapters.<port>.type` in the
config chooses the implementation. The registry is the only place that knows
every implementation.

## 10. Tests

`tests/integration/` with `//go:build integration`. Launch Postgres, the upstream,
and **this service built from its Dockerfile**; drive it over HTTP only.

Unit tests live beside the code, use generated mocks, and never need Docker.

## 11. Local stack and CI

- `docker-compose.yml` — the whole stack, so it can be hand-tested before pushing.
- `Dockerfile` (+ `Dockerfile.goreleaser`), `.dockerignore`.
- `.golangci.yml`, `.goreleaser.yaml`.
- `Makefile` with the targets in the SKILL.
- `.github/workflows/`: `check`, `integration-test`, `release`, `security`.

## 12. Before opening the PR

Run the stack with `make compose-up` and exercise it by hand. The integration
suite proves the paths it covers; launching it once proves the paths it does not.
