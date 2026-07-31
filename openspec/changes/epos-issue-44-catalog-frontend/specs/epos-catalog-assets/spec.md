## ADDED Requirements

### Requirement: The frontend ships inside the registry binary, and only that one

Every asset the catalog serves SHALL be embedded at compile time in the binary
that serves the catalog, that binary SHALL need no file outside itself to render
a page, and the command-line binary SHALL contain none of it.

#### Scenario: A fresh clone builds a complete binary offline
- **WHEN** the repository is cloned and built with no network access and no
  credentials, the module cache being already populated
- **THEN** the build succeeds and the resulting registry binary serves the
  catalog complete with its stylesheet, its scripts and its logos — a statement
  about building and running the binary, which the browser the end-to-end tier
  downloads does not weaken because that tier is not part of building it

#### Scenario: The command-line binary carries no frontend
- **WHEN** the packages reachable from the command-line binary are enumerated
- **THEN** the package holding the embedded assets is not among them, so a user
  who installs the CLI to pack and publish skills receives no component bundle,
  no stylesheet, no template and no logo

#### Scenario: Putting it back fails the build
- **WHEN** a change makes any package the command-line binary reaches import the
  embedded-asset package
- **THEN** the test suite fails naming the import, so the separation is enforced
  rather than reviewed

#### Scenario: No asset is fetched at build time
- **WHEN** the build is inspected
- **THEN** it downloads no package, runs no package manager and invokes no
  bundler; every asset is already in the repository

#### Scenario: No asset is fetched at page load
- **WHEN** a served or exported page is loaded with all third-party hosts
  unreachable
- **THEN** it renders identically, because no stylesheet, script, font or image
  is requested from another origin

### Requirement: The UI kit is vendored as a pinned built bundle

The catalog SHALL consume `gaarutyunov/ui-kit` as committed built artifacts from
a published release, pinned to a recorded version, with a documented refresh
procedure.

#### Scenario: The pinned version is recorded
- **WHEN** the vendored kit is inspected
- **THEN** the exact released version it was taken from is recorded beside it,
  along with the kit's licence

#### Scenario: Refreshing is a reviewable diff
- **WHEN** the kit is updated to a newer release
- **THEN** the update is a change to the committed files that a reviewer can see
  in the pull request, rather than a silent difference on the next build

#### Scenario: Consuming the kit needs no credential
- **WHEN** a contributor or a workflow builds the project
- **THEN** no registry token is required for the kit, because the built release
  artifacts are committed rather than installed from an authenticated package
  registry

#### Scenario: The kit is loaded once per page
- **WHEN** a catalog page is loaded
- **THEN** the kit's components are registered from a single script and its
  tokens from a single stylesheet

### Requirement: Components come from the kit; page furniture may not

Where the kit provides a component for an element the catalog needs, the catalog
SHALL use it rather than reimplement it.

#### Scenario: The leaderboard uses the kit's table
- **WHEN** the leaderboard is rendered
- **THEN** it is the kit's table component, with the rank, skill and count
  columns configured on it

#### Scenario: The stat is the kit's if the kit has one
- **WHEN** the pull count is rendered as a prominent figure on a detail page
- **THEN** it uses the kit's metric component if the pinned release provides one;
  and only if it does not may an equivalent be styled from the kit's tokens, with
  a comment recording that it exists because the pinned release lacked it

#### Scenario: Layout containers are not invented as components
- **WHEN** a grid, a footer or a prose container is needed
- **THEN** it is written as plain markup styled from the kit's design tokens,
  consistently with the kit's own position that a wrapper whose whole job is
  layout is not a component

#### Scenario: Colours and spacing come from tokens
- **WHEN** the catalog's own stylesheet is read
- **THEN** its colours, spacing, radii and type sizes reference the kit's design
  tokens rather than restating literal values

### Requirement: Markdown is rendered in Go, with raw HTML disabled and output sanitised

`SKILL.md` SHALL be treated as untrusted input, rendered server-side, with raw
HTML passthrough disabled and the result sanitised before it reaches a page.

#### Scenario: Raw HTML in a document does not reach the page
- **WHEN** a `SKILL.md` contains a raw script tag, an inline event handler, or
  an embedded object or iframe
- **THEN** none of it appears as markup in the rendered page

#### Scenario: An executable link scheme is refused
- **WHEN** a document contains a Markdown link or image whose target uses a
  scheme that can execute
- **THEN** the rendered output does not carry that target, even though the link
  was written as Markdown rather than as raw HTML

#### Scenario: Ordinary documents render fully
- **WHEN** a document uses headings, lists, tables, fenced code, emphasis,
  blockquotes and ordinary links
- **THEN** all of it renders, because the boundary is on what can execute and not
  on what is expressive

#### Scenario: Relative links do not become catalog routes
- **WHEN** a document links to a path relative to itself
- **THEN** the rendered link either resolves to something the catalog can serve
  or is rendered inert; it never resolves to an unrelated catalog page

#### Scenario: The choice is asserted, not assumed
- **WHEN** the test suite runs
- **THEN** a hostile document fixture is rendered and asserted to contain none of
  the above, so a later configuration change that re-enables raw HTML fails the
  build

#### Scenario: Rendering happens once, in Go
- **WHEN** a page containing a rendered document is delivered
- **THEN** no Markdown parser is shipped to the browser and the document is
  already HTML when it arrives

#### Scenario: The constraint is applied before HTML exists
- **WHEN** an unsafe link or image target is rejected
- **THEN** it is rejected while the document is still a syntax tree, not by
  post-processing a string of HTML

#### Scenario: No hand-written HTML sanitiser
- **WHEN** the rendering path is read
- **THEN** it contains no bespoke HTML parser or tag-stripping routine; the
  output is constrained by what the renderer is permitted to emit, and any
  additional sanitisation uses an established library

#### Scenario: The renderer is a dependency chosen for this job
- **WHEN** the Markdown renderer is inspected
- **THEN** it is a maintained, specification-compliant, pure-Go renderer whose
  own dependency footprint is minimal, and it is the only Markdown
  implementation in the module

### Requirement: Every dependency this change adds is named and justified

This change adds more than one module. Each SHALL be recorded with what it is
for and where it is linked, and none SHALL require cgo.

#### Scenario: Each addition has a stated reason
- **WHEN** the module requirements are compared before and after this change
- **THEN** every direct dependency that appeared is accounted for by a decision
  that names what it does and what was rejected in its place

#### Scenario: The hard constraint holds
- **WHEN** the added dependencies are built
- **THEN** every one of them is pure Go, so the project's cross-builds continue
  to run with cgo disabled

#### Scenario: Test-only dependencies do not reach the binaries
- **WHEN** a dependency exists only to test the catalog
- **THEN** it is reachable only from test files selected by an explicit build
  tag, and neither released binary links it

#### Scenario: The accounting says which binary each addition lands in
- **WHEN** the record of added dependencies is read
- **THEN** each entry names the binary it links into, and the entries for the
  markup renderer, the store client and the emission exporter name the registry
  binary and not the command-line one

#### Scenario: A dependency that only one page needs is not taken
- **WHEN** an addition would serve a single presentational nicety
- **THEN** it is not taken; the effect is achieved with the design tokens
  already vendored, or recorded as a follow-up

#### Scenario: The security scan stays green
- **WHEN** the project's vulnerability scan runs after the additions
- **THEN** it passes, because it is a required check and a new dependency is the
  most likely thing to break it

### Requirement: The JavaScript budget is three behaviours

Browser-side scripting SHALL be limited to behaviour that cannot be
server-rendered, and no page's primary content SHALL depend on it.

#### Scenario: Scripting does the three things it is for
- **WHEN** the catalog's own script is read
- **THEN** it covers filtering an already-delivered index, copying a command to
  the clipboard, and the theme preference — and no data fetching, routing or
  templating

#### Scenario: No framework and no build step
- **WHEN** the catalog's assets are inspected
- **THEN** there is no framework, no bundler configuration, no transpiled output
  and no source map; the script that ships is the script in the repository

#### Scenario: Content survives without scripting
- **WHEN** any catalog page is loaded with scripting unavailable
- **THEN** its content, its navigation and its links all work

#### Scenario: Copying is progressive
- **WHEN** the clipboard is unavailable
- **THEN** the install command is still visible and selectable as text
