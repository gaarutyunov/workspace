## ADDED Requirements

### Requirement: The project ships a skill that teaches how to author skills with Epos

The repository SHALL carry a skill whose subject is authoring skills with Epos,
packable by the project's own pack command and publishable alongside the other
example skills.

#### Scenario: The skill exists as a skill, not as documentation
- **WHEN** the repository is read
- **THEN** it holds a skill directory with an entry document and reference
  documents, laid out so that the project's own pack command packs it with no
  special handling

#### Scenario: It teaches the whole authoring loop
- **WHEN** the skill's entry document is read
- **THEN** it covers when to reach for Epos and the round trip an author takes —
  packing a skill, publishing it, installing it — and points at each reference
  for the detail rather than restating it

#### Scenario: The references it promises are the ones it carries
- **WHEN** the skill is read
- **THEN** it carries a reference for every command the CLI offers, a reference
  for the composition language, and a reference for values and template syntax

#### Scenario: It is packed and published like any other skill
- **WHEN** the publishing workflow runs
- **THEN** this skill is packed by the project's pack command and published to
  the same registry as the other demo skills, using no tool the project does not
  ship

#### Scenario: The catalog renders it
- **WHEN** the demo catalog is opened
- **THEN** this skill appears in it and its detail page renders its own entry
  document — a skill about authoring skills, delivered through the pipeline it
  describes

### Requirement: The command and composition references are generated, not written

The skill's command reference and composition-language reference SHALL be
produced by the project's existing documentation generator from the same sources
the implementation uses, and SHALL be covered by the drift check that generator
already has.

#### Scenario: The references come from the implementation
- **WHEN** the generated references are compared with their sources
- **THEN** the command reference is derived from the command definitions
  themselves and the composition reference from the instruction table the parser
  uses, so neither restates anything by hand

#### Scenario: One generator, one drift check
- **WHEN** the generator runs
- **THEN** it produces the documentation site's pages and the skill's references
  in the same invocation, checked by the same gate, because a second generator
  with a check of its own is how one of the two quietly stops being checked

#### Scenario: A stale reference fails the build
- **WHEN** a command gains a flag, or an instruction gains a form, and the
  generated references are not regenerated and committed
- **THEN** continuous integration fails naming the stale file

#### Scenario: The generated files say they are generated
- **WHEN** a generated reference is opened
- **THEN** it carries a banner naming the source it was generated from and
  saying not to edit it by hand, so a reader who wants to change the text knows
  where to go

#### Scenario: The registry binary's own surface is covered
- **WHEN** the command reference is read
- **THEN** it documents the registry binary's commands and flags as well as the
  CLI's, because a binary the generator does not walk is a binary whose settings
  no page describes and no drift check protects

#### Scenario: The entry document is not generated
- **WHEN** the entry document is read
- **THEN** it is authored, because there is no machine-readable source for when
  a reader should reach for a tool, and a generated one would be a table of
  contents

### Requirement: The values guidance is authored and is checked against the worked example

The skill SHALL carry guidance on values files, template syntax and what belongs
in values, and that guidance SHALL be consistent with the example skill the
repository ships.

#### Scenario: Values and template syntax are covered
- **WHEN** the values reference is read
- **THEN** it explains how a values file is written, how values are scoped, and
  what the template syntax permits — including that templates are substituted
  and never executed

#### Scenario: It says how to decide what becomes a value
- **WHEN** an author asks what belongs in values
- **THEN** the reference gives criteria rather than a list — including when a
  part of a document's header should be parameterised, and when whether a
  reference is included at all should be a value rather than a separate skill

#### Scenario: The worked example is the repository's own
- **WHEN** the guidance illustrates gating a reference on a value
- **THEN** it uses the example the repository actually ships — a reference
  trimmed to a single language where the upstream carries several — so the
  guidance and the artifact demonstrate each other

#### Scenario: Guidance that the example contradicts is a defect
- **WHEN** the guidance describes a parameter or a stage
- **THEN** it is one the example skill has, so a claim the repository's own
  artifact does not support is caught rather than published

#### Scenario: The skill declares its own contract where the project has one
- **WHEN** the project supports a declared values contract and this skill takes
  parameters
- **THEN** this skill declares them the way it tells its readers to, because a
  skill teaching a practice it does not follow teaches the practice is optional
