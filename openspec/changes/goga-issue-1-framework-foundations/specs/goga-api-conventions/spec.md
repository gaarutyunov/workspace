## ADDED Requirements

**Milestone: spec-wide. The option and settings shape is fixed at M0 with the
root package and is binding on every module from M1 onward; the telemetry
invariant becomes checkable at M1 and is re-checked by every later milestone; the
escape-hatch and error requirements apply to each module as it lands. No
requirement here waits for a milestone of its own.**

### Requirement: Construction is by variadic options, never by a parameter struct

Every exported constructor and every exported entry point SHALL accept a variadic
list of option functions, and the framework SHALL NOT expose a parameter struct
for a caller to populate.

#### Scenario: A caller configures by passing options
- **WHEN** a caller constructs any part of the framework with non-default settings
- **THEN** it passes option functions, and the call site reads as a list of named
  choices rather than as a struct literal

#### Scenario: A settings type cannot be named by a caller
- **WHEN** a caller looks for a settings type to fill in
- **THEN** there is none to find: the type is unexported, so no other package can
  name it, construct it or embed it, and the only populated instance in existence
  is the one the framework builds from the caller's options

#### Scenario: There is no exported struct in the caller-facing option surface
- **WHEN** any module's public surface is examined for a struct a *caller* could
  populate and pass to the framework
- **THEN** none exists, so the alternative to options is unspellable rather than
  merely unaccepted

#### Scenario: Types that cross the port to an adapter are exported, and that is not an exception
- **WHEN** a port hands an adapter per-call options, or a conformance suite in a
  third package constructs them
- **THEN** those types are exported, because an adapter in another package must
  name them in its method signatures to implement the port at all — and this is
  not a way round the rule above, because no framework entry point accepts one
  from a caller and constructing one yields nothing usable

#### Scenario: An adapter receives the module's settings without naming the struct
- **WHEN** an adapter in its own package implements its module's port and needs
  values the caller gave the *module*
- **THEN** it names a read-only interface of accessors, or the exported
  driver-side options type, and can neither construct nor mutate the module's own
  settings behind it — which is what allows that struct to stay unexported

#### Scenario: An adapter's own settings are configured by options too
- **WHEN** an adapter has settings of its own, distinct from its module's
- **THEN** they are supplied by options typed to that adapter, not by a parameter
  struct, and the adapter's settings type may itself stay unexported because no
  caller has to name it

#### Scenario: Options remain statically typed wherever the adapter is known at build time
- **WHEN** an adapter is selected statically or through its typed handle
- **THEN** its options are functions typed to that adapter's own settings type,
  fully checked by the compiler, and no parameter struct appears — so the
  parameter-struct fallback is not taken on any path where it could be avoided

#### Scenario: The dynamic path takes configuration as data, and says why
- **WHEN** an adapter is chosen by a name that is only known at run time
- **THEN** its configuration is supplied as a decoded data node rather than as a
  typed struct the caller names, because a type cannot be recovered from a
  runtime string — and the framework decodes that node into the adapter's own
  settings type rather than asking the caller to assert it
- **AND** the framework documents this as the one place the caller does not get
  static checking, rather than describing every path as equally typed

#### Scenario: An option can be held and passed without naming what it mutates
- **WHEN** a caller stores or forwards a module's options
- **THEN** the option type is exported and usable on its own terms, even though
  the type it mutates is not

#### Scenario: An option validates its own input
- **WHEN** an option is given a value outside its permitted range
- **THEN** construction fails naming the option and the offending value, rather
  than accepting it and failing at first use

#### Scenario: Defaults apply when an option is omitted
- **WHEN** a caller omits an option
- **THEN** the documented default applies, and the caller does not have to restate
  it

#### Scenario: Option names follow one pattern
- **WHEN** an option is added to any module
- **THEN** its name follows the house pattern for setting, appending and removing,
  so options read the same way across modules

#### Scenario: Adding an option does not break callers
- **WHEN** a new option is added to a module
- **THEN** existing call sites continue to compile unchanged

### Requirement: The language version requirement is explicit and justified

The framework SHALL state the Go version it requires, and SHALL require a version
newer than the current stable release only where a capability depends on it.

#### Scenario: The requirement is discoverable before adoption
- **WHEN** a project considers adopting any part of the framework
- **THEN** the required Go version is stated in the framework's own documentation
  and skill, because the requirement propagates into the adopting project's own
  module and cannot be scoped to the package that needs it

#### Scenario: A pre-release toolchain is named as such
- **WHEN** the required version is a release candidate rather than a stable release
- **THEN** that is stated plainly rather than implied, together with the
  consequence that a default toolchain setting will fetch and use it silently
  while a pinned one will fail the build outright

#### Scenario: Enforcement tooling keeps working across the version bump
- **WHEN** the framework requires a language version its linting tools cannot yet
  process
- **THEN** the framework ships a way to run those tools anyway, because a version
  bump that silently disables the enforcement would defeat the framework's own
  reason for existing

### Requirement: Every part of the framework is instrumented

Every module of the framework that performs a runtime operation SHALL emit
telemetry for its operations, and no such module SHALL be exempt or offer a way
to disable it.

#### Scenario: Each module's operations produce telemetry
- **WHEN** any framework operation runs — loading configuration, resolving an
  adapter, running a query, applying a migration, serving a request, making an
  outbound call, handling a protocol request
- **THEN** it produces a span, records its duration, and on failure records the
  error type using the official conventions

#### Scenario: Telemetry cannot be switched off
- **WHEN** a caller looks for a way to construct a framework object without
  instrumentation
- **THEN** none exists; instrumentation can be replaced but not removed

#### Scenario: Instrumentation lives above the adapter
- **WHEN** a new adapter is written for any pluggable surface
- **THEN** it is instrumented without its author adding anything, because the
  instrumentation belongs to the portable type that wraps it

#### Scenario: An adapter cannot produce a portable object
- **WHEN** an adapter returns its result
- **THEN** it returns the adapter-level type, and only the module's own entry
  point can wrap that into the portable type — so no framework constructor
  returns an uninstrumented object

#### Scenario: No framework entry point returns an adapter-level object
- **WHEN** a caller looks for a way to ask the framework for an adapter rather
  than the portable object that wraps it
- **THEN** none exists: registration is exported so a project can supply its own
  adapter, and lookup is not

#### Scenario: The remaining route to an uninstrumented object is reported
- **WHEN** a project that registered its own adapter calls that adapter's own
  constructor directly, which is its own code and outside the framework's reach
- **THEN** the linter reports it, because the guidance states the strength of
  each mechanism honestly rather than claiming an impossibility

#### Scenario: Coverage is verified, not asserted
- **WHEN** the framework's own tests run
- **THEN** a test compares the set of modules that obtained instrumentation
  against the module list, and fails both when a module performing runtime
  operations has none and when a module is added to the exempt set

#### Scenario: A module with no runtime operation is named, not silently skipped
- **WHEN** a module produces only compile-time or generation-time artefacts —
  generated constants, lint analysers, wiring definitions
- **THEN** it has no operation to record, and it is named in the exempt set the
  test checks, rather than being quietly absent from an enumeration

#### Scenario: A library consumer without a configured backend still works
- **WHEN** a library uses a framework module in a process that never configures
  telemetry
- **THEN** the operations succeed against no-op providers, and telemetry appears
  as soon as a consuming binary configures it

### Requirement: A streaming result outlives the call that returned it

Where any framework API returns a result the caller reads incrementally, that
result SHALL remain usable until the caller closes it.

#### Scenario: A returned stream is readable
- **WHEN** a caller receives a stream and begins reading it
- **THEN** it reads successfully, because neither the operation's timeout nor its
  instrumentation was released when the call returned

#### Scenario: The recorded duration covers the read
- **WHEN** the stream is closed
- **THEN** the operation's recorded duration covers the whole read, not only the
  call that started it

#### Scenario: Closing releases everything, once
- **WHEN** a stream is closed, whether after a full read or an abandoned one
- **THEN** the timeout and the recording are released exactly once, and closing
  again is harmless

#### Scenario: A failed read is recorded as a failure
- **WHEN** an error occurs partway through reading
- **THEN** the operation is recorded as failed rather than as the success it
  appeared to be when the call returned

### Requirement: Every wrapper exposes what it wraps

Each wrapper SHALL provide access to the underlying object it composes.

#### Scenario: The underlying object is reachable
- **WHEN** a caller needs behaviour the wrapper does not model
- **THEN** the wrapper hands back the underlying object rather than trapping the
  caller

#### Scenario: The accessor is discoverable
- **WHEN** a caller looks for the escape hatch
- **THEN** it is named consistently across modules — a generic unwrap where the
  type is opaque, a named accessor where it is not

#### Scenario: An escape hatch is not an unenforced convention
- **WHEN** the guidance describes an escape hatch
- **THEN** it is documented as a supported route, and is not counted among things
  the framework fails to enforce

### Requirement: Failures are recorded and reported consistently

An operation's recorded outcome SHALL match the outcome the caller receives, and
every error the framework returns SHALL identify where it came from.

#### Scenario: A failed operation is recorded as failed
- **WHEN** an operation returns an error through any of its exit paths
- **THEN** the telemetry for that operation records the failure and its error
  type, rather than recording success because the failure left by a different
  path

#### Scenario: The recorded duration is the operation's duration
- **WHEN** an operation's duration is recorded
- **THEN** the elapsed time is measured by the framework from the point the
  operation began, not supplied by the call site

#### Scenario: An error names its origin
- **WHEN** an error crosses a framework boundary
- **THEN** it is wrapped identifying the module and the operation, and the
  original error remains inspectable

#### Scenario: A caller that must branch gets a distinguishable error
- **WHEN** a caller has to distinguish one failure from another — an unknown
  adapter, a missing required key, an unsupported capability
- **THEN** the error is a distinct type or value it can test for, rather than a
  string to match
