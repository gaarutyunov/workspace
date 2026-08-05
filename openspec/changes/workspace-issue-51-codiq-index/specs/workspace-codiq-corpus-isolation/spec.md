## ADDED Requirements

### Requirement: A file is identified by its corpus and its path together

The system SHALL identify a source file by the pair (corpus, repo-relative
path), so that one database can hold many repositories and two repositories
sharing a repo-relative path keep separate rows and separate facts.

Every file row SHALL carry a non-null corpus, and the corpus SHALL be indexed,
because selecting one repository's files is the query every corpus-aware read
begins with.

#### Scenario: Two repositories sharing a path keep separate rows

- **WHEN** two repositories that both contain a file at the same repo-relative
  path are indexed into one database
- **THEN** the graph holds two file rows, one per corpus, each with its own
  occurrences and scopes, and neither index run removed the other's facts

#### Scenario: Re-indexing one repository leaves the others untouched

- **WHEN** one repository is indexed a second time
- **THEN** only that corpus's rows are replaced, every other corpus's row counts
  are unchanged, and the re-indexed corpus's file identifiers are the same ones
  it had before, so that other files' import edges are not invalidated

#### Scenario: A file cannot be resolved without naming a corpus

- **WHEN** the loader resolves a file row
- **THEN** the corpus is part of the lookup, and a lookup by path alone is not
  available — so a future caller cannot reintroduce the collision by omitting it

#### Scenario: Concurrent loads of the same path in different corpora do not serialise on each other

- **WHEN** two files with the same repo-relative path in two different corpora
  are loaded at the same time
- **THEN** they do not contend, because whatever serialises concurrent loads of
  one file distinguishes the two corpora

### Requirement: Coordinate resolution stops at the directory being indexed

The system SHALL resolve package coordinates from manifests in the directory it
is told to index, and SHALL NOT search any directory above it. The directory
being indexed is the repository.

#### Scenario: A manifest outside the indexed directory is never read

- **WHEN** a directory containing no manifest any resolver reads is indexed, and
  a manifest exists in a directory above it
- **THEN** that manifest is not read, and nothing about the resulting
  coordinates depends on where the indexed directory happens to sit on disk

#### Scenario: A repository with a manifest at its root is unaffected

- **WHEN** a repository whose root holds a manifest is indexed at that root
- **THEN** it resolves exactly the coordinates it resolved before this change,
  with the same scheme, manager, name, version and root

#### Scenario: Indexing a subdirectory no longer inherits the enclosing package

- **WHEN** a subdirectory of a package is indexed directly
- **THEN** it is treated as its own repository and named by its corpus, rather
  than inheriting the enclosing package's coordinate
- **AND** the tool's documentation states this, because it is a change from the
  previous behaviour and the previous behaviour is what the usage text
  described

### Requirement: A repository without a manifest is named by its corpus

The system SHALL, for an ecosystem with no manifest inside the repository,
produce a coordinate whose package name is the corpus name and whose root is the
repository root, rather than one whose name is unresolved.

The coordinate SHALL keep exactly the four components it has today, so that
descriptors, the file table's columns and the link pass's join key are unchanged
in shape.

#### Scenario: Two manifest-less repositories do not share a coordinate

- **WHEN** two repositories with no readable manifest are indexed
- **THEN** their coordinates differ by package name, so a same-named symbol in
  each renders a different descriptor

#### Scenario: No cross-repository edge is materialised

- **WHEN** two repositories that each define a symbol with the same name and the
  same relative directory are indexed, and the cross-file link pass runs
- **THEN** no derived edge joins an occurrence in one corpus to an occurrence in
  the other

#### Scenario: An unresolved version still reads as unresolved

- **WHEN** a manifest declares a package name but no version
- **THEN** the version renders as the unresolved marker exactly as before, which
  is reserved for something that genuinely cannot be determined — unlike the
  name, which now always can be

#### Scenario: Directory namespaces are relative to the repository

- **WHEN** a manifest-less repository's files are given descriptors
- **THEN** each file's namespace is its directory relative to the repository
  root, not relative to some ancestor directory outside the repository

### Requirement: The corpus is named on the command line

The system SHALL accept the corpus name as a command-line option, and SHALL
default it to the base name of the resolved repository root.

#### Scenario: The default names the repository directory

- **WHEN** a repository is indexed with no corpus given
- **THEN** the corpus is the repository directory's own name

#### Scenario: An explicit corpus overrides the default

- **WHEN** a corpus name is given explicitly
- **THEN** it is what the file rows carry and what a manifest-less repository's
  coordinate is named after

#### Scenario: The same repository indexed twice under one name is one corpus

- **WHEN** a repository is indexed twice with the same corpus name
- **THEN** the second run replaces the first run's rows rather than adding a
  second copy of the repository
