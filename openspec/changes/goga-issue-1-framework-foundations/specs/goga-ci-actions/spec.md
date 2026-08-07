## ADDED Requirements

**Milestone: split, because the actions are not a package and each one lands with
the milestone that first needs it — which is what the definition of done requires
of part five. `setup-go`, `go-lint` and `go-test` at M0, for goga's own CI.
`go-test-integration` at **M4**, the first milestone whose tests need a
container, extended at M7 with the godog reporting. `go-generate-check` at M9,
where it is the enforcement for generated wiring. `go-vuln`, `go-release` and
`pages-deploy` at M11, adopted by gopgql and epos — they belong to no module.**

### Requirement: Shared actions encapsulate how the tooling is launched

The invocation of each tool SHALL be provided as a composite action, so projects
own their triggers and jobs but not the commands.

#### Scenario: An action ships with the milestone that needs it
- **WHEN** a milestone introduces a tool that has to run in CI
- **THEN** the composite action for it ships in that same milestone, so no
  milestone runs a new class of test or generator without the CI treatment it
  needs

#### Scenario: The linter can run against the framework's own language version
- **WHEN** the aggregating linter cannot process the Go version the framework
  targets
- **THEN** the lint action builds a linter that can, rather than skipping the
  check or pinning the framework to an older language version

#### Scenario: One place defines each tool's invocation
- **WHEN** a project runs linting, testing or releasing
- **THEN** it references the shared action rather than restating the commands

#### Scenario: The Go version comes from the module
- **WHEN** a workflow does not name a Go version
- **THEN** the version declared in the module file is used

#### Scenario: Tool versions are pinned centrally
- **WHEN** a tool is invoked through a shared action
- **THEN** its version is pinned in the action, so projects pin one thing rather
  than many

#### Scenario: Projects keep what is genuinely theirs
- **WHEN** a project needs its own triggers, permissions, concurrency or a
  bespoke job
- **THEN** it defines them itself — the actions cover steps, not workflows

### Requirement: Generated files are verified to be current

CI SHALL detect generated output that has drifted from its source.

#### Scenario: Stale generated output fails
- **WHEN** a generated file no longer matches what its source produces
- **THEN** the check fails and names the file

#### Scenario: Current generated output passes
- **WHEN** everything is up to date
- **THEN** the check passes and changes nothing

#### Scenario: It covers every generator the project declares
- **WHEN** a project declares multiple generators
- **THEN** the check covers all of them, not only the first

#### Scenario: It is the enforcement point for the house conventions that generate code
- **WHEN** dependency-injection wiring, query code, protocol stubs, server
  interfaces, mocks or telemetry attribute constants are expected to be generated
- **THEN** this one check is what makes each of them required, so none of them
  needs its own remembered step or its own review discipline

### Requirement: The house conventions are checked by a linter, not by review

The shared lint action SHALL run the framework's own rules alongside the standard
ones, so a convention the type system cannot express is still caught before merge.

#### Scenario: Framework rules run in every project
- **WHEN** a project runs the shared lint action
- **THEN** the framework's own rules run as part of it, without the project
  configuring them

#### Scenario: Bypassing a framework surface is reported
- **WHEN** code reaches a wrapped library directly instead of through the
  framework's surface for it
- **THEN** the linter reports the import

#### Scenario: A banned tool is refused by import path
- **WHEN** code imports a tool the house has ruled against, or an unmaintained
  variant of one it has ruled for
- **THEN** the linter refuses that import path — and does so by path rather than
  by module, since a banned library can legitimately appear as an indirect
  dependency of a permitted tool

#### Scenario: The framework's own conventions are checked against itself
- **WHEN** the framework's own repository is linted
- **THEN** the same rules apply to it, including its layout convention

#### Scenario: One lint version, one invocation
- **WHEN** several projects lint
- **THEN** they run the same linter version through the same action, rather than
  each pinning and invoking it their own way

### Requirement: Integration tests report their artefacts even on failure

An integration run SHALL publish its results whether it passed or failed, because
a failing run is when they are most needed.

#### Scenario: Results survive a failing run
- **WHEN** an integration suite fails
- **THEN** its results and any produced artefacts are still uploaded

#### Scenario: No container runtime setup is required
- **WHEN** integration tests run on a standard hosted runner
- **THEN** no additional container-runtime setup step is needed
