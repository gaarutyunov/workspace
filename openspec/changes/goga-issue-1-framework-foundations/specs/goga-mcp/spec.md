## ADDED Requirements

### Requirement: MCP servers are built through the framework

An MCP server SHALL be constructed through a framework module rather than against
the protocol SDK directly, because more than one project exposes one.

#### Scenario: A project exposes tools without SDK boilerplate
- **WHEN** a project registers a tool
- **THEN** it supplies a name, a description and a plain function over ordinary
  input and output types, and writes no protocol plumbing

#### Scenario: Two projects get one implementation
- **WHEN** a second project needs an MCP server
- **THEN** it uses the same module, rather than reproducing the first project's
  server, so the two cannot drift to different SDK versions with different
  behaviour

#### Scenario: Resources and prompts are covered too
- **WHEN** a project exposes a resource or a prompt
- **THEN** the module provides the same registration treatment as for tools

#### Scenario: The SDK server remains reachable
- **WHEN** a project needs SDK behaviour the module does not model
- **THEN** the underlying SDK server is available

### Requirement: Every MCP operation is instrumented

Tool calls, resource reads and prompt renders SHALL each produce telemetry, added
by the framework and not by the author of the handler.

#### Scenario: A tool call is traced and measured
- **WHEN** a tool is invoked
- **THEN** the call produces a span identifying the tool and the session, records
  its duration, and on failure records the error type

#### Scenario: A resource read and a prompt render are also recorded
- **WHEN** a resource is read or a prompt is rendered
- **THEN** the operation is traced and measured on the same terms as a tool call

#### Scenario: The handler author adds nothing
- **WHEN** a tool function is written
- **THEN** it contains no telemetry code, and the telemetry is present anyway

#### Scenario: There is no uninstrumented registration path
- **WHEN** a caller looks for a way to register a tool directly on the SDK server
- **THEN** the framework's registration function is the only path, so an
  uninstrumented tool cannot be registered through the framework

#### Scenario: Trace context crosses the protocol boundary
- **WHEN** a framework MCP client calls a framework MCP server
- **THEN** the trace context is propagated by a stated convention, so a call
  spanning both appears as one trace

### Requirement: Failures and timeouts are handled by the protocol's rules

The module SHALL translate handler outcomes into the protocol's own error model.

#### Scenario: A handler error is reported in-band
- **WHEN** a tool function returns an error
- **THEN** the caller receives a tool result marked as an error carrying the
  message, rather than a protocol-level failure

#### Scenario: A tool call is bounded
- **WHEN** a tool exceeds its configured timeout
- **THEN** the call is cancelled and reported as an error result

### Requirement: The transport is selectable and the server is mountable

The module SHALL support the protocol's transports interchangeably and allow the
server to be served alongside an HTTP application.

#### Scenario: The transport is named, not hardcoded
- **WHEN** a caller names a transport
- **THEN** that transport is used, and an unknown name fails naming the supported
  ones

#### Scenario: A standard-input transport is the default
- **WHEN** no transport is named
- **THEN** the standard-input transport is used, which is what a locally launched
  server needs

#### Scenario: An MCP server shares a port with an HTTP service
- **WHEN** a service exposes both an HTTP API and an MCP endpoint
- **THEN** the MCP server can be mounted on the framework's HTTP server rather
  than requiring a second process or a second port

#### Scenario: Shutdown is orderly
- **WHEN** the process receives a termination signal
- **THEN** the MCP server stops on the same terms as the HTTP server

### Requirement: The consumer side is covered symmetrically

The module SHALL provide an MCP client with the same instrumentation guarantees as
the server.

#### Scenario: An outbound tool call is traced
- **WHEN** a client calls a tool on a remote server
- **THEN** the call produces a span, propagates trace context, and records its
  duration and error type
