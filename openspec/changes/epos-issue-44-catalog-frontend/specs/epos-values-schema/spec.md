## ADDED Requirements

<!-- PLACEMENT NOTE, for the reviewer rather than the implementer.

     This capability is specified here because the owner asked for it on this
     change's proposal. Design D14 argues it should be *delivered* under
     epos#47 ("install --set does not infer types"), whose subject is already
     what a value's type is and whose acceptance criteria this supersedes —
     not because it is unwanted, but because it is a packaging and install
     feature with no frontend in it, and epos#47 already exists on exactly
     this surface. Nothing here is split into sub-issues; the recommendation
     is that one existing issue absorbs one coherent deliverable.

     If the owner keeps it on epos#44, this delta is implemented as written
     and the catalog consumes it directly. If it moves to epos#47, this delta
     moves with it and only the last requirement — "The catalog renders a
     skill's values contract" — stays on epos#44, degrading to absent when an
     artifact carries no schema. Either way the requirements below are the
     same; only which pull request carries them changes. -->

### Requirement: A skill declares its install-time parameters as an OpenAPI v3 schema

A skill SHALL be able to declare the values it accepts as a schema document in
the OpenAPI v3 Schema Object dialect, and that declaration SHALL be the contract
between the skill's author and whoever installs it.

#### Scenario: The parameters are declared, not inferred by the reader
- **WHEN** a skill that accepts install-time parameters is inspected
- **THEN** the parameters it accepts, their types, their defaults and which of
  them are required are readable from a schema the skill carries, rather than
  being deduced by reading its templates

#### Scenario: The schema is structural
- **WHEN** the schema is read
- **THEN** every property it declares has a declared type, so that validation
  and defaulting have one answer for every path rather than depending on which
  branch of a composition keyword matched

#### Scenario: The dialect is a schema dialect, not a document format
- **WHEN** the schema is validated by a general-purpose validator
- **THEN** it validates, because what the skill carries is a schema object and
  not an API description wrapped around one

#### Scenario: Stage scopes are part of the contract
- **WHEN** a skill was built from a multi-stage recipe and stages contribute
  their own parameters
- **THEN** the composed schema mirrors the scoping the renderer already applies —
  the skill's own parameters at the top level, each contributing stage's
  parameters under that stage's name, and the shared block under its usual name

#### Scenario: A schema is optional and its absence is not an error
- **WHEN** a skill carries no schema
- **THEN** it installs exactly as it does today, because the schema is a
  contract a skill may offer and not a new requirement on every artifact

### Requirement: The schema travels with the artifact and is cheap to read

The schema SHALL be carried by the packed artifact, and a reader that only wants
the parameter contract SHALL NOT have to download the skill's content to get it.

#### Scenario: The schema is in the artifact
- **WHEN** a skill declaring a schema is packed and published
- **THEN** the schema is part of the published artifact, so an installer that
  pulled the skill has it without consulting the source repository

#### Scenario: One request yields the contract
- **WHEN** a client wants only the parameter contract for a published skill
- **THEN** it obtains the schema from the artifact's manifest annotations,
  without fetching the content layer

#### Scenario: The skill's own configuration document is not repurposed
- **WHEN** the packed artifact's config blob is compared with the skill's
  document frontmatter
- **THEN** it still mirrors that frontmatter and nothing else, because the
  project's own specification makes that an invariant and an epos extension may
  not alter the skill artifact; the schema travels as an epos-namespaced
  annotation, which is the mechanism the project already uses for
  epos-specific data a client reads without fetching a layer

#### Scenario: An oversized schema does not bloat every manifest
- **WHEN** a schema is larger than the limit set for carrying it on the manifest
- **THEN** it is carried in the content layer only, and the manifest records
  that it is there, so a reader knows the difference between "no schema" and
  "a schema too large to carry on the manifest"

#### Scenario: The two copies cannot disagree
- **WHEN** the inlined schema and the one in the content layer are compared
- **THEN** they are the same document, because one is written from the other at
  pack time rather than being authored twice

### Requirement: Values are validated against the schema before anything is rendered

Where a skill declares a schema, install SHALL validate the merged values
against it and SHALL refuse to render if they do not conform.

#### Scenario: A value of the wrong type is refused
- **WHEN** a value's type does not match the declared type
- **THEN** the install fails, naming the value's path, what was declared and
  what was supplied, before any file is rendered or written

#### Scenario: A missing required value is refused
- **WHEN** a required parameter has no value from any source
- **THEN** the install fails naming it, rather than rendering a document with an
  empty substitution in it

#### Scenario: Declared defaults are applied
- **WHEN** a parameter with a declared default is not supplied
- **THEN** the declared default is what the templates see, so a default lives in
  the contract rather than being repeated in every template that reads it

#### Scenario: Validation happens after merging, not per source
- **WHEN** values arrive from several files and several command-line settings
- **THEN** the merged result is what is validated, because a file supplying half
  a required object and a flag supplying the other half is valid

#### Scenario: A skill with no schema is unaffected
- **WHEN** a skill carrying no schema is installed
- **THEN** no validation step runs and the install behaves as it did before

### Requirement: A declared type is what gives a command-line value its type

Where a schema declares a parameter's type, a value supplied on the command line
SHALL be interpreted as that type, and the file and command-line paths SHALL
agree on what a value means.

#### Scenario: A boolean set on the command line is a boolean
- **WHEN** a parameter declared as a boolean is set to a false value on the
  command line
- **THEN** the templates see a false boolean, and a section gated on that
  parameter is omitted

#### Scenario: The two ways of supplying a value agree
- **WHEN** the same parameter is given the same value through a values file and
  through a command-line setting
- **THEN** the rendered result is identical, because both arrive at the same
  typed value

#### Scenario: An undeclared parameter still gets a sensible type
- **WHEN** a value is set on the command line for a parameter the schema does
  not declare, or the skill declares no schema at all
- **THEN** its type is inferred the way the established package manager in this
  space infers it, rather than every value silently becoming a string

#### Scenario: A string can be forced, by a named option
- **WHEN** a value that would otherwise be read as a boolean or a number must be
  a string, and no schema declares it
- **THEN** a documented option supplies it as a string, carrying the same name
  the established package manager uses so that the knowledge transfers, and the
  schema rejects it if a declared type disagrees

#### Scenario: The behaviour change is announced, not slipped in
- **WHEN** this change alters what an existing command-line setting means
- **THEN** the change is stated as a behaviour change in the change's own
  description and in the generated command reference, with the string-forcing
  option named as the way to keep the previous meaning — because values that
  used to be strings become numbers, and a version-like value in particular
  renders differently afterwards

#### Scenario: The reversed decision is replaced, not deleted
- **WHEN** the code that previously kept every command-line value a string is
  read after the change
- **THEN** it records that the earlier decision was reversed and why, rather
  than leaving no trace that it was ever made

#### Scenario: A value that cannot be coerced is refused, not guessed
- **WHEN** a supplied value cannot be represented as its declared type
- **THEN** the command fails naming the parameter and both types, rather than
  substituting a zero value

### Requirement: A command infers a schema from a skill's own templates

The CLI SHALL provide a command that reads a skill's templates and writes a
starting schema for the values they reference, without executing them.

#### Scenario: The input is one local skill, named explicitly
- **WHEN** the command is invoked
- **THEN** it takes exactly one positional argument naming either a skill
  directory or a skill already in the local store, and fails saying so when
  given a different number of arguments

#### Scenario: Every referenced parameter appears
- **WHEN** the command is run against a skill whose templates reference values
- **THEN** the emitted schema has a property for every value path the templates
  reference, including paths reached through a scoping action that rebinds the
  template's context

#### Scenario: A value is a string unless the templates say otherwise
- **WHEN** a value is referenced only as a substitution
- **THEN** it is typed as a string, which is the default

#### Scenario: A value used as a condition is a boolean
- **WHEN** a value is the condition of a conditional action, or an argument to a
  logical operator in one
- **THEN** it is typed as a boolean

#### Scenario: A value compared with a number is numeric
- **WHEN** a value is an operand of a comparison whose other operand is a numeric
  literal
- **THEN** it is typed as a number, and as an integer when the literal is one

#### Scenario: A value iterated over is a list
- **WHEN** a value is the subject of an iteration action
- **THEN** it is typed as an array

#### Scenario: A value with sub-fields is an object
- **WHEN** a value is referenced only through its sub-fields
- **THEN** it is typed as an object carrying those sub-fields as properties

#### Scenario: Templates are parsed, never executed
- **WHEN** the command runs
- **THEN** it parses the templates and inspects their syntax trees; it does not
  execute them, so a template with side effects or a missing value cannot affect
  the command's outcome

#### Scenario: Contradictory usage is reported, not resolved
- **WHEN** one value path is used in two ways that imply different types
- **THEN** the command reports the conflict, naming the path and both places it
  was used, and does not silently pick one

#### Scenario: Stage scoping is preserved where the input records stages
- **WHEN** the input is a built skill carrying the annotation that says which
  stage contributed each file
- **THEN** a value referenced by a file that stage contributed lands under that
  stage's scope in the emitted schema, matching where the renderer will look for
  it

#### Scenario: A plain directory has no stages and the schema says so
- **WHEN** the input is a skill directory, which records no stages
- **THEN** the emitted schema carries the skill's own parameters and the shared
  block only, and the command does not invent stage scopes it cannot know

#### Scenario: Inference does not resolve a recipe
- **WHEN** stage attribution is wanted
- **THEN** it is read from the built artifact's own annotation rather than by
  resolving a recipe's sources, because a recipe whose source is a registry or a
  remote repository would make an offline inference command a network command

#### Scenario: The output is a draft a human finishes
- **WHEN** the command emits a schema
- **THEN** it says that the result is a starting point to be reviewed and
  committed — because a value used as a condition is equally consistent with a
  non-empty string, so the boolean rule is a useful guess and not a proof

#### Scenario: An existing schema is not silently replaced
- **WHEN** the command is run against a skill that already carries a schema
- **THEN** it does not overwrite it unless overwriting was explicitly requested,
  and it can instead report how the inferred schema differs from the committed
  one

#### Scenario: Inference needs no values and reaches no registry
- **WHEN** the command is run
- **THEN** it requires no values file and makes no registry request, because its
  input is local and it reads only that skill's own templates and annotations

### Requirement: The catalog renders a skill's values contract

Where a skill's artifact carries a values schema, the catalog's detail page
SHALL present the parameters it declares, and where it does not, the page SHALL
omit the section rather than invent one.

#### Scenario: The parameters are a table, from the artifact
- **WHEN** a skill declaring a schema is opened in the catalog
- **THEN** the page shows each declared parameter with its type, whether it is
  required, its default and its description, taken from the artifact's own
  schema

#### Scenario: A skill without a schema shows no parameter section
- **WHEN** a skill carrying no schema is opened
- **THEN** the page has no parameter section at all, rather than an empty one or
  one assembled from guesses

#### Scenario: The contract does not cost an extra fetch
- **WHEN** the list pages are rendered
- **THEN** reading the schema has not caused a content-layer fetch, because the
  schema arrives on the manifest

#### Scenario: A schema too large to carry on the manifest is not silently nothing
- **WHEN** a skill's manifest records that a schema exists only in the content
  layer
- **THEN** the catalog either renders it from the layer it already fetches for
  the detail page, or says the contract was not read — it does not present the
  skill as declaring no parameters

#### Scenario: The schema is untrusted input like the rest of the artifact
- **WHEN** a schema's descriptions, defaults or property names are rendered
- **THEN** they are escaped as the untrusted, publisher-authored strings they
  are, and an oversized or malformed schema fails that page's parameter section
  rather than the catalog
