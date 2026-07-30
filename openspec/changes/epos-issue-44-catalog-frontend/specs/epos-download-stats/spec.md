## ADDED Requirements

### Requirement: The catalog reads counts through a statistics source

The catalog SHALL obtain download counts from a configurable statistics source
with an off mode as its default and a mode that reads a snapshot file. Obtaining
counts SHALL take a context, and the source SHALL be the only thing that knows
where numbers come from.

#### Scenario: Off is the default and is a normal outcome
- **WHEN** no statistics source is configured
- **THEN** the catalog renders with no counts, and this is not an error — most
  registries have no epos registry in front of them

#### Scenario: A snapshot supplies the numbers
- **WHEN** the snapshot source is configured with a file of per-repository counts
- **THEN** the catalog renders those counts, which is what makes a static export
  able to show them at all

#### Scenario: A statistics source that fails does not take the catalog with it
- **WHEN** the configured source cannot be read or cannot be parsed
- **THEN** the catalog still serves every page, the counts degrade to absent,
  and the failure is reported in the process output rather than on the page as a
  zero

#### Scenario: A skill with no recorded downloads is distinguishable from one with none
- **WHEN** a skill has no row in the statistics source
- **THEN** its count renders as unknown rather than as zero

#### Scenario: Adding a source is an addition, not a rewrite
- **WHEN** a further statistics source is added later
- **THEN** nothing outside that source changes, because the interface between
  the catalog and its counts is a single context-taking method returning a
  snapshot

### Requirement: The snapshot has one shape, and it states when it was taken

The snapshot SHALL be a single document carrying a capture time and one row per
OCI repository, each row carrying the verified and unverified counts separately.
The same definition SHALL serve as both the on-disk shape and the in-memory
shape.

#### Scenario: The capture time travels with the counts
- **WHEN** a snapshot is read
- **THEN** the moment it was captured is available to the renderer, because a
  count without a time is not a fact a page can honestly state

#### Scenario: The two sides of the counter stay separate
- **WHEN** a snapshot row is read
- **THEN** verified and unverified counts are distinct fields, so the ranking
  metric is never silently the sum

#### Scenario: The repository is the key
- **WHEN** a snapshot row is matched to a skill
- **THEN** it is matched by OCI repository, which is the only key the download
  counter records

#### Scenario: There is one schema
- **WHEN** the writer of a snapshot and the reader of a snapshot are compared
- **THEN** they use the same type, so the two cannot drift

#### Scenario: A malformed snapshot is refused, not half-read
- **WHEN** a snapshot file cannot be parsed
- **THEN** it is rejected whole with an error naming the file, rather than
  yielding a partially populated set of counts

### Requirement: The snapshot is produced by running the real chain

A snapshot SHALL be derived from the download counter that an epos registry
actually incremented, through the exporter that registry already implements. It
SHALL NOT be hand-authored.

#### Scenario: The numbers were measured
- **WHEN** a snapshot is produced
- **THEN** every count in it came from an epos registry that served the
  corresponding requests

#### Scenario: No new exporter is required to read them
- **WHEN** the counter is read for a snapshot
- **THEN** it is read through an exporter the registry already implements, and
  no new exporter, endpoint or listener is added to the registry to make it
  possible

#### Scenario: The final counts are not lost
- **WHEN** the registry is stopped as part of producing a snapshot
- **THEN** the shutdown flushes the pending counts, so the last interval is
  included

### Requirement: The leaderboard ranks verified pulls and says what they are

The catalog's ranking metric SHALL be the verified side of the download counter,
and the page SHALL state what the number counts.

#### Scenario: Ranking uses the defensible number
- **WHEN** the leaderboard is ordered
- **THEN** it is ordered by downloads recorded as verified, not by the total

#### Scenario: The inflated side is never the headline
- **WHEN** unverified counts are shown at all
- **THEN** they are labelled distinctly from the ranking metric and are not what
  the leaderboard sorts on, because signature and attestation fetches land in the
  skill's own repository and cannot be told apart from pulls

#### Scenario: The column says what it counts
- **WHEN** the count column is read
- **THEN** its wording says these are pulls made by the epos client, and a
  reader can find that definition on the page rather than having to infer it

#### Scenario: A pull by the epos client is counted
- **WHEN** a skill is pulled with `epos pull` through an epos registry
- **THEN** exactly one verified download is recorded for that skill's repository

#### Scenario: A pull by another OCI client is not counted as verified
- **WHEN** the same skill is pulled by a client that does not send the epos
  download header
- **THEN** no verified download is recorded, and the leaderboard's number is
  therefore a floor and not a total

### Requirement: The registry is unchanged and stateless

This change SHALL NOT alter `epos-registry`'s configuration, its listeners, its
API surface or its statelessness.

#### Scenario: The registry API surface is untouched
- **WHEN** the registry is exercised after this change
- **THEN** it serves the same paths on the same single listener as before, and
  no metrics or catalog endpoint has been added to it

#### Scenario: No durable state is introduced anywhere
- **WHEN** the registry and the catalog are both running
- **THEN** neither writes a counter, a cache or an index to disk; the snapshot
  is an input the catalog reads and never a store it maintains

#### Scenario: The unbounded attribute stays off the wire
- **WHEN** a statistics source consumes the counter
- **THEN** it aggregates over the request user-agent rather than keying on it,
  so an attacker-supplied header cannot multiply the rows a catalog holds
