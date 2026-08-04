## Why

epos#51 is not a feature request. Its body **is** the specification — "the
remainder of this document is the format specification itself, written to be
lifted into the epos repository" — and it has already been adopted by a
downstream consumer. This change lifts it, reconciles it with epos as epos
actually is, and fixes the places where the two disagree.

Two consumers are waiting, and they are waiting on different things:

> **epos** must ship before M3: new artifact kinds; reference composition;
> **a public Go API (`pkg/`) exposing resolution and closure types** — "AgentIQ
> calls `Resolve` inside a DBOS step; shelling out to the CLI is not viable
> inside workflow code"; recursive resolution with cycle detection and a depth
> limit. — `agentiq/SPEC.md` §3.2

> **D1: Adopt epos#51's `vnd.epos.tool.*` format unchanged.** … "This is the
> owner's own format, defined in gaarutyunov/epos#51." — `mcp-anything#142`

The second is the load-bearing one. `mcp-anything#142`'s spec is written, and it
chose **not** to invent a tool format on the explicit grounds that epos owns one.
That makes the `tool` kind specified here a **published contract with a
committed consumer before a single line of it exists.** A silent divergence
would not be a design debate; it would be a break.

**"AgentIQ M3 cannot ship until this is in a tagged epos release."** epos has
**no tags and no releases** — `git tag` is empty and `gh release list` is empty.
`.github/workflows/release.yml` fires on `v*` and `.goreleaser.yaml` builds two
binaries across six platforms, and **neither has ever run.** The release is not a
formality at the end of this change; it is the first exercise of an untested
pipeline, and it is where the change finishes.

### What the issue does not say, and this change had to find

- **`SPEC.md` §2.2 forbids exactly what the issue asks for.** Verbatim: *"The
  `vnd.epos.*` namespace is reserved for Epos-native concepts, which must never
  alter the skill artifact. **v2.0 defines no such types.**"* §15 goes further —
  *"`vnd.epos.*` media types — No Epos-native wire concept survived the design."*
  The reservation was made and then deliberately left unspent. This change spends
  it, and says so in §2.2 rather than around it (design D1).
- **An OCI descriptor has no repository field.** An index's `manifests[]` are
  resolved **within the same repository**, so "publishing an agent means
  publishing five or more artifacts" means publishing them into **one**
  repository. That collides head-on with §2.1's *"one skill per repository"*
  convention, and it is also the only reason the issue's own claim that
  `oras copy --recursive` "transfers the whole closure" is true (design D3).
- **The issue's `org.opencontainers.image.created` annotation would break
  epos's determinism invariant.** `internal/artifact/build.go` builds its
  manifest **by hand instead of using `oras.PackManifest`** precisely to keep
  that timestamp out, and `internal/sign/attach.go` omits it for the same reason.
  Two features assert it: *"Packing the same directory twice produces the same
  digest"*, *"Two identical directories produce the same digest"* (design D4).
- **`epos pull` refuses digest references** (`runPull`, `internal/cli/pull.go`),
  and §4.4 of the issue makes digest resolution mandatory: *"A conforming
  consumer MUST resolve a tag to a digest before execution."* A format whose
  central rule is "pin the digest" cannot ship on a CLI that cannot pull one
  (design D14).
- **Nothing in epos handles more than one artifact.** Every artifact-touching
  command is `cobra.ExactArgs(1)`. There is no batch mode, no `--recursive`, no
  closure and no dependency resolution anywhere in the CLI or the store.
- **The issue never says how a producer *names* a reference.** §5.1 shows
  `skills: [pdf-forms]` — a name resolved against an index entry — but nothing
  says how `pdf-forms` became an index entry in the first place, and §1.3
  forbids a build language to express it. The gap is filled here (design D6).
- **The issue's cycle-detection rationale is inverted.** It says the graph is
  "acyclic unless a cycle is constructed deliberately across two mutable tags."
  A content-addressed graph cannot contain a cycle *at all* — a digest cannot
  cover itself. What the `visited` set actually prevents is **exponential
  re-fetching of a diamond**, and the issue's pseudocode passes it down the
  recursion path-scoped, which does not prevent that. The behaviour changes:
  memoise globally and return the cached closure, do not error (design D7).
- **`agentiq/SPEC.md` §8.4's `Resolve(ctx, ref string) (epos.Closure, error)`
  is not implementable as written.** Resolution needs a registry client,
  credentials, a plain-HTTP switch and a store root. A bare package function has
  nowhere to get them but ambient global state (design D10).
- **Two of the issue's own examples are broken.** §5.4's
  `inputSchema: { $ref: "#/schemas/input" }` points into a document that has no
  `schemas` key; §5.1's `callbacks.beforeAgent: [audit-log]` is a name resolved
  *in the runtime's registry*, which §8's conformance rule — *"fail resolution if
  the definition references a name absent from the index"* — would reject
  (designs D16, D15).
- **epos#44 (PR #53) is in flight and moves the ground under this change.** It
  hoists every registry conversation into a new `internal/registry` package and
  makes it the single owner of `CheckPath`; `internal/skillfile/tree.go`'s
  `checkPath` is now a one-line delegation to it. New artifact fetching belongs
  there, not in a second copy. It leaves `internal/store` untouched and adds
  exactly one function to `internal/artifact`, so the packing and locking ground
  is stable. It also adds `cmd/epos/imports_test.go` — an import-hygiene guard
  asserting which packages each binary may link.

## What Changes

- **Four new document kinds — `Agent`, `Instruction`, `Model`, `Tool` — and
  eight new media types** under `vnd.epos.*`, with the `epos.dev/v1alpha1`
  envelope. `SPEC.md` §2.2's "v2.0 defines no such types" and §15's "no
  Epos-native wire concept survived" are **amended by name**, not quietly
  outgrown. §2.2's actual prohibition — *must never alter the skill artifact* —
  is preserved literally: a skill referenced by an agent is byte-identical to the
  skill epos packs today, and `internal/artifact` gains no new field (design D5).
- **An agent is an OCI image index whose `manifests[]` are annotated
  descriptors.** Reference composition sits beside `Skillfile` merge composition
  and shares nothing with it: `Skillfile` composes *files* into one artifact;
  an index composes *artifacts* by reference, inlining nothing and merging
  nothing. `internal/skillfile` is not touched, and no `Skillfile` instruction is
  added — which matters, because `reference.go`'s `instructionTable` is the
  single source for both the builder's dispatch and the generated docs page.
- **A closure is published into one repository.** `epos push` copies the whole
  closure — definition, instruction, model, every skill, every tool, every
  sub-agent index — into the agent's own repository, then pushes the index last.
  A referenced skill is *copied*, not linked, because a descriptor cannot name
  another repository. Its origin reference is recorded in an annotation so the
  copy is auditable; the skill's own repository stays its canonical publication.
  `<registry>/<namespace>/agents/<agent-name>` is the documented convention, and
  `push` does **not** enforce it: the destination names a namespace and the
  agent's name is appended, exactly as for a skill, because `pushReference`
  already documents why guessing at a destination is unsafe (design D3).
- **`epos pack` takes an agent directory and writes a closure.** One command,
  one exclusive store lock, N artifacts, one index tag. A directory's kind is
  decided by one marker file at its root — `agent.yaml`, `tool.yaml`,
  `instruction.md`, `model.yaml`, beside the existing `SKILL.md` — because
  `runPack` opens `SKILL.md` unconditionally today and "detect an agent
  directory" has no meaning until something is named. A sub-directory becomes a
  referenced artifact; an entry that names an existing artifact by reference is
  resolved to a digest at pack time and never re-resolved afterwards. `Agent` and
  `Tool` documents carry `metadata.version`, because the store addresses an
  artifact as `<name>:<version>` and taking it only from `-t` would make an
  artifact's identity unreproducible from its source (design D6).
- **The definition document carries the reference it was authored against.**
  `skills: [pdf-forms]` stays valid for anything packed from the directory
  itself; `skills: [{name: pdf-forms, ref: ghcr.io/…/pdf-forms:1.2.0}]` names
  something already published. Both publish as written — the document is **never
  rewritten at pack time**, because a rewritten document is neither what the
  author reviewed nor byte-reproducible. Resolution reads the *index entry*, so
  the `ref` is provenance and never a re-resolution (design D6).
- **Recursive resolution with a global memo and a depth limit.** `MaxDepth` is
  16. A digest already resolved returns its cached closure rather than being
  re-fetched or refused, which is what stops a 16-deep diamond costing 2^16
  fetches. `ErrCycleDetected` survives, narrowed to what it can actually catch:
  a store whose bytes do not match their digests (design D7).
- **Resolution fetches documents, not payloads.** Definition, instruction, model
  and tool documents are small and bounded, and are fetched. Skill content layers
  and tool script payloads are **not** — they are returned as descriptors plus
  manifest annotations, and materialised only when asked for. Otherwise a DBOS
  step that resolves one agent pulls hundreds of megabytes inside a workflow
  step (design D8).
- **A public Go API at `pkg/epos` — and it is not resolve-only.** It exposes
  `Resolve` and the `Closure` types that `agentiq/SPEC.md` §8.4 names, **and**
  `Pack`, `Push` and the store handle, because `mcp-anything#142`'s D2 rejected
  depending on epos partly on the grounds that "the API that issue proposes is
  *resolve-only* … `Add` needs pack and push. There is no version of 'depend on
  epos' that unblocks this change." That objection is removed here rather than
  argued with (design D9). `pkg/` and `internal/` are in the same module, so
  nothing is restructured to reach it: the format types are **declared in**
  `pkg/epos` and `internal/agent` imports them, rather than being mirrored across
  a conversion layer maintained in both directions forever.
- **`Resolve` is a method on a `Resolver`, and there is no package-level form.**
  Resolution needs credentials, a store root, a plain-HTTP switch and a timeout;
  a function taking only a reference could get them only from ambient process
  state, and a hidden input is exactly what makes a durable step
  non-reproducible. `agentiq/SPEC.md` §8.4 changes one signature rather than epos
  shipping an API it would have to document as the wrong one to call (design
  D10).
- **The `tool` kind is specified as the contract `mcp-anything#142` already
  bought.** Three things it needs that the issue does not give it, each decided
  here rather than left to divergence: a **standalone tool manifest is
  self-describing** — `dev.epos.name`, `dev.epos.runtime`, title and description
  live in the *manifest's own* annotations, because `#142` builds its index from
  annotations alone and never fetches a layer (D11); `spec.runtime` is an **open
  enum with `openapi` registered in it** (D12); and MCP server tools gain
  `application/vnd.epos.tool.mcp.v1+json` carrying `server.json`, keeping the
  issue's container-image form as an alternative rather than the only option
  (D13).
- **`epos pull` accepts a digest.** For agents it must; for skills the existing
  refusal becomes an inconsistency the moment agents can, so it is lifted for
  both (design D14).
- **Signing is unchanged and now covers more.** A cosign signature over the
  index transitively covers the closure, because every reference carries its own
  digest. `internal/sign` gains nothing; `epos sign` learns one new subject.
- **Discovery works for free where it works at all.** An agent index carries
  `org.opencontainers.image.title` and `.description` — the same two annotations
  `epos list`/`search` already read at step 4 of §7.2 — so agents enumerate
  through `_catalog` with no new endpoint, no Epos media type and no change to
  §7's limits. Rendering agents in epos#44's catalog frontend is **out of scope**
  and named as such (design D19).
- **What epos does not become.** No API server, no database, no web UI, no
  registry service, no build language for agents, no tag resolution at execution
  time. Restated because the issue restates it, and because a change that adds a
  public API and a multi-artifact CLI is exactly where that line gets crossed by
  accident.
- **A tagged release.** `agentiq/SPEC.md` §3.2 blocks on a tag, and epos has
  never cut one.

## Capabilities

### New Capabilities

- `epos-agent-artifact-format`: the four kinds, their media types, the document
  envelope, the annotation set, the index rules, and producer/consumer
  conformance.
- `epos-reference-composition`: reference composition as a peer to `Skillfile`
  merge composition — how a closure is authored, how a reference is named, the
  one-repository rule, and the guarantee that the skill artifact is untouched.
- `epos-closure-resolution`: recursive resolution, the global memo, the depth
  limit, digest verification, and what resolution does and does not fetch.
- `epos-public-go-api`: `pkg/epos` — `Resolve`, the `Closure` types, `Pack`,
  `Push`, the store handle, and what the package promises about stability.
- `epos-multi-artifact-cli`: `epos pack`, `push` and `pull` over a whole
  closure in one command, digest references, signing the index, and discovery.
- `epos-tool-kind-contract`: the `tool` kind as a standalone, self-describing
  artifact — annotation requirements, the open `runtime` enum, and MCP server
  tools.

### Modified Capabilities

<!-- epos predates OpenSpec in this workspace and has no capability specs under
     openspec/specs/, so there are none to amend. epos's own SPEC.md is the
     project's reference and is amended by this change: §2.2 and §15 (the
     `vnd.epos.*` prohibition), §2.1 (the repository convention), §6.1 (`pull`
     by digest, `pack`/`push` over a closure), §7 (discovery, unchanged and
     stated so), §12 (a new Track C), §13.4 (`pkg/` in the project tree). Each
     amendment is a named task in milestone C0. -->

## Impact

- **`internal/agent/` (new)**: the whole format — document types and their
  parsing, the index builder, the validator, and the resolver. It is where a
  reader will look for "what is an agent artifact", and nothing else in epos
  needs to know.
- **`internal/registry`**: the closure fetcher lands here, beside epos#44's
  `Client`, `FetchReferenceContent` and `CheckPath`. `Client` gains index
  fetching and referrer-safe descriptor traversal. **No second OCI client.**
- **`internal/artifact`**: unchanged in behaviour. `CollectionType`
  (`application/vnd.agentskills.collection.v1`) is **declared and unused today**
  — it stays unused; an agent index is not a skill collection and this change
  does not repurpose it.
- **`internal/store`**: unchanged. The closure is many blobs and one index
  written under **one** exclusive lock via the existing
  `Store.Push(ctx, tag, write)` seam; `Prune`'s mark-and-sweep already walks
  `content.Successors`, which reaches an index's `manifests[]` — verify, do not
  assume, that an agent tag keeps its whole closure alive.
- **`internal/skillfile`**: **untouched.** No instruction is added to
  `reference.go`'s `instructionTable`, and `Tree`/`Build` see no agent concept.
- **`internal/cli`**: `pack` gains agent-directory detection; `push` gains
  closure copy; `pull` gains digest references; `sign`/`verify` gain an index
  subject. `list`/`search` are unchanged in code and gain agents by annotation.
- **`pkg/epos/` (new)**: the only exported package in the repository. It holds
  the format's document and closure types and exports no machinery — no store
  internals, no registry client, no locking — and no third-party type beyond
  `ocispec.Descriptor`.
- **`cmd/epos/imports_test.go`**: epos#44's import-hygiene guard must be
  extended, not sidestepped — `pkg/epos` must not pull `internal/catalog`,
  ClickHouse or goldmark into the CLI binary.
- **`SPEC.md`**: §2.1, §2.2, §6.1, §7, §12, §13.4 and §15, plus a new section
  for the agent artifact format and one for the public Go API.
- **`features/`**: two new feature files — `package-an-agent.feature` and
  `resolve-an-agent.feature` — read by godog runners in `tests/integration`.
  Feature files stay canonical and are never copied into the test tree (§13.3).
- **`go.mod`**: **no new dependency.** Everything needed is already there —
  `oras-go` v2.6.2, `image-spec` v1.1.1, `go-digest`, `goccy/go-yaml`,
  `lockedfile`. A format change that needs a new dependency would be the wrong
  format.
- **No migration.** No agent artifact exists anywhere yet, and no existing skill
  artifact changes shape.
</content>
