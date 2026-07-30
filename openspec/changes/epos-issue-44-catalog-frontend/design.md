# Design — epos#44, the catalog frontend

## What is actually there today

Read from `origin/main` of `gaarutyunov/epos` (`deb2b69`), not from a working
checkout.

**Module** `github.com/gaarutyunov/epos`, Go 1.26.4. One module, `main` per
binary under `cmd/`, shared code in top-level `internal/`. No `pkg/`, no `api/`
— SPEC §13.4 mandates that shape ("Plain Go. No code generation, no model, no
hexagonal layering, no DDD"). OCI via `oras.land/oras-go/v2 v2.6.2`; cobra;
koanf (never Viper); OTel `v1.44.0` with the stdout metric exporter.

**Binaries**: `cmd/epos` (13 commands) and `cmd/epos-registry` (a single flat
command). There is no `serve`, `web`, `ui` or `catalog` command anywhere.

**`//go:embed`: zero occurrences in the repository.** Embedding a frontend is
net-new; there is no precedent to follow and nothing to extend.

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

## D2: `epos catalog serve|export`, on the `epos` binary

**Decision.** One new command tree on `cmd/epos`:

```
epos catalog serve   --registry --namespace --refs --plain-http --base-path \
                     --stats-source --stats-file --addr
epos catalog export  --registry --namespace --refs --plain-http --base-path \
                     --stats-source --stats-file --out
```

One renderer, two drivers. `serve` answers requests; `export` walks the same
route table and writes each route to a file. A page that only one of them can
produce is a bug.

**Why not a third binary (`epos-catalog`).** Nothing about it deploys separately
from the CLI. A third binary is a third goreleaser build matrix, a third set of
release artifacts and a third `main` to keep in step, bought for no isolation
that matters — the catalog holds no secrets and takes no writes.

**Why not on `epos-registry`.** Two SPEC clauses forbid it and both are right.
§10.1 decision #3: *the registry never renders anything*. Decision #2: `/v2/`
only, no second API surface. Beyond the letter: `epos-registry` is designed to
run as N stateless replicas behind a load balancer (§4.4), and the catalog wants
a warm per-digest cache and an index it built at startup. Putting them in one
process makes the relay's statelessness a lie.

**Why on `epos` rather than nothing.** "Embedded into Go" is the issue's own
constraint, and `epos catalog serve --registry localhost:5000` is a real
feature for anyone running a private registry — the same binary they already
have, browsing the skills they already pulled. The cost is 104 KB of vendored
JS plus templates in a binary that is already several megabytes.

**Consequence: `internal/cli/discover.go` gets lifted — and it is not quite a
pure move.** The discovery client, `discover`, `skill` and `errNoCatalog` move
to a new `internal/registry` package, exported, and `internal/cli` calls into
it. But `newOCIRegistry(host string, opts registryOptions)` and
`ociRegistry.explain` depend on `registryOptions`, which lives in
`internal/cli/credentials.go`, carries the cobra flag binding and the Docker
credential store, and is shared by `pull`, `push`, `build`, `sign` and
`install`.

**Decision: `registryOptions` does not move.** `internal/registry` defines its
own plain options struct — plain-HTTP, an `auth.Credential` resolver, a
`remote.Client` — with no cobra and no koanf in it, and `internal/cli` builds
one from its existing `registryOptions`. Dragging cobra into `internal/registry`
to avoid writing an eight-line adapter would put flag parsing under a package
whose job is to talk to registries, and would make every registry-contacting
command depend on the CLI's flag types.

Behaviourally this is still a move: `epos list` and `epos search` must produce
byte-identical output afterwards, the existing `discover` tests move with it,
and their expected output must not be edited in the same commit. If it has to
be, the move was not a move.

**Consequence: the docsgen drift gate fires.** `internal/docsgen` renders
`docs/src/pages/cli.astro` from the live cobra tree, and
`.github/workflows/ci.yml` fails on any diff. Adding `epos catalog` changes that
page. Regenerating and committing it is a required task, not an accident.

### D2a: flags, not koanf; kebab-case, not dots; `RunE` and `cmd.OutOrStdout()`

**Decision.** `epos catalog` is configured by flags alone, named in kebab-case:
`--registry`, `--namespace`, `--refs`, `--plain-http`, `--base-path`,
`--stats-source`, `--stats-file`, plus `--addr` on `serve` and `--out` on
`export`.

koanf and the `EPOS_REGISTRY_` env prefix belong to `epos-registry`, which is a
long-running server configured by an operator. Every command on the `epos`
binary today is flags-only and kebab-case (`--plain-http`, `--password-stdin`,
`--versions`). `epos catalog serve` being a server is not a reason to make one
subcommand of `epos` configure itself differently from the other thirteen; a
container deployment (**D5**'s rejected alternative) passes flags perfectly
well. The dotted `--metrics.exporter` form on `epos-registry` exists only
because koanf maps dots to config keys — copying the punctuation without the
mechanism would be cargo cult.

The rest is the repository's existing shape and is called out only because a
new command is where it gets forgotten: factory functions returning
`*cobra.Command` registered in `NewRootCommand`, `RunE` so errors propagate,
`cobra.NoArgs` on every one of them (both subcommands take only flags), and all
output through `cmd.OutOrStdout()` so the commands are testable in memory.

### D2b: the catalog is served under a base path, and it is the same in both modes

**Decision.** Both subcommands take `--base-path` (default `/`), every internal
URL the templates emit is prefixed with it, and the two drivers produce
identical bytes **for the same base path**.

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
sweep **or** an explicit list of references, and the choice is a flag, not a
fallback chain.

- `--registry <host> --namespace <ns>` — the `epos list` path. Requires
  `GET /v2/_catalog`.
- `--refs <file>` — a checked-in list of `<host>/<repo>:<tag>` references, one
  per line. No `_catalog` required.

**Why both.** `errNoCatalog` exists in the shipped code because registries
disagree about `_catalog`: it is an optional part of the distribution spec, and
several of the largest registries either omit it or scope it to an
authenticated, per-account view. The demo publishes to `ghcr.io` (**D10**), and
a demo that cannot enumerate its own registry is not a demo. A `--refs` file
also makes the static export reproducible: the same file produces the same site.

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
is a goroutine, a lock and a cache-invalidation policy, and **D4e** already
records what that costs when it is not needed.

### D3c: the content layer is untrusted, and the existing guards come with it

**Decision.** The exported remote-fetch routine keeps every guard
`internal/skillfile` applies today: the 64 MiB layer cap, `checkPath`'s refusal
of `..`, absolute and non-canonical entries, and the rejection of symlinks and
hardlinks. The routine to export is **`skillfile.fetchOCIBase`** — resolve,
fetch the manifest, assert exactly one layer, fetch it, untar into a `Tree` —
not `install.read` (which reads the *local store*) and not `ociTreeFiles` (which
takes bytes already in hand).

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

## D4: Download statistics — the producer, the consumer, and what may be ranked

This is the part of the issue with no implementation behind it, so it gets the
most space. It is also the part where the first draft of this design overreached
and had to be cut back; **D4e** records what was cut and why, because the
argument for cutting it is more useful than the design that was cut.

### D4a: the counter already has a readable output — use it

**Decision.** Add no exporter. The snapshot that feeds the leaderboard is
produced from the **stdout exporter `epos-registry` already implements**, parsed
the way the repository already parses it.

`tests/integration/steps_counting.go` reads `epos.downloads` out of
`epos-registry`'s stdout as OTel JSON and asserts on it, with
`metricsInterval = 200ms` and last-export-wins on the cumulative value. That is
a working, tested, dependency-free reader for exactly the numbers the
leaderboard wants. The snapshot job (**D5**) starts `epos-registry` with
`--metrics.exporter stdout`, drives the demo's pulls, shuts it down so the final
flush lands, and converts the last export into the snapshot file.

**Consequences, all of them good for this change:** no new module, no second
listener, no goroutine, no durable state, no amendment to SPEC §4.4, §4.5,
§5.1, §5.2, §5.3 or §10.1, and nothing in `epos-registry` changes at all.

### D4b: the `client` attribute stays where it is

With no Prometheus exporter there is no label-cardinality decision to make. The
observation that produced one in the first draft is still worth recording,
because it constrains whoever implements **D4e**:

`Download.Client` is the raw `User-Agent`. As a Prometheus label it would be
attacker-controlled, unbounded cardinality — one time series per distinct
User-Agent per repository, forever, created by anyone who can issue a blob
`GET`. The SPEC already refuses far less: `VersionAttribute` is off by default
with the comment *"version-valued attributes accumulate without bound under a
Prometheus exporter, one time series per version per repository, forever."*
Versions are at least finite and authored by the publisher; User-Agents are
neither. **Any future scrapable exporter must drop `client`.** Bucketing it into
an enum (`epos`/`oras`/`docker`/`other`) is not the fix — it duplicates
`verified`, since a request from `epos pull` is precisely a request carrying
`Epos-Download`, and it adds a parsing rule that rots on every client's next
release.

The snapshot reader ignores `client` for the same reason: the leaderboard is
per-repository, and aggregating over clients is what it wants anyway.

### D4c: the leaderboard ranks the verified side of the counter

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

### D4d: the catalog reads counts through a `Stats` source, with two implementations

**Decision.** One interface, one method, `context`-taking, two implementations
selected by `--stats-source`:

```go
// Stats reports how often each repository has been pulled.
type Stats interface {
	Pulls(ctx context.Context) (Snapshot, error)
}

// Snapshot is per-repository counts as of a stated moment.
type Snapshot struct {
	CapturedAt time.Time
	Rows       map[string]Pulls // keyed by OCI repository
}

type Pulls struct{ Verified, Unverified int64 }
```

| source | where the numbers come from | who uses it |
|---|---|---|
| `none` (default) | nothing — the column is absent and the home page falls back to a stated deterministic order | anyone browsing a registry with no `epos-registry` in front of it |
| `snapshot` | a JSON file with the shape of `Snapshot` above | `epos catalog export`, and the demo |

`none` is the default and it is a first-class mode, not a failure state: most
registries have no `epos-registry` in front of them, and a catalog that renders
a broken leaderboard in that case is worse than one that renders a catalog.

`Snapshot` is the wire shape and the in-memory shape, deliberately — one
definition, `encoding/json` tags, no converter, no second schema to drift.

**Rejected: counting in the catalog itself, by proxying pulls through it.** That
would give exact numbers with no metrics pipeline at all — and would put the
catalog on the data path of every pull, which is the architecture SPEC §4.2
spent its budget avoiding.

### D4e: what was cut, and what live counts would actually cost

The first draft of this design implemented `metrics.ExporterPrometheus`, opened
a second listener on `epos-registry` for it, and gave the catalog a third
`Stats` implementation that polled it. **All three are cut.** The reasoning is
recorded here rather than deleted, because someone will want live counts and
should not have to rediscover the price.

What the polling design dragged in, none of which the deliverable needs:

- **A dependency tree in the CLI binary.** `go.opentelemetry.io/otel/exporters/prometheus`
  pulls `github.com/prometheus/client_golang`, `prometheus/common` and `procfs`
  into `epos-registry`; parsing the exposition text pulls `prometheus/common/expfmt`
  into **`epos`**, so the CLI would carry a Prometheus text parser. The module has
  none of these today.
- **The change's only goroutine and its only durable state.** A poller mutating a
  totals map that HTTP handlers read, with a persistence format, an atomic-write
  discipline, a shutdown path and a `-race` job on three platforms — for a
  deliverable (**D5**) that is a static export.
- **A hand-rolled solution to a solved problem.** The accumulator existed to
  survive counter resets; Prometheus solves resets, staleness, downsampling and
  multi-replica aggregation properly, and the accumulator solved only the first.
- **Five SPEC amendments** (§4.5, §5.3, §10.1, §12, and the registry's listener
  description) for a capability nothing in the issue asked for.

**What live counts would take, when someone wants them.** A `promql` source
behind the same one-method interface, pointed at a Prometheus that scrapes an
`epos-registry` exporting to it — with `client` dropped from that exporter's
attributes (**D4b**). That is an addition, not a rewrite, which is the whole
reason `Stats` is one method wide. Filed as a follow-up rather than built.

**What this costs today, stated plainly.** `epos catalog serve` against a
private registry shows no counts unless someone hands it a snapshot file. The
demo's numbers are a snapshot with a timestamp on the page. There are no live
counts anywhere in this change, and that is a real reduction against the issue's
ask.

---

## D5: the demo is a static export on the Pages site the repo already has

**Decision.** `epos catalog export --base-path /epos/catalog --out catalog-dist`
writes to a directory of its own, published to `gh-pages` under `catalog/` and
served at `https://gaarutyunov.github.io/epos/catalog/`. The demo's numbers come
from a `snapshot` produced by a CI job that runs the real pipeline against an
ephemeral zot and `epos-registry`.

**Why.** The repository can reach exactly one deployment target today: GitHub
Pages, from `gh-pages`, already built and already `https_enforced`. It cannot
run a Go binary anywhere, publishes no container image, and names no host.
`keep_files: true` is already set on the docs deploy — for an unrelated reason,
but it means a second publisher into the same branch does not wipe the first,
which is what makes `/epos/catalog/` cheap.

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
   must join that concurrency group, or the two races and one loses — silently,
   because both report success.

None of these fails loudly. All three are checked by opening the deployed docs
site after the catalog's first deploy, and that check belongs in the task list.

**What it costs, stated plainly.** A static export cannot show live pull counts.
Real numbers need a live `epos-registry` in front of the registry serving the
pulls, and a live catalog scraping it — neither of which exists and neither of
which Pages can host. **The demo's leaderboard is therefore honest-but-small**:
the counts are the demo pipeline's own pulls, produced by CI, and the page says
so in words on the page rather than in a comment in the repository. This is a
real reduction against the issue's ask and it is the owner's to overturn.

**The workflow trap.** `docs.yml` triggers on `docs/**` only. A catalog export
driven from Go source would never fire it. The workflow's paths and the export
step are both part of this change; getting this wrong produces a site that
silently never updates.

**Alternatives rejected.**

- *A container image plus a host.* This is what a live demo requires: a
  `dockers:` (or ko) target in `.goreleaser.yaml`, an image pushed to ghcr, and
  a host running zot + `epos-registry` + `epos catalog serve`. Rejected as the
  default because it needs infrastructure and secrets the repository has never
  had, and it would park #44 behind an owner provisioning decision. Sized in
  tasks as a follow-on: the image target is roughly ten lines of goreleaser, and
  everything else in this change already works live via `serve`.
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

**New dependency, and it is the only one.** A Markdown renderer is genuinely
new — the module has none. `github.com/yuin/goldmark` is the choice: it is the
CommonMark implementation the Go ecosystem standardises on, pure Go, no cgo
(SPEC §1.2), and its default configuration is the safe one. It is the **single**
module this change adds; if an implementation finds itself adding a second, that
is a signal to stop and re-read **D4e**.

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

**What is deliberately not copied from skills.sh**: the 8-week sparkline (no
time series exists — see **D4d**; adding one means a `promql` stats source, and
`ga-chart-frame` draws no data by design), security-audit columns, topics, the
agent marquee animation, editorial picks, and the `/api/v1` JSON surface.

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
   exist in `internal/cli/discover.go` *because this is common*. `epos list`
   and `epos search` do not work against a registry without it, and neither does
   the catalog's namespace mode (**D3**).

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

## D10: publishing the example — either command, neither blocking

**Decision.** #44 does **not** block on epos#43. The publish step is one line in
one CI workflow, and the spec requires *"the repository's own tooling publishes
the example, and no OCI client other than `epos` is required once one exists"* —
satisfied by `epos push` after #43 merges, and by `oras cp
--from-oci-layout-path "$(epos store path)" …` until then, which is what the
quick start documents today.

**Why not block.** #43 is CI-green and awaiting approval only. Blocking four
capabilities on an approval gate for one workflow line trades all of #44's
progress for a cosmetic difference in a YAML file. The issue's actual
requirement — *"we should pack my go skill … so we would also use epos to pack
our own skill"* — is about `epos pack`, which shipped long ago.

**Which registry.** `ghcr.io/gaarutyunov/skills/`. It is free, the org already
pulls from it in CI, and a workflow's `GITHUB_TOKEN` can push packages it owns —
so publishing needs no new secret. The consequence is **D3**: ghcr is one of the
registries where a `_catalog` sweep cannot be relied on, so the demo runs in
`--refs` mode. That is not a workaround; it is the reason `--refs` is specified.

**Rejected: publishing to a zot instance stood up for the demo.** Needs a host
(**D5**) and makes the demo's artifacts disappear when it goes away.

---

## D11: what the catalog can show about parametrisation, and what it cannot

**The gap.** The issue wants the demo to show "parametrisation of tools". The
artifact does not carry its parameters. `epos build` writes
`dev.epos.skillfile.digest`, `org.opencontainers.image.base.name`, `.base.digest`
and `dev.epos.skillfile.stages` (`provenanceFor` in `internal/cli/build.go`), and
the config blob carries the `SKILL.md` frontmatter. **No annotation records which
`{{ .Values.x }}` a skill accepts, what type it is, or what it defaults to.** A
catalog cannot render a values form because there is nothing to render it from.

**Decision.** Do not add one in this change. Show what the artifact does carry,
which turns out to be the better demonstration:

- **`dev.epos.skillfile.stages` is a file→stage map.** It says, per file in the
  installed tree, which Skillfile stage produced it. Rendered as a grouped table,
  it *is* the picture the issue asks for: `references/cli.md` from the `cli`
  stage, `references/generics.md` from `pro`, the testcontainers example from
  `containers`, everything else from the base. "Build with references from spf13
  and golang-pro, dropping what we don't use" becomes a table of real annotation
  data rather than a claim in prose.
- **The base and Skillfile digests** identify the recipe and pin the base.
- **The parameters themselves are documented in `SKILL.md`**, which #42's task
  2.6 already requires the derived skill's entry document to do, and which the
  detail page renders in full.

**Why not add a `dev.epos.skillfile.values` annotation here.** It is the right
general fix and it belongs to the builder, not to a frontend. Specifying a values
schema — types, defaults, required-ness, per-stage scoping — inside a change
whose subject is a catalog page would be a builder feature smuggled in through a
UI issue, and it would collide with epos#47 (`--set` does not infer types), which
is already the owner's on the same surface. Recorded as a follow-up worth filing.

**The absence is visible on the page, deliberately.** The detail page shows an
install command; for a skill with parameters it cannot pre-fill them. The
go-house page therefore shows the two values profiles as what they are — files
in the repository, linked — rather than as something the catalog discovered.

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
  snapshot parsing including a repository with no row; `--refs` parsing; the
  export path-containment check against a hostile repository name.
- **Integration, real containers**: a zot registry (`ghcr.io/project-zot/zot-linux-amd64:v2.1.18`,
  the pinned image already in `tests/integration/registry_read_path_test.go`)
  with skills packed and pushed into it, `epos-registry` in front, `epos pull`
  driving the counter, the counter read out of the registry's stdout export the
  way `tests/integration/steps_counting.go` already reads it, and the rendered
  page asserted to carry the count. This is the only test that proves the whole
  chain, and the chain is the deliverable.
- **A hostile artifact**, pushed to the real registry: an oversized layer and a
  layer with a `..` entry. The catalog must still list it, its page must say the
  document could not be read, and no file may appear outside `--out` (**D3c**,
  **D3d**, **D12**).
- **A `--refs`-mode export against a registry with `_catalog` disabled**, so the
  ghcr case (**D3**, **D10**) is covered by a test and not by hope.
- **A new `features/` file**, since the features are canonical and never
  paraphrased into Go.
- **The docsgen drift gate** must be green after `epos catalog` joins the cobra
  tree (**D2**).

---

## Open questions for the owner

1. **ui-kit v0.4.0** — cut it, or hold it and hand-roll the stat tile? This is
   the same question bikelanes#4 is parked on (**D6a**). One answer serves both.
2. **The demo's deployment** — static on Pages with CI-produced numbers
   (**D5**, recommended, buildable now), or a container image plus a host for
   live counts? The second needs infrastructure the repository has never had.
3. **`examples/go-house/`** — this change assumes epos#42 merges and supplies it
   (**D1**). If #42 is rejected, #44 needs a different example skill and loses
   the three capabilities the issue wants demonstrated.
4. **Live counts, or a snapshot?** (**D4e**) This change ships no live download
   statistics anywhere — the demo shows a timestamped snapshot and a private
   registry shows nothing unless someone hands it a file. That is a deliberate
   cut and the owner may want it back; **D4e** prices it. It is the same
   question as 2 seen from the other end, and answering 2 with "a container and
   a host" makes answering this one worthwhile.
