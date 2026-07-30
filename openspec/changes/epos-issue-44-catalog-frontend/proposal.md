## Why

epos can pack a skill, publish it and pull it back, and it has an OTel counter
that increments on every content blob it serves. What it has never had is a way
to *look at* any of that. `epos list` and `epos search` print rows to a
terminal; the docs site at `https://gaarutyunov.github.io/epos/` describes the
CLI and nothing else. There is no page anywhere that shows what a registry
holds, what a skill's `SKILL.md` says, or how often anything has been pulled.

epos#44 asks for that page — a catalog frontend in the shape of skills.sh,
styled like garutyunov.com, built from `gaarutyunov/ui-kit` and vanilla JS,
embedded into the Go binary — plus a deployed demo carrying a real skill that
epos itself packed.

Three of the issue's premises need correcting before any of it is buildable,
and one of them changes the deliverable:

- **"show the download statistics"** — the counter exists
  (`internal/metrics/metrics.go`, `epos.downloads`, incremented by
  `cmd/epos-registry/handler.go`'s `countDownload`), but **nothing durable ever
  reads it**. `metrics.New` implements exactly two exporters, `stdout` and
  `none`, and returns *"metrics exporter %q is not implemented"* for anything
  else. SPEC §4.4 forbids `epos-registry` from holding state, so the counter
  survives only until the process exits. **A leaderboard has no data source
  today.** Design **D4** closes this with the smallest thing that is honest —
  and deliberately does *not* build a telemetry stack to do it.
- **"deploy a demo"** — the repo deploys exactly one thing: `docs/dist` to the
  `gh-pages` branch, from a workflow triggered on `docs/**` alone
  (`.github/workflows/docs.yml`). `.goreleaser.yaml` builds binaries and **no
  container image**. GitHub Pages cannot run a Go binary, and there is no host
  named anywhere in the repository. Design **D5** picks the deployment that the
  repo can actually reach today and says plainly what it costs.
- **"push to registry"** — publishing is `oras cp` today. `epos push` exists on
  a branch (epos#43, CI-green, unmerged). Design **D10** keeps #44 off that
  gate.

And one thing the issue asks for cannot be shown at all as things stand: an
artifact does not declare its parameters. `epos build` writes
`dev.epos.skillfile.stages`, `dev.epos.skillfile.digest` and the two
`org.opencontainers.image.base.*` annotations, and the config blob carries the
`SKILL.md` frontmatter — but nothing records which `{{ .Values.x }}` a skill
accepts or what they default to. Design **D11** says what the catalog shows
instead, and why that is the better demonstration anyway.

## What Changes

- **`epos catalog serve` and `epos catalog export`** — one new subcommand tree on
  the existing `epos` binary, two modes over one renderer. `serve` runs a
  read-only HTTP server against a registry; `export` writes the same pages to a
  directory as static HTML. Both render server-side from Go templates. The
  browser gets vanilla JS for three things only: theme, client-side filtering of
  an already-delivered index, and clipboard. No framework, no bundler, no Node
  at serve time (design **D2**).
- **Four page shapes, in skills.sh's information architecture** — a home page
  that *is* the leaderboard, a catalog list, a skill detail page whose body is
  the rendered `SKILL.md`, and a tools page. skills.sh's home is a ranked table
  with `#` / `Skill` / activity / `Installs`; its detail page is a 9/3 split with
  the readme in the main column and installs, repository and first-seen in the
  aside. Both shapes are adopted; both are also, independently, the shape
  epos#42's design **D3** already measured off garutyunov.com's CV page —
  `max-w-6xl` (1152px), `px-4 sm:px-6 lg:px-8`, a 9/3 grid, mono section labels,
  breadcrumbs. **The two references agree**, which is the reason this is one
  design and not a negotiation (design **D8**).
- **The download counter finally reaches a page, without a telemetry stack.**
  The catalog reads counts through a `Stats` source with two implementations:
  `none` (the default — the column is absent, not zeroed) and `snapshot` (a JSON
  file of per-repository counts, captured at a stated moment). The snapshot is
  produced by running the real chain — pack, publish, pull, read the counter —
  through the exporter `epos-registry` already has, parsed the way
  `tests/integration/steps_counting.go` already parses it. **No new exporter, no
  scrape loop, no Prometheus, no second listener, and not one byte of new state
  in `epos-registry`** (design **D4**). A live-counts deployment is a named
  follow-up behind the same one-method interface, and design **D4e** records
  exactly what it costs.
- **The leaderboard ranks verified downloads.** `Download.Verified` is true only
  when the request carried `Epos-Download`, which only `epos pull` sends. The
  unverified side is known-inflated — a cosign signature is a referrer in the
  skill's own repository, so every `epos verify` counts as a download of the
  skill it verifies, and the code says so at length. Ranking on the verified
  side is the one number the system can defend. skills.sh does exactly the same
  thing for the same reason: its counts come from its own CLI's telemetry, not
  from registry traffic (design **D4c**).
- **ui-kit is vendored as a built release bundle and embedded.**
  `internal/catalog/assets/vendor/ui-kit/{ga-ui-kit.min.js,ga-ui-kit.css,LICENSE,VERSION}`
  — 104 KB of it the two files the browser loads, zero runtime network,
  committed, refreshed by a script.
  The kit's GitHub Packages publication needs a PAT even when public, which is
  why `docs/vendor/ui-kit/VENDORED.md` already vendors it; but the **Release
  assets are anonymously downloadable** (verified: `curl` against
  `releases/latest/download/…` returns 200 with no token), which the docs
  vendoring predates and which makes the bundle the better artifact to pin
  (design **D6**).
- **`SKILL.md` is rendered in Go, with raw HTML off and the output sanitised.**
  A skill's `SKILL.md` arrives from a registry and is authored by whoever
  published it. Rendering it into the catalog's own origin is the change's one
  genuine security boundary; it is treated as one (design **D7**).
- **A tools page that is a capability table, not a logo wall.** The issue asks
  for "logos of registries that support OCI like zot and gitlab". An
  unqualified logo says *epos works here*, and epos's discovery needs
  `GET /v2/_catalog`, which several major registries do not implement — the code
  has `errNoCatalog` precisely because of it. Every entry carries what it was
  verified to support and how (design **D9**).
- **The demo is a static export published to the existing Pages site**, at
  `/epos/catalog/`, carrying `examples/go-house/` — epos#42's derived Go skill —
  packed by `epos pack` and published to `ghcr.io/gaarutyunov/skills/`. Its
  download numbers come from a snapshot that a CI job produces by running the
  real pipeline end to end against an ephemeral zot and `epos-registry`, and the
  page states their provenance rather than implying a global popularity it does
  not have (design **D5**).

## Capabilities

### New Capabilities

- `epos-catalog`: the `epos catalog` command, where its data comes from, the
  four pages and their routes, and what the tools page is allowed to claim.
- `epos-download-stats`: the `Stats` source and its two implementations, the
  snapshot file's shape and where it comes from, and which side of the counter a
  leaderboard may rank on.
- `epos-catalog-assets`: embedding — the vendored ui-kit bundle, the embed tree,
  server-side Markdown rendering and its sanitisation, and the JavaScript budget.
- `epos-catalog-demo`: the published example skill, the static export, where it
  is deployed, and the honesty requirements on the numbers it shows.

### Modified Capabilities

<!-- epos predates OpenSpec: there is no capability spec under openspec/specs/
     to amend. SPEC.md is the project's own reference; §13.4's package tree and
     §14's site-surface and deployment sections are amended by this change, as
     recorded in the epos-catalog and epos-catalog-demo deltas. §4.4, §4.5,
     §5.1, §5.2, §5.3 and §10.1 are deliberately left untouched. -->

## Non-goals

- **No Skillfile, no quick start, no landing page.** epos#42 owns
  `examples/go-house/`, the landing, the docs shell and the `EPOS` wordmark, and
  its design **D1** drew the line: *"#44 keeps the catalog frontend, the `epos
  pack`/publish of that example to the demo registry, and the
  leaderboard/downloads UI."* That line is honoured here without amendment. The
  parametrisation, the spf13/`golang-pro` drops, the removed Viper half and the
  Go-only testcontainers slice — everything the #44 issue lists under "show all
  the capabilities" — is #42's artifact. #44 packs it, publishes it and displays
  it (design **D1**).
- **No `epos push` dependency.** #44 does not block on epos#43. The publish step
  is one line of a CI workflow and is written to be either command (design
  **D10**).
- **No change to `epos-registry` at all.** SPEC §4.5 and §10.1 stand: no write
  path, no rendering, no second listener. The catalog is a `/v2/` client and
  nothing more; it is never served by the relay.
- **No durable state anywhere.** SPEC §4.4 is not amended, and the catalog is
  stateless too: the snapshot is an input file, not a store the catalog writes.
- **No new metrics exporter and no metrics listener.** SPEC §5.3 names
  `prometheus` and `otlp`; neither is implemented here. Shipping an exporter
  whose only consumer is one CI job is how unused code and unwanted dependency
  trees arrive — design **D4e** shows the working, `curl`-free alternative that
  the repository's integration suite already uses.
- **No live download counts.** Design **D4e** states plainly what this costs and
  what it would take to add.
- **No search backend, no accounts, no publishing UI, no audits.** skills.sh has
  security-audit integrations, editorial picks, topic taxonomies and an
  authenticated JSON API. None of that is asked for and none of it is here.
- **No general values/parameters view.** The artifact does not declare its
  parameters and this change does not add a builder annotation to make it
  (design **D11**).
