## 1. Verify the two claims the whole change rests on

Sequenced first because both were read from the code and both would invalidate
later tasks if wrong. Cheap to check, expensive to discover late.

- [ ] 1.1 Confirm `--set x=false` leaves the feature **on**: build any skill with a `{{ if .Values.x }}` guard, install with `--set x=false`, and observe the guarded section present. Then confirm `--set x=` and a YAML `x: false` both leave it absent.
- [ ] 1.2 Confirm a git `FROM` against `gaarutyunov/workspace` resolves a skill subdirectory: `FROM git+https://github.com/gaarutyunov/workspace#<ref>:.agents/skills/go-project-scaffold` builds. If the repository is private to the token in play, this is where it surfaces — and it is the D1 assumption that lets #42 proceed without #44.
- [ ] 1.3 Confirm the stage-scope hazard is real: a file brought in by `COPY --from=pro` that contains `{{ .Values.foo }}` must be given `pro.foo`, not top-level `foo`. Note the exact failure message so the quick start can quote it if useful.

## 2. `examples/go-house/` — the recipe, before anything documents it

Written before the quick start because the page quotes this file. Writing the
page first means writing prose about a build nobody has run.

- [ ] 2.1 `examples/go-house/Skillfile` — four stages: `idiomatic` (spf13 `go`), `pro` (`golang-pro`), `containers` (`testcontainers-go`), and an unnamed final stage continuing from `go-project-scaffold`. Pin every git source to a tag or SHA (design D5).
- [ ] 2.2 The `idiomatic` stage: strip the "modern stdlib / current syntax" range and the debugging essay from the 774-line `SKILL.md` with `AWK` on section boundaries — **not** `PATCH` (design D5). Land the remainder as `references/idiomatic-go.md`, whose layout section is inside the stripped range (design D6 — this is what keeps the example out of the `internal/` argument).
- [ ] 2.3 The `pro` stage: `RM references/generics.md`, `RM references/project-structure.md`, and `AWK` out `interfaces.md`'s "Interface Satisfaction Verification" section and `concurrency.md`'s static worker pool. Each drop is a named conflict, not a length cut — keep the attributions where a reader of the Skillfile can see them.
- [ ] 2.4 The `containers` stage: `COPY --from=containers` only the Go example file(s) the profile needs.
- [ ] 2.5 Final stage: `SET name go-house`, `SET version …` (none of the three sources has a top-level `version` for the packer to use), then `AWK` the fixed `## Non-negotiable` block out and `APPEND` a parameterised replacement guarded on `{{ if .Values.openapi }}`, `di`, `telemetry`, `testcontainers`, plus one **string** parameter so both parameter shapes appear. Configuration stays fixed at koanf — it is a standing preference, not a per-project axis.
- [ ] 2.6 `values-service.yaml` (everything on) and `values-library.yaml` (the single-purpose-library case the scaffold skill names). **YAML booleans**, and supply values for every stage scope the copied files need (task 1.3).
- [ ] 2.7 A `//go:build integration` test that builds the Skillfile with the real builder and installs it under **both** profiles, asserting the guarded sections present under one and absent under the other. Assert the missing-value failure too.
- [ ] 2.8 Check the resulting skill reads as **one** skill: one entry document routing to its references, and no two surviving references opposed on the same question. This is the acceptance criterion the issue actually cares about, and no test will catch it.

## 3. `Base.astro` — the layout, before the pages that use it

- [ ] 3.1 `width?: "prose" | "wide"` prop, default `"prose"`. Only `index.astro` passes `"wide"` (design D3). Do **not** touch the generated pages' `<Base …>` call — that lives in `internal/docsgen/page.go`.
- [ ] 3.2 Global spacing for the kit's block components — `ga-note`, `ga-code`, `ga-card` — from the spacing tokens. This is the single-point fix for "notes are stuck to each other": the component sets `:host { display: block }` and `.note { margin: 0 }`, and no page supplies a margin.
- [ ] 3.3 Token corrections: `--ga-fg-muted` → `--ga-muted` (the former does not exist, so every muted string on the site is currently the `#a1a1a1` fallback), accent fallback `#3b82f6` → `#54a2ff`, and adopt `--ga-font-sans` / `--ga-font-mono` in place of the hand-written system stack.
- [ ] 3.4 Shared furniture: the back link, the footer and the section-label pattern, all currently duplicated across four pages.
- [ ] 3.5 Remove `quickstart.astro`'s local `ga-code { margin-bottom: 0.75rem }` so it does not fight 3.2.

## 4. The landing

- [ ] 4.1 ASCII `EPOS` wordmark: `<pre>` with `aria-label`, `--ga-font-display`, negative tracking and tight leading, `select-none`, scaling down at small viewports. #44 wants the same lettering for the catalog, so build it as something reusable rather than inline art.
- [ ] 4.2 The hero band: two-column `[auto 1fr]`, wordmark left, **one** balanced muted sentence right, `sr-only` `<h1>`, stacking below the large breakpoint. **No buttons** (design D2a).
- [ ] 4.3 The install band: mono uppercase section label over `ga-code prompt="$"`, with the quick-start and reference links directly beneath — the two `ga-button`s move up from the page footer.
- [ ] 4.4 Six feature cards: 1/2/3 columns, 16px gap, border-only over a low-alpha fill, colour-only hover. Each card is a capability in the shipped CLI or the shipped instruction set. **Check every card against `SPEC.md` for a withdrawn capability** — no write path, no `push`, no native discovery, no Kubernetes installer, no download statistics.
- [ ] 4.5 Cut the three Skillfile-mechanics sections. Before deleting each, confirm its information is on the quick start or the reference — or that it was a claim the code does not support.
- [ ] 4.6 Confirm nothing above the feature list says "Skillfile", "layer", "manifest" or "digest".

## 5. The quick start

- [ ] 5.1 Rewrite to **≤ 700 words** of prose (from ~2480). Delete the "What you need" preamble outright — a reader who needs *registry*, *digest* and *OCI* defined is not the audience for a quick start.
- [ ] 5.2 Path A, **consuming a published skill, first**: `pull` → `install -f values.yaml` → `ls`. Reachable without writing a `SKILL.md`, and its subject is a skill the reader did not write — which is the coverage gap today (step 5's `pull` currently pulls back what step 4 published).
- [ ] 5.3 Path B, authoring: write, `pack`, publish, `pull` back. Publishing is `oras cp`; do not write an `epos push` that does not exist (#43). Keep it shorter than Path A.
- [ ] 5.4 The worked example section, quoting `examples/go-house/Skillfile` — stages, a cross-stage copy, a whole-file drop and a section edit, plus one sentence on why deriving beats forking.
- [ ] 5.5 The parameterisation demo: install with `values-library.yaml`, show the sections gone; re-install the **same artifact** with `values-service.yaml`, show them back, and say no rebuild was needed. Show `--set x=` once as the one-off off-switch with the one-sentence reason, and **never** `--set x=false` (design D4).
- [ ] 5.6 Retain exactly the prose that prevents a wrong command: `install` resolves from the local store and does not fetch; a value nobody supplied fails the install. At most three notes on the page.
- [ ] 5.7 Audit every command against the cobra tree: no `init`/`new`/`push`/`login`/`template`/`lint`; `--registry` present where required; one argument order for `build` across the whole site; every link through the base-path helper.

## 6. The generated pages

- [ ] 6.1 Apply the token corrections to the style blocks in `internal/docsgen/cli.go` and `internal/docsgen/skillfile.go`, and the shared furniture in `internal/docsgen/page.go`. **Go, not Astro** — CI regenerates and fails on a diff.
- [ ] 6.2 Run `go run ./internal/docsgen`, commit the output, and confirm `go run ./internal/docsgen -check` is clean.
- [ ] 6.3 Confirm the reference pages' **documentary** content is byte-identical — only chrome and style changed. `escape()` turns `{`/`}` into entities for Astro while the `<style>` blocks keep literal braces, so a careless refactor there is silent.

## 7. Before opening the pull request

- [ ] 7.1 `npm run build` in `docs/` clean, and again with the preview base path set — links and assets must resolve under a sub-path.
- [ ] 7.2 Read the landing and the quick start at 375px, 768px and 1440px. Confirm nothing scrolls horizontally, adjacent notes are separated, and the ASCII wordmark fits.
- [ ] 7.3 Grep the built output for `#a1a1a1`, `#3b82f6` and `--ga-fg-muted`. All three should be gone.
- [ ] 7.4 Recount the quick start's prose words against the 700 budget. A budget nobody measures is a suggestion.
