## ADDED Requirements

### Requirement: Configuration loads with a stated precedence

Configuration SHALL be loaded from defaults, a file, the environment and flags in
an order the caller can read from the call itself, not infer.

#### Scenario: The order is explicit
- **WHEN** a developer reads the loading call
- **THEN** the precedence of defaults, file, environment and flags is visible
  there, rather than having to be reconstructed from provider behaviour

#### Scenario: Later sources win
- **WHEN** the same key is supplied by more than one source
- **THEN** the later source in the stated order takes effect

#### Scenario: A missing file is not fatal by default
- **WHEN** no configuration file is present
- **THEN** loading succeeds using the remaining sources, unless the caller
  declared the file required

#### Scenario: Environment key mapping is documented
- **WHEN** an environment variable maps to a nested key
- **THEN** the separator convention is documented at the call site, because two
  existing projects chose incompatible conventions

### Requirement: Both a typed value and the raw handle are returned

Loading SHALL produce a typed configuration value **and** expose the underlying
configuration handle.

#### Scenario: Typed access
- **WHEN** a caller supplies a struct
- **THEN** it is populated, with durations and slices decoded

#### Scenario: The raw handle is reachable
- **WHEN** a caller needs a subtree the typed struct does not model
- **THEN** the underlying handle is available for it, so the wrapper never traps
  a caller that outgrows it

#### Scenario: A required value that is absent fails loudly
- **WHEN** a value declared required is missing from every source
- **THEN** loading fails naming the key, rather than yielding a zero value
