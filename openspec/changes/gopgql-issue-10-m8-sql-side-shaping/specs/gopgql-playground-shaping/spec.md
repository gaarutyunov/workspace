## ADDED Requirements

### Requirement: The playground toggles between the two shaping strategies

The browser playground SHALL let a reader switch between the two shaping
strategies over one schema, query and set of variables, and SHALL show the SQL
each strategy emits.

#### Scenario: Both strategies are shown for one query
- **WHEN** a reader enters a schema, a query and its variables and switches
  strategy
- **THEN** the panel shows the SQL that strategy emits for that same input

#### Scenario: The two differ
- **WHEN** the same query is compiled under each strategy
- **THEN** the two SQL texts differ — one projects the flat columns, the other
  builds the nested response and returns it as a single value

#### Scenario: The bind parameters are shown and are the same
- **WHEN** a query carrying variables is compiled under each strategy
- **THEN** the ordered bind parameters are shown, and are the same under both,
  because the graph pattern does not change with the strategy

#### Scenario: Real compiled Go
- **WHEN** the panel produces its output
- **THEN** it comes from the gopgql compiler compiled to WebAssembly, with no
  JavaScript re-implementation and nothing hardcoded

#### Scenario: A rejected query is still rejected
- **WHEN** a query exceeding the depth ceiling is compiled under either strategy
- **THEN** the panel presents the refusal as the designed outcome, as it already
  does, rather than an empty result

### Requirement: The playground shows SQL, never results

Because the browser has no database, the panel SHALL present generated SQL only,
and SHALL say so rather than let a reader infer that the two responses were
compared in the browser.

#### Scenario: The panel states its limits
- **WHEN** the shaping panel is displayed
- **THEN** it states that it shows generated SQL and not query results, and that
  no database is being contacted

#### Scenario: No response, count or timing is shown
- **WHEN** the shaping panel is displayed
- **THEN** it shows no response document, no row count from an execution and no
  measured timing, none of which can be obtained without a database

#### Scenario: What can be derived is derived
- **WHEN** the panel describes what each strategy asks the database for
- **THEN** it reports the result-set shape the compiler determined — several
  projected columns assembled in Go, against a single column assembled in the
  database — because that follows from the compiled query alone

#### Scenario: The build is unaffected
- **WHEN** the WebAssembly playground is built
- **THEN** it builds, because compiling under either strategy needs nothing from
  the packages that require a database connection
