## ADDED Requirements

### Requirement: The CLI publishes a skill without a second client

`epos` SHALL provide a `push` command that copies a skill from the local store
to an OCI registry, so that publishing a skill requires no OCI client other than
`epos`.

#### Scenario: A packed skill is published with epos alone
- **WHEN** a skill has been packed into the local store and the author runs
  `epos push` naming it and a registry
- **THEN** the skill is present in that registry and no other OCI client was
  invoked

#### Scenario: What is published is a conformant artifact
- **WHEN** a skill published by `epos push` is fetched by a client that has never
  heard of Epos
- **THEN** it fetches successfully, carries the agent-skills artifact type,
  exactly one content layer and the inlined config blob, and extracts to a
  directory indistinguishable from the one that was packed

### Requirement: Operands follow `helm push`

`push` SHALL take exactly two positional operands, in the order *what* then
*where*: a local store tag of the form `<name>:<version>`, and a registry
destination. The version SHALL come from the store tag and SHALL NOT be settable
by a flag.

#### Scenario: The familiar command line works
- **WHEN** the author writes the artifact first and the destination second, the
  way `helm push <chart.tgz> oci://<host>/<repo>` is written
- **THEN** the command is accepted

#### Scenario: There is no version flag
- **WHEN** the command's flags are inspected
- **THEN** none of them sets the name or the version, because both come from the
  artifact

#### Scenario: A bare name is refused
- **WHEN** the first operand names a skill without a version
- **THEN** the command fails, says a `<name>:<version>` tag is required, and
  points at the command that lists what the store holds

#### Scenario: A digest is refused the way pull refuses one
- **WHEN** the first operand names a digest rather than a tag
- **THEN** the command fails saying it needs a tag, consistently with `pull`,
  and nothing is sent to the registry

#### Scenario: A skill the store does not hold is refused before any request
- **WHEN** the first operand names a tag that is not in the local store
- **THEN** the command fails naming the tag, and no network request is made

### Requirement: An `oci://` prefix is accepted but not required

The destination SHALL be accepted both with and without a leading `oci://`, and
the two forms SHALL name the same registry.

#### Scenario: The helm form works
- **WHEN** the destination is written as `oci://<host>/<namespace>`
- **THEN** the prefix is stripped and the push targets `<host>/<namespace>`

#### Scenario: The epos form works
- **WHEN** the destination is written as `<host>/<namespace>`, the way every
  other epos reference is written
- **THEN** the push targets the same place as the `oci://` form

#### Scenario: A host with a port survives either form
- **WHEN** the destination names a host carrying a port, with or without the
  prefix
- **THEN** the port is part of the host and is not mistaken for a tag

### Requirement: The destination names a namespace and the skill name is appended

The repository pushed to SHALL be the destination with the skill's name appended
as a final path segment, and the remote tag SHALL be the version alone.

#### Scenario: The repository identifies the skill
- **WHEN** a skill named `reviewer` at version `1.0.0` is pushed to
  `<host>/<namespace>`
- **THEN** it lands at repository `<host>/<namespace>/reviewer`, tagged `1.0.0`

#### Scenario: Push and pull are inverses
- **WHEN** a skill is pushed and then pulled back by its published reference
- **THEN** the pulled store holds it under the same `<name>:<version>` tag it was
  pushed from

#### Scenario: The remote tag carries no name
- **WHEN** the registry's tags for that repository are listed
- **THEN** the tag is the version alone, not `<name>:<version>`

### Requirement: Push moves bytes and derives nothing

`push` SHALL transfer the manifest, config blob and content layer already in the
local store without repacking, re-deriving or altering them, and the published
manifest digest SHALL equal the digest the local store holds.

#### Scenario: The digest survives publication
- **WHEN** a skill is packed and then pushed
- **THEN** the digest `push` reports is the digest `pack` reported

#### Scenario: Pushing twice changes nothing
- **WHEN** an unchanged skill is pushed a second time
- **THEN** the digest is unchanged and the operation succeeds

#### Scenario: Annotations and media types are untouched
- **WHEN** the published manifest is compared with the one in the local store
- **THEN** its artifact type, config media type, layer media type and every
  annotation — including a derived skill's provenance annotations — are identical

#### Scenario: A built skill publishes like a packed one
- **WHEN** a skill produced by `epos build` from a Skillfile is pushed
- **THEN** it publishes by the same path, and its base and Skillfile provenance
  annotations arrive intact

### Requirement: Push reports where it published and what it published

`push` SHALL print the fully resolved reference it pushed to together with the
manifest digest, in the one-line form `pack` and `pull` already use.

#### Scenario: The resolved reference is visible
- **WHEN** a push succeeds
- **THEN** the output names the registry, the repository including the appended
  skill name, the tag and the digest

#### Scenario: A mistyped destination is visible immediately
- **WHEN** the destination already ends in the skill's own name, so the
  repository gains it twice
- **THEN** the push succeeds and the printed reference shows the doubled segment,
  rather than the mistake surfacing later as a failed pull

#### Scenario: Output is one line per push
- **WHEN** the output is piped to a tool that splits on whitespace
- **THEN** the reference and the digest are two fields of a single line, as they
  are for `pack` and `pull`

### Requirement: Publishing is not a download

`push` SHALL NOT send the download-reporting header that `pull` sends, and a
publish SHALL NOT be counted as a download.

#### Scenario: No download is recorded by a publish
- **WHEN** a skill is published through a registry that counts downloads
- **THEN** the publish leaves the download counts unchanged

### Requirement: The record of the withdrawn write path is corrected

The specification, the feature files and the generated documentation SHALL state
that `epos-registry` serves no write path **and** that the CLI has a `push`
command, and SHALL NOT state that no `epos push` exists.

#### Scenario: The specification distinguishes the server from the command
- **WHEN** the write-path section is read
- **THEN** it withdraws the `epos-registry` write path and its reasoning, and
  says the CLI publishes directly to the upstream registry

#### Scenario: No surviving claim that push does not exist
- **WHEN** the specification, the feature files and the documentation pages are
  searched for the claim that there is no `epos push`
- **THEN** no such claim remains

#### Scenario: The generated reference documents push as a command
- **WHEN** the CLI reference page is regenerated from the command tree
- **THEN** `push` appears as a command with its operands and flags, the
  hand-written section asserting publishing needs another client is gone, and the
  drift check passes

#### Scenario: The two-reference consequence still stands
- **WHEN** the write-path section is read for what it means operationally
- **THEN** it still says a user configures `epos-registry` for reading and the
  upstream registry for publishing, and still explains why no publish can be
  counted
