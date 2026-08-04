## ADDED Requirements

### Requirement: An agent is an OCI image index whose entries are annotated descriptors

The system SHALL represent an agent as an OCI Image Index carrying
`artifactType` `application/vnd.epos.agent.index.v1+json`, whose dependencies are
expressed as annotated descriptors in `manifests[]`.

Exactly one entry SHALL carry `dev.epos.role=definition`. At most one entry MAY
carry `instruction` and at most one `model`. Entries with role `skill`, `tool` or
`subagent` MAY appear any number of times and SHALL carry `dev.epos.name`, unique
within its role. An entry with role `subagent` SHALL itself be an agent index
conforming to this specification. The index SHALL carry `dev.epos.spec-version`.

Heterogeneous `artifactType` values within `manifests[]` are intended and
supported: a consumer selects the artifact it wants by `artifactType` and
annotations, as a runtime selects a platform image.

#### Scenario: A packed agent is a conformant image index
- **WHEN** an agent is packed
- **THEN** the result is an OCI image index whose `artifactType` names the agent
  index type, which carries the specification version, and which a client with no
  epos-specific knowledge can parse as an ordinary image index

#### Scenario: An index without exactly one definition is refused
- **WHEN** an index carries zero entries with role `definition`, or more than one
- **THEN** it is refused at both packing and resolution, and the message names how
  many were found

#### Scenario: A second instruction or model is refused
- **WHEN** an index carries two entries with role `instruction`, or two with role
  `model`
- **THEN** it is refused naming the role

#### Scenario: Names are unique within a role and may repeat across roles
- **WHEN** two entries share a role and a name
- **THEN** packing fails naming the role and the name
- **AND WHEN** a skill and a tool share a name
- **THEN** packing succeeds, because the definition document addresses each
  through its own list

#### Scenario: A sub-agent entry is itself an agent index
- **WHEN** an entry carries role `subagent`
- **THEN** its `artifactType` is the agent index type, and an entry that is not is
  refused naming the entry

### Requirement: The format defines four kinds with reserved media types

The system SHALL define the media types below, and SHALL amend the project
specification's statement that no `vnd.epos.*` wire types exist. The
prohibition that a `vnd.epos.*` type must never alter the skill artifact SHALL
remain in force and SHALL be satisfied.

| Media type | Use |
|---|---|
| `application/vnd.epos.agent.index.v1+json` | `artifactType` of the agent index |
| `application/vnd.epos.agent.definition.v1+json` | `artifactType` of the definition manifest |
| `application/vnd.epos.agent.definition.layer.v1+yaml` | the definition document blob |
| `application/vnd.epos.instruction.v1+json` | `artifactType` of an instruction manifest |
| `application/vnd.epos.instruction.layer.v1+md` | the instruction document blob |
| `application/vnd.epos.model.v1+json` | `artifactType` of a model manifest |
| `application/vnd.epos.model.layer.v1+yaml` | the model configuration blob |
| `application/vnd.epos.tool.script.v1+json` | `artifactType` of a script tool manifest |
| `application/vnd.epos.tool.script.layer.v1+tar` | the script tool payload |
| `application/vnd.epos.tool.mcp.v1+json` | `artifactType` of an MCP server tool manifest |
| `application/vnd.epos.tool.mcp.layer.v1+json` | the MCP server descriptor blob |

A referenced skill keeps the Agent Skills artifact type it already has, and a
referenced MCP server container image keeps the ordinary OCI image manifest type.

#### Scenario: The skill artifact is unchanged
- **WHEN** a skill is packed, before and after this capability exists
- **THEN** its artifact type, config media type, content layer media type,
  annotations and manifest digest are identical, because no code in the skill
  packing path changed

#### Scenario: The skill collection type is not repurposed
- **WHEN** an agent index is packed
- **THEN** it does not use the Agent Skills collection type, which belongs to a
  different specification and means a different thing

### Requirement: Every manifest uses the empty config and exactly one layer

The system SHALL set `config` to the OCI empty descriptor
`application/vnd.oci.empty.v1+json` on every manifest it creates for these kinds,
and SHALL emit exactly one layer carrying the document or payload.

#### Scenario: A definition manifest has an empty config and one layer
- **WHEN** any of the four kinds is packed
- **THEN** its config descriptor is the OCI empty descriptor and it carries
  exactly one layer of the media type this specification names for that kind

#### Scenario: A manifest with more than one layer is refused
- **WHEN** resolution encounters a manifest of one of these kinds with zero or
  more than one layer
- **THEN** it is refused naming the manifest and the layer count

### Requirement: Every document uses one envelope

The system SHALL require every document blob to use the envelope
`apiVersion: epos.dev/v1alpha1` with a `kind`, a `metadata` block carrying a
`name`, and a `spec` block. A published document SHALL NOT carry a `status`
block; the field exists so that a consumer may populate it locally.

The recognised kinds are `Agent`, `Instruction`, `Model` and `Tool`.

A document of a kind that can be packed on its own — `Agent` and `Tool` — SHALL
additionally carry `metadata.version`, because the store and the registry address
an artifact as `<name>:<version>` and taking the version only from a command-line
flag would make an artifact's identity unreproducible from its source directory.
`Instruction` and `Model` exist only inside a closure and SHALL NOT require one.

#### Scenario: A document without the envelope is refused
- **WHEN** a document blob lacks the API version, the kind, or the metadata name
- **THEN** packing fails naming which is missing and the path of the file

#### Scenario: A standalone document without a version is refused
- **WHEN** an agent or a tool is packed and its document carries no version
- **THEN** packing fails naming the field, unless a version was supplied on the
  command line, which overrides it exactly as it does for a skill

#### Scenario: A published document carrying status is refused
- **WHEN** a document carries a `status` block at pack time
- **THEN** packing fails, because status is a consumer's local annotation and not
  part of a published artifact

#### Scenario: An unrecognised kind is refused
- **WHEN** a document declares a kind this specification does not define
- **THEN** packing fails naming the kind and listing the recognised ones

### Requirement: The definition document references by name and inlines nothing

The system SHALL define the `Agent` document as identity properties plus names
resolved against index entries: a title, a description, an agent-class hint, at
most one instruction, at most one model, and lists of skills, tools and
sub-agents. It SHALL NOT inline the content of anything it references.

Every name appearing in the skills, tools and sub-agents lists SHALL exist in the
index with the matching role. Callback names SHALL NOT be checked against the
index: they are resolved by the runtime's own registry, and validating them here
would reject every agent that uses one.

#### Scenario: A definition naming an absent skill is refused
- **WHEN** the definition names a skill that no index entry carries
- **THEN** resolution fails naming the skill and the role it looked in

#### Scenario: A callback name is not required to exist in the index
- **WHEN** the definition declares a callback naming something absent from the
  index
- **THEN** packing and resolution both succeed, because callbacks are runtime
  references

#### Scenario: The definition carries no instruction body
- **WHEN** a definition document is read
- **THEN** it contains no instruction text, no model credentials and no skill
  content — every one of those is a separate artifact reached by reference

### Requirement: Credentials never appear in an artifact

The system SHALL define the `Model` document as provider, endpoint, model
identifier and generation parameters, and SHALL refuse a model document
containing a credential field. Credentials are supplied by the runtime.

#### Scenario: A model document carrying a key is refused
- **WHEN** a model document declares an API key, token, password or secret field
- **THEN** packing fails naming the field, because an artifact is published and a
  credential in it is published with it

### Requirement: Annotations identify a role, a name and a specification version

The system SHALL use the `dev.epos` reverse-DNS namespace for its own
annotations, and standard OCI annotations where one already means the right
thing.

| Annotation | Where | Required |
|---|---|---|
| `dev.epos.role` | index entry | yes |
| `dev.epos.name` | index entry | for `tool`, `skill`, `subagent` |
| `dev.epos.spec-version` | index | yes |
| `dev.epos.source` | index entry | when the entry was resolved from a reference |
| `io.modelcontextprotocol.server.name` | index entry, MCP tool manifest | for MCP server tools |
| `org.opencontainers.image.title` | index and manifests the system writes | yes |
| `org.opencontainers.image.description` | index and manifests the system writes | recommended |
| `org.opencontainers.image.created` | index, manifests | omitted unless requested |

The specification version SHALL be a semantic version string naming the version
of this format, beginning at `0.1.0`, so that a consumer can gate on it. It is
the format's version and not the tool's.

A requirement that a manifest carry an annotation SHALL bind only to manifests
the system itself writes. A referenced foreign manifest — a skill packed
elsewhere, a stock container image used as an MCP server — SHALL be validated on
its **index entry's** annotations and on nothing else, because it is carried by
digest and cannot be annotated without changing its digest.

#### Scenario: A referenced container image needs no title
- **WHEN** a closure references a stock container image as an MCP server tool
- **THEN** validation passes without that image carrying a title annotation, and
  its index entry's role, name and server-name annotations are what is checked

#### Scenario: An entry with an unknown role is carried, not refused
- **WHEN** an index entry carries a role this specification does not define
- **THEN** the index still resolves, the entry is reported as unrecognised, and
  the consumer records that it ignored it

#### Scenario: An MCP server name annotation matches the server descriptor
- **WHEN** an MCP server tool is packed
- **THEN** the annotation's value equals the name in the server descriptor, and a
  mismatch fails packing naming both

### Requirement: Packing is deterministic and carries no timestamp by default

The system SHALL omit `org.opencontainers.image.created` from every manifest and
from the index unless a timestamp is explicitly supplied. Packing the same source
twice SHALL produce the same index digest.

When a timestamp is explicitly supplied, the system SHALL state that digest
determinism is forfeited.

#### Scenario: Packing the same agent twice produces the same index digest
- **WHEN** an agent directory is packed twice, on two platforms
- **THEN** every artifact digest and the index digest are identical

#### Scenario: A requested timestamp appears and is documented as costly
- **WHEN** a creation timestamp is explicitly supplied
- **THEN** it appears on the index and on every manifest packed in that
  invocation, and the command's help states that supplying it makes two packs of
  one directory differ

### Requirement: A conforming producer and a conforming consumer are defined

The system SHALL state the conformance obligations of a producer and of a
consumer, so that an implementation that never imports epos can be conformant.

A conforming producer emits the index artifact type, exactly one definition
entry, a unique name on every skill, tool and sub-agent entry, the empty config
descriptor on every manifest it creates, and pushes the complete closure before
pushing the index.

A conforming consumer resolves a tag to a digest before execution and records it,
rejects an index with zero or several definition entries, enforces a depth limit
on sub-agent resolution, fails when the definition references a name absent from
the index, and never re-resolves a tag for the duration of an execution. A
conforming consumer MAY ignore roles it does not understand, provided it records
that it did so.

#### Scenario: The closure is pushed before the index
- **WHEN** a push is interrupted after some artifacts and before the index
- **THEN** no index referencing missing manifests was ever published, because the
  index is pushed last

#### Scenario: A tag is resolved once
- **WHEN** an execution begins from a tag
- **THEN** the tag is resolved to a digest once, the digest is recorded, and every
  subsequent fetch in that execution is by digest

#### Scenario: An artifact produced outside epos is accepted
- **WHEN** a tool artifact produced by a different implementation of this
  specification is pulled
- **THEN** epos resolves it, because conformance is defined over the bytes in the
  registry and not over the tool that wrote them
</content>
