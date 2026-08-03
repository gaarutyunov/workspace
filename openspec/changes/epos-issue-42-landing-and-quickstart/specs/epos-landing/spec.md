## ADDED Requirements

### Requirement: A hero that states what Epos is, above the fold

`docs/src/pages/index.astro` SHALL open with a hero band whose first screen
names the product and its value in one sentence, and SHALL NOT open with
Skillfile syntax, OCI vocabulary, or a problem statement.

#### Scenario: The hero is a two-column band
- **WHEN** the landing renders at a viewport of 1024px or wider
- **THEN** the hero is a two-column grid sized `auto 1fr` — wordmark left, one
  sentence right — matching garutyunov.com's hero grid

#### Scenario: It stacks on a phone
- **WHEN** the landing renders below the large breakpoint
- **THEN** the two cells stack, wordmark above sentence, and the wordmark scales
  down so it fits the viewport without the page scrolling horizontally

#### Scenario: The wordmark is ASCII in the display font
- **WHEN** the hero renders
- **THEN** the visual wordmark is an ASCII rendering of `EPOS` in a `<pre>` using
  `--ga-font-display`, with negative letter-spacing and tight line-height so the
  glyph rows join

#### Scenario: The wordmark is not the accessible heading
- **WHEN** a screen reader reaches the hero
- **THEN** it announces a visually hidden `<h1>`, and the `<pre>` carries an
  `aria-label` rather than being read glyph by glyph

#### Scenario: Exactly one sentence of value copy
- **WHEN** the hero's right column renders
- **THEN** it contains a single balanced sentence in the muted foreground colour
  at the large display scale, and no second paragraph

#### Scenario: No buttons in the hero
- **WHEN** the hero renders
- **THEN** it contains no call-to-action buttons — the install command below it
  is the call to action

#### Scenario: The word "Skillfile" does not appear above the feature list
- **WHEN** a reader sees the landing's first two bands
- **THEN** neither mentions `Skillfile`, layers, manifests or digests

### Requirement: An install band that is the command

Below the hero the landing SHALL present the install command as a terminal
snippet under a section label, in place of a button row.

#### Scenario: Section label pattern
- **WHEN** the install band renders
- **THEN** its label is monospace, uppercase, foreground-coloured, not
  letter-spaced, with no rule or divider beneath it

#### Scenario: The command is a prompted code block
- **WHEN** the install band renders
- **THEN** the command appears in `ga-code` with a `$` prompt

#### Scenario: The primary links follow the command
- **WHEN** the install band renders
- **THEN** the quick-start and reference links appear directly beneath the
  command, not only in the page footer

### Requirement: A feature list of capabilities that exist

The landing SHALL carry a feature list of cards. Every card SHALL describe a
capability reachable from the shipped CLI or the shipped Skillfile instruction
set, and SHALL NOT describe anything the reference marks as withdrawn or
unimplemented.

#### Scenario: Card grid columns
- **WHEN** the feature list renders
- **THEN** it is one column on a phone, two at the small breakpoint and three at
  the large one, with a 16px gap

#### Scenario: Card anatomy
- **WHEN** a feature card renders
- **THEN** it is border-only over a low-alpha elevated fill with an 8px radius,
  and contains a title, one short body paragraph, and no more

#### Scenario: Hover changes colour only
- **WHEN** the pointer enters a feature card
- **THEN** only its fill, border and title colour change — there is no lift,
  scale, shadow or transform

#### Scenario: Multi-stage composition is one of the features
- **WHEN** the feature list renders
- **THEN** one card names multi-stage composition from several skills, and
  another names install-time parameterisation

#### Scenario: No card promises a withdrawn capability
- **WHEN** the feature list is reviewed against `SPEC.md`
- **THEN** no card claims a write path, `epos push`, native discovery, a
  Kubernetes installer, or download statistics

### Requirement: The landing keeps only the sections a landing needs

The Skillfile-mechanics prose currently on the landing SHALL be removed from it,
and its content SHALL be reachable from the quick start or the Skillfile
reference instead.

#### Scenario: The instruction inventory paragraph goes
- **WHEN** the reworked landing renders
- **THEN** it does not enumerate the Skillfile instruction set in prose

#### Scenario: The "no push" explanation goes
- **WHEN** the reworked landing renders
- **THEN** it does not explain why the write path was withdrawn; that belongs to
  the reference

#### Scenario: Nothing is lost
- **WHEN** a section is cut from the landing
- **THEN** its information is either present on the quick start or the reference,
  or it was a claim the code does not support

### Requirement: The landing shares the site's one container width

The landing SHALL render in the same container as every other page — the
reference site uses one width throughout and its inner pages are not narrower
than its landing — and SHALL differ from a documentation page only in filling
that container edge to edge instead of splitting it into content and aside.

#### Scenario: No width of its own
- **WHEN** the landing renders on a wide viewport
- **THEN** its container is the same width, with the same gutters, as every
  documentation page, and the shared layout offers no per-page width option

#### Scenario: The landing bands are full width
- **WHEN** the hero, install band and feature grid render
- **THEN** each spans the whole container, with no aside column, which is the
  only structural difference from a documentation page

#### Scenario: The documentation pages' reading measure does not regress
- **WHEN** the quick start, CLI reference and Skillfile reference render after
  this change
- **THEN** their content column is no wider than it was before it, the extra
  container width having gone to the aside

#### Scenario: The landing keeps the visually hidden title
- **WHEN** the landing renders
- **THEN** its heading remains visually hidden behind the wordmark, and this is
  the one page where that is so — the documentation pages show their titles
