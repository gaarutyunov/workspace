Milestone-ordered, following `SPEC.md` §12's own idiom: this change is
**Track C — agents**, C0 through C6. Each milestone ends with a **gate**: godog
scenarios in `features/` at the repository root, run by `tests/integration` under
`//go:build integration` against a real `zot` in testcontainers (§13.3, §13.5).
Go unit tests are an inner-loop check only and never satisfy a gate. No milestone
is phased or partial (§12).

Code references are to `origin/main` at `77ab541`. The base clone's working tree
is **stale** — local `main` has no `internal/` at all — so read with
`git show origin/main:<path>` or from `.worktrees/issue-46`, which is
byte-identical to `origin/main` for `internal/`, `cmd/` and `go.mod`.

## 0. C0 — the specification amendments

Sequenced first because it is what the owner is approving. If D1 is not
accepted, nothing below should be written.

- [ ] 0.1 `SPEC.md` §2.2: replace "**v2.0 defines no such types.**" with the four types this change defines, keeping the surviving prohibition — that a `vnd.epos.*` type must never alter the skill artifact — **verbatim and untouched** (design D1). §2.2's remaining sentences about overlays and discovery are unaffected and stay.
- [ ] 0.2 `SPEC.md` §15 "Removed from scope": correct "`vnd.epos.*` media types — No Epos-native wire concept survived the design". It is a statement of fact that this change falsifies; it is edited, not reinterpreted.
- [ ] 0.3 `SPEC.md` §2.1: add the agent repository convention `<registry>/<namespace>/agents/<agent-name>` beside the existing `agent-skills` one, and state the rule behind both — the repository name identifies the artifact without a manifest lookup. State that an agent's closure lives in **one** repository and why (design D3).
- [ ] 0.4 `SPEC.md` — **new section**, the agent artifact format: media types, annotations, the `epos.dev/v1alpha1` envelope, the four kinds, the index rules, resolution, and producer/consumer conformance. This is epos#51's body, lifted, with the corrections D4, D6, D7, D11–D17 make to it. Each correction is marked in the text as a deviation from the issue, so a reader of both is never left guessing which is current.
- [ ] 0.5 `SPEC.md` §6.1: `pack` and `push` operate over a closure; `pull` accepts a digest reference (design D14). Record the tag form a digest pull writes and why (`<name>:sha256-<hex>`), so §9.3's collection contract does not silently acquire an exception.
- [ ] 0.6 `SPEC.md` §7: two sentences — agents are enumerated by the same annotations skills are, so §7.1's limits, §7.2's four steps and §7.3's commands are **unchanged**, and no Epos discovery representation is introduced, since §2.2 makes a point of its absence. The second sentence is the caveat: §7.2's step 2 filters to `--namespace`, so a user who has standardised on `--namespace <ns>/agent-skills` sees **no agents and no error**; the namespace must be the parent of both (design D19).
- [ ] 0.7 `SPEC.md` §9: `prune` reaches an index's `manifests[]` through `content.Successors`, so a tagged agent keeps its closure. **Verified during review** — `oras-go` v2.6.2 `content/graph.go` returns `Subject` plus `index.Manifests` for `ocispec.MediaTypeImageIndex`, so `mark` in `internal/store/store.go` needs no change. Record it in §9 and keep gate 6.15; the contingency is closed. Add the digest-pull tag rule from 0.5.
- [ ] 0.8 `SPEC.md` §12: a new **Track C** table, C1–C6 with their gates, in the same shape as Tracks A and B.
- [ ] 0.9 `SPEC.md` §13.4: `pkg/epos/` in the project tree, with one sentence on why the repository that says "shared code goes in the top-level `internal/` deliberately, not by default" now has an exported package at all (design D9).
- [ ] 0.10 `SPEC.md` §2.4: state that `org.opencontainers.image.created` is omitted by default on the new kinds too, and that `--created` forfeits determinism (design D4). The existing determinism invariants are not weakened.
- [ ] 0.11 Re-read `origin/issue-44` (PR #53) at its then-current head and confirm `internal/registry`'s shape — `Client`, `Options`, `FetchReferenceContent`, `UnpackContent`, `MaxContentLayer`, `CheckPath`. Every claim in D18 is a claim about an **unmerged branch**. If it has changed shape, D18 is reopened here, not patched around in C4.
- [ ] 0.12 Record in the PR description the one thing left that would make this change wrong if it turns out false: that `internal/registry` lands as read (0.11). The other two were verified during review — `content.Successors` traverses an index (0.7), and an `ocispec.Descriptor` carries no repository field, which is what the whole of C6 rests on (D3).

## 1. C1 — the format and its validator

- [ ] 1.1 The document types — `Agent`, `Instruction`, `Model`, `Tool` and the shared `apiVersion`/`kind`/`metadata`/`spec` envelope — are declared in `pkg/epos` from the start, and `internal/agent` imports them (design D9). Declaring them internally and mirroring them publicly in C5 would mean a conversion layer maintained in both directions forever. Parsed with `goccy/go-yaml`, already a direct dependency.
- [ ] 1.2 Media type and annotation constants, exactly as `SPEC.md`'s new section names them, in one file so the format has one source. `dev.epos.spec-version`'s value is `0.1.0` — the **format's** version, not the tool's — and is a constant, not a build variable. `internal/artifact`'s constants are **not** touched.
- [ ] 1.2a Marker-file dispatch (design D6): `agent.yaml`, `tool.yaml`, `instruction.md`, `model.yaml`, beside the existing `SKILL.md`. The **file name** is the discriminator; the `kind` inside is validated against it and never used to find it. Two markers in one directory is an error naming both. `runPack` currently opens `filepath.Join(dir, artifact.SkillFile)` unconditionally, so this is the first thing C3 changes.
- [ ] 1.3 Envelope validation: API version, kind, `metadata.name`. A `status` block at pack time is an error (the field is a consumer's local annotation, §4.3 of the issue). `metadata.version` is **required on `Agent` and `Tool`** — the kinds that can be packed alone — because `resolveTag` (`internal/cli/pack.go`) and `splitStoreTag` (`internal/cli/push.go`) both require `<name>:<version>`, and taking it only from `-t` would make an artifact's identity unreproducible from its source (design D6). `-t` overrides it, exactly as for a skill.
- [ ] 1.4 `Agent` validation: at most one instruction, at most one model; every name in `skills`, `tools`, `subAgents` unique within its list; `callbacks` validated as non-empty strings and **never** checked against the index (design D15).
- [ ] 1.5 `Model` validation refuses any credential-shaped field — key, token, password, secret — naming the field. An artifact is published, and a credential in it is published with it.
- [ ] 1.6 `Tool` validation: `spec.inputSchema` is an **inline** JSON Schema object with a `type` (design D16). No JSON Schema library is added; the field is validated as an object and never evaluated.
- [ ] 1.6a Required manifest annotations bind only to manifests epos writes. A referenced foreign manifest — a skill packed elsewhere, a stock container image used as an MCP server — is validated on its **index entry's** annotations and on nothing else, because it is carried by digest and annotating it would change that digest (design D13).
- [ ] 1.7 Index validation: exactly one `definition`; at most one `instruction` and one `model`; `dev.epos.name` present and unique within role for `skill`, `tool`, `subagent`; a `subagent` entry's `artifactType` is the index type. An **unknown role is carried and reported**, never refused (§8's "MAY ignore roles it does not understand, provided it records that it did so").
- [ ] 1.8 Every manifest this package builds uses `ocispec.DescriptorEmptyJSON` as its config and exactly one layer (design D2). Assert the empty descriptor's digest as a constant so an `oras-go` change cannot move it silently.
- [ ] 1.9 Manifests are assembled **by hand**, mirroring `internal/artifact/build.go`, not via `oras.PackManifest` — `PackManifest` stamps `org.opencontainers.image.created` and would break 1.10 (design D4).
- [ ] 1.10 `org.opencontainers.image.created` is emitted only when explicitly supplied. Unit test: two builds of one input produce identical bytes.
- [ ] 1.11 Typed errors callers must branch on, so tests use `errors.Is`/`errors.As` and not string matching: no definition entry, several definition entries, duplicate name in role, unknown kind, missing envelope field, credential in a model, unrecognised role. Wrapped with `%w`, per the repository's convention.

### Gate — C1

- [ ] 1.12 `features/package-an-agent.feature`, first scenarios: a hand-written agent directory packs into a conformant index in the local store; the index is an ordinary OCI image index that plain `oras` can fetch and parse from a real `zot`.
- [ ] 1.13 Packing the same agent directory twice produces the same index digest; two identical directories produce the same index digest — the §2.4 invariants, asserted for the new kinds.
- [ ] 1.14 An index with two `definition` entries, and one with none, are each refused with the named error.

## 2. C2 — the tool kind as a standalone contract

Placed here, before closures exist, because `mcp-anything#142` needs **the tool
kind** and not the agent kind, and because it can then be reported back on that
issue while the rest of Track C is still being built.

- [ ] 2.1 `epos pack` recognises a `tool.yaml` directory (1.2a) and packs a single tool artifact: `application/vnd.epos.tool.script.v1+json`, empty config, one layer `application/vnd.epos.tool.script.layer.v1+tar` built by `internal/artifact`'s existing deterministic tar path.
- [ ] 2.1a The layer's tar is rooted at `<tool-name>/` — the convention §2.1 already fixes for a skill content layer — and the `Tool` document sits at `<tool-name>/tool.yaml` inside it (design D6). A manifest of these kinds carries exactly one layer and a script tool has both a document and executable files, so where the document sits has to be named or two implementations write artifacts neither can read. **This is information `mcp-anything#142` does not have** (8.6).
- [ ] 2.1b `spec.entrypoint`, and every path in the payload tar, go through `internal/registry.CheckPath` at pack time **and** at materialise time, and a violation is a **conformance** failure so a foreign artifact cannot carry one past. `CheckPath`'s own doc comment is the rule: "One implementation, here … A second copy is how one of them loses a rule."
- [ ] 2.2 The tool **manifest** carries `dev.epos.name`, `dev.epos.runtime`, `org.opencontainers.image.title` and `org.opencontainers.image.description` (design D11). The last two are the keys `internal/artifact`'s `assemble` already derives for skills — same keys, same meaning.
- [ ] 2.3 `dev.epos.tool.params`: top-level parameter names as a **JSON array of strings**, capped at **4096 bytes of encoded value**. Not comma-separated — a JSON Schema property name may contain a comma, and a separator with no escape rule is a parsing bug waiting for the first name that has one. Over the cap the annotation is **omitted with a warning** and packing succeeds; it is an optional index hint, and refusing to publish a valid tool for a long parameter list would turn it into a packing constraint. The full schema stays in the layer.
- [ ] 2.4 `spec.runtime` registered values `bash`, `js`, `lua`, `openapi`; the enum is **open** (design D12). An unrecognised value warns naming it and is carried through pack, push, pull and resolve **byte-identically**. A missing or non-string value is an error.
- [ ] 2.5 Document the one-artifact-one-tool rule and the OpenAPI mapping — one artifact per operation, layer carrying the pruned document, `spec.entrypoint` naming it — as the convention for `runtime: openapi`, so a second consumer does not invent a different one.
- [ ] 2.6 `application/vnd.epos.tool.mcp.v1+json` with one layer `application/vnd.epos.tool.mcp.layer.v1+json` carrying `server.json` verbatim (design D13). Validate it is well-formed JSON with a `name`, and that `io.modelcontextprotocol.server.name` equals it. Nothing else: epos neither connects to an MCP server nor runs a container.
- [ ] 2.7 The container-image form of an MCP server tool stays valid — an index entry pointing at an ordinary image manifest with the server-name annotation. A consumer distinguishes the two by `artifactType` only.
- [ ] 2.8 A **conformance fixture**: a tool artifact assembled by test code that does **not** use `internal/agent`, checked into `tests/conformance/` beside the existing `seed/`, so the round trip is verified against bytes rather than against this implementation's own writer.

### Gate — C2

- [ ] 2.9 `features/package-an-agent.feature`: a tool artifact packs, pushes to real `zot` and is pulled back by plain `oras`; its media types, config descriptor and layer match the specification.
- [ ] 2.10 A store of tool artifacts is enumerated by **reading manifest annotations only** — name, runtime, title, description all present, **no layer fetched**. This is `mcp-anything#142`'s D4 asserted from epos's side; if it fails, that consumer cannot index its own store.
- [ ] 2.11 A tool declaring an unrecognised runtime survives pack → push → pull → resolve byte-identically, is reported as unrecognised, and is neither rewritten nor deleted.
- [ ] 2.12 An MCP server tool with only a remote endpoint in `server.json` packs and resolves with no container image anywhere.
- [ ] 2.13 The 2.8 fixture resolves through epos.

## 3. C3 — packing a closure

- [ ] 3.1 `epos pack <dir>` dispatches on the marker file (1.2a) and packs an `agent.yaml` directory as a closure: one exclusive `Store.Push(ctx, tag, write)` (`internal/store/store.go`) writing N artifacts and one index, so a concurrent reader sees all of it or none.
- [ ] 3.2 A bare name in `skills`/`tools`/`subAgents` resolves to a sub-directory of the pack context, classified by the same marker rule (1.2a), and is packed into the closure. A bare name with no such directory fails naming the name **and the path it looked for** (design D6). The instruction and the model are found by their marker files, not by a name in the definition — the definition names a role for each.
- [ ] 3.3 A `{name, ref}` entry resolves the reference to a digest **once**, copies the artifact into the closure by descriptor (`oras.Copy`, never repack), and records the reference in `dev.epos.source`.
- [ ] 3.4 **The document is never rewritten.** Whichever authoring form was written is what is published; assert the published blob digest is a pure function of the source file.
- [ ] 3.5 Sub-agents recurse: a sub-directory containing its own `Agent` document is packed as its own index and referenced with role `subagent`.
- [ ] 3.6 `internal/skillfile` is **untouched** — no entry added to `reference.go`'s `instructionTable`, which is the single source for both the builder's dispatch and the generated docs page (§14.1) and whose every `Example` is executed by `TestDocumentedExamplesBuild`. A test asserts the table's length and contents are unchanged.
- [ ] 3.7 A build-language base that resolves to an agent index fails naming the artifact type. `fetchOCIBase` (`internal/skillfile/oci.go`) already rejects a manifest with `len(Layers) != 1`; an index has none, so confirm the failure is **legible** rather than merely present.
- [ ] 3.8 `epos pack` on a directory carrying only `SKILL.md` packs a skill exactly as before, with the same digest. This is the regression that matters most in this milestone.
- [ ] 3.9 `--created=<RFC3339>` opts into the timestamp, with help text saying in one line that it forfeits digest determinism (design D4).
- [ ] 3.10 `--supersedes <ref>` sets the index `subject`, off by default, with help text stating both costs: the superseded version becomes undeletable while this one exists, and it appears in that version's referrers alongside signatures (design D17).
- [ ] 3.10a The superseded index is **not transferred by push**. `content.Successors` returns an index's `Subject` first, so a naive `oras.Copy` would try to copy the previous closure and would fail whenever it is not in the local store — the normal case. Push skips the subject, as cosign does; only the descriptor is recorded, and the subject is expected already at the destination. Pack therefore needs only to resolve the reference once for its media type, digest and size.

### Gate — C3

- [ ] 3.11 An agent directory with an instruction, a model, one sub-directory skill, one referenced published skill, two tools and one sub-agent packs in **one** command into a complete closure.
- [ ] 3.12 A second process resolving the tag during a pack sees either no tag or a complete closure — the lock discipline (§9.2) proven for a multi-artifact write, not assumed from the single-artifact case.
- [ ] 3.13 The referenced published skill's manifest digest inside the closure equals its digest in its own repository (design D5).
- [ ] 3.14 A skill packed before and after this milestone has the same digest.

## 4. C4 — resolution

- [ ] 4.1 The resolver in `internal/agent`, over a **narrow fetcher interface declared in `internal/agent` itself** — at the point of use, which is where Go puts an interface — satisfied by the local store and by `internal/registry.OCIRegistry`. **One** interface, introduced because a test requires it, which is §13.4's bar and its named example.
- [ ] 4.2 Index fetching and descriptor traversal land on epos#44's `OCIRegistry` concrete type, beside `FetchReferenceContent`. **No second OCI client**, and **`internal/registry.Client` does not grow** (design D18): it is already six methods with generated mocks in three packages (`internal/registry/mocks_test.go`, `internal/catalog/mocks_registry_test.go`, `internal/cli/mocks_test.go`) and `epos list`'s laziness assertions ride on its shape. Widening it for consumers that do not use the new methods would churn all three.
- [ ] 4.3 A tag is resolved to a digest **once**; every subsequent fetch is by digest. A test moves the tag mid-resolution and asserts the resolution is unaffected.
- [ ] 4.4 Every fetched manifest and blob is verified against its descriptor digest, and nothing bypasses the verifying fetch path. This is what makes D7's acyclicity argument true rather than assumed.
- [ ] 4.5 `visited` is a **map from digest to resolved closure, shared across the whole resolution** — not a set passed down one path as epos#51 §6's pseudocode has it. A repeated digest returns its memoised closure and is **not** an error (design D7).
- [ ] 4.6 `MaxDepth = 16`; `ErrDepthExceeded` names the depth and the entry. `ErrCycleDetected` is retained **as an assertion that epos never returns in practice**: 4.4 makes its only case unreachable, because mismatched content fails verification before it is parsed. It is kept because `agentiq/SPEC.md` §8.4 names it and because it is what would catch a future change bypassing the verifying fetch path. Its doc comment says exactly that, so nobody downstream writes a live branch on it.
- [ ] 4.6a The cycle assertion is tested with a **deliberately non-verifying fetcher, as a unit test, and is not a godog gate** — it cannot be produced against a real registry, and a gate nobody can write is a gate that gets deleted.
- [ ] 4.7 Resolution fetches the index, every referenced manifest and its annotations, the definition, the instruction, the model, and an **MCP server's `server.json`** (small, no executable bytes, and where the connection details live). It does **not** fetch skill content layers, script tool payloads or container images (design D8). A script tool's own document is inside its payload (2.1a) and is therefore not fetched either — 2.2's manifest annotations are what make that sufficient.
- [ ] 4.8 An explicit materialise call fetches a referenced payload, verified against the descriptor already in the closure, with no second resolution. It runs every extracted path through `CheckPath` (2.1b).
- [ ] 4.8a A `Closure` makes it unambiguous, per entry, whether content is present or only a descriptor — so a caller never reads an unmaterialised payload as an empty artifact. A nil-versus-empty distinction in a struct field is not enough; it is an explicit state.
- [ ] 4.9 Resolution fails naming the skill and the role when the definition references a name absent from the index; `callbacks` are exempt (design D15).
- [ ] 4.10 Local-store and registry resolution go through one code path, so a locally packed agent and a published one produce the same closure.

### Gate — C4

- [ ] 4.11 `features/resolve-an-agent.feature`: an agent pushed to real `zot` resolves into a complete closure, including a two-level sub-agent.
- [ ] 4.12 A **diamond** — two sub-agents referencing one shared sub-agent — resolves, fetches the shared artifact **once**, and does not fail. Assert the fetch count, because this is the scenario the issue's own pseudocode gets wrong and a passing resolution would hide it.
- [ ] 4.13 Depth 17 fails with the depth error naming the entry; depth 16 succeeds.
- [ ] 4.14 Resolving an agent that references a large skill transfers bytes proportional to the documents, not to the skill. Assert against the registry's request log, not a timing.
- [ ] 4.15 A locally packed agent resolves with **no** registry request, and produces the same closure as after a push-and-resolve.

## 5. C5 — the public Go API

- [ ] 5.1 `pkg/epos`: the resolver, `MaxDepth`, `ErrDepthExceeded`, `ErrCycleDetected`, plus `Pack`, `Push` and a store handle (design D9). The document and `Closure` types already live here from 1.1. It exports **no machinery** — no store internals, no registry client, no locking — and the only third-party type in its exported surface is `ocispec.Descriptor`, which is what a descriptor already is and which carries its own compatibility promise.
- [ ] 5.2 A `Resolver` constructed from explicit options — store root, registry configuration, plain-HTTP, per-operation timeout — because resolution cannot happen without them and ambient process state is a hidden input to a caller that must be reproducible (design D10).
- [ ] 5.3 **No package-level `Resolve(ctx, ref)`.** It could only work by reading ambient credentials, and a hidden input is exactly what makes a durable step non-reproducible. Unset `Options` fields fall back to the CLI's own defaults, so a zero value is usable — a documented fallback, not an invisible one. `agentiq/SPEC.md` §8.4 changes one signature (8.5). Shipping the convenience form and documenting in the same breath that a durable step should not call it was considered and rejected (design D10).
- [ ] 5.4 `internal/cli` is refactored to call `pkg/epos` for pack, push and resolve, so the public API has a first consumer inside the repository and cannot drift from what the CLI does. If that refactor turns out to distort either side, say so and keep them separate rather than forcing it.
- [ ] 5.5 Extend epos#44's import-hygiene guard to run over `./pkg/epos` itself, not only over the CLI main package. The existing test already asserts `internal/catalog` and goldmark are absent from the CLI, which covers `pkg/epos` transitively once the CLI imports it — asserting it on `pkg/epos` directly is what makes the guard fire **before** that import exists. (ClickHouse only ever arrives via `internal/catalog`; name what the existing test names.)
- [ ] 5.6 Package documentation stating the stability promise, that it is pre-1.0 while the format is at `v1alpha1`, and which identifiers a consumer should pin. `agentiq/SPEC.md` §17.2's depguard confines this import to `artifact/` — verify that rule names the right path once `pkg/epos` exists.
- [ ] 5.7 A test in a **separate module** under `tests/` importing `pkg/epos` by module path, proving it is importable from outside and that no internal type leaks into an exported signature.

### Gate — C5

- [ ] 5.8 The external-module test resolves an agent from a real `zot`, in-process, with no `epos` binary on `PATH` — which is the property `agentiq/SPEC.md` §3.2 actually blocks on.
- [ ] 5.9 The same test packs and pushes a tool through `pkg/epos`, and epos's CLI then resolves it — the `mcp-anything#142` D2 objection answered by a test rather than by prose.
- [ ] 5.10 `errors.Is` matches the exported depth error from outside the module.

## 6. C6 — publishing a closure

- [ ] 6.1 `epos push <name>:<version> <destination>` detects an agent index and copies the **whole closure** into `<destination>/<name>`, index **last** (design D3). The destination is a namespace and the name is appended, **always** — the rule `pushReference` (`internal/cli/push.go`) already documents and deliberately does not de-duplicate. epos inserts no `agents/` segment of its own; the user writes `oci://ghcr.io/acme/agents` exactly as they write `oci://ghcr.io/acme/agent-skills`, and a rule that inserted one would produce `…/agents/agents/<name>` the first time somebody followed the convention. `runPush` already holds a *shared* store lock across the upload; keep that discipline.
- [ ] 6.2 A partial push leaves unreferenced manifests and **no index**, so a published index never names an absent manifest.
- [ ] 6.3 An unchanged agent pushed twice uploads no new blob and yields the same index digest.
- [ ] 6.4 `epos pull` accepts a digest reference, for agents **and** for skills (design D14). `runPull` and `runPush` both refuse digests today; lifting it for one and not the other leaves an inconsistency with no defender.
- [ ] 6.5 A digest pull writes the store tag `<name>:sha256-<hex>` — cosign's substitution, valid per the OCI tag grammar — so the artifact survives `prune`, whose sweep is rooted at tags. Documented in `SPEC.md` §9 (0.5, 0.7).
- [ ] 6.6 `epos sign` / `epos verify` accept an agent index as subject. `internal/sign` gains **nothing**: `attach` already takes any subject descriptor, and a signature over the index transitively covers the closure.
- [ ] 6.7 A skill's signature is byte-identical to the one produced before this change — `internal/sign/attach.go` deliberately omits `created` so two signatures match, and that must still hold.
- [ ] 6.8 The agent index carries `org.opencontainers.image.title` and `.description`, so `epos list` and `epos search` include agents with **no code change** in `internal/cli/discover.go` or epos#44's `internal/registry.Discover` (design D19).
- [ ] 6.9 `internal/catalog` (epos#44) is **not** extended. Rendering agents in the catalog frontend is out of scope and is named as such in `SPEC.md`, so the omission reads as a decision.

### Gate — C6

- [ ] 6.10 An agent is pushed to real `zot`, and `oras copy --recursive` moves the whole closure into a second empty registry where it resolves — the claim epos#51 §4.1 makes, proven.
- [ ] 6.11 A push killed partway leaves no index; a re-push completes.
- [ ] 6.12 An agent is pulled **by digest**, and survives a `store prune`.
- [ ] 6.13 A signed agent verifies; replacing any referenced artifact's content fails verification.
- [ ] 6.14 Agents and skills published to one namespace are both listed; searching the agent's description matches it; a registry without `_catalog` reports the capability unavailable exactly as before.
- [ ] 6.15 A tagged agent's whole closure — including sub-agent indexes and their contents — survives `store prune`; removing the tag and pruning sweeps it, except what another tag still reaches (0.7).

## 7. Documentation and CI

- [ ] 7.1 `docs/`: an agent page beside `skillfile.astro`, generated from the same fixtures the godog scenarios use, so it cannot drift (§14.1's rule for the Skillfile reference, applied to the new format).
- [ ] 7.2 `internal/docsgen`: the new commands and flags appear on the CLI page. `docsgen/cli.go` walks the cobra tree, so this is a check rather than work — verify it, do not assume it.
- [ ] 7.3 `README.md`: agents in the same register as skills. What epos does **not** become — no API server, no database, no web UI, no registry service — restated, because a change adding a public API and a multi-artifact CLI is where that line gets crossed by accident.
- [ ] 7.4 `.github/workflows/ci.yml`: the two new godog feature files in the integration job. If the job's time budget is reached, split by feature file rather than thinning scenarios.
- [ ] 7.5 Full CI green — lint, vet, format, `govulncheck`, three-platform unit tests, the whole godog suite against containers, the docs build, and `goreleaser check`.
- [ ] 7.6 Confirm `go.mod` gained **nothing** (design D20). A format that needed a new dependency to express itself would be the wrong format.
- [ ] 7.7 Test conventions are the repository's and the workspace rules agree here: `stretchr/testify` for assertions, `go.uber.org/mock` via the `tool` directive for mocks, godog for gates. Nothing new is introduced.

## 8. Release — the change is not done at merge

`agentiq/SPEC.md` §3.2: "AgentIQ M3 cannot ship until this is in a tagged epos
release." epos has **no tags and no releases**: `.github/workflows/release.yml`
fires on `v*` and `.goreleaser.yaml` builds two binaries across six
platform/arch combinations, and **neither has ever run**. This is a first
execution, not a formality.

- [ ] 8.1 `goreleaser check`, then a local `goreleaser release --snapshot --clean` producing all twelve artifacts, **before** any tag is pushed. A tag is not a place to discover a broken pipeline.
- [ ] 8.2 CI green on `main`; the release gate is ordering, not a re-run.
- [ ] 8.3 Tag `v0.1.0`. `v1.0.0` would claim a stability that a `v1alpha1` document envelope and a first-ever public Go API do not support.
- [ ] 8.4 Verify the release published both binaries for all six platform/arch combinations and that the archives extract and run.
- [ ] 8.5 Report the tag on epos#51 and on `gaarutyunov/agentiq#4`, which epos#51 blocks, **together with the four changes AgentIQ must make** (design "Changes consumers must make", items 1–4). A tag alone does not unblock it: §8.4's package-level `Resolve(ctx, ref)` does not exist and becomes a `Resolver`, §8.4's `Skills []SkillDoc` expects content resolution does not fetch, §7.6 gets the instruction/model cardinality wrong, and code branching on the cycle error is dead.
- [ ] 8.6 Report on `gaarutyunov/mcp-anything#142` that its task 1.4 is answered — `runtime: openapi` **accepted** into the enum, `application/vnd.epos.tool.mcp.v1+json` **accepted** with its proposed spelling — plus items 6–10 of "Changes consumers must make": the manifest-annotation requirement, `dev.epos.tool.params` as a **JSON array** capped at 4096 bytes and omitted rather than truncated, the `Tool` document's position at `<tool-name>/tool.yaml` **inside** the payload tar (which #142 does not have and cannot guess), the `spec.entrypoint` path-validation rule, and that `pkg/epos` will **not** exist in a tagged release before #142 needs it — so `pkg/toolstore` ships as planned and the swap stays available.
</content>
