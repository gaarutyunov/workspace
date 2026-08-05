## ADDED Requirements

### Requirement: A mutation field may name a database function to call

The system SHALL provide a directive that maps a GraphQL mutation field to a
function the database already owns, identified by its schema and name, and SHALL
compile a mutation operation over such a field into a call to that function.

The system SHALL NOT derive any mutation from a type mapping: no create, update
or delete field is generated from a node type, and no input type is inferred. A
mutation exists only where the schema document declares one and names its
target.

#### Scenario: A declared mutation field compiles to a function call
- **WHEN** a mutation operation selects a field carrying the directive
- **THEN** the emitted statement calls the named function in the named schema,
  and contains no graph name, no pattern match and no graph-table construct

#### Scenario: Nothing mutates through the property graph
- **WHEN** any mutation is compiled
- **THEN** the property graph is not written through, because the emitted
  statement does not reference it — the database's own prohibition on writing
  through a property graph is unaffected by this capability

#### Scenario: A mutation field without a target is refused
- **WHEN** a schema document declares a mutation field that does not name a
  function
- **THEN** parsing fails naming that field, because there is no default target
  and none is inferred

#### Scenario: The directive is only valid on a mutation field
- **WHEN** the directive appears on a field of any type other than the mutation
  root
- **THEN** parsing fails naming the field

#### Scenario: Query compilation still refuses a mutation
- **WHEN** a mutation operation is passed to the query-compilation entry point
- **THEN** it is refused, and the message directs the caller to the
  mutation-compilation entry point rather than stating that mutation is
  impossible

#### Scenario: One root field per mutation operation
- **WHEN** a mutation operation selects more than one root field
- **THEN** compilation fails, matching the rule already in force for queries

### Requirement: Arguments map to function parameters by name

The system SHALL emit the call in a form that binds each argument to a parameter
**by name**, so that the order of arguments in the schema document, in the
operation, and in the function's own signature are mutually independent.

Parameter names SHALL be declared, never derived from the GraphQL argument name
by a naming convention.

#### Scenario: Argument order does not affect the result
- **WHEN** the same mutation is executed twice with its arguments supplied in
  different orders
- **THEN** both calls bind the same values to the same parameters and return the
  same result

#### Scenario: A parameter name is declared alongside its argument
- **WHEN** a function parameter's name differs from the GraphQL argument name
- **THEN** the schema document declares the parameter name on the argument, and
  the emitted call uses it

#### Scenario: An argument that cannot be mapped is refused at parse time
- **WHEN** an argument's GraphQL name is not usable as a parameter name and no
  parameter name is declared for it
- **THEN** parsing fails naming the argument, rather than emitting a call that
  the database would reject as referring to an unknown function

#### Scenario: Values are bound, identifiers are not
- **WHEN** a call is emitted
- **THEN** every argument value is a bind parameter and never interpolated, and
  the schema, function and parameter names are identifiers validated against the
  schema document and quoted, never bind parameters

### Requirement: An argument the operation document does not pass takes the function's default

The system SHALL omit from the emitted call any argument the **operation
document** does not pass, so that the parameter's declared default applies. The
system SHALL NOT emit a default keyword and SHALL NOT substitute a value of its
own.

Omission SHALL be a property of the operation document and not of an individual
request, because the emitted statement is fixed before any request exists.

#### Scenario: An argument absent from the document reaches the function's default
- **WHEN** an operation document does not pass an optional argument
- **THEN** the argument is absent from the emitted call, and the function
  observes its own declared default

#### Scenario: An argument passed as an unset nullable variable arrives as null
- **WHEN** an operation document passes an argument as a nullable variable and a
  request supplies no value for it
- **THEN** the argument is present in the call and bound as null — which is the
  function's default only when that default is itself null

#### Scenario: An unset non-null variable is still an error
- **WHEN** a request supplies no value for a variable the operation declares
  non-null
- **THEN** compilation fails naming the variable, as it does today

#### Scenario: An argument with a schema-document default is always sent
- **WHEN** a mutation argument declares a default in the schema document and an
  operation does not supply a value
- **THEN** that default is applied and bound as an ordinary argument, and the
  function's own default for the parameter is never reached

#### Scenario: The distinction is documented where it is read
- **WHEN** an author needs the function's default to apply
- **THEN** the reference states that the argument must be absent from the
  operation document, that a schema-document default pre-empts the database's,
  and that a null value is not a default — none of which the system can detect
  on the author's behalf

### Requirement: The return kind is declared, not inferred

The system SHALL require a void-returning function to be declared as such on the
directive, and SHALL treat every other declaration as scalar-returning.

A scalar-returning call SHALL be executed as a query returning exactly one row
of one column, and its value mapped through the same scalar correspondence used
for column types. A void-returning call SHALL be executed as a statement, and a
successful execution SHALL yield true.

The system SHALL refuse, at compile time, a declaration of a set-returning,
output-parameter, variadic or polymorphic function.

#### Scenario: A scalar result is returned
- **WHEN** a scalar-returning function is called
- **THEN** the single value it returns is mapped to the declared GraphQL scalar
  and returned to the caller

#### Scenario: A declared void function reports success
- **WHEN** a function declared void is called and does not raise
- **THEN** true is returned, and the function's side effect is visible to the
  caller's transaction

#### Scenario: A successful void call never reports false
- **WHEN** a function declared void succeeds
- **THEN** the result is true, and is not derived from reading a value the
  function did not return

#### Scenario: A void declaration must be a non-null boolean field
- **WHEN** a field declared void has any GraphQL type other than a non-null
  boolean
- **THEN** parsing fails naming the field, because there is no value to map

#### Scenario: The return kind is not discovered from the database
- **WHEN** a call is compiled
- **THEN** nothing inspects the function's actual return type, so compilation
  stays free of a database and a scalar boolean function returning false is
  never confused with a void one

#### Scenario: A result of unexpected shape is a clear error
- **WHEN** a scalar call returns other than exactly one row of one column
- **THEN** a descriptive error is returned rather than a panic or a silently
  truncated value

#### Scenario: A set-returning declaration is refused
- **WHEN** the schema document declares a function return that would require
  shaping a set
- **THEN** compilation fails naming the field, because a function result does
  not flow through the projection machinery

#### Scenario: A declaration that disagrees with the database is the database's error
- **WHEN** the declared return kind does not match the function's actual return
  type
- **THEN** the disagreement surfaces as the database's error at call time, and
  not as a compile-time claim the system cannot make without a database
