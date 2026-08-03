## Context

epos ships a docs site at `https://gaarutyunov.github.io/epos/` — Astro 5, four
pages, ui-kit v0.2.0 **vendored** (not installed: the kit publishes to GitHub
Packages, which needs a PAT even for public packages — `docs/vendor/ui-kit/VENDORED.md`).

Two of the four pages are **generated**, and that is a property this change
**preserves and extends, never works around**. An auto-generated reference cannot
drift from the code it documents; a hand-written one always does. Every style,
chrome and layout decision below therefore has to reach `cli.astro` and
`skillfile.astro` *through their generator* — which means editing
`internal/docsgen`, not the Astro. Nothing in this change replaces a generated
page with a hand-authored one, bypasses the drift gate, or moves a reference out
of `internal/docsgen`; where the generator cannot yet express something the
change needs, the generator gains the capability.

`internal/docsgen/main.go`:

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
re-runs the generator and fails on any diff — the gate stays. `index.astro` and
`quickstart.astro` are hand-written and covered by no drift check, which is the
asymmetry to be uncomfortable about: the two pages this change rewrites by hand
are the two nothing verifies. Hence D5, which puts the quick start's worked
example behind a test.

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
  every source skill lives at a real path under
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

This section measures the reference site's **landing** (`app/page.tsx`,
`app/globals.css`, `components/*`) against epos's landing. The site's **inner**
pages — the five skill pages and the CV — are a different and, for a docs site,
more important shape; they are measured separately in **D3**, because three of
epos's four pages are inner pages.

| element | garutyunov.com | epos landing |
|---|---|---|
| background | `#000000`, one elevation `#1a1a1a` | `--ga-bg` / `--ga-bg-elev` (identical values) |
| container | `max-w-6xl` = **1152px**, `px-4 sm:px-6 lg:px-8` | **every** page widens to this — inner pages included (D3) |
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

## D3: epos's docs pages are *inner* pages — one shell, a 9/3 grid, breadcrumbs

An earlier draft of this design said "the landing is wide, the docs pages stay
narrow". Measuring the reference site's inner pages shows that is **wrong**, and
correcting it is the largest single change in this revision.

Measured from `app/[skill]/page.tsx` (route is top-level `/{skill}`, not
`/skills/[slug]`), `app/cv/page.tsx`, `app/layout.tsx`,
`components/section-label.tsx`, `components/skill-chip.tsx` on `origin/main`:

| element | garutyunov.com inner pages | epos docs pages |
|---|---|---|
| container | **the same `max-w-6xl` = 1152px as the landing** — `app/cv/page.tsx:27` is byte-identical to `app/page.tsx:19`. Inner pages do **not** narrow | same 1152px shell as the landing |
| gutters | `px-4 sm:px-6 lg:px-8` (CV, landing); the skill page's bare `px-4` is a divergence, not a pattern | `px-4 sm:px-6 lg:px-8` |
| body layout | 12-column grid, `lg:grid-cols-12`, main `lg:col-span-9` + `aside lg:col-span-3`, `gap-12 lg:gap-16` (skill) / `gap-10 lg:gap-14` (CV) | `col-span-9` main + `col-span-3` aside, one gap value |
| effective measure | **≈824px** at the 1152px cap — *wider* than epos's current 832px `main`, not narrower | ≈824px, i.e. today's measure, kept |
| sticky header | `sticky top-0 z-50 bg-background flex h-14` — 56px, opaque `#000`, **no border, no blur** | same |
| footer | **there is none.** `app/layout.tsx` renders `<header>` + `<main>` and nothing else | epos keeps its footer (see below) |
| page `h1` | **visible**, not `sr-only` — `text-4xl font-semibold tracking-tight text-foreground mb-6` = 36px/40px, weight 600, `-0.025em`, `#ededed`, 24px below. CV steps `text-3xl sm:text-4xl` | same, and the landing's `sr-only` `h1` is the exception, not the rule |
| section heading | `SectionLabel` — `text-sm font-mono font-medium uppercase tracking-normal text-foreground mb-3.5` = 14px mono, weight 500, UPPERCASE, tracking **0em**, 14px below, no rule | same component, same values, on every page |
| bullets | never a real list marker: `<li class="flex gap-3">` with a leading `—` span nudged `mt-1`/`mt-0.5` | same em-dash bullet |
| ruled rows | CV sidebar: `flex justify-between text-sm border-b border-border py-2` — label `text-foreground`, value `font-mono text-muted` | the pattern for any key/value list |
| chips | `inline-flex items-center px-2.5 py-0.5 rounded-full border border-border text-xs text-muted`, group `gap-1.5` = 6px | same |
| rhythm | always `space-y-*`, never element margins: 48px between sections, 40px between entries, 8–10px between bullets | same |
| colours | `--foreground #ededed`, `--muted #878787`, `--dim #454545`, `--border #1a1a1a`, `--border-subtle #111111`, `--card #1a1a1a` on `#000` | the identical tokens, via the kit |

**Decision.** Drop the `width?: "prose" | "wide"` prop. `Base.astro` instead
gives **every** page the 1152px shell and the sticky 56px header, and the three
docs pages render their content in the inner-page **9/3 grid**: content in
`col-span-9`, an aside in `col-span-3`. The reading measure lands at ~824px —
within 8px of today's 832px `main`, so no page's prose gets harder to read while
every page gains the site's actual proportions. The landing is then not a special
width at all; it is the same shell with a full-width band instead of a 9/3 split.

**Why this is better than the prop.** The prop existed to protect the docs pages
from a width they never needed protecting from. The real difference between the
landing and an inner page on garutyunov.com is not container width — it is
*whether there is an aside*. Modelling that directly means the two generated
pages get a sidebar slot (an on-page contents list is the obvious tenant, and
`internal/docsgen` already knows every section it emits), which the prop could
never have given them.

**The aside is where the generated pages gain the most.** `cli.astro` is 2109
words and `skillfile.astro` 3341, with no navigation within the page at all. The
site's own answer to "where am I in a set" is the skill page's *Other skills*
list and the CV's *Areas* rows; the docs equivalent is a per-page contents list
plus links to the sibling reference. Both are derivable in the generator.

**D3a: breadcrumbs.** The owner asked for them explicitly, and the reference site
has them on every inner page — hand-rolled twice, with **divergent** styling:

```jsx
// app/[skill]/page.tsx:43-49
<nav className="flex items-center gap-2 text-xs text-dim pt-8 pb-6">
  <Link href="/" className="hover:text-foreground transition-colors shrink-0">
    German Arutyunov
  </Link>
  <span className="shrink-0">/</span>
  <span className="text-foreground">{skill.title}</span>
</nav>
```

```jsx
// app/cv/page.tsx:28-34
<nav className="flex items-center gap-2 text-sm font-mono text-muted pt-4 pb-6">
  <Link href="/" …>German Arutyunov</Link>
  <span className="shrink-0">/</span>
  <span className="text-foreground">CV</span>
</nav>
```

They agree on the structure — a `<nav>` of flex children, **no `<ol>`/`<li>`**, a
literal `/` separator in a bare `<span>`, `gap-2` = 8px on both sides of the
separator, `pb-6` = 24px down to the `h1`, first crumb a link with
`hover:text-foreground transition-colors`, **last crumb a plain `<span>` in
`text-foreground`, never a link**. They disagree on font (inherited sans vs
`font-mono`), size (`text-xs` 12px vs `text-sm` 14px), link colour (`text-dim`
`#454545` vs `text-muted` `#878787`) and top offset (`pt-8` 32px vs `pt-4` 16px).

**Decision.** Follow the **CV variant**: `font-mono`, 14px, `--ga-muted` for the
link, `--ga-fg` for the current page, `/` separator, 8px gaps, 24px to the `h1`.
Reasons, in order: it is the more legible of the two (`#454545` on `#000` fails
contrast at 12px); mono matches a documentation site's character and the
`SectionLabel` treatment it sits above; and the site's own metadata convention
(D2) is that machine-ish text is mono. The skill page's 12px `text-dim` form is
treated as the divergence it is, not as a second pattern to reproduce.

**Three things are added that the reference site does not have**, and they are
additions on purpose rather than copies: the `<nav>` gains
`aria-label="Breadcrumb"`, the current-page crumb gains `aria-current="page"`,
and the `/` separator gains `aria-hidden="true"` so a screen reader does not read
"slash" between crumbs. The reference site omits all three; reproducing an
accessibility gap is not fidelity. Nothing else about the markup changes, so the
visual result is the CV's breadcrumb exactly.

**The breadcrumb replaces the per-page back link.** Every epos page currently
hand-rolls its own "← back to the landing". The first crumb *is* that link, and
one shared definition beats four copies — which is what the existing "shared page
furniture" requirement was already asking for. On the two generated pages the
breadcrumb is emitted by `internal/docsgen/page.go`, from the page's own title;
that is the generator being extended, per the Context.

**Depth.** The site's breadcrumbs are always exactly two crumbs. epos's docs are
also two levels — `epos / Quick start`, `epos / CLI reference`,
`epos / Skillfile reference` — so no deeper case has to be designed. The landing,
being the root, carries none.

**What the reference site does *not* give us, and where we stop copying.**
`@tailwindcss/typography` is loaded in `app/globals.css:2` and **`prose` appears
zero times in the repo** — the entire site is hand-rolled per element. There is
no `<h3>` anywhere, no styled paragraph-in-flow, no inline code, no code block,
no blockquote, no table. So for a documentation site there is **no long-form
scale to copy**: the site's inner pages are bullets, ruled rows and chips, not
prose. Where epos needs something the reference has no answer for — an `h3`, a
code block's surround, a table in the CLI reference — the spec extends the
existing scale rather than importing an outside one, and says so. Claiming to
have "copied" an `h3` from a site that has none would be a fabrication.

**Rejected:**

- *Keep the `"prose" | "wide"` prop and leave the docs at 832px.* This is what the
  earlier draft said. It contradicts the measurement: the reference site's inner
  pages are 1152px, and its own reading column is *wider* than epos's, not
  narrower. The owner asked for the inner-page style; this was not it.
- *Copy the skill page's 12px `text-dim` breadcrumb.* Rejected above on contrast.
- *Reproduce the site's inner-page divergences* (`px-4` at all breakpoints, two
  different grid gaps, two breadcrumb styles, no footer, no print stylesheet).
  Rejected: those are drift in the reference, not design. epos picks the CV's
  gutters, one gap value, one breadcrumb, and keeps its footer — a docs site
  needs the licence and repository links a personal site does not.
- *Overriding `max-width` from a page's scoped `<style>`.* Astro scopes styles to
  the component and `main` lives in `Base`; it would need `:global`, which is the
  same global reach with none of the type safety.

---

## D4: parameterisation is install-time, and `--set x=false` is true — for now

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

**This is a bug, and it is being fixed — epos#47.** The owner's ruling on this
design: *"Extract into separate issue, this must be fixed and work same as in
helm. Explore helm source code."* That issue is **epos#47, "install --set does
not infer types (must match helm)"**, and it is the one place the defect is
tracked. `applySet`'s comment is therefore **not** a considered position to be
documented as behaviour-by-design; it is a limitation with an owner-approved
fix pending, and helm's `pkg/strvals` (`false`/`true` → `bool`, integers →
`int64`, `null` → nil, `a,b` → list, `\,` escaping, `--set-string`,
`--set-file`) is the target semantics.

**Decision — two parts, and the second is temporary.**

1. **`-f values-library.yaml` / `-f values-service.yaml` is the demo's primary
   path, permanently.** This is *not* a workaround and does not go away when #47
   lands. A values file is the right shape for the thing being demonstrated: the
   owner's scenario is "disable some dependencies because the project doesn't
   need it, and enable it later by changing the values" — a *named, committed,
   re-appliable profile*, which is a file, not a command line. `--set` is for
   one-off overrides, and it stays a footnote on the page whatever its type
   semantics.
2. **Until #47 lands, `--set` appears once, in its only correct off-form:
   `--set openapi=` (empty string), with one sentence of prose saying why.**
   This part **is** a workaround and is written to be deleted. A reader who
   guesses `--set openapi=false` today gets a silently wrong install, and the
   quick start cannot ship without warning them.

**Exactly what becomes removable when #47 lands**, so whoever closes it knows
what to delete here:

- The one sentence in the quick start explaining that command-line values stay
  strings and so `=false` reads as true.
- The `--set openapi=` empty-value form, replaced by the natural
  `--set openapi=false`.
- The prohibition in the `epos-quickstart` capability on writing `=false` on the
  command line.
- The corresponding "Booleans are real booleans" caveat in the
  `epos-derived-go-skill` capability — after #47 the YAML profiles are still the
  right primary path (part 1), but for the reason above, not because `--set` is
  broken.

Nothing else in this change depends on the bug. The values profiles, the
`{{ if .Values.x }}` guards, the two-profile install test and the whole worked
example are unaffected by #47 either way.

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

**Rejected:** `PATCH` for the edits to the vendored base skills. go-gitdiff is
applied strictly — **no fuzz, no offset search** — so any upstream drift in a
774-line `SKILL.md` fails the build outright. `AWK` (line-oriented, section-
boundary matching) and `REPLACE` (RE2, and a zero-match **warns and continues**)
degrade gracefully on a base you do not control. `RM` is the exception where
strictness is right and already the behaviour: an absent path is fatal, because
"a path that is not there is a path the author was wrong about".

---

## D6: how the derived skill is scoped, and what it does *not* decide

**Five** stages, chosen from what the source skills actually contain. The fifth,
`cli`, is added in this revision on the owner's *"drop viper"* ruling — see
D6a, which explains why the drop is only meaningful with that source present.

| stage | source | what happens to it | why |
|---|---|---|---|
| *(final, unnamed)* | `go-project-scaffold` — 438 lines, 3 files | base; `## Non-negotiable` excised with `AWK` and re-added parameterised; `SET name`/`SET version` | the only one the workspace routes for Go work (`AGENTS.md`), and already written as if it had parameters |
| `idiomatic` | spf13 `go` — 774 lines, one `SKILL.md` | keep the philosophy (≈11-429, **including the generics guardrails at 380-429**); strip the "modern stdlib / current syntax" cookbook (≈430-718) and the debugging essay (750-774) | ~290 stripped lines are a stdlib cookbook, useful but not house guidance; the surviving half is the part `go-project-scaffold` has no view on |
| `pro` | `golang-pro` — 2255 lines, 6 files | keep `references/{concurrency,testing,generics}.md` minus named sections; **drop `project-structure.md` whole**; drop `interfaces.md`'s "Interface Satisfaction Verification" | see D6a — the drops are load-bearing, and `generics.md` is now a *precise* strip rather than a whole-file drop |
| `cli` | `cobra-viper` — 446 lines, one `SKILL.md` | keep the Cobra half; **`AWK` out `## Viper Configuration Patterns` (251-362) whole**; `REPLACE` the remaining Viper mentions; `APPEND` the koanf translation | the owner's *"drop viper"*, and the workspace's own live example of an override that could not be layered — D6a |
| `containers` | `testcontainers-go` — 3437 lines | `COPY` only the Go example(s) the profile needs, path-scoped | #44: *"add testcontainers reference but only go, it has a bunch of references"* |

---

### D6a: the four drops, each attributable to a named conflict

**1. `var _ Interface = (*Impl)(nil)` — dropped, and the owner is emphatic.**
The review comment reads: *"Drop viper and explicit interface implementation. The
var _ Interface thing. I hate it."* `interfaces.md:173-181` is the offending
section, "Interface Satisfaction Verification":

```go
var _ io.Reader = (*MyReader)(nil)
var _ io.Writer = (*MyWriter)(nil)
var _ io.Closer = (*MyCloser)(nil)
```

`go-project-scaffold/SKILL.md:175` — *"**Never** write
`var _ Interface = (*Impl)(nil)`. The compiler enforces…"* — and
`references/review.md:77` makes removing it a review checklist item. A clean
two-sided conflict, the crispest one-line demonstration of "drop what we don't
use" in the whole set, and now an owner instruction on top of that. It is
dropped, the derived skill inherits `go-project-scaffold`'s prohibition, and the
build test asserts the string `var _ ` does not occur in the installed artifact —
a drop nobody verifies is a drop that comes back on the next upstream bump.

**2. `references/project-structure.md` (477 lines) — dropped whole.** The single
biggest source of conflict in the workspace: `gin` + `zap` +
**`kelseyhightower/envconfig`** as *the* configuration mechanism (a **third**
config library, against `go-project-scaffold`'s koanf and `cobra-viper`'s Viper),
the **archived** `github.com/golang/mock/mockgen` driven by a `tools.go` of blank
imports that `go/SKILL.md:712` says never to generate, deprecated `// +build`
tags, and the exact `api/`+`service/`+`repository/` layer set `go/SKILL.md:120`
says to reject. Nothing in it survives a house review, so nothing in it is worth
a precise strip.

**3. `concurrency.md:15-51`'s static `WorkerPool` — dropped.**
`go/SKILL.md:187` names it an anti-pattern and `:195` answers with `errgroup` +
`SetLimit`. The section goes; rate limiting and pipelines stay.

**4. Viper — dropped from a source that is added in order to drop it.** See
immediately below.

---

### D6b: generics — kept, with two blocks strip

**The owner reversed this one.** The earlier draft dropped
`golang-pro/references/generics.md` whole. The review says simply *"Generics is
good."* — so the file stays, and the strip becomes precise. Re-reading the file
against `go/SKILL.md` shows the earlier all-or-nothing call was over-broad: two
blocks out of twelve sections are wrong, and the earlier rationale conflated
them.

`generics.md` is 442 lines in twelve sections. **Ten survive untouched**: Basic
Type Parameters, Type Constraints, Generic Data Structures, Generic Map
Operations, Generic Pairs (the `Pair`/`Swap` half), Comparable Constraint, Type
Inference, Generic Channels, Union Constraints, Quick Reference. A generic
`Stack[T]` or a generic `Map`/`Filter` is exactly what generics are *for*, and
`go/SKILL.md` endorses them.

**Strip A — `## Generic Interfaces` (270-309), removed whole.** It teaches

```go
type Container[T any] interface { Add(item T); Remove() (T, bool); Size() int }
func ProcessContainer[T any](c Container[T], item T) { … }
```

which is precisely the shape `go/SKILL.md:409-413` shows under **"When NOT to Use
Generics"** with the comment *"Bad: generic interface for polymorphism — this is
Java"*, answered at :415-420 by a concrete `UserStore`. `:422` — *"**Do not**
create generic base types, generic services, or generic repositories."* Clean
section boundary, so `AWK`.

**Strip B — the `Result[T]` block inside `## Generic Pairs and Tuples`
(≈199-228), removed by `REPLACE`.** It opens with its own admission —
`// Generic Result type (like Rust's Result<T, E>)` — and reimplements
`Ok`/`Err`/`IsOk`/`Unwrap`/`UnwrapOr`. Go returns `(T, error)`; a `Result`
wrapper is a different language's idiom and collides with every error-handling
line in both surviving skills. The `Pair`/`Swap` code above it is fine and stays,
which is why this is a `REPLACE` on a multi-line pattern and not an `AWK` on a
section — the bad block is *inside* a good section. **Verify first that epos's
`REPLACE` compiles an RE2 pattern with `(?s)` so a multi-line match is
expressible**; if it does not, the honest fallback is `AWK` on the whole
Pairs-and-Tuples section, losing `Pair` — worse, and worth knowing before the
Skillfile is written. Added as task 1.4.

**Correction, not a strip — the `constraints` package.** `generics.md:40` writes
`import "constraints"`, which is not an importable path (the real one is
`golang.org/x/exp/constraints`), and uses `constraints.Ordered` at `:9`, `:323`
and `:440` where `go/SKILL.md:426` says *"**Do** use `cmp.Ordered`"*. `REPLACE`
rewrites `constraints.Ordered` → `cmp.Ordered` and fixes the import line. Note
that `constraints.Integer | constraints.Float` at `:44` has **no** `cmp`
equivalent — only `Ordered` moved to the standard library — so that illustration
stays and the import must name the real `golang.org/x/exp/constraints` path
alongside `cmp`. Getting this wrong in either direction produces a reference that
does not compile, which is why it is spelled out here rather than left to the
implementer.

**Why this is better than the whole-file drop, beyond the owner's preference.**
The `idiomatic` stage keeps `go/SKILL.md:380-429` — spf13's generics
*guardrails*, including "When NOT to Use Generics". Keeping the `pro` stage's
*recipes* next to them is the pairing the derived skill wants: rules and worked
examples on the same topic, with the two shapes the rules forbid removed from the
examples. That is not redundancy — it is the "no two reference files give
opposing instructions on the same question" scenario being *satisfied* rather
than dodged, and it is a better demonstration of Epos than deleting the file,
because a surgical strip is something a fork cannot keep doing cheaply.

---

### D6c: Viper — the drop the owner named, and the workspace's own unfixable override

*"Drop viper"* — and #44 said the same: *"dropping what we don't use, i.e.
viper"*. Being precise about where Viper actually is matters, because **none of
the four original stages contains any**: `golang-pro` has zero occurrences,
`testcontainers-go` zero, and spf13's `go` mentions Viper only in its author
bio. `go-project-scaffold` mentions it three times and every one already says
*never*. So against the earlier four-stage design the instruction would have been
**vacuous** — nothing to drop.

It is not vacuous against the workspace, because Viper is in `cobra-viper`, whose
**Cobra** half is house standard and whose **Viper** half is house-forbidden. The
vendored skill was never patched: `37bd574` is titled "Add spf13's Go skills,
with koanf in place of Viper", but that describes a workspace *rule*, not an edit
— `cobra-viper/SKILL.md` is verbatim upstream and contains zero occurrences of
"koanf". The override lives in `.claude/rules/go-cli-koanf.md`, which states why:

> **Do not use Viper.** … This is a standing preference, not a per-project call,
> so the skill is left exactly as upstream wrote it and the exception lives here
> instead — **editing a vendored skill would lose the edit the next time it is
> reinstalled.**

That sentence is the strongest argument for Epos anywhere in this workspace, and
the earlier draft already said the quick start should make it: the override is
detached from the skill *because there was no way to layer it onto the skill*.
`FROM` + `AWK`/`REPLACE`/`APPEND` is that way, and it survives reinstallation
because the derivation, not the edited file, is the artifact.

**Decision.** Add `cli` as a fifth stage from `cobra-viper`, and make the drop
real:

- `AWK` out `## Viper Configuration Patterns` — lines **251-362**, from
  "Prefer a Viper Instance over the Global Singleton" through "Config File
  Setup", ending cleanly at `## Version Handling` (363). A whole named section
  with unambiguous boundaries, which is exactly the case `AWK` is for.
- `REPLACE` the residual mentions the section boundary does not catch: the title
  at `:12` ("Go CLI Architecture: Cobra & Viper"), `### Unified Configuration`
  at `:31`, and any Viper line under `## Common Mistakes` (438+).
- `APPEND` the koanf translation from `.claude/rules/go-cli-koanf.md` in its
  place, so the derived skill carries the house configuration guidance the
  upstream skill cannot.

The result lands as `references/cli.md`. Everything else in `cobra-viper` — the
command-first architecture, the constructor-per-command factory, `RunE`,
context-aware commands, `Args` validation, flag design, in-memory CLI testing —
is kept as written, because it is spf13's and it is what the house follows.

**This is the change's best single demonstration**, better than any of the other
drops: it is a real workspace problem, unsolved today, with a written admission
that it is unsolved, and the derivation solves it. The quick start should say so
in one sentence.

**Interpretation flagged.** The owner wrote "drop viper" as a three-word
instruction on the stripping list; adding a source in order to strip it is an
inference, and it grows the example from four stages to five. The alternative
reading — assert "no Viper guidance survives" without adding the source — is
satisfiable by doing nothing, which cannot be what was meant. If the owner wants
the example kept to four stages, the `cli` stage is the piece to cut, and the
`epos-derived-go-skill` requirement reduces to the vacuous form.

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
2. **`internal/` as the default package home** (D6) — unresolved between two
   merged skills. Not needed for the example; needed before the derived skill
   could be adopted as the real house skill.
3. **Pin for the git `FROM` sources** (D5) — a workspace tag, or a SHA? A tag
   reads better in a tutorial; a SHA needs no tagging discipline.
4. **Five stages, or four?** (D6c.) Adding `cobra-viper` as the `cli` stage is
   how "drop viper" becomes a real drop rather than a vacuous assertion, and it
   is the change's strongest demonstration — but it is an inference from a
   three-word instruction, and it makes the example bigger. Flagged, not assumed.

**Resolved since the first review.** *"Should `--set x=false` infer a boolean?"*
— yes, and it is now **epos#47**, filed at the owner's direction. D4 records
which parts of this change are written around the bug and are to be deleted when
#47 lands, and which parts stand on their own regardless.
