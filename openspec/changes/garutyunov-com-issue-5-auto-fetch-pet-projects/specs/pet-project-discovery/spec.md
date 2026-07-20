## ADDED Requirements

### Requirement: Discover pet projects from GitHub by topic

At build time the site SHALL query GitHub for all repositories owned by
`gaarutyunov` that carry the `pet-project` topic, and use that result as the set
of pet projects to render.

#### Scenario: Repos with the topic are discovered
- **WHEN** the site is built and `gaarutyunov` has repos tagged `pet-project`
- **THEN** each such repo is considered a candidate pet project

#### Scenario: Repos without the topic are ignored
- **WHEN** a `gaarutyunov` repo does not carry the `pet-project` topic
- **THEN** it is not included as a pet project

### Requirement: Use the repo homepage as the project URL

For each discovered repo the site SHALL use the repo's `homepage` field (the
GitHub Pages website URL) as the project URL fed into the metadata crawl.

#### Scenario: Repo has a homepage
- **WHEN** a discovered repo has a non-empty `homepage`
- **THEN** that URL is used as the project's URL for the crawl and as the card link

#### Scenario: Repo has no homepage
- **WHEN** a discovered repo has an empty or missing `homepage`
- **THEN** the repo is skipped (not rendered) rather than linked to a non-site URL

### Requirement: Exclude non-project repos

The discovery SHALL exclude the site's own repository (`garutyunov.com`) even if
it were to carry the topic, so the site never lists itself as a pet project.

#### Scenario: Site repo is filtered out
- **WHEN** the discovery result would contain the `garutyunov.com` repo
- **THEN** it is removed from the pet-project list

### Requirement: Map GitHub metadata to the pipeline fallback

Each discovered repo SHALL be mapped to the pipeline's `Project` shape, with a
fallback derived from GitHub metadata: name from the repo, description from the
repo description, and `created` from the repo `created_at`. The card icon SHALL
come from the live page's `og:image` via the existing crawl (repos have no icon
field).

#### Scenario: Fallback populated from repo metadata
- **WHEN** a repo is mapped to a project
- **THEN** its fallback name/description/created come from the repo's fields and
  the crawl supplies the icon from the live page's `og:image`

#### Scenario: Crawl overrides fallback when live metadata is present
- **WHEN** the project's live page exposes `og:title` / `og:description` /
  `og:image`
- **THEN** those values are used in preference to the GitHub-derived fallback
  (existing pipeline behavior is preserved)

### Requirement: Deterministic ordering

The rendered pet projects SHALL appear in a stable, deterministic order across
builds (e.g. by creation date) rather than GitHub's incidental API order.

#### Scenario: Stable order
- **WHEN** the site is built twice with the same set of repos
- **THEN** the projects render in the same order both times

### Requirement: Build never fails on GitHub unavailability

Discovery SHALL degrade gracefully so that a GitHub API failure, rate-limit, or
timeout never breaks `next build`.

#### Scenario: GitHub API unreachable at build
- **WHEN** the GitHub discovery request fails or times out during the build
- **THEN** the build completes successfully with an empty (or last-known) pet-project
  list rather than throwing

#### Scenario: Authenticated when a token is available
- **WHEN** a `GITHUB_TOKEN` is present in the build environment
- **THEN** the discovery request is authenticated (higher rate limit); when absent
  it still attempts an unauthenticated request
