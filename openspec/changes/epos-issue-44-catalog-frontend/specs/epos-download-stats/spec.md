## ADDED Requirements

### Requirement: The download counter reaches a persistent, queryable store

The project SHALL ship a way for the download counter to leave the registry
process and land in a store that outlives it and can be queried after the fact.
A count that exists only for the lifetime of a process SHALL NOT be the basis
for anything a page shows.

#### Scenario: Counts survive the process that recorded them
- **WHEN** an epos registry that has served downloads is stopped and started
  again
- **THEN** the counts it recorded before stopping are still readable from the
  store, because they were exported to it rather than held in the process

#### Scenario: The store answers questions, not just holds rows
- **WHEN** the catalog needs the pull counts for the skills it lists
- **THEN** it obtains them by querying the store for those repositories, rather
  than by reading a log the registry happened to print

#### Scenario: History is retained, not only the latest total
- **WHEN** the store is queried
- **THEN** it holds the counter's history over time and not only its most recent
  value, so a later change can show a trend without changing where the numbers
  come from

#### Scenario: The relay never reads the store
- **WHEN** a request under the distribution API is served
- **THEN** nothing in answering it reads, queries or waits on the store; the
  relay's relationship with the store is outward emission only, and the catalog
  reading counts is a separate path that no distribution request enters

#### Scenario: A store that is unavailable does not break serving
- **WHEN** the store cannot be reached
- **THEN** the registry still serves every request it would otherwise serve, and
  the loss is metrics rather than availability

#### Scenario: Counts add up across replicas and restarts
- **WHEN** several registry instances serve downloads for the same repository,
  or one instance is restarted mid-window
- **THEN** the total the store yields for that repository is the sum of the
  downloads that were actually served, neither double-counted nor reduced to a
  single instance's share — which follows from each download being recorded as
  its own event rather than as a running total that several producers each
  maintain

#### Scenario: A download is recorded as an event, not as a running total
- **WHEN** a download is recorded for the store
- **THEN** it is emitted as one span describing that download, so counting is
  counting rows and no reader has to know how partial totals from several
  producers combine

#### Scenario: Every download is recorded, none is sampled
- **WHEN** the tracing pipeline is configured
- **THEN** the download span is always sampled, and the configuration says that
  reducing it would silently reduce every number the catalog renders

#### Scenario: The span is a measurement, not a tracing deployment
- **WHEN** the span is inspected
- **THEN** it carries only the attributes the counter carries, with no request
  headers, no automatically instrumented server span and no events, so that
  general-purpose instrumentation cannot reintroduce what this change removes

#### Scenario: The counter still behaves as it does today
- **WHEN** the registry is configured with the existing metrics exporters
- **THEN** the counter is recorded and emitted exactly as before, because the
  span is emitted beside it from the same call and the same attributes, not in
  place of it

### Requirement: The database schema is defined by this change and epos writes no code to fill it

The tables the catalog reads SHALL be defined as checked-in schema, the pipeline
that fills them SHALL be a configured collector rather than code in this
project, and the catalog's query SHALL be written against that schema rather
than discovered by an implementation.

#### Scenario: There is no ingestion code
- **WHEN** the path from a served download to a row in the store is traced
- **THEN** every step between the registry's emission and the row is a
  configured collector; this project contributes no client that writes to the
  store, no batching, no retry and no migration code

#### Scenario: The schema is checked in, not improvised
- **WHEN** the store's schema is looked for
- **THEN** it is a checked-in definition in this repository — the table the
  catalog reads and the rollup that fills it — reviewed like any other file,
  rather than something an implementation decided at the keyboard

#### Scenario: The collector's own tables are not redefined
- **WHEN** the checked-in schema is read
- **THEN** it declares only this project's own table and the rollup into it; the
  collector's tables are the collector's and are neither declared nor altered
  here

#### Scenario: The counts outlive the rows they came from
- **WHEN** the collector's raw records expire under their retention policy
- **THEN** the counts the catalog reads are unaffected, because they were rolled
  up into a table with no such expiry — a leaderboard must not quietly shrink on
  the day a retention window first closes

#### Scenario: The rollup exists before the first record arrives
- **WHEN** a deployment is brought up
- **THEN** the schema is applied before the collector's first write, because a
  rollup of this kind sees only what is written after it exists; and the
  checked-in schema records how to backfill a deployment where that ordering was
  missed

#### Scenario: The query is stated with the schema
- **WHEN** the schema is read
- **THEN** the query the catalog runs against it is stated alongside, including
  how partial rows are aggregated, so that reading the stored column directly —
  which is correct only by coincidence of timing — is not the first thing an
  implementation tries

### Requirement: Only the collector may write, and the registry holds no credential that can

Write access to the store SHALL belong to the collector alone. The registry
SHALL hold no credential for the store, and the catalog SHALL hold one that can
only read.

#### Scenario: The relay holds no database credential
- **WHEN** the registry's configuration is inspected with the catalog disabled
- **THEN** it holds an emission endpoint and no database credential of any kind,
  so compromising the process that answers unauthenticated requests from the
  public internet does not yield access to the store

#### Scenario: The catalog's credential cannot write
- **WHEN** the catalog's credential is used to attempt to create, alter, insert
  into or delete from the store
- **THEN** the store refuses it, because the grant permits reading one table and
  nothing else — "the catalog only reads" is enforced by the store and not by a
  convention an implementation has to remember

#### Scenario: A read-only credential is still bounded
- **WHEN** the catalog's credential is configured
- **THEN** limits on how long a query may run and how much it may return are
  configured with it, because a credential that can only read can still be used
  to make the store unavailable

#### Scenario: The three privileges are declared together
- **WHEN** the checked-in schema is read
- **THEN** it declares which principal writes, which reads and which holds
  nothing, so the separation is reviewable rather than assumed

### Requirement: Statistics are optional, and their absence is a configuration

Emitting measurements to a store and rendering counts SHALL be independently
optional, both off by default, and neither absence SHALL be an error or a
degraded page.

#### Scenario: A registry with no store configured behaves as it does today
- **WHEN** the registry is run without the store pipeline enabled
- **THEN** it emits nothing outward, requires no collector and no database, and
  serves exactly as it does today

#### Scenario: A catalog with no statistics source is complete
- **WHEN** the catalog is run with no statistics source
- **THEN** every page renders in full, with no count column anywhere and no
  wording that implies a ranking; this is the documented configuration for
  anyone who does not want to run a database, not a failure state

#### Scenario: The two switches are independent
- **WHEN** one of the two is enabled and the other is not
- **THEN** both combinations are supported: measurements may be collected
  without any catalog being served, and a catalog may be served without any
  measurements being collected

#### Scenario: Turning statistics off is not a code path
- **WHEN** the pages rendered with and without a statistics source are compared
- **THEN** the difference is which sections the renderer emits, not a separate
  renderer, a separate template set or a separate set of routes

### Requirement: The registry exports through its existing instrumentation path and holds no state

The registry SHALL emit the counter through the instrumentation path it already
uses, selected by the same configuration key, and SHALL remain stateless.

#### Scenario: The exporter is chosen the way exporters are already chosen
- **WHEN** an operator configures where downloads are recorded
- **THEN** they select an exporter by name, in the same configuration style and
  through the same mechanism the registry's existing settings use, and the
  existing settings continue to behave as before

#### Scenario: The existing exporters keep working
- **WHEN** the registry is configured with the exporter used for local
  development, or with metrics disabled
- **THEN** it behaves exactly as it does today, so nothing that runs the
  registry without a store is affected

#### Scenario: There is still one instrumentation path
- **WHEN** the registry's instrumentation code is read
- **THEN** a download is recorded once, at one call site, building one attribute
  set that both the counter and the span use — so the two cannot describe
  different events — and the destination is an exporter rather than a second
  code path or a database client in the request handler

#### Scenario: No durable state is held by the registry
- **WHEN** the registry is exercised after this change
- **THEN** it writes no counter, cache, index or table of its own to disk, keeps
  nothing that replicas would have to share, and remains deployable as several
  identical instances behind a load balancer

#### Scenario: The registry's API surface gains no endpoint
- **WHEN** the registry's distribution API routes are compared before and after
- **THEN** they are the same paths on the same single listener, with no metrics
  endpoint and no scrape endpoint added; the catalog, where it is enabled, is
  served from that same listener under its own prefix and adds nothing to the
  distribution API itself

#### Scenario: Exporting does not slow the request
- **WHEN** a download is recorded
- **THEN** the request is answered without waiting for the measurement to reach
  the store

### Requirement: The user-agent never reaches a store

The request's user-agent SHALL NOT be recorded as a distinguishing attribute in
any exporter that persists or exposes measurements.

#### Scenario: The persisted attribute set is bounded
- **WHEN** measurements arrive in the store
- **THEN** they are distinguished by the repository and by whether the download
  was verified, and not by the user-agent — which is attacker-supplied, of
  unbounded cardinality, and would let anyone able to fetch a blob multiply the
  rows the store keeps, forever

#### Scenario: Dropping it is enforced, not documented
- **WHEN** the metric pipeline is configured
- **THEN** the attribute is removed by the pipeline itself rather than by a
  convention the next exporter has to remember

#### Scenario: Bucketing is not the fix
- **WHEN** an alternative to dropping the user-agent is considered
- **THEN** collapsing it into a small set of client names is not adopted,
  because it restates the verified attribute — a request from the epos client is
  precisely a request carrying the epos download header — while adding a parsing
  rule that ages with every client release

#### Scenario: Filtered attributes do not leak through a side channel
- **WHEN** the pipeline is configured to drop the attribute
- **THEN** no other feature of the pipeline re-attaches the dropped attribute to
  what is exported

### Requirement: The catalog reads counts through a statistics source

The catalog SHALL obtain download counts through one interface with several
implementations, selected by the operator, and that interface SHALL be the only
thing that knows where numbers come from. Obtaining counts SHALL take a context.

#### Scenario: Off is a first-class mode
- **WHEN** no statistics source is configured
- **THEN** the catalog renders with no counts and this is not an error — most
  registries have no epos registry in front of them, and a catalog that renders
  a broken leaderboard in that case is worse than one that renders a catalog

#### Scenario: The store is a source
- **WHEN** the catalog is pointed at the statistics store
- **THEN** it queries it for the repositories it lists and renders the counts it
  gets back

#### Scenario: A file is a source
- **WHEN** the catalog is given a file of per-repository counts
- **THEN** it renders those counts, which is what lets an export be reproduced
  and tested without standing up a store

#### Scenario: Adding a source is an addition, not a rewrite
- **WHEN** a further statistics source is added later
- **THEN** nothing outside that source changes, because the interface between
  the catalog and its counts is a single context-taking method returning a set
  of per-repository counts with the moment they were current

#### Scenario: A statistics source that fails does not take the catalog with it
- **WHEN** the configured source cannot be reached, cannot be read or cannot be
  parsed
- **THEN** the catalog still serves every page, the counts degrade to absent,
  and the failure is reported in the process output rather than on the page as a
  zero

#### Scenario: A slow store cannot pin a handler
- **WHEN** a query to the statistics store does not return
- **THEN** it is bounded by a timeout and the page is served without counts,
  rather than a request being held open

#### Scenario: A skill with no recorded downloads is distinguishable from one with none
- **WHEN** a skill has no row in the statistics source
- **THEN** its count renders as unknown rather than as zero

#### Scenario: A source reports on the catalog's own skills and no others
- **WHEN** a source is asked for counts
- **THEN** it reports on the repositories this catalog lists, so that a store
  holding counts for repositories outside this catalog does not leak them into
  its pages; which repositories those are is fixed when the source is built,
  keeping the method itself a single context-taking call

#### Scenario: The catalog only reads
- **WHEN** the catalog uses a statistics source
- **THEN** it issues reads, holds no credential that could write, and never
  creates, alters or deletes anything in the store

#### Scenario: A slow store does not slow the registry's own API
- **WHEN** the statistics store is unreachable or does not answer, while the
  catalog is enabled in the same process as the relay
- **THEN** distribution API requests are served as fast as they were before, and
  no query holds a resource that answering them needs

#### Scenario: The store credential is not an argument
- **WHEN** the catalog is told how to reach the statistics store
- **THEN** the credential arrives through the environment or from a file the
  configuration names, and there is no command-line flag that accepts it at all
  — a long-running server's arguments are readable by every process on the host

#### Scenario: The credential does not reach the output
- **WHEN** the catalog logs, fails, or writes an export
- **THEN** the credential appears in none of them

### Requirement: A served catalog's counts follow the store; an exported one carries the moment it was built

Counts SHALL be obtained when a served page is requested and when an export is
produced, and SHALL never be fixed for the lifetime of a serving process.

#### Scenario: A served page reflects the store as of the request
- **WHEN** a page showing counts is served
- **THEN** the counts come from the statistics source as of that request, within
  a stated freshness bound, so that a skill pulled after the catalog started
  shows a higher number when the page is reloaded

#### Scenario: Freshness is bounded, not unbounded querying
- **WHEN** many pages are served in quick succession
- **THEN** the source is not queried once per page without limit; results may be
  held for a short, stated interval, and that interval is what "as of that
  request" is bounded by

#### Scenario: The index and the counts refresh independently
- **WHEN** counts refresh while the catalog is running
- **THEN** the set of skills the catalog lists does not change, because the index
  is still built once at startup, and the two are separate decisions

#### Scenario: An export queries once and bakes the answer
- **WHEN** the catalog is exported
- **THEN** the counts are obtained during the export and written into the pages,
  so the exported files show numbers without needing anything at the time they
  are read

#### Scenario: An exported page states when its numbers were captured
- **WHEN** an exported page shows counts
- **THEN** the moment they were captured appears on the page, because a count
  without a time is not a fact a static page can honestly state

### Requirement: A statically hosted page never queries the store itself

Where the catalog is published as static files, the store SHALL NOT be queried
from the reader's browser.

#### Scenario: No credential is published
- **WHEN** an exported page is inspected
- **THEN** it carries no address, credential or query for the statistics store,
  because publishing one would put a working credential for a queryable database
  into a public document

#### Scenario: The numbers are already in the page
- **WHEN** an exported page is loaded with every host other than its own
  unreachable
- **THEN** its counts still render, because they were resolved when the page was
  built

#### Scenario: Counts do not depend on scripting
- **WHEN** an exported page is loaded with scripting unavailable
- **THEN** its counts are still shown

### Requirement: The per-repository counts have one shape and state when they were current

The set of counts the catalog renders SHALL be one document carrying a capture
time and one row per OCI repository, each row carrying the verified and
unverified counts separately, and the same definition SHALL serve as the
on-disk shape, the query result shape and the in-memory shape.

#### Scenario: The capture time travels with the counts
- **WHEN** counts are obtained from any source
- **THEN** the moment they were current is available to the renderer

#### Scenario: The two sides of the counter stay separate
- **WHEN** a row is read
- **THEN** verified and unverified counts are distinct fields, so the ranking
  metric is never silently the sum

#### Scenario: The repository is the key
- **WHEN** a row is matched to a skill
- **THEN** it is matched by OCI repository, which is the only key the download
  counter records

#### Scenario: There is one schema
- **WHEN** the writer of a counts file and the reader of one are compared
- **THEN** they use the same type, so the two cannot drift

#### Scenario: A malformed counts file is refused, not half-read
- **WHEN** a counts file cannot be parsed
- **THEN** it is rejected whole with an error naming the file, rather than
  yielding a partially populated set of counts

### Requirement: Every number shown was measured

No figure the catalog presents SHALL be seeded, illustrative or hand-authored.

#### Scenario: The numbers came from served requests
- **WHEN** any count is shown
- **THEN** it came from a download an epos registry actually answered and
  recorded

#### Scenario: A counts file is derived, not written
- **WHEN** a counts file is produced
- **THEN** it is derived from the statistics store rather than authored by hand

#### Scenario: The final counts are not lost
- **WHEN** a registry is stopped as part of producing counts
- **THEN** its shutdown flushes the pending measurements, so the last interval
  is included

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
