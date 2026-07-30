## ADDED Requirements

### Requirement: The project publishes its own example skill with its own tooling

The repository SHALL pack the worked example skill it ships and publish it to a
public registry from continuous integration, using `epos` itself for every step
that `epos` has a command for.

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
- **WHEN** the workflow packs the example
- **THEN** it packs the derived Go skill checked in by the landing-and-quickstart
  change, and this change does not define a second recipe for it

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

#### Scenario: The deployed site is checked, not assumed
- **WHEN** the catalog is deployed for the first time
- **THEN** the documentation site's own entry page is opened and confirmed still
  served, because none of the ways this breaks fails loudly

#### Scenario: The workflow actually fires
- **WHEN** a change is made to the Go sources that produce the catalog, without
  touching the documentation directory
- **THEN** the deployment workflow runs and the published catalog is rebuilt

#### Scenario: The export is reproducible
- **WHEN** the export is run twice against the same references and the same
  statistics snapshot
- **THEN** it produces the same files

#### Scenario: The demo enumerates by reference list
- **WHEN** the demo catalog is exported against a registry that does not offer
  catalog enumeration
- **THEN** it is exported from the checked-in reference list, and this is the
  configured mode rather than a fallback

### Requirement: The demo's numbers state their provenance

The deployed demo SHALL NOT present its download figures as a measure of general
popularity, and SHALL say on the page where they came from and when.

#### Scenario: The reader is told what the numbers are
- **WHEN** the demo's leaderboard is read
- **THEN** the page states that the counts come from the project's own demo
  pipeline and names the moment they were captured

#### Scenario: The numbers are real
- **WHEN** the statistics snapshot the demo ships is produced
- **THEN** it is produced by running the real chain — packing, publishing to a
  registry, pulling through an epos registry, and reading the counter — rather
  than being written by hand

#### Scenario: Nothing is illustrative
- **WHEN** any figure appears on the demo
- **THEN** it was measured, because a seeded or illustrative count on a page
  headed with a download figure is the one outcome worse than showing none

#### Scenario: Staleness is visible
- **WHEN** the snapshot is older than the page it is shown on
- **THEN** the page carries the snapshot's timestamp so a reader can tell

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

#### Scenario: Parametrisation is explained by the document, not fabricated by the page
- **WHEN** the example skill's parameters are described
- **THEN** the description comes from the skill's own document and from the
  values profiles checked into the repository, and the page does not present a
  parameter list as though the catalog had discovered it

#### Scenario: The demo carries more than one skill
- **WHEN** the demo catalog is opened
- **THEN** it lists several skills, so that the leaderboard, the list page and
  the filter are exercised by the demo rather than merely present in it
