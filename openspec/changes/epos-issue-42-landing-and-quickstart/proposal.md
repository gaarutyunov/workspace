## Why

epos#42 says the landing and the quick start are both wrong, and on the code
they are. But two of the issue's premises need correcting first, because one of
them changes what gets built and the other changes *when*:

- **"it doesn't have hero section"** — `docs/src/pages/index.astro:25` does have
  a `<header class="hero">`. What it lacks is everything a hero is *for*: a
  badge, an `<h1>` and one lede paragraph, then straight into prose. No CTA
  above the fold (the two `ga-button`s are in the footer at line 113), no
  feature list, no visual. The complaint is right; the diagnosis is "the hero is
  a heading, not a hero", which is a different fix from "add a hero".
- **"the quick start would explain how we did this with Epos"** — the artifact
  it would explain is **epos#44's** deliverable ("pack my go skill as an example
  skill and push to registry"). #42 as literally written documents something
  that does not exist yet. See design **D1**: the resolution is to move the
  *recipe* into #42 and leave *packing, publishing and displaying it* in #44,
  which makes #42 buildable now and #44 strictly downstream.

The rest of the issue survives intact and is worse than it reads.
`quickstart.astro` is **645 lines / ~2480 words** for 23 commands — the "What
you need" section defines *registry*, *digest* and *OCI* before the first
command runs. It covers authoring a skill end to end and **does not cover
consuming someone else's at all**: step 5's `epos pull` pulls back the skill you
published in step 4. `AS <stage>` and `COPY --from=` appear **zero times**, and
the only templating shown is straight substitution — never `{{ if }}`. So
multi-stage composition and parameterisation, the two things the issue calls
"the pure power of Epos", are absent from the tutorial entirely.

## What Changes

- **A real landing.** `index.astro` becomes hero + feature list in
  garutyunov.com's shape: a two-column `[auto 1fr]` band with an **ASCII `EPOS`
  wordmark** in Fira Mono against one balanced value sentence, then a mono
  uppercase section label over a `$`-prompt install snippet, then a 1/2/3-column
  border-only card grid. Six features, each one a capability that exists in the
  shipped CLI. The three Skillfile-mechanics sections move out of the landing
  and into the reference and quick start where they belong (design **D2**).
- **A quick start that is commands.** Rewritten to a target of **≤ 700 words**
  of prose across two paths — *use a published skill* (which does not exist
  today) and *author your own* — with the concept-defining preamble deleted and
  every explanation that is not load-bearing cut. Prose earns its place by
  preventing a wrong command, not by teaching OCI.
- **The worked example the issue asks for**, as a checked-in, CI-executed
  artifact under `examples/go-house/`: one Skillfile deriving **one** house Go
  skill from **five** real skills — `go-project-scaffold` as the parameterised
  base, spf13's `go` stripped to its philosophy, `golang-pro` stripped of the
  layered-structure reference and two named sections, `cobra-viper` with its
  **Viper half removed and the house koanf translation appended in its place**,
  and a path-scoped slice of `testcontainers-go`. Five stages, `COPY --from`,
  `RM`, `AWK`, `REPLACE`, `APPEND`, `SET`, and `{{ if .Values.x }}` on the
  features a library does not want.
- **The drops are surgical where surgery is what the conflict deserves.**
  `golang-pro`'s generics reference is **kept** — it is good material — minus
  the one generic-interface section `go/SKILL.md` calls *"this is Java"* and the
  Rust-style `Result[T]` block, with `constraints.Ordered` corrected to
  `cmp.Ordered`. `var _ Interface = (*Impl)(nil)` is dropped outright and its
  absence is asserted by test. Only `project-structure.md`, which conflicts with
  the house standard on every axis it touches, is dropped whole (design **D6a**,
  **D6b**, **D6c**).
- **A correction the demo cannot ship without — until epos#47 lands.**
  `--set x=false` stores the **string** `"false"`, which `{{ if }}` reads as
  **true** (`internal/install/values.go` — *"Values stay strings"*, verified).
  That is a **bug**, now tracked as **epos#47** *"install --set does not infer
  types (must match helm)"*, and this change is written around it *temporarily*:
  one sentence of warning and `--set x=` (empty) as the documented one-off
  off-switch, both listed in design **D4** as the exact text to delete when #47
  lands. The `-f values-*.yaml` profiles stay the demo's primary path
  permanently — a named, committed, re-appliable profile is the right shape for
  "disable a dependency and enable it later", whatever `--set` does with types.
- **The note-spacing bug, fixed once.** `ga-note` sets `:host { display: block }`
  and `.note { margin: 0 }`, and **no page anywhere supplies an external
  margin** — `git grep 'ga-note\s*{'` over `docs/` returns nothing. Adjacent
  notes touch at 0px (`quickstart.astro:251-276`, `:419-430`). One rule in
  `Base.astro`'s `is:global` block covers all four pages.
- **The site actually adopts the tokens it imports.** `--ga-fg-muted` is
  referenced ~10 times across the pages and **does not exist** in
  `tokens.css` — every muted string on the site is currently rendering its
  `#a1a1a1` fallback instead of the house `#878787`. `Base.astro` falls back to
  `#3b82f6` where the real accent is `#54a2ff`. Nothing uses `--ga-font-sans`
  (Geist), `.ga-theme`, or the spacing scale. "Follow garutyunov.com's style"
  is, in its most literal sense, this list.
- **The docs pages are styled as garutyunov.com's *inner* pages, breadcrumbs
  included.** The site's skill pages and CV are **not** narrower than its
  landing — `app/cv/page.tsx:27` is byte-identical to `app/page.tsx:19`, both
  `max-w-6xl` (1152px) — and they get their reading measure from a 12-column
  grid with a `col-span-9` body beside a `col-span-3` aside (≈824px, within 8px
  of epos's current `main`). So every epos page adopts the one 1152px shell, the
  56px sticky header, the visible `text-4xl font-semibold tracking-tight` `h1`,
  the em-dash bullets, the ruled key/value rows, the pill chips — and a
  **breadcrumb** above every docs page's title, in the CV's mono 14px form, plus
  the `aria-label` / `aria-current` / `aria-hidden` the reference site omits. The
  breadcrumb replaces the back link each page hand-rolls today (design **D3**).
- **The two generated pages stay generated — that is a feature, and it is
  extended, not worked around.** `cli.astro` and `skillfile.astro` come from
  `internal/docsgen` with a CI drift gate (`.github/workflows/ci.yml:36-43`); an
  auto-generated reference cannot drift from the code it documents. Nothing here
  replaces one with a hand-authored page or bypasses the gate. Their share of
  the style work — tokens, shared chrome, the breadcrumb, the new sidebar slot —
  is a change to `internal/docsgen/{page,cli,skillfile}.go` plus a regenerate,
  spelled out so nobody edits the Astro and loses it.

## Capabilities

### New Capabilities

- `epos-landing`: the hero, the feature list, and what "garutyunov.com's style"
  concretely means for an Astro page built on ui-kit v0.2.0.
- `epos-quickstart`: the concise two-path quick start, and the prose budget that
  keeps it concise.
- `epos-derived-go-skill`: the multi-stage, parameterised worked example — the
  artifact, its values profiles, and the CI harness that stops the tutorial from
  documenting a build that no longer runs.
- `epos-docs-style`: the shared inner-page shell — one container width, the
  sticky header, the breadcrumb, the 9/3 content-and-aside grid — plus the token
  and spacing corrections, across all four pages, including the two that are
  generated from Go and stay that way.

## Non-goals

- **No `epos push`.** Publishing is `oras cp` today; #43 adds `push`. The
  worked example is deliberately built from `git+https://` and local sources so
  the multi-stage demo does not sit behind #43 (design **D1**).
- **No catalog UI, leaderboard or download counts.** That is #44. `git grep
  'go:embed'` over epos returns zero hits; there is no frontend to extend.
- **No fix to `--set` type inference — that is epos#47.** Making `--set x=false`
  a real boolean, matching helm's `pkg/strvals`, is now its own issue at the
  owner's direction. #42 documents today's behaviour correctly and marks every
  sentence written around the bug as deletable when #47 lands (design **D4**).
- **No resolution of the `internal/` conflict.** The derived skill is built from
  `go-project-scaffold` as the base, which settles it *for the example* by
  precedence and not by decision. The standing contradiction between the two
  merged skills is the owner's call (design **D6**).
