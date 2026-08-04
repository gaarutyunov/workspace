## 1. Verify the claims the change rests on

Sequenced first because each was read from a library, an unmerged issue or an
upstream document, and each invalidates later work if wrong. All are cheap now
and expensive to discover from a half-built store.

- [ ] 1.1 Confirm `oras-go` v2's `content/oci.Store` behaves as design **D3** assumes at the version actually pinned in `go.mod`: `index.json` read once at construction, `saveIndex` writing in place, in-process mutexes only. If a later version has added cross-process safety, **stop and revise D3** rather than layering redundant locking on top.
- [ ] 1.2 Confirm the two-step removal (**D3**, verified constraint 2): `Store.Delete` refuses to collect a still-tagged manifest, so removal is `Untag` then `Delete` with `AutoGC`. Confirm the "unclosed Reader" caveat empirically with a deliberately-leaked `Fetch` reader, so the close discipline is tested rather than assumed.
- [ ] 1.3 Re-confirm **D2**'s premise that epos exposes no importable Go API: check `gaarutyunov/epos` default branch for a `pkg/` tree with pack/push. If one has appeared, D2 is reopened before `pkg/toolstore` is written, not after.
- [ ] 1.4 Read epos#51 as it stands today and record which of **D7** (`runtime: openapi`) and **D8** (`application/vnd.epos.tool.mcp.v1+json`) it has accepted, rejected or not yet answered. Both are extensions this change proposes back to that issue; the media types here follow whatever it says, and where it is silent this change writes its own and the divergence is recorded in SPEC.md.
- [ ] 1.5 Verify **D10** before touching `go.mod`: that `modelcontextprotocol/go-sdk` v1.7.0 exists, that MCP revision `2026-07-28` removes the `initialize` handshake and `Mcp-Session-Id`, and what that does to `pkg/session` and `pkg/transport`. D10 states this is unverified. If the upgrade is breaking beyond this change's absorption, **keep v1.4.1** and file the stateless-core work as its own issue — milestones 2–9 do not depend on it.
- [ ] 1.5a Confirm the integration facts D14 and D15 rest on, all read from `main` and all cheap to re-check: `Registry` is immutable after construction (`pkg/upstream/registry.go:95`); the mutation seam is `RegistryManager.UpdateUpstream` / `RemoveUpstream` (`pkg/upstream/refresher.go:16`); `Manager.Rebuild` reconstructs upstreams from `cfg.Upstreams` (`pkg/mcp/manager.go:201`) and is driven by the fsnotify watcher in `pkg/config/loader.go`; and `listToolsMiddleware` (`pkg/mcp/manager.go:627`) returns *only* the search tool when search is enabled. If any has changed, D14/D15 are revised before milestone 5 is written.
- [ ] 1.6 Confirm the `search.ToolDef` claim behind **D12** — that `InputSchema` is returned in full today (`pkg/search/search.go:20`) — and measure one real OpenAPI-derived tool's schema against its description, so the token argument has a number attached to it in the PR description.

## 2. `pkg/toolstore` — the layout, the lock, the atomic write

The foundation everything else sits on, and the one milestone whose failure mode
is silent corruption rather than a red test. It lands alone.

- [ ] 2.1 `pkg/toolstore` package with `Open(path)` taking the store root; it is the **only** package permitted to import `oras.land/oras-go/v2` (**D2**).
- [ ] 2.2 Advisory locking via `github.com/rogpeppe/go-internal/lockedfile`: **shared** for resolve, fetch and index rebuild; **exclusive** for pack, push, tag, untag, delete and retention (**D3**).
- [ ] 2.3 The `oci.Store` is constructed **inside** the lock, every time, so the on-disk `index.json` is read fresh. This is the step that is easy to omit and that makes every other lock useless — assert it with a test that mutates the index from a second process between two operations of the first.
- [ ] 2.4 `AutoSaveIndex: false`; `index.json` is written by this package via temp file → `fsync` → `os.Rename`.
- [ ] 2.5 Every content reader is closed before any `Delete` call, per 1.2.
- [ ] 2.6 Pack, push, tag, resolve, untag, delete against the local layout. Pack writes the **epos artifact format unchanged** (**D1**): `artifactType` `application/vnd.epos.tool.script.v1+json`, config `application/vnd.oci.empty.v1+json`, exactly one layer `application/vnd.epos.tool.script.layer.v1+tar`, payload envelope `apiVersion: epos.dev/v1alpha1` / `kind: Tool`, annotations in `dev.epos.*`.
- [ ] 2.7 Startup refusal when the store path is on a filesystem where advisory locking is unreliable (NFS, SMB): detect, and fail naming the path (**D3**). A silent start here is the failure this whole milestone exists to prevent.
- [ ] 2.8 A `depguard` rule in `.golangci.yml` denying `oras.land/oras-go/v2` outside `pkg/toolstore`, mirroring AgentIQ's own rule (**D2**). `depguard` is not currently enabled — enabling it must not turn other existing imports red; scope the rule to this one package pair.
- [ ] 2.8a Every exported store operation takes a `context.Context` first and honours it, and every remote registry call has a configured per-operation timeout (**D16**). `.claude/rules/review-patterns.md` lists missing HTTP client timeouts as a repeat finding in this repo.
- [ ] 2.8b `pkg/toolstore` exports **concrete types**; the small interface each consumer needs is declared in the consuming package, as `Builder`, `ToolExecutor` and `RegistryManager` already are. This is also what keeps **D2**'s "the swap is one package" promise honest.
- [ ] 2.8c Name the typed/sentinel errors that scenarios require callers to branch on, so tests use `errors.Is`/`errors.As` rather than string matching: unsupported runtime (4.5), source disabled (4.4), shadowed by a declared tool (5.9), digest mismatch (9.2), unrecognised `artifactType` (9.5), and registry-unreachable (7.5/8.1). Wrap with `%w` per the repo's convention.
- [ ] 2.9 **Two-process locking test**: two OS processes (not two goroutines) each add a different tool to one store concurrently; both tags survive. Two goroutines would pass against the in-process mutexes and prove nothing.
- [ ] 2.10 **Crash test**: kill a process mid index-write; the store still resolves everything that was present before, and `index.json` is not truncated.
- [ ] 2.11 **Foreign-client test**: after an add, the directory validates as an OCI Image Layout and a plain `oras` client resolves and pulls the tag with no mcp-anything knowledge.
- [ ] 2.12 Filesystem check per **D3**: refuse at startup on a positively identified network filesystem (NFS, SMB) naming the path; **warn and continue** when the type cannot be determined. Both branches tested, because "unknown" is the branch that will actually fire on someone's machine.

## 3. The derived index

The highest-leverage decision in the design (**D4**), and the one most likely to
be eroded later by someone optimising startup. The tests are what defend it.

- [ ] 3.1 Build the in-memory index by walking `index.json` and reading **manifest annotations only**. Never fetch a layer blob to index.
- [ ] 3.2 Pack (2.6) writes name, description, runtime and the flattened parameter list into manifest annotations, because 3.1 is impossible otherwise. This is a constraint on the *format*, not on the indexer.
- [ ] 3.3 Rebuild at startup and refresh after every `Add` and `Delete`. Never persisted, never migrated, no recovery step.
- [ ] 3.4 A manifest missing `dev.epos.name` is logged at WARN naming the digest, skipped, and indexing continues.
- [ ] 3.4a The index is an **immutable value swapped atomically** on rebuild (`atomic.Pointer`), never mutated in place — the pattern `config.Loader` already uses and that `Registry` already embodies (**D4**). Readers take no lock.
- [ ] 3.4b A `-race` test hammering `store_search` while adds and deletes run, asserting no race and that each search result set is consistent with one point in time rather than a mixture of two.
- [ ] 3.5 A test asserting the blob-fetch count during index construction is **zero** — instrumented at the store boundary, so it fails if someone adds a convenience read.
- [ ] 3.6 A test asserting the index after an unclean kill is identical to the index before it, with no repair step in between.
- [ ] 3.7 A doc comment on the index type stating that it is derived and that persisting it is the thing not to do, with the reason (**D4**). The first person to want faster startup will read this file.

## 4. Execution — the `store` upstream builder and the Lua tool runtime

Tools have to run before the four-tool surface is worth having. This milestone
closes the gap the issue's phrasing conceals: four runtimes are today three.

- [ ] 4.1 A `store` upstream builder registered through `RegisterBuilder` (`pkg/upstream/upstream.go:34`) that materialises a stored artifact into the existing `script` / `command` / `http` executors. `ScriptConfig.ScriptPath` is unchanged — a store-backed script is materialised to a path like any other.
- [ ] 4.2 A **Lua tool runtime** in `pkg/upstream/script` beside the Sobek one, pooled and timeout-bounded in the same shape. `pkg/runtime/lua` today serves auth scripts only (`LuaRuntimeConfig` has `MaxAuthVMs` and no script pool); extend it with a script pool rather than forking it.
- [ ] 4.2a Config for 4.2, which does not exist today: `ScriptConfig` (`pkg/config/config.go:469`) gains a `runtime` discriminator (`js` default, `lua`) — it currently has only `script_path` and the `script` builder is hard-wired to `cfg.JSScriptPool`. Add `LuaRuntimeConfig.MaxScriptVMs` and the pool wiring mirroring `JSScriptPool`; `MaxAuthVMs` stays as it is, for auth scripts.
- [ ] 4.3 An OpenAPI-sourced artifact materialises into the existing `http` executor: the layer carries the document pruned to one operation plus base URL and outbound-auth reference, `spec.entrypoint` naming the document inside the tar (**D7**).
- [ ] 4.4 The **capability gate** (**D11**): each source individually enable-able in config; `bash` and `mcp-stdio` default to **off**. This is a gate, not a sandbox, and the config reference says so in those words.
- [ ] 4.5 An artifact whose `spec.runtime` is unrecognised is indexed and listed; `Execute` on it fails naming the unsupported runtime; the artifact is neither rewritten nor deleted (**D7**'s open-enum rule).
- [ ] 4.5a The credential rule from **D7**: an `store_add`-ed OpenAPI tool may name an existing outbound-auth credential only when its base URL is that upstream's own base URL or is on an explicit allowlist. Any other base URL is called **unauthenticated**; asking for the credential anyway is an error naming both, never a silent downgrade. This is a credential-exfiltration path the capability gate does not cover, so it is a test, not a doc note.
- [ ] 4.6 Tests: a stored JavaScript tool and a stored Lua tool each execute; a Bash tool is refused when the source is disabled and runs when enabled; an unknown runtime produces the error in 4.5 and nothing else; and the three credential cases in 4.5a (redirected credential refused, matching pairing allowed, no-credential call allowed).

## 5. The four tools — `Search`, `Execute`, `Add`, `Delete`

Issue #142's entire surface. Sequenced after 2–4 because each of the four is a
thin shell over machinery that now exists.

- [ ] 5.1 The four tools are registered **only when a tool store is configured**; with no store they are absent from `tools/list` and the proxy behaves exactly as today. Wire names are `store_search`, `store_execute`, `store_add`, `store_delete` — snake_case like every other tool here, and `Registry.Dispatch` rejects names without the `__` separator (**D15**).
- [ ] 5.2 `store_add`: validate → pack → push → refresh index → publish through `RegistryManager.UpdateUpstream` (`pkg/upstream/refresher.go:16`), presenting the store as **one synthetic upstream** named for the store prefix (**D14**). `Registry` itself stays immutable after construction — "mutate the live registry" is not available and is not what this does. An invalid definition (bad JSON Schema) fails before anything is written.
- [ ] 5.3 `store_delete`: untag → delete with GC → refresh index → `RegistryManager.UpdateUpstream` with the remaining entries (or `RemoveUpstream` when the last one goes). A subsequent `store_execute` says the tool does not exist.
- [ ] 5.3a **`Manager.Rebuild` re-materialises the store** (`pkg/mcp/manager.go:201`), which reconstructs upstreams from `cfg.Upstreams` and is driven by the fsnotify config watcher. Without this, any unrelated edit to the config file silently deletes every added tool from the live registry — no error, no log, and the tools reappear on restart, which makes it intermittent. Two tests: an unrelated config edit leaves added tools callable, and a reload does not resurrect a deleted one (**D14**).
- [ ] 5.3b **`listToolsMiddleware` (`pkg/mcp/manager.go:627`) returns the four store tools too.** Today it returns *only* `search_tools` when search is enabled — i.e. the four tools would be invisible in exactly the deployments most likely to configure a store. Stored tools themselves stay **out** of `tools/list` while a store is configured; listing them is the token cost the feature exists to avoid (**D15**).
- [ ] 5.4 `Search`'s response shape as a **specified contract** (**D12**): fully-qualified name, description truncated to a configured budget (default 200 chars), and a flattened top-level parameter list of `name: type` plus required/optional. No `inputSchema`, no nested schemas, no per-property descriptions, no enums, no examples. Remove `InputSchema` from `search.ToolDef` (`pkg/search/search.go:20`).
- [ ] 5.5 `store_search`'s response is bounded by a configured maximum size, truncates its result list to fit, and **states how many were elided**. Enforced, not intended — a test asserts the bound with a store of many large-schema tools.
- [ ] 5.6 A test asserting a `store_search` hit's size is **independent of the hit's `inputSchema` size** — the property D12 actually claims, which a fixed-size assertion would not catch.
- [ ] 5.7 `store_execute` validates arguments server-side against the full schema and returns an error naming the offending parameter: a missing required one by name, a type mismatch with expected and received type. This is what makes 5.4 safe, so it lands in the same milestone, not later.
- [ ] 5.8 **Lexical fallback** (**D13**): with no embedding provider configured, `store_search` matches lexically over the derived index — substring and token overlap on name, description and parameter names — and the response states which mode produced it. A test asserts **no outbound network request** is made to serve a query in this mode.
- [ ] 5.9 Precedence and namespacing (**D9**): store tools carry their own prefix, default `scratch`, via the existing `{prefix}__{tool}` mechanism. On a deliberately shared prefix the declared tool wins, the stored one is shadowed, the collision is logged with both sources named, and `store_search` marks it shadowed. `store_add` of a name that would be shadowed **fails naming the winner** rather than writing an uncallable artifact.
- [ ] 5.9a Shadowing resolves **before** `registry.New` is called, by filtering the synthetic upstream's entry list against declared names. Declared-versus-declared collisions — a shared `tool_prefix`, a duplicate prefixed name — stay **fatal** exactly as today (`pkg/upstream/registry.go:125,135`); they are not softened into warnings. A test asserts two config upstreams sharing a prefix still fail with a store configured (**D9**).
- [ ] 5.10 Tests covering the four tools end to end, in the repo's existing style — plain Go over Testcontainers in `tests/integration`, behind the existing build tags. **No godog**: it has never been used here, there are no `.feature` files and it is not in `go.mod` (**D18**). Cover the add-then-execute-without-restart path and the delete-then-execute path.

## 6. MCP servers as upstreams

The owner's second requirement, and the milestone that reverses a documented
non-goal.

- [ ] 6.1 An `mcp` upstream builder registered through `RegisterBuilder`, re-exposing the remote server's tools under `{prefix}__{tool}` using the existing `MCPUpstreamSpec.ToolPrefix`.
- [ ] 6.2 Reference form 1 — **remote Streamable HTTP**: a URL plus an outbound-auth reference, resolved through the existing auth pipeline.
- [ ] 6.3 Reference form 2 — **local stdio**: spawn a command on `PATH` (`npx`, `uvx`, …), supervise it for the life of the upstream, capture its stderr into the proxy's logs, terminate it on shutdown and on upstream removal. Gated off by default per 4.4.
- [ ] 6.4 Reference form 3 — **container image**: usable only where a runtime already exists; in Kubernetes the operator declares a sidecar and the proxy connects to it as a local endpoint. **The proxy never shells out to Docker**, in any deployment (**D8**).
- [ ] 6.5 A stored MCP server artifact is `application/vnd.epos.tool.mcp.v1+json` with one layer carrying `server.json` and the manifest annotated `io.modelcontextprotocol.server.name`; no `Tool` document is required. The reference form is read from `server.json`'s own `remotes[]` / `packages[]`, not from an mcp-anything field (**D8**). If 1.4 found epos#51 chose a different name, use theirs — this is the one-line change D8 anticipates.
- [ ] 6.6 Two upstreams advertising the same tool name both stay callable; two upstreams declared with the **same prefix** fail at load naming both, not at call time.
- [ ] 6.7 An unreachable `mcp` upstream leaves the proxy starting and serving everything else, reporting through the existing readiness surface (`pkg/upstream/readiness.go`).
- [ ] 6.7a Both new builders (`store`, `mcp`) are blank-imported in `cmd/proxy/deps/deps.go` and carry the **treeshake test** `.claude/rules/registry-pattern.md` requires for every new registry entry (`make check` runs `tests/treeshake`). `oras-go` is precisely the heavyweight transitive dependency that rule exists to keep out of an SDK user's binary.
- [ ] 6.8 **SPEC.md §2**: strike *"Aggregating other MCP servers (HTTP REST upstreams only)"* and state that it was a non-goal and why it changed. Deleting the line silently is the thing not to do (**proposal**, *a documented non-goal is struck*).

## 7. Retention and promotion

- [ ] 7.1 Retention keeps the most recent N **versions per tool name**, N configurable, retention disable-able, running on `Add` rather than on a timer.
- [ ] 7.2 Retention never removes an artifact referenced by the live tool registry snapshot; when it would, the artifact is kept and the reason logged.
- [ ] 7.3 Removal is untag → delete with GC (per 1.2); a test asserts the manifest **and its layer blob** are gone from `blobs/sha256/` and the store still validates as a layout.
- [ ] 7.4 Tests for the two ways retention gets this wrong: forty **distinct** names with keep-3 leaves all forty; six versions of **one** name with keep-3 leaves three.
- [ ] 7.5 Promotion: `oras.Copy` from the local layout to a configured registry, as a `promote: true` argument to `store_add` and as an exported operation on `pkg/toolstore`. The copied artifact's **digest is unchanged**. **No CLI subcommand** — `cmd/proxy` has no CLI framework at all today (no flags, no subcommands, `spf13/cobra` only an indirect dep), so adding one means a `NewRootCmd()` factory and turning `main()` into a `serve` subcommand: a structural change to the binary that has nothing to do with #142. Deferred to 11.6 (**D17**).
- [ ] 7.5a Registry access is configured, not assumed (**D16**): credentials per host via the repo's `${ENV_VAR}` indirection, never a literal; per-host TLS with an explicit plain-HTTP opt-in for a local `zot`; a per-operation timeout on every pull, push and copy; and no silent fallback to an ambient Docker config file unless the deployment opts in.
- [ ] 7.6 A test asserting `Add` without promotion makes **no request to any remote registry**, on a proxy that has a promotion target configured.

## 8. Multiple replicas — the registry-backed store and the startup refusal

The section of the design where "no Postgres" is under genuine strain. It is
implemented as written, including the refusal, because the refusal is the whole
value of having named the problem.

- [ ] 8.1 A registry-backed store mode: the configured registry **is** the store, the local layout is a pull-through cache refreshed on an interval and on cache miss. `Add` is pack → push to registry → invalidate local, so the tool is live on this pod immediately.
- [ ] 8.2 Promotion in this mode still means copying to a **different** registry the proxy does not read from — the one-sentence rule from **D5**: `Add` writes to the store the proxy reads from; promote copies to one it does not.
- [ ] 8.3 **Startup refusal**, driven by declared config rather than by discovery: `tool_store.shared` (default `false`); the proxy refuses to start when `shared` is true and the store is local-only, naming both. A pod cannot read its own `spec.replicas` — doing so would mean a Kubernetes API read of the owning Deployment plus RBAC the proxy does not have and should not acquire for this.
- [ ] 8.3a The **chart and the operator set `shared`**, because they are what actually know the replica count: the chart from `replicaCount`, the operator from the `MCPProxy`'s replica count. A chart rendering more than one replica against a local-only store fails at **template time**, which is strictly better than failing at pod start.
- [ ] 8.3b Say plainly in the config reference what this does not cover: a hand-written Deployment scaled to three replicas without setting `shared` gets no refusal. The chart and the operator are the supported paths.
- [ ] 8.4 Document the accepted consequences in the config reference rather than in the design only: `Add` is eventually consistent across replicas bounded by the refresh interval; `Delete` is worse, leaving a tool callable elsewhere for up to one interval; a registry outage fails the write path. Sticky sessions or a single replica are the real constraints, and are named as such.
- [ ] 8.4a The refresh goroutine has a **named owner and a shutdown path** — started from the store's lifecycle, stopped on `ctx` cancellation, and joined on shutdown, the way 6.3 specifies for spawned stdio servers. An interval goroutine with no stated owner is how a proxy ends up leaking one per reload.
- [ ] 8.5 A test for 8.3 (refusal), one for 8.3a (chart template failure), and one for 8.1's cache-miss refresh. Full multi-pod convergence is an E2E concern, not a unit one.

## 9. AgentIQ SPEC.md §3.2 conformance

The three things AgentIQ states on this proxy. Sequenced here because each is
built out of milestones 2–6, and separated so that AgentIQ's acceptance is
checkable as a unit.

- [ ] 9.1 Resolve MCP server and script-tool descriptors from an agent index **by digest**, recursively, with cycle detection by digest and a bounded depth. A resolved descriptor is materialised into the store's own format, so an index-resolved tool and an `Add`-ed one are indistinguishable to `Search` and `Execute`.
- [ ] 9.2 A referenced descriptor whose content does not hash to the recorded digest fails resolution naming the descriptor, and **nothing** from that index is exposed.
- [ ] 9.3 Expose the resolved closure over **Streamable HTTP with CORS**, allowed origins from configuration. The default must not be a wildcard — a browser-callable tool proxy with `*` is an open executor.
- [ ] 9.4 **Dispatch on `artifactType`**, distinguishing at minimum a container image from a script artifact. Never infer from a tag, repository name, file extension, or an annotation a producer may omit. A test asserts a script artifact tagged to look like an image still dispatches as a script.
- [ ] 9.5 An unrecognised `artifactType` is listed as unsupported naming the type, refuses to execute with that same message, and leaves the rest of the closure unaffected.
- [ ] 9.6 A conformance test naming AgentIQ §3.2's three bullets, so that a future change breaking one of them fails a test that says which downstream project cares. Plain Go in `tests/integration`, per **D18**.

## 10. The go-sdk upgrade, SPEC.md, config reference, CI

The upgrade is sequenced **last and separately** because D10 records it as
unverified and the rest of the change does not depend on it. If 1.5 said no, 10.1
and 10.2 do not happen and the change still ships.

- [ ] 10.1 Move `modelcontextprotocol/go-sdk` v1.4.1 → v1.7.0, on its own commit, with the acceptance criterion that **every existing transport and every existing tool keeps working** — the existing integration and E2E suites are the evidence, unmodified.
- [ ] 10.2 If revision `2026-07-28`'s stateless core lands with it: remove the session state the protocol no longer has, and reconcile `pkg/session` with SPEC.md §1's "No database. No persistent state. Every pod is identical." If the upgrade is deferred, file that reconciliation as its own issue and say so in the PR.
- [ ] 10.3 **SPEC.md**: §1's "No database. No persistent state." claim corrected — note it is **already false on `main`** (`pkg/session/postgres`, `pkg/session/redis`, `pkg/cache/redis`), so this is a correction owed regardless of this change, not a concession this change forces; the store is durable, the index is not; §2's non-goal struck (6.8); §4's go-sdk pin corrected to whatever 10.1 concluded; new sections for the tool store and the `mcp` upstream type. §5's layout drift is **out of scope** and stays (`internal/crdutil` still exists, so "replaced by `pkg/`" is not quite right either) — record that in the PR so the remaining drift is a known quantity rather than an oversight.
- [ ] 10.4 Config reference for the `tool_store` block (path, retention, registry credentials and per-host TLS, per-operation timeouts, cache refresh interval, `shared`, promote target, per-runtime enablement, search budget, store prefix) and the `mcp` upstream type, plus `ScriptConfig.runtime` from 4.2a. The bash entry states in plain words that a Bash tool runs with the proxy's filesystem, network, environment and credentials, and that **anyone able to call `Add` on such a proxy can execute arbitrary commands in it** — this is the central risk of the design and the config reference is where it will actually be read.
- [ ] 10.5 README: the four tools, the scratchpad motivation, and the local-first quickstart that needs no registry, no database and no Docker.
- [ ] 10.5a **Test conventions: the repo's, not the workspace's.** mcp-anything uses plain `testing` with hand-rolled fakes — no `stretchr/testify` import anywhere (indirect only), no `mockgen`, no godog. The workspace rules `go-test-assertions.md` (testify) and `go-test-mocks.md` (gomock) point the other way. New packages follow **the repo**, because one new package built to a different testing idiom than its own repo is worse than either idiom consistently applied. Recorded here rather than silently taken, so the owner can overrule it in review (**D18**).
- [ ] 10.6 Full CI green — `Lint, Vet, Unit Tests, Build`, `Integration Tests`, the E2E matrix, and the coverage gate. `codecov/project` is a ratchet against the branch point, and `patch` is 100% on changed lines: new packages arrive with their tests or the patch gate is red. `make check` includes the treeshake suite (6.7a).
- [ ] 10.7 Confirm `pkg/crd/v1alpha1` is genuinely untouched, as the proposal claims — precedence is a runtime rule (**D9**), not a schema change. If a CRD field turned out to be necessary, the proposal's Impact section is wrong and gets corrected rather than quietly outgrown.

## 11. Follow-ups to file, not to do here

- [ ] 11.1 Reconciling store-added tools back into CRDs via a controller — the issue defers it explicitly ("Afterwards we can think of some kind of reconciliation with a controller… But it's out of scope for now").
- [ ] 11.2 SPEC.md §5's `internal/`-versus-`pkg/` layout drift (10.3).
- [ ] 11.3 The stateless-core work, if 1.5 deferred the go-sdk upgrade (10.2).
- [ ] 11.4 `runtime: openapi` and `application/vnd.epos.tool.mcp.v1+json` as proposals on epos#51 (1.4) — filed there, not carried here.
- [ ] 11.5 Narrowing the existing `search_tools` response, which has the same token-economy argument as **D12** but a different compatibility story — it changes behaviour for every current deployment and breaks `tests/integration/tool_search_test.go:202`. Worth doing; not here (5.4a).
- [ ] 11.6 A promotion CLI, and with it the Cobra adoption `cmd/proxy` would need — a `NewRootCmd()` factory, `RunE`, `cmd.OutOrStdout()`, today's `main()` becoming `serve` (**D17**).
- [ ] 11.7 Cosign signing of stored artifacts via the Referrers API. Worth having for **attribution**; it is not isolation and must not be presented as mitigating **D11** (a signed Bash script has exactly the authority an unsigned one does).
