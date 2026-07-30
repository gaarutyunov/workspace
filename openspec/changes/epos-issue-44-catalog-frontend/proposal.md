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

Three of the issue's premises need correcting before any of it is buildable:

- **"show the download statistics"** — the counter exists
  (`internal/metrics/metrics.go`, `epos.downloads`, incremented by
  `cmd/epos-registry/handler.go`'s `countDownload`), but **nothing durable ever
  reads it**. `metrics.New` implements exactly two of the four exporters SPEC
  §5.3 names — `stdout` and `none` — and returns *"metrics exporter %q is not
  implemented"* for the rest. The counter survives only until the process exits.
  **A leaderboard has no data source today.** Design **D4** gives it one: the
  `otlp` exporter §5.3 already promised, pushing into ClickHouse, which the
  catalog queries.
- **"deploy a demo"** — the repo deploys exactly one thing: `docs/dist` to the
  `gh-pages` branch, from a workflow triggered on `docs/**` alone
  (`.github/workflows/docs.yml`). `.goreleaser.yaml` builds binaries and **no
  container image**. GitHub Pages cannot run a Go binary, and there is no host
  named anywhere in the repository. Design **D5** renders the real catalog to
  static HTML during CI and publishes that, and says plainly which half of
  "persistent metrics you can query on the catalog page" a static host can and
  cannot have.
- **"push to registry"** — this one has stopped being a problem since the issue
  was written. epos#43 merged (`6f7738a`), so `epos push` and `epos registry
  login` are on `origin/main` and the demo publishes with the CLI itself rather
  than delegating to `oras`. Design **D10** records the one thing a publish job
  still has to get right: there are two credential failures and they read
  differently.

And one thing the issue asks for could not be shown at all as things stood: an
artifact does not declare its parameters. `epos build` writes
`dev.epos.skillfile.stages`, `dev.epos.skillfile.digest` and the two
`org.opencontainers.image.base.*` annotations, and the config blob carries the
`SKILL.md` frontmatter — but nothing records which `{{ .Values.x }}` a skill
accepts or what it defaults to. **This change closes that gap** with a declared
values schema and a command that infers one from a skill's own templates
(design **D14**), which also supersedes epos#47's approach to the same subject.

## What Changes

- **`epos catalog serve` and `epos catalog export`** — one new subcommand tree on
  the existing `epos` binary, two modes over one renderer. `serve` runs a
  read-only HTTP server against a registry; `export` writes the same pages to a
  directory as static HTML. Both render server-side from Go templates. The
  browser gets vanilla JS for three things only: theme, client-side filtering of
  an already-delivered index, and clipboard. No framework, no bundler, no Node
  at build or serve time (design **D2**).
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
- **A persistent, queryable statistics store, and the exporter that fills it.**
  `epos-registry` gains the **`otlp`** exporter SPEC §5.3 already names —
  completing that section rather than amending it — pushing `epos.downloads`
  into an **OpenTelemetry Collector** whose `clickhouseexporter` writes to
  **ClickHouse**. The catalog reads counts through a one-method `Stats`
  interface with three implementations: `none` (the default — the column is
  absent, not zeroed), `clickhouse` (a SQL query), and `file` (a JSON document,
  for reproducible exports and tests). **`serve` reads counts per request**, so
  a pull followed by a reload shows a higher number; `export` queries once and
  bakes the answer in with its capture time (design **D4**). `epos-registry`
  still holds no durable state, still has one listener, and still never reads
  the store back — the persistence is on the far side of a one-way push, which
  is why SPEC §4.4 is untouched (**D4a**).
- **The user-agent stops being recorded.** `Download.Client` is the raw
  `User-Agent` — attacker-controlled, unbounded cardinality, one row group per
  distinct value per repository, forever, created by anyone who can issue a blob
  `GET`. It was harmless while the only exporter was stdout. With a store it is
  not, so it is removed by an SDK view rather than by convention, and SPEC
  §5.3's attribute list is amended (design **D4c**).
- **The leaderboard ranks verified downloads.** `Download.Verified` is true only
  when the request carried `Epos-Download`, which only `epos pull` sends. The
  unverified side is known-inflated — a cosign signature is a referrer in the
  skill's own repository, so every `epos verify` counts as a download of the
  skill it verifies, and the code says so at length. Ranking on the verified
  side is the one number the system can defend. skills.sh does exactly the same
  thing for the same reason: its counts come from its own CLI's telemetry, not
  from registry traffic (design **D4d**).
- **A values schema, and a command that infers it.** A skill may carry a
  `values.schema.json` — an OpenAPI 3.1 Schema Object, which is a JSON Schema
  2020-12 document — declaring the parameters it accepts, their types, defaults
  and required-ness, scoped per Skillfile stage the way the renderer already
  scopes values. It is validated at install, it types a `--set`, and
  `epos values schema` infers a first draft by walking a skill's template parse
  trees: string by default, boolean when a value gates a conditional, numeric
  when it is compared with a number literal (design **D14**). **Design D14d
  recommends this be delivered under epos#47 rather than here**, and says what
  happens under either answer; the catalog renders the contract when an artifact
  carries one and shows no parameter section when it does not.
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
  genuine security boundary; it is treated as one (design **D7**). The renderer
  is `github.com/yuin/goldmark` — CommonMark-compliant, pure Go, **zero
  dependencies**, raw HTML off by default — with `html/template` for the pages;
  design **D7a** records the whole shortlist, including why importing Hugo as a
  library (88 modules, 699 packages, a v0 API) is not a trade.
- **A tools page that is a capability table, not a logo wall.** The issue asks
  for "logos of registries that support OCI like zot and gitlab". An
  unqualified logo says *epos works here*, and epos's discovery needs
  `GET /v2/_catalog`, which several major registries do not implement — the code
  has `errNoCatalog` precisely because of it. Every entry carries what it was
  verified to support and how (design **D9**).
- **The demo is the real catalog, pre-rendered during CI and published to the
  existing Pages site** at `/epos/catalog/`, carrying `examples/go-house/` —
  epos#42's derived Go skill — packed by `epos pack` and published to
  `ghcr.io/gaarutyunov/skills/`. **A CI job simulates download traffic** through
  the whole chain — pack, push, pull through `epos-registry`, into the store —
  with a deliberately uneven distribution so the leaderboard ranks something,
  and the export queries the store and writes the numbers into the HTML with
  their capture time and window on the page (designs **D5**, **D15**).
- **End-to-end tests in a real browser, with `playwright-go`.** Navigation from
  every page, correct rendering of the leaderboard, the rendered document, the
  filter and the tools table, and — the assertion that forced the per-request
  count read — **pull a skill, refresh, watch the number move** against `serve`.
  Against the static export the opposite is asserted deliberately: the number
  does *not* move until CI re-exports, so the difference is a tested property
  rather than a production surprise (design **D16**). Two facts an implementer
  will otherwise lose a day to are recorded there: playwright-go's module path
  moved to `github.com/mxschmitt/playwright-go` at v0.6100.0, and it downloads a
  Node-based driver that must be pinned and cached.

## Capabilities

### New Capabilities

- `epos-catalog`: the `epos catalog` command, where its data comes from, the
  four pages and their routes, and what the tools page is allowed to claim.
- `epos-download-stats`: the persistent store and the exporter that fills it,
  the `Stats` source and its three implementations, when counts are read, the
  attribute that must never reach a store, and which side of the counter a
  leaderboard may rank on.
- `epos-catalog-assets`: embedding — the vendored ui-kit bundle, the embed tree,
  server-side Markdown rendering and its sanitisation, the JavaScript budget,
  and the dependency budget.
- `epos-catalog-demo`: the published example skill, the CI-generated traffic,
  the pre-rendered static export, where it is deployed, and the honesty
  requirements on the numbers it shows.
- `epos-catalog-e2e`: browser-driven coverage of navigation, rendering and the
  counts, in both modes, and the rule that the browser tooling stays out of the
  shipped binaries.
- `epos-values-schema`: the declared values contract, how it travels with the
  artifact, validation and defaulting at install, typed `--set`, the inference
  command and its rules, and the catalog's rendering of the contract.
  **Design D14d recommends this capability be delivered under epos#47**; it is
  specified here because the owner asked for it here, and only its last
  requirement is #44's under either answer.

### Modified Capabilities

<!-- epos predates OpenSpec: there is no capability spec under openspec/specs/
     to amend. SPEC.md is the project's own reference. This change amends:
     §5.3 (the otlp exporter becomes implemented; `client` leaves the attribute
     list — D4c), §13.4's package tree, §13.5/§13.6 (the end-to-end tier and its
     build tag), §14's site-surface and deployment sections, and — only if the
     values schema is delivered here rather than under epos#47 — §2.2 and §10.3.
     §4.4, §4.5, §5.1, §5.2 and §10.1 are deliberately left untouched, and D4a
     is the argument for why a persistent store does not disturb §4.4. -->

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
- **No write path on `epos-registry`, and no state in it.** SPEC §4.4, §4.5 and
  §10.1 stand: no write path, no rendering, no second listener, no durable
  state. The registry pushes measurements outward and never reads them back; the
  catalog is a `/v2/` client and is never served by the relay (design **D4a**).
- **No durable state in the catalog either.** The catalog queries the store and
  reads a counts file; it creates, alters and deletes nothing.
- **The published demo does not query the store from the browser.** Static
  hosting cannot hold a credential, an open SQL endpoint is a denial-of-service
  surface, and a page whose numbers arrive by `fetch` breaks two requirements
  this change already carries. The query runs at export time and the answer is
  in the HTML (design **D5a**).
- **No `prometheus` exporter.** SPEC §5.3 names it and it stays unimplemented: a
  scrape needs a second listener on `epos-registry`, which §10.1 forbids, and a
  scrape reaches one replica of a deployment specified as N behind a load
  balancer. Push is the shape that fits (design **D4a**).
- **No syntax highlighting in rendered documents.** `chroma` plus
  `goldmark-highlighting` is the right pairing and is not taken now: chroma
  embeds every lexer, and `goldmark-highlighting/v2` has never cut a semver tag.
  Fenced code renders as `<pre><code>` from the kit's tokens (design **D7a**).
- **No time series on the page.** The store keeps history, so a sparkline is now
  possible rather than impossible — but `Stats` returns totals and the kit's
  chart component draws no data by design. A follow-up with a real basis
  (design **D8**).
- **The documentation site is not ported to Go.** Astro still builds `docs/`.
  This change renders the catalog; reading the review's "render during CI" as a
  mandate to rewrite the docs site would be inventing scope (design **D7a**).
- **No search backend, no accounts, no publishing UI, no audits.** skills.sh has
  security-audit integrations, editorial picks, topic taxonomies and an
  authenticated JSON API. None of that is asked for and none of it is here.
