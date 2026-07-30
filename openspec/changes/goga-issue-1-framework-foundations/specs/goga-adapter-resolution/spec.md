## ADDED Requirements

**Milestone: delivered with each adapter-bearing module, first at M2
(`goga/serve`), then M4 (`goga/database`) and M6 (`goga/mcp`). There is no
milestone for a shared registry — the owner has deferred it until Go ships
generic methods — so this capability specifies how a module resolves an adapter,
and the rules every module's own table must follow identically.**

### Requirement: Each module owns its adapter table, to one shape

Every module with interchangeable adapters SHALL keep its own registration table
in its own package, and every such table SHALL behave identically, so that six
tables cannot drift into six behaviours.

#### Scenario: A module gains a pluggable surface
- **WHEN** a module needs interchangeable adapters
- **THEN** it declares its own table — registration, lookup, and an inspectable
  list of what is registered — following the same shape as every other module's,
  rather than inventing its own semantics for duplicates, unknown names or
  errors

#### Scenario: There is no shared registry to depend on
- **WHEN** a module resolves an adapter
- **THEN** it does so without a framework-wide registry type, because a registry
  that stores an implementation against a port interface and returns that
  implementation's own concrete type cannot be expressed in the language today

#### Scenario: The deferred registry is described, not designed around
- **WHEN** the shared registry becomes expressible
- **THEN** it is generic over the port interface an adapter satisfies, stores the
  structs that satisfy it and returns their concrete types, and the modules'
  tables collapse into it with no change to any registration call

#### Scenario: Adapters are typed, not asserted
- **WHEN** an adapter is resolved
- **THEN** it comes back as the module's declared adapter type without a type
  assertion at the call site

#### Scenario: The caller's options reach the adapter
- **WHEN** an adapter needs the caller's settings to construct itself
- **THEN** the module passes them as a read-only accessor interface that the
  adapter names in its own signature, while the settings type itself stays
  unexported — so an adapter reads a value it can neither construct nor mutate,
  and no caller-facing parameter struct appears

#### Scenario: A module whose adapters read nothing passes nothing
- **WHEN** no adapter of a given module reads any setting
- **THEN** that module's opener takes none, and it declares no accessor
  interface, because a parameter no implementation reads is an abstraction with
  no user — the modules are free to differ here now that no shared registry
  imposes one signature on all of them

#### Scenario: The accessor interface has one home
- **WHEN** an adapter author looks for the accessor interface to name
- **THEN** it is in the same package as the port interface being implemented,
  which the adapter already imports, rather than in a different package per
  module

### Requirement: Adapters self-register and are selected by name

An adapter SHALL register itself, and a caller SHALL select one by naming it.

#### Scenario: Selection is by scheme where there is a URL
- **WHEN** a caller supplies a connection URL
- **THEN** the adapter registered under that URL's scheme is used

#### Scenario: Selection is by plain name where there is no URL
- **WHEN** a surface selects its adapter by name alone — a router, an exporter, a
  protocol transport, a deployer — with no connection URL to carry it
- **THEN** that module's table is keyed by the name directly, and neither the
  caller nor the module composes a URL whose scheme would not be the adapter's
  name

#### Scenario: A module keyed one way does not carry the other
- **WHEN** a module resolves by name
- **THEN** nothing in its resolution path parses or synthesises a URL, so the
  failure where a synthesised scheme resolves to the wrong key cannot occur

#### Scenario: An adapter's dependency is optional
- **WHEN** a project does not use a given adapter
- **THEN** that adapter's third-party dependency does not enter the project's
  module graph

#### Scenario: A duplicate registration is a programming error
- **WHEN** two adapters register the same key in one module
- **THEN** the conflict surfaces immediately at initialisation rather than
  producing an arbitrary winner at first use

#### Scenario: An unknown adapter is self-diagnosing
- **WHEN** a caller names an adapter nothing registered
- **THEN** the failure names the module, the name that was asked for, the ones
  that are registered, and the likely cause — a missing adapter import — and it
  reads the same way whichever module produced it

#### Scenario: The registered set is inspectable
- **WHEN** a caller or a diagnostic needs to know what is available
- **THEN** the module reports what is registered

#### Scenario: A project can add an adapter but cannot ask for a raw one
- **WHEN** a project registers an adapter the framework does not ship
- **THEN** registration is exported so that it can, and lookup is not — no
  framework entry point returns an adapter-level object, so the framework never
  hands back something uninstrumented

### Requirement: Resolution is observable

Adapter resolution SHALL be instrumented by the module that performs it.

#### Scenario: Resolution produces telemetry
- **WHEN** an adapter is resolved
- **THEN** the resolution is recorded with the module and the adapter selected,
  because which adapter a process actually selected is an operational question

#### Scenario: A failed resolution is recorded
- **WHEN** resolution fails
- **THEN** the failure is recorded with its error type

#### Scenario: Resolution telemetry needs no special arrangement
- **WHEN** a module records a resolution
- **THEN** it uses the same instrumentation handle it uses for every other
  operation, with no separately declared interface and no dependency running both
  ways between a registry and the telemetry module
