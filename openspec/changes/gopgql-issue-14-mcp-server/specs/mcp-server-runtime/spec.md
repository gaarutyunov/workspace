## ADDED Requirements

### Requirement: Serve one schema against one database

The server SHALL be started with an SDL document and a database connection
string, and SHALL serve MCP over stdio.

#### Scenario: Startup
- **WHEN** the server is started with a valid SDL path and connection string
- **THEN** it serves the MCP protocol over stdio and advertises its tools

#### Scenario: Configuration from the environment
- **WHEN** the SDL path or connection string is supplied through the environment
  instead of a flag
- **THEN** the server starts the same way

#### Scenario: Invalid SDL
- **WHEN** the SDL fails to parse or validate
- **THEN** the server exits with an error naming the problem rather than starting
  with a half-loaded schema

#### Scenario: Database unreachable at startup
- **WHEN** the database cannot be reached
- **THEN** the server reports the failure rather than serving tools that would
  fail on every call

### Requirement: The server never migrates and never writes

The server SHALL expose no migration or mutation capability, and SHALL execute
only read statements.

#### Scenario: No migration tool
- **WHEN** a client lists the server's tools
- **THEN** no tool applies migrations or alters the schema

#### Scenario: Writes are refused
- **WHEN** a statement that would write is somehow issued on the server's
  connection
- **THEN** the database refuses it, because the connection is read-only

### Requirement: Tool discovery

The server SHALL advertise its tools with descriptions and input schemas
sufficient for a client to call them correctly.

#### Scenario: Listing tools
- **WHEN** a client lists tools
- **THEN** both the schema tool and the query tool are returned, each with a
  description and a declared input schema
