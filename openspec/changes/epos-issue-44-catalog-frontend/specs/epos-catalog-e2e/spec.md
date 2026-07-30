## ADDED Requirements

### Requirement: The frontend is exercised in a real browser

The catalog SHALL be covered by end-to-end tests that drive a real browser
against a running catalog, so that navigation and rendering are asserted as a
reader experiences them rather than as template output.

#### Scenario: The tests drive a browser, not a template
- **WHEN** the end-to-end suite runs
- **THEN** it loads pages in a browser engine and asserts on what the rendered
  document contains, so a page that produces correct HTML but does not render is
  a failure

#### Scenario: Both modes are covered
- **WHEN** the suite runs
- **THEN** it covers the served catalog and the exported static directory, the
  latter served by a plain static file server, because the deployed demo is the
  exported form and only exercising the served form would leave it untested

#### Scenario: The catalog under test is a real one
- **WHEN** the suite sets up its subject
- **THEN** the catalog is built from skills packed, published and pulled through
  a real registry, consistently with the project's rule against substituting
  fakes for the registry

#### Scenario: The suite does not depend on the published site
- **WHEN** the suite runs
- **THEN** it never requests the project's deployed site, so a deployment
  outage, a stale publish or an unavailable network host cannot make it pass or
  fail for reasons unrelated to the change under test

#### Scenario: The scenarios are written where the project's scenarios live
- **WHEN** the end-to-end behaviour is read
- **THEN** it is expressed in the project's own feature files rather than
  paraphrased into test code, consistently with how every other behaviour in the
  project is specified

### Requirement: Navigation works from every page the catalog serves

Every link the catalog emits SHALL resolve, and the suite SHALL walk the site
rather than checking one page.

#### Scenario: The leaderboard leads to a skill
- **WHEN** a leaderboard row is activated
- **THEN** that skill's detail page loads and shows that skill

#### Scenario: Every page in the route table is reachable
- **WHEN** the site is walked from the home page
- **THEN** the catalog list, a skill detail page and the tools page are all
  reached by following links, without a URL being typed

#### Scenario: No link is broken
- **WHEN** the internal links on every page are followed
- **THEN** each resolves, so a base-path mistake — the failure this design's
  prefix rule exists to prevent — fails the suite instead of the deployment

#### Scenario: Breadcrumbs return where they say
- **WHEN** a breadcrumb link on an inner page is activated
- **THEN** the page it names is loaded

#### Scenario: Assets load
- **WHEN** any page is loaded
- **THEN** its stylesheet, its script and its images all load, and no request is
  made to a host other than the one serving the page

### Requirement: Pages render their content correctly

The suite SHALL assert that each page shows the content it exists to show, not
merely that it responded.

#### Scenario: The leaderboard shows ranked rows
- **WHEN** the home page is loaded
- **THEN** it shows a row per skill, in descending order of the ranking metric,
  each carrying a rank, a name and a count

#### Scenario: The detail page shows the rendered document
- **WHEN** a skill's detail page is loaded
- **THEN** the skill's own document is present as rendered markup — headings as
  headings, lists as lists, tables as tables — and not as raw source and not as
  its frontmatter

#### Scenario: The filter narrows the list
- **WHEN** a query is typed into the catalog list page's filter
- **THEN** the visible rows narrow to those that match

#### Scenario: The tools page shows its table
- **WHEN** the tools page is loaded
- **THEN** each registry row shows its three capability statuses and how each
  was established

#### Scenario: A hostile document is inert in the browser
- **WHEN** a skill whose document contains a script, an event handler and an
  executable link scheme is opened
- **THEN** the browser executes nothing from it and the page carries no such
  target, asserted in the browser rather than only against a rendered string

#### Scenario: The page reports no errors
- **WHEN** any page is loaded
- **THEN** the browser reports no uncaught script error and no failed request

### Requirement: A pull changes the number a served catalog shows on refresh

Against the served catalog, downloading a skill SHALL change the count that
skill's pages show once the page is reloaded.

#### Scenario: The count moves after a pull
- **WHEN** a skill's count is read from the served catalog, that skill is then
  pulled through an epos registry, and the page is reloaded
- **THEN** the count shown for that skill has increased

#### Scenario: The count that moves is the ranking metric
- **WHEN** the pull was made by the epos client
- **THEN** the number that increased is the verified count the leaderboard ranks
  on, not only a total

#### Scenario: Counts are read when the page is served, not once at startup
- **WHEN** a served page showing counts is requested
- **THEN** the count it shows reflects the statistics source as of that request,
  within a stated freshness bound, so a long-running catalog does not serve the
  numbers it started with

#### Scenario: The skill index is still fixed at startup
- **WHEN** a skill is published after the catalog started
- **THEN** it does not appear until the catalog is restarted, because the counts
  refreshing and the index refreshing are separate decisions and only the first
  is made here

### Requirement: A static export's numbers change when it is rebuilt, and only then

The exported catalog SHALL carry the counts that were true when it was exported,
and the suite SHALL assert that this is what happens rather than leaving it to be
discovered in production.

#### Scenario: A reload of a static page does not change the number
- **WHEN** an exported page is loaded, a skill is pulled, and the page is
  reloaded from the same exported directory
- **THEN** the number is unchanged, because a static file cannot know about the
  pull — and this is asserted, so the difference from the served mode is a
  tested property

#### Scenario: A re-export carries the new numbers
- **WHEN** the catalog is exported again after further pulls
- **THEN** the newly exported page shows the higher count

#### Scenario: The page says when its numbers were captured
- **WHEN** an exported page showing counts is loaded
- **THEN** the capture time is present on the page, so a reader can tell how old
  the numbers are

### Requirement: The browser tooling stays out of the shipped binaries

The end-to-end tooling SHALL be confined to the test tier and SHALL not become a
requirement for building, installing or running either binary.

#### Scenario: Neither binary links the browser tooling
- **WHEN** the released binaries are built
- **THEN** neither contains the browser automation library or any part of its
  driver, and the constraint that the project builds without cgo is unaffected

#### Scenario: The ordinary test run does not need a browser
- **WHEN** the project's unit tests are run
- **THEN** they run without a browser, without a driver download and without
  network access, because the end-to-end tier is selected explicitly

#### Scenario: The browser and driver are pinned
- **WHEN** the end-to-end suite provisions its browser
- **THEN** the driver and browser versions are pinned and recorded, and
  continuous integration caches them, so a suite passing today and failing
  tomorrow means the catalog changed and not that an upstream browser did

#### Scenario: The runtime the harness downloads is not a runtime the product needs
- **WHEN** the project's claim that the catalog needs no separate runtime is
  read
- **THEN** it is stated as a claim about building, serving and rendering the
  catalog, and the test harness's own driver is named as test tooling, so the
  two statements do not contradict each other

#### Scenario: The dependency is declared and its cost is stated
- **WHEN** the module requirements are read after this change
- **THEN** the browser automation library appears with a recorded reason, so
  that the project's existing decision to keep browser drivers out of its
  dependency graph is met with an argument rather than being quietly reversed
