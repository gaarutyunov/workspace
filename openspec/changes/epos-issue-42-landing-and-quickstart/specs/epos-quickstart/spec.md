## ADDED Requirements

### Requirement: The quick start is commands, with prose only where it prevents an error

`docs/src/pages/quickstart.astro` SHALL be rewritten to a hard budget of **at
most 700 words** of prose across the whole page, excluding code blocks, headings
and the table of contents. Every retained paragraph SHALL exist to stop a reader
running a wrong command.

#### Scenario: The budget is met
- **WHEN** the reworked page's prose is counted
- **THEN** it is at most 700 words, down from roughly 2480

#### Scenario: The concept preamble is gone
- **WHEN** a reader opens the page
- **THEN** the first thing after the heading is a command, not a definition of
  *registry*, *digest* or *OCI*

#### Scenario: Every step leads with its command
- **WHEN** a step renders
- **THEN** its command block precedes any explanation of it

#### Scenario: Prose that only restates a command is removed
- **WHEN** a paragraph says what the adjacent command plainly says
- **THEN** it is not on the page

#### Scenario: Prose that prevents an error is kept
- **WHEN** a behaviour would surprise a reader into a wrong command
- **THEN** one sentence states it — specifically that `install` resolves from the
  local store and does not fetch, and that a value nobody supplied fails the
  install

### Requirement: Two paths — using a published skill, and authoring one

The quick start SHALL cover consuming a skill someone else published **and**
authoring one, as two separately followable paths, with consuming first.

#### Scenario: The consuming path does not require authoring
- **WHEN** a reader follows the consuming path only
- **THEN** they reach an installed skill without writing a `SKILL.md`

#### Scenario: The consuming path starts from a skill the reader did not write
- **WHEN** the consuming path's first command runs
- **THEN** its subject is a skill published by someone else, not one the reader
  packed earlier on the page

#### Scenario: Pull precedes install
- **WHEN** the consuming path installs a skill
- **THEN** a `pull` or `build` step precedes it, because install does not fetch

#### Scenario: The authoring path is the shorter one
- **WHEN** both paths are on the page
- **THEN** the authoring path covers writing the skill, packing it, publishing
  it and pulling it back, and no more

#### Scenario: Publishing is described as it actually works today
- **WHEN** the authoring path reaches publishing
- **THEN** it uses the copy-into-a-registry tool the CLI has no replacement for,
  and does not present an `epos push` command that does not exist

### Requirement: Only commands and flags the CLI has

Every command, subcommand and flag on the page SHALL exist in the cobra tree, and
argument order SHALL be consistent across the whole site.

#### Scenario: No invented commands
- **WHEN** the page is checked against the command tree
- **THEN** it contains no `epos init`, `epos new`, `epos push`, `epos login`,
  `epos template` or `epos lint`

#### Scenario: Required flags are shown
- **WHEN** the page shows a command whose flag is required
- **THEN** that flag is present in the example — the registry flag on the
  catalogue commands in particular

#### Scenario: One argument order
- **WHEN** the build command appears on the landing and on the quick start
- **THEN** both write the context and the tag flag in the same order

#### Scenario: Links resolve under the site's base path
- **WHEN** the page links to another page
- **THEN** it builds the URL through the layout's base-path helper rather than
  writing a root-relative path

### Requirement: The multi-stage, parameterised worked example is on the page

The quick start SHALL demonstrate deriving **one** skill from **several**, and
SHALL demonstrate turning a feature off and back on by changing values.

#### Scenario: A multi-stage Skillfile appears
- **WHEN** the worked example renders
- **THEN** it shows a Skillfile with named stages and at least one cross-stage
  copy — constructs that appear zero times on the page today

#### Scenario: Content is dropped from a base the reader does not own
- **WHEN** the worked example renders
- **THEN** it shows removing a whole file from a base skill and editing a section
  out of another, and says in one sentence why that beats forking the skill

#### Scenario: A feature is disabled by values
- **WHEN** the reader installs with the lean values profile
- **THEN** the sections guarded by the disabled features are absent from the
  installed skill

#### Scenario: The same skill is re-enabled without rebuilding
- **WHEN** the reader re-installs the same built artifact with the full values
  profile
- **THEN** the sections reappear, and the page states that no rebuild was needed
  because parameters are resolved at install time

#### Scenario: The page quotes the checked-in example rather than restating it
- **WHEN** the worked example's Skillfile appears on the page
- **THEN** it is the content of the example checked into the repository, so the
  page cannot drift from a build that works

### Requirement: The page states how to disable a feature correctly

Because a value set on the command line is stored as a string and a non-empty
string is true to the template engine, the quick start SHALL NOT present a
command-line `=false` as a way to disable a feature.

#### Scenario: Booleans come from a values file
- **WHEN** the page turns a feature off
- **THEN** it does so with a boolean in a values file, which the loader parses as
  a real boolean

#### Scenario: The command-line off-switch is the empty value
- **WHEN** the page shows a one-off override that turns a feature off
- **THEN** it assigns the empty value, and never the word `false`

#### Scenario: The reason is stated once
- **WHEN** the page first shows a value being overridden on the command line
- **THEN** one sentence says that command-line values stay strings, so `=false`
  would read as true

### Requirement: Notes on the page are separated

Consecutive notes SHALL NOT render with their borders touching.

#### Scenario: Two adjacent notes
- **WHEN** two notes appear one after another
- **THEN** there is vertical space between them

#### Scenario: The number of notes is reduced
- **WHEN** the reworked page renders
- **THEN** it carries at most three notes, because a page of asides is a page
  that has not decided what matters
