## Context

epos ships a docs site at `https://gaarutyunov.github.io/epos/` — Astro 5, four
pages, ui-kit v0.2.0 **vendored** (not installed: the kit publishes to GitHub
Packages, which needs a PAT even for public packages — `docs/vendor/ui-kit/VENDORED.md`).

Two of the four pages are **generated**. `internal/docsgen/main.go`:

```go
func targets() []target {
	return []target{
		{path: "docs/src/pages/cli.astro", render: renderCLI},
		{path: "docs/src/pages/skillfile.astro", render: renderSkillfile},
	}
}
```

`cli.astro` comes from the cobra tree via `cli.NewRootCommand()`;
`skillfile.astro` from `skillfile.NewReference()`. `.github/workflows/ci.yml:36-43`
re-runs the generator and fails on any diff. `index.astro` and `quickstart.astro`
are hand-written and covered by no drift check.

Page weights today:

| page | lines | words | generated |
|---|---|---|---|
| `index.astro` | 170 | ~606 | no |
| `quickstart.astro` | 645 | ~2480 | no |
| `cli.astro` | 454 | ~2109 | **yes** |
| `skillfile.astro` | 643 | ~3341 | **yes** |

What the CLI actually offers — 13 commands, `internal/cli/root.go`: `pack`,
`pull`, `store {ls,path,prune}`, `build`, `list`, `search`, `install`,
`uninstall`, `ls`, `generate-key-pair`, `sign`, `attest`, `verify`. **There is
no `init`, no `new`, no `push`, no `login`, no `template`, no `lint`.** Publishing
is `oras cp`; authentication is `oras login`.

---

## D1: #42 owns the recipe; #44 owns packing, publishing and displaying it

**Decision.** Specify and build #42 now. Move the *derived Go skill's Skillfile
and values profiles* into #42 as `examples/go-house/`, checked in and executed by
CI. #44 keeps the catalog frontend, the `epos pack`/publish of that example to
the demo registry, and the leaderboard/downloads UI. Neither issue blocks the
other, and the shared artifact has exactly one home.

**Why the question is real.** #42 says: *"Here in the issue I explained what I
want to get [#44] … The idea is that the quick start would explain how we did
this with Epos."* Read literally, #42 narrates #44's output — and #44's output
does not exist. `git ls-tree -r origin/main | grep -i 'skill.md\|Skillfile$'`
returns **nothing**: every Skillfile in the repo lives inside a Go string literal
in `internal/skillfile/reference.go`, a test fixture, or escaped HTML in an
`.astro` page. There is no packed example skill and no frontend (`git grep
'go:embed'` → zero hits).

**Alternatives rejected.**

- *Block #42 on #44 entirely.* Rejected. The landing is the issue's first and
  loudest complaint and shares nothing with #44 — blocking it buys nothing. It
  also gets the dependency backwards: #44 needs a *recipe* to pack, and #42 is
  where the recipe is designed and explained.
- *Land the landing now, defer the quick start to after #44.* Viable fallback,
  and the honest answer if the owner wants #44's scope untouched. Rejected as
  the default because the quick start does not actually need anything from #44:
  `FROM git+https://github.com/o/r#<ref>:<subdir>` is a shipped `FROM` source
  (`internal/skillfile/git.go`, pinned to a commit SHA **and** a tree SHA), and
  the three Go skills live at real paths in
  `gaarutyunov/workspace:.agents/skills/`. The whole multi-stage demo runs
  against git sources with no registry involved.
- *Write the example against `ghcr.io/gaarutyunov/skills/...` OCI refs now.*
  Rejected: that is the one form that genuinely requires #44 (and #43's `push`,
  or an `oras cp` by hand). Specified instead as a **swap**, once #44 publishes:
  four `FROM` lines change and the prose gains one sentence.

**The hazard if the order goes the other way.** If #44 runs first and invents its
own Skillfile, the two diverge and the quick start documents a build nobody
maintains. This is why the example is *checked in at one canonical path and
executed by CI* rather than living as prose on a page: whichever issue lands
first, the other consumes the file. That property matters more than which issue
technically owns it.

---

## D2: what "follow garutyunov.com's style" means, concretely

The reference is `projects/garutyunov.com` — Next.js 16 + Tailwind v4, and it
uses **no ui-kit components at all** on `main`. The kit is a *downstream
extraction*: `ui-kit/src/tokens/tokens.css` is headed "Extracted from
gaarutyunov.com", `ga-card`'s docstring says "styled after the 'pet projects'
cards on garutyunov.com", `ga-badge`'s says "after the skill chips". So the
translation is not "consume the site's components" — it is **the tokens are
already the site's palette, and three kit components already are the site's
patterns.**

Measured from `app/page.tsx`, `app/globals.css`, `components/*`:

| element | garutyunov.com | epos landing |
|---|---|---|
| background | `#000000`, one elevation `#1a1a1a` | `--ga-bg` / `--ga-bg-elev` (identical values) |
| container | `max-w-6xl` = **1152px**, `px-4 sm:px-6 lg:px-8` | landing band widens; docs pages stay narrow (D3) |
| hero grid | `grid-cols-1 lg:grid-cols-[auto_1fr]`, `gap-10 lg:gap-14` | same two-column band |
| hero left | ASCII box-drawing wordmark, `<pre>`, Fira Mono, `text-[8px] sm:text-[10px] lg:text-[12px]`, `tracking-[-1px]`, `leading-[125%]`, `select-none` | ASCII `EPOS` wordmark, same treatment, `--ga-font-display` |
| hero right | **one** sentence, `text-xl sm:text-2xl lg:text-3xl leading-tight tracking-tight text-balance`, muted `#878787` | one sentence, same scale via `--ga-fs-*`, `--ga-muted` |
| hero `h1` | `sr-only` — the visual name is the `<pre>` with `aria-label` | same |
| hero CTAs | **none** | none (D2a) |
| section label | `text-sm font-mono font-medium uppercase tracking-normal text-foreground mb-3.5` — 14px mono, UPPERCASE, **foreground-coloured, not letter-spaced**, no rule | same |
| section rhythm | uniform `mt-12` = **48px** | `--ga-space-12` |
| card grid | `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`, `gap-4` = 16px | same |
| card | `rounded-lg border border-border bg-card/30 p-5`, internal `gap-3`; icon 40px + `h3` + `text-sm text-muted leading-relaxed` + `mt-auto pt-2` mono footer | `ga-card` in that shape |
| card hover | **colours only** — fill 30%→60%, border `#1a1a1a`→`#454545`, title → `#54a2ff`. No lift, no shadow, no scale | same |
| code affordance | `rounded-md bg-card/80 px-4 py-3 font-mono text-sm` with muted `$` prefix + copy icon | `ga-code prompt="$"` |
| metadata | everything numeric/machine-ish is `font-mono` + `uppercase` + `text-xs` | same |
| accent | `#54a2ff`, **hover only**; green/amber/purple/red defined and unused | same restraint |
| theme | hard-coded dark, no `prefers-color-scheme`, no `data-theme` | dark; `[data-theme="light"]` left as the kit's opt-in, unused |

**D2a: the hero gets no buttons, and that is a decision, not an omission.** A
product landing normally opens with "Install" / "Get started" buttons.
garutyunov.com has none, and its equivalent is the *mid band*:
`<SectionLabel>Get in touch</SectionLabel>` over a `$ mailto:` terminal snippet.
The faithful mapping is a mid band of **`INSTALL` over `ga-code prompt="$"`** with
the `go install` line — which is a better CTA for this audience than a button,
because it is the command. The two existing `ga-button`s move from the page
footer up to directly under that snippet.

**D2b: the ASCII wordmark is not decoration copied for its own sake.** #44 says
*"We need to use same letters Epos For the skills"* — the same lettering is
wanted across the site and the future catalog. Establishing the `EPOS` ASCII
wordmark in #42 is what #44 then reuses.

**Rejected:** inventing a gradient/glow hero. There is a hero template in the
workspace at `.agents/skills/social-image/scripts/hero-template.html` using
`--ga-bg: #0a0e14` / `--ga-accent: #7fd1ff` / a radial-gradient glow, claiming to
"mirror the GA ui-kit dark house style". **It does not** — the site is `#000000`
with no gradient anywhere. A spec derived from that template would be wrong;
naming it here so nobody derives one.

---

## D3: the landing is wide, the docs pages stay narrow

`Base.astro` sets `main { max-width: 52rem }` (832px) globally. That is right for
prose and wrong for a hero plus a 3-column grid; garutyunov.com's band is 1152px,
and the kit's own `--ga-max-width` is 880px.

**Decision.** Add a `width?: "prose" | "wide"` prop to `Base.astro`, defaulting
to `"prose"`. `index.astro` passes `"wide"`. The other three pages are untouched,
including the two generated ones — which matters, because a change to their
`<Base …>` call would mean editing `internal/docsgen/page.go`'s `frontmatter()`.

**Rejected:** overriding `max-width` from `index.astro`'s scoped `<style>`.
Astro scopes styles to the component, and `main` lives in `Base`; it would need
`:global`, which is the same global reach with none of the type safety.

---

## D4: parameterisation is install-time, and `--set x=false` is true

This is the load-bearing correction in the change. Epos has **two** parameter
mechanisms and they are deliberately disjoint — `internal/skillfile/reference.go`
says "the two never collide":

- **Build-time: `ARG` + `$NAME`.** Plain string substitution into an
  instruction's arguments. **There is no conditional instruction.** The
  instruction set is exactly ten (`FROM COPY RM APPEND REPLACE PATCH AWK SET
  UNSET ARG`) and `instructionByOp` is built from the same table that generates
  the reference, so an op the builder honours but the table omits cannot exist.
  You **cannot** conditionally include or exclude a file at build time.
- **Install-time: `{{ }}`, Go `text/template`, no custom functions, `.Values`
  and nothing else.** `internal/install/render.go` explains why `if` works:

  > A missing value is an error rather than the `<no value>` Go prints by
  > default. text/template's missingkey=error would say it more directly, but it
  > also makes `{{ if .Values.optional }}` an error on the absent key it exists
  > to test, so optionality would become unexpressible …

  So `{{ if .Values.openapi }} … {{ end }}` is supported **by design**, and
  toggling means re-running `epos install`.

**The trap.** `internal/install/values.go`:

```go
// Values stay strings. Helm infers types here; this does not, because 10.3
// gives text/template no custom functions …
func applySet(top map[string]any, set string) error {
	…
		if i == len(keys)-1 {
			cursor[key] = value
```

`--set openapi=false` stores the **string** `"false"`. A non-empty string is
**truthy** to `{{ if }}`, so the feature the user just "disabled" stays on. By
contrast `LoadValues` reads `-f` files with `yaml.Unmarshal` into
`map[string]any`, so `openapi: false` in a YAML file is a real Go `bool` and is
falsy. Verified against the code, not inferred.

**Decision.** The demo's primary path is `-f values-library.yaml` /
`-f values-service.yaml` — two profiles, and "enabling it later" is swapping the
file. `--set` appears once, as the one-off override, in its **only** correct
off-form: `--set openapi=` (empty string). The quick start states the reason in
one sentence, because a reader who guesses `--set openapi=false` gets a silently
wrong install.

**Rejected:** specifying a fix to `applySet` so `false` infers a boolean. It is
a change to epos's value semantics with a real argument on both sides (the
comment above is a considered position, not an oversight), it is out of a
docs issue's scope, and #42 can be correct without it. Flagged for the owner
below.

**One more consequence worth writing down.** Stage names are the values-scope
keys (`internal/artifact/artifact.go`, `StagesAnnotation` =
`dev.epos.skillfile.stages`), so a file that `COPY --from=pro` brought in renders
against `.Values.pro`, not the top level. Any copied file containing `{{` needs a
value in its stage's scope or the install fails. This is precisely the class of
error that only shows up when the example is actually run — hence D5.

---

## D5: the example is a checked-in, CI-executed artifact, not prose on a page

`internal/skillfile` already has `TestDocumentedExamplesBuild`, which executes
every example in `reference.go`'s instruction table against the real builder.
`quickstart.astro` is covered by **nothing** — its Skillfiles are escaped HTML.

**Decision.** `examples/go-house/{Skillfile,values-library.yaml,values-service.yaml}`
is checked in, and a Go test builds it and installs it under **both** profiles,
asserting the presence and absence of the parameterised sections. The quick start
quotes that file rather than restating it.

**Consequences accepted:**

- The `FROM git+https://…#<ref>:.agents/skills/<name>` sources make the test
  network-dependent. It goes behind `//go:build integration` — which
  `go-project-scaffold` mandates anyway — so `go test ./...` stays hermetic.
- Pinning `#<ref>` to a tag or SHA means the example is reproducible but ages.
  That is the correct trade: an unpinned `#main` example silently changes meaning
  when the workspace skills change, and epos's whole argument is that pinning is
  the point.

**Rejected:** `PATCH` for the edits to the three base skills. go-gitdiff is
applied strictly — **no fuzz, no offset search** — so any upstream drift in a
774-line `SKILL.md` fails the build outright. `AWK` (line-oriented, section-
boundary matching) and `REPLACE` (RE2, and a zero-match **warns and continues**)
degrade gracefully on a base you do not control. `RM` is the exception where
strictness is right and already the behaviour: an absent path is fatal, because
"a path that is not there is a path the author was wrong about".

---

## D6: how the derived skill is scoped, and what it does *not* decide

Four stages, chosen from what the three skills actually contain:

| stage | source | what happens to it | why |
|---|---|---|---|
| *(final, unnamed)* | `go-project-scaffold` — 438 lines, 3 files | base; `## Non-negotiable` excised with `AWK` and re-added parameterised; `SET name`/`SET version` | the only one of the three the workspace routes for Go work (`AGENTS.md`), and already written as if it had parameters |
| `idiomatic` | spf13 `go` — 774 lines, one `SKILL.md` | keep the philosophy (≈11-429); strip the "modern stdlib / current syntax" cookbook (≈430-718) and the debugging essay (750-774) | ~290 stripped lines are a stdlib cookbook, useful but not house guidance; the surviving half is the part `go-project-scaffold` has no view on |
| `pro` | `golang-pro` — 2255 lines, 6 files | keep `references/{concurrency,testing}.md` minus two sections; **drop `generics.md` and `project-structure.md` whole**; drop `interfaces.md`'s "Interface Satisfaction Verification" | see below — this is where the drops are load-bearing rather than cosmetic |
| `containers` | `testcontainers-go` — 3437 lines | `COPY` only the Go example(s) the profile needs, path-scoped | #44: *"add testcontainers reference but only go, it has a bunch of references"* |

**The `golang-pro` drops are removals of content that is wrong here, not merely
duplicated:**

- `references/generics.md` (442 lines) teaches `type Container[T any]` and a
  Rust-style `Result[T]`; `go/SKILL.md:409-423` labels that shape *"this is
  Java"* and says "do not create generic base types, generic services, or
  generic repositories". It also writes `import "constraints"` (`:40`) — not a
  package — where `go/SKILL.md:426` says use `cmp.Ordered`.
- `references/project-structure.md` (477 lines) is the single biggest source of
  conflict in the workspace: `gin` + `zap` + **`kelseyhightower/envconfig`** as
  *the* configuration mechanism (a **third** config library, against
  `go-project-scaffold`'s koanf and `cobra-viper`'s Viper), the **archived**
  `github.com/golang/mock/mockgen` driven by a `tools.go` of blank imports that
  `go/SKILL.md:712` says never to generate, deprecated `// +build` tags, and the
  exact `api/`+`service/`+`repository/` layer set `go/SKILL.md:120` says to
  reject.
- `interfaces.md:173-180`'s `var _ io.Reader = (*MyReader)(nil)` is #44's
  "explicit interface conformance". `go-project-scaffold/SKILL.md:174-176`:
  *"**Never** write `var _ Interface = (*Impl)(nil)` … Java-flavoured noise."*
  A clean two-sided conflict, and the crispest one-line demonstration of "drop
  what we don't use" in the whole set.
- `concurrency.md:15-51` opens with a static `WorkerPool`, which
  `go/SKILL.md:187` names an anti-pattern and `:195` answers with `errgroup` +
  `SetLimit`. The section goes; rate-limiting and pipelines stay.

**Viper — the drop the issue names, and the one that is *already* a workaround.**
#44 says "dropping what we don't use, i.e. viper". Worth being precise about
where Viper actually is: the vendored skills were **not** patched. `37bd574` is
titled "Add spf13's Go skills, with koanf in place of Viper", but that describes
a workspace *rule*, not an edit — `cobra-viper/SKILL.md` is verbatim upstream
Viper and contains zero occurrences of "koanf". The override lives in
`.claude/rules/go-cli-koanf.md`, which states why:

> **Do not use Viper.** … This is a standing preference, not a per-project call,
> so the skill is left exactly as upstream wrote it and the exception lives here
> instead — **editing a vendored skill would lose the edit the next time it is
> reinstalled.**

That sentence is the strongest argument for Epos anywhere in this workspace, and
the quick start should say so plainly: the override is detached from the skill
*because there was no way to layer it onto the skill*. `FROM … ` + `AWK`/`REPLACE`
is that way. It survives reinstallation because the derivation, not the edited
file, is the artifact.

**What this deliberately does NOT decide — for the owner.** The parameterised
base is `go-project-scaffold`, so the derived skill prescribes
`internal/app`, `internal/config`, `internal/server`, `internal/<feature>`. The
spf13 `go` skill calls *"relying heavily on an `internal/` folder by default"* an
anti-pattern (`:65`), says *"For Applications: … Using `internal/` here is usually
just adding unnecessary path depth"* (`:75`), and prescribes top-level domain
packages *"one level deep — no `internal/` nesting"* (`:92`). **Both skills are
merged on `main`** (workspace#31), so this is a live contradiction in guidance
already in force, recorded in the goga#1 design doc under *"the layout
contradiction is live in merged guidance"*.

Taking `go-project-scaffold` as the base resolves it **for this example by
precedence, not by decision** — `AGENTS.md` puts the house standard on top and
spf13's skills "underneath". The derived skill is a demonstration of Epos, not a
ruling on Go layout, and it must not read as one: the stage that carries spf13's
material lands as `references/idiomatic-go.md`, whose layout section is part of
the stripped range. **If the owner wants the derived skill to be the real house
Go skill rather than a demo, the `internal/` default has to be decided first,
and that is the owner's call.**

---

## Open questions for the owner

1. **Does the derived skill's Skillfile live in #42 (recommended, D1) or #44?**
   Either works provided it is one checked-in file both issues point at. If #44
   keeps it, #42 reduces to landing + note fix + token fix now, and the quick
   start follows #44.
2. **Should `--set x=false` infer a boolean?** (D4.) Today it does not, and the
   docs will say so. Changing it is a small, separate epos change.
3. **`internal/` as the default package home** (D6) — unresolved between two
   merged skills. Not needed for the example; needed before the derived skill
   could be adopted as the real house skill.
4. **Pin for the git `FROM` sources** (D5) — a workspace tag, or a SHA? A tag
   reads better in a tutorial; a SHA needs no tagging discipline.
