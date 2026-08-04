## Why

`mcp-anything` is a Kubernetes-native gateway: an operator declares upstreams as
CRDs or as a mounted ConfigMap, the proxy compiles them into MCP tools at load
time, and the tool set is fixed until something outside the proxy changes a
declaration. That is the right shape for a platform team publishing an approved
catalogue. It is the wrong shape for the thing the owner actually wants next.

> It should work as a proxy that has four tools: Search, Execute, Add, Delete.
> The agents would be able to add new tools in JavaScript, Lua, Bash or OpenAPI
> by themselves into the proxy. This is done to optimise token usage. Agents
> could analyse their sessions and extract most used commands into the proxy to
> avoid generating them all the time. **Think a reusable scratchpad.**
> — gaarutyunov/mcp-anything#142

The motivation is token economy, and it is measurable: an agent that has issued
the same six-step `gh api` incantation four times this session is paying for
those tokens every time. If it can write the incantation into the proxy once and
thereafter call one tool by name, the tokens are paid once. Nothing in the
gateway lets it do that — a tool can only come from a declaration the agent
cannot write.

The issue's own storage answer was Postgres, and the owner has since withdrawn
it:

> we have discussed in agentiq spec that it would be great to use **OCI for MCP
> definitions instead of kubernetes resources**. This will make it more
> universal. And **we don't need Postgres**. Research agentregistry
> implementations… But we also have scripts. We also need to **add support for
> MCP servers**. Currently we only have scripts in different runtimes.

That is the change: a local-first proxy, backed by an OCI image layout rather
than a database, that keeps every Kubernetes capability it has today.

**Why not Postgres, when every comparable registry uses one.** agentregistry,
the MCP Registry and epos-registry are all *publication* systems — human-authored
content, curated, reviewed, multi-tenant, long-lived, and queried by people who
did not write it. A Postgres schema with users, namespaces and moderation is the
correct answer to that problem. This is not that problem. A scratchpad entry is
agent-authored, written mid-session, read by the one agent that wrote it, and may
live for four minutes. It needs to be *addressable and reproducible*, not
*governed*. Content addressing gives that for free; a database would have to be
operated, migrated, backed up and — for a `--local` invocation on a laptop —
installed. The one thing publication systems have that a scratchpad wants is the
**promotion** path: a tool that turns out to be genuinely good should be
publishable to a real registry, and `oras.Copy` is that path with no new format.

## What Changes

- **An OCI image layout becomes the tool store.** `~/.mcp-anything/store` (or a
  configured path) holds tool artifacts in the `vnd.epos.tool.*` format epos#51
  already defines. No Postgres — and, deliberately, **no SQLite and no bbolt
  either**: the store is the layout, and nothing else is durable.
- **Four MCP tools — Search, Execute, Add, Delete — manage it at runtime.** `Add`
  writes an artifact and the tool is callable on the next call; `Delete` removes
  it; `Search` finds it; `Execute` runs it. This is the whole of issue #142's
  surface. On the wire they are `store_search`, `store_execute`, `store_add` and
  `store_delete`: every existing tool in this proxy is snake_case, and a bare
  `Add` would be a plausible collision with an upstream's own tool (design D15).
- **A derived in-memory index makes the store searchable.** OCI has no query
  interface, so the proxy rebuilds an index at startup by walking `index.json`
  and reading **manifest annotations only** — never a layer blob. The index is a
  pure function of the layout, so losing it costs nothing. **"No database" does
  not mean "no index"; it means the index is never the source of truth.**
- **`Search` is designed to earn its own tokens.** The existing `search_tools`
  returns each hit's **full `inputSchema`** (`pkg/search/search.go:20`), which is
  unbounded. The store's `store_search` instead returns name, description and a
  flattened parameter list, and never the full schema, because `Execute`
  validates arguments server-side and returns actionable errors. The existing
  `search_tools` contract is **not** changed — narrowing it would alter behaviour
  for deployments with no store configured, which this change promises leaves
  everything untouched (design D12).
- **MCP servers become upstreams.** A new upstream type speaks MCP to a remote
  Streamable HTTP endpoint or to a locally spawned stdio server, and re-exposes
  its tools under the existing `{prefix}__{tool}` namespace.
- **A documented non-goal is struck, not quietly contradicted.** SPEC.md §2 lists
  *"Aggregating other MCP servers (HTTP REST upstreams only)"* as a non-goal.
  This change reverses it, and says so in the same document.
- **Lua joins JavaScript as a tool runtime.** Today `pkg/runtime/lua` serves
  *auth scripts only* — `LuaRuntimeConfig` has `MaxAuthVMs` and no script pool —
  so the issue's four-runtime promise is currently three.
- **The Kubernetes deployment is untouched and keeps working.** CRDs, ConfigMap
  config, the operator, Gateway API wiring, groups, overlays, rate limits,
  circuit breakers, inbound/outbound auth and OTel all survive unchanged. The
  store is **additive**: a proxy with no store configured behaves exactly as it
  does today.

## Capabilities

### New Capabilities

- `mcp-anything-tool-store`: the OCI image layout as the tool store — layout,
  the artifact format, cross-process locking, the derived index, retention, and
  promotion to a real registry.
- `mcp-anything-runtime-tool-management`: the `Search` / `Execute` / `Add` /
  `Delete` MCP surface, what each returns, and the token budget `Search` is held
  to.
- `mcp-anything-mcp-upstreams`: MCP servers as upstreams — remote HTTP and local
  stdio — and the tool-name namespacing that keeps them collision-free.
- `mcp-anything-agent-index-resolution`: the three things AgentIQ SPEC.md §3.2
  requires of this proxy — resolve descriptors from an agent index by digest,
  expose the closure over Streamable HTTP with CORS, and dispatch on
  `artifactType`.

### Modified Capabilities

<!-- mcp-anything predates OpenSpec in this workspace; there is no existing
     capability spec under openspec/specs/ to amend. The project's own SPEC.md is
     the reference, and this change updates it: §2's "Aggregating other MCP
     servers" non-goal is struck, §1's "No database. No persistent state." is
     qualified, and §4's go-sdk pin moves. -->

## Impact

- **`pkg/toolstore/` (new)**: the only package permitted to import
  `oras.land/oras-go/v2`. Open-under-lock, atomic index write, pack, push, tag,
  untag, delete, GC, retention, promote.
- **`pkg/upstream/`**: a `store` builder that materialises artifacts into the
  existing `script` / `command` / `http` executors, and an `mcp` builder for MCP
  server upstreams. `RegisterBuilder` (`pkg/upstream/upstream.go:34`) already
  takes both without modification — this is the seam the design relies on.
- **`pkg/upstream/script/`**: gains a Lua executor beside the Sobek one. The
  `ScriptConfig.ScriptPath` contract is unchanged; store-backed scripts are
  materialised to a path like any other.
- **`pkg/search/`**: unchanged in shape — `ToolDef` keeps `InputSchema` (design
  D12). A lexical fallback is added for deployments with no embedding provider,
  because a local-first proxy must not have to call OpenAI to search its own
  scratchpad.
- **`pkg/upstream/`** (registry seam): `Add` and `Delete` go through
  `RegistryManager.UpdateUpstream` / `RemoveUpstream`
  (`pkg/upstream/refresher.go:16`), presenting the store as one synthetic
  upstream. `Registry` itself stays immutable after construction (design D14).
- **`pkg/mcp/manager.go`**: `Rebuild` must re-materialise store entries, or an
  unrelated config-file edit silently drops every added tool (design D14).
  `listToolsMiddleware` (line 627) collapses `tools/list` to a single search tool
  when tool search is enabled — the token-economy pattern this change
  generalises, and which must be extended to expose the four store tools or they
  are invisible in exactly the deployments that want them (design D15).
- **`pkg/config/`**: a `tool_store` block (path, retention, registry credentials
  and TLS, per-operation timeouts, cache refresh interval, `shared`, promote
  target, per-runtime enablement, search budget, store prefix) and an `mcp`
  upstream type. All optional; secrets via the repo's `${ENV_VAR}` indirection
  (design D16). `ScriptConfig` gains a `runtime` discriminator so a script
  upstream can select Lua — today it has only `script_path` and the builder is
  hard-wired to the JS pool.
- **`cmd/proxy/deps/deps.go`**: blank imports for the new `store` and `mcp`
  builders, with the treeshake test `.claude/rules/registry-pattern.md` requires
  for every new registry entry. `oras-go` is exactly the heavyweight transitive
  dependency that rule exists to keep out of SDK users' binaries.
- **No CLI.** `cmd/proxy` gains no Cobra and no subcommands; promotion is an
  argument to `store_add` (design D17).
- **`pkg/crd/v1alpha1/`**: unchanged. Precedence between a CRD-declared tool and
  a store-added one is a runtime rule (design D9), not a schema change.
- **`go.mod`**: adds `oras.land/oras-go/v2`,
  `github.com/rogpeppe/go-internal/lockedfile`; moves
  `github.com/modelcontextprotocol/go-sdk` from v1.4.1 to v1.7.0.
- **`SPEC.md`**: §1 (the "no persistent state" claim), §2 (the struck non-goal),
  §4 (the go-sdk pin), and new sections for the store and the MCP upstream type.
- **`tests/`**: plain Go tests in the repo's existing style — `tests/integration`
  and `tests/e2e` behind the existing build tags, no new test framework (design
  D18; the repo has never used godog and it is not in `go.mod`). Coverage for the
  four tools end to end, a **two-process** locking test, an
  index-rebuild-from-layout test, a retention test, and a config-reload test
  proving added tools survive `Rebuild`.
- **No migration.** There is no prior tool store to migrate from.
