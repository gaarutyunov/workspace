## ADDED Requirements

### Requirement: Reference composition is a peer to merge composition and shares nothing with it

The system SHALL provide reference composition alongside the existing build
language's merge composition. The build language composes **files** into one
artifact; reference composition composes **artifacts** by reference, inlining
nothing and merging nothing.

The system SHALL NOT add any instruction to the build language for this purpose,
SHALL NOT give the build language any agent concept, and SHALL NOT allow a build
language reference to name an agent.

#### Scenario: The build language is unchanged
- **WHEN** the instruction reference table is read
- **THEN** it contains exactly the instructions it contained before, so the
  generated documentation page and the builder's dispatch are unchanged

#### Scenario: An agent may reference a built skill
- **WHEN** a skill produced by the build language is referenced by an agent
- **THEN** it is referenced as an ordinary skill artifact, and its build
  provenance annotations survive the reference intact

#### Scenario: A build cannot reference an agent
- **WHEN** a build declares a base that resolves to an agent index
- **THEN** the build fails naming the artifact type, because merging an index of
  references into a file tree has no meaning

### Requirement: The skill artifact is never altered by being referenced

The system SHALL carry a referenced artifact by digest without repacking,
rewriting or annotating it. A skill's manifest digest after entering a closure
SHALL equal its digest before.

#### Scenario: A referenced skill keeps its digest
- **WHEN** a published skill is referenced by an agent, packed and pushed
- **THEN** the skill manifest digest in the agent's repository equals the digest
  in the skill's own repository

#### Scenario: A referenced skill is still an ordinary skill
- **WHEN** the referenced skill is pulled from the agent's repository by a client
  with no agent knowledge
- **THEN** it extracts as an ordinary skill directory and installs unchanged

### Requirement: A directory's kind is decided by one named file at its root

The system SHALL classify a directory by exactly one marker file at its root, and
SHALL use the file name as the discriminator. The kind declared inside the
document SHALL be validated against the file it was found in, and SHALL NOT be
used to find it.

| Marker file at the directory root | Kind |
|---|---|
| the existing skill document | a skill, unchanged |
| `agent.yaml` | `Agent` |
| `tool.yaml` | `Tool` |
| `instruction.md` | `Instruction` |
| `model.yaml` | `Model` |

A directory carrying more than one marker SHALL fail at pack time naming both,
because choosing between them would let a directory silently pack as the wrong
kind. A referenced sub-directory SHALL be classified by the same rule, so no list
in the definition document carries its own convention.

An instruction and a model SHALL be found by their marker file rather than by a
name in the definition, because the definition names a role for each and not an
entry.

#### Scenario: A directory with an agent document packs as an agent
- **WHEN** a directory containing the agent marker file is packed
- **THEN** it packs as an agent closure

#### Scenario: A directory with no new marker packs as a skill
- **WHEN** a directory containing only the existing skill document is packed
- **THEN** it packs as a skill, with the digest it produced before this
  capability existed

#### Scenario: Two markers are refused
- **WHEN** a directory carries both an agent marker and a tool marker
- **THEN** packing fails naming both files

#### Scenario: The declared kind must match the file it is in
- **WHEN** the agent marker file contains a document declaring a different kind
- **THEN** packing fails naming the file and both kinds

### Requirement: A closure is authored as a directory and named by reference or by path

The system SHALL pack an agent from a directory. A name appearing in the
definition document's skills, tools or sub-agents lists SHALL be satisfied either
by a sub-directory of that directory, or by an entry that names an existing
artifact by reference.

A name with neither SHALL fail at pack time, naming the name and the path that
was looked for.

#### Scenario: A sub-directory becomes a referenced artifact
- **WHEN** the definition names a skill and a sub-directory of that name exists
- **THEN** the sub-directory is packed into the closure as its own artifact and
  appears as an index entry with that name

#### Scenario: A published artifact is referenced by name and reference
- **WHEN** the definition names a skill together with a registry reference
- **THEN** the reference is resolved to a digest once at pack time, the artifact
  is copied into the closure, and the index entry carries that digest

#### Scenario: A name with no source is refused
- **WHEN** the definition names a tool with neither a sub-directory nor a
  reference
- **THEN** packing fails naming the tool and the directory path it expected

### Requirement: The definition document is published exactly as authored

The system SHALL NOT rewrite a document at pack time. Whichever authoring form a
reference was written in SHALL appear in the published blob.

A reference written in a document SHALL be provenance only. Resolution SHALL read
the index entry and its digest, and SHALL NOT re-resolve a reference found in a
document.

#### Scenario: A document written with a reference publishes with it
- **WHEN** a definition naming a skill with a registry reference is packed
- **THEN** the published document blob still contains that reference, and packing
  the same directory again produces the same blob digest

#### Scenario: Resolution ignores a reference in a document
- **WHEN** a resolved agent's definition names a skill with a reference whose tag
  has since moved
- **THEN** resolution returns the artifact the index entry pins, and no request is
  made against that tag

### Requirement: A closure is published into one repository

The system SHALL publish an agent's complete closure into the agent's own
repository, because an OCI descriptor names no repository and an index's entries
are resolved within the repository the index was fetched from.

The documented repository convention for an agent SHALL be
`<registry>/<namespace>/agents/<agent-name>`, one agent per repository, alongside
the existing one-skill-per-repository convention. It is a convention the
publisher follows by choosing a destination namespace, and the system SHALL NOT
insert a path segment to enforce it.

A referenced artifact copied into a closure SHALL record the reference it was
resolved from in an annotation, so the copy is auditable. That annotation SHALL
be informational and SHALL NOT be resolved.

#### Scenario: The whole closure is transferred by a generic client
- **WHEN** a generic OCI client copies the agent's repository recursively
- **THEN** the definition, instruction, model, every skill, every tool and every
  sub-agent index arrive, with no epos-specific knowledge involved

#### Scenario: A referenced skill is copied, not linked
- **WHEN** an agent references a skill published in another repository
- **THEN** the skill's manifest and blobs exist in the agent's repository after
  push, and the index resolves without reaching the skill's own repository

#### Scenario: The origin of a copy is recorded
- **WHEN** a copied artifact's index entry is read
- **THEN** it names the reference it was resolved from, and resolution does not
  use it

#### Scenario: The skill's own repository stays canonical
- **WHEN** skills are listed or searched
- **THEN** the skill appears once, from its own repository, and the copies inside
  agent repositories are not enumerated as separate skills
</content>
