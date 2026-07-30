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
                     --stats-source --stats-file --stats-dsn-file --stats-ttl --addr
epos catalog export  --registry --namespace --refs --plain-http --base-path \
                     --stats-source --stats-file --stats-dsn-file --out
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
`--stats-source`, `--stats-file`, `--stats-dsn-file`, plus `--addr` and
`--stats-ttl` on `serve` and `--out` on `export`.

**One exemption, and it is a secret rather than a setting.** The statistics
store's DSN is a credential and does not go on a command line — it arrives in
`EPOS_CATALOG_STATS_DSN` or from the file `--stats-dsn-file` names (**D4e**).
That is one environment variable read directly, not koanf and not an env prefix;
the rule below is about configuration style, and it is not weakened by refusing
to put a password in `ps(1)`.

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

## D4: Download statistics — a persistent store, and what may be ranked

This is the part of the issue with no implementation behind it, so it gets the
most space.

**This section is a reversal.** The previous draft decided (as **D4a**) to add
no exporter at all and to feed the leaderboard from a one-off snapshot scraped
out of `epos-registry`'s stdout. The owner's review rejects that:

> We need to ship persistent metrics exporter we can query on catalog page. I
> would suggest clickhouse.

The reversal is accepted and the reasoning below is rewritten to match. What
survives from the previous draft is the part that was never about the exporter:
ranking must count the verified side only (**D4d**), and the `client` attribute
is unbounded attacker-controlled cardinality (**D4c**) — which was a note about
a hypothetical exporter and is now a live constraint, because an exporter is
shipping.

### D4a: the counter needs a destination that outlives the process, and OTel already names it

**Decision.** `epos-registry` gains the **`otlp`** exporter, selected by the
`--metrics.exporter` key that already selects one. It pushes `epos.downloads`
out of the process; it queries nothing and stores nothing.

This is not a new mechanism. SPEC §5.3's own table already lists the three
exporters the project intended:

| Exporter | Use |
|---|---|
| `stdout` | godog runs, local development |
| `prometheus` | Production scrape |
| `otlp` | Production push |

`stdout` and `none` are implemented; `metrics.New` returns *"metrics exporter %q
is not implemented"* for the other two. So **implementing `otlp` completes
§5.3 rather than amending it**, and it is the push half — the one that needs no
listener on `epos-registry`, no second port, and no inbound path into a process
whose whole design is that anything may land on any replica.

**Why `otlp` and not `prometheus`.** A scrape endpoint means a second listener
on `epos-registry`, which SPEC §10.1 decision #2 (`/v2/` only, no second API
surface) rules out, and it means the *store* pulls from N replicas behind a load
balancer — which is exactly the topology §4.4 describes and exactly the topology
a scrape cannot address, because a scrape reaches one replica. Push is the only
shape that works with the deployment the project already specifies.

**§4.4 is not amended, and this is the load-bearing point.** §4.4 says
`epos-registry` holds no durable state: *"No manifest cache, no digest→role
lookup table, no shared store between replicas."* Exporting a measurement is not
holding state. The registry accumulates nothing it must survive a restart with,
shares nothing between replicas, and reads nothing back. The persistence is in a
store the registry never queries, on the far side of a one-way push. Had the
decision been "write rows to ClickHouse from the request handler", §4.4 *would*
have to be amended and a database client would sit on the request path — see
**D4f**.

The cost is real and is stated in **D4f**: the OTLP exporter drags a large
dependency graph into `epos-registry`.

### D4b: the store is ClickHouse, and epos writes none of the code that fills it

**Decision.** The persistent store is **ClickHouse**, as the owner suggested. It
is filled by an **OpenTelemetry Collector** running the contrib
`clickhouseexporter`, and epos ships the collector's configuration, not an
ingestion path. The catalog **reads** it with
`github.com/ClickHouse/clickhouse-go/v2` (official, pure Go, `database/sql`
support, native or HTTP protocol).

```
epos-registry --metrics.exporter otlp  ──OTLP──▶  OTel Collector  ──▶  ClickHouse
                                                                          │
                                        epos catalog {serve,export} ──SQL─┘
```

**Why a collector rather than writing to ClickHouse from Go.** ClickHouse has no
OTLP receiver — verified, and worth writing down because it is the thing most
likely to be assumed. Open-source ClickHouse exposes native TCP and an HTTP
interface; neither speaks OTLP. There are exactly two ways to get OTel metrics
into it: the collector's `clickhouseexporter`, or bespoke INSERTs from your own
process. The second means a ClickHouse driver in `epos-registry`, a schema epos
invents and migrates, batching, retry and back-pressure written by hand, and a
second instrumentation path beside the OTel SDK that §5.3 says there is only one
of. The collector is a container and a config file.

**Temporality is a decision, not a default to accept.** OTLP's default for a
monotonic counter is **cumulative**, and SPEC §4.4 puts N replicas behind a load
balancer. Cumulative rows from several replicas, several process lifetimes and
several export intervals all land in the same table differing only by resource
identity and start time — so `sum()` over them double-counts every interval and
`max()` throws away every replica but one. This is the kind of thing that looks
right on a single-replica demo (**D15** is exactly that) and is wrong the moment
anyone runs two.

**Decision: export the counter with delta temporality**, via the SDK's
temporality selector on the OTLP exporter, so rows are additive and the
catalog's query is a plain `sum()` over a window. The alternative — keep
cumulative and make the query take the last value per resource-identity and
start-time before summing — is a correct query that every future reader has to
re-derive, and it breaks silently when a replica restarts mid-window. Delta puts
the complexity in one exporter option instead of in every query.

This is not a free choice and the trade is worth naming: delta temporality means
a dropped export is a permanently lost increment, where cumulative would have
healed on the next one. For a download counter feeding a leaderboard that is the
right side to be wrong on — an undercount by one pull, against a number the page
already describes as a floor (**D4d**).

**The honest caveat, stated here so it is not discovered later.**
`clickhouseexporter`'s support is **beta for traces and logs and *alpha* for
metrics** (its own README), and its default schema is created by the exporter
itself — for metrics, type-partitioned tables of which `otel_metrics_sum` is the
one a monotonic counter lands in. Consequences the implementation must respect:

- Query the exporter's schema; do not re-declare it. The exporter's README
  recommends `create_schema: false` in production with the DDL managed
  separately, and is explicit that column names and types must not change or its
  inserts break.
- Pin the collector image and record the schema version the query was written
  against, because an alpha component's schema is the thing that will move.
- The catalog's query lives behind the `Stats` interface (**D4e**), so a schema
  change is one implementation, not a rewrite.

**Rejected: ClickHouse Cloud, or any managed store, as the demo's backing.** It
needs an account, a credential and a bill, all of which are the owner's to
provision and none of which the repository has. What the demo can do without any
of that is **D5**.

**Rejected: SQLite, or a file the registry appends to.** It is the smaller
thing, and it is exactly what §4.4 refuses: durable state in `epos-registry`
that N replicas cannot share.

### D4c: the `client` attribute must be dropped, and now that is enforceable

The previous draft recorded this as a constraint on a hypothetical future
exporter. An exporter is now shipping, so it is a requirement.

`Download.Client` is the raw `User-Agent`. In a store it is attacker-controlled,
unbounded cardinality — one row group per distinct User-Agent per repository,
forever, created by anyone who can issue a blob `GET`. The SPEC already refuses
far less: `VersionAttribute` is off by default with the comment *"version-valued
attributes accumulate without bound under a Prometheus exporter, one time series
per version per repository, forever."* Versions are at least finite and authored
by the publisher; User-Agents are neither.

**Decision.** The attribute is removed by the metric pipeline, not by
convention. The OTel Go SDK has the mechanism:

```go
sdkmetric.NewView(
	sdkmetric.Instrument{Name: "epos.downloads"},
	sdkmetric.Stream{
		AttributeFilter: attribute.NewAllowKeysFilter("repository", "verified", "version"),
	},
)
```

registered with `sdkmetric.WithView` on the provider. An allow-list rather than
a deny-list, so a future attribute is excluded until someone decides otherwise.

Two details that are easy to get wrong:

- **Exemplars.** The SDK documents that attributes a view filters out may still
  appear on exemplars, which record the dropped measurement attributes.
  Exemplars must be off, or filtered too.
- **The stdout exporter.** Nothing forces the filter to be exporter-specific,
  and making it so is a second code path for no gain. Apply the view
  unconditionally. If `tests/integration/steps_counting.go` asserts on `client`,
  that assertion changes — and it is the only place in the repository that reads
  the attribute at all, which is the argument for dropping it everywhere rather
  than only where it is dangerous.

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
selected by `--stats-source`:

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
| `none` (default) | nothing — the column is absent and the home page falls back to a stated deterministic order | anyone browsing a registry with no `epos-registry` in front of it |
| `clickhouse` | a SQL query against the store (**D4b**) | `epos catalog serve` against a live deployment; the demo's export job |
| `file` | a JSON document with the shape of `Counts` above | reproducible exports, unit tests, and anyone with numbers but no store |

`none` is the default and it is a first-class mode, not a failure state: most
registries have no `epos-registry` in front of them, and a catalog that renders
a broken leaderboard in that case is worse than one that renders a catalog.

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
`--stats-ttl=0` exactly "query every request", which is what the end-to-end test
sets it to rather than sleeping.

**The credential does not go on the command line.** `--stats-dsn` would put a
working credential for a queryable database in `ps(1)` and in every shell
history on the box, for a `serve` process that runs for days. This is the one
place **D2a**'s flags-only rule bends, and it bends the way the CLI already
bends it for `epos registry login --password-stdin`: the DSN arrives in
`EPOS_CATALOG_STATS_DSN`, or from a file named by `--stats-dsn-file`. That is
one environment variable, not a koanf tree and not an env prefix — **D2a**'s
argument was about configuration style, and a secret is not configuration style.

The TTL is the stated freshness bound in the stats delta. It must be short
enough that the e2e assertion — pull, reload, number moved — is not flaky, which
means the test either waits out the TTL or the TTL is configurable and the test
sets it to zero. Prefer the latter; a test that sleeps is a test that will be
made to sleep longer.

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
should meet them expecting them.

- **A large dependency graph in `epos-registry`.** Measured:
  `go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetricgrpc` at v1.44.0
  resolves to **21 modules / ~379 packages**, pulling gRPC, protobuf,
  `go.opentelemetry.io/proto/otlp`, `grpc-gateway/v2` and `genproto`. **The HTTP
  variant does not help**: `otlpmetrichttp` measures 21 modules / ~378 packages
  and still links gRPC for its status codes. Choose between them on
  firewall-friendliness, not on weight, and do not justify HTTP by claiming it is
  lighter — it is not.
- **A ClickHouse client in `epos`.** `clickhouse-go/v2` is ~16 modules, all pure
  Go. It links into the CLI, which today has none of them.
- **Two services to run for a real deployment**, plus a schema owned by an alpha
  upstream component (**D4b**).
- **Three SPEC amendments**, where the previous draft made none in this area:
  §5.3's exporter table gains an implemented `otlp` and its attribute list loses
  `client` (**D4c**); §13.4's package tree gains the new packages; §14 gains the
  catalog. **§4.4, §4.5, §5.1, §5.2 and §10.1 are still untouched** — the
  argument for §4.4 in particular is in **D4a** and is the reason this shape was
  chosen over the simpler-looking one.
- **`govulncheck` surface.** It is a required job and roughly forty new modules
  arrive at once. Expect to have to move a version.

**Rejected, and this is the one that looks cheaper than it is: writing rows to
ClickHouse directly from `epos-registry`.** It removes the collector and the
OTLP dependency graph. It also puts a database client on the request path of a
process specified to hold no state and to answer from any replica, invents and
migrates a schema epos would then own, and creates a second instrumentation path
beside the OTel SDK that §5.3 says there is one of. It would require amending
§4.4. Not taken.

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
EPOS_CATALOG_STATS_DSN=<the CI store> \
epos catalog export --base-path /epos/catalog --out catalog-dist \
                    --stats-source clickhouse
```

writing a directory of finished HTML, published to `gh-pages` under `catalog/`
and served at `https://gaarutyunov.github.io/epos/catalog/`.

**This is what the owner's review asks for, and it is worth naming the words.**

> We are hosting on GitHub pages. To achieve this we need to render real
> frontend during CI into a static website with SSR. During CI real catalog is
> rendered from markdown into html and server.

"Static website with SSR" is not a contradiction: it means the HTML is produced
by a server-side renderer *at build time* rather than by JavaScript in the
reader's browser. `epos catalog export` is exactly that renderer, and the
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
| `epos catalog serve` + `--stats-source clickhouse` | queried per request, short TTL (**D4e**) | **yes** — this is the mode the owner's e2e assertion describes, and it is tested there |
| the published Pages demo | queried once, during the export | **no** — they change when CI re-exports, which is asserted as a property rather than discovered |

**The residual gap, named.** Within one CI run the store is persistent in the
sense that matters technically — it outlives the `epos-registry` process, holds
history, and answers queries — but it does not outlive the *runner*. So the
demo's leaderboard shows one build's traffic, and the page says so. Making the
demo accumulate history across runs needs a ClickHouse that is always there, and
that is the same provisioning decision as a host for `serve`. It is question 2
for the owner, now sharpened: **one host with ClickHouse and `epos catalog
serve` on it turns the demo from a build's snapshot into a live catalog with
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
  with skills packed and pushed into it, `epos-registry` in front exporting
  OTLP, a collector and a ClickHouse (there is an official
  `testcontainers-go/modules/clickhouse`, v0.43.0, matching the
  testcontainers-go the module already has), `epos pull` driving the counter,
  and the rendered page asserted to carry the count that the store returns. This
  is the test that proves the whole chain, and the chain is the deliverable.
  Note that the collector's metrics support is alpha (**D4b**) — if it proves
  unusable, that is a finding for the owner about ClickHouse, not a licence to
  fall back to a hand-written store.
- **A hostile artifact**, pushed to the real registry: an oversized layer and a
  layer with a `..` entry. The catalog must still list it, its page must say the
  document could not be read, and no file may appear outside `--out` (**D3c**,
  **D3d**, **D12**).
- **A `--refs`-mode export against a registry with `_catalog` disabled**, so the
  ghcr case (**D3**, **D10**) is covered by a test and not by hope.
- **A new `features/` file**, since the features are canonical and never
  paraphrased into Go.
- **End-to-end, in a browser**: **D16**. It is a third tier, not a variation on
  the integration tier, because it needs a browser and the integration tier is
  required to run everywhere the unit tier does.
- **The docsgen drift gate** must be green after `epos catalog` joins the cobra
  tree (**D2**).

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
| `epos catalog serve` + a live stats source | read the count, `epos pull` the skill, reload, **the count has increased**. This is the owner's assertion, literally, and it is why `serve` reads counts per request (**D4e**) rather than at startup. |
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
   zot, `epos-registry`, a collector, ClickHouse and `epos catalog serve` turns
   that into a live catalog with accumulating history and **nothing else in this
   change has to change**. It needs infrastructure and a credential the
   repository has never had, so it is the owner's call and it is the biggest
   remaining gap between what shipped and what was asked for.
4. **`examples/go-house/`** — this change assumes epos#42 merges and supplies it
   (**D1**). If #42 is rejected, #44 needs a different example skill and loses
   the three capabilities the issue wants demonstrated.
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
