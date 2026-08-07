## ADDED Requirements

**Milestone: M9 (`goga/di` + `goga/app`, with the `go-generate-check` action).
Adopters: skill-test/go-service, which already pins the maintained wire fork,
then sysgo, whose templates are retargeted to emit framework calls. The two
directories are one deliverable — the provider sets exist to build the
composition root, and the root's unexported fields are what make a generated
injector the only practical route — and the action is the enforcement rather than
an extra.**

### Requirement: Compile-time dependency injection is the house mechanism

Wiring SHALL be generated at compile time, and every framework module SHALL
publish the provider set needed to construct it.

#### Scenario: Each module publishes its providers
- **WHEN** a project wires a framework module
- **THEN** it references that module's exported provider set rather than writing
  constructor calls by hand

#### Scenario: Common compositions are published too
- **WHEN** a project needs a typical composition — a service, a service with
  persistence, a protocol server
- **THEN** a composed provider set exists for it, so the project does not
  reassemble the same union

#### Scenario: Wiring a module cannot omit its telemetry
- **WHEN** a module's provider set is used
- **THEN** it brings that module's instrumentation with it, so a wired module can
  never be an uninstrumented module

#### Scenario: The injection tool is named unambiguously
- **WHEN** a project adds the dependency-injection tool
- **THEN** the guidance names the specific maintained implementation and its
  version pin, so no project adds an unmaintained one

#### Scenario: A missing dependency fails at build time
- **WHEN** a required provider is absent from the wiring
- **THEN** the failure occurs while building, not on the first request

### Requirement: Provider shapes match what the injection tool can consume

Every framework provider SHALL have a shape the generator recognises, so that
wiring a module does what its author intended.

#### Scenario: Teardown actually runs
- **WHEN** a module needs to release something at shutdown — flushing telemetry,
  closing a pool
- **THEN** its provider exposes that in the form the generator recognises as a
  cleanup, so the generated wiring calls it; a shutdown function of any other
  shape would be provided as an ordinary value that nothing ever calls

#### Scenario: A module's options can be supplied through the wiring
- **WHEN** a project wires a module and wants to configure it
- **THEN** there is a stated way to supply that module's options through the
  graph, and configuring one module does not require restating every other

#### Scenario: Provider inputs are unambiguous
- **WHEN** a provider takes a value such as an address or a connection string
- **THEN** that value has its own named type, because the generator matches
  providers by type and two plain strings in one graph are indistinguishable

#### Scenario: A generic constructor is instantiated by the project
- **WHEN** a framework constructor is generic over the project's own type, as
  configuration loading is
- **THEN** the guidance states that the project supplies the instantiation, so
  this is a documented one-liner rather than a generation failure to debug

### Requirement: Generated wiring is enforced, not offered

Hand-written wiring in place of generated wiring SHALL be detected and rejected.

#### Scenario: The composition root cannot be hand-built
- **WHEN** a caller tries to construct the framework's composition root directly
- **THEN** no exported constructor exists for it, so a generated injector is the
  practical route

#### Scenario: Stale generated wiring fails the build
- **WHEN** the wiring source changes and the generated wiring is not regenerated
- **THEN** the required continuous-integration check fails

#### Scenario: Missing generated wiring fails the build
- **WHEN** generated wiring is absent from the repository
- **THEN** the same check fails, so the generated file cannot be quietly omitted

#### Scenario: Providers used outside an injector are reported
- **WHEN** a framework provider is called from ordinary code rather than from a
  generated injector
- **THEN** the linter reports it

#### Scenario: The unmaintained implementation is refused
- **WHEN** a project imports the archived dependency-injection module
- **THEN** the linter rejects that import path

#### Scenario: One generation entry point covers it
- **WHEN** generation runs for a project
- **THEN** the wiring is regenerated as part of the single project-wide generation
  command, not by a separate remembered step
