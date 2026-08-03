## ADDED Requirements

**Milestone: M2 (`goga/serve`, with its listener port, the standard-library
listener and the conformance suite) — the owner's *"http with telemetry for
gopgql and epos"*. Adopters: epos, then gopgql.**

**This capability was narrowed in the current revision (design D22).** The
previous version specified a router interface — route registration, middleware
registration, and a framework path-parameter syntax each adapter translated —
with `gin`, `chi` and `mux` adapters behind it. It no longer does. The evidence
was already in that version's own requirements: it had to specify that middleware
registered after a route is *rejected as a programming error* precisely because
the three routers disagree about what it means, and it had to specify pattern
translation because they disagree about that too. Those are the symptoms of a
port drawn wider than its implementations genuinely share.

What replaces it is the narrowest thing all three already agree on: the standard
library's handler interface. A router is now the application's own choice and
needs no framework adapter, while everything the module actually exists for —
tracing, operational endpoints, bounded timeouts, one graceful drain — applies to
all of them uniformly.

### Requirement: The server accepts any standard HTTP handler

The server SHALL take the application's handler as the standard library's handler
interface, and SHALL NOT require the application to register routes through a
framework-specific routing interface.

#### Scenario: A project brings its own router
- **WHEN** an application builds its routes with the standard library, or with
  either of the supported third-party routers
- **THEN** it passes the result to the server directly, because all three are
  already standard handlers, and no framework adapter sits between them

#### Scenario: Routing features are not diminished
- **WHEN** an application uses a routing feature specific to its router — a route
  group, a binding helper, a router-specific middleware signature
- **THEN** it is available in full, because the framework does not model routing
  and therefore cannot fail to model a part of it

#### Scenario: The framework does not translate route patterns
- **WHEN** an application declares a route
- **THEN** it uses its own router's pattern syntax directly, and no framework
  translation step exists that could disagree with it

#### Scenario: Middleware ordering is the router's own contract
- **WHEN** an application registers middleware
- **THEN** it does so through its own router, whose documented behaviour applies
  unchanged, and the framework neither reinterprets nor rejects the ordering

#### Scenario: A project pays for no router it did not choose
- **WHEN** a project uses the standard library's router
- **THEN** no third-party router dependency enters its module graph

#### Scenario: Framework middleware still applies to everything
- **WHEN** the server is configured with framework-level middleware
- **THEN** it wraps the application's whole handler, so its coverage does not
  depend on which router is inside or on the order routes were registered

### Requirement: The replaceable part is the listener, not the router

Where the server's behaviour is pluggable, the seam SHALL be the mechanism that
listens and serves, and it SHALL be narrow enough that two implementations
genuinely agree.

#### Scenario: The default listener is the standard library's
- **WHEN** no listener is named
- **THEN** the standard library's server is used

#### Scenario: An alternative listener is an adapter
- **WHEN** a project needs a different way to listen — a cleartext HTTP/2
  listener, a Unix socket, an in-process test listener
- **THEN** it supplies one through the module's listener port, and the
  application's handler is unaffected

#### Scenario: The listener port stays narrow
- **WHEN** a listener adapter is written
- **THEN** it implements serving a handler at an address and shutting down, and
  nothing else

#### Scenario: An optional capability arrives as a separate interface
- **WHEN** a listener supports something not every listener can, such as serving
  TLS
- **THEN** it is expressed as an additional interface the server tests for, so no
  listener that lacks the capability has to declare a stub, and adding the
  capability breaks no existing adapter

#### Scenario: A second listener brings a conformance suite with it
- **WHEN** a second listener adapter is published
- **THEN** a conformance suite is introduced at that point and both listeners
  pass it — v1 ships one listener, and a conformance suite for one
  implementation establishes nothing

#### Scenario: Adopting projects get test helpers regardless
- **WHEN** a project adopts the module
- **THEN** the framework provides helpers to assert, against the project's own
  handler, that a request is traced exactly once, that the operational paths are
  not traced, that a configured timeout is enforced, and that an in-flight
  request survives a drain — these are properties of the server rather than of a
  listener, which is why they are helpers and not a conformance suite

### Requirement: Instrumentation is attached above the handler, exactly once

Request instrumentation SHALL be applied by the server to whatever handler it is
given, and SHALL NOT be implemented by the application or by a listener adapter.

#### Scenario: Requests are traced identically whatever the router
- **WHEN** the same application runs behind different routers
- **THEN** the request spans and metrics are the same, because the
  instrumentation wraps the handler from outside

#### Scenario: A listener adapter carries no telemetry
- **WHEN** a listener adapter is written
- **THEN** it contains no instrumentation, and requests are instrumented anyway

#### Scenario: Instrumentation is not applied twice
- **WHEN** the server composes the handler
- **THEN** request instrumentation is applied once, so a request produces one
  server span

#### Scenario: There is no untraced path to the application
- **WHEN** an application's handler reaches the process
- **THEN** it does so through the server's constructor, so it cannot be served
  uninstrumented — and the linter enforces this rather than banning the router
  library outright

#### Scenario: The router's own logging does not compete with the house logger
- **WHEN** an application's router ships its own request logger
- **THEN** the framework's guidance and template disable it, so structured
  logging has a single source

### Requirement: Generated server code needs no adapter

Server code produced from an interface description SHALL run without a framework
routing seam.

#### Scenario: A generated server runs unchanged
- **WHEN** a project generates its HTTP server from its interface description
- **THEN** the generated server is already a standard handler, so it is passed to
  the server directly and runs on whichever router the project generated it for
