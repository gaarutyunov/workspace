## Context

Issue #142 asks for four MCP tools — `Search`, `Execute`, `Add`, `Delete` — so an
agent can write its own tools into the proxy at runtime and stop regenerating
them. The issue proposed Postgres for storage. The owner then withdrew that in
favour of OCI, aligned with the AgentIQ spec, and added a second requirement:
support MCP servers, not only scripts.

This design is written against the code as it stands on `main`, not against
SPEC.md, because the two have drifted — SPEC.md §5 still describes an `internal/`
tree that is now nearly empty (`internal/crdutil` is all that remains; the rest
moved to `pkg/`), and pins go-sdk v1.3.0 where `go.mod` says v1.4.1. Where they
disagree, the code wins and SPEC.md is corrected by this change.

SPEC.md §1's "No database. No persistent state. Every pod is identical." is
**already false on `main`** — `pkg/session/postgres`, `pkg/session/redis` and
`pkg/cache/redis` all exist. That matters for how this change is read: it is not
introducing durability into a stateless proxy, it is adding a second durable
thing to a proxy that already has optional ones. The claim in §1 needs correcting
regardless of this change; this change corrects it.

### What already exists, because "do not remove existing functionality" owes an account

Reading the repo rather than the spec changes what this change actually has to
build. Most of the machinery is present:

| Capability | Where | State |
| --- | --- | --- |
| Pluggable upstream types | `pkg/upstream/upstream.go:34` `RegisterBuilder` | A registry keyed by type string, populated from `init()`. Adding `store` and `mcp` types needs no change to the seam. |
| JavaScript tool runtime | `pkg/upstream/script` (Grafana Sobek), `pkg/runtime/js` | Working, pooled, timeout-bounded, `ctx.fetch` available. Loads from `ScriptConfig.ScriptPath`. |
| Bash / subprocess tools | `pkg/upstream/command` | Working. `Shell: true` runs via `sh -c`; env, working dir, output cap, timeout. |
| OpenAPI tools | `pkg/upstream/http` | The original product. Overlays, jq transforms, synthetic dry-run, validation. |
| Lua | `pkg/runtime/lua`, `pkg/auth/*/lua.go` | **Auth scripts only.** `LuaRuntimeConfig` exposes `MaxAuthVMs` and no script pool. There is no Lua *tool* runtime. |
| Semantic tool search | `pkg/search/search.go`, `pkg/mcp/manager.go` | `search_tools` exists. `listToolsMiddleware` already collapses `tools/list` to just `search_tools` when enabled — the exact token-economy pattern #142 wants, generalised by this change. |
| Tool-name collision handling | `{prefix}__{tool}`, `MCPUpstreamSpec.ToolPrefix` | Solved. Reused, not reinvented. |
| Kubernetes | `pkg/crd/v1alpha1`, `pkg/operator`, `charts/` | `MCPProxy` / `MCPUpstream` CRDs, service discovery, Gateway API refs, rate limits. |

So the genuinely new work is: the OCI store, the four-tool surface, MCP servers
as upstreams, and a Lua tool runtime. The four runtimes are **three plus a gap**,
not four, and the issue's phrasing conceals that.

### Verified constraints

Each of these was checked against the artefact named, not inferred:

1. **`oras-go` v2 `content/oci.Store` is single-process only.** At v2.6.2 it holds
   in-process mutexes, reads `index.json` once at construction, and `saveIndex`
   writes in place. Two processes silently lose each other's tags; a crash
   mid-write truncates the index. The OCI image-layout spec is silent on
   concurrency, so this is a gap every implementer must fill. epos hit it first
   and its fix is in `epos/SPEC.md` §9.2.
2. **Delete works, in two steps.** `Store.Delete` refuses to garbage-collect a
   dangling manifest that is still tagged (`isTagged`, `oci.go:586`), so removal
   is `Untag` then `Delete` with `AutoGC` on. Verified by reading v2.6.2.
   `Delete` "may fail … if there is a process (i.e. an unclosed Reader) using
   target" — every `Fetch` reader must be closed first.
3. **epos exposes no importable Go API.** epos's OCI store, packing and registry
   client are entirely under `internal/` (`internal/store`, `internal/skillfile`,
   `internal/cli`). This is not a policy preference — Go's `internal/` rule makes
   them unimportable from another module. epos `main` carries no Go code at all;
   the implementation lives on in-flight branches. This settles D2 by the
   compiler rather than by argument.
4. **`Search` currently returns unbounded results.** `search.ToolDef`
   (`pkg/search/search.go:17`) embeds the full `inputSchema` as
   `json.RawMessage`. For an OpenAPI-derived tool that is routinely larger than
   the tool description by an order of magnitude.
5. **`go.mod` pins `modelcontextprotocol/go-sdk` v1.4.1** and
   `philippgille/chromem-go` v0.7.0.

## Goals / Non-Goals

**Goals:**

- An agent can add, find, run and remove its own tools at runtime, over MCP.
- The store is an OCI image layout and nothing else is durable.
- A useful tool can be promoted to a real registry with no format change.
- MCP servers are upstreams.
- Every Kubernetes capability keeps working, unchanged.
- The proxy runs on a laptop with no registry, no database and no Docker.

**Non-Goals:**

- A registry service, catalogue API or web UI. The proxy reads and writes a
  layout; it does not serve the Distribution API. (epos-registry exists.)
- Sandboxing Bash or stdio MCP servers. See D11 — the honest answer is a
  capability gate, not a sandbox.
- Multi-tenancy, ownership, moderation or review. That is what makes this a
  scratchpad and not agentregistry.
- Reconciling store-added tools back into CRDs via a controller. The issue
  explicitly defers this ("Afterwards we can think of some kind of
  reconciliation with a controller… But it's out of scope for now").
- Defining a new artifact format. See D1.

## Decisions

The nine questions the research left open are settled here as D1–D9, each with
the alternative that was rejected. D10–D13 settle what drafting turned up. D14–D18
settle what spec review turned up — all five are integration facts about the
existing code that the first draft got wrong or left silent, and each would have
been discovered during implementation at a much worse moment.

### D1: Adopt epos#51's `vnd.epos.tool.*` format unchanged

A stored tool is an OCI image manifest with `artifactType`
`application/vnd.epos.tool.script.v1+json`, the empty config descriptor
`application/vnd.oci.empty.v1+json`, and exactly one layer of media type
`application/vnd.epos.tool.script.layer.v1+tar` carrying the payload. The
document envelope is epos's Kubernetes-style `apiVersion: epos.dev/v1alpha1`,
`kind: Tool`. Annotations use the `dev.epos.*` namespace, and MCP servers carry
`io.modelcontextprotocol.server.name`.

This is the owner's own format, defined in gaarutyunov/epos#51, and AgentIQ
already depends on this proxy dispatching on it (`agentiq/SPEC.md` §3.2). A
second format would make "more universal" false on the first day.

- *Rejected — a `vnd.mcpanything.tool.*` namespace.* It buys freedom to change
  the shape without coordinating with epos, and costs the one property the owner
  asked for. If the format needs to change, the change belongs in epos#51.

### D2: Use `oras-go` v2 directly, and share the wire format rather than a library

`pkg/toolstore` imports `oras.land/oras-go/v2` and implements pack, push,
resolve, tag, untag and delete against a local `content/oci.Store`. It does not
import epos.

This is not a preference. epos's store, packing and registry client are under
`internal/` and therefore **cannot be imported from another module** — and epos
`main` has no Go code at all yet. Waiting for epos to publish a `pkg/` API would
block #142 on a change that is itself still open (epos#51), and the API that
issue proposes is *resolve-only*: it exposes `Resolve` and the `Closure` types,
with no public pack or push. `Add` needs pack and push. There is no version of
"depend on epos" that unblocks this change.

Interoperability is preserved where it matters — **at the wire format** (D1). An
artifact this proxy writes is one `epos pull` can read, and vice versa, because
both are ordinary OCI artifacts with the same media types.

**This diverges from AgentIQ's posture, and the divergence should be stated
precisely rather than overstated.** AgentIQ's `.golangci.yml` depguard rule
(`agentiq/SPEC.md` §17.2) denies `oras.land/oras-go/v2` in every package except
`artifact/`, with the rationale "OCI access goes through the epos API, in
`artifact/` only". That rule is **scoped to AgentIQ's own module**; it does not
bind sibling projects, and mcp-anything is not in violation of anything. What it
expresses is a *direction of travel* — one OCI client per system, owned by epos —
and this design departs from that direction for the reason above. The mitigation
is to make the departure reversible: `pkg/toolstore` is the **only** package
permitted to import `oras-go`, enforced by mcp-anything's own depguard rule,
mirroring AgentIQ's. If epos later ships a public pack/push API, the swap is one
package.

- *Rejected — vendor or fork epos's `internal/store`.* Copies drift, and the
  locking discipline (D3) is the part most expensive to have drift.
- *Rejected — shell out to the `epos` CLI.* It puts a binary on the critical path
  of an MCP tool call, and the proxy ships as a single static binary today.
- *Rejected — `go-containerregistry`.* No native `artifactType` support, which
  D1's dispatch (and AgentIQ §3.2's third requirement) is built on.

### D3: Locking, atomic index writes, local filesystem only

The store copies epos's fix verbatim, because the failure it prevents is silent:

- Advisory file locks via `github.com/rogpeppe/go-internal/lockedfile` — a
  maintained export of the Go toolchain's own implementation. Pure Go, `flock`
  on Unix, `LockFileEx` on Windows.
- **Shared** lock for resolve, fetch and index rebuild; **exclusive** for pack,
  push, tag, untag, delete and retention.
- `AutoSaveIndex: false`; the store writes `index.json` itself via temp file →
  `fsync` → `os.Rename`.
- The `oci.Store` is opened **inside** the lock, so the on-disk index is read
  fresh. This is the step that is easy to omit and that makes the rest useless.
- Every `Fetch` reader is closed before any `Delete`, per the v2.6.2 doc comment.

The store directory MUST be on a local filesystem. Advisory locks are unreliable
over NFS and SMB, and the proxy fails loudly at startup rather than corrupting an
index slowly. In Kubernetes this means an `emptyDir` or a local PV, never a
shared `ReadWriteMany` volume — which is also why D5 exists.

**Detection is best-effort, and the asymmetry is deliberate.** Filesystem type is
`statfs` magic numbers on Linux, `f_fstypename` on Darwin, and something else
again on Windows, and the proxy ships on all three via goreleaser. So: a
**positively identified** network filesystem (NFS, SMB/CIFS, and the obvious
others) is a startup refusal naming the path; an **undeterminable** filesystem
logs a warning naming the path and continues. Refusing on "don't know" would
break ordinary local filesystems the detection simply has not been taught, and
this check exists to catch the one configuration people actually reach for by
mistake — a shared volume — not to prove locality.

### D4: The index is derived, in-memory, and reads annotations only

At startup, and after every `Add` or `Delete`, the proxy walks `index.json`,
reads each tagged manifest, and builds an in-memory index from **manifest
annotations only**. It never fetches a layer blob to populate the index.

This is the highest-leverage single decision in the design, so it is stated as a
constraint on the format rather than on the code: **`dev.epos.name`, the tool
description, the runtime, and a flattened parameter list live in manifest
annotations.** Layers are fetched only when a tool is executed. A store with 500
tools costs 500 small manifest reads at startup and zero blob reads, and `Search`
never touches a blob at all.

The index is a pure function of the layout. It is never written to disk, never
migrated, and a crash loses nothing. **"No database" does not mean "no index" —
it means the index is not the source of truth.** Say this plainly, because the
first person to want faster startup will propose persisting it.

**Concurrency: an immutable snapshot behind an `atomic.Pointer`.** The index is
read by `Search` while `Add` and `Delete` rebuild it, and `make test` runs
`-race`, so the model has to be stated rather than left to the implementor. A
rebuild constructs a **new** index value and swaps it in; nothing is mutated in
place and no reader takes a lock. This is the pattern `config.Loader` already
uses for `atomic.Pointer[ProxyConfig]` and that `upstream.Registry` already
follows by being "immutable after construction and safe for concurrent reads"
(`pkg/upstream/registry.go:95`) — reusing it means one concurrency model in the
proxy rather than two. A `Search` that began before an `Add` completes reads a
consistent older snapshot, which is the correct answer for a scratchpad.

- *Rejected — SQLite or bbolt for the index.* It is a database with a different
  name, and it reintroduces exactly what the owner removed: a second durable
  thing that can disagree with the first.
- *Rejected — the OCI Referrers API for discovery.* It answers "what refers to
  this?", not "what tools exist?", and it needs a registry; there is no local
  equivalent.
- *Rejected — an `application/vnd.oci.image.index.v1+json` catalogue artifact.*
  It would need updating on every `Add`, making a write to one tool a rewrite of
  a shared object — the write contention a scratchpad least wants.

### D5: `Add` writes to the configured store; promotion is separate and explicit

`Add` writes to **the store the deployment configured**, which is the local
layout by default. It never pushes to a remote registry as a side effect.

Promotion is a distinct, explicit operation — `oras.Copy` from the local layout
to a configured registry, exposed as an argument to `Add` (`promote: true`) and
as a CLI subcommand. Nothing is published because an agent experimented.

This interacts with D6 and the two must not contradict: in a deployment that
configures a registry as the source of truth (§ *Multiple replicas*), "the
configured store" **is** that registry, and `Add` writes there. Promotion still
means "copy to a *different*, more permanent registry". The rule in one sentence:
`Add` writes to the store the proxy reads from; promote copies to a store the
proxy does not read from.

### D6: Multiple replicas — see the named section below

This is the question where "no Postgres" is under genuine strain, and it is
answered in its own section rather than as a decision bullet, because the honest
answer is longer than one.

### D7: An OpenAPI tool is one artifact per operation, with `runtime: openapi`

epos#51's `Tool` document enumerates `runtime: bash | js | lua`. mcp-anything has
four sources, so `openapi` must be added — proposed to epos#51, with
mcp-anything treating the enum as open (carry an unknown runtime through, refuse
to execute it) so #142 is not blocked on that issue.

The shape needs care, because there is a real mismatch: epos#51's `Tool` is **one
artifact, one tool**, while an OpenAPI document is **one document, N tools**. The
resolution is that an `Add` of an OpenAPI source stores **one artifact per
selected operation**, whose layer carries an OpenAPI document pruned to that one
operation, plus the base URL and the outbound-auth reference. `spec.entrypoint`
names the document inside the tar.

That is not a workaround; it is what the scratchpad motivation actually
describes. An agent extracting "the call I keep making to create a GitHub issue"
is extracting one operation, not importing the GitHub API. Bulk import of a whole
API remains what the existing `http` upstream is for, declared in config, and is
untouched.

**The base URL and the credential must not be independently choosable, or
`Add` becomes a credential-exfiltration primitive.** An agent that can name both
an arbitrary base URL *and* an existing named `outbound_auth` entry has asked the
proxy to attach that upstream's token to a request at a URL the agent chose. D11
dismisses OpenAPI as "network egress only", which is true of the *existing* http
upstream — where an operator wrote the base URL — and false of an `Add`-ed one.

The rule, therefore: an `Add`-ed OpenAPI tool MAY name an existing
`outbound_auth` entry **only** when its base URL is the base URL of the upstream
that owns that credential. Any other base URL is permitted but is sent
**unauthenticated**. Requesting a credential for a foreign base URL is an error
naming both, not a silent downgrade — a silent downgrade would leave an agent
believing the call was authenticated. Deployments wanting a broader pairing
configure an explicit allowlist; there is no wildcard.

- *Rejected — one artifact per whole OpenAPI document.* It gives the derived
  index one entry covering N tools, so `Search` can no longer return tools, which
  defeats the token economy the feature exists for.
- *Rejected — a sibling `vnd.epos.tool.openapi.v1+json` type.* Defensible, and it
  is the cleaner modelling if epos#51's owner prefers it. Not chosen because it
  doubles the dispatch surface for one field's worth of difference, and because
  `runtime` is already the discriminator. **This is the weakest of the nine
  positions and the one most worth overruling.**

### D8: MCP servers are referenced by remote URL or local stdio command; container images are optional

A local-first proxy cannot require Docker, so the reference forms are, in
preference order:

1. **A remote Streamable HTTP endpoint** — a URL and an outbound-auth reference.
   No process, no image, works identically on a laptop and in a cluster.
2. **A local stdio server** spawned by the proxy — `npx`, `uvx`, or any command
   on `PATH`. This is how MCP servers are distributed in practice today.
3. **A container image**, used only where a container runtime exists. In
   Kubernetes that is a sidecar the operator declares; the proxy never shells out
   to Docker.

epos#51 covers only form 3: "For an MCP server tool, the referenced artifact is
an ordinary container image and the `Tool` document is omitted". That is
insufficient here, and the gap is worth naming because it is a *finding about
epos#51*, not a decision of this change. The extension proposed back to epos#51
is small and faithful to its own wording — epos#51 already calls the server's
`server.json` "authoritative", so let the artifact **be** the `server.json`:
`artifactType` `application/vnd.epos.tool.mcp.v1+json`, one layer carrying
`server.json`, manifest annotated `io.modelcontextprotocol.server.name`. The MCP
Registry's `server.json` schema already models all three forms (`remotes[]`,
`packages[]` with npm / pypi / oci), so nothing new is invented. Until epos#51
accepts it, mcp-anything writes that media type in its own store and the format
is a one-line change if the name is rejected.

### D9: Config and CRD win over the store; a default prefix makes it rare

Two rules, in order:

1. **Structural.** Store-added tools get their own tool prefix, default `scratch`
   (configurable). So `scratch__create_issue` cannot collide with a configured
   upstream's `github__create_issue` at all. This reuses `{prefix}__{tool}` and
   `MCPUpstreamSpec.ToolPrefix` — mechanism that already exists.
2. **Precedence, as a backstop for a deployment that deliberately shares a
   prefix.** The declarative source wins. A store tool whose fully-qualified name
   collides with a config- or CRD-declared tool is **shadowed**, logged at WARN,
   and reported in `Search` results as shadowed. `Add` of a colliding name fails
   with an error naming the winner, rather than writing an artifact that will
   never be callable.

The direction is not arbitrary: an operator's reviewed declaration must not be
silently displaced by an agent's mid-session write. The reverse rule would make a
cluster's behaviour depend on what an agent did five minutes ago.

**Where this meets the existing fatal checks, and why they are not weakened.**
`registry.New` today treats *both* a shared `tool_prefix` and a duplicate
prefixed name as construction errors (`pkg/upstream/registry.go:125,135`), and
`Rebuild` validates prefixes before that. Rule 2 above must not turn those into
warnings — a config with two upstreams claiming one prefix is a deployment
mistake and must keep failing loudly. The two rules live at different points in
the pipeline and that is what keeps them consistent:

- **Declared versus declared** — config and CRD upstreams, including an `mcp`
  upstream — stays **fatal**, unchanged, inside `registry.New`.
- **Store versus declared** resolves **before** `registry.New` is called. The
  store is presented as one synthetic upstream (D14), and its entry list is
  filtered against the declared names first: a colliding stored tool is dropped
  from the list, logged, and marked shadowed in `Search`. `registry.New`
  therefore never sees the collision and never has to be taught to tolerate one.

So `Add`'s pre-flight rejection (rule 2) and the load-time fatal error are the
same rule applied at two different times, not two rules that disagree.

- *Rejected — last-write-wins.* Makes the proxy non-deterministic across
  restarts, since the store survives a restart and a race does not.
- *Rejected — leaving it undefined.* The collision is reachable in one
  configuration line; undefined behaviour here is a support burden.

### D10: Upgrade `modelcontextprotocol/go-sdk` v1.4.1 → v1.7.0

Recommended, sequenced as its own task with the acceptance criterion that every
existing transport and every existing tool keeps working.

The reason is not novelty. MCP revision `2026-07-28` makes the protocol core
**stateless** — the `initialize` handshake and `Mcp-Session-Id` are removed — and
mcp-anything's SPEC.md §1 already promises "No database. No persistent state.
Every pod is identical." The proxy has been paying to carry session state that
the protocol now says it should not have. The same revision adds header-based
routing (`Mcp-Method` / `Mcp-Name`) explicitly aimed at proxies, and cacheable
list results: both let a client invoke one tool without a `tools/list` round
trip, which is the same token economy #142 exists for, arriving through the
protocol instead of through a tool.

**Caveat, stated rather than hidden:** the v1.7.0 API surface and the exact
contents of revision `2026-07-28` come from the research pass and are not
verified in this repo — `go.mod` was read (v1.4.1) but the newer SDK was not.
Implementation MUST confirm both before committing to the upgrade, and MUST fall
back to keeping v1.4.1 (deferring the stateless-core work to its own issue) if
the upgrade turns out to be breaking in ways this change cannot absorb. The
store, the four tools and MCP upstreams do not depend on it.

### D11: Four runtimes are four security boundaries, and the spec says so

The runtimes are not interchangeable, and presenting them as four uniform "tool
types" would be the most damaging thing this document could do:

| Source | Mechanism | Isolation |
| --- | --- | --- |
| JavaScript | Sobek, in-process, pooled, timeout via `vm.Interrupt` | Sandboxed interpreter. No filesystem, no exec; network only via `ctx.fetch`. |
| Lua | gopher-lua, in-process, pooled | Sandboxed interpreter, same shape. |
| Bash | `os/exec` subprocess, optionally `sh -c` | **None.** Full authority of the proxy process — its filesystem, its network, its service-account token, its environment. |
| OpenAPI | Outbound HTTP through the existing pipeline | Network egress only, but reaches anything the proxy can reach. |
| MCP over stdio | Spawned process | **None**, same as Bash, and it is a *long-lived* process rather than a one-shot. |

The consequence is a **capability gate, not a sandbox**: each source is
individually enable-able, and the two unsandboxed ones — `bash` and `mcp-stdio` —
default to **off**. Turning them on is a deliberate act by whoever deploys the
proxy, in the same config file that grants it credentials.

OCI signing (cosign via the Referrers API, per epos and epos#51) is worth having
and does not help here: it establishes **attribution** — who packed this
artifact — not **isolation**. A signed Bash script runs with exactly the
authority an unsigned one does. AgentIQ's SPEC.md §9.6 already frames the stdio
case correctly — "spawned by the proxy and inherit its trust boundary — this is
documented as a deliberate security property of the deployment, not a defect" —
and this design adopts that framing and extends it to Bash.

### D12: `Search` returns names, descriptions and parameters — never a full schema

`Search` exists to save tokens. If a hit costs more than regenerating the command
would have, the feature is a net loss, so its response shape is a specified
contract and not an implementation detail.

A result carries: the fully-qualified tool name, the description (truncated to a
configured budget, default 200 characters, **truncated on rune boundaries** — the
repo's own `.claude/rules/review-patterns.md` lists byte-slicing a user-facing
string as a repeat review finding), and a **flattened parameter list** — one line
per top-level parameter as `name: type` plus required/optional, with no nested
schemas, no per-property descriptions, no enums and no examples. The full
`inputSchema` is never returned.

This is safe because `Execute` validates arguments server-side against the full
schema and returns an actionable error naming the offending parameter. The agent
needs to know *which* parameters exist, not their complete JSON Schema.

**This is a new result type, and `search.ToolDef` is left alone.** An earlier
draft removed `InputSchema` from `search.ToolDef` (`pkg/search/search.go:20`).
That is wrong twice over: it changes what the *existing* `search_tools` tool
returns in every deployment — including one with no store configured, which this
change promises is byte-for-byte unaffected — and it breaks
`tests/integration/tool_search_test.go:202`, which asserts `inputSchema` is
non-nil for every hit. `store_search` gets its own bounded result type; the
existing `search_tools` contract is untouched. Narrowing `search_tools` may well
be worth doing on its own token-economy merits, but it is a separate change with
a separate compatibility story, and it is filed as a follow-up rather than
smuggled in here.

The budget is enforced, not merely intended: a `Search` response has a configured
maximum size, results are truncated to fit, and the response says how many were
elided.

### D13: A lexical fallback when no embedding provider is configured

`pkg/search` embeds via chromem-go, and every built-in provider (OpenAI, Cohere,
Mistral, Jina, Vertex, Azure…) is a **network call**; the one local option
(`hugot`) is a heavy separate dependency. A local-first proxy that must call
OpenAI to search its own scratchpad is not local-first, and on a laptop with no
API key `Search` would simply not work.

So when no embedding provider is configured, `Search` falls back to lexical
matching over the same derived index — substring and token overlap on name,
description and parameter names — and says which mode it used. Semantic search
stays the better answer when a provider is available; it stops being a
prerequisite for the feature to exist.

This was not in the research and is a genuine gap: the existing `search_tools` is
an opt-in extra for a large configured catalogue, where requiring an embedding
provider is reasonable. `Search` in #142 is the *primary* discovery path, and a
primary path may not have a network dependency.

### D14: The store is one synthetic upstream, and `Rebuild` must re-materialise it

"`Add` mutates the live registry" is not implementable as stated. `Registry` is
"immutable after construction and safe for concurrent reads"
(`pkg/upstream/registry.go:95`). The seam that does exist is
`upstream.RegistryManager` (`pkg/upstream/refresher.go:16`) —
`UpdateUpstream(name, entries, specYAMLRoot)` and `RemoveUpstream(name)` — which
rebuilds and swaps the whole registry under the manager's lock. `Add` and
`Delete` go through that, presenting the store as **one synthetic upstream**
named for the store prefix (`scratch` by default).

Modelling it as one upstream rather than N is what makes D9's precedence rule and
the existing prefix machinery fall out for free, and it is the smallest thing
that fits a seam already there.

**The failure this decision exists to prevent:** `Manager.Rebuild(ctx, cfg)`
(`pkg/mcp/manager.go:201`) reconstructs the upstream set from `cfg.Upstreams`,
and it is invoked by the fsnotify config watcher in `pkg/config/loader.go`.
Unless the store's entries are re-materialised **inside** `Rebuild`, any
unrelated edit to the config file silently deletes every added tool from the live
registry, with no error and no log line — the tools are still in the store, so
they come back on the next restart, which makes the bug intermittent and
maddening. `Rebuild` must therefore treat the store as a source of upstreams
alongside `cfg.Upstreams`. This is a required behaviour with a test, not a note.

### D15: Wire names are snake_case, and the four tools survive the `tools/list` collapse

Two integration facts decide this, and both were missed by the first draft.

**Naming.** Issue #142 writes "Search, Execute, Add, Delete" as prose. Every MCP
tool this proxy actually exposes is snake_case (`search_tools`,
`github__create_issue`), and `Registry.Dispatch` rejects names without the `__`
separator. A bare `Add` is also a plausible collision with an upstream's own
tool. The wire names are therefore **`store_search`, `store_execute`,
`store_add`, `store_delete`**, and the spec uses those. The capitalised words
remain the right way to talk about them in prose.

**Visibility.** `listToolsMiddleware` (`pkg/mcp/manager.go:627`) returns *only*
`search_tools` from `tools/list` whenever tool search is enabled for an endpoint.
Left alone, that is precisely the deployment most likely to configure a store —
and the four store tools would be invisible in it. So the middleware returns
`search_tools` (when enabled) **plus the four store tools**, which is the minimum
that keeps the feature reachable while preserving the collapse's whole point.

That settles the redundancy question too:

- **Stored tools are ordinary registry entries** under the store prefix, so
  `scratch__create_issue` is dispatchable by name like any other tool. A client
  that already knows the name pays nothing extra.
- **They are omitted from `tools/list`** whenever the store is configured.
  Listing them is exactly the per-session token cost the feature exists to avoid.
- **`store_execute` is how an agent calls one it just found**, without a
  `tools/list` round trip. It is a name→dispatch shim over the same registry
  entry, not a second execution path with its own semantics.

`store_search` does **not** replace `search_tools`: the two coexist, search
different sets (the store versus the configured catalogue) and return different
shapes (D12). A deployment with both enabled has both, and that is intended.

### D16: The registry connection is configured, credentialed and bounded

Promotion (D5) and the registry-backed store (§ *Multiple replicas*) both talk to
a remote registry, and neither says how. Unspecified, this is where an
implementor invents something. The `tool_store` config block therefore carries,
explicitly:

- **Credentials**, via the repo's existing `${ENV_VAR}` indirection for anything
  secret — never a literal in the config file. `oras-go` needs a `remote.Client`
  with a credential function; the config supplies username/password or a bearer
  token per registry host, and falls back to an ambient Docker config file only
  when the deployment opts in.
- **A per-operation timeout** on every pull, push and `oras.Copy`, defaulted, and
  a `context.Context` threaded from the caller. The repo's own
  `.claude/rules/review-patterns.md` lists missing HTTP client timeouts as a
  repeat finding.
- **A refresh interval** for the pull-through cache, defaulted, and the explicit
  statement that this interval *is* the staleness bound the multi-replica section
  describes.
- **TLS settings** per host, including a plain-HTTP opt-in for a local registry,
  because a laptop-local `zot` is the intended promotion target for testing.

### D17: No Cobra in this change; promotion is an MCP argument, and the CLI is a follow-up

D5 mentions "a CLI subcommand" for promotion. `cmd/proxy/main.go` has no CLI
framework at all — no flags, no subcommands; it calls `mcpanything.LoadConfig()`
and `proxy.Start(ctx)`, and `spf13/cobra` is present only as an indirect
dependency of golangci-lint. Introducing Cobra means a `NewRootCmd()` factory,
turning today's `main()` into a `serve` subcommand, and a new direct dependency —
a structural change to the binary that has nothing to do with issue #142 and that
the proposal's Impact section does not carry.

So promotion in this change is the `promote: true` argument to `store_add` plus a
`Promote` operation on the store package, and **no CLI is added**. A promotion
subcommand is a good idea and is filed as a follow-up, where the Cobra adoption
can be scoped and reviewed on its own.

### D18: Tests follow the target repo's conventions, not the workspace's defaults

The first draft specified godog feature files. **The repo has never used godog**:
there are no `.feature` files, godog is not in `go.mod`, and `tests/integration`
and `tests/e2e` are plain Go tests over Testcontainers behind build tags, as
`.claude/rules/integration-tests.md` and `.claude/rules/e2e-tests.md` document.
Adding a BDD framework for one feature would leave the repo with two testing
idioms. The tests here are plain Go, table-driven, in the existing directories.

The same reasoning resolves a live conflict with the workspace-level rules. This
workspace's `go-test-assertions.md` mandates testify and `go-test-mocks.md`
mandates generated gomock. mcp-anything uses **neither** — no `stretchr/testify`
import anywhere (it is indirect only), no `mockgen`, hand-rolled fakes
throughout. Introducing both into one new package would make that package the odd
one out in its own repo while satisfying a rule written for the workspace's
greenfield Go projects. **Consistency within the repo wins**, and the divergence
is recorded here rather than silently taken, so that the owner can overrule it in
review if the intent was the reverse.

## Multiple replicas: where "no Postgres" is under strain

This deserves its own section because it is the one place where the storage
decision has a cost that the decision does not pay for, and a footnote would
misrepresent it.

**The problem.** A local OCI layout is per-process and, in Kubernetes, per-pod.
Three replicas behind a Service means `Add` on pod A produces a tool that pods B
and C do not have. The next `tools/list` or `Execute` lands on a different pod
and the tool is not there. Postgres would not have had this problem: one
database, three readers, immediately consistent.

**Say this plainly: choosing OCI relocates the consistency problem rather than
solving it.** OCI's content addressing gives reproducibility and portability, not
coordination. What it does give is that concurrent `Add`s of *identical* content
converge on the same digest, so replicas cannot disagree about what a tool *is* —
only about whether they have it yet.

**The recommended answer: registry as source of truth, local layout as
pull-through cache.**

- A multi-replica deployment configures a registry. That registry is the store
  (D5), and it is where `Add` writes.
- Each pod keeps a local layout as a **cache**, and refreshes it on an interval
  and on cache miss.
- `Add` is: pack → push to registry → invalidate local → the tool is live on this
  pod immediately.
- Other pods see it after at most one refresh interval.

**The consequences, stated honestly rather than mitigated away:**

- **`Add` is eventually consistent across replicas**, bounded by the refresh
  interval. An agent that adds a tool and calls it in the next request may get
  "unknown tool" from a different pod. The mitigation is sticky sessions or a
  single replica — both of which are real constraints, not workarounds.
- **`Delete` is worse than `Add`**, because a tool that should be gone remains
  callable on other pods for up to one interval. Where that matters, delete via
  the registry and accept the window, or run one replica.
- **The write path now depends on the registry.** A registry outage makes `Add`
  fail. The local-only mode has no such dependency, which is a genuine argument
  for the laptop case and against the cluster case.
- **With no registry configured, multi-replica is unsupported.** The proxy MUST
  refuse to start in that combination rather than serving an inconsistent tool
  set silently. A loud refusal at startup is the whole value of naming this
  problem.

  **How the pod knows, since it cannot read its own replica count.** A pod has no
  access to its Deployment's `spec.replicas`; discovering it would mean a
  Kubernetes API read of the owning Deployment plus the RBAC to allow it, which
  the proxy does not have today and should not acquire for this. The check is
  therefore driven by **declared** configuration, not by discovery:

  - The `tool_store` block carries an explicit `shared: true|false`, defaulting
    to `false` (a single process owns this store).
  - The proxy refuses to start when `shared: true` and the store is local-only.
    That is the whole rule, and it is one comparison.
  - **The Helm chart and the operator set it**, because they are the components
    that *do* know the replica count — the chart renders `replicaCount` and the
    operator writes the `MCPProxy`'s replica count into the rendered config. A
    chart rendering `replicaCount: 3` with a local-only store fails at template
    time with the same message, which is better than failing at pod start.

  The cost of this design is honest and worth stating: a hand-rolled Deployment
  that scales to three replicas without setting `shared` gets no refusal. The
  chart and the operator are the supported paths and they are covered; a
  hand-written manifest is not, and the config reference says so.

**Rejected alternatives**, each for a reason worth recording:

- *A shared `ReadWriteMany` volume.* Directly contradicts D3: advisory locks are
  unreliable over NFS and SMB, so this trades a visible inconsistency for a
  silent index corruption.
- *Gossip or leader election between replicas.* Builds a distributed system to
  avoid a database, which is the trade in the wrong direction.
- *Postgres for the cluster case only, OCI for local.* Two storage backends, two
  code paths, two sets of bugs, and the format stops being universal — which was
  the owner's stated reason for OCI in the first place.
- *Requiring one replica always.* Too strong: the read path scales fine, and most
  deployments will add tools rarely and read them constantly.

## Risks / Trade-offs

- **[`Add` executes agent-authored code with the proxy's authority]** — the
  central risk of the whole design, and it is not fully mitigable. D11's
  capability gate defaults the unsandboxed sources off; inbound auth already
  governs who may call `Add`. What remains: anyone who can call `Add` on a proxy
  with `bash` enabled has a shell in that pod, with its service-account token.
  The spec must say that, because a deployment that does not know it will enable
  bash for convenience.
- **[The store is per-pod by default]** — see the section above. Accepted, with a
  startup refusal for the configuration that would be silently wrong.
- **[The derived index rebuild is O(tools) at startup]** — manifest reads only
  (D4), so it is small, but a store that grows without bound makes startup grow
  with it. Retention (below) bounds it; a store of thousands of tools is outside
  the design's intent and should be a registry.
- **[Retention deletes something an agent still wanted]** — keep-last-N per name
  is a heuristic. Mitigated by scoping it to *versions of one name* rather than
  distinct tools, by never collecting a tool referenced by the live registry
  snapshot, and by making N configurable with retention off as a valid setting.
- **[Depending on an unmerged format]** — epos#51 is open, and D7 and D8 both
  propose extensions to it. If it merges with a different shape, this change's
  media types and annotations change. That is a one-package edit (D2's
  containment rule) and is cheaper than the alternative of inventing a format
  that would then need reconciling.
- **[The go-sdk upgrade is unverified]** — D10 records this explicitly and makes
  the rest of the change independent of it.
- **[`Search`'s truncation can hide a needed parameter]** — D12 flattens to top
  level, so a deeply nested request body appears as one object parameter. The
  compensation is that `Execute` validates and its error names the missing field;
  the agent learns by calling rather than by reading. This is a deliberate trade
  of one failed call against a full schema on every search hit.
- **[SPEC.md has already drifted from the code]** — this change corrects §1, §2
  and §4, but the §5 layout section describes an `internal/` tree the repo no
  longer has. Fixing all of it is out of scope; the sections this change touches
  are corrected and the rest is left, which means the drift is reduced, not
  eliminated.
