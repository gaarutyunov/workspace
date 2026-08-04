## ADDED Requirements

### Requirement: Resolution walks an index into a closure

The system SHALL resolve a reference into a closure: the index digest, the
definition document, at most one instruction, at most one model, the referenced
skills, the referenced tools, and the recursively resolved sub-agents.

A tag SHALL be resolved to a digest exactly once, at the start of resolution.
Every subsequent fetch SHALL be by digest.

Resolution SHALL be idempotent: the same digest SHALL always produce the same
closure, so a caller may cache it and may retry it.

#### Scenario: A tag resolves into a complete closure
- **WHEN** an agent is resolved from a tag
- **THEN** the closure carries the index digest, the definition, the instruction
  and model where present, every skill, every tool and every sub-agent

#### Scenario: The same digest twice yields the same closure
- **WHEN** one digest is resolved twice
- **THEN** the two closures are equal, which is what makes resolution safe to
  retry inside a durable step

#### Scenario: A moved tag does not change a resolution in progress
- **WHEN** the tag an execution began from is moved to a different digest
  mid-execution
- **THEN** the resolution continues against the digest it recorded, and no request
  is made against the tag again

### Requirement: Fetched bytes are verified against their descriptor

The system SHALL verify every fetched manifest and blob against the digest of the
descriptor that named it, and SHALL refuse content that does not match.

This is what makes the format's acyclicity argument true rather than assumed: a
graph is content-addressed only if the content is checked.

#### Scenario: A blob whose bytes do not match its digest is refused
- **WHEN** a store or a registry returns bytes whose digest differs from the
  descriptor's
- **THEN** resolution fails naming the descriptor, and no part of the closure
  built from those bytes is returned

### Requirement: Resolution memoises by digest and bounds its depth

The system SHALL keep a map from digest to resolved closure for the whole
resolution, shared across siblings and not scoped to one recursion path. A digest
already resolved SHALL return its memoised closure rather than being fetched
again.

A repeated digest SHALL NOT be an error. An agent that legitimately names one
sub-agent more than once, directly or through two branches, SHALL resolve.

The system SHALL enforce a maximum sub-agent depth of 16, and SHALL fail with a
distinct depth error naming the depth and the entry that exceeded it.

The system SHALL retain a distinct cycle error, and SHALL document that it is an
internal assertion which resolution never returns in practice: its only case is a
digest encountered while its own resolution is still in progress, and digest
verification makes that unreachable, because mismatched content fails
verification before it is ever parsed. It exists because a consumer's published
interface names it, and because it is what would catch a future change that
bypassed the verifying fetch path.

#### Scenario: A diamond resolves each artifact once
- **WHEN** two sub-agents of one agent reference the same sub-agent
- **THEN** the shared sub-agent is fetched once, both parents carry the same
  resolved closure, and resolution does not fail

#### Scenario: Depth beyond the limit fails distinctly
- **WHEN** sub-agent nesting exceeds the maximum depth
- **THEN** resolution fails with the depth error, naming the depth reached and the
  entry at which it was exceeded

#### Scenario: The cycle error is an assertion, not an outcome
- **WHEN** resolution runs against a content store that verifies digests
- **THEN** the cycle error is never returned, and the documentation says so, so
  that a consumer does not write a live branch on an unreachable case
- **AND WHEN** resolution is driven by a deliberately non-verifying fetcher that
  returns content contradicting its descriptor
- **THEN** the cycle error is returned, which is the assertion firing rather than
  a modelling mistake being reported

### Requirement: Resolution fetches documents and does not fetch payloads

The system SHALL fetch, as part of resolution: the index, every referenced
manifest and its annotations, the definition document, the instruction document,
the model document, and an MCP server tool's server descriptor.

The system SHALL NOT fetch, as part of resolution: skill content layers, script
tool payloads, or container images.

A skill and a script tool SHALL be returned as a descriptor together with the
manifest's annotations, which is enough to name, describe, dispatch and pin
them. A script tool's own document lives inside its payload and is therefore not
fetched either; the manifest annotations carry its name, runtime and description
precisely so that it need not be. Payloads SHALL be materialised only by an
explicit request.

An MCP server tool's descriptor is the exception and is fetched: it is a small
document, it carries no executable bytes, and it is where a consumer finds how to
reach the server.

#### Scenario: Resolving an agent does not download skill content
- **WHEN** an agent referencing several skills is resolved
- **THEN** no skill content layer is fetched, and the closure names each skill by
  descriptor and annotation

#### Scenario: Resolving an agent does not open a script tool
- **WHEN** an agent referencing script tools is resolved
- **THEN** no tool payload is fetched, and each tool's name, runtime and
  description are available from its manifest's annotations

#### Scenario: An MCP server tool is fetched
- **WHEN** an agent referencing an MCP server tool is resolved
- **THEN** the server descriptor is fetched, so the closure names how the server
  is reached

#### Scenario: A payload is available on request
- **WHEN** a caller explicitly asks for a referenced skill's or tool's content
- **THEN** the layer is fetched and verified against the descriptor already in
  the closure, with no second resolution

#### Scenario: A caller can tell what has been materialised
- **WHEN** a closure is inspected
- **THEN** it is unambiguous for every entry whether its content is present or
  only its descriptor, so a caller never reads an empty payload as an empty
  artifact

#### Scenario: Resolution cost is bounded by the number of documents
- **WHEN** an agent referencing a large skill is resolved
- **THEN** the bytes transferred are proportional to the documents and manifests,
  not to the skill's size

### Requirement: Resolution works against the local store and against a registry

The system SHALL resolve from the local store and from a remote registry through
one code path, so that a locally packed agent and a published one resolve
identically.

Registry access SHALL reuse the project's single registry client, its credential
handling and its plain-HTTP option; a second registry client SHALL NOT be
introduced.

#### Scenario: A locally packed agent resolves without a network
- **WHEN** an agent packed into the local store is resolved by its tag
- **THEN** it resolves with no registry request, and produces the same closure it
  produces after being pushed and resolved from the registry

#### Scenario: Resolution against a private registry uses the configured credential
- **WHEN** an agent is resolved from a registry the user has logged in to
- **THEN** the stored credential is used, and a missing credential produces the
  same explanatory error the other registry commands produce
</content>
