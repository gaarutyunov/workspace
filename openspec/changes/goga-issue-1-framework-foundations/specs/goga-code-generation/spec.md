## ADDED Requirements

### Requirement: Generator versions are pinned by the module graph

Every code generator a project uses SHALL be pinned as a module tool dependency
rather than installed ambiently.

#### Scenario: A generator's version is declared in the project
- **WHEN** a project uses a generator
- **THEN** its version is declared alongside the project's other dependencies, so
  every developer and every continuous-integration run uses the same one

#### Scenario: No generator is installed out of band
- **WHEN** generation runs
- **THEN** it requires no separately installed binary whose version nobody records

#### Scenario: The framework ships the declaration
- **WHEN** a project adopts the framework
- **THEN** it inherits the pinned set for the house generators rather than
  assembling it

### Requirement: One generation entry point per project

A project SHALL have a single command that runs every generator it declares.

#### Scenario: Everything regenerates in one command
- **WHEN** a developer regenerates a project
- **THEN** one project-wide command runs every generator, and no generator needs
  to be remembered separately

#### Scenario: Configuration is templated, not invented
- **WHEN** a project adds a generator
- **THEN** the framework provides its configuration template, so the generator's
  settings are a house decision rather than a per-project one

### Requirement: Stale generated output fails the build

Generated files SHALL be committed and SHALL be verified current.

#### Scenario: Stale generated output fails
- **WHEN** a generated file no longer matches what its source produces
- **THEN** the required check fails and names the file

#### Scenario: Every declared generator is covered
- **WHEN** a project declares several generators
- **THEN** the check covers all of them, not only the first

#### Scenario: This is the enforcement point for generated wiring
- **WHEN** dependency-injection wiring, query code, protocol stubs, server
  interfaces, mocks or attribute definitions are generated
- **THEN** each is kept current by this one check, rather than each having its own
  remembered step

### Requirement: Generated code compiles against framework seams

Where generated code needs a runtime, the framework SHALL provide the interface it
compiles against, so the generated output inherits framework behaviour unmodified.

#### Scenario: Generated query code uses the portable database handle
- **WHEN** type-safe query code is generated for the house database engine
- **THEN** it compiles against the framework's database handle and inherits its
  instrumentation, with no generated line edited

#### Scenario: A seam constrained by its generator says which adapter it needs
- **WHEN** a generator's runtime interface is expressed in one backend driver's
  own types, so no other adapter could satisfy it
- **THEN** the seam requires that adapter explicitly and fails with a
  distinguishable error under any other, rather than being presented as working
  on every adapter

#### Scenario: Generated protocol services are instrumented
- **WHEN** a service is generated from a protocol definition
- **THEN** the framework's server construction instruments it on the same terms as
  the HTTP server, and the generated output is untouched

#### Scenario: Generated HTTP servers mount through the router interface
- **WHEN** a server is generated from an interface description
- **THEN** it mounts through the framework's router interface

#### Scenario: Attribute definitions are generated, not hand-written
- **WHEN** telemetry attributes are needed
- **THEN** they come from generated constants, and a hand-written attribute key
  where a generated constant exists is reported by the linter

#### Scenario: A project extends the attribute registry without forking it
- **WHEN** a project needs attributes specific to its own domain
- **THEN** it keeps its own registry and generates into its own package, while the
  framework's own attributes stay in the framework

### Requirement: Protocol definitions are linted and checked for breaking changes

Where a project defines a wire protocol, the framework SHALL provide the lint and
compatibility configuration.

#### Scenario: A protocol definition is linted
- **WHEN** a protocol definition changes
- **THEN** it is linted against the house configuration

#### Scenario: A breaking protocol change is detected
- **WHEN** a change would break existing consumers
- **THEN** the check reports it against the default branch rather than leaving it
  to review
