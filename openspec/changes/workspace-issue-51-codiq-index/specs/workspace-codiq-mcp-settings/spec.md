## ADDED Requirements

### Requirement: The workspace registers the codiq graph as an MCP server

The workspace SHALL register the codiq graph's read surface as an MCP server in
its committed MCP configuration, beside the existing code-graph server, and
SHALL grant it the same kind of permission entry the existing server has.

The registration SHALL point at the read surface codiq's own deployment
publishes, and SHALL NOT require any binary to be installed on the operator's
path or any path into a gitignored directory to be committed.

#### Scenario: An agent can query the graph without extra setup

- **WHEN** the codiq stack is running and a session starts in this workspace
- **THEN** the graph's tools are available to the agent, with no per-session
  configuration

#### Scenario: The permission entry matches the existing convention

- **WHEN** the settings are read
- **THEN** the new server's tools are allowed by the same wildcard form the
  existing code-graph server's tools are allowed by

#### Scenario: Committed configuration names nothing gitignored

- **WHEN** the configuration is reviewed
- **THEN** it references no path under the gitignored projects directory, so it
  remains true for a checkout that has not cloned those projects

#### Scenario: A stopped stack fails visibly

- **WHEN** a session starts while the stack is down
- **THEN** the server is unreachable and says so, rather than appearing healthy
  and returning empty results

### Requirement: The read surface is read-only

The registered server SHALL expose queries only, and SHALL NOT expose any means
of writing to the graph.

#### Scenario: No write tool is offered

- **WHEN** the server's tools are listed
- **THEN** none of them mutates the graph

#### Scenario: A write would be refused by the database

- **WHEN** a statement that writes reaches the database over this connection
- **THEN** the database refuses it, so the guarantee does not depend on the
  server's own correctness

### Requirement: The project instructions say which graph to reach for

The workspace's own agent instructions SHALL state that two code-graph servers
are registered, what each is for, and which to use for which kind of question.

#### Scenario: An agent is not left to guess

- **WHEN** an agent reads the workspace instructions
- **THEN** it can tell from them which server answers a given kind of question,
  rather than discovering by trying both

#### Scenario: The distinction survives the comparison

- **WHEN** the comparison has produced its result
- **THEN** the instructions are updated to reflect what it found, so the
  guidance is grounded in the measurement rather than in the expectation
