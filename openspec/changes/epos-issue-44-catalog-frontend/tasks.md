## 1. Verify the claims the change rests on

Sequenced first because each was read from code or measured from outside, and
each would invalidate later work if wrong. All cheap; all expensive to discover
late.

- [ ] 1.1 Confirm the manifest carries everything the list pages need in **one** GET: fetch a packed skill's manifest and check that `config.data` is present and decodes to the full `SKILL.md` frontmatter, and that `org.opencontainers.image.title`/`.description` are on the manifest annotations. `internal/artifact/build.go` says so in a comment — verify it against a real registry, because design **D3** spends the whole list page on it.
- [ ] 1.2 Confirm `dev.epos.skillfile.stages` decodes to a **file path → stage name** map on a skill built by `epos build` (`provenanceFor`, `internal/cli/build.go:193`), and confirm it is **absent** on a skill produced by `epos pack`. Design **D11** builds the detail page's provenance table on this and nothing else.
- [ ] 1.3 Confirm `SKILL.md` cannot be fetched without the whole layer: check the content layer is a single gzipped tar and that no registry range request can yield one entry. If a cheaper path exists, take it and revise **D3**'s caching note.
- [ ] 1.4 Establish `_catalog` support empirically for every registry that will appear on the tools page, starting with `ghcr.io` and GitLab's container registry. Record the HTTP status each returns and whether it is authentication-dependent. This is the evidence for the tools page's capability column (**D9**) and it decides whether the demo can use namespace mode at all (**D3**, **D10**).
- [ ] 1.5 Confirm the stdout exporter's output can be read for a snapshot outside a Go test: run `epos-registry --metrics.exporter stdout --metrics.interval …`, drive a pull, stop it, and confirm the final flush lands and carries `repository` and `verified`. `tests/integration/steps_counting.go` already parses this shape (cumulative, last-export-wins) — reuse its parsing rather than re-deriving it. **D4a** rests entirely on this.
- [ ] 1.6 Decide the ui-kit version (**D6a**) — this is question 1 to the owner and it is the same question bikelanes#4 is parked on. Nothing else in the change depends on the answer; only whether the stat tile is `ga-metric` or fifteen lines of CSS.
- [ ] 1.7 Confirm `epos install`'s agent targets are what **D9** says: `install.DefaultBasePath` is the single default and every other target arrives through the worktree manifest's additional base paths. The agents table is written by hand against this, not derived — task 8.6 depends on knowing which.

## 2. `internal/registry` — lift discovery out of `internal/cli`

Before the catalog, because the catalog consumes it and a move mixed into new
code is a move nobody can review.

- [ ] 2.1 Move `registryClient`, `ociRegistry`, `newOCIRegistry`, `discover`, `skill`, `matches`, `withinNamespace`, `unsupported` and `errNoCatalog` from `internal/cli/discover.go` to a new `internal/registry` package, exported. Move the tests and the mockgen directive with them.
- [ ] 2.1a **`registryOptions` does not move** (**D2**). It lives in `internal/cli/credentials.go`, carries the cobra flag binding and the Docker credential store, and is shared by `pull`, `push`, `build`, `sign` and `install`. `internal/registry` defines its own plain options struct — plain-HTTP, a credential resolver, a client — with no cobra and no koanf in it; `internal/cli` builds one from `registryOptions`. Keep `explain`/`explainAuth`'s messages identical: they are the user-facing text for an auth failure.
- [ ] 2.2 `internal/cli/list.go` and `search.go` call into the new package. **Assert byte-identical output**: the godog features covering `epos list` and `epos search` must pass unchanged, and their expected output must not be edited in this task. If it has to be, the move was not a move.
- [ ] 2.3 Export the remote fetch-and-unpack routine the detail page needs. It is **`skillfile.fetchOCIBase`** — resolve, fetch the manifest, assert exactly one layer, fetch it, untar into a `Tree` (**D3c**). Not `install.read`, which reads the *local store*; not `ociTreeFiles`, which takes bytes already in hand. Whatever is exported keeps `checkPath`, the symlink/hardlink rejection and the 64 MiB cap — the catalog points at arbitrary registries, so the exposure is larger than the Skillfile `FROM` this was written for, not smaller.

## 3. Statistics — the source and the snapshot

Before the frontend, because a leaderboard with nothing behind it is the thing
this change exists to avoid. **Read design D4e before starting**: an earlier
draft implemented a Prometheus exporter, a metrics listener and a scrape poller
here, and all three were cut. Do not reintroduce them.

- [ ] 3.1 `Stats` — one context-taking method returning a `Snapshot` (`CapturedAt`, and per-repository `Verified`/`Unverified`). One type serves as both the on-disk JSON shape and the in-memory shape, so there is no converter and no second schema (**D4d**).
- [ ] 3.2 `none` — the default. The pull column is **absent**, not zero; the leaderboard falls back to a stated deterministic order. Test that the rendered page contains no count column at all.
- [ ] 3.3 `snapshot` — read and validate the JSON. A malformed file is rejected whole with the filename in the error, never half-read into partial counts.
- [ ] 3.4 A failing source degrades: every page still serves, counts go absent, the failure is logged, nothing renders as zero. Test with a missing file and with a truncated one.
- [ ] 3.5 Unknown ≠ zero. A skill with no row renders as unknown. This is a rendering rule as much as a data one; assert it in the renderer test.

## 4. Statistics — producing the snapshot

- [ ] 4.1 The snapshot *producer*: read the counter out of `epos-registry`'s stdout export (task 1.5) and write the `Snapshot` JSON. Aggregate over `client` rather than keying on it (**D4b**). Keep it small and keep it in the CI job's own tooling — this is not a new `epos` command, and a growing one is the signal that **D4e** is being relitigated.
- [ ] 4.2 Stop the registry before reading the final value: the shutdown flush is what makes the last interval's counts land, and skipping it silently loses them.
- [ ] 4.3 **No changes to `internal/metrics` and no changes to `cmd/epos-registry`.** If a diff appears in either, stop: the design says the counter already has a readable output, and if it does not, that is a finding for the owner rather than an exporter to write.

## 5. `internal/catalog` — the model and the renderer

- [ ] 5.1 The model: what a page needs, built from a manifest, its inline config, its provenance annotations and (for a detail page) its content layer. **One entry per repository, not per version** (**D3a**) — the counter's only key is the repository. No registry types in the template data; the renderer must be testable with a literal.
- [ ] 5.2 The route table, shared by both drivers (**D2**): home (leaderboard), catalog list, skill detail, tools. `export` walks it; `serve` serves it. One test asserts the two produce identical bytes **for the same base path and model**, and a second asserts a different base path changes only the prefix (**D2b**).
- [ ] 5.3 `html/template` for every page. Server-rendered; the browser receives HTML. Rendered Markdown enters as pre-sanitised HTML from task 6, at one place — do not scatter `template.HTML` through the templates.
- [ ] 5.4 The detail-page cache: keyed on manifest digest, which is immutable, so there is no invalidation path to get wrong. Bound it.
- [ ] 5.5 A skill whose layer cannot be read, is oversized, or is hostile still lists, and its detail page says the document could not be read. Do not fail the catalog for one bad artifact — that is a page an attacker can take the site down with.
- [ ] 5.7 `serve` answers only for repositories in the index built at startup; anything else is a 404 with no registry request (**D3b**). Without this the catalog is a fetch-anything proxy wearing a UI. Say in the command's help that the index is fixed until restart.
- [ ] 5.8 Thread `context.Context` through the model build, every registry fetch, `Stats.Pulls` and both drivers. `serve` gives each request-scoped layer fetch its own timeout; `export` runs under one deadline (**D12**). Retrofitting this later means changing every signature.
- [ ] 5.6 The provenance section from `dev.epos.skillfile.stages` (task 1.2): files grouped by contributing stage, plus base name/digest and Skillfile digest. Omit the whole section when the annotation is absent — an empty provenance table is worse than none.

## 6. Markdown — the security boundary

Written as its own section because design **D7** is the one place in this change
where getting it wrong is not a cosmetic defect.

- [ ] 6.1 Add `github.com/yuin/goldmark` — the **only** module this change adds. Pure Go, no cgo (SPEC §1.2). Confirm `govulncheck` stays green; it is a required CI job. If a second module appears in `go.mod`, stop and re-read **D4e**.
- [ ] 6.2 Render with raw HTML **off** (goldmark's default; the requirement is that it stays off and that a test proves it) and constrain link, image and autolink schemes to `http`, `https`, `mailto` and relative, **as an AST transformer** — before any HTML string exists (**D7**). Note that a `javascript:` or `data:text/html` Markdown link is **not** raw HTML and survives "disable raw HTML"; it must be defanged explicitly. Do not hand-write an HTML sanitiser.
- [ ] 6.3 Strip the frontmatter before rendering. `artifact.ParseFrontmatter` already finds its extent; the body starts after it.
- [ ] 6.4 Resolve relative links to something the catalog can serve or render them inert. Never to an unrelated catalog route.
- [ ] 6.5 A hostile fixture corpus, asserted: raw `<script>`, an `<img onerror>`, an inline SVG with a handler, an `<iframe>`, a `javascript:` link, a `data:text/html` image, and a document that is nothing but frontmatter. Each asserts on the **rendered output**, so a later configuration change that re-enables passthrough fails the build.
- [ ] 6.6 Assert the expressive path too — headings, nested lists, tables, fenced code, blockquotes, ordinary links all render. A sanitiser that eats the content is a different bug with the same cause.

## 7. Assets — vendoring and embedding

- [ ] 7.1 `internal/catalog/assets/vendor/ui-kit/` with `ga-ui-kit.min.js`, `ga-ui-kit.css`, `LICENSE` and `VERSION` from the pinned release (**D6**). Confirm again at commit time that the release assets download anonymously — the whole no-secret argument rests on it.
- [ ] 7.2 A refresh script (`make update-ui-kit` or a small `tools/` program) that downloads the assets for a given tag and rewrites the files. It is run by a human; it is **not** a build step. Document it beside the vendored files the way `docs/vendor/ui-kit/VENDORED.md` documents its own.
- [ ] 7.3 `//go:embed` the assets tree. This is the repository's **first** `go:embed` — check `.gitattributes`/`.gitignore` do not exclude anything under it, and check goreleaser's `CGO_ENABLED=0` cross-builds still produce a working binary on all six targets.
- [ ] 7.4 `app.css` — page furniture the kit deliberately does not provide: the grid, the footer, the prose container for rendered documents, and the leaderboard row density. Every value from a `--ga-*` token; no literal colours. Note the tokens' known trap from epos#42 task 3.3: `--ga-fg-muted` **does not exist**, the token is `--ga-muted`.
- [ ] 7.5 `app.js` — three behaviours only (**D6**/assets delta): filter the delivered index, copy to clipboard, theme. No fetching, no routing, no templating. Assert every page works with scripting off.
- [ ] 7.6 The stat tile: `ga-metric` if task 1.6 says v0.4.0, otherwise fifteen lines in `app.css` with a comment naming the released version that lacked it, so the follow-up is findable.
- [ ] 7.7 Registry and agent logos as embedded SVG, each with its source and licence recorded (**D9**). Any mark whose terms do not permit referential use becomes a text row — decide per logo, do not commit first and check later.

## 8. The pages

- [ ] 8.1 The shell: the docs site's container and gutters (1152px, `px-4 sm:px-6 lg:px-8`), the 56px sticky header, breadcrumbs on every inner page with `aria-label`/`aria-current`, the 9/3 grid on detail pages. This is epos#42's design **D3** applied to Go templates instead of Astro — reuse the measurements, do not re-derive them.
- [ ] 8.2 The `EPOS` wordmark from **one** shared asset (**D8**). If epos#42 has merged, consume its file. If not, create the asset at a path #42 can consume and say so in the pull request, because whoever lands second adopts rather than copies.
- [ ] 8.3 Home = leaderboard. Columns `#` / `Skill` / `Pulls`, the whole row an `<a>`, rank and count monospace and right-aligned, name over `owner/repo`. Views as navigation, not a dropdown. Taken from skills.sh's home; the sparkline column is deliberately **not** taken, because no time series exists (**D4d**).
- [ ] 8.4 Catalog list with the client-side filter over the delivered index. Works with scripting off, minus the filter.
- [ ] 8.5 Detail page: breadcrumb, title, tags; main column = rendered `SKILL.md`; aside = pulls, repository, version, licence (from frontmatter), and the provenance block. A copyable install command as a full-width control, skills.sh's shape.
- [ ] 8.6 Tools page: two sections, Registries and Agents. Each registry row carries pull / push / `_catalog` status and how it was verified (**D9**, task 1.4). **The agents list cannot be derived from the code** — `install.DefaultBasePath` is the one default and everything else comes from the user's manifest (task 1.7). Write it as a checked-in table where each row names the agent's skill directory and whether epos installs there by default; that is verifiable, which a positioning blurb is not.
- [ ] 8.7 Dark only, matching both references. No theme toggle beyond the token-level `data-theme` the kit already supports.

## 9. The command

- [ ] 9.1 `epos catalog serve` and `epos catalog export` under a `catalog` parent (**D2**), each a factory returning `*cobra.Command`, registered in `NewRootCommand`, `RunE` not `Run`, `cobra.NoArgs` on all three, output through `cmd.OutOrStdout()`. Flags, **kebab-case and flags-only — no koanf, no env prefix** (**D2a**): `--registry`, `--namespace`, `--refs`, `--plain-http`, `--base-path`, `--stats-source`, `--stats-file`, plus `--addr` on serve and `--out` on export.
- [ ] 9.2 `--namespace` and `--refs` are mutually exclusive and one is required — checked before any network request. A `--namespace` sweep against a registry without `_catalog` **fails**, naming the registry; it does not fall back (**D3**).
- [ ] 9.3 A `--refs` entry that cannot be resolved is named in the error. Do not emit a site that silently omits a skill.
- [ ] 9.3a `--out` semantics (**D12**): create the directory if absent; refuse an existing directory that is not recognisably a previous export's output; prune pages this export did not write; verify every written path resolves under `--out` before writing, because route paths come from registry-supplied repository names. Never recursively delete a directory a human named.
- [ ] 9.4 `serve` shuts down gracefully on signal, the way `cmd/epos-registry/main.go` already does — `signal.NotifyContext`, `srv.Shutdown`, a `ReadHeaderTimeout`. A server without one is the kind of omission that only shows up in a container.
- [ ] 9.5 Regenerate `docs/src/pages/cli.astro` and commit it — the CI drift gate fails otherwise (**D2**). Do not hand-edit the `.astro`.
- [ ] 9.6 Check whether `internal/docsgen/cli.go`'s hand-written prose sections need a sentence about the catalog. They are prose, so the drift gate cannot catch a stale one.
- [ ] 9.7 `SPEC.md`: add the new packages to §13.4's package tree, and record the catalog in §14's site-surface and deployment sections. **Nothing else** — §4.4, §4.5, §5.1, §5.2, §5.3 and §10.1 are untouched by this change and the edit should say so, so a later reader does not go looking for an amendment that was deliberately not made.

## 10. The demo

Sequenced last because 10.2 depends on epos#42 merging (**D1**). Everything above
this section is independent of it.

- [ ] 10.1 A `--refs` file for the demo, checked in, listing the skills the demo publishes. More than one skill, so the leaderboard, the list page and the filter are exercised and not merely present.
- [ ] 10.2 A workflow that packs `examples/go-house/` with `epos pack` and publishes it with `epos registry login ghcr.io --password-stdin` + `epos push go-house:<version> oci://ghcr.io/gaarutyunov/skills` (**D10** — epos#43 merged, `6f7738a`, so no `oras` anywhere). `GITHUB_TOKEN` is sufficient and **no new secret is needed — but the job needs `permissions: packages: write`**; `ci.yml` declares `contents: read`, so the default is not enough. **Blocked until epos#42 merges** — that is the only task in this change that is.
- [ ] 10.2a Do not collapse the two credential failures. `auth.ErrBasicCredentialNotFound` fails locally and never reaches the registry ("no credential is stored"); a wrong or expired credential returns a real 401 ("the stored credential was rejected"). A missing `packages: write` shows up as the **401**, so a job that reports every failure as "log in" sends the next person to re-run a login that already worked. Surface the CLI's message as it comes (**D10**).
- [ ] 10.3 A snapshot job: stand up zot and `epos-registry` the way `ci.yml`'s conformance job already does (`--metrics.exporter stdout`), publish the demo skills, pull each through `epos pull`, **stop the registry so the final flush lands**, read the counter from its stdout, write the snapshot JSON, commit or upload it. The numbers are small and real; nothing is seeded (**D4a**, **D5**).
- [ ] 10.4 An export job running `epos catalog export --base-path /epos/catalog --out catalog-dist` and publishing to `gh-pages` with **`destination_dir: catalog`**. Three traps, all silent (**D5**): the output directory must **not** be under `docs/dist`, which Astro clears; `publish_dir` without `destination_dir` overwrites the docs' root `index.html` and `keep_files: true` does not protect a same-named file; and the job must join `docs.yml`'s `concurrency: {group: docs}` or the two force-pushes race and both report success. **Fix the trigger too**: `docs.yml` fires on `docs/**` only, so a Go-driven catalog change would never deploy.
- [ ] 10.4a After the first deploy, open the docs site's own entry page and confirm it is still served. None of 10.4's failure modes fails the workflow.
- [ ] 10.5 The provenance line on the demo's leaderboard: what the counts are, that they come from the project's own pipeline, and when they were captured. This is a page requirement, not a footnote in the repository.
- [ ] 10.6 Link the catalog from the docs landing, and the docs from the catalog header.

## 11. Tests

- [ ] 11.1 A new `features/` file for the catalog — the features at the repository root are canonical and are never paraphrased into Go (SPEC §13.3).
- [ ] 11.2 Unit, no Docker and no network (SPEC §13.5): the renderer over a literal model for all four pages and both drivers, at two base paths; the Markdown corpus, hostile and expressive (tasks 6.5, 6.6); snapshot parsing including a malformed file and a repository with no row; `--refs` parsing; the export path-containment check against a hostile repository name; the unknown-vs-zero rule.
- [ ] 11.3 Integration, `//go:build integration`, real containers (SPEC §13.2 — no fakes, no in-memory registry): pack → push → `epos-registry` in front of zot → `epos pull` → read the counter from the registry's stdout export → render → assert the count on the page. This is the only test that covers the whole chain, and the chain is the deliverable.
- [ ] 11.4 An export in `--refs` mode against a registry with catalog enumeration unavailable, so the ghcr case is covered by a test rather than by hope (**D3**, **D10**).
- [ ] 11.4a A hostile artifact pushed to the real registry — an oversized layer and one with a traversing entry. The catalog lists it, its page says the document could not be read, no file lands outside `--out`, and the process survives (**D3c**, **D3d**, **D12**).
- [ ] 11.5 Reuse the pinned zot image already in `tests/integration/registry_read_path_test.go`; add no second registry image.
- [ ] 11.6 CI stays green end to end: `gofmt`, `go vet`, the docsgen drift gate, golangci-lint, `go test -race ./...` on three OSes, integration, conformance, `govulncheck`. The Windows unit run is the one that most often surprises an `embed.FS` change — check the embedded paths use forward slashes.

## 12. Follow-ups to file, not to do here

- [ ] 12.1 A builder annotation declaring a skill's parameters, so a catalog can render them (**D11**). Belongs to the builder and overlaps epos#47.
- [ ] 12.2 Raise `docs/vendor/ui-kit` from v0.2.0 to the release this change pins, so the repository holds one vendored kit instead of two (**D6**). Held back only because epos#42 is in review against v0.2.0.
- [ ] 12.3 Live download counts: a `promql` statistics source behind the same one-method interface, and the `prometheus` exporter it needs on `epos-registry` — with `client` dropped from that exporter's attributes. **D4e** has the full sizing and the reasons it is not here.
- [ ] 12.4 A container image target in `.goreleaser.yaml`, if the owner wants the live demo rather than the static one (**D5**).
- [ ] 12.5 The kit's own docs recommend `https://esm.sh/@gaarutyunov/ui-kit`, which 404s because the package is not on public npm. That is a ui-kit issue, found here.
