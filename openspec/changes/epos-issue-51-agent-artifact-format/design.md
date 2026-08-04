## Context

Read against `gaarutyunov/epos` `origin/main` at `77ab541`, the in-flight
`origin/issue-44` (PR #53, 80 files), `agentiq/SPEC.md` at `fe56fd0`, and
`openspec/changes/mcp-anything-issue-142-oci-tool-store/` on
`spec/mcp-anything-issue-142`. These facts shape every decision below.

**The base clone's working tree is stale and must not be trusted.** Local `main`
is at `781266b` and contains only `README.md`, `SPEC.md`, `features/`. There is
no `internal/` on disk. All code, and a `SPEC.md` ~6 KB longer than the one on
disk, live on `origin/main`. §2.1, §2.3–2.5, §7 and §9 are byte-identical
between the two; §4.5 and §5.4 are withdrawn on `origin/main` and `push` is
added to §6.1.

**§2.2 forbids this change's central move, in as many words.**

> The `vnd.epos.*` namespace is reserved for Epos-native concepts, which **must
> never alter the skill artifact**. **v2.0 defines no such types.** Overlays
> became `Skillfile` (§8), which produces ordinary conformant artifacts, and
> discovery is served by the registry's own `_catalog` (§7) rather than by an
> Epos-specific representation.

§15 "Removed from scope" repeats it: *"`vnd.epos.*` media types — No Epos-native
wire concept survived the design."*

**Determinism is engineered, not incidental.** `internal/artifact/build.go`
assembles `ocispec.Manifest` by hand rather than calling `oras.PackManifest`,
specifically because `PackManifest` stamps `org.opencontainers.image.created`.
`internal/artifact/pack.go` sorts entries lexicographically, zeroes `ModTime`,
`Uid` and `Gid`, uses `tar.FormatPAX` and sets `gzip.Header{OS: 255}` so the
gzip stream carries no mtime and no filename. `internal/sign/attach.go` omits
`created` from the signature manifest so two signatures of one artifact are
byte-identical. Three feature scenarios assert the result.

**The skill artifact's own shape is inherited, not chosen.** §2.1: skills
conform to the *Agent Skills OCI Artifacts* specification, with a real config
blob `application/vnd.agentskills.skill.config.v1+json` mirroring `SKILL.md`
frontmatter and inlined into the descriptor's `data` field. The OCI empty
descriptor appears in exactly one place in the repository —
`internal/sign/attach.go`, for cosign referrers.

**`internal/store` is a solved problem and this change does not reopen it.**
`Store.withLock` opens `oci.New(root)` *inside* the lock, sets
`AutoSaveIndex=false`, and `writeJSONAtomic` does `CreateTemp` → `Write` →
`Sync` → `Rename`. `store.lock` sits at `<root>/store.lock`, a sibling of the
layout, not inside it. `Push` takes an exclusive lock and hands the caller a
`*oci.Store`; `Read`, `Resolve` and `Tags` take a shared one. GC is
`Store.Prune` only — mark-and-sweep from tagged manifests over
`content.Successors` — and §9.3 states there is "no automatic collection, no
reference counting, no GC roots, no leases."

**Nothing in epos handles two artifacts.** Every artifact-touching command is
`cobra.ExactArgs(1)`; `push` is `ExactArgs(2)` where the second argument is a
destination namespace. `runPush` calls `oras.Copy(ctx, st, tag, repo, version,
oras.DefaultCopyOptions)` under a *shared* store lock. `runPull` and `runPush`
both refuse digest references.

**epos#44 has already claimed the registry seam.** `internal/registry` now owns
`Client` (Catalog / Tags / Annotations / Manifest / FetchContent / Host),
`FetchReferenceContent`, `UnpackContent`, `MaxContentLayer` and `CheckPath`.
`internal/skillfile/tree.go`'s `checkPath` is a one-line delegation to it, and
`internal/skillfile/oci.go` lost 168 lines to it. `internal/store` and
`internal/artifact`'s pack/build path are untouched by that branch.

**`mcp-anything#142` has committed to this format before it exists.** Its D1
adopts `application/vnd.epos.tool.script.v1+json`, the empty config descriptor,
one layer of `application/vnd.epos.tool.script.layer.v1+tar`, the
`epos.dev/v1alpha1` / `kind: Tool` envelope and the `dev.epos.*` annotation
namespace, rejecting a `vnd.mcpanything.tool.*` namespace on the grounds that
"if the format needs to change, the change belongs in epos#51." Its D4 builds
the searchable index from **manifest annotations only** and never fetches a
layer blob. Its D2 declines to *import* epos, partly because "the API that issue
proposes is *resolve-only*", and its task 1.3 says D2 is reopened if a `pkg/`
tree with pack and push appears.

**epos has never released.** `git tag` is empty; `gh release list` is empty.
`.github/workflows/release.yml` triggers on `v*`, and `.goreleaser.yaml` builds
`epos` and `epos-registry` for linux/darwin/windows × amd64/arm64 with
`CGO_ENABLED=0`. Neither has ever executed.

-----

## Goals / Non-Goals

**Goals.** Lift epos#51's specification into epos as a normative section;
reconcile it with §2.1, §2.2, §2.4, §7, §9 and §13.4; deliver the `tool` kind as
the contract `mcp-anything#142` has already bought; give AgentIQ an importable
`Resolve`; make `epos pack` and `epos push` handle a closure in one command;
cut the first tagged release.

**Non-goals.** An API server, a database, a web UI, a registry service. A build
language for agents. Tag resolution at execution time. Rendering agents in
epos#44's catalog frontend. An agent *runtime* — epos packages, resolves and
publishes definitions and executes nothing.

-----

## Decisions

### D1: `SPEC.md` §2.2 is amended by name, not circumvented

§2.2 says "v2.0 defines no such types" and §15 says no Epos-native wire concept
survived. Both statements become false, and both are edited. What §2.2 *forbids*
— that a `vnd.epos.*` type "must never alter the skill artifact" — is not
relaxed by a word, and D5 shows it is honoured literally.

The distinction matters because the two sentences have different standing.
"v2.0 defines no such types" is a **statement of fact about a version**; it
expires the moment a version defines one. "Must never alter the skill artifact"
is a **constraint**, and it survives untouched. Rewriting the first without
touching the second is the whole of the reconciliation.

- *Rejected — reuse `application/vnd.agentskills.collection.v1`.* It is declared
  in `internal/artifact/artifact.go` and used nowhere, so it is available. It is
  also **not epos's type**: it belongs to the Agent Skills specification, which
  gives it a meaning (a collection of skills) that an agent index is not. Taking
  someone else's reserved identifier for a different concept is worse than
  spending a reservation epos made for itself.
- *Rejected — leave §2.2 alone and note the exception in the new section.* Two
  sections of one document contradicting each other is how a specification stops
  being read.

### D2: The new kinds use the OCI empty config; the skill kind keeps its own

Every manifest this change creates sets `config` to
`application/vnd.oci.empty.v1+json` and carries exactly one layer, as epos#51 §4.2
requires and `mcp-anything#142` D1 has already implemented against.

That is *not* what a skill manifest does — a skill's config is a real blob of
`application/vnd.agentskills.skill.config.v1+json` mirroring `SKILL.md`
frontmatter. The inconsistency is only apparent: **the skill's shape is
inherited from the Agent Skills specification, not chosen by epos** (§2.1,
"conform to"), and it exists because a skill has frontmatter worth exposing
without fetching a layer. An `Instruction` is a Markdown blob with no
frontmatter; a `Model` is four scalars. There is nothing to put in a config that
is not already in the document or in an annotation, and inventing one would make
the same information addressable two ways.

The empty descriptor is a fixed, known blob — digest
`sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a`, size
2, content `{}` — and `internal/sign/attach.go` already pushes it via
`ocispec.DescriptorEmptyJSON`, so this introduces no new mechanism.

### D3: A closure is one repository, because a descriptor has no repository

**An OCI descriptor carries a media type, a digest and a size. It does not carry
a repository.** An index's `manifests[]` are resolved relative to the repository
the index was fetched from. Therefore an agent's entire closure must exist in the
agent's own repository, and `epos push` **copies** every referenced artifact
there.

Consequences, all of them real:

1. **The repository convention gains a second form, and `push` does not enforce
   it.** §2.1's `<registry>/<namespace>/agent-skills/<skill-name>` stays for
   skills; agents are `<registry>/<namespace>/agents/<agent-name>`. One agent per
   repository, for the same reason as one skill per repository: the repository
   name identifies the artifact without a manifest lookup.

   **`epos push` treats the destination exactly as it does today** — a namespace,
   to which the artifact's own name is appended, always. `pushReference`
   (`internal/cli/push.go`) documents why: *"the skill's name is appended,
   **always** — including when the last path segment already equals the skill's
   name … Detecting and de-duplicating a destination that already ends in the
   skill's name is not safe."* The user writes `oci://ghcr.io/acme/agents` for an
   agent exactly as they write `oci://ghcr.io/acme/agent-skills` for a skill.
   epos inserts no segment of its own, because a rule that silently inserts
   `agents/` produces `…/agents/agents/<name>` the first time someone follows the
   convention, and the existing anti-de-duplication rationale says why guessing
   is worse than appending.
2. **A referenced skill is duplicated.** Registries deduplicate blobs *within* a
   repository, not across them, so a skill referenced by four agents is stored
   five times. This is the price of a spec-defined mechanism, and it is the same
   price Helm pays for vendored subcharts. It is bounded — skills are small, and
   §2.1 caps a base layer at 64 MiB — and it buys the property the issue
   actually wants: `oras copy --recursive` on the agent's repository moves the
   whole closure with no epos-specific knowledge.
3. **Provenance must be recorded or it is lost.** Once copied, nothing in the
   agent's repository says the skill came from
   `ghcr.io/acme/agent-skills/pdf-forms:1.2.0`. The index entry carries
   `dev.epos.source` with the reference the producer resolved. It is
   informational: resolution never reads it, and never re-resolves it (§4.4).
4. **The skill's own repository remains canonical.** The copy is a pin, not a
   republication; `epos list` and `epos search` continue to enumerate the
   canonical one.

- *Rejected — a reference form that names a repository.* It would work, and it
  would stop being OCI. Every registry, every `oras` client and every mirroring
  tool would have to learn epos's addressing, which is the opposite of the
  reason §1.1 chose OCI.
- *Rejected — push each artifact to its own repository and let the index dangle.*
  It produces an index no registry can traverse and no `oras copy --recursive`
  can follow, which silently breaks garbage collection at the registry and
  breaks the closure the first time anything is pruned.

### D4: Determinism beats `org.opencontainers.image.created`

epos#51 §3 lists `org.opencontainers.image.created` as *recommended* on the index
and on manifests. epos's packing path exists in its present hand-rolled form
**specifically to keep that annotation out**, and three feature scenarios assert
the consequence.

The rule: **`created` is omitted by default, on every manifest and on the
index.** `epos pack --created=<RFC3339>` sets it explicitly, and the help text
states in one line that doing so forfeits digest determinism. epos#51's
"recommended" is honoured as "supported and available", which is what a
recommendation can mean without overturning a delivered invariant.

- *Rejected — set `created` to the wall clock, as recommended.* It makes
  "packing the same directory twice produces the same digest" false, and that
  scenario is a delivered A2 gate.
- *Rejected — set `created` to the Unix epoch.* A constant timestamp is a lie
  that costs the same bytes as no timestamp and looks like data.

### D5: Reference composition never touches the skill artifact

§2.2's surviving prohibition is satisfied by construction, and the tasks assert
it rather than asserting the intention:

- `internal/artifact`'s constants, `Build`, `BuildFiles`, `PackDir` and
  `PackFiles` are unchanged. No new annotation is added to a skill manifest.
- A skill entering a closure is **copied by digest** — `oras.Copy` over the
  descriptor — never repacked. Its manifest digest at the destination equals its
  digest at the source, and a feature scenario asserts exactly that.
- `internal/skillfile` gains nothing. No instruction is added to
  `reference.go`'s `instructionTable`, which is the single source for both the
  builder's dispatch and the generated docs page (§14.1), and whose every
  `Example` is executed by `TestDocumentedExamplesBuild`.

The two composition models are peers precisely because they do not meet:
`Skillfile` merges *files* at build time and produces one conformant skill;
an index composes *artifacts* at pack time and inlines nothing. An agent may
reference a skill that a `Skillfile` built; a `Skillfile` may never reference an
agent.

### D6: An agent is a directory with named documents, and the document is published as written

epos#51 §5.1 shows `skills: [pdf-forms]` and §1.3 forbids a build language, so
nothing in the issue says how `pdf-forms` becomes an index entry, what file the
`Agent` document lives in, or where a tool's document sits inside its payload.
`runPack` (`internal/cli/pack.go`) opens `filepath.Join(dir, artifact.SkillFile)`
— `SKILL.md` — and errors if it is absent, so "detect an agent directory" has no
meaning until a marker exists. Three things get names.

**The marker files.** A directory is classified by exactly one document at its
root, and the file name *is* the discriminator — the kind inside it is validated
against the name, never used to find it:

| File at the directory root | Kind |
|---|---|
| `SKILL.md` | a skill (unchanged) |
| `agent.yaml` | `Agent` |
| `tool.yaml` | `Tool` |
| `instruction.md` | `Instruction` |
| `model.yaml` | `Model` |

Two markers in one directory is a pack-time error naming both, because guessing
which one the author meant is how a directory silently packs as the wrong kind.
A sub-directory named by the definition is classified the same way, so
`skills/pdf-forms/SKILL.md` is a skill and `tools/fetch-invoice/tool.yaml` is a
tool with no per-list convention to remember.

`instruction.md` and `model.yaml` are found by role rather than by name in the
definition, matching epos#51 §5.1 where `instruction:` and `model:` name a role
and not an entry.

**A tool's document lives inside its payload, at `<tool-name>/tool.yaml`.**
epos#51 §4.2 gives every manifest "exactly one layer carrying the document **or**
payload", and a script tool has both. The layer is therefore a tar rooted at
`<tool-name>/` — the same root convention §2.1 already fixes for a skill's
content layer, produced by the same deterministic `PackDir` — containing
`tool.yaml` and the entrypoint's files. This has to be said explicitly: it is
information `mcp-anything#142` does not have, since its D1 adopted the layer
media type as "carrying the payload" with nothing said about the document.

**Every packable document carries `metadata.version`.** `resolveTag` requires
`<name>:<version>` and reads `version` from `SKILL.md` frontmatter; `splitStoreTag`
(`internal/cli/push.go`) requires the same form. An `Agent` or a `Tool` packed on
its own therefore needs a version, and taking it only from `-t` would make the
store tag unreproducible from the source directory — which D4's determinism
argument and 3.4's "the published blob is a pure function of the source file"
both depend on. `metadata.version` is required on `Agent` and `Tool`; `-t`
overrides it exactly as it does for a skill. `Instruction` and `Model` are never
packed alone — they exist only inside a closure — and do not need one.

**The reference forms.** Two authoring forms, one resolution rule:

```yaml
skills:
  - pdf-forms                                       # packed from ./skills/pdf-forms
  - name: invoice-ocr                               # already published
    ref: ghcr.io/acme/agent-skills/invoice-ocr:1.2.0
```

- A **bare name** MUST correspond to a sub-directory of the pack context, which
  `epos pack` packs into the closure. A bare name with no such directory is a
  pack-time error naming the name and the path it looked for.
- A **mapping with `ref`** names something already published or already in the
  local store. `epos pack` resolves it to a digest **once**, copies it into the
  closure, and records the reference in `dev.epos.source` (D3).

**The document is never rewritten at pack time.** A rewritten document is not
what the author reviewed, not what a reviewer diffed, and not reproducible from
the source directory. The published document keeps whichever form was written;
the *index entry* is what resolution reads, so a `ref` is provenance and never a
re-resolution — which is what §4.4's "MUST NOT re-resolve a tag during an
execution" requires.

This also makes both `mcp-anything#142`'s and AgentIQ's assumptions hold: a
consumer only ever reads names and index entries, exactly as epos#51 §6's
pseudocode does.

- *Rejected — a separate `agent.lock` or `refs.yaml`.* §4.4 is emphatic that
  there is no lock file, and it is right: the index *is* the lock.
- *Rejected — rewrite `ref` forms to bare names at pack time.* It makes the
  published artifact differ from the source for no gain, and destroys the one
  record of where a vendored copy came from.

### D7: Resolution memoises. It does not detect cycles, because there are none

epos#51 §6 says cycle detection "is sound because the graph is content-addressed
and therefore acyclic unless a cycle is constructed deliberately across two
mutable tags — which resolution to digest already prevents."

The conclusion is right and the reason is wrong, and the wrong reason produces
the wrong code. **A content-addressed graph cannot contain a cycle at all.** For
index A to reference index B which references A, A's digest would have to cover
bytes containing A's digest. That is a preimage attack on SHA-256, not a
configuration mistake. No arrangement of mutable tags creates one, because tags
are resolved before any descriptor is followed.

What *is* reachable, and what the issue's pseudocode does not prevent, is a
**diamond**. The pseudocode passes `visited ∪ {entry.digest}` **down** the
recursion — path-scoped — so two siblings referencing the same sub-agent each
resolve it in full. Sixteen levels of that is 2^16 resolutions of the same
bytes.

The rule:

- `visited` is a **map from digest to resolved closure, shared across the whole
  resolution**, not a set passed down one path.
- A digest already resolved **returns its memoised closure**. It is not an
  error. A legitimate agent that names the same sub-agent twice must work.
- `MaxDepth` is 16 and `ErrDepthExceeded` is the real structural guard.
- **Every fetched blob is verified against its descriptor digest**, which is what
  makes the acyclicity argument true rather than assumed. `oras-go`'s
  `content.FetchAll` verifies; the requirement is that nothing bypasses it.
- `ErrCycleDetected` **survives as an assertion, and epos is documented as never
  returning it in practice.** Its only reachable case is a digest encountered
  while its own resolution is still in progress, and the bullet above makes that
  unreachable: a store returning mismatched bytes fails verification *before* the
  bytes are parsed, so the failure surfaces as a verification error and never as
  a cycle. It is kept for two reasons and no others — `agentiq/SPEC.md` §8.4
  names it as part of the API, and it is the assertion that catches a future
  resolver change that bypasses the verifying fetch path. It is therefore
  **tested with a deliberately non-verifying fetcher in a unit test, and is not a
  godog gate**, because it cannot be produced against a real registry. Its doc
  comment says all of this, so nobody downstream writes a live branch on it.

### D8: Resolution fetches documents, not payloads

A `Closure` is **identity and configuration**, not bytes.

| Fetched by `Resolve` | Not fetched |
|---|---|
| The index | Skill content layers (`…skill.content.v1.tar+gzip`) |
| Definition, instruction and model documents | Script tool payloads (`…tool.script.layer.v1+tar`) |
| MCP server descriptors (`…tool.mcp.layer.v1+json`) | MCP server container images |
| Every referenced manifest and its annotations | |

**A script tool's document is not fetched, because it is inside the payload.**
D6 puts `tool.yaml` at `<tool-name>/tool.yaml` in the tar, and the tar is the
one layer. A tool is therefore returned exactly as a skill is — descriptor plus
manifest annotations — and D11 is what makes that sufficient: name, runtime,
title and description are on the manifest precisely so a consumer can list and
dispatch a tool without opening it. `spec.inputSchema` arrives with the payload,
at the moment a consumer materialises the tool in order to run it, which is when
it needs the schema anyway. `mcp-anything#142` D4 already works this way from the
other side — it indexes on annotations and fetches the layer only to execute.

An MCP server tool is the one exception, and it is not a payload: its layer is a
small JSON document, it carries no executable bytes, and the reference forms a
consumer needs in order to *connect* are all inside it. It is fetched.

Skills and script tool payloads are materialised only by an explicit call.

Two consumers force this. `agentiq/SPEC.md` §8.4 calls `Resolve` **inside a DBOS
step**; a step that pulls a 64 MiB skill layer per skill has a retry cost and a
timeout profile nobody designed for, and AgentIQ's `Project` writes rows, not
files. `mcp-anything#142` D4 refuses to fetch a layer to index a tool at all.
Resolving an agent should cost tens of kilobytes.

`agentiq/SPEC.md` §8.4 sketches `Skills []SkillDoc`, which reads like content.
It is a descriptor and its config; AgentIQ is told (see "Changes consumers must
make").

### D9: `pkg/epos` exposes pack and push, not resolve alone

epos#51 asks for "a public Go API under `pkg/` exposing `Resolve` and the
`Closure` types". `mcp-anything#142` D2 declined to depend on epos and gave
resolve-only as one of its reasons:

> the API that issue proposes is *resolve-only*: it exposes `Resolve` and the
> `Closure` types, with no public pack or push. `Add` needs pack and push. There
> is no version of "depend on epos" that unblocks this change.

Its task 1.3 then says D2 is **reopened** if a `pkg/` tree with pack and push
appears on epos's default branch. So the surface is `Resolve` + `Closure` +
`Pack` + `Push` + a store handle. Removing a stated objection is cheaper than
arguing it, and the API is not larger for it: pack and push already exist inside
`internal/`; publishing them is a façade, not a design.

Three things this decision explicitly does **not** claim:

1. **It does not unblock `mcp-anything#142`, and must not be sequenced as if it
   did.** That change ships against its own `pkg/toolstore`, and it is right to
   — epos has no tag, and #142 cannot wait for one. D9 makes the swap #142
   promised ("if epos later ships a public pack/push API, the swap is one
   package") *possible*, not scheduled.
2. **It does not weaken #142's other reason for D2.** AgentIQ's `.golangci.yml`
   confines `oras-go` to one package, and #142 mirrors that rule. A `pkg/epos`
   that internally imports `oras-go` is *exactly* a one-package swap under such a
   rule, so D9 is compatible with it rather than in tension.
3. **The binding contract between the three repositories is the artifact, not
   the API.** Every conformance scenario is expressed over bytes in a registry —
   media types, config descriptor, layer, annotations — so a consumer that never
   imports epos is still conformant. That is what makes independent shipping
   safe.

`pkg/` and `internal/` live in the same module (`github.com/gaarutyunov/epos`),
so imports run **either way**, and the direction chosen matters more than it
looks. The **format types are declared in `pkg/epos`** — `Agent`, `Instruction`,
`Model`, `Tool`, `Closure` and the descriptor wrappers — and `internal/agent`
imports them. The obvious alternative, declaring them internally and mirroring
them publicly, buys type-independence at the cost of a conversion layer in both
directions that has to be maintained forever and that will drift the first time
a field is added on one side only.

The independence it would buy is also not worth much here: these types **are**
the wire format. They change when `SPEC.md` changes, which is exactly when a
consumer wants to know. What `pkg/epos` must not export is machinery — no
store internals, no `oras-go` types beyond `ocispec.Descriptor`, which is a
third-party type with its own compatibility promise and is what a descriptor
already is.

### D10: `Resolve` is a method on a `Resolver`, and there is no package-level form

`agentiq/SPEC.md` §8.4 specifies:

```go
func Resolve(ctx context.Context, ref string) (epos.Closure, error)
```

That signature has nowhere to obtain a registry credential, a plain-HTTP switch
for a local `zot`, a per-operation timeout, or a store root — all of which
resolution needs, and all of which `internal/cli`'s `registryOptions` and
`store.Root(explicit)` already carry. A package-level function with only a ref
can work only by reading ambient global state, and ambient credentials inside a
DBOS step is exactly the kind of hidden input that makes a step non-reproducible.

**So the package-level form is not provided at all.** `epos.NewResolver(opts…)`
and `(*Resolver).Resolve(ctx, ref)` are the API. AgentIQ changes one signature.

Shipping the convenience form "so §8.4 compiles verbatim" was considered and
rejected: it would mean exporting a function and documenting in the same breath
that a durable step should not call it, which is how a footgun becomes
permanent. `agentiq/SPEC.md` is a draft that has not been implemented against
this API yet — correcting one line there is cheaper than carrying an ambient
default in a public package for the life of the module. The correction is filed
in "Changes consumers must make".

The option-carrying form is also what makes resolution testable against a `zot`
container without setting process-wide environment variables, which is how every
other integration suite in this repository works.

`Options` covers the store root, the registry configuration path, the
plain-HTTP switch and a per-operation timeout, and it defaults to what the CLI
uses — `EPOS_HOME` or `~/.epos`, and the credentials `epos registry login`
writes. A zero `Options` is therefore usable; it is just not invisible.

### D11: A standalone tool manifest is self-describing

`mcp-anything#142` D4 and its task 3.1 build the searchable index by walking
`index.json` and reading **manifest annotations only**, never a layer. Its task
3.4 skips a manifest missing `dev.epos.name` with a WARN.

epos#51 §3 puts `dev.epos.name` on the **index entry**, and a standalone tool
artifact — one packed and pushed on its own, which is every tool in #142's store
— has no index entry. As written, #142 cannot index its own artifacts.

The rule: a `tool` manifest **carries its own identity in its own annotations**,
whether or not it ever appears in an agent index.

| Annotation | On the tool manifest | Meaning |
|---|---|---|
| `dev.epos.name` | required | the tool's name |
| `dev.epos.runtime` | required for script tools | `spec.runtime`, so dispatch needs no layer |
| `org.opencontainers.image.title` | required | `metadata.name` |
| `org.opencontainers.image.description` | recommended | `spec.description` |
| `dev.epos.tool.params` | optional | top-level parameter names, as a JSON array |

The first two are epos-native; the next two are the keys `internal/artifact`'s
`assemble` already derives for skills and `epos list`/`search` already read, so
this is the house pattern rather than a new one.

`dev.epos.tool.params` is **names only**, and the full `inputSchema` stays in the
layer. Annotations are covered by the manifest digest and counted against
registry manifest-size limits; an unbounded JSON Schema in an annotation makes
the manifest unbounded. #142's `store_search` returns "a flattened parameter
list, and never the full schema", so names are what it needs, and `Execute`
validates against the layer's schema anyway.

Two details that a wire format with an external consumer cannot leave open:

- **The value is a JSON array of strings**, not a comma-separated list. JSON
  Schema property names may contain commas, and a separator with no escape rule
  is a parsing bug waiting for the first tool that hits it. A JSON array needs
  no escape rule and #142 already parses JSON.
- **The cap is 4096 bytes of the encoded value, and exceeding it omits the
  annotation with a warning rather than failing the pack.** The annotation is
  optional; refusing to publish an otherwise-valid tool because its parameter
  list is long would turn an optional index hint into a hard packing
  constraint. A consumer that finds it absent falls back to the layer, which it
  must be able to do anyway. The number is epos's own choice — large enough for
  any plausible parameter list, small enough that the annotation cannot dominate
  a manifest — and is stated as a choice, not derived from a registry limit.

When such a tool *does* appear in an agent index, `dev.epos.name` appears in
**both** places, and the index entry wins. That is not redundancy for its own
sake: the index entry's name is the key the definition document resolves against
and may legitimately differ from the tool's own published name, exactly as an
import alias may differ from a package name.

### D12: `spec.runtime` is an open enum, and `openapi` is registered in it

epos#51 §5.4 gives `runtime: bash | js | lua`. `mcp-anything#142` D7 needs a
fourth, `openapi`, and proposes it back here. Two decisions, and they are
separable:

**`openapi` is added to the enum.** epos validates the field and never executes
it, so the cost of a registered value is one entry in a list. The alternative —
mcp-anything carrying it as a vendor extension — means mcp-anything writes
artifacts that epos's own validator rejects, which falsifies #142's own D1
scenario, *"an artifact written here is readable by epos tooling"*. The
registered set becomes `bash`, `js`, `lua`, `openapi`.

**The enum is open.** An unrecognised `runtime` is **carried, not rejected**:
epos validates the field's presence and type, warns naming the value, and packs,
pushes, pulls and resolves the artifact unchanged. A consumer refuses to
*execute* it, naming the runtime — which is precisely #142's task 4.5. A format
whose producer set is larger than its consumer set needs the closed half to be
"what a runtime will run", not "what a registry will store".

**One-artifact-one-tool is preserved, and it is #142's problem to satisfy.**
epos#51's `Tool` is one artifact, one tool; an OpenAPI document is one document,
N operations. #142 D7 resolves this by storing one artifact per selected
operation, whose layer carries the document pruned to that operation and whose
`spec.entrypoint` names it inside the tar. That needs **nothing from epos** —
the shape already fits — and this change adopts it as the documented convention
for `runtime: openapi` so a second consumer does not invent a different one.

- *Rejected — a sibling `application/vnd.epos.tool.openapi.v1+json` type.*
  #142 D8 calls this "the cleaner modelling if epos#51's owner prefers it" and
  "the weakest of the nine decisions". It is declined because `runtime` is
  already the discriminator and a second discriminator for the same distinction
  is how a format grows two ways to say one thing. Recorded so the owner can
  overrule it in review, since the consumer flagged it as genuinely close.

### D13: MCP server tools get their own media type; the container image stays valid

epos#51 §5.4: *"For an MCP server tool, the referenced artifact is an ordinary
container image and the `Tool` document is omitted."*

`mcp-anything#142` D8 finds three reference forms for an MCP server — remote
Streamable HTTP, a locally spawned stdio process, and a container image — and
epos#51 covers only the third. A remote Streamable HTTP MCP server **has no
container image**, so as written the format cannot express the most common
deployment. #142 calls the gap "a gap in epos#51, not a decision of this change"
and proposes `application/vnd.epos.tool.mcp.v1+json`.

Adopted, with the spelling #142 proposed:

- `artifactType` `application/vnd.epos.tool.mcp.v1+json`, empty config, one
  layer `application/vnd.epos.tool.mcp.layer.v1+json` carrying the MCP
  Registry's own `server.json` **verbatim**. Nothing is invented: `server.json`
  already carries `remotes[]` and `packages[]`, and those are the reference
  forms.
- The manifest carries `io.modelcontextprotocol.server.name`, which MUST equal
  `server.json`'s `name` — as epos#51 §3 already requires of the index entry.
- **The container-image form survives unchanged.** An index entry MAY point
  directly at an `application/vnd.oci.image.manifest.v1+json` with
  `io.modelcontextprotocol.server.name`, exactly as epos#51 §4.1's example
  shows. A consumer distinguishes the two by `artifactType` — never by tag,
  repository name or file extension, which is #142's task 9.4.

epos itself neither connects to an MCP server nor runs a container. It validates
`server.json` as well-formed JSON with a `name` matching the annotation, and
stops there.

**Required annotations bind only to manifests epos creates.** A stock container
image referenced as an MCP server tool carries whatever its builder gave it, and
will usually have no `org.opencontainers.image.title`. Requiring one would make
a conformant closure fail validation for a reason its author cannot fix. The
rule is: epos sets title and description on every manifest it writes; a
referenced foreign manifest is validated on its **index entry's** annotations —
`dev.epos.role`, `dev.epos.name`, and the MCP server name — and on nothing else.
This is also what makes D5's "carried by digest without being annotated" true.

### D14: `epos pull` accepts a digest reference

`runPull` and `runPush` both refuse digest references today. §4.4 of the issue
makes a digest the *only* correct thing to execute against — *"A conforming
consumer MUST resolve a tag to a digest before execution and MUST record the
digest"* — and `agentiq/SPEC.md` §6.3 pins a whole workflow run by
`AgentDigest`. A format built on digests cannot ship on a CLI that cannot pull
one.

`epos pull <ref>@sha256:…` is accepted. A digest names no tag, so something must
decide what the artifact is called in the local store — and that decision is
constrained by `Store.Prune`, whose mark-and-sweep is rooted at **tags**. Storing
it untagged means the next prune collects it.

`epos pull` by digest therefore writes the tag **`<name>:sha256-<hex>`** — the
same `:`-for-`@` substitution cosign uses, valid per the OCI tag grammar
(`[a-zA-Z0-9_][a-zA-Z0-9._-]{0,127}`; `sha256-` plus 64 hex is 71 characters),
and legible in `epos store ls`. The alternative, storing it untagged and teaching
`prune` about a second kind of root, adds an exception to the one piece of this
system §9.3 describes as having "no reference counting, no GC roots, no leases."

The rule is stated in `SPEC.md` §9 so `prune`'s contract does not silently
acquire an exception, and in §6.1 so a user is not surprised by the tag they get.

The refusal is lifted for **skills too**. Once agents can be pulled by digest,
a `pull` that refuses a digest for skills is an inconsistency with no defender.

### D15: Callbacks are not index references

epos#51 §5.1's `callbacks.beforeAgent: [audit-log]` is "resolved by name in the
runtime's registry". §8's consumer conformance says: *"fail resolution if the
definition references a name absent from the index."* Applied to `callbacks`,
that rule rejects every agent that uses one.

The rule is scoped: `skills`, `tools` and `subAgents` are **index references**
and every name in them MUST exist in the index. `callbacks` are **runtime
references**, validated by the runtime and not by epos, and are never checked
against the index. `instruction` and `model` are role references and name a role
rather than an entry.

epos validates that `callbacks` values are non-empty strings and stops.

### D16: `spec.inputSchema` is an inline JSON Schema

epos#51 §5.4 shows `inputSchema: { $ref: "#/schemas/input" }`, pointing into a
document that has no `schemas` key. It is a placeholder, and taken literally it
is unresolvable.

`spec.inputSchema` is an **inline JSON Schema object** (Draft 2020-12). It is
what `mcp-anything#142` needs to validate arguments server-side, and inlining it
keeps a tool document self-contained — which matters because the document is the
unit that gets copied into an agent's repository (D3).

epos validates that it is an object with a `type`, and does no schema-semantics
validation. epos is not a JSON Schema implementation and adding one would put a
new dependency in `go.mod` for a field it never evaluates.

### D17: `subject` for version history is opt-in, and it costs something

epos#51 §4.1 rule 6: the index MAY carry `subject` referencing a previous
version, forming a history discoverable through the Referrers API.

Supported, behind `epos pack --supersedes <ref>`, and off by default — because
it is not free:

- The Referrers list of v1 now returns v2, v3, … **mixed with v1's cosign
  signatures**, which every consumer must then filter by `artifactType`.
- Registry garbage collection treats a referrer as a reason to keep its subject
  alive, so **v1 can never be deleted while v2 exists**. That is sometimes the
  point and sometimes a surprise.
- An index has exactly one `subject`. Spending it on version history means it
  cannot be spent on anything else later.

A default that quietly makes old versions undeletable is the wrong default. The
flag's help text says what it does in one sentence.

**The superseded index is not transferred.** `content.Successors` returns an
index's `Subject` first, so a naive `oras.Copy` of a superseding index would try
to copy the entire previous closure — and would fail outright if the previous
version is not in the local store, which it usually is not. `epos push` skips the
subject, exactly as cosign does when pushing a signature: the subject is expected
to be **already present in the destination**, which is the only situation in
which a version history means anything. If it is absent, the push still succeeds
and the referrers link simply resolves to nothing, which is the registry's
defined behaviour for a dangling subject. `epos pack --supersedes` therefore
needs only the previous version's descriptor — media type, digest, size — and
resolves the reference once to obtain it.

### D18: The code lands in `internal/agent`, on top of epos#44's `internal/registry`

`SPEC.md` §13.4: *"Plain Go. No code generation, no model, no hexagonal
layering, no DDD… Shared code goes in the top-level `internal/` deliberately,
not by default. Interfaces are introduced only where a test or a second
implementation actually requires one."*

- **`internal/agent`** owns the document types, the index builder, the validator
  and the resolver. One package, because a reader asking "what is an agent
  artifact" should have one place to look, and because splitting a format across
  packages is how two halves of it drift.
- **Registry access goes through `internal/registry`.** epos#44 made it the
  single owner of talking to a registry and of `CheckPath`; its `OCIRegistry`
  gains index fetching and descriptor traversal. A second OCI client in
  `internal/agent` would undo that branch's central refactor a week after it
  landed.
- **`internal/registry.Client` does not grow.** It is already a six-method
  interface with generated mocks in three packages
  (`internal/registry/mocks_test.go`, `internal/catalog/mocks_registry_test.go`,
  `internal/cli/mocks_test.go`), and `epos list`'s laziness assertions ride on
  its exact shape. Adding two methods for the resolver's benefit would churn all
  three mock sites and widen an interface for consumers that do not use the new
  methods. The resolver declares its own narrow fetcher **at the point of use**
  — which is where Go says an interface belongs — and `OCIRegistry` and the local
  store both satisfy it.
- **User-supplied paths go through `CheckPath`, not a second copy of the rule.**
  `internal/registry`'s doc comment is explicit: *"One implementation, here,
  because it guards three callers with the same exposure … A second copy is how
  one of them loses a rule."* `spec.entrypoint` and every path inside a tool
  payload tar are user-supplied paths into an archive, so they are validated by
  the same function, at pack time and again at materialise time, and a violation
  is a **conformance** failure so a foreign producer cannot smuggle one past.
- **The store is used through its existing seam.** The whole closure is written
  in one `Store.Push(ctx, tag, write)` call, so N artifacts and the index land
  under **one** exclusive lock. No new locking, no new atomicity mechanism.
- **One interface, and only because a test requires it.** The resolver takes a
  fetcher interface so it can be driven from the local store or a remote
  registry, which is §13.4's stated bar and matches its named example ("the
  upstream registry and the `FROM` resolvers are the likely cases").
- `cmd/epos/imports_test.go` (epos#44) is extended so `pkg/epos` cannot pull
  `internal/catalog`, ClickHouse or goldmark into the CLI binary.

### D19: Discovery works by annotation; the catalog frontend is out of scope

An agent index carries `org.opencontainers.image.title` and
`org.opencontainers.image.description`. Those are the two annotations §7.2's
step 4 already reads, and the ones `internal/artifact`'s `assemble` already
derives for skills. So `epos list` and `epos search` enumerate agents **with no
code change and no new endpoint**, and §7's limits are unchanged: discovery
still requires `_catalog`, is still client-side, and still publishes no Epos
representation. §7's text needs one sentence saying agents are included, not a
rewrite.

One caveat belongs in that sentence, because it is a silent failure otherwise:
§7.2's step 2 filters the catalog to `--namespace`, which defaults to the whole
registry. A user who has standardised on `--namespace acme/agent-skills` will see
no agents at all and no error, because agents live under `acme/agents`. The
namespace has to be the parent of both.

epos#44's catalog frontend renders skills, reading `SKILL.md` bodies through
goldmark. Rendering **agents** there is out of scope and named as such —
epos#51's "it does not gain a web UI" is about not becoming agentregistry, and
this change adds nothing to `internal/catalog`. If the owner wants agents in the
catalog, that is epos#44's successor, not this.

### D20: godog stays the gate; no new test framework and no new dependency

Every milestone gate is godog scenarios in `features/`, run by
`tests/integration` under `//go:build integration` against a real `zot` in
testcontainers, with feature files staying canonical at the repository root
(§13.3, §13.5). Unit tests use `stretchr/testify` and `go.uber.org/mock`, which
is what the repository already does and what `.claude/rules/go-test-assertions.md`
and `go-test-mocks.md` require — the two agree here, unlike in `mcp-anything`.

`go.mod` gains **nothing**. `oras-go` v2.6.2, `image-spec` v1.1.1, `go-digest`,
`goccy/go-yaml` and `lockedfile` cover the whole change. A format that needed a
new dependency to express itself would be the wrong format.

-----

## Changes consumers must make

A tag alone does not unblock either consumer. These are the mismatches found
while reconciling, filed here so they are reported on the issue rather than
discovered downstream.

**AgentIQ (`agentiq/SPEC.md` at `fe56fd0`)**

1. **§8.4's `Resolve(ctx, ref string)` does not exist.** There is no
   package-level form, deliberately: it could only work by reading ambient
   credentials, and a hidden input makes a durable step non-reproducible.
   Construct an `epos.Resolver` with explicit options and call its `Resolve`.
   One signature changes in §8.4 (D10).
2. **§8.4's `Skills []SkillDoc` is descriptors, not content.** `Resolve` does
   not fetch skill layers (D8). If `Project` needs skill *bodies* in
   `agentiq.*` rows, it must materialise them explicitly, and that is a fetch
   with a size and a timeout, not a field access.
3. **§7.6 says "zero or more descriptors annotated `instruction`, `model`,
   skill, tool, subagent."** `instruction` and `model` are capped at **one
   each** (epos#51 §4.1 rule 2). Zero-or-more is wrong for two of the five.
4. **`epos.ErrCycleDetected` will essentially never fire**, and code that
   branches on it as a normal outcome is dead. `ErrDepthExceeded` is the guard
   that fires (D7).

**mcp-anything (`spec/mcp-anything-issue-142`)**

5. **D7's `openapi` and D8's `application/vnd.epos.tool.mcp.v1+json` are both
   accepted**, with D8's exact spelling and one layer of
   `application/vnd.epos.tool.mcp.layer.v1+json`. Task 1.4 can be answered:
   accepted, accepted.
6. **Task 3.4's "a manifest missing `dev.epos.name`" is now a conformance
   violation, not just a WARN-and-skip** — D11 requires the annotation on the
   manifest itself. Skipping remains the right *behaviour*; the artifact is
   non-conformant, and saying so in the log is more useful than "missing
   annotation".
7. **D2 is reopened by task 1.3's own trigger**, but must not be re-decided in
   #142's favour by sequencing: `pkg/epos` will not exist in a tagged release
   before #142 needs it. Ship `pkg/toolstore`; the swap stays available (D9).
8. **`dev.epos.tool.params` is a JSON array of names, capped at 4096 bytes, and
   omitted rather than truncated when it does not fit** (D11). #142's
   `store_search` contract already returns "a flattened parameter list, and
   never the full schema", so this is a narrowing of the annotation, not of the
   tool — but a consumer must handle its absence by falling back to the layer.
9. **A script tool's `Tool` document lives at `<tool-name>/tool.yaml` inside the
   `…tool.script.layer.v1+tar` layer** (D6). #142 D1 adopted that layer as
   "carrying the payload" with nothing said about where the document sits, and
   two implementations that disagree here produce artifacts neither can read.
   The tar's root directory is `<tool-name>/`, matching the skill content
   layer's convention.
10. **`spec.entrypoint` must be a relative, canonical, non-escaping path** and is
    validated as such at pack time and at materialise time (D18). #142
    materialises store-backed scripts to a path and hands it to an executor;
    an unvalidated entrypoint from a foreign artifact is a path-traversal write.

-----

## Risks

- **The first release is an untested pipeline.** `.goreleaser.yaml` and
  `release.yml` have never run; the tag that finishes this change is their first
  execution, across six platform/arch combinations. Budget for the release
  failing on its first attempt, and run `goreleaser check` and a local
  `--snapshot` build before tagging. (This is the same shape as the gopgql
  release-path risk, and there it was real.)
- **epos#44 is unmerged and 80 files wide.** Every claim here about
  `internal/registry` is a claim about a branch. If PR #53 changes shape, D18's
  landing site moves. The mitigation is ordering: C0 re-reads `origin/issue-44`
  before C3 is written, and D18 is reopened rather than patched around.
- **Duplication under D3 is unbounded in the number of agents.** Four agents
  referencing one skill store it five times. Acceptable at this scale, wrong at
  a large one; if it ever bites, the answer is registry-side cross-repo mounting
  (`POST /v2/<name>/blobs/uploads/?mount=`), which is a push optimisation and
  not a format change. Recorded so the format is not blamed later.
- **The `tool` kind is a contract with a consumer that ships first.**
  mcp-anything will write `vnd.epos.tool.*` artifacts before epos can read one.
  The conformance scenarios in C1 and C5 are the only thing that will catch a
  divergence, and they must run against artifacts produced *outside* epos —
  hence the fixture requirement in the C5 gate.
- **A public API is a promise.** `pkg/epos` is the first exported surface epos
  has ever had, and the first tag makes it semver-bearing. It is scoped
  deliberately small, exports the format's types and no machinery, and is
  documented as `v0.x` —
  which is what `agentiq/SPEC.md` should pin against.
</content>
