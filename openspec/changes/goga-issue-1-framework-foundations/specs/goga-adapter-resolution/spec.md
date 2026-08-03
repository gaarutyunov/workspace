## ADDED Requirements

**Milestone: the shared registry ships at M0 (`goga/registry`); per-module
resolution is delivered with each adapter-bearing module, first at M1
(`goga/telemetry`'s exporter tables), then M2 (`goga/serve`), M4
(`goga/database`) and M6 (`goga/mcp`). The registry is generic over the port an
adapter satisfies and returns adapters as their concrete type, which requires Go
1.27 generic methods.**

### Requirement: One shared registry, generic over the port

The framework SHALL provide a single registration table type, generic over the
port interface an adapter satisfies, and every adapter-bearing module SHALL hold
one for its own port rather than reimplementing the storage.

#### Scenario: A module gains a pluggable surface
- **WHEN** a module needs interchangeable adapters
- **THEN** it instantiates the shared table for its own port and its own key
  convention, so registration, duplicate handling, unknown-key errors and
  inspection behave identically across modules without being written more than
  once

#### Scenario: The registry is generic over the port, not over a concrete type
- **WHEN** the registry is declared for a surface
- **THEN** its type parameter is the port interface that adapters satisfy, and an
  adapter is a struct stored against that port

#### Scenario: An adapter is recovered as its concrete type
- **WHEN** a caller resolves an adapter whose concrete type it already knows
- **THEN** the registry returns that concrete type, so the adapter's own surface
  beyond the port is reachable without a type assertion written at the call site

#### Scenario: A concrete type that does not match is reported, not returned
- **WHEN** a caller asks for a concrete type the stored adapter is not
- **THEN** resolution fails with an error naming both the type requested and the
  type stored, because the language cannot constrain the requested type to the
  registry's port and the check therefore happens at resolution time

#### Scenario: The registry depends on nothing
- **WHEN** the registry is compiled
- **THEN** it imports no other framework package, so no module's use of it can
  create a dependency cycle with the telemetry module

### Requirement: A module's own opener checks the port at compile time

Where a module resolves an adapter it declares, the check that the adapter
satisfies that module's port SHALL be made by the compiler rather than deferred
to resolution time.

#### Scenario: The module declares the adapter constraint
- **WHEN** a module exposes a typed way to open one of its adapters
- **THEN** the adapter type is constrained by a declaration naming both that
  module's port and the settings the adapter consumes, so a type satisfying
  neither is rejected before the program runs

#### Scenario: A type that does not satisfy the port is rejected
- **WHEN** project code asks a module's opener for a type that does not implement
  that module's port
- **THEN** the program does not compile, and the failure names the missing part
  of the contract

#### Scenario: The caller's options reach the adapter
- **WHEN** an adapter needs the caller's settings to construct itself
- **THEN** the module passes the adapter its own settings value, built from
  options typed to that adapter, and the settings type itself may remain
  unexported — so no caller-facing parameter struct appears and no caller needs to
  name the type

#### Scenario: A module whose adapters read nothing passes nothing
- **WHEN** no adapter of a given module reads any setting
- **THEN** that module's opener takes none, and it declares no accessor
  interface, because a parameter no implementation reads is an abstraction with
  no user — the shared registry stores adapters and imposes no opener signature,
  so modules are free to differ here

### Requirement: Adapter configuration is decoded into the adapter's own type

Where configuration selects and configures an adapter, the framework SHALL decode
the configuration into the settings type that adapter declares, and SHALL apply
the caller's options over it.

#### Scenario: Configuration is decoded to the adapter's expected type
- **WHEN** an adapter is opened and configuration exists for it
- **THEN** that configuration is unmarshalled into the settings type the adapter
  declared, and the adapter is initialised from it

#### Scenario: Explicit options take precedence over configuration
- **WHEN** both configuration and options supply the same setting
- **THEN** the option wins, because it is the more specific and more explicit form

#### Scenario: An adapter validates its own settings
- **WHEN** an adapter is initialised with settings it cannot accept
- **THEN** it reports the failure as an error naming the problem, and the module
  wraps it identifying the module and the adapter, rather than panicking or
  starting in a degraded state

#### Scenario: Options are typed to one adapter
- **WHEN** project code passes an option belonging to a different adapter, or
  mixes two adapters' options in one call
- **THEN** the program does not compile

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
  operation, with no separately declared interface

#### Scenario: The shared registry is not the thing instrumented
- **WHEN** the resolution span is emitted
- **THEN** it is emitted by the module that owns the port, not by the shared
  registry, so the registry carries no telemetry dependency and no dependency
  runs both ways between it and the telemetry module
