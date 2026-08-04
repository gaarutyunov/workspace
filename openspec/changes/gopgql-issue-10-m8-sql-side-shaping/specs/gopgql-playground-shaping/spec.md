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

### Requirement: The playground runs both strategies and shows they agree

> **Amended after gopgql#31 merged.** This requirement previously read "The
> playground shows SQL, never results", and forbade the panel from displaying a
> response, a row count or a timing, because the browser had no database. #31
> has since put a pinned wasm build of the forked PostgreSQL in the page, so the
> premise no longer holds. What is kept, and strengthened, is the requirement
> that the panel not imply a stronger guarantee than the milestone makes — a
> panel that shows two responses is more exposed to that, not less.

Because the panel can now execute what it compiles, it SHALL run both
strategies' statements and report whether the responses they produce are the
same, and SHALL state what that comparison is over.

#### Scenario: Both strategies are executed
- **WHEN** a reader runs the shaping panel
- **THEN** both compiled statements execute, against a single database populated
  once, so that any difference between the responses is attributable to the
  strategies and not to the data

#### Scenario: The verdict is reported
- **WHEN** both statements have executed
- **THEN** the panel reports whether the two responses are identical, and shows
  each response

#### Scenario: The verdict names what it compared
- **WHEN** the panel reports that the responses are identical
- **THEN** it states that the comparison is over the canonical encoding of each
  response, and not over the bytes the database sent, which differ

#### Scenario: The result sets differ where the responses do not
- **WHEN** the panel's default fixture is executed
- **THEN** the Go-side statement returns several flat rows and the SQL-side
  statement returns one row of one column, and both are shown, because two
  identical responses are only meaningful beside the result sets they came from

#### Scenario: What can be derived is derived before anything runs
- **WHEN** the panel describes what each strategy asks the database for
- **THEN** it reports the result-set shape the compiler determined — several
  projected columns assembled in Go, against a single column assembled in the
  database — because that follows from the compiled query alone

#### Scenario: A rejected statement is reported as itself
- **WHEN** the database refuses the schema or either compiled statement
- **THEN** the panel reports that refusal, in the database's own words, rather
  than presenting it as a disagreement between the strategies

#### Scenario: The build is unaffected
- **WHEN** the WebAssembly playground is built
- **THEN** it builds, because compiling under either strategy — and shaping or
  decoding a result set — needs nothing from the packages that require a
  database connection
