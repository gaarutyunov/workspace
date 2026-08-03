# Design — epos#44, the catalog frontend

## What is actually there today

Read from `origin/main` of `gaarutyunov/epos` (`deb2b69`), not from a working
checkout.

**Module** `github.com/gaarutyunov/epos`, Go 1.26.4. One module, `main` per
binary under `cmd/`, shared code in top-level `internal/`. No `pkg/`, no `api/`
— SPEC §13.4 mandates that shape ("Plain Go. No code generation, no model, no
hexagonal layering, no DDD"). OCI via `oras.land/oras-go/v2 v2.6.2`; cobra;
koanf (never Viper); OTel `v1.44.0` with the stdout metric exporter.

**Binaries**: `cmd/epos` and `cmd/epos-registry` (a single flat command). Since
epos#43 merged (`6f7738a`), the CLI publishes for itself: `epos push
<name>:<version> <destination>` plus `epos registry login` / `logout`, sharing
one credential-bearing client with `pull`, `build`, `sign`, `attest` and
`verify`. There is no `serve`, `web`, `ui` or `catalog` command anywhere.

**`//go:embed`: zero occurrences in the repository.** Embedding a frontend is
net-new; there is no precedent to follow and nothing to extend.

**`epos-registry` is a cobra command with a koanf tree and one listener.**
`newRootCommand` in `cmd/epos-registry/main.go` takes `--addr`, `--upstream` and
three `metrics.*` keys; `loadConfig` resolves `EPOS_REGISTRY_*` through koanf,
mapping both `X_Y` and `X__Y` onto dotted keys. It has **no subcommands** today.
This is the binary the catalog joins (**D2**), and its configuration mechanism
is the one the catalog's settings use unchanged.

**`internal/skillfile` is not a small import.** It carries the Skillfile build
language and pulls **`go-git/v5`, `benhoyt/goawk`, `bluekeyes/go-gitdiff` and
`goccy/go-yaml`**. `fetchOCIBase` — the remote fetch-and-unpack the catalog's
detail page needs — lives in it. That matters only because the catalog moved to
a binary that does not link it (**D2a**).

**`internal/docsgen` generates two pages, from live sources, behind a CI drift
gate.** `targets()` names `docs/src/pages/cli.astro` (walked from
`cli.NewRootCommand`) and `docs/src/pages/skillfile.astro` (read from
`skillfile.NewReference()`, which is already plain data). `go run
./internal/docsgen -check` fails when a committed page is stale. **It walks the
`epos` tree only** — `epos-registry`'s flags are generated nowhere and appear on
no page. Both facts are load-bearing for **D17**.

**Enumeration already exists, unexported.** `internal/cli/discover.go`:

```go
type registryClient interface {
	Catalog(ctx context.Context) ([]string, error)
	Tags(ctx context.Context, repository string) ([]string, error)
	Annotations(ctx context.Context, repository, reference string) (map[string]string, error)
}
func discover(ctx context.Context, c registryClient, namespace string, versions bool) ([]skill, error)
var errNoCatalog = errors.New("registry does not support catalog enumeration")
```

This is SPEC §7.2's four-step pipeline — `_catalog` → filter to namespace →
`tags/list` per repository → read manifest annotations — and it backs both
`epos list` and `epos search`. `unsupported(err)` maps 403/404/405/501 to
`errNoCatalog`; 401 is deliberately excluded. `Annotations` reads only
`org.opencontainers.image.title` and `.description`.

**Metadata is cheap; content is not.** `internal/artifact/build.go` inlines the
config blob into its descriptor's `Data` field, and the comment says why:

> The config blob is carried inline in its descriptor's data field, so a client
> that only wants the frontmatter — `epos search`, **a discovery UI** — reads it
> out of the manifest without a second round trip.

So one manifest `GET` yields: `artifactType`, the title/description annotations,
`org.opencontainers.image.base.name` / `.base.digest`,
`dev.epos.skillfile.digest`, `dev.epos.skillfile.stages`, and the **complete
`SKILL.md` frontmatter as JSON** (`artifact.Config` is `map[string]any`, so
`license`, `references`, `allowed-tools` and any custom key survive).

`SKILL.md` itself does not. `internal/artifact/pack.go` puts exactly one
`application/vnd.agentskills.skill.content.v1.tar+gzip` layer rooted at
`<skill-name>/`. It is gzipped, so there is no range trick: reading `SKILL.md`
means fetching the whole layer and untarring it. Two routines already do it,
both unexported — `skillfile.ociTreeFiles([]byte) (*Tree, error)` and
`install.read(...) (packed, error)`.

**Counting.** `internal/metrics`:

```go
type Download struct{ Repository string; Verified bool; Client string; Version string }
func (d *Downloads) Record(ctx context.Context, dl Download)
```

`epos.downloads`, a monotonic `Int64Counter`, unit `{download}`, attributes
`repository`, `verified`, `client` (the User-Agent) and optionally `version`.
`cmd/epos-registry/handler.go`'s `countDownload` increments it for `GET` on a
blob answered 200 or 307; manifest requests and `HEAD` never count.
`metrics.New` implements `stdout` and `none` and refuses everything else.

**Deployment.** `.github/workflows/docs.yml` builds `docs/` with Astro and
pushes `docs/dist` to `gh-pages` via `peaceiris/actions-gh-pages@v4.1.0` with
`keep_files: true`; it triggers on `docs/**` only. Pages serves
`https://gaarutyunov.github.io/epos/` from `gh-pages` — `cname: null`, no
custom domain, no `pet-project` topic. `pr-preview.yml` puts PR builds under
`/epos/pr-preview/pr-<N>/`. `.goreleaser.yaml` builds `epos` and `epos-registry`
for three OSes and two architectures and publishes **no container image**.

**ui-kit is already vendored, at v0.2.0**, as raw ES source under
`docs/vendor/ui-kit/`, extracted by `git archive`. `VENDORED.md` gives the
reason: GitHub Packages needs authentication even for public packages, and a
workflow's `GITHUB_TOKEN` cannot read another repository's package.

---

## D1: epos#42 owns the recipe; #44 packs, publishes and displays it — unchanged

**Decision.** Honour epos#42's design **D1** verbatim. `examples/go-house/` —
the five-stage Skillfile, the two values profiles, the surgical drops (Viper,
`var _ Interface = (*Impl)(nil)`, the Go-only testcontainers slice) and the
integration test that asserts them — is #42's deliverable and is not respecified
here. #44 packs that directory, publishes the artifact, and renders it.

**Why this is not a judgement call.** epos#44's body and epos#42's `examples/go-house/`
task list describe the same artifact, clause for clause:

| #44's words | #42's task |
|---|---|
| "parametrisation of tools" | 2.6 — `{{ if .Values.openapi }}`, `di`, `telemetry`, `testcontainers`, plus one string parameter |
| "build with references from spf and golang pro by dropping what we don't use, I.e viper" | 2.4 — `AWK` out `## Viper Configuration Patterns` (251–362), `APPEND` the koanf translation |
| "…and explicit interface conformance" | 2.3 — `AWK` out `interfaces.md`'s "Interface Satisfaction Verification" (173–181); 2.8 asserts no `var _ ` survives |
| "add testcontainers reference but only go" | 2.5 — the `containers` stage copies only the Go example files |
| "pack my go skill as an example skill and push to registry" | #42 **D1**, explicitly deferred: "#44 keeps … the `epos pack`/publish of that example to the demo registry" |

#42's D1 also names the hazard, and it is the one worth respecting: *"If #44
runs first and invents its own Skillfile, the two diverge and the quick start
documents a build nobody maintains."* Writing a second Skillfile here would
produce exactly that.

**Sequencing, and the honest cost.** #42 is not merged (workspace#41, in owner
review). One task in this change — packing and publishing the example — cannot
run until `examples/go-house/` exists. **This does not make #44 blocked.** The
catalog command, the stats pipeline, the embedding, the pages and the tools page
— everything the issue's first paragraph asks for — depend on nothing in #42.
The recommendation is to leave #44 unblocked and merge #42 first, since #42 is
already in review and its artifact is the demo's only content dependency.

**Alternatives rejected.**

- *Move the Skillfile into #44 because "push to registry" is #44's.* Rejected.
  Packing and publishing a file is not the same as designing it, and #42 has
  already done the design work down to line numbers in the source skills. The
  boundary as drawn puts the artifact where the reasoning about it lives.
- *Block #44 on #42 on the board.* Rejected as the default, because it stops
  four-fifths of the work for one workflow step. Flagged as the owner's call: if
  #42 is rejected rather than merged, this change loses its demo content and
  needs a different example skill — say `epos pack`-ing one of the workspace's
  existing skills unmodified, which shows none of the three capabilities the
  issue wants shown.
- *Duplicate the wordmark.* Rejected — see **D8**.

---

## D2: the catalog belongs to `epos-registry`, not to the `epos` CLI

**This section is a reversal.** The previous draft put the catalog on `cmd/epos`
as `epos catalog serve|export`. The owner's review rejects that:

> Catalog is not part of CLI it's part of the registry. Like zot has a UI.
> People downloading CLI don't need ui artifacts.

The reversal is accepted, and it moves more than a command name. Everything
below — which binary grows, which package the assets are embedded in, which
package `internal/catalog` may import, how it is configured, and what the SPEC
has to say — follows from it.

**Decision.** The catalog is a capability of `epos-registry`:

```
epos-registry --catalog --catalog-namespace <ns> [--catalog-refs <file>] \
              --catalog.base-path / --catalog.stats-source clickhouse
                        # relay on /v2/, catalog on the same listener

epos-registry catalog export --upstream <url> --catalog-namespace <ns> \
              --base-path /epos/catalog --out catalog-dist \
              --catalog.stats-source clickhouse
                        # the same renderer, driven offline, to a directory
```

`cmd/epos` gains **nothing**: no command, no template, no stylesheet, no
vendored bundle. `internal/catalog` — the model, the renderer, the templates and
the embedded assets — is imported by `cmd/epos-registry` and by nothing the CLI
links.

**The zot comparison is exact, and it is the argument.** zot ships one binary
that terminates the Distribution API and, in the builds that enable it, serves a
browsing UI from the same process over the same listener. Nobody installs
`zli`, zot's *client*, and receives a web frontend with it. The split is
between the thing an operator deploys and the thing a user installs, and the
owner's second sentence is the whole point: someone who runs `go install
.../cmd/epos` to pack and push a skill should not be carrying 104 KB of
JavaScript, a stylesheet, four HTML template trees and a set of registry logos
to do it.

**One renderer, two drivers, unchanged.** The served catalog and the exported
directory come from one route table and one template set. A page that only one
of them can produce is a bug. What changed is which binary holds the renderer,
not that there are two ways to drive it.

**Why the export subcommand is on `epos-registry` too.** The exported site is
the *same renderer* over the same model; putting `export` on `epos` would put
`internal/catalog` back into the CLI's link graph and undo the whole decision
for the sake of where a subcommand is spelled. GitHub Pages cannot run a Go
binary (**D5**), so the export exists for the demo — and the demo is a
deployment concern, which is what `epos-registry` is.

### D2a: what the move costs, and what it buys

Stated together, because a reversal that only lists its benefits is not a
design decision.

**It costs two SPEC amendments that the previous draft used as its reason not to
do this.**

- **Decision ledger #2 — *"`/v2/` only; no second API surface"* — is amended.**
  The catalog is a second surface. It is not a second *API*: it serves HTML on
  `GET` under a reserved path prefix, speaks no Epos-specific media type and
  negotiates nothing. The amendment says exactly that, and says the catalog is
  **off unless enabled**, so a default `epos-registry` still serves `/v2/` and
  nothing else. The zot precedent is the argument the ledger row should carry.
- **§4.4 — *"no manifest cache, no digest→role lookup table, no shared store
  between replicas"* — is amended, narrowly.** The catalog's index and its
  per-digest document cache are exactly a manifest cache. The amendment scopes
  §4.4's prohibition to the **relay path**: no request under `/v2/` may be
  answered from, or made slower by, anything the catalog holds; the catalog's
  index is process-local, in memory, rebuilt at startup, derived entirely from
  upstream, shared with nothing and never written to disk. What §4.4 exists to
  protect — any `/v2/` request may land on any replica and get the same answer —
  is untouched, and that sentence stays in §4.4 word for word.

**Decision ledger #3 was cited by the previous draft and does not apply.** It
reads *"Rendering location — Helm model: templates rendered at install, never by
the registry or a server"*. That is about **skill values templates** — the
`{{ .Values.x }}` substitution §10.3 performs at install. The catalog renders
HTML pages about artifacts; it renders no skill and installs nothing. Reading
#3 as "the registry may not emit HTML" was a misreading in the previous draft
and is corrected here rather than carried forward.

**It costs an availability coupling on the relay, and this is the one that has to
be got right.** `epos-registry` today contacts upstream for the first time when
it answers its first request; it starts regardless of whether upstream is up.
The catalog builds its index at startup (**D3b**), so a naive implementation
makes an unreachable upstream at boot into a registry that does not start —
turning a catalog feature into an outage on the relay, which is precisely the
coupling §4.4's narrow amendment is supposed to avoid.

**Decision: a failed or partial index never stops the registry.** The listener
comes up first and `/v2/` serves immediately. The index build is a startup step
whose failure is logged and whose result is an empty catalog answering a page
that says the catalog could not be built; the relay is unaffected either way.
A skill that could not be read leaves that skill out and the rest listed, which
is **D3d** one level up. Enabling the catalog must not be able to reduce the
registry's availability, and that is asserted rather than intended.

**It costs a replica caveat, and it must be stated rather than discovered.**
With N replicas each building its own index at its own startup, two replicas can
briefly disagree about which skills exist — a skill published between two
restarts appears on some replicas and not others. That is a property of a
read-only view, not a correctness bug, and the alternative (a shared index) is
the durable state §4.4 refuses. The mitigation is that the *counts* are read per
request from a store all replicas share (**D4e**), so the numbers never
disagree; only the membership can, and only until the next restart.

**It costs a package-boundary problem the previous shape did not have, and this
is the sharpest consequence of the move.** The detail page needs the remote
fetch-and-unpack routine, which today is `skillfile.fetchOCIBase`. When the
catalog lived on `epos`, exporting it in place was free — the CLI already links
`internal/skillfile`. `cmd/epos-registry` does not, and `internal/skillfile`
imports **`go-git/v5`, `benhoyt/goawk`, `bluekeyes/go-gitdiff` and
`goccy/go-yaml`**: the entire Skillfile build language would land in the
registry binary to obtain one function.

**Decision: the routine moves down, it is not exported in place.**
`internal/registry` gains a `FetchContent(ctx, ref) (map[string][]byte, error)`
— resolve, fetch the manifest, assert exactly one layer, fetch it, untar into an
in-memory file map, keeping `checkPath`, the symlink and hardlink rejection and
the 64 MiB cap. `internal/skillfile` builds its `Tree` from that map and keeps
the `Tree` type, so nothing about `FROM` changes and there is still exactly one
implementation of the guards. This is a **larger refactor than the previous
draft's "export it"**, it is the honest price of the move, and it is worth
paying: it also gives `epos-registry` a dependency budget it can defend.

**It buys three things.**

1. **`epos` stops growing.** No `//go:embed`, no vendored bundle, no goldmark in
   the CLI. The Markdown renderer, the templates and the assets are linked by
   `epos-registry` alone.
2. **The counts stop being a remote reading.** The process that *counts* a
   download and the process that *renders* the number are now the same
   deployment, which is what makes **D4e**'s per-request read and the owner's
   *"pull, refresh, the number moved"* one host rather than two.
3. **Configuration stops being a special case.** The previous draft argued at
   length for flags-only, no-koanf, and then had to make an exception for the
   store credential. `epos-registry` is already a koanf server with an
   `EPOS_REGISTRY_` prefix; the catalog's settings join it, and the credential
   is `EPOS_REGISTRY_CATALOG_STATS_DSN` like every other key. See **D2b**.

**Rejected: a third binary, `epos-catalog`.** A third goreleaser matrix, a third
set of release artifacts and a third `main`, bought for no isolation that
matters — and it splits the catalog from the counter it renders, which is the
one thing the move exists to join. zot does not ship its UI as a separate
binary either.

**Rejected: a build tag, the way zot gates its UI.** It is the closest imitation
of the reference, and it is not taken: a build tag means goreleaser builds two
`epos-registry` variants, and it means the catalog's code is not compiled by the
ordinary `go build ./...` or seen by `go vet`, which is how a tagged package
rots. A runtime flag, defaulting off, gives the operator the same choice and
keeps one artifact and one build. The binary carries the assets either way.

**Rejected: leaving `epos catalog serve` as well, "for local browsing".** It is
the tempting compromise and it defeats the decision — the CLI would link
`internal/catalog` to have it, which is precisely the artifact the owner does
not want in a CLI. Anyone with a private registry runs `epos-registry
--catalog`, which is the same binary an operator of that registry already has.

### D2b: configuration joins `epos-registry`'s koanf tree

**Decision.** Every catalog setting is a key on `epos-registry`, in the dotted
koanf style the binary already uses, resolvable from a flag or from
`EPOS_REGISTRY_*`:

| key | flag | what it does |
|---|---|---|
| `catalog` | `--catalog` | serve the catalog on the existing listener; **default false** |
| `catalog.base-path` | `--catalog.base-path` | prefix every internal URL (**D2c**) |
| `catalog.namespace` | `--catalog.namespace` | enumerate this namespace through `_catalog` |
| `catalog.refs` | `--catalog.refs` | a file of explicit references instead (**D3**) |
| `catalog.stats-source` | `--catalog.stats-source` | `none` (default), `clickhouse` or `file` (**D4e**) |
| `catalog.stats-dsn` | *(no flag)* | **environment or file only** — a credential |
| `catalog.stats-file` | `--catalog.stats-file` | a counts document |
| `catalog.stats-ttl` | `--catalog.stats-ttl` | freshness bound on the per-request read |

**Exactly one dot, then kebab-case — and this is a correction, not a style
preference.** An earlier draft of this section wrote three-level keys
(`catalog.stats.source`) and claimed `EPOS_REGISTRY_CATALOG_STATS_DSN` would
reach them "with no new mechanism". **It would not.** `loadConfig`'s
`TransformFunc` lowercases, maps `__` to `.`, then applies a **hardcoded**
`strings.Replace(key, "metrics_", "metrics.", 1)`, then replaces every remaining
`_` with `-`. So `EPOS_REGISTRY_CATALOG_STATS_DSN` becomes
`catalog-stats-dsn` — one flat key, matching nothing.

Two consequences:

- **The key shape follows the one the binary already has.**
  `metrics.version-attribute` is one dot and then a hyphen, and the catalog's
  keys are the same shape for the same reason. Inventing a third level would
  require generalising the transform, and generalising it — mapping every `_` to
  `.` — would break `metrics.version-attribute` itself, whose env form is
  `EPOS_REGISTRY_METRICS_VERSION_ATTRIBUTE`. That is a breaking change to a
  shipped key, bought for punctuation.
- **The transform still needs one line.** `catalog_` must be mapped to
  `catalog.` beside the existing `metrics_` line. It is a one-line change and it
  is the difference between the credential resolving and silently not, so it is
  a task rather than an assumption.

**The DSN has no flag at all** — a long-running server's arguments are readable
by every process on the host — which is now an ordinary consequence of being a
koanf key rather than the exception to a flags-only rule the previous draft had
to argue for. Because env is that key's **only** path, the transform above is
load-bearing for it specifically, and a test resolves it end to end.

`epos-registry catalog export` is a subcommand of the same binary and reads the
same keys, minus `catalog` and `catalog.stats-ttl` and plus `--out`.

**One mechanical detail that will otherwise cost an hour.** `newRootCommand`
declares `--addr`, `--upstream` and the `metrics.*` flags on `cmd.Flags()` —
**local** flags, which a subcommand does not inherit. `export` needs
`--upstream` and every `catalog.*` key, so either those move to
`PersistentFlags()` or the subcommand declares its own set and shares one
registration helper with the root. Prefer the shared helper: making the server's
`--addr` visible on an export subcommand that opens no port is worse than a
little duplication of registration.

The rest is the repository's existing shape, called out because a new command is
where it gets forgotten: a factory returning `*cobra.Command`, `RunE` so errors
propagate, `cobra.NoArgs`, and output through `cmd.OutOrStdout()`.

**Consequence: `internal/cli/discover.go` still gets lifted, and now it is
load-bearing rather than tidy.** `cmd/epos-registry` must not import
`internal/cli` — that would link the entire CLI, cobra tree and all, into the
registry. So the discovery client, `discover`, `skill` and `errNoCatalog` move
to a new `internal/registry` package, exported, and `internal/cli` calls into
it. `registryOptions` does **not** move: it lives in
`internal/cli/credentials.go`, carries the cobra flag binding and the Docker
credential store, and is shared by `pull`, `push`, `build`, `sign` and
`install`. `internal/registry` defines its own plain options struct — plain-HTTP,
a credential resolver, a client — with no cobra and no koanf in it, and each
binary builds one its own way.

Behaviourally this is still a move: `epos list` and `epos search` must produce
byte-identical output afterwards, the existing `discover` tests move with it,
and their expected output must not be edited in the same commit. If it has to
be, the move was not a move.

**Consequence: the docsgen drift gate fires twice.** `internal/docsgen` renders
`docs/src/pages/cli.astro` from the live cobra tree and CI fails on any diff.
The tree it walks is `epos`'s, which this change no longer touches — but
`epos-registry`'s new flags are rendered nowhere today, which is itself a gap
(**D17** closes it, because the Epos skill's CLI reference has the same
problem).

### D2c: the catalog is served under a base path, and it is the same in both modes

**Decision.** Both drivers take a base path (default `/`) — `--catalog.base-path`
on the server, `--base-path` on `export` — every internal URL the templates emit
is prefixed with it, and the two produce identical bytes **for the same base
path**.

The base path is also what keeps the catalog off `/v2/`. A served catalog
mounted at `/` still hands `/v2/` to the relay first: the registry's routes are
matched before the catalog's, and no catalog route may shadow one. That is a
requirement, not an ordering accident — an operator who sets
`--catalog.base-path /v2` is refused at startup.

This is not a nicety. The project's Pages site is a *project* page:
`docs/astro.config.mjs` reads `base = process.env.BASE_PATH ?? "/epos"` for
exactly this reason, and `pr-preview.yml` re-points it again per pull request to
`/epos/pr-preview/pr-<N>`. The demo lives at `/epos/catalog/`. A template
emitting `/skills/foo` or `/assets/app.css` resolves at the domain root and
404s on every page.

**Rejected: relative URLs throughout.** It avoids the flag, and it breaks the
moment a route has a different depth from another — a detail page at
`catalog/skills/foo/` and a home page at `catalog/` cannot share one relative
asset path without `../` counting, which is exactly the bug this is meant to
avoid.

**Rejected: prefixing only on export.** It makes `serve` and `export` produce
different bytes by construction, which is the invariant **D2** exists to keep.

---

## D3: Two enumeration modes, because `_catalog` is not universal

**Decision.** The catalog takes its skill list from **either** a `_catalog`
sweep **or** an explicit list of references, and the choice is a setting, not a
fallback chain.

- `catalog.namespace` — the `epos list` path, run against the registry the
  process already fronts. Requires `GET /v2/_catalog`.
- `catalog.refs` — a checked-in list of `<host>/<repo>:<tag>` references, one
  per line. No `_catalog` required.

**There is no `--registry` flag any more, and that is a consequence of D2.**
When the catalog served from the CLI it had to be told which registry to browse.
Served from `epos-registry`, the registry is `--upstream`, which is already
required and already configured: the catalog shows the skills of the registry it
fronts, which is the only thing a registry's own UI should show. `export` takes
`--upstream` explicitly because it runs without a listener, and it is the same
key.

**Why both.** `errNoCatalog` exists in the shipped code because registries
disagree about `_catalog`, and SPEC §4.1 now says so in its own words:

> `GET /v2/_catalog` is proxied **when the upstream registry supports it**, and
> is the basis for discovery (§7). It is outside the Content Discovery
> conformance category and **is disabled on several hosted registries**; where
> upstream does not support it, `epos-registry` relays upstream's response
> unchanged and `epos search` reports the capability as unavailable.

The demo publishes to `ghcr.io` (**D10**), and a demo that cannot enumerate its
own registry is not a demo. A `--refs` file also makes the static export
reproducible: the same file produces the same site.

**Why not a fallback.** Silently degrading from "everything in the namespace" to
"whatever a file happens to list" makes a missing skill indistinguishable from a
registry that answered 404. The two modes produce different sites and the
operator should have said which one they wanted.

**Metadata comes from the manifest, content from the layer.** For the list and
leaderboard pages, one manifest `GET` per reference is enough — title,
description, the frontmatter from the inline config, and the provenance
annotations. The content layer is fetched only for a detail page, and only for
`SKILL.md`; `serve` caches the parsed result keyed by manifest digest (an
immutable key, so the cache never needs invalidating), and `export` fetches each
one once by construction.

**Rejected: a hand-authored catalog index file committed to the repo.** SPEC
§15 already rules on it — *"Hand-authored or scanned catalogs: drift and cost
without solving the general case"*. `--refs` is not that: it names references to
resolve live, and every field on the page still comes from the registry.

### D3a: one page per repository, showing one version

**Decision.** A skill is a **repository**. One leaderboard row, one catalog row
and one detail page per repository; the detail page renders the newest version
and lists the others as links that change the rendered document without becoming
routes of their own.

**Why.** The download counter's only key is `repository` — `Download.Repository`,
and SPEC §5.1 is explicit that no manifest parsing is required to count. A
per-version page would have to show a per-version count that does not exist, or
show the repository's count on every version page, which is worse. skills.sh
resolves it the same way: one page per skill, no version anywhere on it.

`discover(..., versions=true)` yields one row per tag and is what `epos list
--versions` uses; the catalog uses the repository-level form and reads the tag
list separately for the version selector.

### D3b: on `serve`, a route resolves only against the index built at startup

**Decision.** `serve` builds its index once at startup and answers only for
repositories in it. A path naming anything else is a 404, not a fetch.

Without this, a URL path is an instruction to fetch an arbitrary repository from
the configured registry — an unauthenticated, unbounded proxy wearing a catalog.
Since paths are also derived from registry-supplied repository names, the same
rule is what keeps route construction and route resolution symmetrical.

The index is static for the process's lifetime. Refreshing it is a restart. That
is a real limitation and it is the right one for a first version: a refresh loop
is a goroutine, a lock and a cache-invalidation policy.

**This says nothing about the counts.** The *numbers* beside the skills are read
per request (**D4e**), which is what makes the owner's *"numbers change when we
download something and refresh the page"* true. Fixing the index at startup and
fixing the counts at startup are separate decisions and only the first is made
here; conflating them is the mistake this paragraph exists to prevent.

### D3c: the content layer is untrusted, and the existing guards come with it

**Decision.** The relocated remote-fetch routine keeps every guard
`internal/skillfile` applies today: the 64 MiB layer cap, `checkPath`'s refusal
of `..`, absolute and non-canonical entries, and the rejection of symlinks and
hardlinks. The routine is today's **`skillfile.fetchOCIBase`** — resolve, fetch
the manifest, assert exactly one layer, fetch it, untar — not `install.read`
(which reads the *local store*) and not `ociTreeFiles` (which takes bytes
already in hand).

**It moves to `internal/registry` rather than being exported where it is**
(**D2a**): `epos-registry` must not link `internal/skillfile`, which imports
`go-git/v5`, `goawk`, `go-gitdiff` and `goccy/go-yaml`. `internal/registry`
exposes the fetch and the untar as a file map; `internal/skillfile` keeps `Tree`
and builds one from that map, so `FROM` behaves identically and the guards have
exactly one implementation. Moving it, rather than copying it, is the whole
point — a second copy is how one of them loses a guard.

Those guards exist because a Skillfile's `FROM` can name any registry. The
catalog points at any registry by definition, so if anything the exposure is
larger. Losing a guard while "reusing" the code is the failure mode worth
naming: a decompression bomb or a `../../etc` entry from a hostile artifact
should fail that artifact's page, not the process — which is why **D3d** exists.

### D3d: one bad artifact fails one page

A skill whose layer is oversized, malformed, hostile or simply unreachable still
appears in the catalog from its manifest metadata; its detail page says the
document could not be read. A catalog that 500s because one publisher pushed a
bad artifact is a catalog an attacker can take down.

---

## D4: Download statistics — a persistent store, and what may be ranked

This is the part of the issue with no implementation behind it, so it gets the
most space.

**This section has been reversed twice, and the second review sharpened it.**
The first draft fed the leaderboard from a snapshot scraped out of
`epos-registry`'s stdout; the owner rejected that and asked for a persistent
store, suggesting ClickHouse. The second review keeps the store and fixes the
shape of the pipeline:

> Instead of adding ingestion code for clickhouse, add OTEL collector that will
> process **traces** and export values to clickhouse in some format appropriate
> for catalog. **Define the database schema in the spec.** This way we don't need
> additional code for clickhouse. And **we don't need write credentials for the
> registry.** The catalog only reads from it. **It should be an optional
> feature.** People who don't want to ship clickhouse don't get the leaderboard
> and downloads.

Four instructions, and each of them changes something:

1. **Traces, not metrics** — the durable record of a download is a **span**, not
   a counter datapoint (**D4a**).
2. **The schema is defined here** — the DDL is in this design and checked into
   the repository, not left to the implementation (**D4b**).
3. **The registry holds no write credential** — the collector is the only writer,
   which is a security property and is specified as one (**D4g**).
4. **The whole thing is optional** — off by default, at two independent
   switches, and the pages degrade rather than break (**D4h**).

What survives unchanged from the previous draft is the part that was never about
the pipeline: ranking counts the verified side only (**D4d**), and the raw
user-agent must never reach a store (**D4c**).

### D4a: a download is recorded as a span, and that is what makes the rest cheap

**Decision.** `epos-registry` gains an **OTLP traces exporter**, selected by a
new `--traces.exporter` key (`none` by default, `otlp` to enable). Every
download it counts also emits one span, `epos.download`, with the same
attributes the counter carries. The existing `epos.downloads` counter and its
`stdout`/`none` exporters are **unchanged**.

One recording site, two emissions. `countDownload` calls one function; that
function increments the counter and, when tracing is enabled, ends a span. The
two cannot describe different events because there is one call and one attribute
set — which is what SPEC §5.3's *"one instrumentation path"* means and what a
second, parallel instrumentation would break.

**Why a span rather than the `otlp` metrics exporter the previous draft chose.**
This is the owner's instruction and it is also, on the merits, the better half of
the fork:

- **A span is an event, so counting is `count()`.** The previous draft spent
  three paragraphs, a verification task and an exporter option on
  **temporality** — cumulative rows from N replicas and several process lifetimes
  land in one table and `sum()` double-counts them, so the counter had to be
  exported with delta temporality and the reason recorded in a comment. With one
  row per download, none of that exists. **Tasks 1.5a and 3.2a are deleted, not
  moved**, and the query stops being a thing a reader has to re-derive.
- **It moves off an alpha component.** `clickhouseexporter` documents its own
  support as **beta for traces and logs, alpha for metrics**. The previous draft
  built the whole leaderboard on the alpha half and carried a verification task
  whose failure condition was "stop and report it to the owner". The traces path
  is the supported one, and its `otel_traces` table is the exporter's most
  stable schema.
- **It carries more than a count, for free.** A span has a timestamp, so
  `epos_downloads_total`'s hourly bucketing (**D4b**) is a `GROUP BY` rather
  than a second instrument, and the time series **D8** defers becomes a query
  rather than a redesign.

**What it costs, stated plainly.** One span per blob `GET` is far more rows than
one counter export per interval. Three consequences the implementation must
respect:

- **Sampling must be off.** A sampled trace is a sampled count, and a
  leaderboard built on 10 % of downloads is a wrong number presented as a right
  one. The tracer provider uses `AlwaysSample` for this span, deliberately, with
  a comment saying that changing it silently changes every number the catalog
  renders. If volume ever forces sampling, the answer is pre-aggregation in the
  collector, not a sampled count.
- **The span is minimal.** No HTTP server instrumentation, no auto-instrumented
  middleware, no request headers. One span, four attributes, no events, no
  links. This is a measurement that happens to travel as a span, not a tracing
  deployment.
- **The rows expire and the counts must not.** `otel_traces` is written with a
  TTL. That is correct for spans and fatal for a lifetime counter, which is
  exactly why **D4b** rolls them up into a table with no TTL rather than
  querying the raw spans.

**Why not `prometheus`.** Unchanged from the previous draft and still right: a
scrape needs a second listener, and a scrape reaches one replica of a
deployment specified as N behind a load balancer (§4.4). Push is the shape that
fits. §5.3's `prometheus` row stays unimplemented.

**§5.3 is amended, where the previous draft claimed it was completed.** The
previous draft argued that implementing the `otlp` *metrics* exporter completed
§5.3's table rather than amending it. That argument no longer applies: `otlp`
under §5.3 stays unimplemented, and §5.3 gains a new subsection for the
**download span** — its name, its attributes and the fact that it is the durable
record. Claiming otherwise would be the more comfortable sentence and the false
one.

### D4b: the store is ClickHouse, and the schema is defined here

**Decision.** The persistent store is **ClickHouse**. It is filled by an
**OpenTelemetry Collector** running the contrib `clickhouseexporter` on its
**traces** pipeline. epos ships the collector configuration and the DDL below;
epos writes **no ingestion code at all**.

```
epos-registry --traces.exporter otlp ──OTLP──▶ Collector ──INSERT──▶ ClickHouse
       │                                                        (otel_traces)
       │  read-only DSN                                                │
       │                                                     materialized view
       └───────────── catalog ◀────── SELECT ────── epos_downloads_total
```

**Why a collector rather than writing to ClickHouse from Go.** ClickHouse has no
OTLP receiver — verified, and worth writing down because it is the thing most
likely to be assumed. Open-source ClickHouse exposes native TCP and an HTTP
interface; neither speaks OTLP. So the two ways to get OTel data into it are the
collector's `clickhouseexporter` or bespoke INSERTs from your own process. The
second means a ClickHouse **write** client in `epos-registry`, batching, retry
and back-pressure written by hand, and a schema epos then owns and migrates.
The collector is a container and a config file, and it is the reason the
registry needs no write credential (**D4c**).

**The schema, in three parts.** The first is the collector's; the other two are
this project's and are checked in as one `.sql` file.

**1. `otel_traces` — created by the exporter, never by epos.** The
`clickhouseexporter` creates it on first use (`create_schema: true`) or is given
it by an operator (`create_schema: false`, which its README recommends in
production). Epos declares none of it and alters none of it. The columns the
rollup reads are `Timestamp`, `ServiceName`, `SpanName` and
`SpanAttributes Map(LowCardinality(String), String)`.

**2. `epos_downloads_total` — the catalog's table, and the only thing it
queries.**

```sql
CREATE TABLE IF NOT EXISTS epos_downloads_total
(
    Repository  LowCardinality(String),
    Verified    Bool,
    Bucket      DateTime,        -- start of the hour, UTC
    Downloads   UInt64
)
ENGINE = SummingMergeTree
PARTITION BY toYYYYMM(Bucket)
ORDER BY (Repository, Verified, Bucket);
```

**3. `epos_downloads_mv` — the rollup that fills it.**

```sql
CREATE MATERIALIZED VIEW IF NOT EXISTS epos_downloads_mv
TO epos_downloads_total AS
SELECT
    SpanAttributes['repository']         AS Repository,
    SpanAttributes['verified'] = 'true'  AS Verified,
    toStartOfHour(Timestamp)             AS Bucket,
    count()                              AS Downloads
FROM otel_traces
WHERE ServiceName = 'epos-registry' AND SpanName = 'epos.download'
GROUP BY Repository, Verified, Bucket;
```

**The catalog's query, in full, because "define the schema" means the read side
too:**

```sql
SELECT Repository, Verified, sum(Downloads) AS Downloads
FROM epos_downloads_total
WHERE Repository IN ? AND Bucket >= ?
GROUP BY Repository, Verified;
```

**Five properties of that schema, each of which is a decision:**

- **`sum()` is not optional.** `SummingMergeTree` collapses rows *eventually*, in
  background merges. Reading `Downloads` without summing returns whatever the
  merge state happens to be — right on an idle demo, wrong under load. The
  aggregation is in the query, always, and the DDL carries a comment saying so.
- **The rollup is what survives the TTL.** `otel_traces` expires its rows;
  `epos_downloads_total` has no TTL, so a lifetime count outlives the spans that
  produced it. Querying the raw spans instead would have produced a leaderboard
  that quietly shrinks the day the TTL first fires — the sort of defect nobody
  finds until it has been wrong for a month.
- **A materialized view is an insert trigger, so it must exist before the
  collector starts.** ClickHouse materialized views see only rows inserted after
  they are created; they do not backfill. Applying the DDL is a bootstrap step
  in the compose file and in CI, before the collector's first insert, and
  backfilling an existing deployment is one `INSERT … SELECT` that the `.sql`
  file carries as a comment.
- **Hourly buckets, not raw rows.** An hour is small enough for any window a
  page shows and large enough that the table stays negligible. It also makes
  **D8**'s deferred sparkline a `GROUP BY Bucket` rather than a new pipeline.
- **`Verified` is a `Bool` here and a string in the span.** OTLP attributes on
  the wire are strings in the exporter's map column, so the view does the
  conversion once, in the one place that knows the encoding.

**What this buys against the owner's words.** *"We don't need additional code for
clickhouse"* is literally true: there is no Go on the write path, and the read
path is one `SELECT` against a table this document defines. The `.sql` file and
the collector `.yaml` are configuration, in the sense the repository already
uses that word for `.goreleaser.yaml` and `.golangci.yml` — reviewed, pinned and
diffable, and not a schema an implementation improvises.

**Rejected: querying `otel_traces` directly and skipping the rollup.** It removes
two DDL statements and it is what an implementation will reach for first. It
scans raw spans on every page load, it breaks silently at the first TTL
expiry, and it puts the encoding of `verified` into every query instead of into
one view. Named here so that removing the view is a decision someone has to
argue for.

**Rejected: ClickHouse Cloud, or any managed store, as the demo's backing.** It
needs an account, a credential and a bill, all of which are the owner's to
provision and none of which the repository has. What the demo can do without any
of that is **D5**.

**Rejected: SQLite, or a file the registry appends to.** It is the smaller
thing, and it is exactly what §4.4 refuses: durable state in `epos-registry`
that N replicas cannot share.

### D4g: the registry never holds a credential that can write

**This is a security property, not a convenience, and the owner named it as
one:** *"we don't need write credentials for the registry."*

**Decision.** Three principals, three privileges, and they are declared in the
same `.sql` file as the schema:

| principal | credential | privilege |
|---|---|---|
| `epos-registry` (relay) | an **OTLP endpoint**. No database credential of any kind. | none — it cannot reach ClickHouse |
| the collector | `epos_collector` | `INSERT` on `otel_traces` |
| the catalog | `epos_catalog` | `SELECT` on `epos_downloads_total`, and nothing else |

```sql
CREATE USER IF NOT EXISTS epos_catalog IDENTIFIED BY '...'
    SETTINGS PROFILE 'readonly';
GRANT SELECT ON epos.epos_downloads_total TO epos_catalog;
```

**Three things this makes true, which the previous draft could only assert:**

- A compromise of the relay yields an OTLP endpoint, not a database. The relay
  is the process on the public internet answering unauthenticated `GET`s; it is
  the one that must hold nothing.
- The catalog cannot create, alter, insert or delete, because it has no grant to
  do so. *"The catalog only reads"* stops being a rule an implementer has to
  remember and becomes a rule the database enforces.
- `readonly` alone is not enough and the DDL says so: a read-only user can still
  run a query expensive enough to be a denial of service, so the profile also
  bounds `max_execution_time` and `max_result_rows`. This matters most for
  **D5a**'s rejected browser-side query and is worth having regardless.

**The one place the registry does read the store, named because D2 created it.**
The catalog now runs *inside* `epos-registry` (**D2**), so the process does hold
the read-only DSN — the previous draft's *"the registry's only relationship with
the store is export"* is no longer true and has been rewritten rather than left
to be discovered. What replaces it is narrower and checkable: **no request under
`/v2/` ever reads the store.** The relay path holds no DSN, makes no query and
cannot be made slower or less available by one; a store that is unreachable
costs the catalog its numbers and costs `/v2/` nothing. That is asserted by a
test, not by a paragraph.

### D4h: the whole feature is optional, at two independent switches

> It should be an optional feature. People who don't want to ship clickhouse
> don't get the leaderboard and downloads.

**Decision.** Two switches, both defaulting to off, and neither implies the
other:

| switch | default | off means |
|---|---|---|
| `--traces.exporter` | `none` | the registry emits no spans, needs no collector, and nothing is stored |
| `--catalog.stats-source` | `none` | the catalog renders with no counts at all |

An operator who wants a browsable registry and no telemetry stack runs
`epos-registry --catalog` and gets pages with no numbers. An operator who wants
numbers in Grafana and no pages runs `--traces.exporter otlp` without
`--catalog`. Neither combination is a degraded mode; both are configurations.

**The consequence for the home page, which is a real correction.** The previous
draft's proposal said flatly that *"the home page **is** the leaderboard"*. With
statistics optional, that cannot be the requirement, and the delta already had a
"degrades honestly" scenario contradicting the prose above it. Resolved in
favour of the switch: **the home page is the catalog's entry page. It is a
ranked leaderboard when a statistics source is configured, and a deterministic
index of skills when one is not** — the pull column absent rather than zeroed,
and no ordering claiming to be a popularity ranking. Both shapes are specified
and both are tested; neither is an error path.

**And the dependency follows the switch.** `clickhouse-go/v2` links into
`epos-registry` whether or not a source is configured, because Go has no
conditional imports. That is honest to state and it is the argument for keeping
the *store* optional rather than making the *driver* optional: roughly sixteen
pure-Go modules in the binary an operator deploys, and none in the CLI a user
installs (**D2**).

### D4c: the `client` attribute must be dropped, and with a store it is worse than cardinality

The previous draft recorded this as a constraint on a hypothetical future
exporter. Something is now shipping, so it is a requirement — and the span
(**D4a**) makes the argument stronger rather than weaker.

`Download.Client` is the raw `User-Agent`. Under a metrics exporter it is
attacker-controlled, unbounded cardinality — one time series per distinct
User-Agent per repository, forever, created by anyone who can issue a blob
`GET`. The SPEC already refuses far less: `VersionAttribute` is off by default
with the comment *"version-valued attributes accumulate without bound under a
Prometheus exporter, one time series per version per repository, forever."*
Versions are at least finite and authored by the publisher; User-Agents are
neither.

**Under a trace exporter it is not a cardinality problem, it is a data problem.**
Every span becomes a durable row in ClickHouse carrying an arbitrary
attacker-supplied string, retained for the TTL, in a table an operator will
eventually put a dashboard on. A registry with a public read path would be
storing unbounded caller-controlled text on behalf of anyone who can `curl` a
blob. That is worse than the row-count objection and it is the reason this stays
a hard rule rather than a tuning knob.

**Decision.** The attribute is removed by the pipeline in both directions, not
by convention:

- **On the metric**, by an SDK view — an allow-list, so a future attribute is
  excluded until someone decides otherwise:

  ```go
  sdkmetric.NewView(
  	sdkmetric.Instrument{Name: "epos.downloads"},
  	sdkmetric.Stream{
  		AttributeFilter: attribute.NewAllowKeysFilter("repository", "verified", "version"),
  	},
  )
  ```

  registered with `sdkmetric.WithView` on the provider.
- **On the span**, by never setting it. The span carries `repository`,
  `verified` and optionally `version`, and the attribute set is built by the
  same function that builds the metric's, so the two cannot diverge. There is no
  span-side equivalent of a view, which is exactly why the shared attribute
  builder is the mechanism rather than a second list to keep in step.

Three details that are easy to get wrong:

- **Exemplars.** The SDK documents that attributes a view filters out may still
  appear on exemplars, which record the dropped measurement attributes.
  Exemplars must be off, or filtered too.
- **Auto-instrumentation would put it back.** Any `otelhttp` handler wrapper
  records `http.user_agent` on its own server span as a matter of course. This
  is the argument in **D4a** for one hand-written minimal span and no HTTP
  auto-instrumentation on the relay: a middleware added later for unrelated
  reasons would silently reintroduce exactly what this section removes.
- **The stdout exporter.** Nothing forces the filter to be exporter-specific,
  and making it so is a second code path for no gain. Apply it unconditionally.
  `tests/integration/steps_counting.go` is the only place in the repository that
  reads the attribute at all, which is the argument for dropping it everywhere
  rather than only where it is dangerous.

**Bucketing is not the fix.** Collapsing the user-agent into an enum
(`epos`/`oras`/`docker`/`other`) duplicates `verified` — a request from `epos
pull` is precisely a request carrying `Epos-Download` — and adds a parsing rule
that rots on every client's next release.

**SPEC §5.3's attribute list changes.** It names `repository`, `verified` and
`client`. Dropping `client` is an amendment to that sentence and this change
makes it, with the reason.

### D4d: the leaderboard ranks the verified side of the counter

**Decision.** The default ranking metric is
`epos.downloads{verified="true"}`. The unverified side is available and may be
displayed, but it is never the rank key and never the headline number.

**Why.** `metrics.go`'s own comment on `Download.Verified` is the argument:

> The unverified side of this attribute is known to be inflated, and signatures
> are the largest single source: a cosign signature is a referrer of the skill
> manifest, so its blob shares the skill's repository, and every `epos verify`
> fetches one. Those fetches are counted here as unverified downloads of the
> skill and cannot be distinguished without a digest→role table, which is the
> durable state SPEC.md 4.4 refuses.

A leaderboard ranking a number the code documents as wrong is worse than no
leaderboard. The verified side has a precise meaning — *pulls made by `epos`* —
and the page says exactly that rather than "downloads".

The precedent is the reference design's own: skills.sh's counts are anonymous
telemetry from the `npx skills` CLI, not registry traffic (`/docs/cli`: *"the
CLI collects anonymous telemetry data to help rank skills on the leaderboard"*).
Its column header is **Installs**, not Downloads. epos's equivalent honest
header is **Pulls**, and that is what the pages use, with the definition one
hover away.

### D4e: the catalog reads counts through a `Stats` source, and reads them per request

**Decision.** One interface, one method, `context`-taking, three implementations
selected by `catalog.stats-source`:

```go
// Stats reports how often each repository has been pulled.
type Stats interface {
	Pulls(ctx context.Context) (Counts, error)
}

// Counts is per-repository pulls as of a stated moment.
type Counts struct {
	CapturedAt time.Time
	Rows       map[string]Pulls // keyed by OCI repository
}

type Pulls struct{ Verified, Unverified int64 }
```

**Which repositories a source reports on is fixed when the source is built, not
passed to the method.** The catalog asks about the repositories in its index
(**D3b**), and an unscoped `clickhouse` source would return every repository the
collector has ever seen — including ones this catalog does not list. So the
repository set is a constructor argument:
`NewClickHouseStats(db, repos []string, ttl time.Duration)`. That keeps the
interface one method wide, which is the property that makes a fourth source an
addition rather than a rewrite, and it puts the scope where the index already
is. `none` and `file` ignore it; `file` still filters its rows to the index, so
the three sources answer the same question.

| source | where the numbers come from | who uses it |
|---|---|---|
| `none` (default) | nothing — the column is absent and the home page is an index rather than a ranking (**D4h**) | anyone who wants a browsable registry without a telemetry stack |
| `clickhouse` | the `SELECT` in **D4b**, against `epos_downloads_total`, with a read-only credential (**D4g**) | `epos-registry --catalog` on a live deployment; the demo's export job |
| `file` | a JSON document with the shape of `Counts` above | reproducible exports, unit tests, and anyone with numbers but no store |

`none` is the default and it is a first-class mode, not a failure state: it is
the *"people who don't want to ship clickhouse"* case the owner named, and a
catalog that renders a broken leaderboard in it is worse than one that renders a
catalog.

`file` is kept even though `clickhouse` exists, and it earns its place three
times over: it is what makes the demo delta's *"the export is reproducible"*
scenario testable, it is how the renderer's unit tests get counts without a
container, and it is the answer for anyone who has numbers from somewhere epos
does not know about. It is an *input*, never a store the catalog writes.

`Counts` is the wire shape, the query-result shape and the in-memory shape,
deliberately — one definition, `encoding/json` tags, no converter, no second
schema to drift.

**When counts are read, and why this is not a detail.** The owner's e2e comment
requires that *"numbers change when we download something and refresh the
page"*. That is only true if `serve` reads counts **per request**, not once at
startup. **D3b** fixes the *index* at startup; it says nothing about the
numbers, and conflating the two would have quietly made the refresh assertion
unsatisfiable.

- `serve` calls `Stats.Pulls` on the request path, behind a short TTL cache
  (single-digit seconds) so a burst of page loads does not become a burst of
  queries, and behind a timeout so a slow store cannot pin a handler. A failing
  query degrades counts to absent and serves the page.
- `export` calls it once and bakes the answer into the files, with the capture
  time on the page.

**The cache is a lazy refresh on the request path under one mutex — not a
background goroutine.** A refresher goroutine needs an owner, a shutdown path
threaded through `srv.Shutdown`, and a `-race` story on three platforms, and it
buys nothing here: the work is one query, and the first request after the TTL
expires is the natural place to do it. Holding the mutex across the query
serialises a stampede for free; if that proves too coarse, `singleflight` is the
next step and it is still not a goroutine anyone owns. This also makes
`--catalog.stats-ttl=0` exactly "query every request", which is what the end-to-end test
sets it to rather than sleeping.

**The credential does not go on the command line.** A `--catalog.stats-dsn` flag
would put a working credential for a queryable database in `ps(1)` and in every
shell history on the box, for a process that runs for days. So the key has **no
flag at all**: it is `catalog.stats-dsn`, reachable from
`EPOS_REGISTRY_CATALOG_STATS_DSN` or from a file the configuration names.

Since **D2**, this is an ordinary koanf key rather than an exception. The
previous draft had argued the catalog should be flags-only and then had to carve
out the DSN; served from `epos-registry`, the setting simply joins the tree the
binary already resolves, and the absence of a flag is the whole mechanism.

The TTL is the stated freshness bound in the stats delta. It must be short
enough that the e2e assertion — pull, reload, number moved — is not flaky, which
means the test either waits out the TTL or the TTL is configurable and the test
sets it to zero. Prefer the latter; a test that sleeps is a test that will be
made to sleep longer.

**One new hazard the move creates, and it has to be answered.** The catalog now
shares a process with the relay, so a catalog request that blocks on a slow
ClickHouse holds a goroutine in the process that is also answering `/v2/`. The
bounded query timeout and the single-flight TTL cache above are what keep that
from becoming a relay problem, and the integration tier asserts the property
directly: with the store unreachable, `/v2/` latency is unaffected and every
catalog page still serves without counts (**D4g**).

**Rejected: counting in the catalog itself, by proxying pulls through it.** That
would give exact numbers with no metrics pipeline at all — and would put the
catalog on the data path of every pull, which is the architecture SPEC §4.2
spent its budget avoiding.

**Rejected: querying ClickHouse from the browser.** See **D5** — it is the
decision that separates "the store is queryable" from "the published page
queries it", and they are not the same statement.

### D4f: what a persistent store costs, stated plainly

The previous draft cut an exporter to avoid these costs. The owner has decided
they are worth paying; that does not make them disappear, and an implementer
should meet them expecting them. The accounting below is rewritten for the
traces pipeline (**D4a**) and for the catalog living in `epos-registry`
(**D2**) — both of which move where the weight lands.

- **A large dependency graph in `epos-registry`, and *only* there.**
  `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc` at v1.44.0
  pulls gRPC, protobuf, `go.opentelemetry.io/proto/otlp`, `grpc-gateway/v2` and
  `genproto`; the metric variants measured 21 modules / ~379 packages and the
  trace ones are the same closure. **The HTTP variant does not help** —
  `otlptracehttp` still links gRPC for its status codes. Choose between them on
  firewall-friendliness, not on weight, and do not justify HTTP by claiming it is
  lighter. Task 1.6 measures the trace exporters rather than the metric ones.
- **A ClickHouse client in `epos-registry`.** `clickhouse-go/v2` is ~16 modules,
  all pure Go. It links unconditionally, because Go has no conditional imports,
  even when `catalog.stats-source` is `none` (**D4h**).
- **Nothing new in `epos`.** This is the change the move buys, and it is worth
  stating in the same list as the costs: the CLI gains no OTLP exporter, no
  ClickHouse driver, no goldmark, no embedded assets. Its module graph is
  unchanged by this change except for whatever `internal/registry` needs, which
  it already had.
- **A larger refactor than "export a function".** `internal/registry` takes over
  the remote fetch-and-unpack from `internal/skillfile` (**D2a**, **D3c**) so
  that `epos-registry` does not link `go-git`, `goawk` and `go-gitdiff`. That is
  real work on code that already passes tests, and skipping it means a registry
  binary carrying the entire Skillfile build language.
- **Three services to run for a real deployment** — registry, collector,
  ClickHouse — plus one `.sql` file to apply before the collector's first insert
  (**D4b**).
- **SPEC amendments, and there are more of them than the previous draft
  claimed.** §15 decision #2 (`/v2/` only) and §4.4 (statelessness) are both
  amended by **D2a** — the previous draft cited exactly these two as the reason
  *not* to do this, so an implementer who reads §4.4 and stops will conclude the
  change is illegal. §5.3 gains the download span and loses `client` from the
  attribute list (**D4a**, **D4c**); §3's component table gains the catalog;
  §13.4's package tree gains the new packages; §14 gains the catalog.
  **§4.5, §5.1, §5.2 and §10.3 stay untouched**, and the change says so.
- **`govulncheck` surface.** It is a required job and roughly forty new modules
  arrive at once. Expect to have to move a version.

**Rejected, and this is the one that looks cheaper than it is: writing rows to
ClickHouse directly from `epos-registry`.** It removes the collector and the
OTLP dependency graph. It also puts a **write** credential in the process on the
public internet — the thing **D4g** exists to prevent, and the thing the owner's
review names outright — puts a database client on the request path, and invents
a schema epos would then own and migrate. Not taken.

**Rejected: keeping the metrics `otlp` exporter as well as the span.** Two
durable paths for the same event is two things to keep in step and two answers
to "how many downloads", and the second one is on the alpha half of the
collector (**D4a**). The counter keeps its `stdout` exporter, which is what
godog and local development use; it does not also get a store.

**Rejected: keeping the snapshot-from-stdout mechanism as well.** The previous
draft's producer — start `epos-registry --metrics.exporter stdout`, drive pulls,
stop it, parse the last OTel JSON export the way
`tests/integration/steps_counting.go` already parses it — still works, and it is
tempting to keep as the demo's cheap path. It is not kept as a *source*, because
two mechanisms producing the same numbers is two things to keep in step; the
`file` source above is the same idea with the store as its origin. The parsing
code in `steps_counting.go` stays where it is, testing what it already tests.

---

## D5: the demo is pre-rendered during CI and published to the Pages site the repo already has

**Decision.** A CI job stands up the whole chain, generates traffic (**D15**),
and runs

```
EPOS_REGISTRY_CATALOG_STATS_DSN=<the CI store, read-only> \
epos-registry catalog export --upstream http://zot:5000 \
                             --catalog.refs demo/refs.txt \
                             --base-path /epos/catalog --out catalog-dist \
                             --catalog.stats-source clickhouse
```

writing a directory of finished HTML, published to `gh-pages` under `catalog/`
and served at `https://gaarutyunov.github.io/epos/catalog/`.

**Note which binary runs.** Since **D2** the renderer lives in `epos-registry`,
so the export job runs the registry binary in a mode that starts no listener.
That reads oddly the first time and it is the right boundary: the exported site
and the served site come from one renderer, and putting `export` on the CLI to
make the command line look tidier would put the whole frontend back into the
binary the owner asked to keep clean.

**This is what the owner's review asks for, and it is worth naming the words.**

> We are hosting on GitHub pages. To achieve this we need to render real
> frontend during CI into a static website with SSR. During CI real catalog is
> rendered from markdown into html and server.

"Static website with SSR" is not a contradiction: it means the HTML is produced
by a server-side renderer *at build time* rather than by JavaScript in the
reader's browser. `epos-registry catalog export` is exactly that renderer, and the
requirement this adds over the previous draft is that the export runs against
the **real** registry with the **real** documents, not a fixture — which the
demo delta now says in its own words.

**Why Pages.** The repository can reach exactly one deployment target today:
GitHub Pages, from `gh-pages`, already built and already `https_enforced`. It
cannot run a Go binary anywhere, publishes no container image, and names no
host. `keep_files: true` is already set on the docs deploy — for an unrelated
reason, but it means a second publisher into the same branch does not wipe the
first, which is what makes `/epos/catalog/` cheap.

**Pages currently reports `status: errored`.** `gh api repos/gaarutyunov/epos/pages`
returns `{"status":"errored", "cname":null, "build_type":"legacy", "source":{"branch":"gh-pages"}}`
even though the site serves. In branch mode the served content is whatever was
last pushed to `gh-pages`, so a failed *build* is compatible with a working
site — which is precisely why nobody has noticed. Before this change's
deployment is called done, that status has to be green or explained, because
otherwise the first real symptom of a broken publish will be indistinguishable
from the state the repository is already in. The demo delta makes this a
scenario rather than a footnote.

### D5a: ClickHouse survives as the store; it does not survive as something the published page queries

The owner asked for a persistent metrics store the catalog page can query. Both
halves are honoured, but not in the same place, and pretending otherwise would
be the dishonest version of this design.

**A page served by GitHub Pages cannot query ClickHouse, and should not.**

1. **There is nowhere to query.** The demo's ClickHouse lives inside the CI job.
   A browser on the public internet cannot reach it, and giving it something to
   reach means a hosted ClickHouse — an account, a credential and a bill, which
   is the same infrastructure decision **D5** rejected for the registry and which
   is the owner's to make, not this change's to assume.
2. **The query would carry a credential in a public document.** Pages serves
   static files; a browser-side query means the address, the user and the
   password of a queryable database in HTML anyone can read. There is no such
   thing as a read-only credential that is safe to publish here: ClickHouse's
   HTTP interface takes arbitrary SQL, and a `readonly` user can still run a
   query expensive enough to be a denial of service. This would be the change's
   worst security decision by a wide margin, and it would be one made for
   presentation.
3. **It contradicts two requirements this change already carries.** The assets
   delta requires that a page renders with every third-party host unreachable,
   and that content survives with scripting unavailable. A page whose numbers
   arrive by `fetch` fails both.

**So the query runs at export time.** The store is queried by the *build*, which
holds the credential the way builds hold credentials, and the answer is written
into the HTML with its capture time beside it. The reader gets numbers with no
request, no credential and no script.

**What this means for each mode, stated so nobody is surprised:**

| | where counts come from | do they change on refresh? |
|---|---|---|
| `epos-registry --catalog --catalog.stats-source clickhouse` | queried per request, short TTL (**D4e**) | **yes** — this is the mode the owner's e2e assertion describes, and it is tested there |
| the published Pages demo | queried once, during the export | **no** — they change when CI re-exports, which is asserted as a property rather than discovered |

**The residual gap, named.** Within one CI run the store is persistent in the
sense that matters technically — it outlives the `epos-registry` process, holds
history, and answers queries — but it does not outlive the *runner*. So the
demo's leaderboard shows one build's traffic, and the page says so. Making the
demo accumulate history across runs needs a ClickHouse that is always there, and
that is the same provisioning decision as a host for the served catalog. It is
question 2 for the owner, now sharpened: **one host running `epos-registry
--catalog` with ClickHouse behind it turns the demo from a build's snapshot into a live catalog with
real history, and nothing else in this change has to change to get there.**

Faking the accumulation — seeding the fresh store from the previously published
numbers so the counts appear to grow — is rejected on the record. It would
satisfy the demo delta's letter and violate *"every count came from a download
an epos registry actually answered"*, which is the requirement the whole
statistics design exists to protect.

**Three ways this silently destroys the docs, all of which the mechanism must
avoid.** The demo delta requires that publishing the catalog leaves the docs
served; these are how that requirement gets violated by an implementation that
looks correct:

1. **`docs/dist` is Astro's `outDir` and is gitignored.** `npm run build` clears
   it. A catalog written into `docs/dist/catalog/` before the Astro build is
   simply deleted. Hence a separate `--out` directory (`catalog-dist/`,
   gitignored) that Astro never touches.
2. **`publish_dir` without `destination_dir` deploys to the branch root.**
   `peaceiris/actions-gh-pages` with `publish_dir: catalog-dist` and no
   `destination_dir` overwrites `gh-pages`'s `index.html` with the catalog's.
   `keep_files: true` preserves files that are *absent* from the new payload; it
   does not protect a same-named file. `destination_dir: catalog` is required,
   not optional.
3. **`docs.yml` force-pushes `gh-pages` under `concurrency: {group: docs,
   cancel-in-progress: true}`.** A second workflow force-pushing the same branch
   must be serialised against it, or the two race and one loses — silently,
   because both report success.

   **But joining that group as it stands does not serialise; it cancels.** With
   `cancel-in-progress: true`, a docs push arriving while the catalog deploy is
   in flight *cancels the catalog deploy*, and the catalog silently never
   publishes. That is a different quiet failure from the race, not a fix for it.
   Serialising means the shared group carries **`cancel-in-progress: false`**,
   which is a change to `docs.yml`'s existing behaviour and has to be made
   deliberately: docs deploys stop cancelling each other and queue instead. That
   is the correct trade for a job whose last action is a force-push — a
   cancelled force-push is exactly the thing being guarded against — but it is a
   change to a workflow this change would otherwise only be adding to, so it
   belongs in the pull request description.

None of these fails loudly. All three are checked by opening the deployed docs
site after the catalog's first deploy, and that check belongs in the task list.

**What it costs, stated plainly.** The published demo's numbers are a build's
worth of traffic, resolved when the page was rendered, with the capture time and
the window on the page. They are real, they are ranked, and they do not move
until CI runs again. Live counts exist and are tested — in `serve` mode
(**D5a**) — but Pages cannot host that mode. This is a real reduction against
the issue's ask, it is smaller than the previous draft's reduction, and closing
it entirely is question 2 for the owner.

**The workflow trap.** `docs.yml` triggers on `docs/**` only. A catalog export
driven from Go source would never fire it. The workflow's paths and the export
step are both part of this change; getting this wrong produces a site that
silently never updates.

**Alternatives rejected.**

- *A container image plus a host.* This is what a live demo requires: a
  `dockers:` (or ko) target in `.goreleaser.yaml`, an image pushed to ghcr, and
  a host running zot, `epos-registry`, an OTel Collector, ClickHouse and `epos
  catalog serve`. Rejected as the default because it needs infrastructure and
  secrets the repository has never had, and it would park #44 behind an owner
  provisioning decision. Sized in tasks as a follow-on: the image target is
  roughly ten lines of goreleaser, the compose file is the same five services CI
  already stands up, and everything else in this change already works live via
  `serve`. **After this change, that follow-on is a deployment, not a
  development** — which it was not before, because before there was nothing live
  to deploy.
- *Querying ClickHouse from the reader's browser.* **D5a**.
- *Netlify/Vercel/Fly.* Same objection, plus a second account and a second
  deploy pipeline for a project whose entire publish story is one Pages branch.
- *A separate `epos-catalog` Pages site under its own repository.* Splits the
  project across two repos to avoid one path prefix.
- *Faking the numbers.* Considered and named here only so the rejection is on
  the record: seeded or illustrative counts on a page headed "downloads" is the
  one outcome worse than no counts.

---

## D6: ui-kit — vendor the release bundle, and this needs v0.4.0

**Decision.** Commit
`internal/catalog/assets/vendor/ui-kit/{ga-ui-kit.min.js, ga-ui-kit.css, VERSION, LICENSE}`
and `//go:embed` the assets tree. Refresh with a small script that downloads the
release assets and rewrites the files; never at build time.

**Which binary carries them is the owner's question from D2, and the answer is
`epos-registry` alone.** `internal/catalog` is the only package with a
`//go:embed`, and it is imported by `cmd/epos-registry` and by nothing on the
CLI's side of the graph. *"People downloading CLI don't need ui artifacts"* is
therefore a property a test can hold: the assets delta requires an assertion
that no package reachable from `cmd/epos` imports `internal/catalog`, so a
future import that quietly puts 104 KB of JavaScript back into the CLI fails the
build rather than the review.

**The kit's distribution, measured.** `@gaarutyunov/ui-kit` publishes to
`npm.pkg.github.com` only — not to public npm (`unpkg` and `esm.sh` both 404 for
it, which incidentally means the kit's own docs "From a CDN (buildless)" snippet
has never worked). The npm package ships raw `src/`, no bundle. But the
**release** attaches three built files, and they are anonymously downloadable
with no token:

```
releases/download/<tag>/ga-ui-kit.min.js   ~97 KB  IIFE, registers every <ga-*>, window.GaUIKit
releases/download/<tag>/ga-ui-kit.esm.js           the same, as ESM
releases/download/<tag>/ga-ui-kit.css      ~7 KB   the tokens
```

The bundle contains no `fetch`, no dynamic `import`, no `@font-face` and no
`@import` — two files, 104 KB, and the page is complete offline.

| option | works in CI | offline `go build` from a fresh clone | needs a secret |
|---|---|---|---|
| `npm install` + build, vendor `dist/` | yes, with `.npmrc` + a PAT — and the package ships no bundle, so an esbuild step is still needed | no | **yes** |
| **commit the release bundle** | **yes, nothing to do** | **yes** | **no** |
| download the release asset at build time | yes | no | no |
| CDN `<script>` | yes | no, and the binary is not self-contained | no |

Committing wins on the axis that matters: `//go:embed` exists so that `go build`
from a fresh clone produces a complete binary, and any build-time fetch quietly
takes that away. It is also how the repository already consumes the kit
(`docs/vendor/ui-kit/`), so this is a variation on an existing convention rather
than a new one.

**Why the bundle rather than raw `src/` like the docs site.** The docs site is
built by Astro, which resolves 41 ES modules for it. A Go binary serving files
out of `embed.FS` would have to serve the whole module graph with correct MIME
types and let the browser resolve relative imports — workable, but 40-odd files
to vendor and one import path away from a 404 at runtime. One `<script>` tag is
the whole integration.

### D6a: v0.3.0 is one component short, and it is the same release bikelanes#4 is parked on

`ga-ui-kit` v0.3.0 (2026-07-27) carries 29 components. Twelve more landed on
`main` afterwards and are in no release. Against this change's page list:

| need | component | v0.3.0? |
|---|---|---|
| leaderboard table | `ga-table` — its own docstring uses a `#`/`Skill`/`Score` leaderboard as the worked example, with whole-row `<a href>` | ✅ |
| badge / chip, card, header, breadcrumbs, tabs, input, select, code, button, avatar | `ga-badge` `ga-card` `ga-header` `ga-breadcrumbs` `ga-tabs` `ga-input` `ga-select` `ga-code` `ga-button` `ga-avatar` | ✅ |
| **pulls stat tile** | **`ga-metric`** (+ `ga-quantity`) | ❌ **main only** |
| footer, prose container, theme toggle, logo grid | none of these are components, by the kit's own design rule | n/a — hand-rolled off tokens, as the kit's own docs site does |

So **one** component is missing, and it is the one the issue's headline feature
needs: the number on the leaderboard and on every skill page.

**gaarutyunov/bikelanes#4 is parked on precisely this question** — open,
labelled `needs:input`, its blocking component work (ui-kit#7) already merged,
waiting only on *"cut ui-kit v0.4.0, or hold the release?"*. It is the same
decision. The owner should get it once.

**Recommendation: cut ui-kit v0.4.0 and pin it here.** One release unblocks both
issues. Note for whoever cuts it: v0.4.0 contains a silent breaking change —
`ga-chat-message`'s `role` attribute was renamed to `from` — which affects
neither epos nor, as far as this change knows, bikelanes, but makes the version
bump a minor rather than a patch.

**Fallback if the release is held.** epos ships against v0.3.0 with a
hand-rolled stat tile: a `<div>` with a label and a mono number, styled from
`--ga-*` tokens, in `app.css`. It is perhaps fifteen lines and it is exactly the
duplication the kit exists to prevent, so it is a fallback and not a plan. The
delta spec is written so that either satisfies it.

**Rejected: depending on `github:gaarutyunov/ui-kit#main`.** Pins to a moving
branch; the same objection raised on bikelanes#4.

**Also rejected: raising `docs/vendor/ui-kit` from v0.2.0 to the same release in
this change.** Two vendored copies of the kit at two versions in one repository
is a genuine wart and it should be fixed — but the docs site is #42's surface,
#42 is in review against v0.2.0, and moving the docs site's kit version
underneath it would invalidate a spec the owner is reading. Recorded as a
follow-up rather than done here.

---

## D7: `SKILL.md` is untrusted input

**Decision.** Render Markdown to HTML **in Go, at render time**, with raw HTML
and raw-HTML-block passthrough disabled, and sanitise the result before it
reaches a template. No client-side Markdown library.

**Why this is the change's security boundary.** Everything else the catalog
renders is a short string from a manifest annotation. `SKILL.md` is an
arbitrary document, fetched from a registry, authored by whoever pushed the
artifact, and rendered into the catalog's own origin. On a shared demo host that
is stored XSS with a supply chain attached. Goldmark's `WithUnsafe` is off by
default; the requirement is that it *stays* off, that the choice is asserted by
a test with a hostile fixture, and that link and image URLs are constrained to
schemes that cannot execute (`http`, `https`, `mailto`, plus relative).

Two subtleties the implementation must not miss, both of which survive
"disable raw HTML":

- A Markdown link with a `javascript:` target is not raw HTML; goldmark will
  render it as an `<a href>`. It must be rejected or defanged.
- Relative links inside `SKILL.md` point at files inside the artifact, not at
  catalog routes. They must resolve to something meaningful or to nothing —
  never to an arbitrary catalog path.

**Why not client-side.** Shipping a Markdown parser to the browser costs more
JavaScript than the entire rest of the page, moves the sanitisation decision to
where it is hardest to test, and makes the static export depend on JS to show
its main content.

### D7a: the Go libraries for rendering markdown to a static site, researched

The owner's review asks for this explicitly — *"Research Go based libraries for
this"* — so the shortlist and the verdicts are recorded rather than assumed.

**Markdown → HTML: `github.com/yuin/goldmark`, v1.8.5.** Pure Go and — the fact
that decides it — **zero dependencies**: its whole build closure is one module.
It is the CommonMark-compliant implementation the Go ecosystem standardises on;
both Hugo and Gitea use it, which is as close to a de facto answer as this
question has. GFM tables, which `SKILL.md` documents use freely, come from
`extension.Table` (or `extension.GFM` for tables plus strikethrough, linkify and
task lists). Raw HTML passthrough is off unless `html.WithUnsafe()` is passed,
which is the property **D7** rests on.

- *Not `github.com/yuin/goldmark/v2`*: v2 is at beta as of this writing. Ship on
  v1.
- *Not `russross/blackfriday/v2`*: last pushed January 2024, not CommonMark
  compliant. It appears in `go.sum` today as a `/go.mod`-only line from cobra's
  module graph — it is not built and is not a dependency.
- *Not `gomarkdown/markdown`*: active, but a blackfriday fork with no tagged
  releases; adopting it means pseudo-versions in `go.mod`.

**Frontmatter: no new module.** goldmark has no official frontmatter extension
and does not need one here — `artifact.ParseFrontmatter` already finds the
extent of a `SKILL.md`'s frontmatter, and the body starts after it. A third-party
frontmatter extension would be a dependency to duplicate code the repository has.

**Templating: `html/template`, from the standard library.** Contextual
autoescaping is the property that matters, and it is why the boundary in **D7**
is placed on the way *in* rather than in the templates.

**Not a static-site generator.** The question "is there a Go library for
building a static site" has a real answer and it is *no*. Hugo is importable —
`github.com/gohugoio/hugo/hugolib` builds, with no cgo on that import path — and
it costs **88 modules and 699 packages**, against a `go.mod` carrying esbuild,
the AWS SDK, gRPC and Dart Sass bindings, with a v0 public surface that has no
stability guarantee and ships breaking changes on a weekly cadence. Inheriting
Hugo's dependency graph and release cadence to obtain "Markdown plus templates
plus a directory walk" is not a trade. Everything else in the Go SSG field is a
CLI, not a library. `html/template` + goldmark **is** the answer, and it is
already what **D2** specifies.

**Syntax highlighting: deliberately not in this change.**
`alecthomas/chroma/v2` (pure Go) via `yuin/goldmark-highlighting/v2` is the
standard pairing and would render fenced code as coloured spans at build time —
which is the right shape, because the alternative is shipping a highlighter to
the browser and blowing the JavaScript budget. It is not taken now for two
reasons: chroma embeds every lexer and style, adding single-digit megabytes to
a binary that also carries the ui-kit bundle; and `goldmark-highlighting/v2` has
**never cut a semver tag** — its latest is a 2023 pseudo-version — so adopting
it means a pseudo-version in `go.mod` for a presentational improvement. Fenced
code renders as `<pre><code>`, styled from the kit's tokens. Recorded as a
follow-up with both facts attached, so the decision is re-openable rather than
forgotten.

**Sanitisation: `microcosm-cc/bluemonday` is named but not adopted.** With
`WithUnsafe` off, goldmark emits a closed element set and the residual vectors
are link, image and autolink targets, which the AST transformer handles. If an
implementation concludes an output-side pass is needed anyway, bluemonday is the
established library to reach for — with the caveat that it has had no release
since July 2024, which for a security-relevant dependency is a fact to weigh
rather than ignore.

**The docs site is untouched.** Astro still builds `docs/`. This change renders
the *catalog* in Go; it does not port the documentation site, and reading the
owner's comment as a mandate to do so would be inventing scope.

**Sanitisation: a scheme allow-list, not a hand-rolled HTML sanitiser.** With
`WithUnsafe` off, goldmark emits a closed set of elements and the residual
vectors are link, image and autolink targets — which an allow-list of `http`,
`https`, `mailto` and relative handles completely, as an AST transformer, before
any HTML exists. A hand-written HTML sanitiser is explicitly ruled out: writing
one is how this goes wrong, and it would be sanitising output that is already
element-constrained. If the implementation concludes an output-side sanitiser is
needed anyway, it uses an established library and says in the pull request what
the transformer could not reach.

**Where the boundary is enforced.** In the renderer, once, on the way in — not
in a template, where `html/template`'s contextual escaping would have to be
defeated with `template.HTML` at every call site and one forgotten `template.HTML`
is the bug.

**Frontmatter.** `SKILL.md` opens with YAML frontmatter that
`artifact.ParseFrontmatter` already reads. The rendered body must begin after
it — a page that opens with a wall of `---name: …` is the tell that this was
missed.

**The document needs its own size cap, and the layer cap is not it.**
`skillfile`'s 64 MiB bound (**D3c**) is on the *layer*; nothing bounds the
`SKILL.md` inside it. A 60 MiB document is a legal artifact, and parsing and
rendering it on every request is a cheap denial of service against `serve` —
cheap because the attacker publishes once and the catalog does the work
repeatedly. Cap the document at a size a document plausibly has (a small number
of megabytes), and treat an oversized one exactly as **D3d** treats an
unreadable layer: the skill still lists, its page says the document could not be
rendered, and nothing else is affected. The cache (**D2**, keyed on digest) is
mitigation, not a fix — it is bounded, so a set of oversized documents evicts
each other.

**Heading anchors are not specified and are deliberately out of scope.** Not
generating them means a rendered document's headings are not linkable, which is
a real but minor loss; generating them means deciding a slug algorithm and
guaranteeing uniqueness within a publisher-authored document. Skipped, and named
here so the omission is a decision.

---

## D8: "same letters Epos", and the two references agreeing

**The reading.** The issue says *"It must look like the skills.sh and
gaarutyunov.com website"* and immediately after, *"We need to use same letters
Epos For the skills."* skills.sh's home page opens with a large ASCII-art
`SKILLS` banner in `<pre>`, Fira Mono, `text-[15px]`, `tracking-[-1px]`.
garutyunov.com opens with an ASCII box-drawing wordmark in `<pre>`, Fira Mono,
`tracking-[-1px]`, `select-none`, with an `sr-only` `h1` beside it. "Same
letters Epos" is the request to render **EPOS** that way. epos#42's design
**D2** already specifies exactly this asset for the landing.

**Decision.** There is **one** `EPOS` wordmark in the repository, as a
checked-in text asset, consumed by both the Astro landing and the Go templates.
Whichever of #42 and #44 lands second adopts the other's file rather than
copying it. If #44 lands first, the asset is created here at a path #42 can
consume; if #42 lands first, this change consumes it as-is.

**The two references do not conflict, which is what makes this cheap.** The
research for #42 measured garutyunov.com's inner pages; the research here
measured skills.sh. They land on the same shell:

| | garutyunov.com (per #42 **D3**) | skills.sh (measured) |
|---|---|---|
| container | `max-w-6xl` = 1152px, `px-4 sm:px-6 lg:px-8` | `max-w-6xl`, `px-4 sm:px-6 lg:px-8` — identical, every page |
| detail layout | 12-col grid, `col-span-9` body + `col-span-3` aside | `grid-cols-12`, 9 / 3, `gap-16` |
| section labels | 14px mono, UPPERCASE, foreground, no rule | mono uppercase `text-sm`, gray, with a bottom rule |
| numbers / identifiers | `font-mono`, `text-xs`, uppercase | mono everywhere: counts, `owner/repo`, column headers, tabs |
| theme | hard-coded dark, `#000` | hard-coded dark, `--ds-background-100: #000`, no toggle |
| accent | `#54a2ff`, hover only | essentially monochrome; colour only as status |
| density | — | 56px table rows, hairline `border-b`, no card shadows in lists |

So this change reuses #42's shell wholesale and takes from skills.sh only what
#42 had no occasion to specify: the leaderboard row (rank, name over
`owner/repo`, right-aligned mono count), the tab row expressing sort as
navigation rather than a dropdown, the detail page's aside stack, and the
copyable install command as a full-width `bg-muted` button.

**What is deliberately not copied from skills.sh**: the 8-week sparkline,
security-audit columns, topics, the agent marquee animation, editorial picks,
and the `/api/v1` JSON surface. The sparkline is the interesting omission: the
store **does** keep history (**D4a**), so the data for one now exists, but
`Stats` returns a set of totals and `ga-chart-frame` draws no data by design.
Adding a time series means widening the interface and finding a chart — a
follow-up with a real basis, rather than the impossibility it was in the
previous draft.

**A note on theme.** Both references are dark-only. The kit supports light via
`<html data-theme="light">` and ships no toggle component. The catalog is
dark-only, matching both references; the tokens make light a later
one-attribute change if it is ever wanted.

---

## D9: the tools page is a capability table wearing logos

**Decision.** The tools page has two sections — **Registries** and **Agents** —
and every registry entry carries a verified capability status, from a
checked-in table, covering at least *pull*, *push* and *`_catalog` discovery*.

**Why the issue as written cannot ship.** *"the logos of registries that support
OCI like zot and gitlab"* — a logo on an epos page is a compatibility claim.
epos needs three different things from a registry and they are not the same
thing:

1. **pull** — every OCI 1.1 registry.
2. **push** — every registry that accepts the agent-skills artifact type; some
   registries reject unknown `artifactType` or non-image manifests.
3. **`_catalog` discovery** — optional in the distribution spec, and this is
   where the list thins out. `errNoCatalog` and its 403/404/405/501 mapping
   exist in `internal/cli/discover.go` *because this is common*, and SPEC §4.1
   states outright that it "is disabled on several hosted registries". `epos
   list` and `epos search` do not work against a registry without it, and
   neither does the catalog's namespace mode (**D3**).

Note that (2) is now a claim epos can make for itself: since epos#43,
publishing is `epos push`, so "push works here" is a statement about the
project's own command rather than about whichever OCI client the reader
happens to have.

zot is the one registry the repository actually exercises — CI runs
`ghcr.io/project-zot/zot-linux-amd64:v2.1.18` and five integration files drive
it through testcontainers. Everything else on the page would be an untested
claim unless it says so. The requirement is therefore that each row states what
was verified and how, with three honest values: *verified in CI*, *verified
manually* (with a date), and *conformant, untested*. A row nobody has checked
says so.

**Trademarks.** The logos are third-party marks and are redistributed inside a
binary. Each one needs a source and a permission check before it is committed,
and referential use (naming a product to say what works with it) is the ground
that has to hold. Any logo whose terms do not permit it becomes a text row —
which the table shape makes a non-event. Logos are embedded as SVG, never
hotlinked.

**Agents.** skills.sh's `/agent` page lists 20 clients with 40×40 SVG logos and
a one-line positioning blurb each. epos cannot derive an equivalent list from
its own code, and the first draft of this design said it could — wrongly.
`epos install` knows exactly **one** agent directory,
`install.DefaultBasePath = ".claude/skills"` (`internal/install/manifest.go`);
every other destination comes from the *user's* `skills.json`
`additionalBasePaths`. Deriving the list from the code yields a one-row table.

**Decision.** The agents section is a checked-in table with the same discipline
as the registries one, and each row states **the skill directory that agent
reads** and whether epos installs there by default or only through
`additionalBasePaths`. That is a fact about each agent that a reader can act on —
it is the value they would put in `skills.json` — and it is verifiable, which a
positioning blurb is not. The row for the default is marked as such.

This also stops the section from becoming a list of tools epos has a
relationship with. It has a relationship with directories.

---

## D10: publishing the example — `epos push`, no gate

**Resolved.** epos#43 merged (`6f7738a`, PR gaarutyunov/epos#48). `epos push
<name>:<version> <destination>` and `epos registry login` / `logout` are on
`origin/main`. The question this section originally answered — whether #44
should wait for them — no longer exists, and the answer it reached (no) is now
moot rather than merely correct.

**Decision.** The demo publishes with the CLI itself:

```
epos registry login ghcr.io -u <actor> --password-stdin
epos pack examples/go-house
epos push go-house:<version> oci://ghcr.io/gaarutyunov/skills
```

No `oras`, no `docker`, nothing outside the binary the repository builds. That
is exactly what the issue asked for — *"we should pack my go skill as an example
skill and push to registry so we would also use epos to pack our own skill"* —
and it is now literally true rather than true of `pack` and delegated for the
rest.

**Which registry.** `ghcr.io/gaarutyunov/skills/`. It is free, the org already
pulls from it in CI, and a workflow's `GITHUB_TOKEN` can push packages it owns —
so publishing needs no new secret, only `permissions: packages: write` on the
job. The consequence is **D3**: ghcr is one of the registries where a `_catalog`
sweep cannot be relied on, so the demo runs in `--refs` mode. That is not a
workaround; it is the reason `--refs` is specified.

**One thing to get right in the workflow: there are two credential failures, not
one, and they read differently** (`registryOptions.explainAuth`,
`internal/cli/credentials.go`):

- **No credential at all** fails inside `oras-go` as
  `auth.ErrBasicCredentialNotFound`. It never reaches the registry, so there is
  no HTTP status to read. Message: *"no credential is stored for it"*.
- **A wrong or expired credential** returns a real **401**. Message: *"the
  stored credential was rejected"*.

Both end at `epos registry login <host>`. A publish job that treats them as one
condition will report a missing `packages: write` permission — a 401 — as a
missing login, and send whoever is debugging it to re-run a login that already
worked. Neither message contains the credential.

**Not a concern here, but worth not misreading:** SPEC §4.5's withdrawal is of
the `epos-registry` **relay** write path, not of publishing. §4.5 now says so
directly — *"What is withdrawn is routing a publish through `epos-registry` —
not publishing"* — and §1.1 lists only *"a write server that packs, validates,
or holds credentials"* as out of scope. The demo publishes straight to the
upstream registry it addressed, which is the case the advisory behind §4.5 was
never about.

**Rejected: publishing to a zot instance stood up for the demo.** Needs a host
(**D5**) and makes the demo's artifacts disappear when it goes away.

---

## D11: what the catalog shows about parametrisation

**This section is a reversal.** The previous draft found that the artifact does
not declare its parameters — `epos build` writes `dev.epos.skillfile.digest`,
`org.opencontainers.image.base.name`, `.base.digest` and
`dev.epos.skillfile.stages` (`provenanceFor`, `internal/cli/build.go`), and the
config blob carries the `SKILL.md` frontmatter, but **nothing records which
`{{ .Values.x }}` a skill accepts, what type it is, or what it defaults to** —
and concluded that specifying one here would be a builder feature smuggled in
through a UI issue. The owner's review overrules that:

> This must be implemented. Let's add kubernetes CRD like schema to skill values
> with OpenAPI v3 schema. […] We should offer a command that would infer the
> schema from templates.

The finding stands; the conclusion does not. **D14** specifies the schema and
the inference command, and argues where the work should be delivered. This
section now covers only what the *catalog* does with it.

**Decision.** The detail page shows the declared parameter contract when the
artifact carries one, and shows no parameter section at all when it does not.
Both branches are specified, because #44 has to be shippable whether or not the
schema lands with it (**D14**).

**With a schema**, the page renders a table of parameters — path, type, required,
default, description — read from the schema the manifest already carries
(**D14b**), so the list pages still cost one manifest `GET` and nothing more.
The schema's strings are publisher-authored and are escaped as the untrusted
input they are, and an oversized or malformed schema fails that page's parameter
section and nothing else, the same rule **D3d** applies to a bad content layer.

**Without a schema**, the page shows what the artifact does carry, which remains
worth showing on its own account:

- **`dev.epos.skillfile.stages` is a file→stage map.** It says, per file in the
  installed tree, which Skillfile stage produced it. Rendered as a grouped table,
  it *is* the picture the issue asks for: `references/cli.md` from the `cli`
  stage, `references/generics.md` from `pro`, the testcontainers example from
  `containers`, everything else from the base. "Build with references from spf13
  and golang-pro, dropping what we don't use" becomes a table of real annotation
  data rather than a claim in prose.
- **The base and Skillfile digests** identify the recipe and pin the base.
- **The parameters are documented in `SKILL.md`**, which #42's task 2.6 already
  requires the derived skill's entry document to do, and which the detail page
  renders in full.

The provenance table is not replaced by the parameter table. They answer
different questions — *what went into this* and *what can I set* — and the
detail page shows both when both exist.

---

## D12: `--out`, path containment, and context

**`--out` semantics.** `export` creates the directory if it does not exist,
writes into it, and **refuses a directory it did not create unless it holds a
marker file the previous export left**. It never recursively deletes a
directory a human named on a command line. When the marker is present it prunes
files the current export did not write, so a skill dropped from `--refs` does
not leave an orphan page served forever — which is a requirement the demo's
"reproducible" scenario does not otherwise cover, because reproducibility says
nothing about deletion.

**Path containment.** Route paths are built from repository names and tags that
come from a **registry**, so `export` writes files at paths an artifact
publisher influences. Every path is resolved and checked to stay under `--out`
before anything is written. This is the same class of defect
`skillfile.checkPath` exists to refuse (**D3c**) — one level up, on the way out
instead of the way in — and `serve` needs the mirror of it, which is **D3b**.

**Context.** Everything that touches a registry or a file takes a
`context.Context` and threads it: `Stats.Pulls(ctx)`, every registry fetch, and
both drivers. `serve` gives each request-scoped layer fetch its own timeout, so
one slow registry cannot pin handlers; `export` runs under one deadline for the
whole walk. Neither is a detail an implementation can add later without
changing every signature.

---

## D13: testing

Constrained by SPEC §13: unit tests beside the code with no Docker and no
network; integration tests under `tests/integration/` behind `//go:build
integration`, driven by godog against `features/*.feature` at the repository
root, with **real registries** — §13.2, *"No fakes, no in-memory registry
substitutes, no mocked HTTP."*

- **Unit, no network**: the renderer against a fixed in-memory model (every page,
  both drivers, byte-identical output for one base path, and correct prefixing
  for another); the Markdown pipeline against a hostile corpus (raw `<script>`,
  `javascript:` and `data:text/html` targets, `<img onerror>`, an SVG with a
  handler, frontmatter passthrough) *and* an expressive corpus, since a
  sanitiser that eats the content is the same bug with a different symptom;
  counts-file parsing including a malformed file and a repository with no row;
  `--refs` parsing; the export path-containment check against a hostile
  repository name; the values-schema inference walker over template fixtures,
  including the `with`-rebinding and conflict cases (**D14c**).
- **Integration, real containers**: a zot registry (`ghcr.io/project-zot/zot-linux-amd64:v2.1.18`,
  the pinned image already in `tests/integration/registry_read_path_test.go`)
  with skills packed and pushed into it, `epos-registry --catalog
  --traces.exporter otlp` in front of it, a collector and a ClickHouse (there is
  an official `testcontainers-go/modules/clickhouse`, v0.43.0, matching the
  testcontainers-go the module already has) with the DDL applied **before** the
  collector starts, `epos pull` driving the counter, and the rendered page
  asserted to carry the count the rollup returns. One process serves both the
  pull and the page, which is what makes this a test of the deployed shape
  rather than of two things wired together for the test. This
  is the test that proves the whole chain, and the chain is the deliverable.
  The collector's **traces** support is beta rather than the alpha its metrics
  support is (**D4a**), which is one reason the span is the durable record; if it
  still proves unusable, that is a finding for the owner about ClickHouse, not a
  licence to fall back to a hand-written store.
- **A hostile artifact**, pushed to the real registry: an oversized layer and a
  layer with a `..` entry. The catalog must still list it, its page must say the
  document could not be read, and no file may appear outside `--out` (**D3c**,
  **D3d**, **D12**).
- **A refs-mode export against a registry with `_catalog` disabled**, so the
  ghcr case (**D3**, **D10**) is covered by a test and not by hope.
- **Two boundary assertions the move makes necessary**: that no package
  reachable from `cmd/epos` imports `internal/catalog`, and that
  `cmd/epos-registry` imports neither `internal/cli` nor `internal/skillfile`
  (**D2a**). Both are `go list -deps` and a comparison; both are the difference
  between a decision and a preference.
- **A new `features/` file**, since the features are canonical and never
  paraphrased into Go.
- **End-to-end, in a browser**: **D16**. It is a third tier, not a variation on
  the integration tier, because it needs a browser and the integration tier is
  required to run everywhere the unit tier does.
- **The docsgen drift gate** must be green after the generator gains the Epos
  skill's reference pages and `epos-registry`'s command tree (**D17**).

---

## D14: the values schema — what it is, and where it should be delivered

The owner's review asks for two things: an OpenAPI v3 values schema that defines
the contract and validates values, and a command that infers that schema from a
skill's templates. Both are specified, in the `epos-values-schema` delta. This
section is the reasoning.

### D14a: what "kubernetes CRD like schema … with OpenAPI v3 schema" should mean here

**Decision.** A skill may carry a `values.schema.json` — an **OpenAPI 3.1 Schema
Object**, which is a JSON Schema 2020-12 document — describing the values it
accepts. What is adopted from Kubernetes is the *structural schema* discipline,
not the CRD envelope.

The CRD comparison is apt for a precise reason. What makes
`spec.versions[].schema.openAPIV3Schema` useful in Kubernetes is not that it is
OpenAPI; it is that it must be **structural**: every field has a declared type,
the root is an object, and composition keywords cannot leave a path's type
ambiguous. That is what makes validation, defaulting and pruning have one answer
per path instead of an answer per matching branch. A values schema wants exactly
that property, so the requirement is written as *structural*, and the delta says
so.

What is **not** adopted: `apiVersion`/`kind`, `spec.versions[]`, storage
versions, conversion webhooks, subresources. A skill has one values contract, not
N versioned ones with conversion between them. Carrying the envelope would be
imitation.

**Why OpenAPI 3.1 rather than 3.0.** A 3.1 Schema Object *is* a JSON Schema
2020-12 document — 3.1 defines a dialect using every 2020-12 vocabulary except
Format Assertion, plus a handful of OpenAPI-only keywords a generic validator
ignores. So "OpenAPI v3 schema", as asked for, and "a schema any JSON Schema
validator can check", which is what makes it cheap, are the same document. 3.0's
schema object is a *divergent* subset and would force an OpenAPI-specific
validator.

**Validation library: `github.com/santhosh-tekuri/jsonschema/v6`.** Pure Go, two
modules, ~93 packages, supports drafts 4 through 2020-12 and defaults to 2020-12
when a document omits `$schema`. Rejected: `getkin/kin-openapi` (~210 packages,
a whole OpenAPI document model this does not need, and a v0 with breaking
releases weeks apart) and `pb33f/libopenapi` (~227 packages; its strength is an
order-preserving document model for linting, and schema validation is a separate
module again). Both, notably, delegate to `santhosh-tekuri/jsonschema` anyway.
One gotcha to record: that library validates plain JSON values —
`map[string]any`, `[]any`, `string`, `bool`, `float64`/`json.Number`, `nil` — so
YAML-derived or Go-typed values must be normalised through JSON first. Helm
wraps the same call in a `recover()` for exactly this reason; normalising is the
better answer.

**Helm, since the owner raised it.** *"In that matter helm is awful"* is a fair
reading of the ergonomics but the mechanism is worth being accurate about, since
the delta borrows from it. Helm **does** support `values.schema.json` at the
chart root and validates merged values against it, recursing into subcharts —
and current Helm (v3.21/v4.2) validates with `santhosh-tekuri/jsonschema/v6`,
so the widely repeated "Helm is draft-07 only" is out of date. What Helm does
**not** do — verified, and this is the actual gap — is **infer** the schema.
Nothing in Helm or its plugin ecosystem derives a schema from `.Values.*` usage
in template bodies; the community generators (`dadav/helm-schema`,
`losisin/helm-values-schema-json`) work from `values.yaml` plus comment
annotations. So the inference command the owner asks for is genuinely new, and
it is the part that makes the schema pleasant instead of a chore.

**Scoping mirrors the renderer, and this is not optional.**
`install.Values.Scope(stage)` gives the skill's own values at the top level, a
stage's values under that stage's name, and the shared `global` block to every
stage. A schema that did not mirror that would validate a document nobody
renders. So the composed schema has a property per contributing stage and a
`global` property — which is, structurally, exactly how Helm nests a subchart's
schema under the subchart's name.

### D14b: the schema is carried where a manifest read can reach it — as an annotation, not in the config blob

**Decision.** The schema lives in the content layer at the skill root, and a
copy is carried on the manifest as the annotation
**`dev.epos.values.schema`**. The catalog reads it from the same manifest `GET`
it already makes, and fetches no content layer to render a parameter table —
the economy **D3** spends the whole list page on.

**The config blob is the wrong home, and this is a correction.** An earlier
draft of this section put the copy in the config blob because that blob is
already inlined in its descriptor's `data` field and
`internal/artifact/build.go`'s comment names *"a discovery UI"* as the reason.
But SPEC §2.1 states as an invariant that **the config blob mirrors `SKILL.md`
frontmatter**, and `artifact.assemble` derives it from `ParseFrontmatter` and
nothing else; §2.2 requires that epos extensions *"must never alter the skill
artifact"*. Putting an epos-specific key in the config blob would make epos emit
a config no conforming producer emits, and would need §2.1 amended — for no gain
over the mechanism the repository already has.

**That mechanism is `dev.epos.*` manifest annotations**, which is exactly what
§2.3 is for and exactly how `dev.epos.skillfile.stages` already carries a JSON
document a client reads without fetching a layer. The values schema is the same
kind of thing, so it goes in the same place, and §2.1 stays untouched.

Annotations are strings and are not a place for arbitrary size. So: above a
stated cap (task 1.11 measures it), the annotation is omitted and a small marker
annotation records that a schema exists in the layer. That keeps *"no schema"*
and *"a schema too large to annotate"* distinct, which matters because the
catalog renders nothing for the first and should not silently render nothing for
the second.

The annotation is written from the layer at pack time, so the two copies cannot
be authored separately and cannot disagree.

**Alternative, if the cap proves too tight: a frontmatter key.** `SKILL.md`
frontmatter is mirrored into the config blob for free, so a `values-schema` key
there would reach the catalog in one GET without touching §2.1 at all. It is not
the default because it puts a schema document inside a YAML front block, which
is unpleasant to author and to diff. Recorded so the fallback is a decision
rather than an improvisation.

### D14c: inferring the schema from templates — the rules, and their honest limit

The owner gave the rules: *"Strings by default and Boolean if used in
conditional operators, I.e. if. Or numeric values if compared to numbers."* They
are implementable exactly as stated by walking the template parse tree.

**What the command reads, which is the first thing to pin down.**
`epos values schema <path-or-ref>` takes **one positional argument, and it is
always local**:

| input | stages? |
|---|---|
| a skill directory — what `epos pack` takes | **no stage scoping.** A directory has no stages; the emitted schema has the skill's own properties and `global`, and nothing else. |
| a reference into the local store — a skill `epos build` or `epos pull` already produced | **stage scoping**, read from that artifact's `dev.epos.skillfile.stages` annotation, which is a file→stage map and therefore says which stage contributed the template each reference was found in. |

**No registry access, and now that claim is true rather than aspirational.** An
earlier draft said the command needs no registry *and* preserves stage scoping,
which cannot both hold for a Skillfile input: stage attribution for a recipe
means resolving its `FROM`, and a `FROM` naming an OCI or git source **is**
registry access. Resolving that by taking a Skillfile and pulling its bases
would make an inference command a network command. So the command does not take
a Skillfile. It takes a directory or something already in the store, stage
attribution comes from the annotation on a built artifact rather than from
re-deriving the build, and the "no registry" property is a consequence of the
input rather than a promise laid over it.

**Mechanism.** `text/template/parse` — parse, never execute. `template.Template`
exposes `.Tree`, and `parse.Parse` will produce trees standalone. epos makes
this markedly easier than it is for Helm: SPEC §10.3 gives `text/template` **no
custom functions**, so there is no Sprig-sized function map to stub out. Walk
from `Root`, collect `*parse.FieldNode` whose `Ident[0] == "Values"`, and carry a
stack of the enclosing `*parse.IfNode` / `*parse.RangeNode` / `*parse.WithNode`.

| usage | inferred type |
|---|---|
| substitution only | `string` (the default) |
| the pipeline of `if` / `else if` / `with`, or an argument to `not` / `and` / `or` within one | `boolean` |
| an operand of `eq` / `ne` / `lt` / `le` / `gt` / `ge` whose other operand is a `*parse.NumberNode` | `integer` if the literal is integral, else `number` |
| the subject of `range` | `array` |
| referenced only through sub-fields | `object` with those properties |

**Two things the walker must get right**, both of which are how this goes wrong
quietly:

- **`with` and `range` rebind dot.** Inside `{{ with .Values.image }}`, a `.tag`
  is `.Values.image.tag`. Without scope tracking, half the paths in a real skill
  are wrong.
- **`*parse.ChainNode`** carries fields hung off a parenthesised expression and
  is the node people forget.

There is **no traversal utility in the standard library** — the open proposal
golang/go#56404 exists precisely because there isn't — and no maintained Go
library that already extracts `.Values` references from template trees. This is
a walker to write, and it is perhaps two hundred lines.

**The limit, stated because the command must state it.** `{{ if .Values.x }}` is
exactly as true for a non-empty string as for `true`. Go template truthiness
makes the boolean rule a **useful heuristic, not a proof**, and a skill that
genuinely gates on a non-empty name will be typed `boolean` and be wrong. So the
command emits a **draft to be reviewed and committed**, says so in its output,
refuses to overwrite an existing schema without being told to, and can instead
report how the inferred schema differs from the committed one. Contradictory
usage — one path used as a condition *and* compared to a number — is reported
with both source positions, not resolved by precedence. A command that silently
picks is a command whose output nobody checks.

**Command shape.** `epos values schema <path-or-ref>`, a `values` parent with a
`schema` subcommand, following `epos registry login`'s existing two-level
precedent rather than inventing a third naming style. `cobra.ExactArgs(1)` — the
input is required and there is no useful default, and validating the count with
a `cobra.Args` validator keeps it out of `RunE`. Flags kebab-case, `RunE`, output
through `cmd.OutOrStdout()` — **D2a**'s rules, which apply to every command this
change adds.

### D14e: typed `--set` is a behaviour change, and it needs saying so

This is the part of **D14** that can break a working install, so it gets its own
section rather than a clause.

`applySet` (`internal/install/values.go`) stores every value as a string, and
its doc comment records that as a **decision with a reason**:

> Values stay strings. Helm infers types here; this does not, because 10.3 gives
> `text/template` no custom functions and a template that cannot convert is
> better served by a value that is what the user typed than by one silently
> promoted to a float.

That reasoning is sound for a world with no schema. It is what epos#47 exists to
overturn, because its consequence — `--set openapi=false` being a truthy
non-empty string, silently enabling the thing the user just disabled — is worse
than the problem it avoids. But overturning it changes what existing commands
do, and the change is not confined to booleans:

- `--set version=1.0` becomes a number, and a template rendering it emits `1`,
  not `1.0`. This is precisely the "silently promoted to a float" case the
  comment names, and it is a real regression for anyone setting a version, a
  semver range or a zero-padded identifier.
- `--set x=null` becomes nil rather than the string `"null"`.
- Every assertion in `internal/install/values_test.go` that expects a string
  changes.

**Decision.** Take the change, and make the escape hatch explicit and
documented:

- **With a schema**, the declared type wins. `--set version=1.0` against
  `type: string` stays the string `"1.0"` — which is the schema earning its
  place, because it removes the guess entirely.
- **Without a schema**, infer as helm's `strvals` does, and provide
  **`--set-string`** as the forcing form, the same name helm uses, so the
  knowledge transfers.
- A value that cannot be represented as its declared type is an error naming the
  parameter and both types. Never a zero value.
- The change is called out in the pull request and in the CLI reference as a
  behaviour change, with `--set-string` named as the migration. It is not a
  silent improvement.

The old doc comment must be replaced rather than deleted: the next reader should
find out that the decision was reversed and why, not that it never existed.

### D14d: where this should be delivered — the recommendation

**This is a question for the owner, not a decision this change should make
silently, so it is put plainly.**

**Recommendation: deliver the schema and the inference command under epos#47,
re-scoped — not as a new issue, and not split into sub-issues.**

The argument:

1. **It is not a frontend.** Every part of it — an artifact-format addition, a
   pack-time inlining rule, install-time validation and defaulting, a new
   command that reads templates — lands in packaging, install and the CLI. The
   only part that touches #44 is rendering a table from data the artifact
   carries, and that part is specified here and stays here.
2. **epos#47 is already this subject.** Its title is *"install `--set` does not
   infer types (must match helm)"*; its defect is that `applySet` stores every
   value as a string so `--set openapi=false` is truthy; its acceptance criteria
   are about what type a value has. A declared schema is the **better answer to
   its own question**: with a declared type, `--set x=false` is coerced to what
   the skill said it was, rather than to whatever a syntax heuristic guessed.
   The schema supersedes #47's proposed approach without abandoning its goal,
   and #47's acceptance criteria survive intact as the fallback path for
   undeclared values.
3. **The house rule is satisfied, in the direction it points.** One issue is one
   deliverable and is not split without the owner asking. Re-scoping #47 to
   *"values are typed by a declared schema"* is one coherent deliverable — the
   schema without validation is decoration, and validation without the inference
   command is a chore nobody performs. It is **absorption, not a split**. What
   *would* violate the rule is carving three sub-issues out of the owner's
   paragraph, and that is not proposed.
4. **#44 is already large.** It carries four capabilities, and this review adds
   a persistent metrics stack, CI traffic generation and a browser-driven test
   tier. Adding an artifact-format change and a new command tree on top produces
   a pull request no reviewer can hold in their head — which is how the parts
   that matter get waved through.

**What happens under each answer**, so neither leaves a gap:

- *If the owner keeps it on #44*: the `epos-values-schema` delta is implemented
  as written in this change. Nothing needs re-specifying; the tasks are already
  sequenced.
- *If it moves to #47*: the delta moves with it, and only its last requirement —
  *"The catalog renders a skill's values contract"* — stays on #44. #44 ships
  either way, because **D11** specifies both branches and the parameter section
  is absent when no artifact declares a schema.

**SPEC consequences either way.** §10.3 (values and rendering) gains the schema
and the validation step; §2.2 (Epos extensions) gains the schema's place in the
artifact. Neither is amended by this change if the work moves.

---

## D15: the demo's numbers come from traffic CI generates

> Simulate traffic in CI and pack leaderboard with this download traffic.

**Decision.** A CI job drives real pulls against the demo's skills before the
site is rendered, and the leaderboard is filled from what the registry counted.

**The chain is the real one, end to end.** Pack with `epos pack`, publish with
`epos push`, stand up zot and `epos-registry` the way `ci.yml`'s conformance job
already does, pull each skill with `epos pull` through the registry, let the
measurements reach the store (**D4b**), then export (**D5**). Every number on
the published page is a request the registry answered. Nothing is inserted into
the store; nothing is seeded.

**The distribution is the point.** A leaderboard where every row shows the same
count demonstrates a table, not a ranking. The generator drives deliberately
different pull counts per skill — a fixed, checked-in profile rather than a
random one, so a change in the published numbers means the catalog changed and
not that the generator improvised.

**Both columns get exercised.** `epos pull` sends `Epos-Download` and lands in
the verified count; a plain blob `GET` without the header lands in the
unverified one. Driving both is what makes the page's distinction between them
visible rather than theoretical, and it is cheap — the unverified side is a
`curl` against a blob, or an `epos verify`, which the code's own comment
explains counts as an unverified download of the skill it verifies.

**The word "simulate" has to reach the page.** The demo delta already requires
that the counts not be presented as general popularity; generated traffic makes
that requirement sharper, not softer. The page says the numbers come from
traffic the project's own build generated, over what window, captured when.
**D5a** explains why that window is one CI run today.

**Rejected: generating the traffic by inserting rows into the store.** It is
faster, it produces the same-looking page, and it breaks the one requirement the
whole statistics design exists to protect — that every count came from a
download the registry actually answered. The point of driving real pulls is that
the leaderboard is then evidence the chain works, which is what a demo is for.

---

## D16: end-to-end tests in a browser, with `playwright-go`

> We must add e2e tests with playwright-go for the Frontend to check that
> navigation works and everything renders correctly and that numbers change when
> we download something and refresh the page.

**Decision.** A third test tier, behind its own build tag, driving a real
browser with `playwright-go` against a catalog built from a real registry.
Scenarios live in the project's `features/` files like every other behaviour
(SPEC §13.3), with playwright-go in the godog step implementations — a new
driver under the existing discipline, not a second test framework beside it.

### D16a: how "numbers change on refresh" is reconciled with a static site

This is the part of the request that has a real design question in it, and
answering it is what **D4e** and **D5a** exist for.

A statically exported page cannot show a number that changes on reload — there
is no server to ask. So the assertion is split, and both halves are asserted:

| subject | assertion |
|---|---|
| `epos-registry --catalog` + a live stats source | read the count, `epos pull` the skill through that same registry, reload, **the count has increased**. This is the owner's assertion, literally, and it is why the served catalog reads counts per request (**D4e**) rather than at startup — and since **D2** the process that counts the pull and the process that renders the number are one. |
| the exported directory, served by a plain file server | read the count, pull, reload, **the count is unchanged** — asserted deliberately, so the difference is a tested property of the static mode rather than a surprise in production. Then re-export and assert the number **has** moved. |

Two consequences worth being explicit about:

- Without **D4e**'s per-request read, the first row is unsatisfiable and the
  request would have been quietly reinterpreted as "the number is correct at
  startup". The owner's comment is what forced that decision into the open.
- The static half is the more useful test of the two, because the static half is
  what gets deployed.

### D16b: `playwright-go`, and the two facts that will otherwise cost a day

**The module path moved.** `github.com/playwright-community/playwright-go`
**301-redirects to `github.com/mxschmitt/playwright-go`**, and v0.6100.0
declares the new path. The consequence is concrete: `go get` at the old path for
v0.6100.0 fails with *"module declares its path as … but was required as …"*.
The last version resolvable at the community path is **v0.6000.0**. Pick
deliberately — pin v0.6000.0 at the old path, or import the new path — and
record which in the pull request, because `go get -u` at the old path is a hard
failure today and the next person will hit it.

**It downloads a Node-based driver.** playwright-go ships no browser; the first
run downloads Playwright's own driver bundle — roughly 50 MB, including a
bundled `node` binary — and then the browsers. Node is *not* required on `PATH`;
the runtime is inside the bundle. Both are cacheable and pinnable:
`PLAYWRIGHT_DRIVER_PATH` (or `RunOptions.DriverDirectory`) fixes the driver
directory, `PLAYWRIGHT_BROWSERS_PATH` fixes the browsers, the driver version is
hard-pinned per playwright-go release, and CI caches
`~/.cache/ms-playwright-go` and `~/.cache/ms-playwright`. There is no official
Action and no official image for the Go bindings.

**This must not be read as contradicting the catalog's "no Node runtime"
claim.** That claim is about **building, serving and rendering the catalog** —
`go build` from a fresh clone produces a binary that serves complete pages, and
nothing in the delivery path involves Node. The test harness downloading a
driver is test tooling, and the specs now say so in both places rather than
leaving a reader to reconcile them.

### D16c: the repository has already refused a browser driver once, and that has to be answered

`internal/sign/sign.go`'s package comment rejects `sigstore/sigstore` partly
because *"it drags in … go-rod — a headless-browser driver that downloads and
spawns a browser binary. None of that is reachable from ECDSA signing, but all
of it lands in go.sum and in govulncheck's surface."* Adopting playwright-go
without meeting that argument would be reversing a written decision by not
noticing it.

**The argument does not transfer, and here is why.** sign.go's objection is to
82 modules arriving in `go.sum` and in `govulncheck`'s surface **for code that
is never reachable** — a browser driver linked into a signing path. Here:

- The dependency is **reachable and used**: it is the only way to assert that
  the frontend renders, which is the deliverable.
- The **module graph is small** — playwright-go's own build closure is roughly
  four modules, all pure Go. The weight is the runtime download, which is not in
  `go.sum` and not in the binaries.
- It sits behind a build tag, imported only by test files, so **neither released
  binary links it** and `go test ./...` never needs a browser.

**Rejected: a separate module under `tests/e2e/go.mod`** to keep the main
`go.mod` clean. It works, and it is a second module to keep tidy, version and
release for a dependency that is already tag-isolated. The repository already
carries test tooling in the main module (`tool go.uber.org/mock/mockgen`), so
this is the existing convention rather than a new indulgence.

**Rejected: `chromedp` or `go-rod`.** Both are pure Go, speak CDP directly, and
need no Node driver — which is genuinely attractive against sign.go's objection.
They are not chosen because the owner named playwright-go, and because
cross-browser coverage, auto-waiting and actionability checks are what keep a
browser suite from becoming a source of flakes. `go-rod` has additionally not
cut a tag in about two years. If the owner would rather not have a Node driver
in the tree at all, **`chromedp` is the substitution to make**, and it changes
the step implementations and nothing in the feature files — which is a reason to
keep the scenarios in `features/` and the driver behind them.

---

## D17: the Epos skill — generated where it can be, authored where it cannot

> Let's also publish Epos skill btw. You will need to create it first. A skill
> that teaches how to properly create skills with Epos. All the cli reference and
> Skillfile reference. And about the values file and the syntax for templates.
> Also some guidance on how to decide about what needs to be in values, like
> parts of the header, whether references are enabled for some tools. For
> example, testcontainers ships a bunch of references for different languages,
> while we only need Go.

**Decision.** The repository gains `skills/epos/` — a skill that teaches how to
author skills with Epos — packed by `epos pack`, published beside `go-house`,
and rendered by the demo catalog. It is **half generated and half authored**, and
the split is not a compromise: it follows from which parts have a machine-readable
source and which are judgement.

### D17a: the two reference documents are generated, by the generator that already exists

**This was worth checking before deciding, and the answer is yes.**
`internal/docsgen` already renders both references from the implementation:

- `renderCLI` walks the live cobra tree (`cli.NewRootCommand`) — names, usage
  lines, summaries, prose and every flag with its type and default.
- `renderSkillfile` reads `skillfile.NewReference()`, which is **already plain
  data**: `Instructions`, `Topics`, `Sources` and `Syntax`, each a struct with
  fields a renderer formats.

So the *sources* are structured and reusable. What is not reusable is the
`page` type: `page.w` writes Astro markup line by line, `escape` escapes for
Astro's brace syntax, and `frontmatter` emits an `import Base from …`. Content
and presentation are fused in the emitter, not in the sources.

**Decision.** Extract the emitter, not the content. `docsgen` gains a Markdown
emitter beside its Astro one, and two new entries in `targets()`:

| target | source | today |
|---|---|---|
| `docs/src/pages/cli.astro` | `cli.NewRootCommand` | exists |
| `docs/src/pages/skillfile.astro` | `skillfile.NewReference()` | exists |
| **`skills/epos/references/cli.md`** | `cli.NewRootCommand` | **new** |
| **`skills/epos/references/skillfile.md`** | `skillfile.NewReference()` | **new** |

**Why this and not a second generator.** `docsgen`'s own comment on `targets()`
answers it: *"A second generator with a drift check of its own is how two pages
start disagreeing about what 'generated' means, and how one of them quietly
stops being checked at all."* Adding two targets puts the skill's references
under the **existing** `go run ./internal/docsgen -check` gate that CI already
runs, so a flag added to `epos pull` updates the docs site and the skill in one
command and fails the build until both are committed. A hand-written skill
reference is a document that is accurate on the day it is written and wrong by
the next release — which is the failure the owner's "all the cli reference and
Skillfile reference" is most exposed to, because a skill is read by an agent
that cannot tell.

**One gap this exposes, and it is worth fixing here.** `renderCLI` walks
`epos`'s tree only, so **`epos-registry`'s flags are documented nowhere** — not
on the docs site, not in a skill, not anywhere but `--help`. This change adds
flags to it (**D2b**), and a previous draft of the task list wrongly asserted
that the drift gate would catch the stale `--metrics.exporter` help string; it
would not, because that binary is not walked. So `docsgen` walks both command
trees, and the CLI reference — Astro and Markdown alike — gains an
`epos-registry` section.

### D17b: the guidance is authored, and it is the part that makes the skill worth having

The owner asked for three things the generator cannot produce, and they are the
reason this is a skill rather than two files:

1. **The values file and the template syntax.** Partly derivable —
   `skillfile.NewReference()` already carries a values-model topic — and partly
   not: worked examples of a `values.yaml` against a real Skillfile are written,
   not generated.
2. **How to decide what belongs in values.** *"Parts of the header, whether
   references are enabled for some tools"* — this is a judgement about API
   design. A parameter earns its place when two real consumers disagree about
   it; everything else is a fork of the skill, not a value.
3. **The worked example the owner gave, which is the whole lesson.**
   *"testcontainers ships a bunch of references for different languages, while we
   only need Go."* That is exactly `examples/go-house/`'s `containers` stage —
   `{{ if .Values.testcontainers }}` gating whether the reference is included at
   all, and a `COPY` that takes only the Go files. The guidance and the example
   are the same artifact seen twice, which is what makes the skill teachable and
   what makes it check itself: a page in `skills/epos/` describing a stage that
   `examples/go-house/` does not have is a defect the demo shows on its own
   detail page.

So `skills/epos/` is:

```
skills/epos/
  SKILL.md                   authored — when to reach for epos, the pack →
                             push → install loop, and where each reference is
  references/cli.md          GENERATED from the cobra trees
  references/skillfile.md    GENERATED from the instruction table
  references/values.md       authored — values files, template syntax, and
                             what belongs in values (the D17b guidance)
  values.schema.json         its own declared contract, if D14 lands here
```

**The recursion is deliberate and it is the demo's strongest argument.** The
Epos skill is packed by `epos pack`, published by `epos push`, listed by the
catalog, and its detail page renders its own `SKILL.md` — a skill about
authoring skills, shipped through the pipeline it documents. It also gives the
demo its **second** skill for free, which the demo delta already required so
that the leaderboard ranks something rather than showing one row.

**Rejected: writing the two references by hand.** Faster today, wrong by the
next release, and invisible to the drift gate that exists precisely to prevent
this.

**Rejected: generating `SKILL.md` too.** There is no source for "when should you
use this"; a generated entry document would be a table of contents, and an
agent reading it would learn nothing it could not get from `--help`.

**Rejected: deriving the Epos skill with a Skillfile from the docs.** Cute, and
it would make the skill a build rather than a directory — but the references
come from Go source, not from another skill, so there is no base to derive from
and `FROM` has nothing to name.

**A scope note, stated because this change has a non-goal about exactly this.**
The non-goals say epos#42 owns `examples/go-house/` and that #44 "does not
define a second recipe for it". That still holds: `skills/epos/` is a different
skill, it is not derived from go-house, and it does not touch #42's recipe. It
is new scope on #44, added by the owner's review, and it is recorded as such
rather than smuggled in under the existing boundary.

---

## Open questions for the owner

1. **Where does the values schema get delivered?** (**D14d**) The recommendation
   is **epos#47, re-scoped** — a declared schema is the better answer to that
   issue's own question, and the schema, its validation and the inference
   command are one deliverable rather than three. Nothing is split; #44 keeps
   only the rendering of a contract the artifact carries, and ships either way.
   **This is the one question whose answer changes what is in this change's pull
   request**, so it wants answering before implementation starts.
2. **ui-kit v0.4.0** — cut it, or hold it and hand-roll the stat tile? This is
   the same question bikelanes#4 is parked on (**D6a**). One answer serves both.
3. **A host, or one CI run's worth of history?** (**D5a**) ClickHouse ships and
   is queryable, but the demo's store lives inside the CI job, so the published
   leaderboard shows the traffic of the build that produced it. One host running
   zot, `epos-registry --catalog`, a collector and ClickHouse turns
   that into a live catalog with accumulating history and **nothing else in this
   change has to change**. It needs infrastructure and a credential the
   repository has never had, so it is the owner's call and it is the biggest
   remaining gap between what shipped and what was asked for.
4. **`examples/go-house/`** — this change assumes epos#42 merges and supplies it
   (**D1**). If #42 is rejected, #44 needs a different example skill and loses
   the three capabilities the issue wants demonstrated. **Since this review the
   dependency is softer**: the Epos skill (**D17**) is #44's own and needs
   nothing from #42, so the demo has a real skill to publish and a leaderboard
   with something on it even if #42 never lands. It would show one skill instead
   of two, and lose the multi-stage provenance table, which is #42's artifact to
   demonstrate.
7. **Does amending §4.4 and decision #2 go too far?** (**D2a**) The catalog
   moving into `epos-registry` requires both — a second (non-API) surface on the
   listener, and a process-local index that is, in §4.4's words, a manifest
   cache. The amendments are written narrowly: the catalog is off by default,
   `/v2/` is answered before any catalog route and never from anything the
   catalog holds, and nothing is written to disk or shared between replicas.
   §3 already anticipates this direction — *"capabilities that require owning an
   index … are added to it over time, making it progressively less of a
   pass-through"* — and §7.4 defers native discovery to exactly such an index.
   Flagged because these two clauses were the previous draft's stated reason for
   the shape the review overturned, and a reader who checks the SPEC first
   should find the amendment rather than a contradiction.
5. **`playwright-go`, or a pure-Go browser driver?** (**D16b**, **D16c**)
   playwright-go was named in the review and is specified. It downloads a
   Node-based driver, which is exactly the class of dependency
   `internal/sign/sign.go` refused once already; **D16c** argues the refusal
   does not transfer, and the argument may not convince. If it does not,
   `chromedp` substitutes without touching the feature files. Flagged rather
   than decided.
6. **Where does the site's Pages build stand?** (**D5**) The API reports
   `status: errored` for `gaarutyunov/epos` today while the site serves — normal
   in branch mode, and it means the first symptom of a broken catalog publish
   will look exactly like the state the repository is already in. Worth clearing
   before the demo deploys, and it may be a pre-existing repository issue rather
   than anything this change should carry.
