## ADDED Requirements

**Milestone: none yet — this capability is deliberately unscheduled. It stays in
scope on the owner's instruction that Service Weaver matters, but the owner's
other instruction gates every milestone on a real project adopting it, and no
project consumes this today; its upstream is archived, and it carries the largest
invented surface in the change. The two instructions pull against each other
here, and the resolution is a schedule rather than a scope change: the
requirements below are specified now so that whichever deployment technology
arrives first is an adapter and not a rewrite, and the milestone opens when a
consumer exists. When it does, the in-process deployer comes first, then
Kubernetes, and the Service Weaver deployer with the consumer that asks for it.**

### Requirement: Components are defined against the framework, deployed by an adapter

An application SHALL express its units of deployment against a framework
interface, and the deployment mechanism SHALL be a replaceable adapter.

#### Scenario: A component is defined once
- **WHEN** a unit of the application is defined as a component
- **THEN** it implements the framework's component interface and names no
  deployment technology

#### Scenario: References between components are typed
- **WHEN** one component depends on another
- **THEN** it holds a typed reference that the deployer resolves, rather than
  constructing the other component itself

#### Scenario: A reference's type is one a distributed deployer can satisfy
- **WHEN** a reference is declared to a concrete implementation type rather than
  to an interface
- **THEN** it is rejected where it is declared, because a distributing deployer
  hands back a stand-in rather than the stored implementation — so the in-process
  deployer must not accept a shape the distributed one will refuse

#### Scenario: A mismatched resolution is an error, not a crash
- **WHEN** a reference resolves to something that is not the referenced type
- **THEN** the caller receives an error identifying the component and the types
  involved

#### Scenario: The same components run in one process
- **WHEN** the in-process deployer is used
- **THEN** the components run in a single process and references resolve to direct
  calls

#### Scenario: The same components run distributed
- **WHEN** a distributing deployer is used
- **THEN** the same components run across process boundaries with no component
  source change

#### Scenario: Tests use the in-process deployer
- **WHEN** components are exercised in tests
- **THEN** the in-process deployer is the default, so a test needs no deployment
  infrastructure

#### Scenario: Replacing the deployment technology does not change components
- **WHEN** the underlying deployment technology is replaced
- **THEN** the change is confined to a deployer adapter, and no component or
  caller changes

#### Scenario: Deployers resolve through this module's own adapter table
- **WHEN** a deployer is selected by name
- **THEN** it resolves through the module's own name-keyed table, on the same
  terms as every other module's, and an unknown name fails naming the supported
  ones

### Requirement: Component interaction is observable regardless of deployer

Cross-component calls SHALL be instrumented by the portable layer.

#### Scenario: A cross-component call is traced
- **WHEN** one component calls another
- **THEN** the call produces a span, records its duration, and on failure records
  the error type

#### Scenario: Telemetry does not depend on the deployer
- **WHEN** the same component graph runs under different deployers
- **THEN** the telemetry it produces is the same, so a local run and a distributed
  run are comparable

#### Scenario: A deployer adapter carries no telemetry
- **WHEN** a deployer adapter is written
- **THEN** it contains no instrumentation, and calls through it are instrumented
  anyway

### Requirement: The lifecycle of a component graph is managed

Starting and stopping a component graph SHALL be handled by the framework.

#### Scenario: Components are initialised before serving
- **WHEN** the graph starts
- **THEN** every registered component is initialised, and a failure aborts startup
  naming the component

#### Scenario: Components are shut down in reverse order
- **WHEN** the graph stops
- **THEN** components are shut down in the reverse of their initialisation order,
  and the errors are reported together rather than the first masking the rest
