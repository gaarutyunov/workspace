# epos#43 — `epos push`

## Why

Publishing a skill today means installing a second client. `epos pack` writes a
conformant OCI artifact into the local store and then stops; the quick start
finishes the job with `oras login` and `oras cp --from-oci-layout-path "$(epos
store path)" …`. The owner's words on the issue:

> When I said we can skip push for now I meant that we don't need to add it to
> our registry. But we still need push in the CLI. It's not convenient for the
> user to install multiple clients. They would expect clear familiar api same as
> helm.

Two separate things were collapsed into one decision, and this change separates
them again:

- **The `epos-registry` write path stays withdrawn.** SPEC §4.5 is right about
  the server: relaying or redirecting upload sessions through `epos-registry`
  breaks §4.2's "blob bytes never cross it", and the 307 design is
  unimplementable because `oras-go` rejects a cross-host upload `Location`
  ([GHSA-jxpm-75mh-9fp7](https://github.com/oras-project/oras-go/security/advisories/GHSA-jxpm-75mh-9fp7)).
  Nothing here revives it.
- **The CLI command was never blocked by that.** The advisory's check compares
  the upload `Location` against the registry the client *targeted*. `epos push
  ghcr.io/acme/agent-skills` targets ghcr.io and gets ghcr.io's own `Location`;
  the check passes, which is exactly why `oras cp` works today. SPEC §4.5's
  clause "*included Epos's own `epos push`*" is true only of a push routed
  *through* `epos-registry`, and §6.1's flat "There is no `epos push`" reads it
  as true of the command in general. It is not. Publishing has been one
  `oras.Copy` away the whole time.

The bar the issue sets is **helm parity**: someone who knows `helm push
chart.tgz oci://host/repo` should be able to guess the epos command, and should
not need `oras` or `docker` installed to run it.

## What Changes

- **`epos push <name>:<version> <destination>`** copies a skill already in the
  local store to a registry, byte for byte. Same operand order as `helm push`;
  the version comes from the artifact, never from a flag; the destination names
  a namespace and the skill name is appended, so `epos push reviewer:1.0.0
  oci://ghcr.io/acme/agent-skills` publishes `ghcr.io/acme/agent-skills/reviewer:1.0.0`.
  An `oci://` prefix is accepted and stripped; it is not required, because
  nothing else in epos takes one.
- **`epos registry login` / `epos registry logout`** — in scope, and the reason
  is the issue's own: without them `epos push` still sends the user to install
  `oras` or `docker` to get a credential into the store, which is the complaint
  verbatim. Credentials resolve from Docker's config and its native helpers
  (`~/.docker/config.json`, `osxkeychain`, `wincred`, `pass`), so an existing
  `docker login` / `oras login` / `helm registry login` already works and the
  new commands write to the same place.
- **No secret ever reaches argv.** `-u/--username` and `--password-stdin`, plus
  an echo-off prompt when stdin is a terminal. There is deliberately **no
  `--password` flag**, which is where this change departs from helm on purpose.
- **Every registry-touching command gets the credential-bearing client**, not
  just `push`. It is built once, in the helper `pull`, `sign`, `attest` and
  `verify` already share. `epos sign` writes a referrer manifest to a registry
  through an anonymous client today, so it cannot work against any registry that
  requires authentication; this change is what fixes that, and doing it any
  other way would mean two answers to "where do credentials come from".
- **The record is corrected.** SPEC §4.5, §5.4, §6.1, §6.2, the §12 milestone
  table and `features/author-and-publish.feature`'s preamble all assert that no
  `epos push` exists. `internal/docsgen/cli.go` carries a hand-written
  "Publishing" section saying the same, which the CI drift gate cannot catch
  because it is prose, not command metadata. All of it is updated in this change.

## Capabilities

### New Capabilities

- `epos-push`: the command — its operands, what it copies, what it prints, what
  it refuses, and the corrected record of the withdrawn write path.
- `epos-registry-credentials`: where credentials come from, how they are stored,
  which commands use them, and what must never happen to them.

### Modified Capabilities

<!-- epos predates OpenSpec: there is no capability spec under openspec/specs/
     to amend. SPEC.md is the project's own reference and is amended by this
     change, as recorded in the `epos-push` delta. -->

## Non-goals

- **No `epos-registry` write path.** SPEC §4.5's withdrawal of the *server*
  stands unchanged, for the reasons it gives. Two references stay two
  references: `epos-registry` for reading, upstream for publishing.
- **No implicit pack.** `epos push` does not take a directory. `helm package`
  then `helm push` is the shape being matched, and `epos pack` already exists.
- **No signing changes.** `epos sign` and `epos attest` keep working the way
  they do — against the registry, after the push — and gain only the credentials
  they were always missing. Signatures are referrers created remotely; nothing
  in the local store has to travel with the artifact.
- **No registry of our own, no publish counter.** SPEC §5.4 already explains why
  a publish cannot be counted: it goes straight to upstream, where
  `epos-registry` never sees it. That remains true and is not a defect of this
  change.

## Interaction with epos#42

epos#42 ("Update the website", spec at workspace#41) documents publishing with
`oras cp`, deliberately: *#42's own* design decision D1 records that its worked example is built
from `git+https://` and local `FROM` sources "so the multi-stage demo does not
sit behind #43", and its `epos-quickstart` delta carries two requirements that
this change falsifies —

- *Scenario: Publishing is described as it actually works today* — "uses the
  copy-into-a-registry tool the CLI has no replacement for, and does not present
  an `epos push` command that does not exist".
- *Scenario: No invented commands* — "contains no `epos init`, `epos new`,
  **`epos push`**, **`epos login`**, `epos template` or `epos lint`".

**#42's quick start is not rewritten by this change, and #43 does not block on
#42.** The two are independent: #42's worked example uses git and local sources
throughout and needs no registry at all. What changes is that two of #42's
scenarios stop being true the moment #43 merges.

**Who owns the edit.** #43 owns the *documentation of `push` itself* — the
generated CLI reference is regenerated here by construction, and the
hand-written "Publishing" section in `internal/docsgen/cli.go` is replaced here
because it is this change that makes it false. #42 owns its own quick start
prose and its own delta specs, because rewriting another change's `epos-quickstart`
spec from inside #43 would leave #42 approving a spec it no longer contains.

**Concretely, whoever merges second reconciles.** If #42 merges first, its
`epos push`/`epos login` prohibitions need amending as part of implementing #43,
and the quick start's step 4 becomes two commands (`epos registry login`, `epos
push`) with the `oras cp` form kept as the "any OCI client also works" note that
SPEC §2.1's conformance claim earns. If #43 merges first, #42's spec should be
updated before it is approved. This is flagged rather than decided because it is
the owner's call which spec absorbs the edit.

## Impact

- **`internal/cli`**: new `push.go` and `registry.go` (the `login`/`logout`
  subcommands); `newRepository` in `pull.go` grows credential resolution and is
  shared by `push`, `pull`, `sign`, `attest` and `verify`; `root.go` registers
  two new top-level commands.
- **`internal/store`**: no change. `Store.Read` already exists for exactly this
  ("copying an artifact out to a registry, say").
- **`internal/artifact`**: no change. Push moves bytes; it never re-derives them.
- **`internal/docsgen`**: the `publishing()` section is rewritten; `cli.astro` is
  regenerated (CI fails otherwise).
- **New direct dependencies**: `oras.land/oras-go/v2/registry/remote/credentials`
  (same module, already required) and `golang.org/x/term` (already in the module
  graph as indirect). No new module.
- **`SPEC.md`**: §4.5, §5.4, §6.1, §6.2 and the §12/§15 tables.
- **`features/author-and-publish.feature`**: preamble and new scenarios.

**Behaviour change for existing users.** `pull`, `verify`, `list`, `search`,
`sign` and `attest` are unconditionally anonymous today. After this change they
send a credential when the ambient store holds one for that registry. A user who
has a stale `docker login` for a registry they read anonymously will start
sending it, so a rejected credential must fail with a message that names the
registry and says the *stored credential* was refused — otherwise it reads as an
unexplained regression. Finding no credential stays a normal outcome, not an
error.
