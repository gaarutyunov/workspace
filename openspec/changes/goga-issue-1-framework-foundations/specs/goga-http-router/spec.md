## ADDED Requirements

### Requirement: The HTTP router is a replaceable adapter

Routing SHALL be expressed through one framework interface with interchangeable
router adapters, so choosing a router is a configuration decision rather than a
rewrite.

#### Scenario: A route is registered once, against the framework
- **WHEN** an application registers a route or middleware
- **THEN** it does so against the framework's router interface, not against a
  specific router library

#### Scenario: Changing router does not change handlers
- **WHEN** a project switches its router
- **THEN** its handlers and route registrations compile and behave unchanged

#### Scenario: The standard library is the default
- **WHEN** no router is named
- **THEN** the standard library's router is used, so a project pays for no router
  dependency it did not ask for

#### Scenario: The full-featured routers are available as adapters
- **WHEN** a project names one of the supported third-party routers
- **THEN** that adapter is used, resolved through the framework's adapter registry

#### Scenario: The interface stays narrow
- **WHEN** a new router adapter is written
- **THEN** it implements serving, route registration and middleware registration
  and nothing more — enough for generated server code to mount on it

#### Scenario: The native router remains reachable
- **WHEN** a project needs a router-specific feature the interface does not model
- **THEN** the underlying router object is available

#### Scenario: Path parameter syntax is translated
- **WHEN** a route pattern uses the framework's parameter syntax
- **THEN** the adapter translates it to its router's own syntax, so one pattern
  works on every adapter

### Requirement: Instrumentation is attached above the router, exactly once

Request instrumentation SHALL be applied by the server to whichever router is in
use, and SHALL NOT be implemented by any router adapter.

#### Scenario: Requests are traced identically on every adapter
- **WHEN** the same application runs on different router adapters
- **THEN** the request spans and metrics are the same

#### Scenario: A router adapter carries no telemetry
- **WHEN** a router adapter is written
- **THEN** it contains no instrumentation, and its routes are instrumented anyway

#### Scenario: Instrumentation is not applied twice
- **WHEN** the server composes the router
- **THEN** request instrumentation is applied once, so a request produces one
  server span

#### Scenario: The router's own logging does not compete with the house logger
- **WHEN** a router adapter's library ships its own request logger
- **THEN** it is not enabled, so structured logging has a single source

### Requirement: Generated server code mounts on any adapter

Server code produced from an interface description SHALL mount through the router
interface.

#### Scenario: A generated server runs on any router
- **WHEN** a project generates its HTTP server from its interface description
- **THEN** the generated server mounts through the framework's router interface and
  runs unchanged on every adapter
