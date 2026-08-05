## ADDED Requirements

### Requirement: The indexed projects are declared, not discovered

The workspace SHALL hold a committed configuration file naming each project to
be indexed, its corpus name and its path, and the index run SHALL index exactly
the projects that file names.

Scanning `projects/` and indexing whatever is found SHALL NOT be the rule,
because the directory holds trees of wildly different size and kind and some of
them carry no code at all.

#### Scenario: The run indexes what the file names

- **WHEN** the index run is started
- **THEN** it indexes each project the configuration file lists, and nothing
  else

#### Scenario: A project is added by editing configuration

- **WHEN** another project is to be indexed
- **THEN** it is added by editing the configuration file, with no change to any
  script or to the indexer

#### Scenario: A deferred project records why it is deferred

- **WHEN** a project under `projects/` is deliberately not indexed
- **THEN** the configuration file names it and states the reason, so that
  someone about to add it reads the reason first

#### Scenario: A missing project is reported, not skipped silently

- **WHEN** the configuration names a project whose path does not exist
- **THEN** the run reports it by name and fails, rather than indexing a smaller
  corpus than was asked for

### Requirement: Projects are indexed one at a time

The index run SHALL invoke the indexer once per project, in sequence, and SHALL
NOT run two indexers against the same database concurrently.

#### Scenario: No two indexers overlap

- **WHEN** the run indexes several projects
- **THEN** each invocation completes before the next begins

#### Scenario: A failed project does not abandon the rest

- **WHEN** one project's index fails
- **THEN** the run reports which project failed and with what, and the operator
  can resume the remaining projects without re-indexing the ones that succeeded

#### Scenario: Re-running the whole set is safe

- **WHEN** the index run is executed twice over an unchanged set of projects
- **THEN** the second run leaves the same graph behind as the first

### Requirement: The run reports what it indexed

The index run SHALL report, per project, the files it walked, the files it
loaded, the files it skipped and the time it took, and SHALL report the totals
across the set.

#### Scenario: Skipped files are named

- **WHEN** a project contains files the indexer could not parse
- **THEN** the run's report names them, because a file missing from the graph is
  indistinguishable from a file with nothing in it

#### Scenario: The report is the comparison's input

- **WHEN** the comparison reports index cost
- **THEN** it takes wall-clock time and files-indexed-over-files-present from
  this report rather than from a separate measurement

### Requirement: The index runs against codiq's own local stack

The index run SHALL use codiq's committed Docker Compose deployment as-is for
PostgreSQL, the schema migration and the read surface, and SHALL NOT define a
second deployment of its own.

#### Scenario: No database configuration is duplicated here

- **WHEN** the stack is brought up
- **THEN** the PostgreSQL version, the credentials, the checkpoint database and
  the read surface all come from codiq's deployment, and this workspace declares
  none of them

#### Scenario: A schema change is picked up by rebuilding

- **WHEN** the graph's schema changes
- **THEN** the documented procedure is to tear the volumes down and re-index,
  not to migrate the existing volume in place

#### Scenario: The run refuses to start without room

- **WHEN** the machine has less free disk than the run's stated floor
- **THEN** the run stops with that measurement in the message rather than
  starting work that will fail partway through
