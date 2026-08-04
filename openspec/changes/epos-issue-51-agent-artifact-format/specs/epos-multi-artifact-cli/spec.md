## ADDED Requirements

### Requirement: One pack command produces a whole closure

The system SHALL pack an agent directory into every artifact of its closure and
its index in a single command invocation, and SHALL write them under a single
exclusive store lock so that a concurrent reader never observes a partial
closure.

Publishing an agent means publishing five or more artifacts; a command per
artifact would not be used.

#### Scenario: One command writes every artifact
- **WHEN** an agent directory containing an instruction, a model, a skill and two
  tools is packed
- **THEN** one invocation writes six artifacts and one index into the local store,
  and prints the index tag and digest

#### Scenario: A concurrent reader sees all of it or none of it
- **WHEN** a second process resolves the agent's tag while a pack is in progress
- **THEN** it either does not find the tag or finds a complete closure, never a
  partial one

#### Scenario: A directory that is not an agent still packs as a skill
- **WHEN** a directory with no agent document is packed
- **THEN** it packs as a skill exactly as before, with the same digest

### Requirement: One push command transfers a whole closure

The system SHALL push every artifact of a closure and then the index, in one
command, into the agent's own repository.

The destination SHALL be treated exactly as it is for a skill: it names a
namespace, and the artifact's own name is appended to it, always — including when
the destination's last segment already equals that name. The system SHALL NOT
insert a segment of its own to enforce the repository convention, because a rule
that silently inserts one produces a doubled segment the first time a user
follows the convention, and because de-duplicating a destination that already
ends in the artifact's name is not safe.

The index SHALL be pushed last, so that a published index never references a
manifest that is not yet present.

#### Scenario: The closure lands in the agent's repository
- **WHEN** an agent is pushed to a destination namespace
- **THEN** every artifact of the closure and the index exist in that namespace
  followed by the agent's name, and the command prints the resolved reference and
  the index digest

#### Scenario: The destination is not rewritten
- **WHEN** a destination whose last segment already equals the agent's name is
  given
- **THEN** the name is appended anyway, producing the same doubled path a skill
  push would produce, because the rule is one rule and not two

#### Scenario: The index is last
- **WHEN** a push fails partway
- **THEN** no index was published, and the registry holds unreferenced manifests
  rather than a broken index

#### Scenario: A generic client pulls what was pushed
- **WHEN** a generic OCI client copies the pushed repository recursively into an
  empty registry
- **THEN** the copy resolves as a complete agent with no epos-specific knowledge

#### Scenario: Pushing an unchanged agent twice changes nothing
- **WHEN** an unchanged agent is pushed twice
- **THEN** the second push uploads no new blob and the index digest is unchanged

### Requirement: A reference may be a digest

The system SHALL accept a digest reference wherever it accepts a tag reference
for pulling, because the format requires a consumer to resolve a tag to a digest
before execution and to execute against the digest.

An artifact pulled by digest SHALL be reachable in the local store afterwards and
SHALL survive garbage collection, and the tag form used to keep it reachable
SHALL be a valid OCI tag and SHALL be documented alongside the store's collection
rules.

#### Scenario: An agent is pulled by digest
- **WHEN** an agent is pulled by a digest reference
- **THEN** the closure is fetched and stored, and resolving that digest locally
  produces the same closure the registry produces

#### Scenario: A digest-pulled artifact survives collection
- **WHEN** the store is pruned after a pull by digest
- **THEN** the artifact is still present, because it is reachable from a tag the
  pull created

#### Scenario: A skill may also be pulled by digest
- **WHEN** a skill is pulled by a digest reference
- **THEN** it is fetched, rather than refused for naming a digest

### Requirement: The whole closure stays reachable in the store

The system SHALL keep every artifact of a closure reachable from the agent's tag
for the purposes of the store's manual collection, and SHALL NOT introduce
automatic collection, reference counting or leases.

#### Scenario: Pruning keeps a tagged agent's closure
- **WHEN** the store is pruned while an agent tag exists
- **THEN** every manifest and blob of that agent's closure survives, including
  sub-agent indexes and their contents

#### Scenario: Pruning removes an untagged closure
- **WHEN** an agent's only tag is removed and the store is pruned
- **THEN** the closure's blobs are swept, except those still reachable from
  another tag

### Requirement: Signing an index covers the closure

The system SHALL allow an agent index to be signed and verified through the
existing signature mechanism, with the signature attached as a referrer of the
index.

A signature over the index SHALL be sufficient for the whole closure, because
every reference carries its own digest and the index digest transitively fixes
them.

#### Scenario: A signed agent verifies
- **WHEN** an agent index is signed and then verified
- **THEN** verification succeeds, and reports the index digest it verified

#### Scenario: Tampering anywhere in the closure fails verification
- **WHEN** any referenced artifact is replaced with different content
- **THEN** the index digest no longer matches and verification fails

#### Scenario: Signing is unchanged for skills
- **WHEN** a skill is signed
- **THEN** the signature is byte-identical to the one produced before this
  capability existed

### Requirement: Version history is available and is not the default

The system SHALL support recording that an index supersedes a previous version of
the same agent, discoverable through the referrers mechanism, only when the
producer explicitly asks for it.

The command SHALL state, where a reader will see it, that recording a supersession
makes the superseded version undeletable while the new one exists and places the
new version alongside signatures in the previous version's referrers.

The superseded artifact SHALL NOT be transferred by a push. Only its descriptor
is recorded, and it is expected to be already present at the destination, which
is the only situation in which a version history means anything. A push SHALL NOT
attempt to copy it, because doing so would fail whenever the previous version is
absent from the local store — which is the normal case.

#### Scenario: A supersession does not drag the old version along
- **WHEN** an agent recording a supersession is pushed and the superseded version
  is not in the local store
- **THEN** the push succeeds and transfers only this version's closure

#### Scenario: Supersession is recorded only on request
- **WHEN** an agent is packed without asking for supersession
- **THEN** the index carries no subject, and its referrers relationship is
  available for other uses

#### Scenario: A recorded supersession is discoverable
- **WHEN** an agent is packed naming the version it supersedes
- **THEN** the previous version's referrers include the new index, distinguishable
  from a signature by its artifact type

### Requirement: Agents are discoverable through the existing mechanism

The system SHALL annotate an agent index with the same title and description
annotations that discovery already reads, so that agents are listed and searched
with no new endpoint, no server-side query and no epos-specific representation.

Discovery's existing limits SHALL be unchanged: it remains available only against
registries that support catalog enumeration, and remains client-side.

#### Scenario: An agent is listed and searched
- **WHEN** agents and skills are published to one namespace and listed
- **THEN** both appear, and searching the agent's description matches it

#### Scenario: Discovery limits are unchanged
- **WHEN** listing runs against a registry with no catalog support
- **THEN** it reports the capability as unavailable exactly as before, and a
  direct reference still resolves
</content>
