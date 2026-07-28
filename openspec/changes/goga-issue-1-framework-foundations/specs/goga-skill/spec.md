## ADDED Requirements

### Requirement: One skill, describing entry points rather than tools

There SHALL be a single skill for goga, and it SHALL NOT re-teach the wrapped
tools.

#### Scenario: It routes to an entry point
- **WHEN** an agent needs configuration, telemetry, a server, a client or a test
  fixture
- **THEN** the skill names the goga entry point to use

#### Scenario: It does not re-document the underlying tools
- **WHEN** the skill is read
- **THEN** it does not explain how to use the wrapped libraries directly, because
  that is the library's job and duplicating it is how the guidance drifts

#### Scenario: It states what goga does not do
- **WHEN** an agent needs something goga does not cover
- **THEN** the skill says so plainly and names the escape hatch

#### Scenario: It states what goga does not enforce
- **WHEN** a convention is not enforced by the API
- **THEN** the skill says which conventions still rest on the reader

### Requirement: Guidance does not contradict itself

The workspace's Go guidance SHALL present one position on any question an agent
must decide.

#### Scenario: Layout guidance is consistent
- **WHEN** an agent reads the available Go guidance on package layout
- **THEN** it finds one position, not two mutually exclusive ones

#### Scenario: A superseded document says so
- **WHEN** guidance is replaced by the library or by another document
- **THEN** the superseded material states what replaced it rather than remaining
  silently in force
