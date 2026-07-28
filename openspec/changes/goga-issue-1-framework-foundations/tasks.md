## 1. Repo foundations

goga is empty — one commit, a one-line README.

- [ ] 1.1 `go mod init github.com/gaarutyunov/goga`; Go version matching the newest project (1.26.x).
- [ ] 1.2 Package layout **flat, no `pkg/`, no `internal/`** for goga's own code, per the issue.
- [ ] 1.3 `.golangci.yml`, `Makefile`, `.goreleaser.yaml` — these double as the templates goga ships (design D3's carve-out).
- [ ] 1.4 **Read Yokai's module decomposition before fixing package boundaries** (design, Risks). Its stack is wrong for us but its seams are worth learning from.

## 2. `goga/config`

The highest-value runtime wrapper: two projects use koanf with *incompatible*
semantics, and both authors wrote a paragraph explaining precedence because
koanf has none.

- [ ] 2.1 `Load` with an explicit source order — defaults → file → env → flags — visible at the call site.
- [ ] 2.2 Typed unmarshalling with duration and slice decoding.
- [ ] 2.3 **Return the raw `*koanf.Koanf` alongside the typed value** — go-service's `k.Cut()` subtree pattern breaks without it (design D2).
- [ ] 2.4 One documented env-key convention. Two projects chose incompatible ones; pick and state it.
- [ ] 2.5 A missing file is non-fatal unless declared required; a missing required key fails naming the key.

## 3. `goga/telemetry`

1 of 4 projects configures this today. That ratio is the argument.

- [ ] 3.1 One call establishing tracer, meter **and** structured logger, installed globally and returned.
- [ ] 3.2 Exporters selected by config name; an unknown name fails at startup naming the supported values rather than silently disabling telemetry.
- [ ] 3.3 Official semantic conventions for resource attributes.
- [ ] 3.4 Ordered shutdown flushing every provider, errors joined rather than first-wins.
- [ ] 3.5 Prometheus reader attached by default; a push exporter additive.

## 4. `goga/serve` and `goga/client`

- [ ] 4.1 `Serve` — signal handling, bounded graceful shutdown, header/read/write timeouts set.
- [ ] 4.2 **Probe and metrics endpoints registered outside the traced router** so they never pollute request traces (design, Context). This is the detail that does not survive a document.
- [ ] 4.3 Non-zero exit status on failure. epos calls `Execute()` not `ExecuteContext` today and has no signal handling at all — the wrapper is what stops that recurring.
- [ ] 4.4 `client.New` — configurable retries with backoff, client spans, context propagation, client metrics, retries logged.
- [ ] 4.5 Both return their underlying objects.

## 5. `goga/gogatest`

Where the knowledge is most expensive and most duplicated: three incompatible
testcontainers strategies, and a godog bootstrap copy-pasted 5× in gopgql and 8×
in epos.

- [ ] 5.1 A container fixture with **one** decided lifecycle and reset strategy, documenting why — weighing gopgql's snapshot/restore, epos's rejection of `CleanupContainer`, and go-service's shared-network stack.
- [ ] 5.2 Deterministic fixture ordering — schema before seed data, regardless of file naming (go-service had to rename scripts `01-`/`02-`/`03-` to force it).
- [ ] 5.3 Teardown that runs on failure and does not accumulate containers across a long run.
- [ ] 5.4 A godog harness owning scenario reset, runner options and reporting, so a suite only registers steps.
- [ ] 5.5 A supported way for a step to reach the test handle — both projects invented their own.
- [ ] 5.6 The container handle is reachable for anything the fixture does not model.

## 6. Composite actions

Today golangci-lint is invoked **four ways at three versions**. `gopgql` and
`epos` share a docs-workflow bug fixed by copy-paste (`keep_files: true`,
"same bug, same fix as gopgql#24").

- [ ] 6.1 `setup-go` — checkout + setup-go + cache; **Go version defaults to what `go.mod` says**.
- [ ] 6.2 `go-lint` — gofmt gate, `go vet`, golangci-lint via the official action at a pinned version.
- [ ] 6.3 `go-test` — race, atomic coverage, coverage summary and artifact.
- [ ] 6.4 `go-test-integration` — tagged run, timeout, **artefacts uploaded even on failure**; no container-runtime setup step, which no project needed.
- [ ] 6.5 **`go-generate-check`** — `go generate ./... && git diff --exit-code`. **No repo has this today.**
- [ ] 6.6 `go-vuln` — one action replacing three mechanisms.
- [ ] 6.7 `go-release` — goreleaser, with a `docker` flag covering the only real divergence.
- [ ] 6.8 `pages-deploy` / `pr-preview` — carrying the `keep_files` fix so the third repo does not learn it the hard way.
- [ ] 6.9 Actions SHA-pinned internally; projects pin **goga** and nothing else.

## 7. The skill

- [ ] 7.1 One skill: which entry point to reach for, what goga does **not** cover, where the escape hatches are.
- [ ] 7.2 It does **not** re-teach cobra, koanf or otel — that is the library's job now, and duplicating it is how guidance drifts.
- [ ] 7.3 State plainly which conventions goga does *not* enforce, so the reader knows what still rests on them.
- [ ] 7.4 **Resolve the existing contradiction** (design D5): the spf13 `go` skill rejects `internal/`-layered packages; `go-project-scaffold` prescribes them. **This wants settling before PR #31 merges**, and it is not goga's code to change — raise it on that PR.

## 8. Prove it on one project

A framework nobody adopts moves no numbers.

- [ ] 8.1 Adopt `gogatest` in **gopgql** — it needs only the test wrappers, so it is the cheapest honest proof, and it would delete the 5× duplicated godog bootstrap.
- [ ] 8.2 Adopt `config` + partial `telemetry` in **epos** — the better test of D2, since epos wants a subset and has no DI.
- [ ] 8.3 Re-measure the compliance numbers afterwards and record them, so the claim in the proposal is checkable rather than rhetorical.
- [ ] 8.4 Retarget sysgo's templates to emit `goga.*` (design D3) — `main.go.tmpl` should collapse to roughly `goga.Run(...)`.
