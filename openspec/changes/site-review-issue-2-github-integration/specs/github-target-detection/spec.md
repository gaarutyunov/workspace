## ADDED Requirements

### Requirement: Detect repository from page HTML

The system SHALL scan the reviewed page's HTML for a GitHub repository URL and
propose the discovered `owner/name` as the default repository to connect.

#### Scenario: Repo link present in page
- **WHEN** the reviewed page's HTML contains one or more `github.com/<owner>/<repo>`
  links
- **THEN** the system proposes the most likely `owner/name` as the default
  repository suggestion

#### Scenario: Multiple distinct repos in page
- **WHEN** the page references more than one distinct repository
- **THEN** the system returns the candidates it found so the user can choose,
  rather than silently guessing a single one

#### Scenario: No repo link present
- **WHEN** the page HTML contains no GitHub repository URL
- **THEN** the system reports no auto-detected repository and the user may select
  one manually

### Requirement: Detect PR number from URL path

The system SHALL derive a pull-request number from the reviewed page's URL when
the path contains a `pr-preview/pr-<N>/` segment, resolving it to PR `#<N>` in the
connected repository.

#### Scenario: PR preview path
- **WHEN** the reviewed page URL path contains `pr-preview/pr-3/`
- **THEN** the system resolves the sync target to pull request `#3`

#### Scenario: No PR segment in path
- **WHEN** the reviewed page URL path contains no `pr-preview/pr-<N>/` segment
- **THEN** the system reports no detected PR and the target falls back to
  issue-based sync

#### Scenario: Detected PR does not exist in the connected repo
- **WHEN** a PR number is parsed from the path but no such open PR exists in the
  connected repository
- **THEN** the system reports the PR as unavailable and falls back to issue-based
  sync rather than failing

### Requirement: Resolve a sync target

Given a connected repository and a reviewed page, the system SHALL resolve a
single sync target descriptor identifying whether comments will go to a PR, an
existing issue, or a new issue.

#### Scenario: PR target resolved
- **WHEN** a valid PR is detected for the connected repo
- **THEN** the resolved target is that pull request

#### Scenario: Issue target requires user choice
- **WHEN** no PR is detected
- **THEN** the resolved target indicates issue mode and the system provides the
  repo's open issues for the user to append to, plus the option to create a new
  issue
