## ADDED Requirements

### Requirement: The CLI serves and exports a catalog of a registry's skills

`epos` SHALL provide a `catalog` command with two subcommands — one that serves
the catalog over HTTP and one that writes it to a directory as static files —
so that a registry's skills can be browsed without installing anything else.

#### Scenario: A registry can be browsed
- **WHEN** the serve subcommand is run against a registry that holds skills
- **THEN** an HTTP server answers on the configured address and its pages list
  those skills

#### Scenario: The same catalog can be written to disk
- **WHEN** the export subcommand is run against the same registry
- **THEN** it writes a directory of static files, and every page in it carries
  the same content as the served page at the corresponding route

#### Scenario: One renderer, two drivers
- **WHEN** a page exists in one mode
- **THEN** it exists in the other, because a route that only one mode can
  produce is a defect

#### Scenario: The catalog is context-aware
- **WHEN** either subcommand is interrupted while it is fetching from a registry
- **THEN** the in-flight work is cancelled and the command exits, because every
  call that touches a registry, a file or a statistics source carries a context

#### Scenario: A slow registry cannot pin the server
- **WHEN** a request causes a fetch that the registry never answers
- **THEN** that fetch is bounded by a timeout and the request fails, rather than
  holding a handler indefinitely

#### Scenario: Nothing is written to the registry
- **WHEN** either subcommand runs
- **THEN** every request it makes to the registry is a read, and the local store
  is not modified

#### Scenario: No runtime beyond the binary
- **WHEN** the served or exported catalog is opened in a browser
- **THEN** it renders without a Node runtime, a package manager, a build step or
  any request to a host other than the one serving it

### Requirement: The skill list comes from one of two explicit sources

The catalog SHALL take its list of skills either from a registry catalog sweep
of a namespace or from an explicit list of references, selected by the operator.
It SHALL NOT silently fall back from one to the other.

#### Scenario: A namespace is swept
- **WHEN** a registry and a namespace are given and the registry supports
  catalog enumeration
- **THEN** the catalog contains the skills in that namespace, discovered the
  same way the list and search commands discover them

#### Scenario: A registry without catalog enumeration is reported, not worked around
- **WHEN** a namespace sweep is requested against a registry that does not
  support catalog enumeration
- **THEN** the command fails saying so, and does not quietly produce a partial
  or empty catalog

#### Scenario: An explicit reference list needs no enumeration
- **WHEN** a file of skill references is given instead of a namespace
- **THEN** each reference is resolved directly and the catalog contains exactly
  those skills, with no catalog enumeration request made

#### Scenario: A reference that cannot be resolved is named
- **WHEN** one reference in the list cannot be resolved
- **THEN** the command reports which reference failed and why, and does not
  emit a page that silently omits it

#### Scenario: Exactly one source is given
- **WHEN** both a namespace and a reference list are given, or neither is
- **THEN** the command fails saying which of the two it needs, before any
  network request is made

### Requirement: A skill is a repository, and the served index is fixed at startup

The catalog SHALL present one entry per OCI repository rather than one per
version, and a served route SHALL resolve only against the index the process
built when it started.

#### Scenario: One page per skill
- **WHEN** a repository holds several versions of a skill
- **THEN** the catalog shows one leaderboard row, one list row and one detail
  page for it, because the download counter's only key is the repository

#### Scenario: Other versions are reachable without becoming routes
- **WHEN** a skill's detail page is opened
- **THEN** the newest version is rendered and the other versions are offered,
  without each version becoming a page of its own

#### Scenario: A path naming an unknown repository is not a fetch instruction
- **WHEN** a served request names a repository that is not in the index
- **THEN** the response is a not-found, and no request is made to the registry —
  the catalog is never a proxy that fetches whatever a URL names

#### Scenario: Refreshing the index is a restart
- **WHEN** a skill is published after the server started
- **THEN** it appears once the server is restarted, and the command's
  documentation says so rather than implying the catalog is live

### Requirement: List metadata costs one manifest request per skill

Every field shown on the home, catalog and tools pages SHALL be derivable from a
skill's manifest and its inlined config. The content layer SHALL NOT be fetched
to render them.

#### Scenario: The catalog list does not download skills
- **WHEN** the home page and the catalog list page are rendered for a registry
  of skills
- **THEN** no content layer is fetched, because the name, description and
  frontmatter are already carried by the manifest and its inline config blob

#### Scenario: Frontmatter beyond name and description survives
- **WHEN** a skill's frontmatter carries fields other than name and description
- **THEN** those fields are available to the renderer, because the config is a
  document and not a fixed pair of strings

### Requirement: A skill's detail page renders its SKILL.md

Each skill SHALL have a detail page whose main body is the rendered content of
its `SKILL.md`, taken from the artifact itself.

#### Scenario: The document is the page
- **WHEN** a skill's detail page is opened
- **THEN** its main column is that skill's `SKILL.md`, rendered, and not a
  summary, an excerpt or a link to elsewhere

#### Scenario: The frontmatter is not part of the body
- **WHEN** a `SKILL.md` opens with frontmatter
- **THEN** the rendered body begins after it, and the frontmatter's fields
  appear as page metadata rather than as text at the top of the document

#### Scenario: The content layer is fetched once per artifact
- **WHEN** a detail page is served more than once for the same artifact digest
- **THEN** the content layer is fetched at most once, keyed on the digest, which
  is immutable and therefore never needs invalidating

#### Scenario: A skill whose artifact cannot be read still lists
- **WHEN** a skill's content layer cannot be fetched, is oversized, or is
  malformed
- **THEN** the catalog still lists the skill from its manifest metadata, and its
  detail page says the document could not be read rather than failing the whole
  catalog

### Requirement: The content layer is treated as untrusted input

Fetching and unpacking a skill's content layer SHALL retain every protection the
project already applies when it unpacks a layer fetched from a registry.

#### Scenario: A traversing entry is refused
- **WHEN** a content layer contains an entry whose path escapes the archive
  root, is absolute, or is not canonical
- **THEN** it is refused, and nothing is written or read outside the intended
  tree

#### Scenario: Links are refused
- **WHEN** a content layer contains a symbolic or hard link
- **THEN** it is refused

#### Scenario: An oversized layer is bounded
- **WHEN** a content layer decompresses beyond the project's existing size limit
- **THEN** the read stops at that limit and the artifact is reported as
  unreadable, rather than being read until memory is exhausted

#### Scenario: The guards are not reimplemented
- **WHEN** the routine that fetches and unpacks a remote layer is read
- **THEN** it is the project's existing remote-fetch routine, exported, rather
  than a third copy of resolve-fetch-untar written for the catalog

### Requirement: The detail page shows how the skill was built

Where a skill carries build provenance annotations, the detail page SHALL
present them, including which Skillfile stage contributed each file.

#### Scenario: Stage provenance is shown as data, not prose
- **WHEN** a skill built from a multi-stage Skillfile is opened
- **THEN** the page shows which stage contributed each file of the installed
  tree, from the artifact's own stage annotation

#### Scenario: The base and the recipe are identified
- **WHEN** a skill records a base artifact or a Skillfile digest
- **THEN** the page shows them, so two artifacts built from the same recipe can
  be recognised as such

#### Scenario: A packed skill shows no provenance section
- **WHEN** a skill was packed from a directory rather than built from a
  Skillfile, and therefore carries no stage annotation
- **THEN** the page omits the provenance section rather than showing it empty

#### Scenario: Parameters are not claimed
- **WHEN** a skill accepts install-time parameters
- **THEN** the page does not present a parameter list or a values form, because
  the artifact does not declare its parameters and the catalog would be
  inventing them

### Requirement: The home page is the leaderboard

The catalog's home page SHALL be a ranked table of skills, and ranking SHALL be
expressed as navigation between named views rather than as a hidden default.

#### Scenario: Ranked rows above anything else
- **WHEN** the home page is opened
- **THEN** its main content is a ranked table of skills, each row carrying at
  least a rank, the skill's name, the repository it lives in and its pull count

#### Scenario: A row is one link
- **WHEN** any part of a leaderboard row is activated
- **THEN** the skill's detail page opens, because the whole row is the link

#### Scenario: The ordering is named on the page
- **WHEN** the leaderboard is shown
- **THEN** the view it is showing is named, and switching to another view is a
  link to that view's own address rather than a client-side re-sort

#### Scenario: The leaderboard degrades honestly with no statistics
- **WHEN** no download statistics source is configured
- **THEN** the pull column is absent rather than zeroed, the ordering falls back
  to a stated deterministic order, and the page does not present itself as a
  ranking by popularity

### Requirement: The catalog list page supports filtering without a server round trip

The catalog SHALL have a list page carrying every skill, filterable by a text
query in the browser.

#### Scenario: Filtering is local
- **WHEN** a query is typed into the catalog list page's search field
- **THEN** the visible rows narrow without a request to the server, because the
  index the filter runs over was delivered with the page

#### Scenario: The page works with scripting unavailable
- **WHEN** the catalog list page is opened with JavaScript disabled
- **THEN** every skill is still listed and every skill's detail page is still
  reachable; only the filter is inert

#### Scenario: The filter matches what a reader can see
- **WHEN** a query matches a skill's name or its description
- **THEN** that skill's row remains visible

### Requirement: The tools page states verified capability, not compatibility by implication

The catalog SHALL have a tools page listing OCI registries and agents, and every
registry entry SHALL carry what it has been verified to support and how that was
established.

#### Scenario: Each registry row distinguishes three capabilities
- **WHEN** the registries section is read
- **THEN** each row states separately whether the registry is known to support
  pulling a skill, publishing a skill, and catalog enumeration — which epos's
  discovery requires and which is optional in the distribution specification

#### Scenario: An unverified claim says it is unverified
- **WHEN** a registry has not been exercised by the project's tests
- **THEN** its row says so, and is distinguishable at a glance from one the
  continuous integration exercises on every run

#### Scenario: The registry the project tests is marked as such
- **WHEN** the registry that the project's integration tests run against appears
  on the page
- **THEN** it is marked as verified in continuous integration

#### Scenario: The named registries appear
- **WHEN** the registries section is read
- **THEN** it includes at least the registry the project tests against and the
  forge registry named in the issue, each with its own capability status

#### Scenario: Logos are embedded and permitted
- **WHEN** a logo is shown
- **THEN** it is served from the catalog's own assets rather than fetched from a
  third-party host, and it is present only if its terms permit referential use;
  an entry without a usable logo appears as a text row

#### Scenario: Each agent row names the directory it reads
- **WHEN** the agents section is read
- **THEN** each row names the skill directory that agent reads and states
  whether `epos install` writes there by default or only when the worktree's
  manifest adds it — which is a fact a reader can act on, and which the catalog
  can be held to

#### Scenario: The default install target is marked
- **WHEN** the agent whose directory `epos install` writes to by default appears
- **THEN** it is marked as the default

#### Scenario: No agent is listed on the strength of a relationship
- **WHEN** an agent appears on the page
- **THEN** it appears because its skill directory is stated, not because it is a
  tool the project would like to be associated with

### Requirement: The catalog adopts the project's site shell

Every catalog page SHALL use the same container, header, breadcrumb and section
conventions as the project's docs site, and SHALL render the project wordmark
from a single shared asset.

#### Scenario: One container width across the site
- **WHEN** any catalog page is measured
- **THEN** its content container matches the docs site's container and gutters,
  so moving between the docs and the catalog does not change the page's shape

#### Scenario: The detail page splits content from metadata
- **WHEN** a skill detail page is viewed above the site's large breakpoint
- **THEN** the rendered document occupies the wider column and the skill's
  metadata occupies a narrower aside beside it; below that breakpoint they stack

#### Scenario: Every inner page carries a breadcrumb
- **WHEN** any page other than the catalog home is opened
- **THEN** a breadcrumb above the title names the path to it, marked up so that
  assistive technology announces the trail and the current page

#### Scenario: One wordmark asset
- **WHEN** the wordmark appears on a catalog page
- **THEN** it is rendered from the same checked-in asset the docs site uses, and
  no second copy of it exists in the repository

#### Scenario: Numbers and identifiers are monospaced
- **WHEN** a count, a digest, a repository name or a column header is rendered
- **THEN** it is set in the monospace face, consistently with both reference
  designs

### Requirement: The catalog is served under a configurable base path

Both modes SHALL take a base path, every internal link and asset reference SHALL
be prefixed with it, and the two modes SHALL produce identical output for the
same base path.

#### Scenario: The site works below the domain root
- **WHEN** the catalog is published under a path prefix rather than at a
  domain root
- **THEN** every page's links, stylesheets, scripts and images resolve, because
  each carries the prefix

#### Scenario: The prefix is not an export-only concern
- **WHEN** the two modes are run with the same base path and the same inputs
- **THEN** their output is identical, so the prefix cannot be a transformation
  one mode applies and the other does not

#### Scenario: A different prefix changes only the prefix
- **WHEN** the same catalog is produced under two different base paths
- **THEN** the two differ only in the prefix on internal references, which is
  what makes per-pull-request preview deployments possible

### Requirement: Export owns its output directory and never writes outside it

`export` SHALL create or reuse its own output directory, SHALL refuse a
directory it cannot establish as its own, SHALL remove pages it no longer
produces, and SHALL never write a file outside that directory.

#### Scenario: A fresh directory is created
- **WHEN** the output directory does not exist
- **THEN** it is created and the catalog is written into it

#### Scenario: An unrelated directory is refused
- **WHEN** the output directory exists and is not recognisable as a previous
  export's output
- **THEN** the command fails naming the directory, and nothing in it is deleted
  or overwritten

#### Scenario: A removed skill leaves no orphan page
- **WHEN** a skill present in a previous export is absent from this one, into a
  directory the previous export produced
- **THEN** its page is removed, so the published site does not serve a page for
  a skill the catalog no longer lists

#### Scenario: A registry-supplied name cannot escape the output directory
- **WHEN** a repository name or tag would produce a path outside the output
  directory
- **THEN** nothing is written, and the command fails naming the offending
  reference

#### Scenario: The same inputs produce the same output
- **WHEN** the export is run twice over the same references and the same
  statistics snapshot
- **THEN** the two directories are identical

### Requirement: The generated CLI reference stays generated

Adding the catalog command SHALL NOT bypass the documentation generator or its
drift gate.

#### Scenario: The reference page covers the new command
- **WHEN** the documentation generator runs after the catalog command is added
- **THEN** the generated CLI reference documents it, and the regenerated page is
  committed so the drift check passes

#### Scenario: The generated page is not hand-edited
- **WHEN** the catalog command's documentation changes
- **THEN** the change is made in the generator, not in the generated page

### Requirement: The project specification records the new packages and the new site surface

The project specification SHALL be updated where it enumerates the internal
packages and where it describes what the project's site serves and how it is
deployed.

#### Scenario: The package tree is current
- **WHEN** the specification's package layout is read after this change
- **THEN** it lists the packages this change adds

#### Scenario: The site surface is current
- **WHEN** the specification's description of the published site is read
- **THEN** it records that the site serves a catalog alongside the documentation,
  and how that catalog is produced and deployed

#### Scenario: Nothing else is amended
- **WHEN** the specification's sections on the registry's statelessness, its
  write path, its API surface and its metrics are compared before and after
- **THEN** they are unchanged, because this change alters none of them
