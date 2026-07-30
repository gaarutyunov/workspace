## ADDED Requirements

### Requirement: A PR preview serves the same site as production

A preview deployment SHALL serve the same assets as the production deployment,
including the PostgreSQL runtime, so that the feature under review can be
exercised in the preview.

#### Scenario: Execution works in a preview
- **WHEN** a reviewer opens a PR preview and triggers execution
- **THEN** it behaves exactly as it does on the production site

#### Scenario: No production-only asset path
- **WHEN** the site is built for a preview
- **THEN** no asset is withheld from it that production serves

#### Scenario: Preview subpaths still resolve
- **WHEN** the site is served from a preview subpath rather than the site root
- **THEN** every asset, including the runtime's binary assets and the worker
  module, resolves relative to the deployed path

### Requirement: Repeated deployments do not accumulate runtime copies

Because the runtime is pinned to an immutable build, its bytes SHALL be
identical across every deployment, so that repeated deployments and concurrent
previews do not add to the published branch's stored size.

#### Scenario: The same bytes are published every time
- **WHEN** the site is built twice from the same pin, on different machines
- **THEN** the runtime's binary assets are byte-identical

#### Scenario: Concurrent previews cost one copy
- **WHEN** several previews are published at once
- **THEN** the published branch stores one copy of the runtime's bytes, not one
  per preview

#### Scenario: The size claim is measured, not assumed
- **WHEN** this change is reviewed
- **THEN** the recorded served size and on-disk size of the runtime accompany
  it, so the budget is stated in real numbers

### Requirement: The reader's download is bounded by their own choice

#### Scenario: A reader who does not execute downloads nothing extra
- **WHEN** a reader visits the site and never triggers execution
- **THEN** the bytes they download are what the site cost before this change

#### Scenario: The runtime is cacheable across runs and visits
- **WHEN** a reader executes a query, then executes another or returns later
- **THEN** the runtime's binary assets are served from cache rather than
  re-downloaded, because their URLs identify their content
