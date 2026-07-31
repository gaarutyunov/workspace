## ADDED Requirements

### Requirement: The project publishes its own example skills with its own tooling

The repository SHALL pack the worked example skills it ships — including the
skill that teaches how to author skills with Epos — and publish them to a public
registry from continuous integration, using `epos` itself for every step that
`epos` has a command for.

#### Scenario: epos packs its own example
- **WHEN** the publishing workflow runs
- **THEN** the example skill is packed by `epos pack`, not by a hand-assembled
  artifact or another tool

#### Scenario: Publishing requires no client the project does not ship
- **WHEN** the workflow publishes the example
- **THEN** it authenticates and pushes with the CLI's own commands, and no
  separate OCI client is installed or invoked

#### Scenario: Publishing needs no new secret
- **WHEN** the workflow authenticates to the demo registry
- **THEN** it uses the credential the workflow already has for the repository's
  own package namespace, with the job granted permission to write packages

#### Scenario: The two credential failures stay distinguishable
- **WHEN** the publish step fails because no credential is stored, or because a
  stored credential was rejected
- **THEN** the workflow surfaces the CLI's own message for whichever occurred,
  rather than collapsing both into one condition — a rejected credential and an
  absent one send whoever is debugging to different places

#### Scenario: The published artifact is the one that was built
- **WHEN** the published artifact is compared with the one in the local store
- **THEN** they are the same bytes, because publishing copies and never
  re-derives

#### Scenario: The example is the one the sibling change defines
- **WHEN** the workflow packs the derived Go example
- **THEN** it packs the derived Go skill checked in by the landing-and-quickstart
  change, and this change does not define a second recipe for it

#### Scenario: The Epos skill is published too
- **WHEN** the publishing workflow runs
- **THEN** it also packs and publishes the skill that teaches authoring skills
  with Epos, so that the registry the demo browses holds a skill about the tool
  that packed it

#### Scenario: The generated references are current when the skill is packed
- **WHEN** the Epos skill is packed
- **THEN** the generated references inside it are the ones the documentation
  generator produces from the current sources, because the drift check has
  already passed — a published skill carrying a reference for a command that no
  longer takes that flag is worse than no reference

#### Scenario: The demo survives the sibling change not landing
- **WHEN** the derived Go example is unavailable because the sibling change has
  not merged
- **THEN** the demo still publishes and renders the Epos skill, so the catalog,
  its pages and its counts are demonstrable — with one skill rather than two,
  and without the multi-stage provenance the derived example exists to show

### Requirement: The published site is rendered from real data during continuous integration

The deployed catalog SHALL be produced by rendering the real catalog to HTML
during the build, from the real skills and their real documents, and SHALL NOT
be assembled in the reader's browser.

#### Scenario: The HTML is produced by the build, not by the browser
- **WHEN** a deployed catalog page is loaded
- **THEN** its content is already HTML when it arrives; nothing fetches data,
  renders a template or converts a document in the browser

#### Scenario: The documents are converted during the build
- **WHEN** the site is built
- **THEN** each skill's document is converted from its source markup to HTML by
  the build, so the published site holds finished pages

#### Scenario: The site is the real catalog, not a fixture
- **WHEN** the deployed site is compared with what the catalog command produces
  against the demo registry
- **THEN** they are the same thing, because the deployment runs that command
  against the real registry rather than rendering a checked-in sample

#### Scenario: The result is a directory of files
- **WHEN** the build finishes
- **THEN** it has produced a directory of static files that any file server can
  serve, because the host it is published to serves files and cannot run the
  binary that produced them

#### Scenario: The renderer is the project's own
- **WHEN** the rendering step is read
- **THEN** it is the catalog command in this repository, so the deployed site
  and a catalog served locally cannot diverge

### Requirement: The demo's leaderboard is packed with traffic the build generated

Continuous integration SHALL drive download traffic against the demo's skills
before the site is rendered, and the leaderboard SHALL be filled from that
traffic.

#### Scenario: The traffic is real requests
- **WHEN** the demo's numbers are produced
- **THEN** they come from downloads an epos registry answered during the build,
  through the same pull path a user would take, and not from rows inserted into
  a store

#### Scenario: The whole chain runs
- **WHEN** the traffic is generated
- **THEN** the skills are packed, published to a registry, pulled through an
  epos registry, and the resulting measurements reach the statistics store the
  catalog then queries

#### Scenario: The distribution makes the leaderboard mean something
- **WHEN** the traffic is generated
- **THEN** different skills receive different numbers of pulls, so the
  leaderboard demonstrates a ranking rather than showing every row with the same
  count

#### Scenario: Both sides of the counter are exercised
- **WHEN** the traffic is generated
- **THEN** it includes pulls made by the epos client and fetches made without
  the epos download header, so the verified and unverified columns are both
  populated by something real

#### Scenario: The traffic is reproducible in shape
- **WHEN** the traffic generator is run twice
- **THEN** it drives the same pattern of pulls, so a change in the published
  numbers means the catalog changed rather than the generator having improvised

#### Scenario: Simulated traffic is labelled as simulated
- **WHEN** the demo's numbers are presented
- **THEN** the page says they were generated by the project's own build and are
  not a measure of how often anyone else has pulled these skills

### Requirement: The demo is deployed to the project's existing site

The catalog SHALL be exported as static files and published to the project's
existing documentation site, under its own path, without displacing the docs.

#### Scenario: The demo is reachable
- **WHEN** the deployment workflow has run on the default branch
- **THEN** the exported catalog is served from the project's site under a
  catalog path

#### Scenario: Publishing the catalog does not remove the docs
- **WHEN** the catalog is published
- **THEN** the documentation pages already published remain served, and
  publishing the documentation likewise leaves the catalog served

#### Scenario: The catalog is published to its own subdirectory
- **WHEN** the catalog is published to the site's branch
- **THEN** it lands under its own directory rather than at the branch root,
  because a payload published at the root replaces the documentation's own entry
  page regardless of any setting that preserves untouched files

#### Scenario: The catalog is not built where the docs build clears
- **WHEN** the catalog is exported
- **THEN** it is written outside any directory the documentation build treats as
  its output, so building the documentation cannot delete it

#### Scenario: The two publishers do not race
- **WHEN** a change triggers both the documentation deployment and the catalog
  deployment
- **THEN** they are serialised, because both rewrite the same branch and two
  concurrent rewrites lose one of the two while both report success

#### Scenario: Serialising is not cancelling
- **WHEN** one of the two deployments starts while the other is in flight
- **THEN** the second waits for the first and then runs; it does not cancel it —
  a shared concurrency setting that cancels in progress would leave the
  cancelled deployment silently unpublished, which is a different failure from
  the race and not a fix for it

#### Scenario: The deployed site is checked, not assumed
- **WHEN** the catalog is deployed for the first time
- **THEN** the documentation site's own entry page is opened and confirmed still
  served, because none of the ways this breaks fails loudly

#### Scenario: The site's own publishing state is confirmed healthy
- **WHEN** the catalog is deployed
- **THEN** the hosting provider's build for the site is confirmed to be
  succeeding, because a deployment that pushes files to a branch reports success
  regardless of whether the site itself last built

#### Scenario: The workflow actually fires
- **WHEN** a change is made to the Go sources that produce the catalog, without
  touching the documentation directory
- **THEN** the deployment workflow runs and the published catalog is rebuilt

#### Scenario: The export is reproducible
- **WHEN** the export is run twice against the same references and the same
  counts
- **THEN** it produces the same files

#### Scenario: The demo enumerates by reference list
- **WHEN** the demo catalog is exported against a registry that does not offer
  catalog enumeration
- **THEN** it is exported from the checked-in reference list, and this is the
  configured mode rather than a fallback

### Requirement: The demo's numbers state their provenance

The deployed demo SHALL NOT present its download figures as a measure of general
popularity, and SHALL say on the page where they came from, over what period and
when they were captured.

#### Scenario: The reader is told what the numbers are
- **WHEN** the demo's leaderboard is read
- **THEN** the page states that the counts come from traffic the project's own
  build generated and names the moment they were captured

#### Scenario: The window is stated
- **WHEN** the counts cover a bounded period rather than all time
- **THEN** the page says which period, so a reader does not read a build's worth
  of traffic as a lifetime total

#### Scenario: The numbers are real
- **WHEN** the counts the demo ships are produced
- **THEN** they are produced by running the real chain — packing, publishing to
  a registry, pulling through an epos registry, and querying the statistics
  store — rather than being written by hand

#### Scenario: Nothing is illustrative
- **WHEN** any figure appears on the demo
- **THEN** it was measured, because a seeded or illustrative count on a page
  headed with a download figure is the one outcome worse than showing none

#### Scenario: Staleness is visible
- **WHEN** the counts are older than the page they are shown on
- **THEN** the page carries their capture time so a reader can tell

### Requirement: The demo shows what the example skill demonstrates

The demo's pages SHALL surface the capabilities the example skill was built to
show, from artifact data where the artifact carries it.

#### Scenario: The multi-stage build is visible
- **WHEN** the example skill's detail page is opened
- **THEN** it shows which stage contributed each file, so that the derivation
  from several upstream skills is visible as data rather than asserted in prose

#### Scenario: What was dropped is legible
- **WHEN** the example skill's page and document are read
- **THEN** a reader can see that the derived skill omits the material the recipe
  drops, because the rendered document is the derived one and not any upstream
  original

#### Scenario: Parametrisation is shown from the skill's declared contract
- **WHEN** the example skill declares a values schema
- **THEN** the page shows the parameters it declares, with their types, defaults
  and descriptions, taken from the artifact rather than from prose about it

#### Scenario: Parametrisation is not fabricated where it is not declared
- **WHEN** the example skill carries no values schema
- **THEN** the page shows no parameter table, and the parameters are described
  by the skill's own document and by the values profiles checked into the
  repository

#### Scenario: The demo carries more than one skill
- **WHEN** the demo catalog is opened
- **THEN** it lists several skills, so that the leaderboard, the list page and
  the filter are exercised by the demo rather than merely present in it

#### Scenario: The Epos skill's page shows what it teaches
- **WHEN** the Epos skill's detail page is opened
- **THEN** its rendered document is the skill's own entry document, and the
  references it names are part of the artifact rather than links off the page

#### Scenario: The demo is served by the registry it browses
- **WHEN** the served form of the demo is exercised
- **THEN** the pages and the distribution API come from the same process, so the
  registry that counted a pull is the one that renders the number

### Requirement: The deployed demo is verified in a browser before it is called done

The demo SHALL be covered by the end-to-end suite against the artefact that gets
deployed, not only against a locally served catalog.

#### Scenario: The exported directory is the subject
- **WHEN** the end-to-end suite runs against the demo
- **THEN** it runs against the exported directory the deployment publishes,
  served by a plain file server, so what is asserted is what gets deployed

#### Scenario: The base path is exercised
- **WHEN** the exported directory under test was produced with the base path the
  deployment uses
- **THEN** every link and asset resolves under that prefix, because a prefix
  mistake is invisible until the site is published

#### Scenario: The demo's numbers are asserted, not eyeballed
- **WHEN** the suite runs against the demo's export
- **THEN** it asserts that the leaderboard carries the counts the build's traffic
  produced and that the capture time is present
