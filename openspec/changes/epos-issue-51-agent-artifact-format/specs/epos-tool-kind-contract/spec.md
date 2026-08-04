## ADDED Requirements

### Requirement: A tool artifact stands alone

The system SHALL define the `tool` kind as an artifact that is valid on its own,
packed, pushed, pulled and resolved without ever appearing in an agent index.

This is required because a consumer of this format keeps a store of tool
artifacts with no agent involved, and that consumer has adopted this format
rather than defining its own.

#### Scenario: A tool is packed and pushed without an agent
- **WHEN** a tool directory is packed and pushed
- **THEN** the artifact is complete and conformant, and no index is created

#### Scenario: A standalone tool is later referenced by an agent
- **WHEN** an agent references a previously published standalone tool
- **THEN** the tool artifact is copied into the closure unchanged, keeping its
  digest

### Requirement: A script tool's document lives inside its payload

The system SHALL place a script tool's document at `<tool-name>/tool.yaml` inside
the tool's single layer, whose tar is rooted at `<tool-name>/` as a skill's
content layer is, and SHALL build it through the same deterministic packing path.

This has to be stated because a manifest of these kinds carries exactly one
layer, and a script tool has both a document and executable files to put in it. A
producer that guesses differently writes an artifact no other implementation can
read.

#### Scenario: The document is found at a defined path
- **WHEN** a script tool artifact's layer is extracted
- **THEN** the document is at the tool's name followed by the document file name,
  beside the files the entry point refers to

#### Scenario: A layer without a document is refused
- **WHEN** a script tool's layer carries no document at that path
- **THEN** validation fails naming the path it looked for

### Requirement: Paths inside a tool payload are validated

The system SHALL validate the tool's entry point, and every path inside a tool's
payload, with the same path check the rest of the project uses for archive
contents — rejecting empty, absolute, parent-escaping and non-canonical paths —
at packing time and again whenever a payload is materialised.

A violation SHALL be a conformance failure and not only a local check, so that an
artifact produced elsewhere cannot carry a path this system would refuse to
write.

The check SHALL be the existing single implementation. A second copy is how one
caller loses a rule.

#### Scenario: An escaping entry point is refused at packing
- **WHEN** a tool declares an entry point that escapes the payload root
- **THEN** packing fails naming the path

#### Scenario: An escaping path in a foreign artifact is refused at materialise
- **WHEN** a tool artifact produced elsewhere carries a payload entry whose path
  escapes the root
- **THEN** materialising it fails naming the entry, and nothing is written outside
  the destination directory

### Requirement: A tool manifest carries its own identity in its own annotations

The system SHALL require a tool manifest to carry its name, its runtime and its
human-readable title in the manifest's own annotations, so that a consumer can
build a searchable listing by reading manifests alone and never fetching a layer.

| Annotation | Requirement |
|---|---|
| `dev.epos.name` | required — the tool's name |
| `dev.epos.runtime` | required for script tools — mirrors the document's runtime |
| `org.opencontainers.image.title` | required |
| `org.opencontainers.image.description` | recommended |
| `dev.epos.tool.params` | optional — top-level parameter names, as a JSON array of strings |

The parameter-name annotation SHALL carry names only, SHALL be encoded as a JSON
array of strings, and SHALL be bounded at 4096 bytes of encoded value. A
separator-delimited encoding SHALL NOT be used, because a schema property name
may contain any character and a separator with no escape rule is a parsing
failure waiting for the first name that contains it.

When the encoded value would exceed the bound, the annotation SHALL be omitted
with a warning naming the tool, and packing SHALL succeed. The annotation is
optional, and refusing to publish an otherwise-valid tool because its parameter
list is long would turn an index hint into a packing constraint. A consumer SHALL
treat its absence as "not indexed here" and fall back to the layer.

The full input schema SHALL stay in the layer, because annotations are covered by
the manifest digest and count against a registry's manifest size limits, and an
unbounded schema in an annotation makes the manifest unbounded.

When a tool also appears in an agent index, its name SHALL appear both on the
manifest and on the index entry, and the index entry's name SHALL be the one the
definition document resolves against — a tool may be referenced under a name that
differs from its published one.

#### Scenario: A listing is built from manifests alone
- **WHEN** a store of tool artifacts is enumerated
- **THEN** every tool's name, runtime, title and description are available without
  fetching a single layer

#### Scenario: A manifest missing its name is not conformant
- **WHEN** a tool manifest carries no name annotation
- **THEN** it is reported as non-conformant naming its digest, and a consumer that
  skips it is behaving correctly

#### Scenario: The parameter annotation is bounded and optional
- **WHEN** a tool whose parameter names exceed the bound is packed
- **THEN** packing succeeds, the annotation is omitted with a warning naming the
  tool, and a consumer falls back to the layer

#### Scenario: A parameter name containing a separator survives
- **WHEN** a tool declares a parameter whose name contains a comma
- **THEN** it round-trips through the annotation intact, because the value is a
  JSON array and not a delimited string

#### Scenario: An index entry may rename a tool
- **WHEN** an agent references a tool under a different name
- **THEN** the definition resolves against the index entry's name, and the tool
  manifest keeps its own

### Requirement: The runtime field is an open enum with four registered values

The system SHALL define the registered runtimes as `bash`, `js`, `lua` and
`openapi`, and SHALL treat the set as open: an unrecognised runtime SHALL be
carried through packing, publishing, pulling and resolution unchanged, reported
as unrecognised, and never rewritten or refused.

A consumer refusing to execute an unrecognised runtime SHALL name it. The
producer set of this format is larger than any one consumer's runtime set, and a
registry that refuses to store what it cannot run would prevent that.

#### Scenario: The fourth runtime is registered
- **WHEN** a tool declares the OpenAPI runtime
- **THEN** it packs, pushes and resolves without a warning, because the value is
  registered

#### Scenario: An unknown runtime survives a round trip
- **WHEN** a tool declaring an unrecognised runtime is packed, pushed, pulled and
  resolved
- **THEN** the document is byte-identical at the end, the value is reported as
  unrecognised, and nothing was rewritten or deleted

#### Scenario: A missing or non-string runtime is refused
- **WHEN** a script tool document declares no runtime, or declares one that is not
  a string
- **THEN** packing fails naming the field, because the field's presence and type
  are validated even though its value set is open

### Requirement: An OpenAPI tool is one artifact per operation

The system SHALL document that a tool artifact describes exactly one tool, and
that an OpenAPI source describing several operations is therefore packed as one
artifact per operation, whose layer carries the document pruned to that operation
and whose entry point names that document inside the payload.

This is a convention rather than a new mechanism: the existing script-tool shape
already expresses it, and stating it here prevents a second consumer from
inventing a different mapping.

#### Scenario: Several operations become several artifacts
- **WHEN** an OpenAPI document describing three operations is packed as tools
- **THEN** three artifacts result, each describing one operation, each with its
  own name and its own input schema

#### Scenario: The entry point names the pruned document
- **WHEN** an OpenAPI tool artifact is inspected
- **THEN** its entry point names a document inside its payload, and that document
  describes exactly the one operation the tool exposes

### Requirement: An MCP server tool has its own artifact type, and a container image remains valid

The system SHALL define an artifact type for an MCP server tool whose single
layer carries the MCP registry's server descriptor verbatim, and SHALL keep the
alternative in which an index entry points directly at an ordinary container
image annotated with the server's name.

The server-descriptor form exists because a remote MCP server reached over HTTP
has no container image, and a format that can only express the container form
cannot express the most common deployment. The reference forms — remote endpoint,
locally spawned process, container image — are read from the server descriptor's
own fields and are not restated in an epos-specific field.

The system SHALL validate that the descriptor is well formed and that its name
matches the annotation, and SHALL do nothing else with it: epos neither connects
to an MCP server nor runs a container.

#### Scenario: A remote MCP server is packaged with no image
- **WHEN** an MCP server reachable over HTTP is packed as a tool
- **THEN** the artifact carries the MCP tool artifact type and one layer holding
  the server descriptor, and no container image is required

#### Scenario: The container-image form still resolves
- **WHEN** an index entry points at an ordinary container image annotated with an
  MCP server name
- **THEN** it resolves as an MCP server tool, as it did before the descriptor form
  existed

#### Scenario: A consumer dispatches on artifact type
- **WHEN** a closure contains a script tool and an MCP server tool
- **THEN** each is distinguished by its artifact type, never by its tag, its
  repository name or a file extension

#### Scenario: A name mismatch is refused
- **WHEN** the server descriptor's name differs from the annotation
- **THEN** packing fails naming both values

#### Scenario: No document is required for an MCP server tool
- **WHEN** an MCP server tool is packed
- **THEN** no tool document is required, because the server descriptor is
  authoritative for what the server is and how it is reached

### Requirement: The tool contract is verified against artifacts produced elsewhere

The system SHALL verify conformance of the tool kind against artifacts produced
by an implementation other than itself, because the kind is a published contract
with a consumer that writes artifacts this project does not write.

#### Scenario: A foreign tool artifact resolves
- **WHEN** a tool artifact built to this specification by a different
  implementation is pulled and resolved
- **THEN** it resolves, its annotations are read, and its runtime is reported

#### Scenario: An epos-produced tool is readable by the consumer's rules
- **WHEN** a tool packed by this project is enumerated by reading manifest
  annotations only
- **THEN** its name, runtime, title and description are all present, so a consumer
  that never fetches a layer can list it
</content>
