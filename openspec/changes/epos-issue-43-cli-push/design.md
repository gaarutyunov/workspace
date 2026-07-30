# Design — `epos push`

## What is actually there today

`internal/cli/root.go` registers thirteen commands: `pack`, `pull`, `store
{ls,path,prune}`, `build`, `list`, `search`, `install`, `uninstall`, `ls`,
`generate-key-pair`, `sign`, `attest`, `verify`. Its package comment says
outright: *"push is deliberately absent — see the write-path note on the A2
issue."* There is no `init`, `new`, `login`, `template` or `lint` either.

The pieces a push needs already exist and are already load-bearing:

| Piece | Where | What it gives push |
|---|---|---|
| `store.Store.Read` | `internal/store/store.go` | a shared-lock read of the OCI layout, written for "copying an artifact out to a registry, say" |
| `newRepository(ref, plainHTTP)` | `internal/cli/pull.go` | reference splitting that survives ports, tags and digests, via `registry.ParseReference` |
| `oras.Copy` | oras-go v2.6.2 | the copy itself, both directions |
| `credentials.NewStoreFromDocker` | `oras-go/v2/registry/remote/credentials` | Docker's config file **plus** the native helpers, written 0600 into a 0700 directory, atomically |

The artifact contract is fixed by `internal/artifact` and must not move.
`artifact.Build`/`assemble` produce: artifact type
`application/vnd.agentskills.skill.v1`; config
`application/vnd.agentskills.skill.config.v1+json`, pushed as a blob *and*
inlined in the descriptor's `data`; exactly one layer,
`application/vnd.agentskills.skill.content.v1.tar+gzip`, a tar+gzip rooted at
`<skill-name>/` with epoch mtimes, uid/gid 0, normalised modes and a pinned gzip
header; manifest annotations `org.opencontainers.image.title` and
`…description` from the frontmatter, plus provenance annotations on a built
skill. The manifest is assembled by hand rather than by `oras.PackManifest`
precisely so no timestamp gets into the digest (SPEC §2.4).

**Push must not touch any of that.** Its whole job is to move existing bytes.

## D1: The command is unblocked; the server write path stays withdrawn

**Decision.** Ship `epos push` as a direct client→registry copy. Leave SPEC §4.5's
withdrawal of the `epos-registry` write path exactly as it is, and amend only the
sentences that over-generalise from the server to the CLI.

**Why the advisory does not apply.** GHSA-jxpm-75mh-9fp7 makes `oras-go` refuse a
blob-upload `Location` whose host differs from *the registry the client was
pointed at*. The withdrawn design pointed the client at `epos-registry:8080` and
had upstream answer with `upstream:5000` — two hosts, refused. `epos push
ghcr.io/acme/agent-skills` points the client at `ghcr.io` and receives ghcr.io's
own `Location`: one host, accepted. This is not an argument that the check is
wrong; it is the observation that `oras cp` publishes successfully today through
the same library, and `epos push` is the same call from the same module.

**Consequence for the record.** These assertions become false and are amended:

| Where | What it says now |
|---|---|
| SPEC §4.5 | "`epos` has no `push` command" |
| SPEC §5.4 | (accurate — no publish counter; kept, reworded to drop the implication that no push exists) |
| SPEC §6.1 | "There is no `epos push`, and no Epos write server" |
| SPEC §6.2 | "The CLI does not … mediate credentials" |
| SPEC §12, row A2 | "The write path was attempted and withdrawn (§4.5)" |
| SPEC §15, rows 4 and 24, and "Removed from scope" | "No write server, and no `epos push`" |
| `features/author-and-publish.feature` | "Publishing is not part of Epos for now" |
| `internal/docsgen/cli.go`, `publishing()` | "There is no `epos push`." |

Two of these are worth naming as hazards rather than chores. SPEC line 26
already reads "`epos-registry` **relays** writes (§4.5) but transforms nothing"
while §4.5 says it serves none — pre-existing drift, fixed here. And
`cliDescription` in `docsgen` carries the comment *"a hard-coded one is exactly
the sentence that still says `push` a year after the write path was withdrawn"* —
the generator's own warning, now pointing the other way at the hand-written
`publishing()` block sitting three functions below it. The CI drift gate
regenerates `cli.astro` from the cobra tree and diffs it, so it catches a missing
*command* but is structurally blind to a false *paragraph*.

**Rejected: revive the redirect or relay uploads through `epos-registry`.**
Rejected for the reasons §4.5 already gives — relaying contradicts §4.2, and
rewriting `Location` reintroduces session mapping and chunked-resume accounting.
Nothing about the CLI command requires either.

## D2: Operand shape — `epos push <name>:<version> <destination>`

**Decision.** Two positional operands, in helm's order: the thing being pushed,
then where it goes. The first is a **local store tag**, which is `<name>:<version>`
by construction. The second is a registry namespace.

```
epos push reviewer:1.0.0 oci://ghcr.io/acme/agent-skills
epos push reviewer:1.0.0 ghcr.io/acme/agent-skills
```

**Why this is the parity that matters.** `helm push` takes an artifact that
`helm package` already produced and a destination; the chart's name and version
come out of the artifact, never from flags. Everything about `epos pack` →
`epos push` mirrors that: `pack` is `package`, the store tag carries the name and
version, and there is no `--version` flag to disagree with the frontmatter.

**Rejected: `epos push <dir>` (pack-and-push in one command).** It would be
convenient and it is what people reach for first. Rejected because it forks the
answer to "what digest does this skill have": a directory that packs to a
different digest than the one in the store would publish silently, and SPEC §2.4
makes that digest the artifact's identity. Helm made the same split for the same
reason. `epos pack ./reviewer && epos push reviewer:1.0.0 …` is two words longer
and has one meaning.

**Rejected: pushing by digest (`epos push reviewer@sha256:… …`).** The local
store is tag-addressed — `pull` already refuses a digest with "pull needs a tag"
because `sha256:…` is not in the character set a tag allows. Push refuses it the
same way, with the same shape of message.

## D3: `oci://` is accepted, not required

**Decision.** Strip a leading `oci://` from the destination if present; accept a
bare host/path otherwise.

**Why not require it.** Helm requires the scheme because helm has *two* chart
transports — classic HTTP chart repositories and OCI registries — and the prefix
is what disambiguates them. epos has exactly one; the scheme would carry zero
information. Requiring it would also make `push` the only epos command whose
reference is written differently from every other: `epos pull
ghcr.io/acme/agent-skills/reviewer:1.0.0` takes no scheme, and neither do
`--registry`, `verify`, or a Skillfile `FROM`.

**Why accept it anyway.** It costs one `strings.TrimPrefix` and it makes a
command line typed from helm muscle memory work instead of erroring. That is the
whole of what "familiar api same as helm" asks for here.

**Rejected: require `oci://` for helm-identical syntax.** It would buy nothing a
user can perceive except a failure mode, and it would make epos internally
inconsistent — a worse outcome than a small deviation from helm.

**Rejected: accept `oci://` on `pull` too, for symmetry.** Out of scope, and it
widens an accepted-input surface on a command nobody complained about.

## D4: The destination names a namespace; the skill name is appended

**Decision.** `oci://ghcr.io/acme/agent-skills` + store tag `reviewer:1.0.0` →
`ghcr.io/acme/agent-skills/reviewer:1.0.0`. Unconditionally, including when the
last path segment already equals the skill name.

**Why.** Three things agree. Helm does exactly this (`helm push mychart-0.1.0.tgz
oci://reg/ns` lands at `reg/ns/mychart:0.1.0`). SPEC §2.1 fixes the repository
convention as `<registry>/<namespace>/agent-skills/<skill-name>` and says "the
repository name therefore identifies the skill without any manifest lookup".
And `runPull` already reads the skill name back out of the last path segment, so
appending is the exact inverse of what pull does — a round trip that holds by
construction rather than by convention.

**The awkward case, handled by output rather than by cleverness.** If someone
writes `oci://ghcr.io/acme/agent-skills/reviewer`, they get
`…/agent-skills/reviewer/reviewer:1.0.0`. Detecting and de-duplicating that is
not safe — `…/reviewer/reviewer` is a legal repository somebody may genuinely
want — so push instead **prints the fully resolved reference it pushed to**,
which makes the mistake visible on the first run rather than on the first failed
pull.

**Rejected: a `--repository` flag naming the exact repository.** Two ways to say
the same thing, one of which can contradict the store tag. No user has asked for
it. Deleted before it exists.

## D5: Push copies bytes; it never re-derives them

**Decision.** `store.Read` (shared lock) → `oras.Copy(ctx, st, "<name>:<version>",
repo, "<version>", oras.DefaultCopyOptions)`. No repacking, no re-tagging of the
manifest, no annotation added or removed, no `created` stamp.

**Why the tag changes shape.** The store tags a skill `reviewer:1.0.0` because a
single flat layout holds many skills (`runPull` is explicit that copying under
the source tag would leave a bare `1.0.0` alongside `reviewer:1.0.0`). A registry
repository holds exactly one skill, so the remote tag is the version alone. Push
is the mirror image of `runPull`, which maps the other way.

**The invariant this buys.** The digest `epos pack` printed is the digest `epos
push` prints is the digest a `pull` or a plain `oras pull` gets back. The quick
start already asserts this in prose ("Same digest as `epos pack` printed") for
the `oras cp` route; push inherits it because it is the same `oras.Copy`.

**Rejected: pushing a directory through `artifact.Build` into the remote
directly.** Same objection as D2, plus it would put a second packing path in
front of a network boundary, where a determinism bug is hardest to notice.

## D6: Output is one line — `<resolved-ref> <digest>`

**Decision.**

```
$ epos push reviewer:1.0.0 oci://ghcr.io/acme/agent-skills
ghcr.io/acme/agent-skills/reviewer:1.0.0 sha256:a32fa1df…
```

**Why not helm's two-line `Pushed:` / `Digest:` form.** `epos pack` and `epos
pull` both print `<tag> <digest>` on one line, and `epos store ls` prints one tag
per line. A user piping epos output into `cut` or `awk` — and a scenario
asserting on it — should not have to special-case one command. The information
is identical to helm's; only the framing differs, and internal consistency is
worth more here than a matching label. The digest is printed either way, which
is the part of helm's behaviour that carries information.

## D7: `epos registry login` / `logout` are in scope

**Decision.** Ship them in this change, as `epos registry login <host>` and
`epos registry logout <host>` — helm's noun-verb shape (`helm registry login`),
not docker's bare `docker login`.

**Why this is not scope creep.** The issue's complaint is *"not convenient for
the user to install multiple clients"*. A `push` that authenticates only from a
credential store nothing in epos can write leaves the user installing `oras` or
`docker` to run `oras login` — the complaint, one command later. The house rule
is one issue, one deliverable, and clearing a technical prerequisite belongs in
the same change. This is that prerequisite, and it is ~60 lines over
`credentials.Login` / `credentials.Logout`.

**Why `registry login` and not `login`.** `epos login` reads as logging in to
*epos*, which is not a thing that exists — epos has no account, no service, no
identity of its own (SPEC's non-goals: "Epos does not issue credentials").
`registry login` says what is being logged in to. Helm reached the same
conclusion for the same reason.

**Rejected: no login command, rely on ambient `docker login`.** Viable — the
credential resolution below reads Docker's store whether or not epos wrote it,
so CI with a `docker/login-action` step needs nothing new. Rejected as the
*only* path because it fails the issue's actual test on a fresh laptop.

**Rejected: shelling out to `oras login`.** Requires the second client the issue
is about.

## D8: Credential resolution, and what must never happen

**Decision — precedence, first match wins:**

1. `--registry-config <path>`, when given (helm's flag name, helm's meaning).
2. `$DOCKER_CONFIG/config.json`, when `DOCKER_CONFIG` is set.
3. `~/.docker/config.json` together with the platform's native credential
   helpers — `osxkeychain`, `wincred`, `pass`.
4. No credential found → the request is made anonymously. A registry that
   permits anonymous push (a local zot with auth off) works; one that does not
   returns 401, and push turns that into a message naming `epos registry login
   <host>`.

All four are `credentials.NewStore` / `NewStoreFromDocker` with
`credentials.Credential(store)` as the `auth.Client`'s `Credential` function.
Nothing about the file format is epos's own.

**Why delegate rather than keep credentials under `$EPOS_HOME`.** An epos-native
credential file would be a fourth place a registry token lives on a developer's
machine, would not be readable by `docker` or `oras`, and would need epos to get
file modes, atomic replacement and keychain integration right by itself.
oras-go's store already creates the directory 0700, writes the file 0600, and
replaces it via a temp file and a rename — and a `docker login` the user ran
last year keeps working with no migration.

**Never, and these are testable:**

- **No secret in argv.** `-u/--username` and `--password-stdin` only. There is
  **no `--password`/`-p` flag**, deliberately unlike `helm registry login -p`:
  argv is world-readable through `/proc/<pid>/cmdline` on Linux and lands in
  shell history. This is the one place the change refuses parity, and it refuses
  it knowingly. When neither `--password-stdin` nor a piped stdin is present and
  stdin is a terminal, prompt with echo off (`golang.org/x/term`, already in the
  module graph).
- **No credential written world-readable.** Delegated to oras-go, and asserted
  on POSIX in the test suite rather than assumed.
- **No credential logged, echoed, or included in an error message.** A 401 is
  reported as "authentication failed for `<host>`", never with what was sent.
- **`AllowPlaintextPut` is set**, because a base64 blob in a config file is what
  Docker's format *is* when no helper is configured — but the help text says so
  in one sentence rather than implying the file is encrypted.

**Rejected: an `EPOS_REGISTRY_TOKEN` environment variable.** A fifth source, and
the one that most reliably ends up in a committed `.env`. CI already sets
credentials through `docker/login-action` or by writing Docker's config, both of
which land in path 2 or 3.

## D9: One credential-bearing client, shared by every command that talks to a registry

**Decision.** Credential resolution goes into `newRepository` in `internal/cli`,
so `push`, `pull`, `sign`, `attest` and `verify` all get it. Discovery's
`newOCIRegistry` gets the equivalent for `remote.Registry`.

**Why this is in scope rather than a follow-up.** `epos sign` and `epos attest`
*write* a referrer manifest to the registry (`sign.Sign(ctx, repo, …)` →
`dst.Push`) through a `remote.Repository` whose `Client` is never set — that is,
anonymously. They cannot work against any registry that requires authentication
to write, which is every registry a real skill would be signed in. Putting
credentials anywhere except the shared helper would mean epos has two answers to
"where do credentials come from", and the sign path would keep the broken one.

**The composition that has to be right.** `runPull` replaces `repo.Client` with a
transport that stamps `Epos-Download` on every request (SPEC §5.2 — it is what
distinguishes a verified download from an inflated one). That must survive:
the auth client wraps the header transport, not the other way round —
`&auth.Client{Client: &http.Client{Transport: headerTransport{…}}, Credential: …}`
— so a pull is still both authenticated and counted. **`epos push` does not send
`Epos-Download`**: a publish is not a download, and SPEC §5.1 counts only blob
`GET`s.

## D10: What deliberately stays simple

Recorded because each of these is a thing a reviewer or an implementer will
reach for, and the answer is no.

- **No `pusher` interface.** `discover.go` defines `registryClient` because
  laziness there is a *behavioural* requirement that can only be asserted over
  the calls made (SPEC §7.2). Push has no such requirement: what is worth
  asserting without a network is destination parsing and refusal, which are pure
  functions, and what is worth asserting with one is the real upload, which
  SPEC §13.2 says must hit a real registry. An interface with one implementation
  and one mock would test that `oras.Copy` was called.
- **No configuration library in `internal/cli`.** koanf belongs to
  `cmd/epos-registry`, which has a config struct; the CLI has flags and one
  environment variable. `DOCKER_CONFIG` is read by
  `credentials.NewStoreFromDocker` inside oras-go, so epos reads no environment
  variable of its own for this and needs no provider chain. (And never Viper —
  `.claude/rules/go-cli-koanf.md`.)
- **No timeout on `push`.** `pull` has none either; a publish is a foreground
  operation the user can interrupt, and `cmd.Context()` carries the
  cancellation. The five-minute `ociTimeout` in `internal/skillfile/oci.go`
  exists because a *build* must not hang on a third party's server mid-graph —
  a different situation.
- **Reuse the existing status-code idiom.** `discover.go`'s `unsupported(err)`
  already does `errors.As(err, &*errcode.ErrorResponse)` and switches on
  `resp.StatusCode`. The 401-means-log-in message uses the same shape; it does
  not introduce a second way to read a registry's status code, and 403 is *not*
  folded into it (a credential that is valid but unauthorised is a different
  problem from no credential).
- **The store's shared lock is held across the upload, on purpose.**
  `store.Read` takes the shared lock for the length of `fn`, so a large push
  blocks `pack`, `pull` and `prune` — which take the exclusive lock — in another
  terminal for its duration. This is what `Read`'s own doc comment anticipates
  ("copying an artifact out to a registry, say"), and it is the correct trade:
  buffering the artifact into memory to release the lock earlier would put a
  second copy of every layer in RAM to avoid a wait nobody has complained about.
  Do not "fix" it.
- **`epos registry …` sits alongside the existing `--registry` flag** on `list`
  and `search`. The overlap is knowing: the flag names a registry to enumerate,
  the command group names registry *credentials*, and helm has the same pair.
  Renaming either to avoid the echo would cost more familiarity than it buys.

## D11: Testing

Unit, in `internal/cli`, driving the `RunE` functions directly the way
`pull_test.go` does — table-driven over reference forms, with testify (`require`
for anything the rest of the case depends on, `assert` otherwise). No network:
these cover destination parsing, `oci://` stripping, name appending, the tag
shape sent to the remote, the digest-rejection message, and the resolved-reference
output.

Integration, in `tests/integration`, against real zot in testcontainers —
SPEC §13.2 is explicit that registries are real, with no fakes and no mocked
HTTP, and zot is chosen partly because it supports htpasswd auth. Scenarios go
in `features/author-and-publish.feature`, which is hand-authored, canonical and
single-source (§13.3): they are written there and consumed by godog, never
paraphrased into a Go table.

The round trip is the gate: `pack` → `push` → `pull` by a second store, and
`pack` → `push` → plain `oras pull`, both landing on the digest `pack` printed.
Authentication gets its own scenario against zot with htpasswd on: anonymous
push refused with a message naming `epos registry login`, then `epos registry
login` followed by a push that succeeds.

**Rejected: a mock registry for the auth path.** SPEC §13.2 forbids it, and the
one thing worth testing about authentication is the handshake a mock would fake.

## Open question for the owner

**Which change absorbs the quick-start edit** — see the proposal's "Interaction
with epos#42". #42's `epos-quickstart` delta currently forbids `epos push` and
`epos login` from appearing on the page. That is correct today and wrong the day
#43 merges. The edit is small either way; naming its owner now avoids two specs
disagreeing in review.
