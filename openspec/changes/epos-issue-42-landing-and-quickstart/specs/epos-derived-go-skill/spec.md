## ADDED Requirements

### Requirement: One house Go skill derived from several published skills

The repository SHALL carry a worked example under `examples/go-house/` that builds
**one** Go skill from the workspace's existing Go skills, using named stages, and
that produces a coherent skill rather than a concatenation of three.

#### Scenario: Four sources, one artifact
- **WHEN** the example is built
- **THEN** the result is a single skill artifact derived from the house scaffold
  skill, spf13's idiomatic-Go skill, the `golang-pro` skill and the
  testcontainers skill

#### Scenario: The house scaffold skill is the base
- **WHEN** the Skillfile's final stage is read
- **THEN** it continues from the house scaffold skill, and the other three
  contribute through cross-stage copies

#### Scenario: Stage names are chosen knowing they are value scopes
- **WHEN** a file arrives in the artifact through a cross-stage copy
- **THEN** any template action in it resolves against that stage's value scope,
  and the example supplies the values that scope needs

#### Scenario: The artifact declares its own identity
- **WHEN** the example is built
- **THEN** the derived skill's name and version are set explicitly rather than
  inherited, because none of the source skills carries a top-level version the
  packer could use

#### Scenario: The derived skill reads as one skill
- **WHEN** the built skill is inspected
- **THEN** it has one entry document that routes to its reference files, and no
  two reference files give opposing instructions on the same question

### Requirement: The scaffold skill's mandates become parameters

The derived skill SHALL express the house scaffold skill's fixed dependency
mandates as install-time parameters, so a project can turn off what it does not
need.

#### Scenario: The parameterised axes are the ones that vary between projects
- **WHEN** the parameters are read
- **THEN** they cover at least: whether the project has an HTTP API generated
  from an OpenAPI spec, whether it has a generated dependency-injection graph,
  whether it emits telemetry through a semantic-convention registry, and whether
  it has an integration suite running real dependencies in containers

#### Scenario: A disabled feature leaves no trace
- **WHEN** the skill is installed with a feature disabled
- **THEN** the installed files contain neither the guidance for that feature nor
  the tool that only that feature needs

#### Scenario: What is not a parameter stays fixed
- **WHEN** the parameters are read
- **THEN** the configuration library is not among them — it is a standing
  workspace preference, not a per-project choice

#### Scenario: A string parameter is demonstrated alongside the toggles
- **WHEN** the skill is installed
- **THEN** at least one parameter carries a value rather than a switch, so the
  example shows both shapes

### Requirement: Two values profiles, and re-enabling without a rebuild

The example SHALL ship two values profiles that differ in which features are on,
and switching between them SHALL require no rebuild.

#### Scenario: A lean profile for a library
- **WHEN** the lean profile is applied
- **THEN** the features a single-purpose library does not need are off

#### Scenario: A full profile for a service
- **WHEN** the full profile is applied to the same built artifact
- **THEN** the features are on again and the sections are present

#### Scenario: No rebuild between the two
- **WHEN** the second profile is applied
- **THEN** the same artifact already in the local store is installed again, with
  no build step in between

#### Scenario: Booleans are real booleans
- **WHEN** a profile turns a feature off
- **THEN** it does so with a YAML boolean, which the value loader parses as a
  boolean, and not with a command-line assignment that would be stored as a
  string

### Requirement: Content that contradicts the house standard is removed, not shipped

The derivation SHALL drop material from the source skills that conflicts with the
house standard, and each drop SHALL be attributable to a specific conflict rather
than to length.

#### Scenario: The compile-time interface assertion pattern is dropped
- **WHEN** the derived skill is searched for the pattern that asserts interface
  satisfaction with a discarded variable
- **THEN** it is absent, because the house standard forbids writing it

#### Scenario: The layered project structure is dropped
- **WHEN** the derived skill is read for project layout
- **THEN** the reference file prescribing handler/service/repository layers is
  absent, along with the third configuration library, the archived mock
  generator, the blank-import tool file and the deprecated build-tag syntax it
  carries

#### Scenario: The generics reference is dropped
- **WHEN** the derived skill is read for generics guidance
- **THEN** the reference file teaching generic containers and a result type is
  absent, because the idiomatic-Go skill names that shape an anti-pattern

#### Scenario: The static worker pool is dropped
- **WHEN** the derived skill's concurrency material is read
- **THEN** the static worker-pool section is absent while rate limiting and
  pipelines remain

#### Scenario: Redundant material is dropped once, not twice
- **WHEN** two sources cover the same topic
- **THEN** exactly one survives in the derived skill

#### Scenario: The testcontainers material is included by path, not wholesale
- **WHEN** the testcontainers stage contributes to the artifact
- **THEN** only the Go example files the profile needs are copied, not the whole
  skill

### Requirement: Edits to bases the author does not control degrade gracefully

The derivation SHALL prefer line-oriented and pattern-based edits over strict
diffs when editing a skill the author does not own.

#### Scenario: No strict diff against a foreign base
- **WHEN** a section is removed from a vendored skill's document
- **THEN** the edit matches on section boundaries or a pattern, not on a
  context diff that fails on any upstream drift

#### Scenario: A removal of a whole file stays strict
- **WHEN** the derivation removes a file that is no longer there
- **THEN** the build fails, because a path that is not there is a path the recipe
  is wrong about

### Requirement: The example is executed, not merely written down

A test SHALL build the example and install it under both profiles, so the
documentation cannot describe a build that no longer runs.

#### Scenario: The build is exercised
- **WHEN** the test suite runs
- **THEN** the example's Skillfile is built by the real builder

#### Scenario: Both profiles are asserted
- **WHEN** the test installs the built artifact
- **THEN** it asserts the presence of the guarded sections under the full profile
  and their absence under the lean one

#### Scenario: A missing value is caught
- **WHEN** a template action in the example references a value no profile
  supplies
- **THEN** the test fails, because the installer refuses to ship a skill with a
  hole in it

#### Scenario: The default test run stays offline
- **WHEN** the suite runs without the integration build tag
- **THEN** the example's test does not run, because its sources are fetched over
  the network

#### Scenario: The sources are pinned
- **WHEN** a source skill is referenced from a git repository
- **THEN** the reference names a tag or commit, not a moving branch

### Requirement: The example is the one place the recipe lives

The Skillfile and its profiles SHALL exist at exactly one path in the repository,
and every other artifact that needs them SHALL read them from there.

#### Scenario: The quick start does not hold a second copy
- **WHEN** the quick start shows the recipe
- **THEN** it presents the checked-in file's content rather than a hand-maintained
  restatement of it

#### Scenario: Packing and publishing the example consume the same file
- **WHEN** the example is later packed and published to a demo registry
- **THEN** that work builds this file, and does not introduce a second recipe
