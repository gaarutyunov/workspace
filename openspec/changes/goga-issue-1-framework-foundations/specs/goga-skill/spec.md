## ADDED Requirements

**Milestone: M13 (the skill), last of the delivered milestones — it routes to
entry points, so it needs entry points to route to, and a routing table written
before the packages exist would name things that do not. The exception is the
last requirement, *Guidance does not contradict itself*: the contradiction it
describes is live in already-merged workspace guidance, so it is fixed alongside
the milestones rather than after them, because every adoption PR is written by an
agent reading that guidance.**

### Requirement: One skill, describing entry points rather than tools

There SHALL be a single skill for goga, and it SHALL NOT re-teach the wrapped
tools.

#### Scenario: It routes to an entry point
- **WHEN** an agent needs configuration, telemetry, a server, a client, a router,
  a database, migrations, an MCP server, gRPC, components, dependency injection
  or a test fixture
- **THEN** the skill names the goga entry point to use

#### Scenario: It does not re-document the underlying tools
- **WHEN** the skill is read
- **THEN** it does not explain how to use the wrapped libraries directly, because
  that is the library's job and duplicating it is how the guidance drifts

#### Scenario: Its structure is fixed, not its prose
- **WHEN** the skill is written
- **THEN** its section structure and routing table are the parts this change
  fixes, because the issue asks for the skill as a pseudo-structure rather than
  as finished text

#### Scenario: Escape hatches are named
- **WHEN** an agent needs something a wrapper does not model
- **THEN** the skill names that module's accessor for the underlying object,
  because an escape hatch is a supported route and not a gap

### Requirement: Every house convention is enforced by goga

The skill SHALL carry an enforcement matrix pairing each house convention with
the mechanism that enforces it, and there SHALL NOT be a set of conventions left
to the reader's discipline.

#### Scenario: Each convention names its mechanism
- **WHEN** a house convention appears in the guidance
- **THEN** it is paired with the mechanism that enforces it — an API shape that
  makes the alternative uncompilable, a lint rule, or a required CI check

#### Scenario: There is no list of unenforced conventions
- **WHEN** the skill is read looking for conventions that rest on the reader
- **THEN** it has none to offer, because a convention without a mechanism is
  recorded as a defect against goga rather than published as a caveat

#### Scenario: A convention that cannot yet be enforced is tracked as a defect
- **WHEN** a house convention is identified with no available mechanism
- **THEN** it is raised as work on goga, and not documented as the reader's
  responsibility

#### Scenario: The mechanism's strength is stated honestly
- **WHEN** a convention is enforced by a lint rule or a CI check rather than by
  the type system
- **THEN** the matrix says so, so nobody mistakes a red build for an
  impossibility

### Requirement: Guidance does not contradict itself

The workspace's Go guidance SHALL present one position on any question an agent
must decide.

*Not gated on any milestone: this repairs guidance already in force on `main`.*

#### Scenario: Layout guidance is consistent
- **WHEN** an agent reads the available Go guidance on package layout
- **THEN** it finds one position, not two mutually exclusive ones

#### Scenario: Guidance already in force is repaired, not merely flagged
- **WHEN** two pieces of guidance that are both already published disagree
- **THEN** one of them is amended, because a disagreement between published
  documents is a defect in force rather than a risk to be noted

#### Scenario: Guidance does not prescribe a structure the framework contradicts
- **WHEN** guidance describes how to organise adapters and the interfaces they
  satisfy
- **THEN** it matches the structure the framework itself ships, so a project
  adopting the framework is not told to arrange its own adapters differently from
  the ones it imports

#### Scenario: A decision the framework leaves open is named as the owner's
- **WHEN** a structural question the framework deliberately does not decide is
  reached
- **THEN** the guidance says whose decision it is and where it will be enforced,
  rather than answering it twice in two documents

#### Scenario: A superseded document says so
- **WHEN** guidance is replaced by the library or by another document
- **THEN** the superseded material states what replaced it rather than remaining
  silently in force
