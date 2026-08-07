## ADDED Requirements

**Milestone: the shared registry ships at M0 (`goga/registry`); per-module
resolution is delivered with each adapter-bearing module, first at M1
(`goga/telemetry`'s exporter tables), then M2 (`goga/serve`'s listener) and M6
(`goga/mcp`'s transports). The registry stores a typed constructor per adapter
name and needs no language feature newer than the framework's stated floor;
`goga/database` has no adapter table at all (design D7).**

### Requirement: A port is bound to an adapter by one of three mechanisms, and the static ones are the default

The framework SHALL support binding a port to an adapter statically at build
time, and SHALL provide the registry only for the case where configuration must
choose at run time.

#### Scenario: The adapter is known when the program is built
- **WHEN** a composition root knows which adapter it wants
- **THEN** it binds the port to the adapter through the dependency-injection
  mechanism, with no registry, no name string and no adapter import for its side
  effect

#### Scenario: The adapter is known but its own settings must be configured
- **WHEN** a composition root wants one named adapter and that adapter's own
  options
- **THEN** it uses the typed handle produced when the adapter was registered, so
  both the port and the settings type are static and no name is resolved at run
  time

#### Scenario: Configuration chooses the adapter
- **WHEN** the adapter is named in configuration and is not known when the
  program is built
- **THEN** the registry resolves it by name, and this is the only binding
  mechanism whose failure is deferred to run time

#### Scenario: A statically known adapter is not resolved through a string
- **WHEN** project code resolves an adapter by a name that is a string literal
- **THEN** the linter reports it, because a literal means the adapter was known
  at build time and one of the static mechanisms was available

### Requirement: One shared registry, storing a typed constructor per adapter

The framework SHALL provide a single registration mechanism that every
adapter-bearing module uses, rather than each module reimplementing the storage.

#### Scenario: A module gains a pluggable surface
- **WHEN** a module needs interchangeable adapters
- **THEN** it uses the shared registry, so registration, duplicate handling,
  unknown-name errors and inspection behave identically across modules without
  being written more than once

#### Scenario: The registry is a value the composition root owns
- **WHEN** an application assembles its adapters
- **THEN** it constructs a registry, attaches each adapter to it explicitly, and
  passes it to the modules that need it — there is no framework-wide default
  registry, and no adapter attaches itself as a side effect of being imported

#### Scenario: A registered adapter can be injected
- **WHEN** a composition root passes the handle returned by registration to
  another provider, or holds it as a field
- **THEN** it can name that handle's type without naming the adapter's settings
  type, because the adapter package exports an alias for it — a handle usable
  only as a local variable would be unusable under the framework's
  dependency-injection rule

#### Scenario: Concurrent registration and inspection are safe
- **WHEN** one goroutine registers an adapter while another lists what is
  registered
- **THEN** neither observes a partially updated registry, and the race detector
  reports nothing

#### Scenario: Two registries do not interfere
- **WHEN** a test constructs its own registry and registers an adapter under a
  name another test also uses
- **THEN** neither affects the other, because duplicate detection is scoped to a
  single registry

#### Scenario: Registration is typed at the point of registration
- **WHEN** an adapter registers itself
- **THEN** what is stored is a constructor from that adapter's settings type to
  the port, so an adapter that does not satisfy the port cannot be registered

#### Scenario: Retrieval is checked against what was registered
- **WHEN** a caller resolves an adapter as a port
- **THEN** the port it asks for is compared against the port the adapter was
  registered for, and a mismatch is an error naming both — a structural check
  alone is not sufficient, because an unrelated interface with the same method
  set would otherwise be accepted

#### Scenario: A module keeps its own typed registration surface
- **WHEN** a module offers adapters
- **THEN** adapter authors and composition roots use that module's own named
  registration function, which takes a context and the module's settings
  accessor — the shared registry is what that surface is implemented over, not
  what callers use directly

#### Scenario: Neither type is named by the registering package's callers
- **WHEN** an adapter is registered
- **THEN** both the port type and the settings type are inferred from the
  constructor, so no other package names either of them

#### Scenario: The constructor shape is fixed across the framework
- **WHEN** any adapter in any module is registered
- **THEN** its constructor takes a context and the settings value, and returns
  the port and an error — one registration shape for every module

#### Scenario: Construction can be cancelled
- **WHEN** an adapter performs I/O to construct itself — dialling a collector,
  binding a listener, opening a socket
- **THEN** it receives the context the caller opened it with, so a startup that
  is cancelled or times out does not block on a half-built adapter
- **AND** the context is a parameter of the constructor rather than a field of
  the settings, because settings are decoded from configuration and a context
  is not configuration

#### Scenario: The registry depends on nothing
- **WHEN** the registry is compiled
- **THEN** it imports no other framework package and no third-party package, so
  no module's use of it can create a dependency cycle with the telemetry module

### Requirement: Going from a port to a concrete adapter type is an escape hatch, and it is honest about being checked at run time

Where a caller needs an adapter's own surface beyond the port, the framework
SHALL provide one documented way to reach it, and SHALL NOT present it as a
compile-time operation.

#### Scenario: A caller reaches the underlying implementation
- **WHEN** project code holds a framework type and needs the underlying
  implementation's own surface
- **THEN** it uses the single escape-hatch method, which reports whether the
  conversion succeeded rather than returning a value that may be wrong

#### Scenario: The escape hatch failing is not an error
- **WHEN** the escape hatch reports that the requested type is not available
- **THEN** the calling code is expected to skip the implementation-specific
  behaviour and continue, so the same code still runs against a different
  adapter

#### Scenario: The conversion is documented as a run-time check
- **WHEN** an adapter author or a caller reads the escape hatch's documentation
- **THEN** it states that the conversion is checked when it runs, because the
  concrete type behind a port is not known to the compiler at that point

#### Scenario: Every adapter documents what it supports
- **WHEN** an adapter is published
- **THEN** its package documentation lists the types its escape hatch supports,
  including stating that it supports none

### Requirement: Adapter configuration is decoded into the adapter's own type

Where configuration selects and configures an adapter, the framework SHALL decode
the configuration into the settings type that adapter declares, and SHALL apply
the caller's options over it.

#### Scenario: Configuration is decoded to the adapter's expected type
- **WHEN** an adapter is opened and configuration exists for it
- **THEN** that configuration is unmarshalled into the settings type the adapter
  declared, and the adapter is constructed from it

#### Scenario: The decoder is supplied, not assumed
- **WHEN** the registry decodes configuration into an adapter's settings type
- **THEN** it uses a decoder given to it at construction rather than choosing
  one, because the framework's configuration library and its struct tags are not
  the registry's to know — a registry that picked a standard-library decoder
  would silently ignore every field tagged for the configuration library

#### Scenario: An unknown setting is an error, not a zero value
- **WHEN** configuration contains a key the adapter's settings type does not
  declare, or a key whose tag the decoder does not match
- **THEN** it is reported at startup rather than discarded, so a mistyped or
  renamed setting cannot leave an adapter running on a default nobody chose

#### Scenario: Explicit options take precedence over configuration
- **WHEN** both configuration and options supply the same setting
- **THEN** the option wins, because it is the more specific and more explicit form

#### Scenario: The settings type stays unexported
- **WHEN** an adapter declares the settings it consumes
- **THEN** that type may remain unexported, and a package that configures the
  adapter correctly is still unable to name, construct or embed it

#### Scenario: An adapter validates its own settings
- **WHEN** an adapter is constructed with settings it cannot accept
- **THEN** it reports the failure as an error naming the problem, and the module
  wraps it identifying the module and the adapter, rather than panicking or
  starting in a degraded state

#### Scenario: Options are typed to one adapter
- **WHEN** project code passes an option belonging to a different adapter, or
  mixes two adapters' options in one call
- **THEN** the program does not compile

#### Scenario: The caller does not name a settings type on the dynamic path
- **WHEN** an adapter is chosen by a name that is only known at run time
- **THEN** the caller supplies the configuration as data and does not name the
  adapter's settings type, because a type cannot be recovered from a runtime
  string — and the framework does not offer a form that asks the caller to
  assert one

### Requirement: Adapters self-register and are selected by name

An adapter SHALL register itself, and a caller SHALL select one by naming it.

#### Scenario: Selection is by a plain adapter name
- **WHEN** any adapter in any module is selected through the registry
- **THEN** the key is the adapter's plain name, and neither the caller nor the
  module composes or parses a URL in order to select it

#### Scenario: A connection URL is configuration, not a selector
- **WHEN** a module takes a connection URL or DSN
- **THEN** that string is passed to the one implementation that module uses, and
  its scheme does not choose an adapter

#### Scenario: An adapter's dependency is optional
- **WHEN** a project does not use a given adapter
- **THEN** that adapter's third-party dependency does not enter the project's
  module graph

#### Scenario: A duplicate registration is reported, not fatal
- **WHEN** two adapters register the same name in one registry
- **THEN** registration returns an error naming the conflict rather than
  panicking, because the registry is an explicitly constructed value and the
  duplicate is detected while ordinary startup code is running
- **AND** the conflict surfaces immediately rather than producing an arbitrary
  winner at first use

#### Scenario: An unknown adapter is self-diagnosing
- **WHEN** a caller names an adapter nothing registered
- **THEN** the failure names the module, the name that was asked for, the ones
  that are registered, and the likely cause — an adapter that was never attached
  to this registry — and it reads the same way whichever module produced it

#### Scenario: The failure names types by their declared name
- **WHEN** a resolution failure mentions the port or the adapter type
- **THEN** it prints the declared type name rather than formatting a zero value,
  so a nil interface does not render as an empty placeholder

#### Scenario: The registered set is inspectable
- **WHEN** a caller or a diagnostic needs to know what is available
- **THEN** the module reports what is registered

#### Scenario: A project can add an adapter but cannot ask for a raw one
- **WHEN** a project registers an adapter the framework does not ship
- **THEN** registration is exported so that it can, and what resolution returns
  is the module's own instrumented type, so the framework never hands back
  something uninstrumented

### Requirement: Resolution is observable

Adapter resolution SHALL be instrumented by the module that performs it.

#### Scenario: Resolution produces telemetry
- **WHEN** an adapter is resolved
- **THEN** the resolution is recorded with the module and the adapter selected,
  because which adapter a process actually selected is an operational question

#### Scenario: A failed resolution is recorded
- **WHEN** resolution fails
- **THEN** the failure is recorded with its error type

#### Scenario: The adapter is identified without the adapter declaring it
- **WHEN** a resolution is recorded
- **THEN** the adapter's identity is derived from the adapter itself rather than
  from a name the adapter had to declare, so a newly written adapter is
  identified correctly without its author doing anything

#### Scenario: Resolution telemetry needs no special arrangement
- **WHEN** a module records a resolution
- **THEN** it uses the same instrumentation handle it uses for every other
  operation, with no separately declared interface

#### Scenario: The shared registry is not the thing instrumented
- **WHEN** the resolution span is emitted
- **THEN** it is emitted by the module that owns the port, not by the shared
  registry, so the registry carries no telemetry dependency and no dependency
  runs both ways between it and the telemetry module
