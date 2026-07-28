## ADDED Requirements

### Requirement: Shared actions encapsulate how the tooling is launched

The invocation of each tool SHALL be provided as a composite action, so projects
own their triggers and jobs but not the commands.

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

### Requirement: Integration tests report their artefacts even on failure

An integration run SHALL publish its results whether it passed or failed, because
a failing run is when they are most needed.

#### Scenario: Results survive a failing run
- **WHEN** an integration suite fails
- **THEN** its results and any produced artefacts are still uploaded

#### Scenario: No container runtime setup is required
- **WHEN** integration tests run on a standard hosted runner
- **THEN** no additional container-runtime setup step is needed
